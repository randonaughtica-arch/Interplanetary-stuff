package com.randonaughtica.interplanetary.client.render;

import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.body.SkyProfile;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.client.render.DimensionEffects;
import net.minecraft.util.math.Vec3d;
import org.jetbrains.annotations.Nullable;

/** Fog and lighting behaviour of a space world. The sky itself is drawn by {@link SpaceSkyRenderer}. */
@Environment(EnvType.CLIENT)
public class SpaceDimensionEffects extends DimensionEffects {
    private final CelestialBody body;

    public SpaceDimensionEffects(CelestialBody body) {
        super(Float.NaN, true, SkyType.NONE, false, false);
        this.body = body;
    }

    @Override
    public Vec3d adjustFogColor(Vec3d color, float sunHeight) {
        SkyProfile sky = body.sky();
        if (!sky.hasAtmosphere()) {
            // Vacuum: the horizon fades into black space.
            return Vec3d.ZERO;
        }
        float light = Math.max(0.04F, sunHeight * 0.94F + 0.06F);
        return color.multiply(light, light, light * 0.97F + 0.03F);
    }

    @Override
    public boolean useThickFog(int camX, int camY) {
        return body.thickFog();
    }

    @Nullable
    @Override
    public float[] getFogColorOverride(float skyAngle, float tickDelta) {
        return null;
    }
}
