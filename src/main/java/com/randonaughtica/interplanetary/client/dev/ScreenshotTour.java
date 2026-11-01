package com.randonaughtica.interplanetary.client.dev;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.client.screen.StarMapScreen;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import com.randonaughtica.interplanetary.registry.ModEntities;
import com.randonaughtica.interplanetary.world.SpaceTravel;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.util.ScreenshotRecorder;
import net.minecraft.server.integrated.IntegratedServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.GameMode;
import net.minecraft.world.Heightmap;
import net.minecraft.world.TeleportTarget;

import java.util.List;
import java.util.UUID;

/**
 * Development tool, off by default: with {@code -Dinterplanetary.screenshotTour=true} the client visits a
 * series of worlds after joining a singleplayer world, takes a screenshot of each sky and then quits.
 * Used by CI (see {@code ./gradlew runScreenshotClient}) to check the renderers visually.
 */
@Environment(EnvType.CLIENT)
public final class ScreenshotTour {
    private record Stop(String body, long time, float yaw, float pitch, boolean rocket) {
    }

    private static final List<Stop> STOPS = List.of(
            new Stop("moon", 18000, 20, -25, true),
            new Stop("mars", 6000, 0, -6, false),
            new Stop("mars", 12650, 90, -4, false),
            new Stop("io", 13500, -20, -28, false),
            new Stop("europa", 1000, 20, -18, false),
            new Stop("enceladus", 18000, 10, -35, false),
            new Stop("titan", 6000, -10, -18, false),
            new Stop("venus", 6000, 0, -4, false),
            new Stop("mercury", 23300, -90, -6, false),
            new Stop("bennu", 18000, 30, 10, false),
            new Stop("miranda", 1000, 0, -12, false),
            new Stop("pluto", 18000, -45, -22, false),
            new Stop("phobos", 15000, 190, -40, false));

    private static final int WAIT_TICKS = 220;

    private static int index = -1;
    private static int ticks;
    private static boolean finished;

    private ScreenshotTour() {
    }

    public static void init() {
        if (Boolean.getBoolean("interplanetary.screenshotTour")) {
            InterplanetaryStuff.LOGGER.info("Screenshot tour enabled");
            ClientTickEvents.END_CLIENT_TICK.register(ScreenshotTour::tick);
        }
    }

    private static int waitingTicks;

    private static void tick(MinecraftClient client) {
        if (finished) {
            return;
        }
        if (client.player == null || client.world == null || client.getServer() == null) {
            // Diagnostics: report what is on screen while waiting to join the world.
            waitingTicks++;
            if (waitingTicks % 200 == 0) {
                InterplanetaryStuff.LOGGER.info("[tour] waiting to join a world, screen: {}",
                        client.currentScreen == null ? "none" : client.currentScreen.getClass().getName()
                                + " - " + client.currentScreen.getTitle().getString());
            }
            if (waitingTicks > 6000) {
                InterplanetaryStuff.LOGGER.error("[tour] never joined a world, giving up");
                finished = true;
                client.scheduleStop();
            }
            return;
        }
        ticks++;
        if (index < 0) {
            if (ticks >= 200) {
                advance(client);
            }
            return;
        }
        if (index >= STOPS.size()) {
            if (ticks == 5) {
                client.options.hudHidden = false;
                client.setScreen(new StarMapScreen(null));
            } else if (ticks == 60) {
                shoot(client, "zz_star_map");
            } else if (ticks == 80) {
                finished = true;
                InterplanetaryStuff.LOGGER.info("Screenshot tour finished");
                client.scheduleStop();
            }
            return;
        }
        if (ticks == WAIT_TICKS) {
            Stop stop = STOPS.get(index);
            shoot(client, String.format("%02d_%s", index, stop.body()));
        } else if (ticks > WAIT_TICKS + 10) {
            advance(client);
        }
    }

    private static void shoot(MinecraftClient client, String name) {
        ScreenshotRecorder.saveScreenshot(client.runDirectory, name + ".png", client.getFramebuffer(),
                message -> InterplanetaryStuff.LOGGER.info("[tour] {}", message.getString()));
    }

    private static void advance(MinecraftClient client) {
        index++;
        ticks = 0;
        if (index >= STOPS.size() || client.player == null) {
            return;
        }
        Stop stop = STOPS.get(index);
        client.options.hudHidden = true;
        UUID id = client.player.getUuid();
        IntegratedServer server = client.getServer();
        if (server == null) {
            return;
        }
        server.execute(() -> {
            ServerPlayerEntity player = server.getPlayerManager().getPlayer(id);
            CelestialBody body = CelestialBodies.get(stop.body());
            ServerWorld world = body == null ? null : server.getWorld(body.worldKey());
            if (player == null || world == null) {
                return;
            }
            player.changeGameMode(GameMode.SPECTATOR);
            server.getOverworld().setTimeOfDay(stop.time());
            BlockPos landing = SpaceTravel.findLandingSpot(world, 0, 0);
            Vec3d pos = Vec3d.ofBottomCenter(landing).add(0, 1.2, 0);
            player.teleportTo(new TeleportTarget(world, pos, Vec3d.ZERO, stop.yaw(), stop.pitch(), entity -> {
            }));
            InterplanetaryStuff.LOGGER.info("[tour] {} at {}", stop.body(), landing.toShortString());
            if (stop.rocket()) {
                float yawRad = stop.yaw() * MathHelper.RADIANS_PER_DEGREE;
                int x = MathHelper.floor(pos.x - MathHelper.sin(yawRad) * 12);
                int z = MathHelper.floor(pos.z + MathHelper.cos(yawRad) * 12);
                int y = world.getTopY(Heightmap.Type.MOTION_BLOCKING_NO_LEAVES, x, z);
                RocketEntity rocket = ModEntities.ROCKET.create(world);
                if (rocket != null) {
                    rocket.refreshPositionAndAngles(x + 0.5, y, z + 0.5, stop.yaw() + 180.0F, 0.0F);
                    rocket.setTier(1);
                    world.spawnEntity(rocket);
                }
            }
        });
    }
}
