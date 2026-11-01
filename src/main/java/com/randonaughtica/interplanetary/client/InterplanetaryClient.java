package com.randonaughtica.interplanetary.client;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.client.dev.ScreenshotTour;
import com.randonaughtica.interplanetary.client.render.RocketEntityModel;
import com.randonaughtica.interplanetary.client.render.RocketEntityRenderer;
import com.randonaughtica.interplanetary.client.render.RocketHud;
import com.randonaughtica.interplanetary.client.render.SpaceDimensionEffects;
import com.randonaughtica.interplanetary.client.render.SpaceSkyRenderer;
import com.randonaughtica.interplanetary.client.screen.StarMapScreen;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import com.randonaughtica.interplanetary.item.StarChartItem;
import com.randonaughtica.interplanetary.registry.ModBlocks;
import com.randonaughtica.interplanetary.registry.ModEntities;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.blockrenderlayer.v1.BlockRenderLayerMap;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.DimensionRenderingRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.EntityModelLayerRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.block.Block;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.option.KeyBinding;
import net.minecraft.client.render.RenderLayer;
import net.minecraft.client.util.InputUtil;
import org.lwjgl.glfw.GLFW;

@Environment(EnvType.CLIENT)
public final class InterplanetaryClient implements ClientModInitializer {
    public static KeyBinding flightComputerKey;

    @Override
    public void onInitializeClient() {
        EntityModelLayerRegistry.registerModelLayer(RocketEntityModel.LAYER, RocketEntityModel::getTexturedModelData);
        EntityRendererRegistry.register(ModEntities.ROCKET, RocketEntityRenderer::new);

        for (Block block : ModBlocks.CUTOUT) {
            BlockRenderLayerMap.INSTANCE.putBlock(block, RenderLayer.getCutout());
        }

        // A custom sky (sun, stars, Milky Way, parent planets, rings, atmosphere) for every world.
        for (CelestialBody body : CelestialBodies.destinations()) {
            DimensionRenderingRegistry.registerDimensionEffects(InterplanetaryStuff.id(body.id()),
                    new SpaceDimensionEffects(body));
            DimensionRenderingRegistry.registerSkyRenderer(body.worldKey(), new SpaceSkyRenderer(body));
            // No fluffy Earth clouds and no rain or snow in space.
            DimensionRenderingRegistry.registerCloudRenderer(body.worldKey(), context -> {
            });
            DimensionRenderingRegistry.registerWeatherRenderer(body.worldKey(), context -> {
            });
        }

        flightComputerKey = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "key.interplanetary.flight_computer", InputUtil.Type.KEYSYM, GLFW.GLFW_KEY_R,
                "category.interplanetary"));
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            while (flightComputerKey.wasPressed()) {
                if (client.player != null && client.currentScreen == null) {
                    openStarMap();
                }
            }
        });
        StarChartItem.openScreen = InterplanetaryClient::openStarMap;

        HudRenderCallback.EVENT.register(RocketHud::render);

        ScreenshotTour.init();
    }

    public static void openStarMap() {
        MinecraftClient client = MinecraftClient.getInstance();
        RocketEntity rocket = client.player != null && client.player.getVehicle() instanceof RocketEntity r ? r : null;
        client.setScreen(new StarMapScreen(rocket));
    }
}
