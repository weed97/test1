using System.Collections.Generic;
using System.Threading.Tasks;
using CPoW.Net;
using CPoW.Runtime;
using UnityEngine;

namespace CPoW.World
{
    /// <summary>Blueprint placement + POST /v1/world/build/validate.</summary>
    public sealed class BuildController : MonoBehaviour
    {
        [SerializeField] int civilizationLevel;
        [SerializeField] float gridSnap = 1f;

        CpowSession _session;
        Transform _player;
        MiningController _mining;
        BuildGhostRenderer _ghost;
        BlueprintCatalogCache _catalog = new();
        int _blueprintIndex;

        readonly Dictionary<string, int> _placedModules = new();
        readonly Dictionary<string, int> _placedMaterials = new();

        public BlueprintCatalogCache Catalog => _catalog;
        public BuildValidationResult LastValidation { get; private set; } = new();
        public string StatusLine { get; private set; } = "건축 모드 — 블루프린트 선택";
        public bool IsBusy { get; private set; }
        public int CivilizationLevel
        {
            get => civilizationLevel;
            set => civilizationLevel = Mathf.Max(0, value);
        }

        public IReadOnlyDictionary<string, int> PlacedModules => _placedModules;
        public IReadOnlyDictionary<string, int> PlacedMaterials => _placedMaterials;

        public BlueprintDef SelectedBlueprint =>
            _catalog.Blueprints.Count == 0
                ? null
                : _catalog.Blueprints[Mathf.Clamp(_blueprintIndex, 0, _catalog.Blueprints.Count - 1)];

        public int BlueprintIndex
        {
            get => _blueprintIndex;
            set
            {
                _blueprintIndex = Mathf.Clamp(value, 0, Mathf.Max(0, _catalog.Blueprints.Count - 1));
                ResetCountsForBlueprint();
                RefreshGhost();
            }
        }

        public string CurrentBiomeId =>
            _mining != null && !string.IsNullOrEmpty(_mining.CurrentCell.BiomeId)
                ? _mining.CurrentCell.BiomeId
                : "plains";

        public string CurrentZoneClass =>
            _mining != null ? _mining.CurrentCell.ZoneClass : "safe";

        Vector3 _lastAnchor;
        string _lastBlueprintId = "";
        int _lastModuleHash;

        public void Initialize(
            CpowSession session,
            Transform player,
            MiningController mining,
            BuildGhostRenderer ghost,
            BlueprintCatalogCache catalog = null)
        {
            _session = session;
            _player = player;
            _mining = mining;
            _ghost = ghost;
            if (catalog != null)
                _catalog = catalog;
            ResetCountsForBlueprint();
            RefreshGhost();
        }

        void LateUpdate()
        {
            if (_player == null || _ghost == null) return;
            var anchor = SnapAnchor();
            var bp = SelectedBlueprint;
            var bpId = bp?.BlueprintId ?? "";
            var hash = ModuleHash();
            if (anchor == _lastAnchor && bpId == _lastBlueprintId && hash == _lastModuleHash)
                return;
            _lastAnchor = anchor;
            _lastBlueprintId = bpId;
            _lastModuleHash = hash;
            RefreshGhost();
        }

        int ModuleHash()
        {
            var h = 17;
            foreach (var kv in _placedModules)
                h = h * 31 + kv.Key.GetHashCode() + kv.Value;
            return h;
        }

        public void ForceRefreshGhost()
        {
            _lastModuleHash = -1;
            RefreshGhost();
        }

        public void SetModuleCount(string moduleId, int count)
        {
            if (string.IsNullOrEmpty(moduleId)) return;
            if (count <= 0)
                _placedModules.Remove(moduleId);
            else
                _placedModules[moduleId] = count;
            RefreshGhost();
        }

        public int GetModuleCount(string moduleId) =>
            _placedModules.TryGetValue(moduleId, out var c) ? c : 0;

        public void SetMaterialCount(string materialId, int count)
        {
            if (string.IsNullOrEmpty(materialId)) return;
            if (count <= 0)
                _placedMaterials.Remove(materialId);
            else
                _placedMaterials[materialId] = count;
        }

        public int GetMaterialCount(string materialId) =>
            _placedMaterials.TryGetValue(materialId, out var c) ? c : 0;

        public void ApplyBlueprintPreset()
        {
            var bp = SelectedBlueprint;
            if (bp == null) return;
            _placedModules.Clear();
            _placedMaterials.Clear();
            foreach (var m in bp.Modules)
                _placedModules[m.ModuleId] = m.Count;
            foreach (var m in bp.Materials)
                _placedMaterials[m.ModuleId] = m.Count;
            RefreshGhost();
            StatusLine = $"프리셋 적용: {bp.Label}";
        }

        public void FillMaterialsFromInventory()
        {
            if (_mining == null) return;
            foreach (var kv in _mining.Inventory.Stacks)
            {
                var key = kv.Key;
                var asInt = Mathf.FloorToInt(kv.Value);
                if (asInt > 0)
                    _placedMaterials[key] = asInt;
            }
            StatusLine = "인벤토리 스택 → 재료 카운트 반영";
        }

        public void ClearPlacement()
        {
            _placedModules.Clear();
            _placedMaterials.Clear();
            RefreshGhost();
            StatusLine = "배치 초기화";
        }

        void ResetCountsForBlueprint()
        {
            _placedModules.Clear();
            _placedMaterials.Clear();
            var bp = SelectedBlueprint;
            if (bp == null) return;
            foreach (var m in bp.Modules)
                _placedModules[m.ModuleId] = 0;
            foreach (var m in bp.Materials)
                _placedMaterials[m.ModuleId] = 0;
        }

        Vector3 SnapAnchor()
        {
            if (_player == null) return Vector3.zero;
            var p = _player.position;
            if (gridSnap <= 0f) return new Vector3(p.x, 0f, p.z);
            var gx = Mathf.Round(p.x / gridSnap) * gridSnap;
            var gz = Mathf.Round(p.z / gridSnap) * gridSnap;
            return new Vector3(gx, 0f, gz);
        }

        void RefreshGhost()
        {
            if (_ghost == null) return;
            var bp = SelectedBlueprint;
            if (bp == null)
            {
                _ghost.Clear();
                return;
            }
            _ghost.SetValidTint(LastValidation.Ok || string.IsNullOrEmpty(LastValidation.Reason));
            _ghost.Rebuild(SnapAnchor(), bp.BlueprintId, _placedModules);
        }

        public async Task<bool> TryValidateAsync()
        {
            if (IsBusy || _session == null || string.IsNullOrEmpty(_session.AreaId))
                return false;
            var bp = SelectedBlueprint;
            if (bp == null)
            {
                StatusLine = "블루프린트 없음";
                return false;
            }

            IsBusy = true;
            try
            {
                if (_mining != null)
                    await _mining.RefreshCellAsync();

                var json = await _session.World.ValidateBuildAsync(
                    _session.AreaId,
                    CurrentBiomeId,
                    bp.BlueprintId,
                    _placedModules,
                    _placedMaterials,
                    civilizationLevel);

                LastValidation = BuildValidationResult.FromJson(json);
                _ghost?.SetValidTint(LastValidation.Ok);
                RefreshGhost();

                if (LastValidation.Ok)
                    StatusLine = $"검증 OK — {LastValidation.BlueprintLabel} ({LastValidation.Reason})";
                else
                    StatusLine = $"검증 실패: {LastValidation.Reason}";

                return LastValidation.Ok;
            }
            catch (System.Exception ex)
            {
                StatusLine = "검증 오류: " + ex.Message;
                return false;
            }
            finally
            {
                IsBusy = false;
            }
        }
    }
}
