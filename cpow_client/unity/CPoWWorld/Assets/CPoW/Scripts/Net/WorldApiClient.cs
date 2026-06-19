using System;
using System.Globalization;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace CPoW.Net
{
    /// <summary>HTTP bridge to /v1/world/* — biomes, mining, modular building.</summary>
    public sealed class WorldApiClient
    {
        readonly string _baseUrl;

        public WorldApiClient(string baseUrl = null)
        {
            _baseUrl = string.IsNullOrEmpty(baseUrl) ? CpowApiConfig.BaseUrl : baseUrl.TrimEnd('/');
        }

        string Url(string path) => _baseUrl + path;

        public Task<string> GetCatalogAsync(CancellationToken ct = default)
            => HttpJson.GetAsync(Url("/v1/world/catalog"), ct);

        public Task<string> InspectCellAsync(
            string areaId,
            float x, float z,
            int depthY = 48,
            int cellSize = 64,
            bool advanceTick = false,
            CancellationToken ct = default)
        {
            var sb = new StringBuilder(192);
            sb.Append("{\"area_id\":\"").Append(Escape(areaId));
            sb.Append("\",\"x\":").Append(x.ToString("F1", CultureInfo.InvariantCulture));
            sb.Append(",\"z\":").Append(z.ToString("F1", CultureInfo.InvariantCulture));
            sb.Append(",\"depth_y\":").Append(depthY);
            sb.Append(",\"cell_size\":").Append(cellSize);
            sb.Append(",\"advance_tick\":").Append(advanceTick ? "true" : "false");
            sb.Append('}');
            return HttpJson.PostAsync(Url("/v1/world/cell"), sb.ToString(), ct);
        }

        public Task<string> MineAsync(
            string areaId, string actorId,
            float x, float z, int depthY,
            string toolType, int toolTier, string oreId,
            string consumable = "",
            CancellationToken ct = default)
        {
            var sb = new StringBuilder(320);
            sb.Append("{\"area_id\":\"").Append(Escape(areaId));
            sb.Append("\",\"actor_id\":\"").Append(Escape(actorId));
            sb.Append("\",\"x\":").Append(x.ToString("F1", CultureInfo.InvariantCulture));
            sb.Append(",\"z\":").Append(z.ToString("F1", CultureInfo.InvariantCulture));
            sb.Append(",\"depth_y\":").Append(depthY);
            sb.Append(",\"tool_type\":\"").Append(Escape(toolType)).Append("\"");
            sb.Append(",\"tool_tier\":").Append(toolTier);
            sb.Append(",\"ore_id\":\"").Append(Escape(oreId)).Append("\"");
            if (!string.IsNullOrEmpty(consumable))
                sb.Append(",\"consumable\":\"").Append(Escape(consumable)).Append("\"");
            sb.Append('}');
            return HttpJson.PostAsync(Url("/v1/world/mine"), sb.ToString(), ct);
        }

        public Task<string> ValidateBuildAsync(string jsonBody, CancellationToken ct = default)
            => HttpJson.PostAsync(Url("/v1/world/build/validate"), jsonBody, ct);

        public Task<string> ValidateBuildAsync(
            string areaId,
            string biomeId,
            string blueprintId,
            System.Collections.Generic.IReadOnlyDictionary<string, int> placedModules,
            System.Collections.Generic.IReadOnlyDictionary<string, int> placedMaterials,
            int civilizationLevel = 0,
            CancellationToken ct = default)
        {
            var sb = new StringBuilder(512);
            sb.Append("{\"area_id\":\"").Append(Escape(areaId));
            sb.Append("\",\"biome_id\":\"").Append(Escape(biomeId));
            sb.Append("\",\"blueprint_id\":\"").Append(Escape(blueprintId)).Append('"');
            sb.Append(",\"civilization_level\":").Append(civilizationLevel);
            sb.Append(",\"placed_modules\":").Append(DictJson(placedModules));
            sb.Append(",\"placed_materials\":").Append(DictJson(placedMaterials));
            sb.Append('}');
            return HttpJson.PostAsync(Url("/v1/world/build/validate"), sb.ToString(), ct);
        }

        static string DictJson(System.Collections.Generic.IReadOnlyDictionary<string, int> dict)
        {
            var sb = new StringBuilder(128);
            sb.Append('{');
            var first = true;
            if (dict != null)
            {
                foreach (var kv in dict)
                {
                    if (!first) sb.Append(',');
                    first = false;
                    sb.Append('"').Append(Escape(kv.Key)).Append("\":").Append(kv.Value);
                }
            }
            sb.Append('}');
            return sb.ToString();
        }

        public Task<string> BossLootAsync(
            string areaId, string actorId, float amount = 1f,
            CancellationToken ct = default)
        {
            var sb = new StringBuilder(128);
            sb.Append("{\"area_id\":\"").Append(Escape(areaId));
            sb.Append("\",\"actor_id\":\"").Append(Escape(actorId));
            sb.Append("\",\"amount\":").Append(amount.ToString("F1", CultureInfo.InvariantCulture));
            sb.Append('}');
            return HttpJson.PostAsync(Url("/v1/world/boss_loot"), sb.ToString(), ct);
        }

        public Task<string> GetInventoryAsync(string areaId, string actorId, CancellationToken ct = default)
            => HttpJson.GetAsync(
                Url("/v1/world/inventory?area_id=" + Uri.EscapeDataString(areaId)
                    + "&actor_id=" + Uri.EscapeDataString(actorId)),
                ct);

        static string Escape(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}
