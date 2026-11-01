package com.randonaughtica.interplanetary.body;

import com.randonaughtica.interplanetary.InterplanetaryStuff;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;

import java.util.List;

/**
 * A group of destinations shown together on the star map (a planet and its moons, a belt...).
 *
 * @param id     system id, also used for the icon texture {@code textures/gui/systems/<id>.png}
 * @param orbit  orbit slot on the star map, 0 = closest to the sun
 * @param bodies ids of the landable bodies of this system
 */
public record StarSystem(String id, int orbit, int color, List<String> bodies) {

    public Identifier icon() {
        return InterplanetaryStuff.id("textures/gui/systems/" + id + ".png");
    }

    public Text displayName() {
        return Text.translatable("system.interplanetary." + id);
    }

    public Text description() {
        return Text.translatable("system.interplanetary." + id + ".desc");
    }
}
