package com.randonaughtica.interplanetary.world.feature;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.util.math.intprovider.IntProvider;
import net.minecraft.world.gen.feature.FeatureConfig;
import net.minecraft.world.gen.stateprovider.BlockStateProvider;

/**
 * @param state  what the boulder is made of
 * @param radius boulder radius in blocks (1-6)
 */
public record BoulderFeatureConfig(BlockStateProvider state, IntProvider radius) implements FeatureConfig {
    public static final Codec<BoulderFeatureConfig> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            BlockStateProvider.TYPE_CODEC.fieldOf("state").forGetter(BoulderFeatureConfig::state),
            IntProvider.createValidatingCodec(1, 6).fieldOf("radius").forGetter(BoulderFeatureConfig::radius)
    ).apply(instance, BoulderFeatureConfig::new));
}
