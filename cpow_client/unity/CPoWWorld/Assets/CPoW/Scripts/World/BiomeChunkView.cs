using UnityEngine;

namespace CPoW.World
{
    /// <summary>Visual layer for one streamed cell — pooled mesh + hazard marker.</summary>
    public sealed class BiomeChunkView : MonoBehaviour
    {
        MeshRenderer _ground;
        MeshRenderer _hazardRing;
        TextMesh _label;

        public ChunkCoord Coord { get; private set; }
        public bool InUse { get; private set; }

        public void BuildIfNeeded(int cellSize)
        {
            if (_ground != null) return;

            var groundGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
            groundGo.name = "Ground";
            groundGo.transform.SetParent(transform, false);
            groundGo.transform.localScale = new Vector3(cellSize * 0.98f, 0.4f, cellSize * 0.98f);
            groundGo.transform.localPosition = new Vector3(cellSize * 0.5f, -0.2f, cellSize * 0.5f);
            _ground = groundGo.GetComponent<MeshRenderer>();
            Destroy(groundGo.GetComponent<Collider>());

            var ringGo = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            ringGo.name = "Hazard";
            ringGo.transform.SetParent(transform, false);
            ringGo.transform.localScale = new Vector3(cellSize * 0.35f, 0.05f, cellSize * 0.35f);
            ringGo.transform.localPosition = new Vector3(cellSize * 0.5f, 0.05f, cellSize * 0.5f);
            _hazardRing = ringGo.GetComponent<MeshRenderer>();
            Destroy(ringGo.GetComponent<Collider>());
            _hazardRing.enabled = false;

            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(transform, false);
            labelGo.transform.localPosition = new Vector3(cellSize * 0.5f, 1.2f, cellSize * 0.5f);
            _label = labelGo.AddComponent<TextMesh>();
            _label.fontSize = 24;
            _label.characterSize = 0.08f;
            _label.anchor = TextAnchor.MiddleCenter;
            _label.color = Color.white;
        }

        public void Activate(ChunkCoord coord, int cellSize, Vector3 worldOrigin)
        {
            Coord = coord;
            InUse = true;
            BuildIfNeeded(cellSize);
            transform.position = worldOrigin;
            gameObject.SetActive(true);
        }

        public void ApplySnapshot(ChunkCellSnapshot snap, int cellSize)
        {
            BuildIfNeeded(cellSize);
            var groundMat = _ground.material;
            groundMat.color = BiomePalette.ColorFor(snap.BiomeId, snap.ZoneClass);

            var hazardColor = BiomePalette.HazardAccent(snap.HazardDanger, snap.AudioStage);
            _hazardRing.enabled = hazardColor.a > 0.01f || snap.HazardDanger > 0;
            if (_hazardRing.enabled)
            {
                _hazardRing.material.color = hazardColor == Color.clear
                    ? new Color(1f, 0.4f, 0.1f, 0.6f)
                    : hazardColor;
            }

            _label.text = string.IsNullOrEmpty(snap.OreHint)
                ? snap.BiomeId
                : $"{snap.BiomeId}\n{snap.OreHint}";
        }

        public void Release()
        {
            InUse = false;
            gameObject.SetActive(false);
        }
    }
}
