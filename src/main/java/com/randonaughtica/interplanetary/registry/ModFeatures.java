package com.randonaughtica.interplanetary.registry;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.world.feature.BoulderFeature;
import com.randonaughtica.interplanetary.world.feature.BoulderFeatureConfig;
import com.randonaughtica.interplanetary.world.feature.CraterFeature;
import com.randonaughtica.interplanetary.world.feature.CraterFeatureConfig;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.world.gen.feature.Feature;

public final class ModFeatures {
    /** Bowl-shaped impact crater with a raised rim: {@code interplanetary:crater}. */
    public static final Feature<CraterFeatureConfig> CRATER = Registry.register(Registries.FEATURE,
            InterplanetaryStuff.id("crater"), new CraterFeature(CraterFeatureConfig.CODEC));

    /** Lumpy rock half-buried in the ground: {@code interplanetary:boulder}. */
    public static final Feature<BoulderFeatureConfig> BOULDER = Registry.register(Registries.FEATURE,
            InterplanetaryStuff.id("boulder"), new BoulderFeature(BoulderFeatureConfig.CODEC));

    private ModFeatures() {
    }

    public static void init() {
    }
}
