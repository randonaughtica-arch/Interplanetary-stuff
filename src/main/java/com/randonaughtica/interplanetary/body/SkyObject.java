package com.randonaughtica.interplanetary.body;

import net.minecraft.util.Identifier;
import org.jetbrains.annotations.Nullable;

/**
 * Something hanging in a world's sky: a parent planet, a sibling moon, ...
 *
 * @param texture          sphere texture (transparent outside of the disc)
 * @param size             half-size of the billboard at a sky distance of 100
 * @param azimuth          degrees clockwise from north (fixed objects)
 * @param elevation        degrees above the horizon (fixed objects)
 * @param orbitPeriod      ticks per orbit; 0 = fixed in the sky (tidally locked parent), negative = retrograde
 * @param orbitInclination degrees the orbit arc is tilted towards the south
 * @param orbitPhase       0..1 starting offset of the orbit
 * @param phases           whether the object shows phases (lit by the sun)
 * @param ring             optional ring system
 */
public record SkyObject(Identifier texture, float size, float azimuth, float elevation, float orbitPeriod,
                        float orbitInclination, float orbitPhase, boolean phases, @Nullable Ring ring) {

    public static SkyObject fixed(Identifier texture, float size, float azimuth, float elevation) {
        return new SkyObject(texture, size, azimuth, elevation, 0, 0, 0, true, null);
    }

    public static SkyObject orbiting(Identifier texture, float size, float period, float inclination, float phase) {
        return new SkyObject(texture, size, 0, 0, period, inclination, phase, true, null);
    }

    public SkyObject withRing(Ring ring) {
        return new SkyObject(texture, size, azimuth, elevation, orbitPeriod, orbitInclination, orbitPhase, phases, ring);
    }

    public SkyObject withoutPhases() {
        return new SkyObject(texture, size, azimuth, elevation, orbitPeriod, orbitInclination, orbitPhase, false, ring);
    }

    public boolean isFixed() {
        return orbitPeriod == 0;
    }

    /**
     * @param texture ring texture (square, annulus with alpha)
     * @param scale   outer ring radius relative to the planet's half-size
     * @param tilt    how far (degrees) the ring plane is opened towards the viewer
     * @param roll    rotation (degrees) of the ring around the view axis
     * @param alpha   overall opacity
     */
    public record Ring(Identifier texture, float scale, float tilt, float roll, float alpha) {
    }
}
