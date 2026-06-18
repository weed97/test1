using System;

namespace CPoW.World
{
    /// <summary>Parsed subset of POST /v1/world/cell response (data layer only).</summary>
    [Serializable]
    public sealed class ChunkCellSnapshot
    {
        public bool Ok;
        public string BiomeId = "plains";
        public string ZoneClass = "safe";
        public int HazardDanger;
        public string AudioCue = "";
        public int AudioStage;
        public float SecondsToEvent;
        public string OreHint = "";
        public string RawJson = "";

        public static ChunkCellSnapshot FromJson(string json)
        {
            var snap = new ChunkCellSnapshot { RawJson = json ?? "", Ok = json != null && json.Contains("\"ok\":true") };
            snap.BiomeId = Extract(json, "biome_id", snap.BiomeId);
            snap.ZoneClass = Extract(json, "zone_class", snap.ZoneClass);
            snap.OreHint = Extract(json, "ore_id", "");
            snap.AudioCue = ExtractNested(json, "audio_cue");
            snap.HazardDanger = ExtractInt(json, "danger", 0);
            snap.AudioStage = ExtractInt(json, "audio_stage", 0);
            snap.SecondsToEvent = ExtractFloat(json, "seconds_to_event", 0f);
            return snap;
        }

        static string Extract(string json, string key, string fallback)
        {
            if (string.IsNullOrEmpty(json)) return fallback;
            var needle = "\"" + key + "\":\"";
            var i = json.IndexOf(needle, StringComparison.Ordinal);
            if (i < 0) return fallback;
            i += needle.Length;
            var j = json.IndexOf('"', i);
            return j < 0 ? fallback : json.Substring(i, j - i);
        }

        static string ExtractNested(string json, string key)
        {
            if (string.IsNullOrEmpty(json)) return "";
            var needle = "\"" + key + "\":\"";
            var i = json.LastIndexOf(needle, StringComparison.Ordinal);
            if (i < 0) return "";
            i += needle.Length;
            var j = json.IndexOf('"', i);
            return j < 0 ? "" : json.Substring(i, j - i);
        }

        static int ExtractInt(string json, string key, int fallback)
        {
            if (string.IsNullOrEmpty(json)) return fallback;
            var needle = "\"" + key + "\":";
            var i = json.IndexOf(needle, StringComparison.Ordinal);
            if (i < 0) return fallback;
            i += needle.Length;
            var end = i;
            while (end < json.Length && (char.IsDigit(json[end]) || json[end] == '-'))
                end++;
            return int.TryParse(json.Substring(i, end - i), out var v) ? v : fallback;
        }

        static float ExtractFloat(string json, string key, float fallback)
        {
            if (string.IsNullOrEmpty(json)) return fallback;
            var needle = "\"" + key + "\":";
            var i = json.IndexOf(needle, StringComparison.Ordinal);
            if (i < 0) return fallback;
            i += needle.Length;
            var end = i;
            while (end < json.Length && (char.IsDigit(json[end]) || json[end] == '-' || json[end] == '.'))
                end++;
            return float.TryParse(
                json.Substring(i, end - i),
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                out var v) ? v : fallback;
        }
    }
}
