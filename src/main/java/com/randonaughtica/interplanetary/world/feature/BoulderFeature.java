package com.randonaughtica.interplanetary.world.feature;

import com.mojang.serialization.Codec;
import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.random.Random;
import net.minecraft.world.StructureWorldAccess;
import net.minecraft.world.gen.feature.Feature;
import net.minecraft.world.gen.feature.util.FeatureContext;

/** A lumpy, half-buried rock. Place with a heightmap placement modifier. */
public class BoulderFeature extends Feature<BoulderFeatureConfig> {
    public BoulderFeature(Codec<BoulderFeatureConfig> codec) {
        super(codec);
    }

    @Override
    public boolean generate(FeatureContext<BoulderFeatureConfig> context) {
        StructureWorldAccess world = context.getWorld();
        Random random = context.getRandom();
        BoulderFeatureConfig config = context.getConfig();
        BlockPos origin = context.getOrigin();

        BlockState ground = world.getBlockState(origin.down());
        if (ground.isAir() || !ground.getFluidState().isEmpty() || !world.getFluidState(origin).isEmpty()) {
            return false;
        }

        int radius = config.radius().get(random);
        double rx = radius + random.nextDouble() * 0.6;
        double ry = radius * (0.65 + random.nextDouble() * 0.35);
        double rz = radius + random.nextDouble() * 0.6;
        BlockPos center = origin.down(Math.max(0, radius / 2));
        int r = radius + 1;

        BlockPos.Mutable pos = new BlockPos.Mutable();
        for (int dx = -r; dx <= r; dx++) {
            for (int dy = -r; dy <= r; dy++) {
                for (int dz = -r; dz <= r; dz++) {
                    double d = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) + (dz * dz) / (rz * rz);
                    if (d > 1.0 + (random.nextDouble() - 0.5) * 0.35) {
                        continue;
                    }
                    pos.set(center.getX() + dx, center.getY() + dy, center.getZ() + dz);
                    BlockState existing = world.getBlockState(pos);
                    if (existing.isOf(Blocks.BEDROCK) || !existing.getFluidState().isEmpty()) {
                        continue;
                    }
                    world.setBlockState(pos, config.state().get(random, pos), Block.NOTIFY_LISTENERS);
                }
            }
        }
        return true;
    }
}
