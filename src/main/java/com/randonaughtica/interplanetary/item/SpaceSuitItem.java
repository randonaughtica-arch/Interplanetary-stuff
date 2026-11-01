package com.randonaughtica.interplanetary.item;

import com.randonaughtica.interplanetary.registry.ModArmorMaterials;
import net.minecraft.item.ArmorItem;
import net.minecraft.item.ItemStack;
import net.minecraft.item.tooltip.TooltipType;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;

import java.util.List;

/** A piece of the space suit. Wearing all four pieces lets you breathe on airless worlds. */
public class SpaceSuitItem extends ArmorItem {
    public SpaceSuitItem(Type type, Settings settings) {
        super(ModArmorMaterials.SPACE_SUIT, type, settings);
    }

    @Override
    public void appendTooltip(ItemStack stack, TooltipContext context, List<Text> tooltip, TooltipType type) {
        tooltip.add(Text.translatable("item.interplanetary.space_suit_piece.tooltip").formatted(Formatting.GRAY));
    }
}
