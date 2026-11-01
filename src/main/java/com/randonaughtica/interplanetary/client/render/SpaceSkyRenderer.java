package com.randonaughtica.interplanetary.client.render;

import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.body.SkyObject;
import com.randonaughtica.interplanetary.body.SkyProfile;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.client.rendering.v1.DimensionRenderingRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.WorldRenderContext;
import net.minecraft.block.enums.CameraSubmersionType;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.render.BufferBuilder;
import net.minecraft.client.render.BufferRenderer;
import net.minecraft.client.render.BuiltBuffer;
import net.minecraft.client.render.GameRenderer;
import net.minecraft.client.render.Tessellator;
import net.minecraft.client.render.VertexFormat;
import net.minecraft.client.render.VertexFormats;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.RotationAxis;
import net.minecraft.util.math.random.Random;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * Draws the sky of a space world: a Milky Way skybox, twinkling stars, the sun (sized by its distance),
 * optional atmosphere colours, and planets/moons with phases and rings.
 */
@Environment(EnvType.CLIENT)
public class SpaceSkyRenderer implements DimensionRenderingRegistry.SkyRenderer {
    private static final Identifier[] SKYBOX = new Identifier[6];
    private static final Identifier SUN_GLOW = InterplanetaryStuff.id("textures/environment/sun_glow.png");
    private static final Identifier SUN_CORE = InterplanetaryStuff.id("textures/environment/sun_core.png");
    private static final Identifier PHASES = InterplanetaryStuff.id("textures/environment/phases.png");
    private static final int PHASE_GRID = 4;
    private static final int PHASE_FRAMES = PHASE_GRID * PHASE_GRID;
    private static final float DISTANCE = 100.0F;

    /** Must match the galactic plane used by tools/generate.py for the skybox. */
    private static final Vector3f GALACTIC_NORMAL = new Vector3f(0.30F, 0.55F, 0.78F).normalize();

    private static final int STAR_COUNT = 2400;
    private static final float[] STAR_VERTICES = new float[STAR_COUNT * 12];
    private static final float[] STAR_COLORS = new float[STAR_COUNT * 4];
    private static final float[] STAR_TWINKLE = new float[STAR_COUNT];

    static {
        for (int i = 0; i < 6; i++) {
            SKYBOX[i] = InterplanetaryStuff.id("textures/environment/space/skybox_" + i + ".png");
        }
        buildStars();
    }

    private final SkyProfile sky;

    public SpaceSkyRenderer(CelestialBody body) {
        this.sky = body.sky();
    }

    @Override
    public void render(WorldRenderContext context) {
        ClientWorld world = context.world();
        if (world == null) {
            return;
        }
        CameraSubmersionType submersion = context.camera().getSubmersionType();
        if (submersion == CameraSubmersionType.LAVA || submersion == CameraSubmersionType.POWDER_SNOW) {
            return;
        }
        float tickDelta = context.tickCounter().getTickDelta(false);
        float time = world.getTime() + tickDelta;

        MatrixStack matrices = new MatrixStack();
        matrices.multiplyPositionMatrix(context.positionMatrix());

        float skyAngle = world.getSkyAngle(tickDelta);
        float angle = skyAngle * MathHelper.TAU;
        Vector3f sunDir = new Vector3f(-MathHelper.sin(angle), MathHelper.cos(angle), 0.0F);
        float daylight = MathHelper.clamp(sunDir.y * 2.5F + 0.5F, 0.0F, 1.0F);
        float atmosphere = MathHelper.lerp(daylight, sky.nightAlpha(), sky.dayAlpha());

        RenderSystem.depthMask(false);
        RenderSystem.disableCull();
        RenderSystem.enableBlend();

        // 1. Milky Way and stars, turning with the sky.
        float starAlpha = sky.starBrightness() * (1.0F - atmosphere);
        if (starAlpha > 0.01F) {
            additive();
            matrices.push();
            matrices.multiply(RotationAxis.POSITIVE_Y.rotationDegrees(-90.0F));
            matrices.multiply(RotationAxis.POSITIVE_X.rotationDegrees(skyAngle * 360.0F));
            drawSkybox(matrices, starAlpha);
            drawStars(matrices.peek().getPositionMatrix(), starAlpha, time);
            matrices.pop();
        }

        Matrix4f matrix = matrices.peek().getPositionMatrix();

        // 2. Atmosphere.
        if (atmosphere > 0.01F) {
            RenderSystem.defaultBlendFunc();
            drawAtmosphere(matrix, daylight, atmosphere);
        }

        // 3. The sun, plus a sunset glow on worlds with an atmosphere.
        additive();
        drawSun(matrix, sunDir, atmosphere);

        // 4. Planets and moons.
        RenderSystem.defaultBlendFunc();
        float objectAlpha = 1.0F - atmosphere * 0.85F;
        if (objectAlpha > 0.02F) {
            for (SkyObject object : sky.objects()) {
                drawObject(matrix, object, sunDir, objectAlpha, time);
            }
        }

        RenderSystem.setShaderColor(1.0F, 1.0F, 1.0F, 1.0F);
        RenderSystem.defaultBlendFunc();
        RenderSystem.disableBlend();
        RenderSystem.enableCull();
        RenderSystem.depthMask(true);
    }

    // ------------------------------------------------------------------ layers

    private static void drawSkybox(MatrixStack matrices, float alpha) {
        RenderSystem.setShader(GameRenderer::getPositionTexColorProgram);
        for (int i = 0; i < 6; i++) {
            bilinear(SKYBOX[i]);
            RenderSystem.setShaderTexture(0, SKYBOX[i]);
            matrices.push();
            switch (i) {
                case 1 -> matrices.multiply(RotationAxis.POSITIVE_X.rotationDegrees(90.0F));
                case 2 -> matrices.multiply(RotationAxis.POSITIVE_X.rotationDegrees(-90.0F));
                case 3 -> matrices.multiply(RotationAxis.POSITIVE_X.rotationDegrees(180.0F));
                case 4 -> matrices.multiply(RotationAxis.POSITIVE_Z.rotationDegrees(90.0F));
                case 5 -> matrices.multiply(RotationAxis.POSITIVE_Z.rotationDegrees(-90.0F));
                default -> {
                }
            }
            Matrix4f m = matrices.peek().getPositionMatrix();
            BufferBuilder buffer = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_TEXTURE_COLOR);
            buffer.vertex(m, -100.0F, -100.0F, -100.0F).texture(0.0F, 0.0F).color(1.0F, 1.0F, 1.0F, alpha);
            buffer.vertex(m, -100.0F, -100.0F, 100.0F).texture(0.0F, 1.0F).color(1.0F, 1.0F, 1.0F, alpha);
            buffer.vertex(m, 100.0F, -100.0F, 100.0F).texture(1.0F, 1.0F).color(1.0F, 1.0F, 1.0F, alpha);
            buffer.vertex(m, 100.0F, -100.0F, -100.0F).texture(1.0F, 0.0F).color(1.0F, 1.0F, 1.0F, alpha);
            draw(buffer);
            matrices.pop();
        }
    }

    private static void drawStars(Matrix4f matrix, float alpha, float time) {
        RenderSystem.setShader(GameRenderer::getPositionColorProgram);
        BufferBuilder buffer = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_COLOR);
        for (int i = 0; i < STAR_COUNT; i++) {
            float twinkle = 0.78F + 0.22F * MathHelper.sin(time * 0.07F * (0.5F + STAR_TWINKLE[i]) + STAR_TWINKLE[i] * 40.0F);
            float a = alpha * STAR_COLORS[i * 4 + 3] * twinkle;
            float r = STAR_COLORS[i * 4];
            float g = STAR_COLORS[i * 4 + 1];
            float b = STAR_COLORS[i * 4 + 2];
            for (int v = 0; v < 4; v++) {
                int o = i * 12 + v * 3;
                buffer.vertex(matrix, STAR_VERTICES[o], STAR_VERTICES[o + 1], STAR_VERTICES[o + 2]).color(r, g, b, a);
            }
        }
        draw(buffer);
    }

    private void drawAtmosphere(Matrix4f m, float daylight, float alpha) {
        float night = 0.05F;
        float k = MathHelper.lerp(daylight, night, 1.0F);
        float zr = red(sky.dayZenith()) * k, zg = green(sky.dayZenith()) * k, zb = blue(sky.dayZenith()) * k;
        float hr = red(sky.dayHorizon()) * k, hg = green(sky.dayHorizon()) * k, hb = blue(sky.dayHorizon()) * k;
        float gr = hr * 0.55F, gg = hg * 0.55F, gb = hb * 0.55F;
        float s = 100.0F;

        RenderSystem.setShader(GameRenderer::getPositionColorProgram);
        BufferBuilder buffer = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_COLOR);
        // top
        buffer.vertex(m, -s, s, -s).color(zr, zg, zb, alpha);
        buffer.vertex(m, s, s, -s).color(zr, zg, zb, alpha);
        buffer.vertex(m, s, s, s).color(zr, zg, zb, alpha);
        buffer.vertex(m, -s, s, s).color(zr, zg, zb, alpha);
        // bottom
        buffer.vertex(m, -s, -s, -s).color(gr, gg, gb, alpha);
        buffer.vertex(m, -s, -s, s).color(gr, gg, gb, alpha);
        buffer.vertex(m, s, -s, s).color(gr, gg, gb, alpha);
        buffer.vertex(m, s, -s, -s).color(gr, gg, gb, alpha);
        float[][] corners = {{-s, -s}, {s, -s}, {s, s}, {-s, s}, {-s, -s}};
        for (int i = 0; i < 4; i++) {
            float x0 = corners[i][0], z0 = corners[i][1], x1 = corners[i + 1][0], z1 = corners[i + 1][1];
            // upper half: zenith -> horizon
            buffer.vertex(m, x0, s, z0).color(zr, zg, zb, alpha);
            buffer.vertex(m, x0, 0.0F, z0).color(hr, hg, hb, alpha);
            buffer.vertex(m, x1, 0.0F, z1).color(hr, hg, hb, alpha);
            buffer.vertex(m, x1, s, z1).color(zr, zg, zb, alpha);
            // lower half: horizon -> ground
            buffer.vertex(m, x0, 0.0F, z0).color(hr, hg, hb, alpha);
            buffer.vertex(m, x0, -s, z0).color(gr, gg, gb, alpha);
            buffer.vertex(m, x1, -s, z1).color(gr, gg, gb, alpha);
            buffer.vertex(m, x1, 0.0F, z1).color(hr, hg, hb, alpha);
        }
        draw(buffer);
    }

    private void drawSun(Matrix4f m, Vector3f sunDir, float atmosphere) {
        float horizonFade = MathHelper.clamp((sunDir.y + 0.12F) * 6.0F, 0.0F, 1.0F);
        if (horizonFade <= 0.0F) {
            return;
        }
        float occlusion = sky.sunOcclusion();
        float r = red(sky.sunColor()), g = green(sky.sunColor()), b = blue(sky.sunColor());
        float size = sky.sunSize();

        RenderSystem.setShader(GameRenderer::getPositionTexColorProgram);
        bilinear(SUN_GLOW);
        RenderSystem.setShaderTexture(0, SUN_GLOW);
        BufferBuilder glow = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_TEXTURE_COLOR);
        billboard(glow, m, sunDir, size * 3.2F + 8.0F, 0.0F, r, g, b, 0.85F * (1.0F - occlusion * 0.45F) * horizonFade, 0, 0, 1, 1);
        // Blue (Mars) or golden sunsets on worlds with an atmosphere.
        if (sky.sunsetColor() != 0 && atmosphere > 0.05F) {
            float low = MathHelper.clamp(1.0F - Math.abs(sunDir.y) * 4.0F, 0.0F, 1.0F);
            if (low > 0.0F) {
                billboard(glow, m, sunDir, size * 4.0F + 30.0F, 0.0F, red(sky.sunsetColor()), green(sky.sunsetColor()),
                        blue(sky.sunsetColor()), 0.7F * low * horizonFade, 0, 0, 1, 1);
            }
        }
        draw(glow);

        float coreAlpha = (1.0F - occlusion) * horizonFade;
        if (coreAlpha > 0.01F) {
            bilinear(SUN_CORE);
            RenderSystem.setShaderTexture(0, SUN_CORE);
            BufferBuilder core = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_TEXTURE_COLOR);
            billboard(core, m, sunDir, size, 0.0F, 1.0F, 1.0F, 1.0F, coreAlpha, 0, 0, 1, 1);
            draw(core);
        }
    }

    private static void drawObject(Matrix4f m, SkyObject object, Vector3f sunDir, float alpha, float time) {
        Vector3f dir = direction(object, time);
        float size = object.size();
        SkyObject.Ring ring = object.ring();

        // Far half of the rings goes behind the planet.
        if (ring != null) {
            drawRingHalf(m, dir, size, ring, alpha, false);
        }

        bilinear(object.texture());
        RenderSystem.setShader(GameRenderer::getPositionTexColorProgram);
        RenderSystem.setShaderTexture(0, object.texture());
        BufferBuilder planet = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_TEXTURE_COLOR);
        billboard(planet, m, dir, size, 0.0F, 1.0F, 1.0F, 1.0F, alpha, 0, 0, 1, 1);
        draw(planet);

        if (object.phases()) {
            // Angle between "planet -> observer" and "planet -> sun" decides how much of the disc is lit.
            float cosPhase = MathHelper.clamp(-dir.dot(sunDir), -1.0F, 1.0F);
            float phase = (float) Math.acos(cosPhase);
            int frame = Math.round(phase / MathHelper.PI * (PHASE_FRAMES - 1));
            if (frame > 0) {
                // Rotate the shadow so the lit limb faces the sun.
                Vector3f projected = new Vector3f(sunDir).sub(new Vector3f(dir).mul(sunDir.dot(dir)));
                Vector3f[] basis = basis(dir);
                float roll = projected.lengthSquared() < 1.0E-6F ? 0.0F
                        : (float) Math.atan2(projected.dot(basis[1]), projected.dot(basis[0]));
                float u0 = (frame % PHASE_GRID) / (float) PHASE_GRID;
                float v0 = (frame / PHASE_GRID) / (float) PHASE_GRID;
                float cell = 1.0F / PHASE_GRID;
                RenderSystem.setShaderTexture(0, PHASES);
                BufferBuilder shadow = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_TEXTURE_COLOR);
                billboard(shadow, m, dir, size * 1.003F, roll, 1.0F, 1.0F, 1.0F, alpha, u0, v0, u0 + cell, v0 + cell);
                draw(shadow);
            }
        }

        if (ring != null) {
            drawRingHalf(m, dir, size, ring, alpha, true);
        }
    }

    private static void drawRingHalf(Matrix4f m, Vector3f dir, float size, SkyObject.Ring ring, float alpha, boolean near) {
        Vector3f[] basis = rolled(basis(dir), ring.roll() * MathHelper.RADIANS_PER_DEGREE);
        float radius = size * ring.scale();
        float squash = MathHelper.sin(ring.tilt() * MathHelper.RADIANS_PER_DEGREE);
        Vector3f center = new Vector3f(dir).normalize().mul(DISTANCE);
        Vector3f major = new Vector3f(basis[0]).mul(radius);
        // Near side of the ring is drawn below the planet's centre.
        Vector3f minor = new Vector3f(basis[1]).mul(-radius * squash);
        float b0 = near ? 0.0F : -1.0F;
        float b1 = near ? 1.0F : 0.0F;

        bilinear(ring.texture());
        RenderSystem.setShader(GameRenderer::getPositionTexColorProgram);
        RenderSystem.setShaderTexture(0, ring.texture());
        BufferBuilder buffer = Tessellator.getInstance().begin(VertexFormat.DrawMode.QUADS, VertexFormats.POSITION_TEXTURE_COLOR);
        float a = alpha * ring.alpha();
        ringVertex(buffer, m, center, major, minor, -1.0F, b0, a);
        ringVertex(buffer, m, center, major, minor, -1.0F, b1, a);
        ringVertex(buffer, m, center, major, minor, 1.0F, b1, a);
        ringVertex(buffer, m, center, major, minor, 1.0F, b0, a);
        draw(buffer);
    }

    private static void ringVertex(BufferBuilder buffer, Matrix4f m, Vector3f center, Vector3f major, Vector3f minor,
                                   float a, float b, float alpha) {
        float x = center.x + major.x * a + minor.x * b;
        float y = center.y + major.y * a + minor.y * b;
        float z = center.z + major.z * a + minor.z * b;
        buffer.vertex(m, x, y, z).texture((a + 1.0F) * 0.5F, (b + 1.0F) * 0.5F).color(1.0F, 1.0F, 1.0F, alpha);
    }

    // ------------------------------------------------------------------ geometry helpers

    /** Direction of a sky object at the given world time. */
    private static Vector3f direction(SkyObject object, float time) {
        if (object.isFixed()) {
            float az = object.azimuth() * MathHelper.RADIANS_PER_DEGREE;
            float el = object.elevation() * MathHelper.RADIANS_PER_DEGREE;
            return new Vector3f(MathHelper.cos(el) * MathHelper.sin(az), MathHelper.sin(el),
                    -MathHelper.cos(el) * MathHelper.cos(az));
        }
        float a = (time / object.orbitPeriod() + object.orbitPhase()) * MathHelper.TAU;
        float inclination = object.orbitInclination() * MathHelper.RADIANS_PER_DEGREE;
        float c = MathHelper.cos(a);
        return new Vector3f(-MathHelper.sin(a), c * MathHelper.cos(inclination), c * MathHelper.sin(inclination));
    }

    /** [screen-right, screen-up] for a billboard facing the camera along {@code dir}. */
    private static Vector3f[] basis(Vector3f dir) {
        Vector3f d = new Vector3f(dir).normalize();
        Vector3f worldUp = Math.abs(d.y) > 0.995F ? new Vector3f(0.0F, 0.0F, -1.0F) : new Vector3f(0.0F, 1.0F, 0.0F);
        Vector3f right = new Vector3f(d).cross(worldUp).normalize();
        Vector3f up = new Vector3f(right).cross(d).normalize();
        return new Vector3f[]{right, up};
    }

    private static Vector3f[] rolled(Vector3f[] basis, float roll) {
        if (roll == 0.0F) {
            return basis;
        }
        float c = MathHelper.cos(roll);
        float s = MathHelper.sin(roll);
        Vector3f right = new Vector3f(basis[0]).mul(c).add(new Vector3f(basis[1]).mul(s));
        Vector3f up = new Vector3f(basis[1]).mul(c).sub(new Vector3f(basis[0]).mul(s));
        return new Vector3f[]{right, up};
    }

    private static void billboard(BufferBuilder buffer, Matrix4f m, Vector3f dir, float size, float roll,
                                  float r, float g, float b, float a, float u0, float v0, float u1, float v1) {
        Vector3f[] basis = rolled(basis(dir), roll);
        Vector3f right = basis[0].mul(size);
        Vector3f up = basis[1].mul(size);
        Vector3f c = new Vector3f(dir).normalize().mul(DISTANCE);
        buffer.vertex(m, c.x - right.x + up.x, c.y - right.y + up.y, c.z - right.z + up.z).texture(u0, v0).color(r, g, b, a);
        buffer.vertex(m, c.x - right.x - up.x, c.y - right.y - up.y, c.z - right.z - up.z).texture(u0, v1).color(r, g, b, a);
        buffer.vertex(m, c.x + right.x - up.x, c.y + right.y - up.y, c.z + right.z - up.z).texture(u1, v1).color(r, g, b, a);
        buffer.vertex(m, c.x + right.x + up.x, c.y + right.y + up.y, c.z + right.z + up.z).texture(u1, v0).color(r, g, b, a);
    }

    // ------------------------------------------------------------------ stars

    private static void buildStars() {
        Random random = Random.create(20240611L);
        Vector3f n = GALACTIC_NORMAL;
        Vector3f a = new Vector3f(n).cross(new Vector3f(0.0F, 1.0F, 0.0F)).normalize();
        Vector3f b = new Vector3f(n).cross(a).normalize();
        float[][] palette = {
                {0.70F, 0.80F, 1.00F}, {0.85F, 0.90F, 1.00F}, {1.00F, 1.00F, 1.00F},
                {1.00F, 0.96F, 0.85F}, {1.00F, 0.88F, 0.70F}, {1.00F, 0.72F, 0.58F}};
        float[] weights = {0.12F, 0.2F, 0.3F, 0.2F, 0.12F, 0.06F};
        for (int i = 0; i < STAR_COUNT; i++) {
            Vector3f dir;
            if (random.nextFloat() < 0.35F) {
                // Concentrate a third of the stars along the Milky Way.
                float phi = random.nextFloat() * MathHelper.TAU;
                float spread = (float) random.nextGaussian() * 0.12F;
                dir = new Vector3f(a).mul(MathHelper.cos(phi)).add(new Vector3f(b).mul(MathHelper.sin(phi)))
                        .add(new Vector3f(n).mul(spread));
            } else {
                float x;
                float y;
                float z;
                float len;
                do {
                    x = random.nextFloat() * 2.0F - 1.0F;
                    y = random.nextFloat() * 2.0F - 1.0F;
                    z = random.nextFloat() * 2.0F - 1.0F;
                    len = x * x + y * y + z * z;
                } while (len >= 1.0F || len < 0.01F);
                dir = new Vector3f(x, y, z);
            }
            dir.normalize(DISTANCE);
            float t = random.nextFloat();
            float size = 0.10F + t * t * t * 0.38F;
            float rotation = random.nextFloat() * MathHelper.TAU;
            Quaternionf q = new Quaternionf().rotateTo(new Vector3f(0.0F, 0.0F, -1.0F), dir).rotateZ(rotation);
            float[][] corners = {{size, -size}, {size, size}, {-size, size}, {-size, -size}};
            for (int v = 0; v < 4; v++) {
                Vector3f corner = new Vector3f(corners[v][0], corners[v][1], 0.0F).rotate(q).add(dir);
                STAR_VERTICES[i * 12 + v * 3] = corner.x;
                STAR_VERTICES[i * 12 + v * 3 + 1] = corner.y;
                STAR_VERTICES[i * 12 + v * 3 + 2] = corner.z;
            }
            float pick = random.nextFloat();
            int color = 0;
            while (color < weights.length - 1 && pick > weights[color]) {
                pick -= weights[color];
                color++;
            }
            STAR_COLORS[i * 4] = palette[color][0];
            STAR_COLORS[i * 4 + 1] = palette[color][1];
            STAR_COLORS[i * 4 + 2] = palette[color][2];
            STAR_COLORS[i * 4 + 3] = 0.35F + random.nextFloat() * 0.65F;
            STAR_TWINKLE[i] = random.nextFloat();
        }
    }

    // ------------------------------------------------------------------ misc

    private static void additive() {
        RenderSystem.blendFuncSeparate(GlStateManager.SrcFactor.SRC_ALPHA, GlStateManager.DstFactor.ONE,
                GlStateManager.SrcFactor.ONE, GlStateManager.DstFactor.ZERO);
    }

    private static void bilinear(Identifier texture) {
        MinecraftClient.getInstance().getTextureManager().getTexture(texture).setFilter(true, false);
    }

    private static void draw(BufferBuilder buffer) {
        BuiltBuffer built = buffer.endNullable();
        if (built != null) {
            BufferRenderer.drawWithGlobalProgram(built);
        }
    }

    private static float red(int rgb) {
        return ((rgb >> 16) & 0xFF) / 255.0F;
    }

    private static float green(int rgb) {
        return ((rgb >> 8) & 0xFF) / 255.0F;
    }

    private static float blue(int rgb) {
        return (rgb & 0xFF) / 255.0F;
    }
}
