using System;
using System.Collections.Generic;
using CPoW.Net;

namespace CPoW.World
{
    /// <summary>Parsed POST /v1/world/cell response.</summary>
    [Serializable]
    public sealed class CellInspectResult
    {
        public bool Ok;
        public string BiomeId = "plains";
        public string BiomeLabel = "";
        public string ZoneClass = "safe";
        public string OreId = "";
        public string OreLabel = "";
        public int OreTier;
        public int HazardDanger;
        public string AudioCue = "";
        public int AudioStage;
        public string PhaseId = "";
        public string RawJson = "";

        public bool HasOre => !string.IsNullOrEmpty(OreId);

        public static CellInspectResult FromJson(string json)
        {
            var r = new CellInspectResult { RawJson = json ?? "", Ok = JsonField.IsOk(json) };
            r.BiomeId = JsonField.GetStringAfter(json, "\"biome\":", "biome_id", r.BiomeId);
            r.BiomeLabel = JsonField.GetStringAfter(json, "\"biome\":", "label", r.BiomeId);
            r.ZoneClass = JsonField.GetStringAfter(json, "\"biome\":", "zone_class", r.ZoneClass);
            r.OreId = JsonField.GetStringAfter(json, "\"ore\":", "ore_id", "");
            r.OreLabel = JsonField.GetStringAfter(json, "\"ore\":", "label", r.OreId);
            r.OreTier = JsonField.GetInt(JsonFieldSlice(json, "\"ore\":"), "tier", 0);
            r.AudioCue = JsonField.GetStringAfter(json, "\"phase\":", "audio_cue", "");
            if (string.IsNullOrEmpty(r.AudioCue))
                r.AudioCue = JsonField.GetStringAfter(json, "\"hazard\":", "audio_cue", "");
            r.HazardDanger = JsonField.GetInt(JsonFieldSlice(json, "\"phase\":"), "danger_level", 0);
            r.AudioStage = JsonField.GetInt(JsonFieldSlice(json, "\"phase\":"), "audio_stage", 0);
            r.PhaseId = JsonField.GetStringAfter(json, "\"phase\":", "phase_id", "");
            return r;
        }

        static string JsonFieldSlice(string json, string anchor)
        {
            if (string.IsNullOrEmpty(json)) return "";
            var i = json.IndexOf(anchor, StringComparison.Ordinal);
            return i < 0 ? json : json.Substring(i);
        }
    }

    /// <summary>Parsed POST /v1/world/mine response.</summary>
    [Serializable]
    public sealed class MineResult
    {
        public bool Ok;
        public string Reason = "";
        public string OreId = "";
        public float Amount;
        public float MiningXp;
        public int MiningTier;
        public string ResourceLabel = "";
        public string AudioCue = "";
        public int AudioStage;
        public bool CreationOk;
        public string CreationObjectId = "";
        public string CreationReason = "";
        public string RawJson = "";

        public static MineResult FromJson(string json)
        {
            var r = new MineResult { RawJson = json ?? "", Ok = JsonField.IsOk(json) };
            r.Reason = JsonField.GetString(json, "reason", "");
            r.OreId = JsonField.GetString(json, "ore_id", "");
            r.Amount = JsonField.GetFloat(json, "amount", 0f);
            r.MiningXp = JsonField.GetFloat(JsonFieldSlice(json, "\"mining\":"), "xp", 0f);
            r.MiningTier = JsonField.GetInt(JsonFieldSlice(json, "\"mining\":"), "tier", 1);
            r.ResourceLabel = JsonField.GetStringAfter(json, "\"resource\":", "label", "");
            r.AudioCue = JsonField.GetStringAfter(json, "\"hazard_audio\":", "audio_cue", "");
            r.AudioStage = JsonField.GetInt(JsonFieldSlice(json, "\"hazard_audio\":"), "audio_stage", 0);
            var creationSlice = JsonFieldSlice(json, "\"creation\":");
            r.CreationOk = JsonField.IsOk(creationSlice);
            r.CreationObjectId = JsonField.GetString(json, "object_id", "");
            if (string.IsNullOrEmpty(r.CreationObjectId))
                r.CreationObjectId = JsonField.GetStringAfter(json, "\"creation\":", "object_id", "");
            r.CreationReason = JsonField.GetStringAfter(json, "\"creation\":", "reason", "");
            return r;
        }

        static string JsonFieldSlice(string json, string anchor)
        {
            if (string.IsNullOrEmpty(json)) return "";
            var i = json.IndexOf(anchor, StringComparison.Ordinal);
            return i < 0 ? "" : json.Substring(i);
        }
    }

    /// <summary>Ore/tool entries from GET /v1/world/catalog.</summary>
    public sealed class WorldCatalogCache
    {
        public readonly List<string> OreIds = new();
        public readonly List<string> OreLabels = new();

        public static WorldCatalogCache Parse(string json)
        {
            var cache = new WorldCatalogCache();
            if (string.IsNullOrEmpty(json))
                return DefaultFallback(cache);

            var idx = 0;
            while (idx < json.Length)
            {
                var oreKey = "\"ore_id\":\"";
                var i = json.IndexOf(oreKey, idx, StringComparison.Ordinal);
                if (i < 0) break;
                var blockStart = json.LastIndexOf('{', i);
                var blockEnd = json.IndexOf('}', i);
                if (blockStart < 0 || blockEnd < 0) break;
                var block = json.Substring(blockStart, blockEnd - blockStart + 1);
                var oreId = JsonField.GetString(block, "ore_id", "");
                var label = JsonField.GetString(block, "label", oreId);
                if (!string.IsNullOrEmpty(oreId) && !cache.OreIds.Contains(oreId))
                {
                    cache.OreIds.Add(oreId);
                    cache.OreLabels.Add(label);
                }
                idx = blockEnd + 1;
            }
            return cache.OreIds.Count > 0 ? cache : DefaultFallback(cache);
        }

        static WorldCatalogCache DefaultFallback(WorldCatalogCache cache)
        {
            cache.OreIds.AddRange(new[] { "coal", "copper_ore", "iron_ore", "diamond_ore" });
            cache.OreLabels.AddRange(new[] { "석탄", "구리 광석", "철 광석", "다이아" });
            return cache;
        }
    }
}
