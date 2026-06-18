using System;
using UnityEngine;

namespace CPoW.Net
{
    /// <summary>API base URL and default actor id (env CPOW_API_URL / CPOW_CREATOR_ID).</summary>
    public static class CpowApiConfig
    {
        public const string DefaultBaseUrl = "http://127.0.0.1:8765";
        public const string DefaultCreatorId = "cpow_player";

        public static string BaseUrl
        {
            get
            {
                var env = Environment.GetEnvironmentVariable("CPOW_API_URL");
                if (!string.IsNullOrWhiteSpace(env))
                    return env.TrimEnd('/');
                return PlayerPrefs.GetString("cpow_api_url", DefaultBaseUrl).TrimEnd('/');
            }
            set => PlayerPrefs.SetString("cpow_api_url", value.TrimEnd('/'));
        }

        public static string CreatorId
        {
            get
            {
                var env = Environment.GetEnvironmentVariable("CPOW_CREATOR_ID");
                if (!string.IsNullOrWhiteSpace(env))
                    return env;
                return PlayerPrefs.GetString("cpow_creator_id", DefaultCreatorId);
            }
            set => PlayerPrefs.SetString("cpow_creator_id", value);
        }
    }
}
