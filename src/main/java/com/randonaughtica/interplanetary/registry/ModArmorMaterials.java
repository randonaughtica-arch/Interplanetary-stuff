package com.randonaughtica.interplanetary.registry;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import net.minecraft.item.ArmorItem;
import net.minecraft.item.ArmorMaterial;
import net.minecraft.recipe.Ingredient;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.registry.entry.RegistryEntry;
import net.minecraft.sound.SoundEvents;
import net.minecraft.util.Util;

import java.util.EnumMap;
import java.util.List;

public final class ModArmorMaterials {
    public static final RegistryEntry<ArmorMaterial> SPACE_SUIT = Registry.registerReference(Registries.ARMOR_MATERIAL,
            InterplanetaryStuff.id("space_suit"),
            new ArmorMaterial(
                    Util.make(new EnumMap<>(ArmorItem.Type.class), map -> {
                        map.put(ArmorItem.Type.BOOTS, 2);
                        map.put(ArmorItem.Type.LEGGINGS, 4);
                        map.put(ArmorItem.Type.CHESTPLATE, 5);
                        map.put(ArmorItem.Type.HELMET, 2);
                        map.put(ArmorItem.Type.BODY, 5);
                    }),
                    12,
                    SoundEvents.ITEM_ARMOR_EQUIP_IRON,
                    () -> Ingredient.ofItems(ModItems.TITANIUM_INGOT),
                    List.of(new ArmorMaterial.Layer(InterplanetaryStuff.id("space_suit"))),
                    1.0F,
                    0.0F));

    private ModArmorMaterials() {
    }

    public static void init() {
    }
}
