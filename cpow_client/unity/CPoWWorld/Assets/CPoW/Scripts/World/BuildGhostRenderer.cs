using System.Collections.Generic;
using UnityEngine;

namespace CPoW.World
{
    /// <summary>Semi-transparent module ghosts at build anchor.</summary>
    public sealed class BuildGhostRenderer : MonoBehaviour
    {
        readonly List<GameObject> _instances = new();
        Material _ghostMat;
        bool _validTint = true;

        public void SetValidTint(bool valid) => _validTint = valid;

        public void Rebuild(
            Vector3 anchorWorld,
            string blueprintId,
            IReadOnlyDictionary<string, int> placedModules)
        {
            Clear();
            if (string.IsNullOrEmpty(blueprintId)) return;

            EnsureMaterial();
            var slots = BuildLayout.SlotsFor(blueprintId, placedModules);
            foreach (var slot in slots)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = "Ghost_" + slot.ModuleId;
                go.transform.SetParent(transform, false);
                go.transform.position = anchorWorld + slot.LocalPos;
                go.transform.localScale = slot.Scale;
                var col = go.GetComponent<Collider>();
                if (col != null) Destroy(col);
                var rend = go.GetComponent<Renderer>();
                rend.sharedMaterial = _ghostMat;
                rend.material.color = ModuleColor(slot.ModuleId);
                _instances.Add(go);
            }
        }

        public void Clear()
        {
            foreach (var go in _instances)
            {
                if (go != null) Destroy(go);
            }
            _instances.Clear();
        }

        void EnsureMaterial()
        {
            if (_ghostMat != null) return;
            var shader = Shader.Find("Standard");
            _ghostMat = new Material(shader);
            _ghostMat.SetFloat("_Mode", 3f);
            _ghostMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            _ghostMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            _ghostMat.SetInt("_ZWrite", 0);
            _ghostMat.DisableKeyword("_ALPHATEST_ON");
            _ghostMat.EnableKeyword("_ALPHABLEND_ON");
            _ghostMat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            _ghostMat.renderQueue = 3000;
        }

        Color ModuleColor(string moduleId)
        {
            var baseColor = moduleId switch
            {
                "foundation_1x1" or "foundation_2x2" => new Color(0.55f, 0.52f, 0.48f),
                "wall_t1" => new Color(0.65f, 0.62f, 0.58f),
                "heater_core" => new Color(0.95f, 0.45f, 0.15f),
                "furnace_box" => new Color(0.35f, 0.35f, 0.38f),
                "chimney_stack" => new Color(0.5f, 0.5f, 0.52f),
                "pipe_straight" => new Color(0.3f, 0.55f, 0.75f),
                "cable_segment" => new Color(0.85f, 0.75f, 0.2f),
                _ => new Color(0.6f, 0.6f, 0.65f),
            };
            var alpha = _validTint ? 0.42f : 0.55f;
            if (!_validTint)
                baseColor = Color.Lerp(baseColor, new Color(0.95f, 0.25f, 0.2f), 0.45f);
            baseColor.a = alpha;
            return baseColor;
        }

        void OnDestroy()
        {
            Clear();
            if (_ghostMat != null) Destroy(_ghostMat);
        }
    }
}
