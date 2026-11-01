package com.randonaughtica.interplanetary.mixin.client;

import com.mojang.serialization.Lifecycle;
import net.minecraft.server.integrated.IntegratedServerLoader;
import net.minecraft.world.SaveProperties;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * Vanilla flags every world containing data-driven dimensions (such as the 30 worlds of this mod) as
 * "experimental" and shows a warning screen whenever such a world is created or opened. The dimensions
 * are safe, so the warning is skipped.
 */
@Mixin(IntegratedServerLoader.class)
public abstract class IntegratedServerLoaderMixin {
    @Redirect(method = "*", require = 0, at = @At(value = "INVOKE",
            target = "Lnet/minecraft/world/SaveProperties;getLifecycle()Lcom/mojang/serialization/Lifecycle;"))
    private Lifecycle interplanetary$loadWithoutWarning(SaveProperties properties) {
        return Lifecycle.stable();
    }

    @ModifyVariable(method = "tryLoad", require = 0, at = @At("HEAD"), argsOnly = true)
    private static Lifecycle interplanetary$createWithoutWarning(Lifecycle lifecycle) {
        return Lifecycle.stable();
    }
}
