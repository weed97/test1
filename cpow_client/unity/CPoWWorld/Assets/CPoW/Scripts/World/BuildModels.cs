using System;
using System.Collections.Generic;
using System.Globalization;
using CPoW.Net;

namespace CPoW.World
{
    public sealed class ModuleReq
    {
        public string ModuleId = "";
        public int Count;
    }

    public sealed class BlueprintDef
    {
        public string BlueprintId = "";
        public string Label = "";
        public string BuildingType = "";
        public string ZoneMin = "safe";
        public int CivMin;
        public readonly List<ModuleReq> Modules = new();
        public readonly List<ModuleReq> Materials = new();
    }

    /// <summary>GET /v1/world/catalog blueprints[] parser.</summary>
    public sealed class BlueprintCatalogCache
    {
        public readonly List<BlueprintDef> Blueprints = new();

        public static BlueprintCatalogCache Parse(string json)
        {
            var cache = new BlueprintCatalogCache();
            if (string.IsNullOrEmpty(json))
                return DefaultFallback(cache);

            var anchor = "\"blueprints\":[";
            var start = json.IndexOf(anchor, StringComparison.Ordinal);
            if (start < 0)
                return DefaultFallback(cache);
            start += anchor.Length - 1;
            var end = json.IndexOf(']', start + 1);
            if (end < 0)
                return DefaultFallback(cache);
            var slice = json.Substring(start, end - start + 1);

            var idx = 0;
            while (idx < slice.Length)
            {
                var bpKey = "\"blueprint_id\":\"";
                var i = slice.IndexOf(bpKey, idx, StringComparison.Ordinal);
                if (i < 0) break;
                var blockStart = slice.LastIndexOf('{', i);
                var blockEnd = FindMatchingBrace(slice, blockStart);
                if (blockStart < 0 || blockEnd < 0) break;
                var block = slice.Substring(blockStart, blockEnd - blockStart + 1);
                cache.Blueprints.Add(ParseBlueprintBlock(block));
                idx = blockEnd + 1;
            }
            return cache.Blueprints.Count > 0 ? cache : DefaultFallback(cache);
        }

        static BlueprintDef ParseBlueprintBlock(string block)
        {
            var bp = new BlueprintDef
            {
                BlueprintId = JsonField.GetString(block, "blueprint_id", ""),
                Label = JsonField.GetString(block, "label", ""),
                BuildingType = JsonField.GetString(block, "building_type", ""),
                ZoneMin = JsonField.GetString(block, "zone_min", "safe"),
                CivMin = JsonField.GetInt(block, "civ_min", 0),
            };
            ParseReqArray(block, "\"modules\":", bp.Modules);
            ParseReqArray(block, "\"materials\":", bp.Materials);
            return bp;
        }

        static void ParseReqArray(string block, string anchor, List<ModuleReq> dest)
        {
            var i = block.IndexOf(anchor, StringComparison.Ordinal);
            if (i < 0) return;
            i = block.IndexOf('[', i);
            if (i < 0) return;
            var j = block.IndexOf(']', i);
            if (j < 0) return;
            var slice = block.Substring(i, j - i + 1);
            var idx = 0;
            while (idx < slice.Length)
            {
                var key = "\"module_id\":\"";
                var k = slice.IndexOf(key, idx, StringComparison.Ordinal);
                if (k < 0) break;
                var subStart = slice.LastIndexOf('{', k);
                var subEnd = slice.IndexOf('}', k);
                if (subStart < 0 || subEnd < 0) break;
                var sub = slice.Substring(subStart, subEnd - subStart + 1);
                dest.Add(new ModuleReq
                {
                    ModuleId = JsonField.GetString(sub, "module_id", ""),
                    Count = JsonField.GetInt(sub, "count", 0),
                });
                idx = subEnd + 1;
            }
        }

        static int FindMatchingBrace(string s, int open)
        {
            if (open < 0 || open >= s.Length || s[open] != '{') return -1;
            var depth = 0;
            for (var i = open; i < s.Length; i++)
            {
                if (s[i] == '{') depth++;
                else if (s[i] == '}')
                {
                    depth--;
                    if (depth == 0) return i;
                }
            }
            return -1;
        }

        static BlueprintCatalogCache DefaultFallback(BlueprintCatalogCache cache)
        {
            var camp = new BlueprintDef
            {
                BlueprintId = "camp_kit",
                Label = "원정 캠프 키트",
                BuildingType = "outpost",
                ZoneMin = "danger",
            };
            camp.Modules.Add(new ModuleReq { ModuleId = "foundation_1x1", Count = 1 });
            camp.Modules.Add(new ModuleReq { ModuleId = "wall_t1", Count = 4 });
            camp.Modules.Add(new ModuleReq { ModuleId = "heater_core", Count = 1 });
            camp.Materials.Add(new ModuleReq { ModuleId = "wood_plank", Count = 8 });
            camp.Materials.Add(new ModuleReq { ModuleId = "stone_brick", Count = 4 });
            cache.Blueprints.Add(camp);
            return cache;
        }
    }

    public sealed class BuildMissingPart
    {
        public string Kind = "";
        public string ModuleId = "";
        public int Count;
        public int Have;
    }

    /// <summary>POST /v1/world/build/validate response.</summary>
    public sealed class BuildValidationResult
    {
        public bool Ok;
        public string Reason = "";
        public string BlueprintId = "";
        public string BlueprintLabel = "";
        public readonly List<BuildMissingPart> Missing = new();
        public string RawJson = "";

        public static BuildValidationResult FromJson(string json)
        {
            var r = new BuildValidationResult { RawJson = json ?? "", Ok = JsonField.IsOk(json) };
            r.Reason = JsonField.GetString(json, "reason", "");
            var bpSlice = SliceAfter(json, "\"blueprint\":");
            r.BlueprintId = JsonField.GetString(bpSlice, "blueprint_id", "");
            r.BlueprintLabel = JsonField.GetString(bpSlice, "label", "");
            ParseMissing(json, r.Missing);
            return r;
        }

        static void ParseMissing(string json, List<BuildMissingPart> dest)
        {
            if (string.IsNullOrEmpty(json)) return;
            var anchor = "\"missing\":[";
            var i = json.IndexOf(anchor, StringComparison.Ordinal);
            if (i < 0) return;
            i += anchor.Length - 1;
            var end = json.IndexOf(']', i + 1);
            if (end < 0) return;
            var slice = json.Substring(i, end - i + 1);
            var idx = 0;
            while (idx < slice.Length)
            {
                var k = slice.IndexOf("\"module_id\":\"", idx, StringComparison.Ordinal);
                if (k < 0) break;
                var subStart = slice.LastIndexOf('{', k);
                var subEnd = slice.IndexOf('}', k);
                if (subStart < 0 || subEnd < 0) break;
                var sub = slice.Substring(subStart, subEnd - subStart + 1);
                dest.Add(new BuildMissingPart
                {
                    Kind = JsonField.GetString(sub, "kind", ""),
                    ModuleId = JsonField.GetString(sub, "module_id", ""),
                    Count = JsonField.GetInt(sub, "count", 0),
                    Have = JsonField.GetInt(sub, "have", 0),
                });
                idx = subEnd + 1;
            }
        }

        static string SliceAfter(string json, string anchor)
        {
            if (string.IsNullOrEmpty(json)) return "";
            var i = json.IndexOf(anchor, StringComparison.Ordinal);
            return i < 0 ? "" : json.Substring(i);
        }
    }

    /// <summary>Ghost slot layout per blueprint (local XZ grid, 1m).</summary>
    public static class BuildLayout
    {
        public sealed class GhostSlot
        {
            public string ModuleId = "";
            public UnityEngine.Vector3 LocalPos;
            public UnityEngine.Vector3 Scale = UnityEngine.Vector3.one;
        }

        public static List<GhostSlot> SlotsFor(string blueprintId, IReadOnlyDictionary<string, int> placed)
        {
            var templates = TemplateSlots(blueprintId);
            var counts = new Dictionary<string, int>(placed);
            var outList = new List<GhostSlot>();
            foreach (var slot in templates)
            {
                if (!counts.TryGetValue(slot.ModuleId, out var left) || left <= 0)
                    continue;
                counts[slot.ModuleId] = left - 1;
                outList.Add(slot);
            }
            return outList;
        }

        static List<GhostSlot> TemplateSlots(string blueprintId)
        {
            if (blueprintId == "smelter_lv1")
                return SmelterSlots();
            if (blueprintId == "power_line")
                return PowerLineSlots();
            return CampKitSlots();
        }

        static List<GhostSlot> CampKitSlots()
        {
            return new List<GhostSlot>
            {
                Slot("foundation_1x1", 0f, 0.1f, 0f, 1f, 0.2f, 1f),
                Slot("wall_t1", 0f, 0.55f, 0.65f, 1f, 0.9f, 0.12f),
                Slot("wall_t1", 0f, 0.55f, -0.65f, 1f, 0.9f, 0.12f),
                Slot("wall_t1", 0.65f, 0.55f, 0f, 0.12f, 0.9f, 1f),
                Slot("wall_t1", -0.65f, 0.55f, 0f, 0.12f, 0.9f, 1f),
                Slot("heater_core", 0f, 0.45f, 0f, 0.35f, 0.35f, 0.35f),
            };
        }

        static List<GhostSlot> SmelterSlots()
        {
            return new List<GhostSlot>
            {
                Slot("foundation_2x2", 0f, 0.12f, 0f, 2f, 0.24f, 2f),
                Slot("wall_t1", 0f, 0.7f, 1.05f, 2f, 1.1f, 0.14f),
                Slot("wall_t1", 0f, 0.7f, -1.05f, 2f, 1.1f, 0.14f),
                Slot("wall_t1", 1.05f, 0.7f, 0f, 0.14f, 1.1f, 2f),
                Slot("wall_t1", -1.05f, 0.7f, 0f, 0.14f, 1.1f, 2f),
                Slot("wall_t1", 0.75f, 0.7f, 0.75f, 0.14f, 1.1f, 0.14f),
                Slot("wall_t1", -0.75f, 0.7f, 0.75f, 0.14f, 1.1f, 0.14f),
                Slot("wall_t1", 0.75f, 0.7f, -0.75f, 0.14f, 1.1f, 0.14f),
                Slot("wall_t1", -0.75f, 0.7f, -0.75f, 0.14f, 1.1f, 0.14f),
                Slot("furnace_box", 0.3f, 0.55f, 0.3f, 0.6f, 0.6f, 0.6f),
                Slot("chimney_stack", 0.3f, 1.2f, 0.3f, 0.25f, 1.4f, 0.25f),
            };
        }

        static List<GhostSlot> PowerLineSlots()
        {
            return new List<GhostSlot>
            {
                Slot("pipe_straight", -1.5f, 0.25f, 0f, 0.2f, 0.2f, 0.8f),
                Slot("pipe_straight", -0.5f, 0.25f, 0f, 0.2f, 0.2f, 0.8f),
                Slot("pipe_straight", 0.5f, 0.25f, 0f, 0.2f, 0.2f, 0.8f),
                Slot("pipe_straight", 1.5f, 0.25f, 0f, 0.2f, 0.2f, 0.8f),
                Slot("cable_segment", -1f, 0.55f, 0.4f, 0.08f, 0.08f, 1.2f),
                Slot("cable_segment", 1f, 0.55f, -0.4f, 0.08f, 0.08f, 1.2f),
            };
        }

        static GhostSlot Slot(string id, float x, float y, float z, float sx, float sy, float sz)
        {
            return new GhostSlot
            {
                ModuleId = id,
                LocalPos = new UnityEngine.Vector3(x, y, z),
                Scale = new UnityEngine.Vector3(sx, sy, sz),
            };
        }
    }
}
