using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace CPoW.Net
{
    /// <summary>HTTP bridge to /v1/areas/* — collaborative CPoW worlds.</summary>
    public sealed class AreasApiClient
    {
        readonly string _baseUrl;
        public string CurrentAreaId { get; private set; } = "";
        public string CurrentUserId { get; }

        public AreasApiClient(string userId, string baseUrl = null)
        {
            CurrentUserId = string.IsNullOrEmpty(userId) ? CpowApiConfig.CreatorId : userId;
            _baseUrl = string.IsNullOrEmpty(baseUrl) ? CpowApiConfig.BaseUrl : baseUrl.TrimEnd('/');
        }

        string Url(string path) => _baseUrl + path;

        public async Task<string> HealthCheckAsync(CancellationToken ct = default)
        {
            return await HttpJson.GetAsync(Url("/v1/health"), ct).ConfigureAwait(false);
        }

        public async Task<string> ListAreasAsync(CancellationToken ct = default)
        {
            return await HttpJson.GetAsync(Url("/v1/areas/list"), ct).ConfigureAwait(false);
        }

        public async Task<string> FoundAreaAsync(
            string label,
            string mode = "creation_adventure",
            string template = "",
            CancellationToken ct = default)
        {
            var sb = new StringBuilder(128);
            sb.Append("{\"founder_id\":\"").Append(Escape(CurrentUserId));
            sb.Append("\",\"label\":\"").Append(Escape(label));
            sb.Append("\",\"mode\":\"").Append(Escape(mode)).Append("\"");
            if (!string.IsNullOrEmpty(template))
                sb.Append(",\"template\":\"").Append(Escape(template)).Append("\"");
            sb.Append('}');
            var json = await HttpJson.PostAsync(Url("/v1/areas/found"), sb.ToString(), ct)
                .ConfigureAwait(false);
            CurrentAreaId = ExtractString(json, "area_id");
            return json;
        }

        public async Task<string> JoinAreaAsync(string areaId, string role = "", CancellationToken ct = default)
        {
            var sb = new StringBuilder(96);
            sb.Append("{\"area_id\":\"").Append(Escape(areaId));
            sb.Append("\",\"creator_id\":\"").Append(Escape(CurrentUserId)).Append("\"");
            if (!string.IsNullOrEmpty(role))
                sb.Append(",\"role\":\"").Append(Escape(role)).Append("\"");
            sb.Append('}');
            var json = await HttpJson.PostAsync(Url("/v1/areas/join"), sb.ToString(), ct)
                .ConfigureAwait(false);
            CurrentAreaId = areaId;
            return json;
        }

        public async Task<string> FetchStateAsync(string areaId = "", CancellationToken ct = default)
        {
            var aid = string.IsNullOrEmpty(areaId) ? CurrentAreaId : areaId;
            return await HttpJson.GetAsync(
                Url("/v1/areas/state?area_id=" + UnityEngine.Networking.UnityWebRequest.EscapeURL(aid)),
                ct).ConfigureAwait(false);
        }

        public async Task<string> CreateObjectAsync(string jsonBody, string areaId = "", CancellationToken ct = default)
        {
            var aid = string.IsNullOrEmpty(areaId) ? CurrentAreaId : areaId;
            if (!jsonBody.Contains("\"area_id\""))
            {
                jsonBody = InjectField(jsonBody, "area_id", aid);
            }
            if (!jsonBody.Contains("\"creator_id\""))
            {
                jsonBody = InjectField(jsonBody, "creator_id", CurrentUserId);
            }
            return await HttpJson.PostAsync(Url("/v1/areas/create"), jsonBody, ct).ConfigureAwait(false);
        }

        public async Task<string> AdventureMineAsync(
            float x, float z, int depthY,
            string toolType = "pickaxe", int toolTier = 1, string oreId = "coal",
            CancellationToken ct = default)
        {
            var sb = new StringBuilder(256);
            sb.Append("{\"area_id\":\"").Append(Escape(CurrentAreaId));
            sb.Append("\",\"actor_id\":\"").Append(Escape(CurrentUserId));
            sb.Append("\",\"action\":\"mine\",\"x\":").Append(x.ToString("F1"));
            sb.Append(",\"z\":").Append(z.ToString("F1"));
            sb.Append(",\"depth_y\":").Append(depthY);
            sb.Append(",\"tool_type\":\"").Append(Escape(toolType)).Append("\"");
            sb.Append(",\"tool_tier\":").Append(toolTier);
            sb.Append(",\"ore_id\":\"").Append(Escape(oreId)).Append("\"}");
            return await HttpJson.PostAsync(Url("/v1/areas/adventure"), sb.ToString(), ct)
                .ConfigureAwait(false);
        }

        static string InjectField(string json, string key, string value)
        {
            if (json.StartsWith("{"))
                return "{\"" + key + "\":\"" + Escape(value) + "\"," + json.Substring(1);
            return json;
        }

        static string Escape(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");

        static string ExtractString(string json, string key)
        {
            var needle = "\"" + key + "\":\"";
            var i = json.IndexOf(needle, System.StringComparison.Ordinal);
            if (i < 0) return "";
            i += needle.Length;
            var j = json.IndexOf('"', i);
            return j < 0 ? "" : json.Substring(i, j - i);
        }
    }
}
