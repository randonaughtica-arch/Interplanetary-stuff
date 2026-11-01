package com.randonaughtica.interplanetary.item;

import com.randonaughtica.interplanetary.entity.RocketEntity;
import com.randonaughtica.interplanetary.registry.ModEntities;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemUsageContext;
import net.minecraft.item.tooltip.TooltipType;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Formatting;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.MathHelper;
import net.minecraft.world.World;
import net.minecraft.world.event.GameEvent;

import java.util.List;

/** Places a rocket of the given tier. Higher tiers reach further destinations. */
public class RocketItem extends Item {
    private final int tier;

    public RocketItem(int tier, Settings settings) {
        super(settings);
        this.tier = tier;
    }

    public int getTier() {
        return tier;
    }

    @Override
    public ActionResult useOnBlock(ItemUsageContext context) {
        World world = context.getWorld();
        if (!(world instanceof ServerWorld serverWorld)) {
            return ActionResult.SUCCESS;
        }
        BlockPos clicked = context.getBlockPos();
        BlockPos pos = world.getBlockState(clicked).isReplaceable() ? clicked : clicked.offset(context.getSide());
        PlayerEntity player = context.getPlayer();

        RocketEntity rocket = ModEntities.ROCKET.create(serverWorld);
        if (rocket == null) {
            return ActionResult.FAIL;
        }
        // Face the rocket's hatch towards the player, snapped to 90 degrees.
        float yaw = player != null ? Math.round(MathHelper.wrapDegrees(player.getYaw() + 180.0F) / 90.0F) * 90.0F : 0.0F;
        rocket.refreshPositionAndAngles(pos.getX() + 0.5, pos.getY(), pos.getZ() + 0.5, yaw, 0.0F);
        rocket.setTier(tier);

        if (!serverWorld.isSpaceEmpty(rocket, rocket.getBoundingBox())) {
            if (player != null) {
                player.sendMessage(Text.translatable("message.interplanetary.rocket.no_room")
                        .formatted(Formatting.RED), true);
            }
            return ActionResult.FAIL;
        }

        serverWorld.spawnEntity(rocket);
        serverWorld.emitGameEvent(player, GameEvent.ENTITY_PLACE, pos);
        context.getStack().decrementUnlessCreative(1, player);
        return ActionResult.CONSUME;
    }

    @Override
    public void appendTooltip(ItemStack stack, TooltipContext context, List<Text> tooltip, TooltipType type) {
        tooltip.add(Text.translatable("item.interplanetary.rocket.tier", tier).formatted(Formatting.GOLD));
        tooltip.add(Text.translatable("item.interplanetary.rocket.range." + tier).formatted(Formatting.GRAY));
        tooltip.add(Text.translatable("item.interplanetary.rocket.usage").formatted(Formatting.DARK_GRAY));
    }
}
