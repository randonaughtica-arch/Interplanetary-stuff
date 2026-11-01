package com.randonaughtica.interplanetary.world;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import net.fabricmc.fabric.api.entity.event.v1.ServerEntityWorldChangeEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.attribute.EntityAttribute;
import net.minecraft.entity.attribute.EntityAttributeInstance;
import net.minecraft.entity.attribute.EntityAttributeModifier;
import net.minecraft.entity.attribute.EntityAttributes;
import net.minecraft.registry.entry.RegistryEntry;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.util.Identifier;
import net.minecraft.world.World;

/**
 * Low gravity! Every living thing on another world gets attribute modifiers that scale its gravity,
 * how far it can fall safely and how much falls hurt.
 */
public final class GravityHandler {
    private static final Identifier GRAVITY = InterplanetaryStuff.id("planetary_gravity");
    private static final Identifier SAFE_FALL = InterplanetaryStuff.id("planetary_safe_fall_distance");
    private static final Identifier FALL_DAMAGE = InterplanetaryStuff.id("planetary_fall_damage");

    private GravityHandler() {
    }

    public static void init() {
        ServerEntityEvents.ENTITY_LOAD.register((entity, world) -> {
            if (entity instanceof LivingEntity living) {
                apply(living, world);
            }
        });
        ServerEntityWorldChangeEvents.AFTER_PLAYER_CHANGE_WORLD.register(
                (player, origin, destination) -> apply(player, destination));
        ServerPlayerEvents.AFTER_RESPAWN.register(
                (oldPlayer, newPlayer, alive) -> apply(newPlayer, newPlayer.getServerWorld()));
        // Safety net (e.g. after /attribute commands or other mods touching attributes).
        ServerTickEvents.END_WORLD_TICK.register(world -> {
            if (world.getTime() % 40 == 0) {
                for (ServerPlayerEntity player : world.getPlayers()) {
                    apply(player, world);
                }
            }
        });
    }

    /** Gravity multiplier of a world: 1.0 on Earth and in non-space dimensions. */
    public static double gravityFactor(World world) {
        CelestialBody body = CelestialBodies.byWorld(world);
        return body == null ? 1.0 : body.gameplayGravity();
    }

    public static void apply(LivingEntity entity, World world) {
        double g = gravityFactor(world);
        double safeFallBonus = g < 1.0 ? Math.min(3.0 / g - 3.0, 40.0) : 0.0;
        set(entity, EntityAttributes.GENERIC_GRAVITY, GRAVITY, g - 1.0,
                EntityAttributeModifier.Operation.ADD_MULTIPLIED_TOTAL);
        set(entity, EntityAttributes.GENERIC_FALL_DAMAGE_MULTIPLIER, FALL_DAMAGE, g - 1.0,
                EntityAttributeModifier.Operation.ADD_MULTIPLIED_TOTAL);
        set(entity, EntityAttributes.GENERIC_SAFE_FALL_DISTANCE, SAFE_FALL, safeFallBonus,
                EntityAttributeModifier.Operation.ADD_VALUE);
    }

    private static void set(LivingEntity entity, RegistryEntry<EntityAttribute> attribute, Identifier id,
                            double value, EntityAttributeModifier.Operation operation) {
        EntityAttributeInstance instance = entity.getAttributeInstance(attribute);
        if (instance == null) {
            return;
        }
        EntityAttributeModifier existing = instance.getModifier(id);
        if (Math.abs(value) < 1.0E-6) {
            if (existing != null) {
                instance.removeModifier(id);
            }
            return;
        }
        if (existing != null) {
            if (existing.value() == value && existing.operation() == operation) {
                return;
            }
            instance.removeModifier(id);
        }
        instance.addTemporaryModifier(new EntityAttributeModifier(id, value, operation));
    }
}
