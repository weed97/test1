using System;
using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using CPoW.Net;
using UnityEngine;

namespace CPoW.Net
{
    /// <summary>WebSocket /v1/world/stream — AOI inventory & drop deltas.</summary>
    public sealed class WorldStreamClient : MonoBehaviour
    {
        readonly ConcurrentQueue<string> _inbox = new();
        ClientWebSocket _socket;
        CancellationTokenSource _cts;
        string _connectionId = "";

        public event Action<string> MessageReceived;

        public async Task ConnectAsync(
            string areaId,
            string actorId,
            float x,
            float z,
            float radiusM = 128f)
        {
            await DisconnectAsync();
            _cts = new CancellationTokenSource();
            _socket = new ClientWebSocket();
            var uri = new Uri(CpowApiConfig.BaseUrl.Replace("http://", "ws://").Replace("https://", "wss://") + "/v1/world/stream");
            await _socket.ConnectAsync(uri, _cts.Token);
            var sub = $"{{\"type\":\"subscribe\",\"area_id\":\"{areaId}\",\"actor_id\":\"{actorId}\",\"x\":{x:F1},\"z\":{z:F1},\"radius_m\":{radiusM:F0}}}";
            var bytes = Encoding.UTF8.GetBytes(sub);
            await _socket.SendAsync(bytes, WebSocketMessageType.Text, true, _cts.Token);
            _ = Task.Run(ReceiveLoop);
        }

        async Task ReceiveLoop()
        {
            var buffer = new byte[8192];
            while (_socket != null && _socket.State == WebSocketState.Open && !_cts.IsCancellationRequested)
            {
                try
                {
                    var seg = new ArraySegment<byte>(buffer);
                    var result = await _socket.ReceiveAsync(seg, _cts.Token);
                    if (result.MessageType == WebSocketMessageType.Close)
                        break;
                    var text = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    _inbox.Enqueue(text);
                }
                catch
                {
                    break;
                }
            }
        }

        public async Task SendPoseAsync(float x, float z)
        {
            if (_socket == null || _socket.State != WebSocketState.Open)
                return;
            var json = $"{{\"type\":\"pose\",\"x\":{x:F1},\"z\":{z:F1}}}";
            var bytes = Encoding.UTF8.GetBytes(json);
            await _socket.SendAsync(bytes, WebSocketMessageType.Text, true, _cts.Token);
        }

        void Update()
        {
            while (_inbox.TryDequeue(out var text))
            {
                if (text.Contains("\"type\":\"subscribed\""))
                    _connectionId = JsonField.GetString(text, "connection_id", "");
                MessageReceived?.Invoke(text);
            }
        }

        public async Task DisconnectAsync()
        {
            if (_cts != null)
            {
                _cts.Cancel();
                _cts = null;
            }
            if (_socket != null)
            {
                try
                {
                    if (_socket.State == WebSocketState.Open)
                        await _socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "bye", CancellationToken.None);
                }
                catch { /* ignore */ }
                _socket.Dispose();
                _socket = null;
            }
        }

        void OnDestroy() => _ = DisconnectAsync();
    }
}
