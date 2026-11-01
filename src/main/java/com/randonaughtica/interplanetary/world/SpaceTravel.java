package com.randonaughtica.interplanetary.world;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import com.randonaughtica.interplanetary.registry.ModEntities;
import com.randonaughtica.interplanetary.registry.ModGameRules;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.registry.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.ChunkSectionPos;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.Heightmap;
import net.minecraft.world.TeleportTarget;
import net.minecraft.world.World;

/** Moving players (and their rockets) between worlds. */
public final class SpaceTravel {
    private SpaceTravel() {
    }

    /** Handles a launch request sent from the flight computer screen. */
    public static void requestLaunch(ServerPlayerEntity player, String destinationId) {
        if (!(player.getVehicle() instanceof RocketEntity rocket)) {
            player.sendMessage(Text.translatable("message.interplanetary.rocket.not_seated").formatted(Formatting.RED), true);
            return;
        }
        CelestialBody body = CelestialBodies.get(destinationId);
        if (body == null) {
            return;
        }
        if (rocket.getState() != RocketEntity.State.IDLE) {
            return;
        }
        if (CelestialBodies.byWorld(player.getWorld()) == body) {
            player.sendMessage(Text.translatable("message.interplanetary.rocket.already_here", body.displayName())
                    .formatted(Formatting.YELLOW), true);
            return;
        }
        if (body.tier() > rocket.getTier()) {
            player.sendMessage(Text.translatable("message.interplanetary.rocket.tier_too_low", body.displayName(), body.tier())
                    .formatted(Formatting.RED), true);
            return;
        }
        boolean needsFuel = player.getServerWorld().getGameRules().getBoolean(ModGameRules.ROCKETS_NEED_FUEL)
                && !player.isCreative();
        if (needsFuel) {
            if (rocket.getFuel() < body.fuelCost()) {
                player.sendMessage(Text.translatable("message.interplanetary.rocket.need_fuel", body.fuelCost(), rocket.getFuel())
                        .formatted(Formatting.RED), true);
                return;
            }
            rocket.setFuel(rocket.getFuel() - body.fuelCost());
        }
        rocket.startCountdown(body.id());
    }

    /** Called when a launching rocket reaches space: moves rocket and pilot to the destination. */
    public static void completeFlight(RocketEntity oldRocket, ServerPlayerEntity player, CelestialBody body) {
        MinecraftServer server = player.getServer();
        ServerWorld target = server == null ? null : server.getWorld(body.worldKey());
        if (target == null) {
            return;
        }
        BlockPos landing = arrivalPoint(player, target, oldRocket.getBlockX(), oldRocket.getBlockZ());
        double spawnY = Math.min(landing.getY() + 64, target.getTopY() - 8);

        RocketEntity rocket = ModEntities.ROCKET.create(target);
        if (rocket == null) {
            return;
        }
        rocket.copyRocketDataFrom(oldRocket);
        rocket.refreshPositionAndAngles(landing.getX() + 0.5, spawnY, landing.getZ() + 0.5, oldRocket.getYaw(), 0.0F);
        rocket.beginLanding();

        player.stopRiding();
        oldRocket.discard();
        target.spawnEntity(rocket);

        teleport(player, target, new Vec3d(rocket.getX(), rocket.getY() + 1.0, rocket.getZ()));
        player.startRiding(rocket, true);
        player.fallDistance = 0;
    }

    /** Teleports a player (across dimensions if needed). */
    public static void teleport(ServerPlayerEntity player, ServerWorld world, Vec3d pos) {
        player.teleportTo(new TeleportTarget(world, pos, Vec3d.ZERO, player.getYaw(), player.getPitch(), entity -> {
        }));
        player.fallDistance = 0;
    }

    /**
     * Where a flight to {@code target} should come down. Returning to Earth brings you back to your spawn
     * point; everywhere else you land at the same coordinates you took off from.
     */
    public static BlockPos arrivalPoint(ServerPlayerEntity player, ServerWorld target, int x, int z) {
        if (target.getRegistryKey() == World.OVERWORLD) {
            BlockPos spawn = player.getSpawnPointPosition();
            if (spawn == null || player.getSpawnPointDimension() != World.OVERWORLD) {
                spawn = target.getSpawnPos();
            }
            x = spawn.getX();
            z = spawn.getZ();
        }
        return findLandingSpot(target, x, z);
    }

    /**
     * Finds a dry, solid spot near (x, z), searching outwards. If there is none (floating asteroids,
     * oceans), a small landing platform is built.
     *
     * @return the position the rocket/player should stand in
     */
    public static BlockPos findLandingSpot(ServerWorld world, int x, int z) {
        for (int radius = 0; radius <= 96; radius += 16) {
            for (int dx = -radius; dx <= radius; dx += 16) {
                for (int dz = -radius; dz <= radius; dz += 16) {
                    if (Math.max(Math.abs(dx), Math.abs(dz)) != radius) {
                        continue; // only the ring of this radius
                    }
                    BlockPos candidate = surfaceAt(world, x + dx, z + dz);
                    if (candidate != null) {
                        return candidate;
                    }
                }
            }
        }
        int y = Math.max(world.getSeaLevel() + 2, world.getBottomY() + 100);
        BlockPos pos = new BlockPos(x, y, z);
        buildPlatform(world, pos.down());
        return pos;
    }

    private static BlockPos surfaceAt(ServerWorld world, int x, int z) {
        world.getChunk(ChunkSectionPos.getSectionCoord(x), ChunkSectionPos.getSectionCoord(z));
        int top = world.getTopY(Heightmap.Type.MOTION_BLOCKING_NO_LEAVES, x, z);
        if (top <= world.getBottomY() + 1 || top >= world.getTopY() - 8) {
            return null;
        }
        BlockPos pos = new BlockPos(x, top, z);
        BlockState ground = world.getBlockState(pos.down());
        if (!ground.getFluidState().isEmpty() || ground.isOf(Blocks.BEDROCK)) {
            return null;
        }
        return pos;
    }

    private static void buildPlatform(ServerWorld world, BlockPos center) {
        BlockState pad = Registries.BLOCK.get(InterplanetaryStuff.id("launch_pad")).getDefaultState();
        for (int dx = -2; dx <= 2; dx++) {
            for (int dz = -2; dz <= 2; dz++) {
                world.setBlockState(center.add(dx, 0, dz), pad);
                for (int dy = 1; dy <= 6; dy++) {
                    BlockPos above = center.add(dx, dy, dz);
                    if (!world.getBlockState(above).isAir()) {
                        world.setBlockState(above, Blocks.AIR.getDefaultState());
                    }
                }
            }
        }
    }
}
