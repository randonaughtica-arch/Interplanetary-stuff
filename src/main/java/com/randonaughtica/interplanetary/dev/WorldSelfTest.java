package com.randonaughtica.interplanetary.dev;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.world.SpaceTravel;
import net.minecraft.block.BlockState;
import net.minecraft.registry.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.crash.CrashException;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.ChunkSectionPos;
import net.minecraft.world.Heightmap;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Development/CI check, off by default. With {@code -Dinterplanetary.ciSelfTest=true} a dedicated server
 * generates terrain on every world, checks there is somewhere to land, prints a small shaded height map
 * of each world to the log, and shuts down. Run it with {@code ./gradlew runCiServer}.
 */
public final class WorldSelfTest {
    private static final String SHADES = " .:-=+*#%@";

    private WorldSelfTest() {
    }

    public static List<String> run(MinecraftServer server) {
        List<String> failures = new ArrayList<>();
        InterplanetaryStuff.LOGGER.info("[selftest] world seed {}", server.getOverworld().getSeed());
        for (CelestialBody body : CelestialBodies.destinations()) {
            InterplanetaryStuff.LOGGER.info("[selftest] generating {}", body.id());
            ServerWorld world = server.getWorld(body.worldKey());
            if (world == null) {
                failures.add(body.id() + ": dimension is missing");
                continue;
            }
            try {
                long start = System.currentTimeMillis();
                // Generate a 9x9 chunk area so that every kind of feature gets placed a few times.
                for (int cx = -4; cx <= 4; cx++) {
                    for (int cz = -4; cz <= 4; cz++) {
                        world.getChunk(cx, cz);
                    }
                }
                BlockPos landing = SpaceTravel.findLandingSpot(world, 0, 0);
                BlockState ground = world.getBlockState(landing.down());
                if (ground.isAir() || !ground.getFluidState().isEmpty()) {
                    failures.add(body.id() + ": no solid ground at " + landing);
                }
                logTerrain(body, world, landing, ground, System.currentTimeMillis() - start);
            } catch (CrashException e) {
                InterplanetaryStuff.LOGGER.error("[selftest] {} failed to generate: {}", body.id(), e.getReport().getMessage(), e);
                failures.add(body.id() + ": " + e.getCause());
            } catch (RuntimeException e) {
                InterplanetaryStuff.LOGGER.error("[selftest] {} failed to generate", body.id(), e);
                failures.add(body.id() + ": " + e);
            }
        }
        return failures;
    }

    /** Prints a 64x64 block shaded height map around the origin plus a census of surface blocks. */
    private static void logTerrain(CelestialBody body, ServerWorld world, BlockPos landing, BlockState ground,
                                   long millis) {
        int size = 64;
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        int[][] heights = new int[size][size];
        Map<String, Integer> census = new HashMap<>();
        for (int x = 0; x < size; x++) {
            for (int z = 0; z < size; z++) {
                int bx = x - size / 2;
                int bz = z - size / 2;
                world.getChunk(ChunkSectionPos.getSectionCoord(bx), ChunkSectionPos.getSectionCoord(bz));
                int h = world.getTopY(Heightmap.Type.MOTION_BLOCKING, bx, bz);
                heights[x][z] = h;
                if (h > world.getBottomY()) {
                    min = Math.min(min, h);
                    max = Math.max(max, h);
                    String id = Registries.BLOCK.getId(world.getBlockState(new BlockPos(bx, h - 1, bz)).getBlock()).getPath();
                    census.merge(id, 1, Integer::sum);
                }
            }
        }
        StringBuilder map = new StringBuilder();
        for (int z = 0; z < size; z += 2) {
            map.append("\n    ");
            for (int x = 0; x < size; x++) {
                int h = heights[x][z];
                if (h <= world.getBottomY()) {
                    map.append(' ');
                } else {
                    int range = Math.max(1, max - min);
                    int index = Math.min(SHADES.length() - 1, 1 + (h - min) * (SHADES.length() - 2) / range);
                    map.append(SHADES.charAt(index));
                }
            }
        }
        InterplanetaryStuff.LOGGER.info("[selftest] {}: landing {} on {}, height {}..{}, generated in {} ms, surface {}{}",
                body.id(), landing.toShortString(), Registries.BLOCK.getId(ground.getBlock()), min, max, millis,
                census, map);
    }
}
