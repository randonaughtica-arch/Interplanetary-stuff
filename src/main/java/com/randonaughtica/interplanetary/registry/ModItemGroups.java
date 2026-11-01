package com.randonaughtica.interplanetary.registry;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import net.fabricmc.fabric.api.itemgroup.v1.FabricItemGroup;
import net.minecraft.item.ItemGroup;
import net.minecraft.item.ItemStack;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.text.Text;

public final class ModItemGroups {
    public static final ItemGroup MAIN = Registry.register(Registries.ITEM_GROUP, InterplanetaryStuff.id("main"),
            FabricItemGroup.builder()
                    .icon(() -> new ItemStack(ModItems.ROCKET_TIER_1))
                    .displayName(Text.translatable("itemGroup.interplanetary.main"))
                    .entries((context, entries) -> ModItems.ITEMS.forEach(entries::add))
                    .build());

    public static final ItemGroup BLOCKS = Registry.register(Registries.ITEM_GROUP, InterplanetaryStuff.id("blocks"),
            FabricItemGroup.builder()
                    .icon(() -> new ItemStack(PlanetBlocks.MOON_REGOLITH))
                    .displayName(Text.translatable("itemGroup.interplanetary.blocks"))
                    .entries((context, entries) -> ModBlocks.BLOCKS.forEach(entries::add))
                    .build());

    private ModItemGroups() {
    }

    public static void init() {
    }
}
