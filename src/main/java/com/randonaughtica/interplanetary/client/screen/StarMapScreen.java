package com.randonaughtica.interplanetary.client.screen;

import com.mojang.blaze3d.systems.RenderSystem;
import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.body.StarSystem;
import com.randonaughtica.interplanetary.entity.RocketEntity;
import com.randonaughtica.interplanetary.network.LaunchRocketPayload;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.tooltip.Tooltip;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.OrderedText;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.Identifier;
import net.minecraft.util.Util;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.random.Random;
import org.jetbrains.annotations.Nullable;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * The flight computer: an animated map of the Solar System. Pick a planet system on the left, a
 * destination on the right, and press Launch while seated in a rocket.
 */
@Environment(EnvType.CLIENT)
public class StarMapScreen extends Screen {
    private static final Identifier SUN = InterplanetaryStuff.id("textures/gui/systems/sun.png");
    private static final int PANEL_WIDTH = 160;
    private static final int STAR_COUNT = 220;

    @Nullable
    private final RocketEntity rocket;
    private final int[] stars = new int[STAR_COUNT * 3];
    private final List<Hotspot> hotspots = new ArrayList<>();
    private final List<ButtonWidget> bodyButtons = new ArrayList<>();
    private StarSystem selectedSystem;
    private CelestialBody selectedBody;
    @Nullable
    private ButtonWidget launchButton;

    private record Hotspot(StarSystem system, int x, int y, int radius) {
    }

    public StarMapScreen(@Nullable RocketEntity rocket) {
        super(Text.translatable("screen.interplanetary.star_map"));
        this.rocket = rocket;
        MinecraftClient minecraft = MinecraftClient.getInstance();
        CelestialBody here = minecraft.world != null ? CelestialBodies.byWorld(minecraft.world) : null;
        this.selectedBody = here != null ? here : CelestialBodies.EARTH;
        StarSystem system = CelestialBodies.systemOf(selectedBody);
        this.selectedSystem = system != null ? system : CelestialBodies.systems().get(2);
        // When sitting in a rocket, suggest the first destination that is not the current world.
        if (rocket != null && here != null) {
            for (String id : selectedSystem.bodies()) {
                if (!id.equals(here.id())) {
                    this.selectedBody = CelestialBodies.get(id);
                    break;
                }
            }
        }
    }

    @Override
    protected void init() {
        Random random = Random.create(42L);
        for (int i = 0; i < STAR_COUNT; i++) {
            stars[i * 3] = random.nextInt(Math.max(1, width));
            stars[i * 3 + 1] = random.nextInt(Math.max(1, height));
            stars[i * 3 + 2] = 0x40 + random.nextInt(0xA0);
        }

        int panelX = width - PANEL_WIDTH + 6;
        int buttonWidth = PANEL_WIDTH - 12;
        bodyButtons.clear();
        int y = 58;
        for (String id : selectedSystem.bodies()) {
            CelestialBody body = CelestialBodies.get(id);
            if (body == null) {
                continue;
            }
            Text label = Text.literal("    ").append(body.displayName());
            if (body == selectedBody) {
                label = Text.literal("    ").append(body.displayName().copy().formatted(Formatting.YELLOW));
            }
            ButtonWidget button = ButtonWidget.builder(label, b -> {
                        selectedBody = body;
                        clearAndInit();
                    })
                    .dimensions(panelX, y, buttonWidth, 16)
                    .tooltip(Tooltip.of(body.description()))
                    .build();
            addDrawableChild(button);
            bodyButtons.add(button);
            y += 18;
        }

        launchButton = ButtonWidget.builder(Text.translatable("screen.interplanetary.launch"), b -> launch())
                .dimensions(panelX, height - 26, buttonWidth, 20)
                .build();
        launchButton.active = canLaunch();
        if (!launchButton.active) {
            launchButton.setTooltip(Tooltip.of(launchProblem()));
        }
        addDrawableChild(launchButton);
    }

    // ------------------------------------------------------------------ launching

    private boolean isSeated() {
        return rocket != null && client != null && client.player != null && client.player.getVehicle() == rocket
                && rocket.isAlive() && rocket.getState() == RocketEntity.State.IDLE;
    }

    @Nullable
    private CelestialBody currentBody() {
        return client != null && client.world != null ? CelestialBodies.byWorld(client.world) : null;
    }

    private boolean canLaunch() {
        return isSeated() && selectedBody != currentBody() && selectedBody.tier() <= rocket.getTier();
    }

    private Text launchProblem() {
        if (!isSeated()) {
            return Text.translatable("screen.interplanetary.problem.not_seated");
        }
        if (selectedBody == currentBody()) {
            return Text.translatable("screen.interplanetary.problem.here");
        }
        return Text.translatable("screen.interplanetary.problem.tier", selectedBody.tier());
    }

    private void launch() {
        if (canLaunch()) {
            ClientPlayNetworking.send(new LaunchRocketPayload(selectedBody.id()));
            close();
        }
    }

    // ------------------------------------------------------------------ input

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        for (Hotspot spot : hotspots) {
            double dx = mouseX - spot.x();
            double dy = mouseY - spot.y();
            if (dx * dx + dy * dy <= (spot.radius() + 3) * (spot.radius() + 3)) {
                selectedSystem = spot.system();
                selectedBody = CelestialBodies.get(spot.system().bodies().get(0));
                clearAndInit();
                return true;
            }
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean shouldPause() {
        return false;
    }

    // ------------------------------------------------------------------ drawing

    @Override
    public void renderBackground(DrawContext context, int mouseX, int mouseY, float delta) {
        context.fill(0, 0, width, height, 0xFF04050B);
        long time = Util.getMeasuringTimeMs();
        for (int i = 0; i < STAR_COUNT; i++) {
            int x = stars[i * 3];
            int y = stars[i * 3 + 1];
            int base = stars[i * 3 + 2];
            int b = MathHelper.clamp(base + (int) (30 * Math.sin(time / 700.0 + i)), 0, 255);
            context.fill(x, y, x + 1, y + 1, 0xFF000000 | b << 16 | b << 8 | Math.min(255, b + 20));
        }
        context.fill(width - PANEL_WIDTH, 0, width, height, 0xC0101420);
        context.fill(width - PANEL_WIDTH, 0, width - PANEL_WIDTH + 1, height, 0xFF3A4A6A);
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        super.render(context, mouseX, mouseY, delta);
        drawMap(context, mouseX, mouseY);
        drawPanel(context);
    }

    private void drawMap(DrawContext context, int mouseX, int mouseY) {
        int mapWidth = width - PANEL_WIDTH;
        int cx = mapWidth / 2;
        int cy = height / 2 + 6;
        int maxRadius = Math.max(40, Math.min(mapWidth / 2, height / 2) - 16);
        List<StarSystem> systems = CelestialBodies.systems();
        double seconds = Util.getMeasuringTimeMs() / 1000.0;

        context.drawCenteredTextWithShadow(textRenderer, title.copy().formatted(Formatting.BOLD), cx, 8, 0xFFE8C070);

        // Sun
        RenderSystem.enableBlend();
        context.drawTexture(SUN, cx - 9, cy - 9, 18, 18, 0, 0, 32, 32, 32, 32);

        hotspots.clear();
        StarSystem hovered = null;
        int count = systems.size();
        for (StarSystem system : systems) {
            int radius = 16 + (int) ((maxRadius - 16) * (system.orbit() + 1) / (double) count);
            boolean belt = system.id().equals("asteroids") || system.id().equals("kuiper");
            drawOrbit(context, cx, cy, radius, belt, system == selectedSystem);

            double speed = 0.25 / Math.pow(system.orbit() + 1, 1.2);
            double angle = system.orbit() * 2.39996 + seconds * speed;
            int x = cx + (int) Math.round(Math.cos(angle) * radius);
            int y = cy + (int) Math.round(Math.sin(angle) * radius);
            int iconRadius = switch (system.id()) {
                case "jupiter", "saturn" -> 8;
                case "uranus", "neptune" -> 7;
                case "asteroids", "kuiper" -> 6;
                default -> 5;
            };
            context.drawTexture(system.icon(), x - iconRadius, y - iconRadius, iconRadius * 2, iconRadius * 2,
                    0, 0, 32, 32, 32, 32);
            hotspots.add(new Hotspot(system, x, y, iconRadius));

            boolean isHovered = (mouseX - x) * (mouseX - x) + (mouseY - y) * (mouseY - y) <= (iconRadius + 3) * (iconRadius + 3);
            if (isHovered) {
                hovered = system;
            }
            if (system == selectedSystem || isHovered) {
                drawCircle(context, x, y, iconRadius + 3, system == selectedSystem ? 0xFFFFD060 : 0xAAFFFFFF);
            }
        }
        RenderSystem.disableBlend();

        if (hovered != null) {
            context.drawTooltip(textRenderer, hovered.displayName(), mouseX, mouseY);
        }

        // Rocket status
        Text status;
        if (isSeated()) {
            status = Text.translatable("screen.interplanetary.rocket_status", rocket.getTier(), rocket.getFuel(),
                    RocketEntity.MAX_FUEL).formatted(Formatting.AQUA);
        } else {
            status = Text.translatable("screen.interplanetary.view_only").formatted(Formatting.GRAY);
        }
        context.drawTextWithShadow(textRenderer, status, 6, height - 14, 0xFFFFFF);
        CelestialBody here = currentBody();
        if (here != null) {
            context.drawTextWithShadow(textRenderer,
                    Text.translatable("screen.interplanetary.you_are_here", here.displayName()).formatted(Formatting.GREEN),
                    6, height - 26, 0xFFFFFF);
        }
    }

    private void drawPanel(DrawContext context) {
        int x = width - PANEL_WIDTH + 6;
        int textWidth = PANEL_WIDTH - 12;
        context.drawTextWithShadow(textRenderer, selectedSystem.displayName().copy().formatted(Formatting.GOLD, Formatting.BOLD), x, 8, 0xFFFFFF);
        int y = 20;
        for (OrderedText line : textRenderer.wrapLines(selectedSystem.description(), textWidth)) {
            if (y > 48) {
                break;
            }
            context.drawText(textRenderer, line, x, y, 0xFFB8C0D0, false);
            y += 9;
        }

        // Body icons on the destination buttons.
        RenderSystem.enableBlend();
        int i = 0;
        for (String id : selectedSystem.bodies()) {
            CelestialBody body = CelestialBodies.get(id);
            if (body == null || i >= bodyButtons.size()) {
                continue;
            }
            ButtonWidget button = bodyButtons.get(i++);
            context.drawTexture(body.texture(), button.getX() + 3, button.getY() + 2, 12, 12, 0, 0, 128, 128, 128, 128);
            if (body.tier() > 1) {
                Text tier = Text.literal("T" + body.tier());
                boolean reachable = rocket == null || body.tier() <= rocket.getTier();
                context.drawTextWithShadow(textRenderer, tier, button.getX() + button.getWidth() - textRenderer.getWidth(tier) - 4,
                        button.getY() + 4, reachable ? 0xFF90E090 : 0xFFFF7070);
            }
        }
        RenderSystem.disableBlend();

        // Facts about the selected destination.
        y = 58 + selectedSystem.bodies().size() * 18 + 4;
        CelestialBody body = selectedBody;
        List<Text> facts = new ArrayList<>();
        facts.add(body.displayName().copy().formatted(Formatting.YELLOW, Formatting.BOLD));
        facts.add(Text.translatable(body.type().translationKey()).formatted(Formatting.GRAY));
        facts.add(Text.translatable("screen.interplanetary.gravity", String.format(Locale.ROOT, "%.3f", body.gravity())));
        facts.add(Text.translatable("screen.interplanetary.temperature", body.temperature()));
        facts.add(Text.translatable("screen.interplanetary.atmosphere", Text.translatable(body.atmosphere().translationKey())));
        if (!body.isEarth()) {
            facts.add(Text.translatable("screen.interplanetary.requirements", body.tier(), body.fuelCost()));
        }
        if (body.requiresSpaceSuit()) {
            facts.add(Text.translatable("screen.interplanetary.suit_required").formatted(Formatting.RED));
        }
        for (Text fact : facts) {
            if (y > height - 38) {
                break;
            }
            context.drawTextWithShadow(textRenderer, fact, x, y, 0xFFE0E0E0);
            y += 10;
        }
        if (isSeated() && !body.isEarth() && rocket.getFuel() < body.fuelCost() && client != null
                && client.player != null && !client.player.isCreative()) {
            context.drawTextWithShadow(textRenderer, Text.translatable("screen.interplanetary.low_fuel").formatted(Formatting.RED),
                    x, height - 38, 0xFFFFFF);
        }
    }

    private static void drawOrbit(DrawContext context, int cx, int cy, int radius, boolean belt, boolean selected) {
        int steps = Math.max(24, (int) (radius * 2.2));
        Random random = Random.create(radius * 31L);
        for (int k = 0; k < steps; k++) {
            double a = k * Math.PI * 2.0 / steps;
            if (belt) {
                for (int j = 0; j < 2; j++) {
                    double r = radius + random.nextGaussian() * 2.0;
                    double aa = a + random.nextDouble() * 0.05;
                    int px = cx + (int) Math.round(Math.cos(aa) * r);
                    int py = cy + (int) Math.round(Math.sin(aa) * r);
                    context.fill(px, py, px + 1, py + 1, 0x70A8A090);
                }
            } else if (k % 2 == 0) {
                int px = cx + (int) Math.round(Math.cos(a) * radius);
                int py = cy + (int) Math.round(Math.sin(a) * radius);
                context.fill(px, py, px + 1, py + 1, selected ? 0x90FFD060 : 0x40A0B0D0);
            }
        }
    }

    private static void drawCircle(DrawContext context, int cx, int cy, int radius, int color) {
        int steps = radius * 8;
        for (int k = 0; k < steps; k++) {
            double a = k * Math.PI * 2.0 / steps;
            int px = cx + (int) Math.round(Math.cos(a) * radius);
            int py = cy + (int) Math.round(Math.sin(a) * radius);
            context.fill(px, py, px + 1, py + 1, color);
        }
    }
}
