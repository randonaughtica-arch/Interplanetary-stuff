package com.randonaughtica.interplanetary.registry;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import net.minecraft.entity.damage.DamageSource;
import net.minecraft.entity.damage.DamageType;
import net.minecraft.registry.RegistryKey;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.world.World;

public final class ModDamageTypes {
    /** Defined in {@code data/interplanetary/damage_type/vacuum.json}. */
    public static final RegistryKey<DamageType> VACUUM = RegistryKey.of(RegistryKeys.DAMAGE_TYPE,
            InterplanetaryStuff.id("vacuum"));

    private ModDamageTypes() {
    }

    public static DamageSource vacuum(World world) {
        return new DamageSource(world.getRegistryManager().get(RegistryKeys.DAMAGE_TYPE).entryOf(VACUUM));
    }
}
