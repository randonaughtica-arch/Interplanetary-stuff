package com.randonaughtica.interplanetary.gametest;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.world.SpaceTravel;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.block.BlockState;
import net.minecraft.registry.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.test.GameTest;
import net.minecraft.test.TestContext;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.ChunkSectionPos;
import net.minecraft.world.Heightmap;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Smoke tests run by {@code ./gradlew runGametest}: every world must exist, generate terrain without
 * errors and offer somewhere to land. A small terrain map of each world is printed to the log.
 */
public class InterplanetaryGameTests implements FabricGameTest {
    private static final String SHADES = " .:-=+*#%@";

    @GameTest(templateName = EMPTY_STRUCTURE)
    public void everyWorldGeneratesAndHasALandingSpot(TestContext context) {
        MinecraftServer server = context.getWorld().getServer();
        List<String> failures = new ArrayList<>();
        for (CelestialBody body : CelestialBodies.destinations()) {
            ServerWorld world = server.getWorld(body.worldKey());
            if (world == null) {
                failures.add(body.id() + ": dimension is missing");
                continue;
            }
            try {
                BlockPos landing = SpaceTravel.findLandingSpot(world, 0, 0);
                BlockState ground = world.getBlockState(landing.down());
                if (ground.isAir() || !ground.getFluidState().isEmpty()) {
                    failures.add(body.id() + ": no solid ground at " + landing);
                }
                logTerrain(body, world, landing, ground);
            } catch (RuntimeException e) {
                InterplanetaryStuff.LOGGER.error("[gametest] {} failed to generate", body.id(), e);
                failures.add(body.id() + ": " + e);
            }
        }
        context.assertTrue(failures.isEmpty(), String.join("; ", failures));
        context.complete();
    }

    @GameTest(templateName = EMPTY_STRUCTURE)
    public void gravityIsLowerOnTheMoon(TestContext context) {
        CelestialBody moon = CelestialBodies.get("moon");
        context.assertTrue(moon != null && moon.gameplayGravity() < 0.2, "Moon gravity should be about 1/6 g");
        CelestialBody earth = CelestialBodies.EARTH;
        context.assertTrue(earth.gameplayGravity() == 1.0, "Earth gravity should be 1 g");
        for (CelestialBody body : CelestialBodies.all()) {
            double g = body.gameplayGravity();
            context.assertTrue(g >= CelestialBody.MIN_GAMEPLAY_GRAVITY && g <= 1.0, body.id() + " has invalid gravity " + g);
        }
        context.complete();
    }

    /** Prints a 48x48 block shaded height map around the origin plus a census of surface blocks. */
    private static void logTerrain(CelestialBody body, ServerWorld world, BlockPos landing, BlockState ground) {
        int size = 48;
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        int[][] heights = new int[size][size];
        Map<String, Integer> census = new HashMap<>();
        for (int x = 0; x < size; x++) {
            for (int z = 0; z < size; z++) {
                int bx = x - 8;
                int bz = z - 8;
                world.getChunk(ChunkSectionPos.getSectionCoord(bx), ChunkSectionPos.getSectionCoord(bz));
                int h = world.getTopY(Heightmap.Type.MOTION_BLOCKING, bx, bz);
                heights[x][z] = h;
                if (h > world.getBottomY()) {
                    min = Math.min(min, h);
                    max = Math.max(max, h);
                    String id = Registries.BLOCK.getId(world.getBlockState(new BlockPos(bx, h - 1, bz)).getBlock()).toString();
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
        InterplanetaryStuff.LOGGER.info("[gametest] {}: landing {} on {}, height {}..{}, surface {}{}",
                body.id(), landing.toShortString(), Registries.BLOCK.getId(ground.getBlock()), min, max, census, map);
    }
}
