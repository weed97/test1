using System.Collections.Generic;
using CPoW.Net;
using UnityEngine;

namespace CPoW.World
{
    /// <summary>AOI world drops — spawn/despawn from stream events.</summary>
    public sealed class WorldDropRenderer : MonoBehaviour
    {
        readonly Dictionary<string, GameObject> _drops = new();

        public void ApplyStreamJson(string json)
        {
            if (string.IsNullOrEmpty(json)) return;
            if (json.Contains("\"type\":\"drop_spawn\""))
                SpawnFromJson(json);
            else if (json.Contains("\"type\":\"drop_despawn\""))
                Despawn(JsonField.GetString(json, "drop_id", ""));
        }

        public void SyncDropsJson(string dropsArrayJson)
        {
            ClearAll();
            if (string.IsNullOrEmpty(dropsArrayJson)) return;
            var idx = 0;
            while (idx < dropsArrayJson.Length)
            {
                var key = "\"drop_id\":\"";
                var i = dropsArrayJson.IndexOf(key, idx, System.StringComparison.Ordinal);
                if (i < 0) break;
                var start = dropsArrayJson.LastIndexOf('{', i);
                var end = dropsArrayJson.IndexOf('}', i);
                if (start < 0 || end < 0) break;
                SpawnFromJson(dropsArrayJson.Substring(start, end - start + 1));
                idx = end + 1;
            }
        }

        void SpawnFromJson(string json)
        {
            var id = JsonField.GetString(json, "drop_id", "");
            if (string.IsNullOrEmpty(id) || _drops.ContainsKey(id)) return;
            var ore = JsonField.GetString(json, "ore_id", "ore");
            var x = JsonField.GetFloat(json, "x", 0f);
            var z = JsonField.GetFloat(json, "z", 0f);
            var amount = JsonField.GetFloat(json, "amount", 1f);

            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "Drop_" + id;
            go.transform.SetParent(transform, false);
            go.transform.position = new Vector3(x, 0.35f, z);
            go.transform.localScale = Vector3.one * 0.45f;
            var rend = go.GetComponent<Renderer>();
            rend.material.color = OreColor(ore);

            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(go.transform, false);
            labelGo.transform.localPosition = new Vector3(0f, 0.6f, 0f);
            var tm = labelGo.AddComponent<TextMesh>();
            tm.text = $"{ore}\n{amount:F1}";
            tm.fontSize = 24;
            tm.characterSize = 0.07f;
            tm.anchor = TextAnchor.MiddleCenter;

            _drops[id] = go;
        }

        void Despawn(string dropId)
        {
            if (!_drops.TryGetValue(dropId, out var go)) return;
            if (go != null) Destroy(go);
            _drops.Remove(dropId);
        }

        public void ClearAll()
        {
            foreach (var kv in _drops)
            {
                if (kv.Value != null) Destroy(kv.Value);
            }
            _drops.Clear();
        }

        static Color OreColor(string oreId) => oreId switch
        {
            "coal" => new Color(0.2f, 0.2f, 0.22f),
            "copper_ore" => new Color(0.75f, 0.45f, 0.25f),
            "iron_ore" => new Color(0.55f, 0.5f, 0.48f),
            "diamond_ore" => new Color(0.4f, 0.85f, 0.95f),
            _ => new Color(0.6f, 0.55f, 0.5f),
        };
    }
}
