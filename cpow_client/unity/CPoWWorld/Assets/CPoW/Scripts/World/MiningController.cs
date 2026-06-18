using System.Threading.Tasks;
using CPoW.Net;
using CPoW.Runtime;
using UnityEngine;

namespace CPoW.World
{
    /// <summary>Player-position mining — cell inspect + POST /v1/world/mine.</summary>
    public sealed class MiningController : MonoBehaviour
    {
        [Header("Tool")]
        [SerializeField] string toolType = "pickaxe";
        [SerializeField] int toolTier = 2;
        [SerializeField] int depthY = 40;
        [SerializeField] string consumable = "";
        [SerializeField] bool useManualOreId;
        [SerializeField] string manualOreId = "coal";

        [Header("Timing")]
        [SerializeField] float cellRefreshInterval = 0.5f;
        [SerializeField] int cellSize = 64;

        CpowSession _session;
        Transform _player;
        float _nextRefresh;
        bool _busy;

        public string ToolType
        {
            get => toolType;
            set => toolType = value;
        }

        public int ToolTier
        {
            get => toolTier;
            set => toolTier = Mathf.Clamp(value, 0, 6);
        }

        public int DepthY
        {
            get => depthY;
            set => depthY = Mathf.Clamp(value, 0, 256);
        }

        public string Consumable
        {
            get => consumable;
            set => consumable = value ?? "";
        }

        public bool UseManualOreId
        {
            get => useManualOreId;
            set => useManualOreId = value;
        }

        public string ManualOreId
        {
            get => manualOreId;
            set => manualOreId = value ?? "";
        }

        public bool IsBusy => _busy;
        public CellInspectResult CurrentCell { get; private set; } = new();
        public MineResult LastMine { get; private set; } = new();
        public WorldCatalogCache Catalog { get; private set; } = new();
        public string StatusLine { get; private set; } = "셀 조사 대기…";

        public void Initialize(CpowSession session, Transform player, WorldCatalogCache catalog = null)
        {
            _session = session;
            _player = player;
            if (catalog != null)
                Catalog = catalog;
        }

        void Update()
        {
            if (_session == null || _player == null || string.IsNullOrEmpty(_session.AreaId))
                return;
            if (_busy || Time.time < _nextRefresh)
                return;
            _nextRefresh = Time.time + cellRefreshInterval;
            _ = RefreshCellAsync();
        }

        public async Task RefreshCellAsync()
        {
            if (_session == null || _player == null) return;
            try
            {
                var json = await _session.World.InspectCellAsync(
                    _session.AreaId,
                    _player.position.x,
                    _player.position.z,
                    depthY,
                    cellSize,
                    advanceTick: false);
                CurrentCell = CellInspectResult.FromJson(json);
                if (!CurrentCell.HasOre && !useManualOreId)
                    StatusLine = $"바이옴: {CurrentCell.BiomeLabel} — 광맥 없음 (깊이 {depthY})";
                else
                {
                    var ore = useManualOreId ? manualOreId : CurrentCell.OreId;
                    StatusLine = $"바이옴: {CurrentCell.BiomeLabel} | 광물: {ore}";
                }
            }
            catch (System.Exception ex)
            {
                StatusLine = "셀 조사 실패: " + ex.Message;
            }
        }

        public async Task<bool> TryMineAsync()
        {
            if (_busy || _session == null || _player == null)
                return false;
            _busy = true;
            try
            {
                await RefreshCellAsync();
                var oreId = useManualOreId ? manualOreId : CurrentCell.OreId;
                if (string.IsNullOrEmpty(oreId))
                {
                    LastMine = new MineResult { Ok = false, Reason = "no_ore_selected" };
                    StatusLine = "채굴 불가 — 이 위치에 광맥이 없습니다.";
                    return false;
                }

                var json = await _session.World.MineAsync(
                    _session.AreaId,
                    _session.UserId,
                    _player.position.x,
                    _player.position.z,
                    depthY,
                    toolType,
                    toolTier,
                    oreId,
                    consumable);

                LastMine = MineResult.FromJson(json);
                if (LastMine.Ok)
                {
                    StatusLine = $"채굴 성공: {LastMine.ResourceLabel} x{LastMine.Amount:F2} | XP {LastMine.MiningXp:F0} T{LastMine.MiningTier}";
                }
                else
                {
                    StatusLine = $"채굴 실패: {LastMine.Reason}";
                }
                return LastMine.Ok;
            }
            catch (System.Exception ex)
            {
                StatusLine = "채굴 오류: " + ex.Message;
                return false;
            }
            finally
            {
                _busy = false;
            }
        }

        public string ActiveOreId() =>
            useManualOreId ? manualOreId : (CurrentCell.HasOre ? CurrentCell.OreId : "");
    }
}
