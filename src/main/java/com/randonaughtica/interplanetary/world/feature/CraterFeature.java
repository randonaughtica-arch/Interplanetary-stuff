package com.randonaughtica.interplanetary.world.feature;

import com.mojang.serialization.Codec;
import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.ChunkPos;
import net.minecraft.util.math.random.Random;
import net.minecraft.world.Heightmap;
import net.minecraft.world.StructureWorldAccess;
import net.minecraft.world.gen.feature.Feature;
import net.minecraft.world.gen.feature.util.FeatureContext;

/**
 * Digs a bowl-shaped impact crater with a raised rim into whatever the surface is made of.
 * Craters are sized so that they never reach outside the area a feature may edit.
 */
public class CraterFeature extends Feature<CraterFeatureConfig> {
    private static final BlockState AIR = Blocks.AIR.getDefaultState();

    public CraterFeature(Codec<CraterFeatureConfig> codec) {
        super(codec);
    }

    @Override
    public boolean generate(FeatureContext<CraterFeatureConfig> context) {
        StructureWorldAccess world = context.getWorld();
        Random random = context.getRandom();
        CraterFeatureConfig config = context.getConfig();
        ChunkPos chunk = new ChunkPos(context.getOrigin());

        // Features may only edit the 3x3 chunks around their own chunk: shrink craters near the edges.
        int localX = random.nextInt(16);
        int localZ = random.nextInt(16);
        int maxOuter = Math.min(Math.min(16 + localX, 31 - localX), Math.min(16 + localZ, 31 - localZ));
        int radius = Math.min(config.radius().get(random), (int) Math.floor(maxOuter / 1.45));
        int centerX = chunk.getStartX() + localX;
        int centerZ = chunk.getStartZ() + localZ;
        int surfaceY = world.getTopY(Heightmap.Type.WORLD_SURFACE_WG, centerX, centerZ) - 1;
        if (surfaceY < world.getBottomY() + radius + 6) {
            return false;
        }

        BlockPos.Mutable pos = new BlockPos.Mutable(centerX, surfaceY, centerZ);
        BlockState surface = world.getBlockState(pos);
        if (surface.isAir() || !surface.getFluidState().isEmpty()) {
            return false;
        }

        double depth = Math.max(2.0, radius * config.depth());
        double rimHeight = radius * config.rim();
        int outer = (int) Math.ceil(radius * 1.45);
        double wobble = random.nextDouble() * Math.PI * 2.0;

        for (int dx = -outer; dx <= outer; dx++) {
            for (int dz = -outer; dz <= outer; dz++) {
                double angle = Math.atan2(dz, dx);
                double edge = radius * (1.0 + 0.07 * Math.sin(angle * 3.0 + wobble) + 0.04 * Math.sin(angle * 7.0 + wobble * 2.0));
                double dist = Math.sqrt(dx * dx + dz * dz) / edge;
                if (dist >= 1.45) {
                    continue;
                }
                int x = centerX + dx;
                int z = centerZ + dz;
                int top = world.getTopY(Heightmap.Type.WORLD_SURFACE_WG, x, z) - 1;

                if (dist < 1.0) {
                    int floor = (int) Math.round(surfaceY - depth * (1.0 - dist * dist));
                    if (top <= floor) {
                        continue;
                    }
                    for (int y = top; y > floor; y--) {
                        pos.set(x, y, z);
                        if (!world.getBlockState(pos).isOf(Blocks.BEDROCK)) {
                            world.setBlockState(pos, AIR, Block.NOTIFY_LISTENERS);
                        }
                    }
                    pos.set(x, floor, z);
                    if (!world.getBlockState(pos).isOf(Blocks.BEDROCK)) {
                        BlockState floorState = dist < 0.55 && config.floor().isPresent()
                                ? config.floor().get().get(random, pos)
                                : surface;
                        world.setBlockState(pos, floorState, Block.NOTIFY_LISTENERS);
                    }
                } else {
                    // Raised rim that fades outwards.
                    double t = (dist - 1.0) / 0.45;
                    int height = (int) Math.round(rimHeight * (1.0 - t) * (1.0 - t) + random.nextDouble() * 0.6 - 0.3);
                    for (int i = 1; i <= height; i++) {
                        pos.set(x, top + i, z);
                        if (world.getBlockState(pos).isAir()) {
                            world.setBlockState(pos, surface, Block.NOTIFY_LISTENERS);
                        }
                    }
                }
            }
        }
        return true;
    }
}
