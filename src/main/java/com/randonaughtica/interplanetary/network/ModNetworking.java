package com.randonaughtica.interplanetary.network;

import com.randonaughtica.interplanetary.world.SpaceTravel;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;

public final class ModNetworking {
    private ModNetworking() {
    }

    public static void init() {
        PayloadTypeRegistry.playC2S().register(LaunchRocketPayload.ID, LaunchRocketPayload.CODEC);
        ServerPlayNetworking.registerGlobalReceiver(LaunchRocketPayload.ID, (payload, context) ->
                context.server().execute(() -> SpaceTravel.requestLaunch(context.player(), payload.destination())));
    }
}
