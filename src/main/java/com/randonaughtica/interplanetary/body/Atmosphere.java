package com.randonaughtica.interplanetary.body;

public enum Atmosphere {
    BREATHABLE("breathable"),
    NONE("none"),
    TRACE("trace"),
    THIN("thin"),
    THICK("thick"),
    CRUSHING("crushing");

    private final String key;

    Atmosphere(String key) {
        this.key = key;
    }

    public String translationKey() {
        return "atmosphere.interplanetary." + key;
    }
}
