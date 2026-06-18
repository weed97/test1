using System.Collections.Generic;
using UnityEngine;

namespace CPoW.Areas
{
    /// <summary>Renders CreativeObjects from /v1/areas/state as 3D placeholders.</summary>
    public sealed class AreaObjectRenderer : MonoBehaviour
    {
        const float GridSpacing = 1.4f;

        readonly Dictionary<string, Transform> _nodes = new();

        public void ClearAll()
        {
            foreach (var kv in _nodes)
            {
                if (kv.Value != null)
                    Destroy(kv.Value.gameObject);
            }
            _nodes.Clear();
        }

        public void SyncFromStateJson(string stateJson)
        {
            if (string.IsNullOrEmpty(stateJson) || !stateJson.Contains("\"objects\""))
                return;

            var seen = new HashSet<string>();
            var index = 0;
            foreach (var pair in ParseObjectEntries(stateJson))
            {
                seen.Add(pair.id);
                if (!_nodes.TryGetValue(pair.id, out var node) || node == null)
                {
                    node = SpawnNode(pair.id, pair.json, index).transform;
                    _nodes[pair.id] = node;
                }
                else
                {
                    node.localPosition = GridPosition(index);
                    UpdateLabel(node, pair.json);
                }
                index++;
            }

            var stale = new List<string>();
            foreach (var id in _nodes.Keys)
            {
                if (!seen.Contains(id))
                    stale.Add(id);
            }
            foreach (var id in stale)
            {
                if (_nodes[id] != null)
                    Destroy(_nodes[id].gameObject);
                _nodes.Remove(id);
            }
        }

        static IEnumerable<(string id, string json)> ParseObjectEntries(string json)
        {
            var objectsIdx = json.IndexOf("\"objects\":", System.StringComparison.Ordinal);
            if (objectsIdx < 0) yield break;
            var i = objectsIdx;
            while (true)
            {
                var idNeedle = "\"";
                var idStart = json.IndexOf(idNeedle, i + 10, System.StringComparison.Ordinal);
                if (idStart < 0) yield break;
                idStart++;
                var idEnd = json.IndexOf('"', idStart);
                if (idEnd < 0) yield break;
                var id = json.Substring(idStart, idEnd - idStart);
                if (id == "objects") { i = idEnd; continue; }

                var brace = json.IndexOf('{', idEnd);
                if (brace < 0) yield break;
                var depth = 0;
                var end = brace;
                for (; end < json.Length; end++)
                {
                    if (json[end] == '{') depth++;
                    else if (json[end] == '}')
                    {
                        depth--;
                        if (depth == 0) break;
                    }
                }
                if (depth != 0) yield break;
                var slice = json.Substring(brace, end - brace + 1);
                yield return (id, slice);
                i = end;
                if (json.IndexOf("}", i + 1, System.StringComparison.Ordinal) < 0)
                    break;
            }
        }

        GameObject SpawnNode(string objectId, string json, int index)
        {
            var visual = VisualObjectData.FromJsonSlice(objectId, json);
            var go = new GameObject("Obj_" + objectId);
            go.transform.SetParent(transform, false);
            go.transform.localPosition = GridPosition(index);

            var sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere.name = "Visual";
            sphere.transform.SetParent(go.transform, false);
            sphere.transform.localScale = Vector3.one * 0.35f;
            var renderer = sphere.GetComponent<Renderer>();
            renderer.material.color = ColorForSlot(visual.Slot);

            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(go.transform, false);
            labelGo.transform.localPosition = new Vector3(0f, 0.55f, 0f);
            var label = labelGo.AddComponent<TextMesh>();
            label.text = string.IsNullOrEmpty(visual.Label) ? objectId.Substring(0, System.Math.Min(6, objectId.Length)) : visual.Label;
            label.fontSize = 24;
            label.characterSize = 0.08f;
            label.anchor = TextAnchor.MiddleCenter;
            label.color = Color.white;
            return go;
        }

        static void UpdateLabel(Transform node, string json)
        {
            var label = node.Find("Label");
            if (label == null) return;
            var tm = label.GetComponent<TextMesh>();
            if (tm == null) return;
            var visual = VisualObjectData.FromJsonSlice("", json);
            if (!string.IsNullOrEmpty(visual.Label))
                tm.text = visual.Label;
        }

        static Vector3 GridPosition(int index)
        {
            const int cols = 6;
            var row = index / cols;
            var col = index % cols;
            return new Vector3(col * GridSpacing, 0f, row * GridSpacing);
        }

        static Color ColorForSlot(string slot) => slot switch
        {
            "weapon" => new Color(0.85f, 0.2f, 0.2f),
            "movement" => new Color(0.2f, 0.6f, 0.95f),
            "accessory" => new Color(0.9f, 0.75f, 0.2f),
            "avatar" => new Color(0.6f, 0.85f, 0.5f),
            _ => new Color(0.55f, 0.58f, 0.62f),
        };
    }
}
