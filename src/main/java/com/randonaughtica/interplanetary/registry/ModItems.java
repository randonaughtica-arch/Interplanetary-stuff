package com.randonaughtica.interplanetary.registry;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import com.randonaughtica.interplanetary.item.FuelItem;
import com.randonaughtica.interplanetary.item.RocketItem;
import com.randonaughtica.interplanetary.item.SpaceSuitItem;
import com.randonaughtica.interplanetary.item.StarChartItem;
import com.randonaughtica.interplanetary.item.TooltipItem;
import net.minecraft.component.type.FoodComponent;
import net.minecraft.entity.EquipmentSlot;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.ArmorItem;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.util.Rarity;

import java.util.ArrayList;
import java.util.List;

public final class ModItems {
    /** Every non-block item of the mod, in creative-tab order. */
    public static final List<Item> ITEMS = new ArrayList<>();

    // Navigation
    public static final Item STAR_CHART = register("star_chart", new StarChartItem(new Item.Settings().maxCount(1)));

    // Rockets
    public static final Item ROCKET_TIER_1 = register("rocket_tier_1",
            new RocketItem(1, new Item.Settings().maxCount(1).rarity(Rarity.UNCOMMON)));
    public static final Item ROCKET_TIER_2 = register("rocket_tier_2",
            new RocketItem(2, new Item.Settings().maxCount(1).rarity(Rarity.RARE)));
    public static final Item ROCKET_TIER_3 = register("rocket_tier_3",
            new RocketItem(3, new Item.Settings().maxCount(1).rarity(Rarity.EPIC)));
    public static final Item ROCKET_FUEL = register("rocket_fuel", new FuelItem(new Item.Settings().maxCount(16)));

    // Rocket parts
    public static final Item IRON_PLATING = register("iron_plating", simple());
    public static final Item TITANIUM_PLATING = register("titanium_plating", simple());
    public static final Item IRIDIUM_PLATING = register("iridium_plating", simple());
    public static final Item NOSE_CONE = register("nose_cone", simple());
    public static final Item ROCKET_FIN = register("rocket_fin", simple());
    public static final Item ROCKET_ENGINE = register("rocket_engine", new TooltipItem(new Item.Settings()));
    public static final Item ADVANCED_ROCKET_ENGINE = register("advanced_rocket_engine",
            new TooltipItem(new Item.Settings().rarity(Rarity.UNCOMMON)));
    public static final Item FUSION_ENGINE = register("fusion_engine",
            new TooltipItem(new Item.Settings().rarity(Rarity.RARE)));

    // Space suit
    public static final Item SPACE_HELMET = register("space_helmet", new SpaceSuitItem(ArmorItem.Type.HELMET,
            new Item.Settings().maxDamage(ArmorItem.Type.HELMET.getMaxDamage(20))));
    public static final Item SPACE_SUIT = register("space_suit", new SpaceSuitItem(ArmorItem.Type.CHESTPLATE,
            new Item.Settings().maxDamage(ArmorItem.Type.CHESTPLATE.getMaxDamage(20))));
    public static final Item SPACE_PANTS = register("space_pants", new SpaceSuitItem(ArmorItem.Type.LEGGINGS,
            new Item.Settings().maxDamage(ArmorItem.Type.LEGGINGS.getMaxDamage(20))));
    public static final Item SPACE_BOOTS = register("space_boots", new SpaceSuitItem(ArmorItem.Type.BOOTS,
            new Item.Settings().maxDamage(ArmorItem.Type.BOOTS.getMaxDamage(20))));

    // Materials
    public static final Item RAW_TITANIUM = register("raw_titanium", simple());
    public static final Item TITANIUM_INGOT = register("titanium_ingot", simple());
    public static final Item RAW_IRIDIUM = register("raw_iridium", simple());
    public static final Item IRIDIUM_INGOT = register("iridium_ingot", simple());
    public static final Item SOLAR_CRYSTAL = register("solar_crystal", simple());
    public static final Item SULFUR = register("sulfur", simple());
    public static final Item FROST_CRYSTAL = register("frost_crystal", simple());

    // Food
    public static final Item ASTRONAUT_ICE_CREAM = register("astronaut_ice_cream", new Item(new Item.Settings()
            .food(new FoodComponent.Builder().nutrition(6).saturationModifier(0.6F).snack().build())));

    private ModItems() {
    }

    private static Item simple() {
        return new Item(new Item.Settings());
    }

    private static <T extends Item> T register(String name, T item) {
        Registry.register(Registries.ITEM, InterplanetaryStuff.id(name), item);
        ITEMS.add(item);
        return item;
    }

    public static RocketItem rocketForTier(int tier) {
        return (RocketItem) switch (tier) {
            case 2 -> ROCKET_TIER_2;
            case 3 -> ROCKET_TIER_3;
            default -> ROCKET_TIER_1;
        };
    }

    /** True if the player wears all four pieces of the space suit. */
    public static boolean hasFullSpaceSuit(PlayerEntity player) {
        return player.getEquippedStack(EquipmentSlot.HEAD).isOf(SPACE_HELMET)
                && player.getEquippedStack(EquipmentSlot.CHEST).isOf(SPACE_SUIT)
                && player.getEquippedStack(EquipmentSlot.LEGS).isOf(SPACE_PANTS)
                && player.getEquippedStack(EquipmentSlot.FEET).isOf(SPACE_BOOTS);
    }

    public static void init() {
    }
}
