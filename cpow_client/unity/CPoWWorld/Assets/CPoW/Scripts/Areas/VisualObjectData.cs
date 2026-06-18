namespace CPoW.Areas
{
    /// <summary>Minimal visual metadata parsed from CreativeObject JSON.</summary>
    public sealed class VisualObjectData
    {
        public string ObjectId = "";
        public string Label = "";
        public string GlbUrl = "";
        public string Slot = "world_prop";
        public string AttachBone = "";

        public bool HasGlb => !string.IsNullOrEmpty(GlbUrl);

        public static VisualObjectData FromJsonSlice(string objectId, string json)
        {
            var v = new VisualObjectData { ObjectId = objectId };
            if (string.IsNullOrEmpty(json)) return v;
            v.Label = Extract(json, "label");
            v.GlbUrl = Extract(json, "glb_url");
            if (string.IsNullOrEmpty(v.GlbUrl))
                v.GlbUrl = ExtractUnit(json, "visual_glb_url");
            v.Slot = Extract(json, "slot");
            if (string.IsNullOrEmpty(v.Slot))
                v.Slot = ExtractUnit(json, "visual_slot");
            if (string.IsNullOrEmpty(v.Slot))
                v.Slot = "world_prop";
            v.AttachBone = Extract(json, "attach_bone");
            return v;
        }

        static string Extract(string json, string key)
        {
            var needle = "\"" + key + "\":\"";
            var i = json.IndexOf(needle, System.StringComparison.Ordinal);
            if (i < 0) return "";
            i += needle.Length;
            var j = json.IndexOf('"', i);
            return j < 0 ? "" : json.Substring(i, j - i);
        }

        static string ExtractUnit(string json, string propName)
        {
            var needle = "\"name\":\"" + propName + "\"";
            var i = json.IndexOf(needle, System.StringComparison.Ordinal);
            if (i < 0) return "";
            var unitNeedle = "\"unit\":\"";
            i = json.IndexOf(unitNeedle, i, System.StringComparison.Ordinal);
            if (i < 0) return "";
            i += unitNeedle.Length;
            var j = json.IndexOf('"', i);
            return j < 0 ? "" : json.Substring(i, j - i);
        }
    }
}
