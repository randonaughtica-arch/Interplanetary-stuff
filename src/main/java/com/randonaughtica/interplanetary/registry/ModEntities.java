package com.randonaughtica.interplanetary.registry;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.SpawnGroup;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;

public final class ModEntities {
    public static final EntityType<RocketEntity> ROCKET = Registry.register(Registries.ENTITY_TYPE,
            InterplanetaryStuff.id("rocket"),
            EntityType.Builder.<RocketEntity>create(RocketEntity::new, SpawnGroup.MISC)
                    .dimensions(1.2F, 4.6F)
                    .passengerAttachments(1.7F)
                    .maxTrackingRange(10)
                    .trackingTickInterval(1)
                    .build("rocket"));

    private ModEntities() {
    }

    public static void init() {
    }
}
