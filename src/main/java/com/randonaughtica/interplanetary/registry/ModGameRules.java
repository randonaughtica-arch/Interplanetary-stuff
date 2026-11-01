package com.randonaughtica.interplanetary.registry;

import net.fabricmc.fabric.api.gamerule.v1.GameRuleFactory;
import net.fabricmc.fabric.api.gamerule.v1.GameRuleRegistry;
import net.minecraft.world.GameRules;

public final class ModGameRules {
    /** When true, players without a full space suit run out of air on worlds without a breathable atmosphere. */
    public static final GameRules.Key<GameRules.BooleanRule> SPACE_SUFFOCATION = GameRuleRegistry.register(
            "interplanetarySpaceSuffocation", GameRules.Category.PLAYER, GameRuleFactory.createBooleanRule(true));

    /** When true, rockets need fuel to launch. */
    public static final GameRules.Key<GameRules.BooleanRule> ROCKETS_NEED_FUEL = GameRuleRegistry.register(
            "interplanetaryRocketsNeedFuel", GameRules.Category.MISC, GameRuleFactory.createBooleanRule(true));

    private ModGameRules() {
    }

    public static void init() {
    }
}
