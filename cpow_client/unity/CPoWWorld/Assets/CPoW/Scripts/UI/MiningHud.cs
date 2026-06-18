using UnityEngine;

namespace CPoW.UI
{
    /// <summary>IMGUI mining panel — tool, depth, mine [E].</summary>
    public sealed class MiningHud : MonoBehaviour
    {
        CPoW.World.MiningController _mining;
        Vector2 _scroll;
        int _orePickerIndex;
        bool _visible = true;

        public void Bind(CPoW.World.MiningController mining)
        {
            _mining = mining;
        }

        void Update()
        {
            if (_mining == null) return;
            if (Input.GetKeyDown(KeyCode.E))
                _ = _mining.TryMineAsync();
            if (Input.GetKeyDown(KeyCode.Tab))
                _visible = !_visible;
        }

        void OnGUI()
        {
            if (_mining == null || !_visible) return;

            const int w = 320;
            const int h = 420;
            var rect = new Rect(Screen.width - w - 12, Screen.height - h - 12, w, h);
            GUI.Box(rect, "채굴 (E)");

            GUILayout.BeginArea(new Rect(rect.x + 8, rect.y + 28, w - 16, h - 36));
            _scroll = GUILayout.BeginScrollView(_scroll);

            var cell = _mining.CurrentCell;
            GUILayout.Label($"위치 광맥: {(cell.HasOre ? cell.OreLabel + " (" + cell.OreId + ")" : "없음")}");
            GUILayout.Label($"구역: {cell.ZoneClass} | 위험 {cell.HazardDanger}");
            if (!string.IsNullOrEmpty(cell.AudioCue))
                GUI.color = cell.HazardDanger > 0 ? new Color(1f, 0.55f, 0.2f) : Color.white;
            GUILayout.Label($"소리 예고: {cell.AudioCue} (단계 {cell.AudioStage})");
            GUI.color = Color.white;

            GUILayout.Space(6);
            GUILayout.Label("— 도구 —");
            GUILayout.BeginHorizontal();
            if (GUILayout.Toggle(_mining.ToolType == "pickaxe", "곡괭이", "Button"))
                _mining.ToolType = "pickaxe";
            if (GUILayout.Toggle(_mining.ToolType == "drill", "드릴", "Button"))
                _mining.ToolType = "drill";
            GUILayout.EndHorizontal();

            GUILayout.BeginHorizontal();
            GUILayout.Label($"티어 {_mining.ToolTier}", GUILayout.Width(70));
            if (GUILayout.Button("-", GUILayout.Width(28)))
                _mining.ToolTier--;
            if (GUILayout.Button("+", GUILayout.Width(28)))
                _mining.ToolTier++;
            GUILayout.EndHorizontal();

            GUILayout.Label("— 깊이 —");
            _mining.DepthY = Mathf.RoundToInt(GUILayout.HorizontalSlider(_mining.DepthY, 8f, 120f));
            GUILayout.Label($"depth_y = {_mining.DepthY}");

            GUILayout.Space(4);
            _mining.UseManualOreId = GUILayout.Toggle(_mining.UseManualOreId, "수동 광물 선택 (광맥 없을 때)");
            if (_mining.UseManualOreId && _mining.Catalog.OreIds.Count > 0)
            {
                var names = _mining.Catalog.OreLabels.ToArray();
                _orePickerIndex = GUILayout.SelectionGrid(
                    _orePickerIndex,
                    names,
                    2);
                if (_orePickerIndex >= 0 && _orePickerIndex < _mining.Catalog.OreIds.Count)
                    _mining.ManualOreId = _mining.Catalog.OreIds[_orePickerIndex];
            }

            GUILayout.Label("소모품 (BM 안정제 등)");
            _mining.Consumable = GUILayout.TextField(_mining.Consumable ?? "");

            GUILayout.Space(8);
            GUI.enabled = !_mining.IsBusy;
            if (GUILayout.Button("채굴 [E]", GUILayout.Height(36)))
                _ = _mining.TryMineAsync();
            GUI.enabled = true;

            GUILayout.Space(6);
            GUILayout.Label(_mining.StatusLine, GUI.skin.box);

            var last = _mining.LastMine;
            if (!string.IsNullOrEmpty(last.Reason) && last.Reason != "mined")
                GUILayout.Label($"결과: {last.Reason}");
            else if (last.Ok)
                GUILayout.Label($"획득 T{last.MiningTier} | +{last.Amount:F2} {last.OreId}");

            GUILayout.Label("Tab: 패널 숨기기 | WASD: 이동", GUI.skin.label);

            GUILayout.EndScrollView();
            GUILayout.EndArea();
        }
    }
}
