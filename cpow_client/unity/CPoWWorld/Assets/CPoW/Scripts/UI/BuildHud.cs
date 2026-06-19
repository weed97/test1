using UnityEngine;

namespace CPoW.UI
{
    /// <summary>IMGUI build panel — blueprint, parts, validate [V].</summary>
    public sealed class BuildHud : MonoBehaviour
    {
        CPoW.World.BuildController _build;
        Vector2 _scroll;
        bool _visible = true;

        public void Bind(CPoW.World.BuildController build)
        {
            _build = build;
        }

        void Update()
        {
            if (_build == null) return;
            if (Input.GetKeyDown(KeyCode.V))
                _ = _build.TryValidateAsync();
            if (Input.GetKeyDown(KeyCode.B))
                _visible = !_visible;
        }

        void OnGUI()
        {
            if (_build == null || !_visible) return;

            const int w = 340;
            const int h = 460;
            var rect = new Rect(12, Screen.height - h - 12, w, h);
            GUI.Box(rect, "건축 (V=검증, B=숨기기)");

            GUILayout.BeginArea(new Rect(rect.x + 8, rect.y + 28, w - 16, h - 36));
            _scroll = GUILayout.BeginScrollView(_scroll);

            var catalog = _build.Catalog;
            if (catalog.Blueprints.Count == 0)
            {
                GUILayout.Label("블루프린트 카탈로그 없음");
            }
            else
            {
                GUILayout.Label("— 블루프린트 —");
                for (var i = 0; i < catalog.Blueprints.Count; i++)
                {
                    var bp = catalog.Blueprints[i];
                    if (GUILayout.Toggle(_build.BlueprintIndex == i, $"{bp.Label} ({bp.BlueprintId})", "Button"))
                        _build.BlueprintIndex = i;
                }
            }

            var selected = _build.SelectedBlueprint;
            if (selected != null)
            {
                GUILayout.Space(4);
                GUILayout.Label($"바이옴: {_build.CurrentBiomeId} | 구역 {_build.CurrentZoneClass}");
                GUILayout.Label($"타입 {selected.BuildingType} | zone≥{selected.ZoneMin} | civ≥{selected.CivMin}");

                GUILayout.BeginHorizontal();
                if (GUILayout.Button("프리셋 채우기"))
                    _build.ApplyBlueprintPreset();
                if (GUILayout.Button("인벤→재료"))
                    _build.FillMaterialsFromInventory();
                if (GUILayout.Button("초기화"))
                    _build.ClearPlacement();
                GUILayout.EndHorizontal();

                GUILayout.Label("— 모듈 —");
                foreach (var req in selected.Modules)
                    DrawCountRow(req.ModuleId, req.Count, true);

                GUILayout.Label("— 재료 —");
                foreach (var req in selected.Materials)
                    DrawCountRow(req.ModuleId, req.Count, false);

                GUILayout.Label("— 문명 레벨 —");
                _build.CivilizationLevel = Mathf.RoundToInt(
                    GUILayout.HorizontalSlider(_build.CivilizationLevel, 0f, 5f));
                GUILayout.Label($"civilization_level = {_build.CivilizationLevel}");
            }

            GUILayout.Space(8);
            GUI.enabled = !_build.IsBusy;
            if (GUILayout.Button("검증 [V]", GUILayout.Height(34)))
                _ = _build.TryValidateAsync();
            GUI.enabled = true;

            GUILayout.Space(6);
            GUILayout.Label(_build.StatusLine, GUI.skin.box);

            var last = _build.LastValidation;
            if (!string.IsNullOrEmpty(last.Reason))
            {
                var color = last.Ok ? Color.green : new Color(1f, 0.55f, 0.35f);
                GUI.color = color;
                GUILayout.Label($"reason: {last.Reason}");
                GUI.color = Color.white;
                foreach (var miss in last.Missing)
                {
                    GUILayout.Label(
                        $"  {miss.Kind} {miss.ModuleId}: need {miss.Count}, have {miss.Have}");
                }
            }

            GUILayout.EndScrollView();
            GUILayout.EndArea();
        }

        void DrawCountRow(string id, int required, bool isModule)
        {
            var have = isModule ? _build.GetModuleCount(id) : _build.GetMaterialCount(id);
            GUILayout.BeginHorizontal();
            GUILayout.Label($"{id} ({have}/{required})", GUILayout.Width(180));
            if (GUILayout.Button("-", GUILayout.Width(28)))
            {
                if (isModule)
                    _build.SetModuleCount(id, have - 1);
                else
                    _build.SetMaterialCount(id, have - 1);
            }
            if (GUILayout.Button("+", GUILayout.Width(28)))
            {
                if (isModule)
                    _build.SetModuleCount(id, have + 1);
                else
                    _build.SetMaterialCount(id, have + 1);
            }
            if (GUILayout.Button("max", GUILayout.Width(36)))
            {
                if (isModule)
                    _build.SetModuleCount(id, required);
                else
                    _build.SetMaterialCount(id, required);
            }
            GUILayout.EndHorizontal();
        }
    }
}
