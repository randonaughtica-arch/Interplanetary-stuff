package com.randonaughtica.interplanetary.client.render;

import com.randonaughtica.interplanetary.client.InterplanetaryClient;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.render.RenderTickCounter;
import net.minecraft.text.Text;

/** Small cockpit panel shown while seated in a rocket: tier, fuel gauge and the flight computer key. */
@Environment(EnvType.CLIENT)
public final class RocketHud {
    private RocketHud() {
    }

    public static void render(DrawContext context, RenderTickCounter tickCounter) {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null || client.options.hudHidden || client.currentScreen != null) {
            return;
        }
        if (!(client.player.getVehicle() instanceof RocketEntity rocket)) {
            return;
        }
        TextRenderer font = client.textRenderer;
        int fuel = rocket.getFuel();
        int x = 8;
        int y = context.getScaledWindowHeight() - 50;
        Text keyHint = Text.translatable("hud.interplanetary.flight_computer",
                InterplanetaryClient.flightComputerKey.getBoundKeyLocalizedText());
        int width = Math.max(150, font.getWidth(keyHint) + 8);

        context.fill(x - 4, y - 4, x + width, y + 36, 0x99000000);
        context.drawText(font, Text.translatable("hud.interplanetary.rocket", rocket.getTier()), x, y, 0xFFE8B0, true);

        int barWidth = 100;
        int filled = barWidth * fuel / RocketEntity.MAX_FUEL;
        int color = fuel >= 50 ? 0xFF4CC3FF : fuel >= 25 ? 0xFFFFC040 : 0xFFFF5040;
        context.fill(x, y + 12, x + barWidth, y + 19, 0xFF2A2A2A);
        context.fill(x, y + 12, x + filled, y + 19, color);
        context.drawText(font, Text.translatable("hud.interplanetary.fuel", fuel, RocketEntity.MAX_FUEL),
                x + barWidth + 4, y + 11, 0xFFFFFF, true);
        context.drawText(font, keyHint, x, y + 24, 0xB0B0B0, true);
    }
}
