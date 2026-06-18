using System;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace CPoW.Net
{
    /// <summary>Thin HTTP JSON helper for cpow_api.</summary>
    public static class HttpJson
    {
        static readonly HttpClient Client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };

        public static async Task<string> GetAsync(string url, CancellationToken ct = default)
        {
            using var response = await Client.GetAsync(url, ct).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        }

        public static async Task<string> PostAsync(string url, string jsonBody, CancellationToken ct = default)
        {
            using var content = new StringContent(jsonBody, Encoding.UTF8, "application/json");
            using var response = await Client.PostAsync(url, content, ct).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        }
    }
}
