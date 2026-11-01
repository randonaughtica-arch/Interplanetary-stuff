package com.randonaughtica.interplanetary.command;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.world.SpaceTravel;
import net.minecraft.command.CommandSource;
import net.minecraft.command.argument.EntityArgumentType;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.text.MutableText;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Vec3d;

import java.util.Collection;
import java.util.List;
import java.util.Locale;

/**
 * {@code /interplanetary travel <destination> [targets]} — instant travel (operators only).<br>
 * {@code /interplanetary info} — facts about the world you are on.<br>
 * {@code /interplanetary destinations} — list every destination.
 */
public final class InterplanetaryCommand {
    private InterplanetaryCommand() {
    }

    public static void register(CommandDispatcher<ServerCommandSource> dispatcher) {
        dispatcher.register(CommandManager.literal("interplanetary")
                .then(CommandManager.literal("travel")
                        .requires(source -> source.hasPermissionLevel(2))
                        .then(CommandManager.argument("destination", StringArgumentType.word())
                                .suggests((context, builder) -> CommandSource.suggestMatching(
                                        CelestialBodies.all().stream().map(CelestialBody::id), builder))
                                .executes(context -> travel(context.getSource(),
                                        StringArgumentType.getString(context, "destination"),
                                        List.of(context.getSource().getPlayerOrThrow())))
                                .then(CommandManager.argument("targets", EntityArgumentType.players())
                                        .executes(context -> travel(context.getSource(),
                                                StringArgumentType.getString(context, "destination"),
                                                EntityArgumentType.getPlayers(context, "targets"))))))
                .then(CommandManager.literal("info")
                        .executes(context -> info(context.getSource())))
                .then(CommandManager.literal("destinations")
                        .executes(context -> destinations(context.getSource()))));
    }

    private static int travel(ServerCommandSource source, String id, Collection<ServerPlayerEntity> players)
            throws CommandSyntaxException {
        CelestialBody body = CelestialBodies.get(id.toLowerCase(Locale.ROOT));
        if (body == null) {
            source.sendError(Text.translatable("commands.interplanetary.unknown", id));
            return 0;
        }
        ServerWorld world = source.getServer().getWorld(body.worldKey());
        if (world == null) {
            source.sendError(Text.translatable("commands.interplanetary.missing_world", id));
            return 0;
        }
        for (ServerPlayerEntity player : players) {
            if (player.hasVehicle()) {
                player.stopRiding();
            }
            BlockPos landing = SpaceTravel.arrivalPoint(player, world, player.getBlockX(), player.getBlockZ());
            SpaceTravel.teleport(player, world, Vec3d.ofBottomCenter(landing));
        }
        source.sendFeedback(() -> Text.translatable("commands.interplanetary.travel", players.size(), body.displayName()), true);
        return players.size();
    }

    private static int info(ServerCommandSource source) {
        CelestialBody body = CelestialBodies.byWorld(source.getWorld());
        if (body == null) {
            source.sendFeedback(() -> Text.translatable("commands.interplanetary.info.not_space"), false);
            return 0;
        }
        source.sendFeedback(() -> body.displayName().copy().formatted(Formatting.GOLD, Formatting.BOLD), false);
        source.sendFeedback(() -> body.description().copy().formatted(Formatting.GRAY), false);
        source.sendFeedback(() -> Text.translatable("screen.interplanetary.gravity",
                String.format(Locale.ROOT, "%.3f", body.gravity())), false);
        source.sendFeedback(() -> Text.translatable("screen.interplanetary.temperature", body.temperature()), false);
        source.sendFeedback(() -> Text.translatable("screen.interplanetary.atmosphere",
                Text.translatable(body.atmosphere().translationKey())), false);
        return 1;
    }

    private static int destinations(ServerCommandSource source) {
        MutableText text = Text.translatable("commands.interplanetary.destinations").formatted(Formatting.GOLD);
        for (CelestialBody body : CelestialBodies.all()) {
            text.append(Text.literal("\n - ").formatted(Formatting.DARK_GRAY))
                    .append(body.displayName().copy().formatted(Formatting.WHITE))
                    .append(Text.literal(" (" + body.id() + ", tier " + body.tier() + ")").formatted(Formatting.GRAY));
        }
        source.sendFeedback(() -> text, false);
        return CelestialBodies.all().size();
    }
}
