using CPoW.Net;

namespace CPoW.Runtime
{
    /// <summary>Session state shared across API clients and streamers.</summary>
    public sealed class CpowSession
    {
        public string UserId { get; }
        public string AreaId { get; set; } = "";
        public AreasApiClient Areas { get; }
        public WorldApiClient World { get; }

        public CpowSession(string userId = null, string baseUrl = null)
        {
            UserId = string.IsNullOrEmpty(userId) ? CpowApiConfig.CreatorId : userId;
            Areas = new AreasApiClient(UserId, baseUrl);
            World = new WorldApiClient(baseUrl);
        }
    }
}
