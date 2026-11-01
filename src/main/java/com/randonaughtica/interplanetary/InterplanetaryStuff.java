package com.randonaughtica.interplanetary;

import com.randonaughtica.interplanetary.command.InterplanetaryCommand;
import com.randonaughtica.interplanetary.network.ModNetworking;
import com.randonaughtica.interplanetary.registry.ModArmorMaterials;
import com.randonaughtica.interplanetary.registry.ModBlocks;
import com.randonaughtica.interplanetary.registry.ModEntities;
import com.randonaughtica.interplanetary.registry.ModFeatures;
import com.randonaughtica.interplanetary.registry.ModGameRules;
import com.randonaughtica.interplanetary.registry.ModItemGroups;
import com.randonaughtica.interplanetary.registry.ModItems;
import com.randonaughtica.interplanetary.world.GravityHandler;
import com.randonaughtica.interplanetary.world.SpaceHazards;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.util.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Interplanetary Stuff — travel the Solar System by rocket.
 *
 * <p>Adds 30 explorable worlds (planets, dwarf planets, moons and asteroids), each with its
 * own terrain, blocks, gravity and sky, plus rockets, a star map, space suits and more.
 */
public final class InterplanetaryStuff implements ModInitializer {
    public static final String MOD_ID = "interplanetary";
    public static final Logger LOGGER = LoggerFactory.getLogger("Interplanetary Stuff");

    public static Identifier id(String path) {
        return Identifier.of(MOD_ID, path);
    }

    @Override
    public void onInitialize() {
        ModArmorMaterials.init();
        ModBlocks.init();
        ModItems.init();
        ModItemGroups.init();
        ModEntities.init();
        ModFeatures.init();
        ModGameRules.init();
        ModNetworking.init();

        GravityHandler.init();
        SpaceHazards.init();

        CommandRegistrationCallback.EVENT.register(
                (dispatcher, registryAccess, environment) -> InterplanetaryCommand.register(dispatcher));

        LOGGER.info("Interplanetary Stuff loaded — {} destinations await!",
                com.randonaughtica.interplanetary.body.CelestialBodies.all().size() - 1);
    }
}
