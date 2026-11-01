package com.randonaughtica.interplanetary.gametest;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import com.randonaughtica.interplanetary.registry.ModEntities;
import com.randonaughtica.interplanetary.registry.ModItems;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.registry.DynamicRegistryManager;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.test.GameTest;
import net.minecraft.test.TestContext;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.BlockPos;

/**
 * Game tests ({@code ./gradlew runGametest}). World generation itself is checked by
 * {@link com.randonaughtica.interplanetary.dev.WorldSelfTest} because the game-test server does not
 * create datapack dimensions.
 */
public class InterplanetaryGameTests implements FabricGameTest {

    @GameTest(templateName = EMPTY_STRUCTURE)
    public void everyWorldIsRegistered(TestContext context) {
        DynamicRegistryManager registries = context.getWorld().getRegistryManager();
        for (CelestialBody body : CelestialBodies.destinations()) {
            Identifier id = InterplanetaryStuff.id(body.id());
            context.assertTrue(registries.get(RegistryKeys.DIMENSION_TYPE).containsId(id),
                    "Missing dimension type " + id);
            context.assertTrue(registries.get(RegistryKeys.CHUNK_GENERATOR_SETTINGS).containsId(id),
                    "Missing noise settings " + id);
        }
        context.complete();
    }

    @GameTest(templateName = EMPTY_STRUCTURE)
    public void gravityIsSensible(TestContext context) {
        CelestialBody moon = CelestialBodies.get("moon");
        context.assertTrue(moon != null && moon.gameplayGravity() < 0.2, "Moon gravity should be about 1/6 g");
        context.assertTrue(CelestialBodies.EARTH.gameplayGravity() == 1.0, "Earth gravity should be 1 g");
        for (CelestialBody body : CelestialBodies.all()) {
            double g = body.gameplayGravity();
            context.assertTrue(g >= CelestialBody.MIN_GAMEPLAY_GRAVITY && g <= 1.0,
                    body.id() + " has invalid gravity " + g);
        }
        context.complete();
    }

    @GameTest(templateName = EMPTY_STRUCTURE)
    public void rocketCanBeFuelled(TestContext context) {
        RocketEntity rocket = context.spawnEntity(ModEntities.ROCKET, new BlockPos(1, 2, 1));
        rocket.setTier(2);
        rocket.setFuel(RocketEntity.MAX_FUEL + 50);
        context.assertTrue(rocket.getFuel() == RocketEntity.MAX_FUEL, "Fuel should be capped at the tank size");
        context.assertTrue(rocket.getTier() == 2, "Tier should be stored");
        context.assertTrue(ModItems.rocketForTier(rocket.getTier()) == ModItems.ROCKET_TIER_2, "Rocket item lookup");
        rocket.discard();
        context.complete();
    }
}
