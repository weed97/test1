using System;

namespace CPoW.World
{
    /// <summary>Integer chunk coordinate in cell space.</summary>
    [Serializable]
    public readonly struct ChunkCoord : IEquatable<ChunkCoord>
    {
        public readonly int X;
        public readonly int Z;

        public ChunkCoord(int x, int z)
        {
            X = x;
            Z = z;
        }

        public static ChunkCoord FromWorld(float worldX, float worldZ, int cellSize)
        {
            var size = Math.Max(1, cellSize);
            return new ChunkCoord(
                FloorDiv(worldX, size),
                FloorDiv(worldZ, size));
        }

        static int FloorDiv(float v, int size)
        {
            var i = (int)Math.Floor(v / size);
            return i;
        }

        public float WorldOriginX(int cellSize) => X * cellSize;
        public float WorldOriginZ(int cellSize) => Z * cellSize;

        public int ChebyshevDistance(ChunkCoord other)
        {
            return Math.Max(Math.Abs(X - other.X), Math.Abs(Z - other.Z));
        }

        public bool Equals(ChunkCoord other) => X == other.X && Z == other.Z;
        public override bool Equals(object obj) => obj is ChunkCoord c && Equals(c);
        public override int GetHashCode() => HashCode.Combine(X, Z);
        public override string ToString() => $"({X},{Z})";
    }
}
