package com.randonaughtica.interplanetary.client.render;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.client.render.OverlayTexture;
import net.minecraft.client.render.VertexConsumer;
import net.minecraft.client.render.VertexConsumerProvider;
import net.minecraft.client.render.entity.EntityRenderer;
import net.minecraft.client.render.entity.EntityRendererFactory;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.RotationAxis;

@Environment(EnvType.CLIENT)
public class RocketEntityRenderer extends EntityRenderer<RocketEntity> {
    private static final Identifier[] TEXTURES = {
            InterplanetaryStuff.id("textures/entity/rocket/tier_1.png"),
            InterplanetaryStuff.id("textures/entity/rocket/tier_2.png"),
            InterplanetaryStuff.id("textures/entity/rocket/tier_3.png")
    };

    private final RocketEntityModel model;

    public RocketEntityRenderer(EntityRendererFactory.Context context) {
        super(context);
        this.model = new RocketEntityModel(context.getPart(RocketEntityModel.LAYER));
        this.shadowRadius = 0.9F;
    }

    @Override
    public void render(RocketEntity entity, float yaw, float tickDelta, MatrixStack matrices,
                       VertexConsumerProvider vertexConsumers, int light) {
        matrices.push();
        matrices.multiply(RotationAxis.POSITIVE_Y.rotationDegrees(180.0F - yaw));
        if (entity.getState() == RocketEntity.State.COUNTDOWN) {
            // The rocket rumbles harder as the countdown runs out.
            float strength = MathHelper.clamp((entity.getStateTicks() + tickDelta) / RocketEntity.COUNTDOWN_TICKS, 0.0F, 1.0F);
            float shake = strength * 0.05F;
            matrices.translate((entity.getRandom().nextFloat() - 0.5F) * shake, 0.0F,
                    (entity.getRandom().nextFloat() - 0.5F) * shake);
        }
        matrices.scale(-1.0F, -1.0F, 1.0F);
        VertexConsumer consumer = vertexConsumers.getBuffer(model.getLayer(getTexture(entity)));
        model.render(matrices, consumer, light, OverlayTexture.DEFAULT_UV, 0xFFFFFFFF);
        matrices.pop();
        super.render(entity, yaw, tickDelta, matrices, vertexConsumers, light);
    }

    @Override
    public Identifier getTexture(RocketEntity entity) {
        return TEXTURES[MathHelper.clamp(entity.getTier(), 1, 3) - 1];
    }
}
