package com.randonaughtica.interplanetary.network;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import net.minecraft.network.RegistryByteBuf;
import net.minecraft.network.codec.PacketCodec;
import net.minecraft.network.codec.PacketCodecs;
import net.minecraft.network.packet.CustomPayload;

/** Client → server: "launch the rocket I'm sitting in towards this body". */
public record LaunchRocketPayload(String destination) implements CustomPayload {
    public static final CustomPayload.Id<LaunchRocketPayload> ID =
            new CustomPayload.Id<>(InterplanetaryStuff.id("launch_rocket"));
    public static final PacketCodec<RegistryByteBuf, LaunchRocketPayload> CODEC =
            PacketCodec.tuple(PacketCodecs.STRING, LaunchRocketPayload::destination, LaunchRocketPayload::new);

    @Override
    public Id<? extends CustomPayload> getId() {
        return ID;
    }
}
