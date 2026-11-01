package com.randonaughtica.interplanetary.body;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import net.minecraft.registry.RegistryKey;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;
import net.minecraft.world.World;

/**
 * A destination you can fly to.
 *
 * @param id          body id; also the dimension id ({@code interplanetary:<id>})
 * @param gravity     surface gravity relative to Earth
 * @param temperature average surface temperature in °C
 * @param distanceAu  distance from the Sun in astronomical units
 * @param mapColor    colour used for the star map
 * @param thickFog    whether the world uses short, thick fog (dense atmospheres)
 */
public record CelestialBody(String id, BodyType type, String system, int tier, float gravity, int temperature,
                            Atmosphere atmosphere, float distanceAu, int mapColor, boolean thickFog,
                            SkyProfile sky) {

    /** Gravity is never allowed to drop below this, so tiny moons remain playable. */
    public static final double MIN_GAMEPLAY_GRAVITY = 0.1;

    public boolean isEarth() {
        return "earth".equals(id);
    }

    public RegistryKey<World> worldKey() {
        return isEarth() ? World.OVERWORLD : RegistryKey.of(RegistryKeys.WORLD, InterplanetaryStuff.id(id));
    }

    /** Multiplier applied to the vanilla gravity of entities on this body. */
    public double gameplayGravity() {
        return isEarth() ? 1.0 : Math.max(MIN_GAMEPLAY_GRAVITY, Math.min(1.0, gravity));
    }

    public boolean requiresSpaceSuit() {
        return atmosphere != Atmosphere.BREATHABLE;
    }

    /** Fuel units a rocket burns to fly here. */
    public int fuelCost() {
        return 25 * Math.max(1, tier);
    }

    public Identifier texture() {
        return InterplanetaryStuff.id("textures/environment/bodies/" + id + ".png");
    }

    public String translationKey() {
        return "body.interplanetary." + id;
    }

    public Text displayName() {
        return Text.translatable(translationKey());
    }

    public Text description() {
        return Text.translatable(translationKey() + ".desc");
    }
}
