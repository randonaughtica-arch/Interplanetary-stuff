package com.randonaughtica.interplanetary.world;

import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import com.randonaughtica.interplanetary.registry.ModDamageTypes;
import com.randonaughtica.interplanetary.registry.ModGameRules;
import com.randonaughtica.interplanetary.registry.ModItems;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;

/**
 * No air out there! Without a full space suit your air supply drains (just like underwater) on every
 * world without a breathable atmosphere. Rockets are pressurised. Toggle with the
 * {@code interplanetarySpaceSuffocation} game rule.
 */
public final class SpaceHazards {
    private SpaceHazards() {
    }

    public static void init() {
        ServerTickEvents.END_WORLD_TICK.register(SpaceHazards::tick);
    }

    private static void tick(ServerWorld world) {
        CelestialBody body = CelestialBodies.byWorld(world);
        if (body == null || !body.requiresSpaceSuit()) {
            return;
        }
        if (!world.getGameRules().getBoolean(ModGameRules.SPACE_SUFFOCATION)) {
            return;
        }
        for (ServerPlayerEntity player : world.getPlayers()) {
            if (player.isCreative() || player.isSpectator() || !player.isAlive()) {
                continue;
            }
            if (ModItems.hasFullSpaceSuit(player) || player.getVehicle() instanceof RocketEntity) {
                continue;
            }
            // Vanilla refills 4 air per tick on land; draining 5 nets one per tick, like holding your breath.
            int air = player.getAir() - 5;
            if (air <= -20) {
                air = 0;
                player.damage(ModDamageTypes.vacuum(world), 2.0F);
            }
            player.setAir(air);
            if (world.getTime() % 40 == 0) {
                player.sendMessage(Text.translatable("message.interplanetary.no_oxygen", body.displayName())
                        .formatted(Formatting.RED), true);
            }
        }
    }
}
