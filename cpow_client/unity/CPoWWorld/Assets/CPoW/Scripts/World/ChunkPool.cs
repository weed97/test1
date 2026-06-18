using System.Collections.Generic;
using UnityEngine;

namespace CPoW.World
{
    /// <summary>
    /// Reuses chunk GameObjects and enforces a hard memory cap via LRU eviction.
    /// Data snapshots live outside views — only meshes are pooled here.
    /// </summary>
    public sealed class ChunkPool
    {
        readonly Transform _root;
        readonly int _cellSize;
        readonly int _maxLoaded;
        readonly Dictionary<ChunkCoord, BiomeChunkView> _active = new();
        readonly LinkedList<ChunkCoord> _lru = new();
        readonly Stack<BiomeChunkView> _free = new();

        public int ActiveCount => _active.Count;
        public int MaxLoaded => _maxLoaded;

        public ChunkPool(Transform root, int cellSize, int maxLoaded)
        {
            _root = root;
            _cellSize = Mathf.Max(1, cellSize);
            _maxLoaded = Mathf.Max(1, maxLoaded);
        }

        public bool TryGet(ChunkCoord coord, out BiomeChunkView view) => _active.TryGetValue(coord, out view);

        public BiomeChunkView Acquire(ChunkCoord coord)
        {
            if (_active.TryGetValue(coord, out var existing))
            {
                TouchLru(coord);
                return existing;
            }

            while (_active.Count >= _maxLoaded && _lru.Last != null)
            {
                var evict = _lru.Last.Value;
                Release(evict);
            }

            var view = _free.Count > 0 ? _free.Pop() : CreateView();
            var origin = new Vector3(coord.WorldOriginX(_cellSize), 0f, coord.WorldOriginZ(_cellSize));
            view.Activate(coord, _cellSize, origin);
            _active[coord] = view;
            TouchLru(coord);
            return view;
        }

        public void Release(ChunkCoord coord)
        {
            if (!_active.TryGetValue(coord, out var view))
                return;
            _active.Remove(coord);
            RemoveLru(coord);
            view.Release();
            _free.Push(view);
        }

        BiomeChunkView CreateView()
        {
            var go = new GameObject("Chunk");
            go.transform.SetParent(_root, false);
            var view = go.AddComponent<BiomeChunkView>();
            go.SetActive(false);
            return view;
        }

        void TouchLru(ChunkCoord coord)
        {
            RemoveLru(coord);
            _lru.AddFirst(coord);
        }

        void RemoveLru(ChunkCoord coord)
        {
            var node = _lru.Find(coord);
            if (node != null)
                _lru.Remove(node);
        }
    }
}
