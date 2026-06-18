using System.Threading.Tasks;
using CPoW.Areas;
using CPoW.Net;
using CPoW.World;
using UnityEngine;

namespace CPoW.Runtime
{
    /// <summary>Bootstraps API session, area founding, chunk streaming, and object sync.</summary>
    public sealed class GameBootstrap : MonoBehaviour
    {
        [SerializeField] string apiBaseUrl = CpowApiConfig.DefaultBaseUrl;
        [SerializeField] string creatorId = CpowApiConfig.DefaultCreatorId;
        [SerializeField] string areaLabel = "Unity 오픈월드";
        [SerializeField] float statePollSeconds = 4f;
        [SerializeField] Transform playerProxy;

        CpowSession _session;
        ChunkStreamer _streamer;
        AreaObjectRenderer _renderer;
        MiningController _mining;
        float _nextPoll;

        async void Start()
        {
            if (playerProxy == null)
            {
                var proxy = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                proxy.name = "PlayerProxy";
                proxy.transform.position = new Vector3(32f, 1f, 32f);
                playerProxy = proxy.transform;
            }

            CpowApiConfig.BaseUrl = apiBaseUrl;
            CpowApiConfig.CreatorId = creatorId;
            _session = new CpowSession(creatorId, apiBaseUrl);

            _renderer = gameObject.GetComponent<AreaObjectRenderer>();
            if (_renderer == null)
                _renderer = gameObject.AddComponent<AreaObjectRenderer>();

            _streamer = gameObject.GetComponent<ChunkStreamer>();
            if (_streamer == null)
                _streamer = gameObject.AddComponent<ChunkStreamer>();

            try
            {
                var health = await _session.Areas.HealthCheckAsync();
                Debug.Log($"[CPoW] API health: {health}");

                var found = await _session.Areas.FoundAreaAsync(areaLabel);
                _session.AreaId = _session.Areas.CurrentAreaId;
                Debug.Log($"[CPoW] Founded area {_session.AreaId}");

                var catalogJson = await _session.World.GetCatalogAsync();
                var catalog = WorldCatalogCache.Parse(catalogJson);
                Debug.Log($"[CPoW] World catalog ores={catalog.OreIds.Count}");

                _streamer.Initialize(_session.World, _session.AreaId, playerProxy);

                _mining = gameObject.GetComponent<MiningController>();
                if (_mining == null)
                    _mining = gameObject.AddComponent<MiningController>();
                _mining.Initialize(_session, playerProxy, catalog);

                var hud = gameObject.GetComponent<CPoW.UI.MiningHud>();
                if (hud == null)
                    hud = gameObject.AddComponent<CPoW.UI.MiningHud>();
                hud.Bind(_mining);

                await RefreshAreaStateAsync();
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[CPoW] bootstrap failed: {ex.Message}");
            }
        }

        async void Update()
        {
            if (_session == null || string.IsNullOrEmpty(_session.AreaId))
                return;
            if (Time.time < _nextPoll)
                return;
            _nextPoll = Time.time + statePollSeconds;
            await RefreshAreaStateAsync();
        }

        async Task RefreshAreaStateAsync()
        {
            try
            {
                var json = await _session.Areas.FetchStateAsync(_session.AreaId);
                _renderer.SyncFromStateJson(json);
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"[CPoW] state poll failed: {ex.Message}");
            }
        }

        /// <summary>Simple WASD proxy movement for chunk streaming demo.</summary>
        void LateUpdate()
        {
            if (playerProxy == null) return;
            var dx = Input.GetAxisRaw("Horizontal");
            var dz = Input.GetAxisRaw("Vertical");
            if (Mathf.Approximately(dx, 0f) && Mathf.Approximately(dz, 0f))
                return;
            var move = new Vector3(dx, 0f, dz).normalized * (8f * Time.deltaTime);
            playerProxy.position += move;
        }
    }
}
