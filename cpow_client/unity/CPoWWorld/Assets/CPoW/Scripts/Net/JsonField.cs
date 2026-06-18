using System;

namespace CPoW.Net
{
    /// <summary>Lightweight JSON field helpers (API responses).</summary>
    public static class JsonField
    {
        public static bool IsOk(string json) =>
            json != null && json.Contains("\"ok\":true");

        public static string GetString(string json, string key, string fallback = "")
        {
            if (string.IsNullOrEmpty(json)) return fallback;
            var needle = "\"" + key + "\":\"";
            var i = json.IndexOf(needle, StringComparison.Ordinal);
            if (i < 0) return fallback;
            i += needle.Length;
            var j = json.IndexOf('"', i);
            return j < 0 ? fallback : json.Substring(i, j - i);
        }

        public static float GetFloat(string json, string key, float fallback = 0f)
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

        public static int GetInt(string json, string key, int fallback = 0)
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

        /// <summary>First match of key after a section anchor (e.g. nested ore).</summary>
        public static string GetStringAfter(string json, string anchor, string key, string fallback = "")
        {
            if (string.IsNullOrEmpty(json)) return fallback;
            var start = json.IndexOf(anchor, StringComparison.Ordinal);
            if (start < 0) return GetString(json, key, fallback);
            return GetString(json.Substring(start), key, fallback);
        }
    }
}
