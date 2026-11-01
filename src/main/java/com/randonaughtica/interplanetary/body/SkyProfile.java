package com.randonaughtica.interplanetary.body;

import java.util.ArrayList;
import java.util.List;

/**
 * Describes how the sky of a world looks. Consumed by the client sky renderer.
 *
 * @param sunSize      half-size of the sun billboard (Earth = 30)
 * @param sunColor     RGB tint of the sun glow
 * @param sunOcclusion 0 = clear view of the sun, 1 = fully hidden by clouds/haze
 * @param dayZenith    atmosphere colour straight up during the day
 * @param dayHorizon   atmosphere colour at the horizon during the day
 * @param dayAlpha     opacity of the atmosphere during the day (0 = vacuum, stars always visible)
 * @param nightAlpha   opacity of the atmosphere at night
 * @param sunsetColor  RGB glow around the sun when it is low (0 = none)
 * @param starBrightness multiplier for star brightness
 * @param objects      planets/moons visible in the sky
 */
public record SkyProfile(float sunSize, int sunColor, float sunOcclusion, int dayZenith, int dayHorizon,
                         float dayAlpha, float nightAlpha, int sunsetColor, float starBrightness,
                         List<SkyObject> objects) {

    public boolean hasAtmosphere() {
        return dayAlpha > 0 || nightAlpha > 0;
    }

    public static Builder builder(float distanceAu) {
        return new Builder(distanceAu);
    }

    public static final class Builder {
        private float sunSize;
        private int sunColor = 0xFFF4D6;
        private float sunOcclusion;
        private int dayZenith;
        private int dayHorizon;
        private float dayAlpha;
        private float nightAlpha;
        private int sunsetColor;
        private float starBrightness = 1.0F;
        private final List<SkyObject> objects = new ArrayList<>();

        private Builder(float distanceAu) {
            // The sun shrinks with distance, but never quite disappears.
            this.sunSize = Math.max(1.6F, Math.min(60.0F, 30.0F / distanceAu));
        }

        public Builder sunColor(int rgb) {
            this.sunColor = rgb;
            return this;
        }

        public Builder sunOcclusion(float occlusion) {
            this.sunOcclusion = occlusion;
            return this;
        }

        public Builder atmosphere(int zenith, int horizon, float dayAlpha, float nightAlpha) {
            this.dayZenith = zenith;
            this.dayHorizon = horizon;
            this.dayAlpha = dayAlpha;
            this.nightAlpha = nightAlpha;
            return this;
        }

        public Builder sunset(int rgb) {
            this.sunsetColor = rgb;
            return this;
        }

        public Builder stars(float brightness) {
            this.starBrightness = brightness;
            return this;
        }

        public Builder object(SkyObject object) {
            this.objects.add(object);
            return this;
        }

        public SkyProfile build() {
            return new SkyProfile(sunSize, sunColor, sunOcclusion, dayZenith, dayHorizon, dayAlpha, nightAlpha,
                    sunsetColor, starBrightness, List.copyOf(objects));
        }
    }
}
