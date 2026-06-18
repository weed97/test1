using UnityEngine;

namespace CPoW.World
{
    /// <summary>Placeholder biome colors until terrain assets stream in.</summary>
    public static class BiomePalette
    {
        public static Color ColorFor(string biomeId, string zoneClass)
        {
            var baseColor = biomeId switch
            {
                "forest" => new Color(0.18f, 0.42f, 0.22f),
                "desert" => new Color(0.82f, 0.72f, 0.45f),
                "tundra" => new Color(0.75f, 0.82f, 0.88f),
                "volcano" => new Color(0.35f, 0.12f, 0.10f),
                "ocean" => new Color(0.12f, 0.28f, 0.55f),
                "swamp" => new Color(0.22f, 0.32f, 0.20f),
                "hills" => new Color(0.38f, 0.48f, 0.30f),
                "mine" => new Color(0.28f, 0.26f, 0.30f),
                "rift" => new Color(0.20f, 0.10f, 0.28f),
                "crystal_cavern" => new Color(0.45f, 0.30f, 0.65f),
                _ => new Color(0.42f, 0.55f, 0.35f),
            };
            if (zoneClass == "danger")
                return Color.Lerp(baseColor, new Color(0.55f, 0.12f, 0.10f), 0.35f);
            if (zoneClass == "buffer")
                return Color.Lerp(baseColor, Color.gray, 0.15f);
            return baseColor;
        }

        public static Color HazardAccent(int danger, int audioStage)
        {
            if (danger <= 0 && audioStage <= 0)
                return Color.clear;
            var t = Mathf.Clamp01(danger / 3f + audioStage * 0.2f);
            return Color.Lerp(new Color(1f, 0.65f, 0.1f), new Color(1f, 0.15f, 0.1f), t);
        }
    }
}
