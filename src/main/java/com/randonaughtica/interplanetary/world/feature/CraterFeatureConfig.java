package com.randonaughtica.interplanetary.world.feature;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.util.math.intprovider.IntProvider;
import net.minecraft.world.gen.feature.FeatureConfig;
import net.minecraft.world.gen.stateprovider.BlockStateProvider;

import java.util.Optional;

/**
 * @param radius crater radius in blocks (2-14)
 * @param depth  depth as a fraction of the radius
 * @param rim    rim height as a fraction of the radius
 * @param floor  optional block for the middle of the crater floor (ice, salt deposits...)
 */
public record CraterFeatureConfig(IntProvider radius, float depth, float rim, Optional<BlockStateProvider> floor)
        implements FeatureConfig {

    public static final Codec<CraterFeatureConfig> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            IntProvider.createValidatingCodec(2, 14).fieldOf("radius").forGetter(CraterFeatureConfig::radius),
            Codec.floatRange(0.05F, 1.5F).fieldOf("depth").forGetter(CraterFeatureConfig::depth),
            Codec.floatRange(0.0F, 1.0F).optionalFieldOf("rim", 0.2F).forGetter(CraterFeatureConfig::rim),
            BlockStateProvider.TYPE_CODEC.optionalFieldOf("floor").forGetter(CraterFeatureConfig::floor)
    ).apply(instance, CraterFeatureConfig::new));
}
