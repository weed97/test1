using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using CPoW.Net;
using UnityEngine;

namespace CPoW.World
{
    /// <summary>
    /// Streams world cells around a follow target. Only AOI ring is resident in memory.
    /// </summary>
    public sealed class ChunkStreamer : MonoBehaviour
    {
        [SerializeField] int cellSize = 64;
        [SerializeField] int loadRadius = 3;
        [SerializeField] int unloadRadius = 4;
        [SerializeField] int maxConcurrentLoads = 4;
        [SerializeField] Transform followTarget;
        [SerializeField] float retargetInterval = 0.35f;

        WorldApiClient _worldApi;
        string _areaId = "";
        ChunkPool _pool;
        ChunkCoord _center;
        readonly Dictionary<ChunkCoord, ChunkCellSnapshot> _dataCache = new();
        readonly HashSet<ChunkCoord> _loading = new();
        float _nextRetarget;
        int _inflight;

        public int CellSize => cellSize;
        public ChunkPool Pool => _pool;

        public void Initialize(WorldApiClient worldApi, string areaId, Transform target = null)
        {
            _worldApi = worldApi;
            _areaId = areaId;
            if (target != null)
                followTarget = target;
            var maxChunks = (loadRadius * 2 + 1) * (loadRadius * 2 + 1);
            _pool = new ChunkPool(transform, cellSize, maxChunks);
        }

        void Update()
        {
            if (_worldApi == null || string.IsNullOrEmpty(_areaId) || followTarget == null || _pool == null)
                return;

            if (Time.time < _nextRetarget)
                return;
            _nextRetarget = Time.time + retargetInterval;

            var coord = ChunkCoord.FromWorld(followTarget.position.x, followTarget.position.z, cellSize);
            if (coord.Equals(_center) && _pool.ActiveCount > 0)
                return;
            _center = coord;
            ReconcileChunks();
        }

        void ReconcileChunks()
        {
            var wanted = new HashSet<ChunkCoord>();
            for (var dz = -loadRadius; dz <= loadRadius; dz++)
            for (var dx = -loadRadius; dx <= loadRadius; dx++)
                wanted.Add(new ChunkCoord(_center.X + dx, _center.Z + dz));

            var toUnload = new List<ChunkCoord>();
            foreach (var kv in _dataCache)
            {
                if (kv.Key.ChebyshevDistance(_center) > unloadRadius)
                    toUnload.Add(kv.Key);
            }
            foreach (var c in toUnload)
            {
                _dataCache.Remove(c);
                _pool.Release(c);
            }

            foreach (var c in wanted)
            {
                if (_pool.TryGet(c, out var view) && _dataCache.TryGetValue(c, out var snap))
                {
                    view.ApplySnapshot(snap, cellSize);
                    continue;
                }
                if (!_loading.Contains(c) && _inflight < maxConcurrentLoads)
                    _ = LoadChunkAsync(c);
            }
        }

        async Task LoadChunkAsync(ChunkCoord coord)
        {
            _loading.Add(coord);
            _inflight++;
            try
            {
                var wx = coord.WorldOriginX(cellSize) + cellSize * 0.5f;
                var wz = coord.WorldOriginZ(cellSize) + cellSize * 0.5f;
                var json = await _worldApi.InspectCellAsync(
                    _areaId, wx, wz, depthY: 48, cellSize: cellSize, advanceTick: false,
                    CancellationToken.None).ConfigureAwait(true);

                var snap = ChunkCellSnapshot.FromJson(json);
                _dataCache[coord] = snap;

                if (coord.ChebyshevDistance(_center) <= loadRadius)
                {
                    var view = _pool.Acquire(coord);
                    view.ApplySnapshot(snap, cellSize);
                }
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"[ChunkStreamer] load {coord} failed: {ex.Message}");
            }
            finally
            {
                _loading.Remove(coord);
                _inflight--;
            }
        }

        public bool TryGetData(ChunkCoord coord, out ChunkCellSnapshot snap) =>
            _dataCache.TryGetValue(coord, out snap);
    }
}
