package com.randonaughtica.interplanetary.registry;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import net.minecraft.block.AbstractBlock;
import net.minecraft.block.Block;
import net.minecraft.block.MapColor;
import net.minecraft.item.BlockItem;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.sound.BlockSoundGroup;
import net.minecraft.util.Identifier;

import java.util.ArrayList;
import java.util.List;

public final class ModBlocks {
    /** Every block of the mod, in creative-tab order. */
    public static final List<Block> BLOCKS = new ArrayList<>();
    /** Blocks that need the cutout render layer (crystal clusters...). */
    public static final List<Block> CUTOUT = new ArrayList<>();

    private ModBlocks() {
    }

    public static <T extends Block> T register(String name, T block) {
        Identifier id = InterplanetaryStuff.id(name);
        Registry.register(Registries.BLOCK, id, block);
        Registry.register(Registries.ITEM, id, new BlockItem(block, new Item.Settings()));
        BLOCKS.add(block);
        return block;
    }

    public static <T extends Block> T registerCutout(String name, T block) {
        CUTOUT.add(block);
        return register(name, block);
    }

    public static AbstractBlock.Settings settings(MapColor color, float hardness, float resistance,
                                                  BlockSoundGroup sounds, boolean requiresTool) {
        AbstractBlock.Settings settings = AbstractBlock.Settings.create()
                .mapColor(color)
                .strength(hardness, resistance)
                .sounds(sounds);
        return requiresTool ? settings.requiresTool() : settings;
    }

    public static void init() {
        PlanetBlocks.init();
    }
}
