package com.randonaughtica.interplanetary.body;

public enum BodyType {
    HOME_PLANET("home_planet"),
    PLANET("planet"),
    DWARF_PLANET("dwarf_planet"),
    MOON("moon"),
    ASTEROID("asteroid");

    private final String key;

    BodyType(String key) {
        this.key = key;
    }

    public String translationKey() {
        return "body_type.interplanetary." + key;
    }
}
