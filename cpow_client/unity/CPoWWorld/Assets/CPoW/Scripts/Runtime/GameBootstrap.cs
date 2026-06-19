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
        BuildController _build;
        WorldStreamClient _worldStream;
        WorldDropRenderer _dropRenderer;
        float _nextPoll;
        float _nextPose;

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
                var blueprintCatalog = BlueprintCatalogCache.Parse(catalogJson);
                Debug.Log($"[CPoW] World catalog ores={catalog.OreIds.Count} blueprints={blueprintCatalog.Blueprints.Count}");

                _streamer.Initialize(_session.World, _session.AreaId, playerProxy);

                _mining = gameObject.GetComponent<MiningController>();
                if (_mining == null)
                    _mining = gameObject.AddComponent<MiningController>();
                _mining.Initialize(_session, playerProxy, catalog);

                var hud = gameObject.GetComponent<CPoW.UI.MiningHud>();
                if (hud == null)
                    hud = gameObject.AddComponent<CPoW.UI.MiningHud>();
                hud.Bind(_mining);
                _mining.MineCompleted += _ => _ = RefreshAreaStateAsync();
                await _mining.RefreshInventoryAsync();

                var ghost = gameObject.GetComponent<BuildGhostRenderer>();
                if (ghost == null)
                    ghost = gameObject.AddComponent<BuildGhostRenderer>();

                _build = gameObject.GetComponent<BuildController>();
                if (_build == null)
                    _build = gameObject.AddComponent<BuildController>();
                _build.Initialize(_session, playerProxy, _mining, ghost, blueprintCatalog);

                var buildHud = gameObject.GetComponent<CPoW.UI.BuildHud>();
                if (buildHud == null)
                    buildHud = gameObject.AddComponent<CPoW.UI.BuildHud>();
                buildHud.Bind(_build);

                _dropRenderer = gameObject.GetComponent<WorldDropRenderer>();
                if (_dropRenderer == null)
                    _dropRenderer = gameObject.AddComponent<WorldDropRenderer>();

                _worldStream = gameObject.GetComponent<WorldStreamClient>();
                if (_worldStream == null)
                    _worldStream = gameObject.AddComponent<WorldStreamClient>();
                _worldStream.MessageReceived += OnStreamMessage;
                await _worldStream.ConnectAsync(
                    _session.AreaId,
                    _session.UserId,
                    playerProxy.position.x,
                    playerProxy.position.z);

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

        void OnStreamMessage(string json)
        {
            if (string.IsNullOrEmpty(json)) return;

            if (json.Contains("\"type\":\"subscribed\""))
            {
                var dropsIdx = json.IndexOf("\"drops\":[", System.StringComparison.Ordinal);
                if (dropsIdx >= 0 && _dropRenderer != null)
                {
                    var start = dropsIdx + "\"drops\":".Length;
                    var end = json.IndexOf(']', start);
                    if (end > start)
                        _dropRenderer.SyncDropsJson(json.Substring(start, end - start + 1));
                }
                if (_mining != null)
                    _mining.ApplyInventoryJson(json);
                return;
            }

            if (_dropRenderer != null)
                _dropRenderer.ApplyStreamJson(json);
            if (_mining != null && json.Contains("inventory_delta"))
                _ = _mining.RefreshInventoryAsync();
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
            if (_worldStream != null && Time.time >= _nextPose)
            {
                _nextPose = Time.time + 0.4f;
                _ = _worldStream.SendPoseAsync(playerProxy.position.x, playerProxy.position.z);
            }
        }

        async void OnDestroy()
        {
            if (_worldStream != null)
                await _worldStream.DisconnectAsync();
        }
    }
}
