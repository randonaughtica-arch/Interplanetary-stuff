package com.randonaughtica.interplanetary.item;

import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.ItemStack;
import net.minecraft.util.Hand;
import net.minecraft.util.TypedActionResult;
import net.minecraft.world.World;

/** Opens the star map. Launching is possible from the map while seated in a rocket. */
public class StarChartItem extends TooltipItem {
    /** Replaced by the client entrypoint with code that opens the star map screen. */
    public static Runnable openScreen = () -> {
    };

    public StarChartItem(Settings settings) {
        super(settings);
    }

    @Override
    public TypedActionResult<ItemStack> use(World world, PlayerEntity user, Hand hand) {
        if (world.isClient) {
            openScreen.run();
        }
        return TypedActionResult.success(user.getStackInHand(hand), world.isClient);
    }
}
