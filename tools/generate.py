#!/usr/bin/env python3
"""Generates the data-driven content of Interplanetary Stuff.

Run from the repository root:  python3 tools/generate.py

Produces (and overwrites):
  * world generation for every celestial body (dimension, dimension type, noise settings,
    noise parameters, biomes, configured/placed features, carvers)
  * blockstates, block/item models, loot tables, tags, recipes, advancements
  * all textures (blocks, items, rocket, space suit, planets, skybox, GUI icons)
  * the English language file
  * src/main/java/.../registry/PlanetBlocks.java (block registrations)

Everything is described by the tables at the top of this file; edit them and re-run.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textures as tx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "src", "main", "resources")
ASSETS = os.path.join(RES, "assets", "interplanetary")
DATA = os.path.join(RES, "data", "interplanetary")
DATA_MC = os.path.join(RES, "data", "minecraft")
DATA_C = os.path.join(RES, "data", "c")
JAVA_PKG = os.path.join(ROOT, "src", "main", "java", "com", "randonaughtica", "interplanetary", "registry")
NS = "interplanetary"

# Must match SpaceSkyRenderer.GALACTIC_NORMAL
GALACTIC_NORMAL = (0.30, 0.55, 0.78)

LANG: dict[str, str] = {}


def mid(path: str) -> str:
    return f"{NS}:{path}"


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def save_png(path: str, arr) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tx.to_image(arr).save(path, optimize=True)


# =============================================================================== blocks

@dataclass
class BlockDef:
    id: str
    name: str
    style: str
    color: int
    map_color: str = "STONE_GRAY"
    sound: str = "STONE"
    hardness: float = 1.5
    resistance: float = 6.0
    tool: str = "pickaxe"          # pickaxe | shovel
    level: int = 0                 # 0 = any, 1 = stone, 2 = iron
    requires_tool: bool = True
    kind: str = "cube"             # cube | falling | cluster
    light: int = 0
    slippery: bool = False
    rotate: bool = False           # random rotated variants (natural blocks)
    drop: dict | None = None       # None = drops itself
    ore_base: str | None = None    # texture of the block this ore sits in
    ore_colors: tuple | None = None
    stone_for_bricks: str | None = None
    extra_tags: list = field(default_factory=list)
    carvable: bool = True


BLOCKS: list[BlockDef] = []
BLOCK_BY_ID: dict[str, BlockDef] = {}


def add_block(b: BlockDef) -> BlockDef:
    assert b.id not in BLOCK_BY_ID, b.id
    BLOCKS.append(b)
    BLOCK_BY_ID[b.id] = b
    return b


def surface(id, name, color, style="regolith", map_color="LIGHT_GRAY", sound="GRAVEL", falling=False, hardness=0.6,
            tool="shovel", **kw):
    return add_block(BlockDef(id, name, style, color, map_color=map_color, sound=sound, hardness=hardness,
                              resistance=hardness, tool=tool, requires_tool=False,
                              kind="falling" if falling else "cube", rotate=True, **kw))


def stone(id, name, color, style="stone", map_color="STONE_GRAY", sound="STONE", hardness=1.5, **kw):
    return add_block(BlockDef(id, name, style, color, map_color=map_color, sound=sound, hardness=hardness,
                              resistance=6.0, **kw))


def bricks(id, name, stone_block: BlockDef):
    return add_block(BlockDef(id, name, "bricks", stone_block.color, map_color=stone_block.map_color,
                              sound="DEEPSLATE_BRICKS" if stone_block.sound == "STONE" else stone_block.sound,
                              hardness=2.0, resistance=6.0, stone_for_bricks=stone_block.id, carvable=False))


def ore(id, name, base: BlockDef, colors, drop, level=1, hardness=3.0, light=0, xp=(0, 0)):
    return add_block(BlockDef(id, name, "ore", base.color, map_color=base.map_color, sound=base.sound,
                              hardness=hardness, resistance=3.0, level=level, ore_base=base.id, ore_colors=colors,
                              drop=dict(drop, ore=True), light=light))


# Ore palettes: (dark, mid, light)
TITANIUM = (0x5A6878, 0xA8B8C8, 0xE8F0F8)
IRON = (0x8A5A3A, 0xC8946E, 0xE8C4A4)
GOLD = (0x8A6A08, 0xE8C030, 0xFFF080)
DIAMOND = (0x1A8A8A, 0x4AE8E0, 0xC8FFFC)
COAL = (0x101010, 0x2A2A2A, 0x4A4A4A)
SULFUR = (0x9A8A10, 0xE8D840, 0xFFF8A0)
SOLAR = (0xC87800, 0xFFC020, 0xFFF4A0)
IRIDIUM = (0x8A8E98, 0xD8DEE8, 0xFFFFFF)


# =============================================================================== bodies

@dataclass
class Feature:
    name: str
    configured: dict
    placement: list
    step: int
    biomes: list | None = None   # restrict to some of the body's biome ids (suffixes)


@dataclass
class BiomeDef:
    suffix: str                       # "" for the main biome
    name: str
    params: dict | None = None        # multi-noise parameters
    top: str | None = None            # override the top block in this biome
    sub: str | None = None


@dataclass
class Body:
    id: str
    name: str
    desc: str
    surface: str
    stone: str
    sub: str | None = None
    steep: str | None = None
    underwater: str | None = None
    patches: list = field(default_factory=list)   # [(block, min_threshold)] using the patch noise
    terrain: dict = field(default_factory=dict)
    sea_level: int = 0
    fluid: str = "minecraft:water"
    sky: int = 0
    fog: int = 0
    water: int = 0x3F76E4
    water_fog: int = 0x050533
    temperature: float = 0.5
    particle: tuple | None = None
    biomes: list = field(default_factory=list)
    features: list = field(default_factory=list)
    spawns: dict = field(default_factory=dict)
    ultrawarm: bool = False
    floating: bool = False
    caves: bool = True


BODIES: list[Body] = []


def body(**kw) -> Body:
    b = Body(**kw)
    if not b.biomes:
        b.biomes = [BiomeDef("", b.name)]
    BODIES.append(b)
    return b


# ------------------------------------------------------------------ feature helpers

def biome_filter():
    return {"type": "minecraft:biome"}


def uniform_int(lo, hi):
    return {"type": "minecraft:uniform", "min_inclusive": lo, "max_inclusive": hi}


def state(block, props=None):
    s = {"Name": block if ":" in block else mid(block)}
    if props:
        s["Properties"] = props
    return s


def simple_provider(block, props=None):
    return {"type": "minecraft:simple_state_provider", "state": state(block, props)}


def crater(name, rmin, rmax, depth=0.45, rim=0.22, chance=3, floor=None):
    config = {"radius": uniform_int(rmin, rmax), "depth": depth, "rim": rim}
    if floor:
        config["floor"] = simple_provider(floor)
    return Feature(name, {"type": mid("crater"), "config": config},
                   [{"type": "minecraft:rarity_filter", "chance": chance}, {"type": "minecraft:in_square"},
                    biome_filter()], 2)


def ore_feature(name, block, target, size=8, count=8, ymin=4, ymax=100):
    return Feature(name, {"type": "minecraft:ore", "config": {
        "size": size, "discard_chance_on_air_exposure": 0.0,
        "targets": [{"target": {"predicate_type": "minecraft:block_match", "block": mid(target)},
                     "state": state(block)}]}},
                   [{"type": "minecraft:count", "count": count}, {"type": "minecraft:in_square"},
                    {"type": "minecraft:height_range", "height": {
                        "type": "minecraft:uniform", "min_inclusive": {"absolute": ymin},
                        "max_inclusive": {"absolute": ymax}}},
                    biome_filter()], 6)


def surface_placement(count=None, chance=None):
    p = []
    if chance:
        p.append({"type": "minecraft:rarity_filter", "chance": chance})
    if count:
        p.append({"type": "minecraft:count", "count": count})
    p += [{"type": "minecraft:in_square"},
          {"type": "minecraft:heightmap", "heightmap": "WORLD_SURFACE_WG"},
          biome_filter()]
    return p


def boulder(name, blocks, rmin=1, rmax=2, chance=None, count=None, biomes=None):
    if isinstance(blocks, str):
        provider = simple_provider(blocks)
    else:
        provider = {"type": "minecraft:weighted_state_provider",
                    "entries": [{"weight": w, "data": state(b)} for b, w in blocks]}
    return Feature(name, {"type": mid("boulder"), "config": {"state": provider, "radius": uniform_int(rmin, rmax)}},
                   surface_placement(count, chance), 9, biomes)


def disk(name, block, targets, rmin=2, rmax=5, chance=None, count=None, half_height=1, biomes=None):
    return Feature(name, {"type": "minecraft:disk", "config": {
        "state_provider": {"fallback": simple_provider(block), "rules": []},
        "target": {"type": "minecraft:matching_blocks",
                   "blocks": [t if ":" in t else mid(t) for t in targets]},
        "radius": uniform_int(rmin, rmax), "half_height": half_height}},
                   surface_placement(count, chance), 7, biomes)


def column(name, block, hmin, hmax, chance=None, count=None, biomes=None):
    return Feature(name, {"type": "minecraft:block_column", "config": {
        "direction": "up",
        "allowed_placement": {"type": "minecraft:matching_blocks", "blocks": "minecraft:air"},
        "prioritize_tip": False,
        "layers": [{"height": uniform_int(hmin, hmax), "provider": simple_provider(block)}]}},
                   surface_placement(count, chance), 9, biomes)


def cluster(name, block, count=2, chance=None, biomes=None):
    st = state(block, {"facing": "up", "waterlogged": "false"})
    placement = surface_placement(count, chance)
    placement.insert(-1, {"type": "minecraft:block_predicate_filter",
                          "predicate": {"type": "minecraft:would_survive", "state": st}})
    return Feature(name, {"type": "minecraft:simple_block", "config": {
        "to_place": {"type": "minecraft:simple_state_provider", "state": st}}}, placement, 9, biomes)


def lake(name, fluid, barrier, chance):
    return Feature(name, {"type": "minecraft:lake", "config": {
        "fluid": simple_provider(fluid, {"level": "0"}), "barrier": simple_provider(barrier)}},
                   [{"type": "minecraft:rarity_filter", "chance": chance}, {"type": "minecraft:in_square"},
                    {"type": "minecraft:heightmap", "heightmap": "WORLD_SURFACE_WG"}, biome_filter()], 1)


FREEZE = "minecraft:freeze_top_layer"


def spawn(entity, weight, lo=1, hi=1):
    return {"type": entity, "weight": weight, "minCount": lo, "maxCount": hi}


# =============================================================================== content tables

def define_content():
    # ------------------------------------------------------------- shared special blocks
    add_block(BlockDef("launch_pad", "Launch Pad", "launch_pad", 0x8A9098, map_color="IRON_GRAY", sound="METAL",
                       hardness=3.0, carvable=False))
    add_block(BlockDef("titanium_block", "Block of Titanium", "metal", 0xB9C4CF, map_color="LIGHT_GRAY",
                       sound="METAL", hardness=5.0, level=1, carvable=False, extra_tags=["minecraft:beacon_base_blocks"]))
    add_block(BlockDef("iridium_block", "Block of Iridium", "metal", 0xD6DAE2, map_color="WHITE",
                       sound="METAL", hardness=6.0, level=2, carvable=False, extra_tags=["minecraft:beacon_base_blocks"]))
    add_block(BlockDef("solar_crystal_block", "Block of Solar Crystal", "crystal_block", 0xFFC830,
                       map_color="GOLD", sound="AMETHYST_BLOCK", hardness=1.5, light=15, carvable=False))
    add_block(BlockDef("frost_crystal_block", "Block of Frost Crystal", "crystal_block", 0x8AD8F8,
                       map_color="LIGHT_BLUE", sound="AMETHYST_BLOCK", hardness=1.5, light=12, carvable=False))
    add_block(BlockDef("solar_crystal_cluster", "Solar Crystal Cluster", "cluster", 0xFFC020, map_color="GOLD",
                       sound="AMETHYST_CLUSTER", hardness=1.5, kind="cluster", light=9,
                       drop={"item": mid("solar_crystal"), "min": 2, "max": 3, "ore": True}, carvable=False))
    add_block(BlockDef("frost_crystal_cluster", "Frost Crystal Cluster", "cluster", 0x8AD8F8, map_color="LIGHT_BLUE",
                       sound="AMETHYST_CLUSTER", hardness=1.5, kind="cluster", light=7,
                       drop={"item": mid("frost_crystal"), "min": 2, "max": 3, "ore": True}, carvable=False))
    add_block(BlockDef("sulfur_block", "Block of Sulfur", "sulfur", 0xE3D24A, map_color="YELLOW", sound="CALCITE",
                       hardness=1.2))
    add_block(BlockDef("methane_ice", "Methane Ice", "ice", 0xE8C496, map_color="TERRACOTTA_WHITE", sound="GLASS",
                       hardness=0.8, slippery=True))
    add_block(BlockDef("nitrogen_ice", "Nitrogen Ice", "ice", 0xF2F2FF, map_color="WHITE", sound="GLASS",
                       hardness=0.8, slippery=True))
    add_block(BlockDef("bright_salt", "Bright Salt", "salt", 0xF4F0E4, map_color="WHITE", sound="CALCITE",
                       hardness=1.0, light=7))
    add_block(BlockDef("tholin_regolith", "Tholin Regolith", "tholin", 0x7A3B25, map_color="TERRACOTTA_RED",
                       sound="SAND", hardness=0.6, tool="shovel", requires_tool=False, rotate=True))
    add_block(BlockDef("pumice", "Pumice", "pumice", 0xC4B9A8, map_color="TERRACOTTA_WHITE", sound="TUFF",
                       hardness=0.8))

    # ------------------------------------------------------------- the Moon
    s = surface("moon_regolith", "Lunar Regolith", 0x9B9B9B)
    st = stone("moon_stone", "Moon Rock", 0x707070)
    bricks("moon_stone_bricks", "Moon Rock Bricks", st)
    ore("moon_titanium_ore", "Lunar Titanium Ore", st, TITANIUM, {"item": mid("raw_titanium")})
    ore("moon_iron_ore", "Lunar Iron Ore", st, IRON, {"item": "minecraft:raw_iron"})
    body(id="moon", name="The Moon",
         desc="Earth's companion. Grey maria, bright highlands and countless craters. Rich in titanium.",
         surface=s.id, stone=st.id,
         terrain=dict(base=66, large=14, lowland=-0.2, medium=5, detail=1.2, ridge=10, ridge_bias=-0.2),
         features=[crater("large_crater", 6, 14, 0.42, 0.24, chance=4),
                   crater("small_crater", 2, 5, 0.5, 0.25, chance=2),
                   ore_feature("titanium_ore", "moon_titanium_ore", "moon_stone", 6, 7, 4, 80),
                   ore_feature("iron_ore", "moon_iron_ore", "moon_stone", 8, 10, 4, 100),
                   boulder("boulder", "moon_stone", 1, 2, chance=3)],
         spawns={"monster": [spawn("minecraft:enderman", 4, 1, 2)]})

    # ------------------------------------------------------------- Mercury
    s = surface("mercury_regolith", "Mercurian Regolith", 0x6E6862, map_color="GRAY")
    st = stone("mercury_stone", "Mercurian Rock", 0x4C4845, map_color="DEEPSLATE_GRAY", sound="DEEPSLATE",
               hardness=2.0)
    bricks("mercury_stone_bricks", "Mercurian Bricks", st)
    ore("mercury_solar_crystal_ore", "Solar Crystal Ore", st, SOLAR,
        {"item": mid("solar_crystal"), "min": 1, "max": 2}, level=1, light=5)
    body(id="mercury", name="Mercury",
         desc="The scorched innermost planet. The Sun looms huge in a black sky. Solar crystals grow here.",
         surface=s.id, stone=st.id, ultrawarm=True, temperature=2.0,
         terrain=dict(base=64, large=12, medium=6, detail=1.5, cliff=10, cliff_sharp=4),
         features=[crater("large_crater", 6, 14, 0.4, 0.22, chance=3),
                   crater("small_crater", 2, 6, 0.5, 0.25, chance=1),
                   ore_feature("solar_crystal_ore", "mercury_solar_crystal_ore", "mercury_stone", 5, 8, 4, 90),
                   boulder("boulder", "mercury_stone", 1, 2, chance=4),
                   cluster("solar_crystals", "solar_crystal_cluster", count=3)],
         spawns={"monster": [spawn("minecraft:magma_cube", 6, 1, 2)]})

    # ------------------------------------------------------------- Venus
    s = surface("venus_soil", "Venusian Soil", 0xA5683C, style="soil", map_color="TERRACOTTA_ORANGE", sound="SAND")
    st = stone("venus_basalt", "Venusian Basalt", 0x4E3E34, style="basalt", map_color="TERRACOTTA_BROWN",
               sound="BASALT", hardness=1.8)
    bricks("venus_basalt_bricks", "Venusian Basalt Bricks", st)
    ore("venus_sulfur_ore", "Venusian Sulfur Ore", st, SULFUR, {"item": mid("sulfur"), "min": 2, "max": 4})
    body(id="venus", name="Venus",
         desc="A crushing, scorching greenhouse world of lava plains under endless yellow clouds.",
         surface=s.id, stone=st.id, ultrawarm=True, temperature=2.0, sea_level=46, fluid="minecraft:lava",
         sky=0xD8A858, fog=0xC89850, particle=("minecraft:ash", 0.02),
         terrain=dict(base=62, large=18, medium=6, detail=1.5, ridge=25, ridge_bias=-0.4),
         features=[lake("lava_lake", "minecraft:lava", "venus_basalt", 8),
                   crater("crater", 4, 9, 0.35, 0.2, chance=12),
                   ore_feature("sulfur_ore", "venus_sulfur_ore", "venus_basalt", 9, 10, 4, 120),
                   disk("sulfur_deposit", "sulfur_block", ["venus_soil"], 2, 4, chance=3),
                   boulder("pumice_boulder", "pumice", 1, 2, chance=4),
                   column("basalt_column", "venus_basalt", 2, 6, count=2)],
         spawns={"monster": [spawn("minecraft:magma_cube", 10, 1, 3), spawn("minecraft:blaze", 2, 1, 1)]})

    # ------------------------------------------------------------- Mars
    s = surface("mars_sand", "Martian Sand", 0xB5552C, style="sand", map_color="TERRACOTTA_ORANGE", sound="SAND",
                falling=True, hardness=0.5)
    sub = surface("mars_regolith", "Martian Regolith", 0x8F4426, style="soil", map_color="TERRACOTTA_RED")
    st = stone("mars_stone", "Martian Rock", 0x6E3324, map_color="TERRACOTTA_RED")
    bricks("mars_stone_bricks", "Martian Bricks", st)
    ore("mars_iron_ore", "Martian Iron Ore", st, IRON, {"item": "minecraft:raw_iron"})
    ore("mars_titanium_ore", "Martian Titanium Ore", st, TITANIUM, {"item": mid("raw_titanium")})
    body(id="mars", name="Mars",
         desc="The Red Planet: rust-red dunes, giant volcanoes, deep canyons and blue sunsets.",
         surface=s.id, sub=sub.id, stone=st.id, patches=[(sub.id, 0.35)],
         sky=0xC9A27E, fog=0xC08A60, temperature=0.3, particle=("minecraft:white_ash", 0.004),
         terrain=dict(base=70, large=22, medium=8, detail=2, ridge=40, ridge_bias=-0.3, canyon=30, canyon_sharp=8,
                      dunes=3),
         features=[crater("crater", 4, 12, 0.4, 0.22, chance=6),
                   ore_feature("iron_ore", "mars_iron_ore", "mars_stone", 9, 12, 4, 110),
                   ore_feature("titanium_ore", "mars_titanium_ore", "mars_stone", 5, 4, 4, 60),
                   boulder("boulder", [("mars_stone", 3), ("mars_regolith", 1)], 1, 2, chance=3)],
         spawns={"monster": [spawn("minecraft:husk", 30, 1, 3)]})

    s = surface("phobos_regolith", "Phobos Regolith", 0x5C544E, map_color="GRAY")
    st = stone("phobos_stone", "Phobos Rock", 0x423C38, map_color="DEEPSLATE_GRAY")
    bricks("phobos_stone_bricks", "Phobos Bricks", st)
    body(id="phobos", name="Phobos",
         desc="Mars' larger moon, a lumpy grooved rock that barely holds on to you. Mars fills the sky.",
         surface=s.id, stone=st.id,
         terrain=dict(base=60, large=10, medium=6, detail=2, canyon=4, canyon_sharp=12),
         features=[crater("stickney", 8, 14, 0.5, 0.25, chance=8),
                   crater("small_crater", 2, 5, 0.5, 0.25, chance=2),
                   boulder("boulder", "phobos_stone", 1, 2, chance=3)])

    s = surface("deimos_regolith", "Deimos Regolith", 0x8C8072, map_color="TERRACOTTA_LIGHT_GRAY")
    st = stone("deimos_stone", "Deimos Rock", 0x675D53)
    bricks("deimos_stone_bricks", "Deimos Bricks", st)
    body(id="deimos", name="Deimos",
         desc="Mars' tiny outer moon, smoothed by a thick blanket of dust.",
         surface=s.id, stone=st.id,
         terrain=dict(base=60, large=8, medium=3, detail=1),
         features=[crater("small_crater", 2, 5, 0.4, 0.15, chance=3)])

    # ------------------------------------------------------------- asteroids
    s = surface("ceres_regolith", "Ceres Regolith", 0x5C5C60, map_color="GRAY")
    st = stone("ceres_stone", "Ceres Rock", 0x404044, map_color="DEEPSLATE_GRAY")
    bricks("ceres_stone_bricks", "Ceres Bricks", st)
    body(id="ceres", name="Ceres",
         desc="The largest object in the asteroid belt, a dwarf planet with glowing salt deposits in its craters.",
         surface=s.id, stone=st.id,
         terrain=dict(base=64, large=10, medium=4, detail=1.2),
         features=[crater("occator", 5, 12, 0.4, 0.2, chance=4, floor="bright_salt"),
                   crater("small_crater", 2, 5, 0.45, 0.2, chance=2),
                   disk("salt_deposit", "bright_salt", ["ceres_regolith"], 1, 3, chance=6)])

    s = surface("vesta_regolith", "Vesta Regolith", 0xA39A8C, map_color="TERRACOTTA_LIGHT_GRAY")
    st = stone("vesta_stone", "Vesta Rock", 0x7A7266)
    bricks("vesta_stone_bricks", "Vesta Bricks", st)
    ore("vesta_diamond_ore", "Vesta Diamond Ore", st, DIAMOND, {"item": "minecraft:diamond"}, level=2)
    body(id="vesta", name="Vesta",
         desc="A battered protoplanet with a gigantic impact basin and a towering central peak. Diamonds hide inside.",
         surface=s.id, stone=st.id,
         terrain=dict(base=66, large=26, medium=6, detail=1.5, ridge=20, ridge_bias=-0.2),
         features=[crater("crater", 4, 10, 0.4, 0.22, chance=4),
                   ore_feature("diamond_ore", "vesta_diamond_ore", "vesta_stone", 5, 4, 4, 40),
                   boulder("boulder", "vesta_stone", 1, 2, chance=4)])

    s = surface("psyche_regolith", "Psyche Gravel", 0x7C7A76, map_color="IRON_GRAY", sound="GRAVEL")
    st = stone("psyche_nickel_iron", "Nickel-Iron", 0x8E9096, style="nickel_iron", map_color="IRON_GRAY",
               sound="METAL", hardness=3.0, level=1)
    bricks("psyche_nickel_iron_bricks", "Nickel-Iron Bricks", st)
    ore("psyche_iridium_ore", "Iridium Ore", st, IRIDIUM, {"item": mid("raw_iridium")}, level=2, hardness=4.0)
    ore("psyche_gold_ore", "Psyche Gold Ore", st, GOLD, {"item": "minecraft:raw_gold"}, level=2, hardness=4.0)
    body(id="psyche", name="Psyche",
         desc="A metal world: the exposed iron core of a shattered protoplanet. The only known source of iridium.",
         surface=s.id, stone=st.id,
         terrain=dict(base=64, large=14, medium=8, detail=3, overhang=0.35),
         features=[crater("crater", 3, 9, 0.45, 0.2, chance=4),
                   ore_feature("iridium_ore", "psyche_iridium_ore", "psyche_nickel_iron", 5, 7, 4, 90),
                   ore_feature("gold_ore", "psyche_gold_ore", "psyche_nickel_iron", 8, 8, 4, 110),
                   boulder("boulder", "psyche_nickel_iron", 1, 2, chance=3)],
         spawns={"monster": [spawn("minecraft:endermite", 5, 1, 2)]})

    s = surface("bennu_regolith", "Bennu Rubble", 0x2F2C2A, map_color="BLACK", sound="GRAVEL")
    st = stone("bennu_stone", "Carbonaceous Rock", 0x3D3936, map_color="BLACK", hardness=1.2)
    bricks("bennu_stone_bricks", "Carbonaceous Bricks", st)
    ore("bennu_coal_ore", "Carbon-Rich Ore", st, COAL, {"item": "minecraft:coal"}, level=0)
    body(id="bennu", name="Bennu",
         desc="A rubble-pile asteroid: a field of drifting boulders and carbon-rich rock above an endless void.",
         surface=s.id, stone=st.id, floating=True, caves=False,
         terrain=dict(),
         features=[ore_feature("coal_ore", "bennu_coal_ore", "bennu_stone", 10, 20, 0, 255)])

    # ------------------------------------------------------------- Jupiter's moons
    s = surface("io_sulfur_crust", "Sulfur Crust", 0xE3D24A, style="sulfur", map_color="YELLOW", sound="CALCITE")
    st = stone("io_stone", "Io Rock", 0xB38A2E, map_color="TERRACOTTA_ORANGE")
    bricks("io_stone_bricks", "Io Bricks", st)
    ore("io_sulfur_ore", "Io Sulfur Ore", st, SULFUR, {"item": mid("sulfur"), "min": 2, "max": 5})
    body(id="io", name="Io",
         desc="The most volcanic world in the Solar System. Lava lakes, sulfur plains and Jupiter overhead.",
         surface=s.id, stone=st.id, sea_level=50, fluid="minecraft:lava", ultrawarm=True,
         particle=("minecraft:ash", 0.004),
         terrain=dict(base=64, large=10, medium=5, detail=1, ridge=30, ridge_bias=-0.6),
         features=[lake("lava_lake", "minecraft:lava", "io_stone", 6),
                   ore_feature("sulfur_ore", "io_sulfur_ore", "io_stone", 10, 12, 4, 120),
                   disk("sulfur_deposit", "sulfur_block", ["io_sulfur_crust"], 2, 5, chance=2),
                   column("sulfur_column", "sulfur_block", 2, 5, chance=3)],
         spawns={"monster": [spawn("minecraft:magma_cube", 15, 1, 3)]})

    s = surface("europa_ice", "Europan Ice", 0xE6DED2, style="ice", map_color="TERRACOTTA_WHITE", sound="GLASS",
                hardness=0.8, tool="pickaxe", slippery=True)
    lin = surface("europa_lineae_ice", "Lineae Ice", 0xE0D6C8, style="lineae", map_color="TERRACOTTA_WHITE",
                  sound="GLASS", hardness=0.8, tool="pickaxe", slippery=True)
    st = stone("europa_stone", "Europan Seabed Rock", 0x7C746A)
    bricks("europa_ice_bricks", "Europan Ice Bricks", s)
    body(id="europa", name="Europa",
         desc="An ice-shelled moon hiding a dark global ocean - and glowing life beneath the ice.",
         surface=s.id, stone=st.id, sub=s.id, patches=[(lin.id, 0.25)], underwater=st.id,
         sea_level=100, temperature=-0.8, water=0x1A4A70, water_fog=0x061420,
         terrain=dict(base=76, large=12, medium=3, detail=0.8, cliff=20, cliff_sharp=4, ridge=14, ridge_bias=0.0),
         features=[boulder("ice_boulder", "europa_ice", 1, 2, chance=6),
                   Feature("freeze", None, None, 10)],
         spawns={"water_creature": [spawn("minecraft:squid", 6, 1, 4)],
                 "underground_water_creature": [spawn("minecraft:glow_squid", 10, 2, 4)],
                 "monster": [spawn("minecraft:stray", 4, 1, 2)]})

    s = surface("ganymede_regolith", "Ganymede Regolith", 0x877C70, map_color="TERRACOTTA_LIGHT_GRAY")
    st = stone("ganymede_stone", "Ganymede Rock", 0x5E564F)
    bricks("ganymede_stone_bricks", "Ganymede Bricks", st)
    body(id="ganymede", name="Ganymede",
         desc="The largest moon in the Solar System, striped with long bright grooves of ancient ice.",
         surface=s.id, stone=st.id, patches=[("minecraft:packed_ice", 0.55)], temperature=-0.5,
         terrain=dict(base=66, large=12, medium=4, detail=1, canyon=6, canyon_sharp=10, ridge=8, ridge_bias=0.0),
         features=[crater("crater", 3, 9, 0.4, 0.2, chance=4),
                   boulder("boulder", "ganymede_stone", 1, 2, chance=5)],
         spawns={"monster": [spawn("minecraft:stray", 4, 1, 2)]})

    s = surface("callisto_regolith", "Callisto Regolith", 0x56504A, map_color="BROWN")
    st = stone("callisto_stone", "Callisto Rock", 0x3E3A36, map_color="DEEPSLATE_GRAY")
    bricks("callisto_stone_bricks", "Callisto Bricks", st)
    body(id="callisto", name="Callisto",
         desc="The most heavily cratered body known: dark, ancient and frozen, with ice in its craters.",
         surface=s.id, stone=st.id, temperature=-0.5,
         terrain=dict(base=64, large=8, medium=4, detail=1),
         features=[crater("large_crater", 6, 14, 0.42, 0.24, chance=2, floor="minecraft:packed_ice"),
                   crater("small_crater", 2, 5, 0.5, 0.25, chance=1),
                   boulder("boulder", "callisto_stone", 1, 2, chance=4)],
         spawns={"monster": [spawn("minecraft:stray", 4, 1, 2)]})

    # ------------------------------------------------------------- Saturn's moons
    s = surface("titan_sand", "Titan Sand", 0x6E4A2A, style="sand", map_color="BROWN", sound="SAND", falling=True,
                hardness=0.5)
    st = stone("titan_stone", "Titan Ice Rock", 0x8A7350, map_color="TERRACOTTA_BROWN")
    bricks("titan_stone_bricks", "Titan Bricks", st)
    body(id="titan", name="Titan",
         desc="A hazy orange world with dunes, rain and lakes - of liquid methane. Fuel for the taking.",
         surface=s.id, stone=st.id, sea_level=58, temperature=-0.3,
         sky=0xC07A30, fog=0xB0702A, water=0x3B2410, water_fog=0x1E1208, particle=("minecraft:mycelium", 0.003),
         terrain=dict(base=62, large=10, medium=5, detail=1, dunes=5),
         features=[lake("methane_lake", "minecraft:water", "titan_stone", 10),
                   disk("methane_ice", "methane_ice", ["titan_sand", "titan_stone"], 2, 4, chance=2),
                   boulder("boulder", "titan_stone", 1, 2, chance=6)])

    s = surface("enceladus_snow", "Enceladus Snow", 0xF4F8FB, style="frost", map_color="WHITE", sound="SNOW",
                hardness=0.4)
    st = stone("enceladus_ice", "Enceladus Ice", 0xCFE2EE, style="ice", map_color="LIGHT_BLUE", sound="GLASS",
               hardness=1.0, slippery=True)
    bricks("enceladus_ice_bricks", "Enceladus Ice Bricks", st)
    body(id="enceladus", name="Enceladus",
         desc="The brightest world of all. Icy geysers erupt from its blue 'tiger stripe' fractures.",
         surface=s.id, stone=st.id, temperature=-0.8, particle=("minecraft:snowflake", 0.003),
         terrain=dict(base=66, large=8, medium=3, detail=1, canyon=12, canyon_sharp=9),
         features=[crater("crater", 3, 8, 0.4, 0.2, chance=6),
                   column("geyser", "minecraft:packed_ice", 3, 9, chance=2),
                   column("blue_geyser", "minecraft:blue_ice", 2, 5, chance=5)],
         spawns={"monster": [spawn("minecraft:stray", 5, 1, 2)]})

    s = surface("mimas_regolith", "Mimas Regolith", 0xB7B5B0, map_color="LIGHT_GRAY")
    st = stone("mimas_stone", "Mimas Ice Rock", 0x8D8B87)
    bricks("mimas_stone_bricks", "Mimas Bricks", st)
    body(id="mimas", name="Mimas",
         desc="The 'Death Star' moon, scarred by one enormous crater. Saturn and its rings fill the sky.",
         surface=s.id, stone=st.id, temperature=-0.5,
         terrain=dict(base=66, large=10, medium=3, detail=1),
         features=[crater("herschel", 10, 14, 0.5, 0.3, chance=3),
                   crater("small_crater", 2, 6, 0.5, 0.25, chance=1)])

    s = surface("rhea_regolith", "Rhea Regolith", 0xC2BDB5, map_color="LIGHT_GRAY")
    st = stone("rhea_stone", "Rhea Ice Rock", 0x97928B)
    bricks("rhea_stone_bricks", "Rhea Bricks", st)
    body(id="rhea", name="Rhea",
         desc="Saturn's second-largest moon: a quiet, cratered ball of ice and rock.",
         surface=s.id, stone=st.id, temperature=-0.5,
         terrain=dict(base=66, large=10, medium=4, detail=1),
         features=[crater("crater", 4, 12, 0.42, 0.22, chance=3),
                   crater("small_crater", 2, 4, 0.5, 0.2, chance=2),
                   boulder("boulder", "rhea_stone", 1, 2, chance=5)])

    dark = surface("iapetus_dark_regolith", "Dark Iapetus Regolith", 0x3A2A1E, map_color="BLACK")
    bright = surface("iapetus_bright_regolith", "Bright Iapetus Regolith", 0xDCD6CB, map_color="WHITE",
                     style="frost", sound="SNOW")
    st = stone("iapetus_stone", "Iapetus Rock", 0x7A756E)
    bricks("iapetus_stone_bricks", "Iapetus Bricks", st)
    body(id="iapetus", name="Iapetus",
         desc="The two-faced moon: one hemisphere coal-black, the other snow-white, with a great mountain ridge.",
         surface=dark.id, stone=st.id, temperature=-0.5,
         terrain=dict(base=66, large=12, medium=4, detail=1, ridge=30, ridge_bias=-0.1),
         biomes=[BiomeDef("dark", "Iapetus - Cassini Regio", {"temperature": [-1.0, 0.0]}, top=dark.id),
                 BiomeDef("bright", "Iapetus - Roncevaux Terra", {"temperature": [0.0, 1.0]}, top=bright.id)],
         features=[crater("crater", 4, 12, 0.42, 0.22, chance=3)])

    # ------------------------------------------------------------- Uranus' moons
    for mid_id, nm, s_col, st_col, desc, terr, feats in [
        ("miranda", "Miranda", 0xA6A39C, 0x7C7A75,
         "A patchwork moon with the tallest cliffs in the Solar System: Verona Rupes.",
         dict(base=64, large=10, medium=5, detail=1, cliff=40, cliff_sharp=6, canyon=10, canyon_sharp=7),
         [crater("crater", 3, 8, 0.4, 0.2, chance=6)]),
        ("ariel", "Ariel", 0xB4B0A8, 0x86827B,
         "The brightest of Uranus' moons, split by deep rift valleys.",
         dict(base=66, large=8, medium=3, detail=1, canyon=18, canyon_sharp=7),
         [crater("crater", 3, 8, 0.4, 0.2, chance=5)]),
        ("umbriel", "Umbriel", 0x4A4846, 0x353331,
         "The darkest of Uranus' large moons, ancient and covered in craters.",
         dict(base=64, large=8, medium=4, detail=1),
         [crater("large_crater", 5, 13, 0.42, 0.24, chance=2), crater("small_crater", 2, 5, 0.5, 0.2, chance=2)]),
        ("titania", "Titania", 0x9E958C, 0x756D66,
         "Uranus' largest moon, torn by enormous canyons such as Messina Chasma.",
         dict(base=66, large=10, medium=4, detail=1, canyon=22, canyon_sharp=6),
         [crater("crater", 4, 10, 0.42, 0.22, chance=4)]),
        ("oberon", "Oberon", 0x857A72, 0x5F5650,
         "The outermost large moon of Uranus, with craters and a mountain six kilometres high.",
         dict(base=66, large=12, medium=4, detail=1, ridge=26, ridge_bias=-0.4),
         [crater("crater", 4, 12, 0.42, 0.22, chance=3)]),
    ]:
        s = surface(f"{mid_id}_regolith", f"{nm} Regolith", s_col,
                    map_color="BLACK" if s_col < 0x606060 else "LIGHT_GRAY")
        st = stone(f"{mid_id}_stone", f"{nm} Rock", st_col,
                   map_color="DEEPSLATE_GRAY" if st_col < 0x606060 else "STONE_GRAY")
        bricks(f"{mid_id}_stone_bricks", f"{nm} Bricks", st)
        feats.append(boulder("boulder", st.id, 1, 2, chance=5))
        body(id=mid_id, name=nm, desc=desc, surface=s.id, stone=st.id, terrain=terr, features=feats,
             temperature=-0.6, spawns={"monster": [spawn("minecraft:stray", 3, 1, 2)]})

    # ------------------------------------------------------------- Neptune
    s = surface("triton_frost", "Triton Frost", 0xE9D6CF, style="frost", map_color="PINK", sound="SNOW",
                hardness=0.5)
    st = stone("triton_stone", "Triton Ice Rock", 0xA6938C, map_color="TERRACOTTA_WHITE")
    bricks("triton_stone_bricks", "Triton Bricks", st)
    body(id="triton", name="Triton",
         desc="Neptune's captured moon: pink nitrogen frost, 'cantaloupe' terrain and erupting nitrogen geysers.",
         surface=s.id, stone=st.id, temperature=-0.9, patches=[("nitrogen_ice", 0.45)],
         terrain=dict(base=64, large=6, medium=3, detail=2, ridge=5, ridge_bias=1.0),
         features=[disk("nitrogen_ice", "nitrogen_ice", ["triton_frost"], 2, 5, chance=3),
                   column("nitrogen_geyser", "nitrogen_ice", 3, 8, chance=4),
                   crater("crater", 3, 7, 0.35, 0.15, chance=10)],
         spawns={"monster": [spawn("minecraft:stray", 4, 1, 2)]})

    # ------------------------------------------------------------- Pluto & Charon
    frost = surface("pluto_frost", "Pluto Frost", 0xF1E6DC, style="frost", map_color="WHITE", sound="SNOW",
                    hardness=0.5)
    st = stone("pluto_stone", "Pluto Ice Rock", 0x6B5B52, map_color="TERRACOTTA_BROWN")
    bricks("pluto_stone_bricks", "Pluto Bricks", st)
    body(id="pluto", name="Pluto",
         desc="The beloved dwarf planet: a heart-shaped glacier of nitrogen ice beside dark red tholin highlands.",
         surface=frost.id, stone=st.id, temperature=-0.9,
         terrain=dict(base=66, large=14, lowland=-0.1, medium=4, detail=1, ridge=28, ridge_bias=-0.2),
         biomes=[BiomeDef("sputnik_planitia", "Pluto - Sputnik Planitia", {"continentalness": [-1.0, -0.05]},
                          top=frost.id),
                 BiomeDef("cthulhu_macula", "Pluto - Cthulhu Macula", {"continentalness": [-0.05, 1.0]},
                          top="tholin_regolith", sub="tholin_regolith")],
         features=[crater("crater", 3, 9, 0.4, 0.2, chance=6),
                   disk("nitrogen_ice", "nitrogen_ice", ["pluto_frost"], 3, 6, chance=2,
                        biomes=["sputnik_planitia"]),
                   boulder("ice_block", "minecraft:packed_ice", 1, 2, chance=4, biomes=["sputnik_planitia"]),
                   boulder("boulder", "pluto_stone", 1, 3, chance=4, biomes=["cthulhu_macula"])],
         spawns={"monster": [spawn("minecraft:stray", 3, 1, 2)]})

    s = surface("charon_regolith", "Charon Regolith", 0x8B8784, map_color="GRAY")
    st = stone("charon_stone", "Charon Rock", 0x615E5B)
    bricks("charon_stone_bricks", "Charon Bricks", st)
    body(id="charon", name="Charon",
         desc="Pluto's giant moon, with a vast canyon belt and a rust-red polar cap known as Mordor Macula.",
         surface=s.id, stone=st.id, temperature=-0.9, patches=[("tholin_regolith", 0.5)],
         terrain=dict(base=66, large=10, medium=4, detail=1, canyon=24, canyon_sharp=6),
         features=[crater("crater", 4, 11, 0.42, 0.22, chance=3),
                   boulder("boulder", "charon_stone", 1, 2, chance=5)])

    # ------------------------------------------------------------- Kuiper belt
    s = surface("eris_frost", "Eris Frost", 0xF7F7F7, style="frost", map_color="WHITE", sound="SNOW", hardness=0.5)
    st = stone("eris_stone", "Eris Ice Rock", 0xB8B6B4)
    bricks("eris_stone_bricks", "Eris Bricks", st)
    body(id="eris", name="Eris",
         desc="The most massive dwarf planet, out in the dark scattered disc. Coated in gleaming methane frost.",
         surface=s.id, stone=st.id, temperature=-1.0,
         terrain=dict(base=66, large=8, medium=3, detail=1),
         features=[crater("crater", 3, 8, 0.38, 0.18, chance=5),
                   disk("methane_ice", "methane_ice", ["eris_frost"], 2, 5, chance=2)])

    s = surface("haumea_ice", "Haumea Ice", 0xDFF2FC, style="ice", map_color="LIGHT_BLUE", sound="GLASS",
                hardness=0.8, tool="pickaxe", slippery=True)
    st = stone("haumea_stone", "Haumea Crystal Rock", 0xA9C2D2, map_color="LIGHT_BLUE")
    bricks("haumea_stone_bricks", "Haumea Bricks", st)
    body(id="haumea", name="Haumea",
         desc="A fast-spinning, egg-shaped dwarf planet of crystalline water ice. Frost crystals glitter everywhere.",
         surface=s.id, stone=st.id, temperature=-1.0,
         terrain=dict(base=66, large=10, medium=5, detail=1, ridge=12, ridge_bias=0.0),
         features=[cluster("frost_crystals", "frost_crystal_cluster", count=4),
                   column("ice_spire", "minecraft:blue_ice", 3, 8, chance=3),
                   crater("crater", 3, 8, 0.4, 0.2, chance=6)])

    s = surface("makemake_frost", "Makemake Frost", 0xC9967A, style="frost", map_color="TERRACOTTA_ORANGE",
                sound="SNOW", hardness=0.5)
    st = stone("makemake_stone", "Makemake Rock", 0x8E6C5A, map_color="TERRACOTTA_BROWN")
    bricks("makemake_stone_bricks", "Makemake Bricks", st)
    body(id="makemake", name="Makemake",
         desc="A reddish dwarf planet beyond Pluto, frosted with methane and ethane ices.",
         surface=s.id, stone=st.id, temperature=-1.0,
         terrain=dict(base=66, large=8, medium=4, detail=1),
         features=[crater("crater", 3, 9, 0.4, 0.2, chance=4),
                   disk("methane_ice", "methane_ice", ["makemake_frost"], 2, 5, chance=2)])


# =============================================================================== items

ITEMS = {
    # id: (name, art, ramp, secondary, tertiary)
    "star_chart": ("Star Chart", "chart", "paper", "gold", None),
    "rocket_tier_1": ("Tier 1 Rocket", "rocket", "white", "red", "glass"),
    "rocket_tier_2": ("Tier 2 Rocket", "rocket", "titanium", "blue", "glass"),
    "rocket_tier_3": ("Tier 3 Rocket", "rocket", "dark", "gold", "cyan"),
    "rocket_fuel": ("Rocket Fuel", "canister", "red", "flame", "iron"),
    "iron_plating": ("Iron Plating", "plate", "iron", None, None),
    "titanium_plating": ("Titanium Plating", "plate", "titanium", None, None),
    "iridium_plating": ("Iridium Plating", "plate", "iridium", None, None),
    "nose_cone": ("Nose Cone", "nose_cone", "red", None, "iron"),
    "rocket_fin": ("Rocket Fin", "fin", "red", None, "iron"),
    "rocket_engine": ("Rocket Engine", "engine", "iron", "flame", None),
    "advanced_rocket_engine": ("Advanced Rocket Engine", "engine", "titanium", "blue", None),
    "fusion_engine": ("Fusion Engine", "engine", "dark", "cyan", None),
    "space_helmet": ("Space Helmet", "helmet", "white", "red", "glass"),
    "space_suit": ("Space Suit", "suit", "white", "red", "dark"),
    "space_pants": ("Space Pants", "pants", "white", "blue", None),
    "space_boots": ("Space Boots", "boots", "white", "red", "dark"),
    "raw_titanium": ("Raw Titanium", "raw", "titanium_raw", None, None),
    "titanium_ingot": ("Titanium Ingot", "ingot", "titanium", None, None),
    "raw_iridium": ("Raw Iridium", "raw", "iridium_raw", None, None),
    "iridium_ingot": ("Iridium Ingot", "ingot", "iridium", None, None),
    "solar_crystal": ("Solar Crystal", "shard", "solar", None, None),
    "sulfur": ("Sulfur", "dust", "sulfur", None, None),
    "frost_crystal": ("Frost Crystal", "shard", "frost", None, None),
    "astronaut_ice_cream": ("Astronaut Ice Cream", "ice_cream", "wafer", "brown", "pink"),
}

ITEM_TOOLTIPS = {
    "star_chart": "Use to open the star map. Launch from it while seated in a rocket.",
    "rocket_fuel": "Right-click a rocket to fill it up (+25 fuel).",
    "rocket_engine": "Chemical engine. Powers Tier 1 rockets.",
    "advanced_rocket_engine": "Titanium engine. Powers Tier 2 rockets.",
    "fusion_engine": "Iridium fusion drive. Powers Tier 3 rockets.",
}


# =============================================================================== worldgen

def nz(name, xz=1.0, y=0.0):
    return {"type": "minecraft:noise", "noise": name, "xz_scale": xz, "y_scale": y}


def add(*args):
    out = args[0]
    for a in args[1:]:
        out = {"type": "minecraft:add", "argument1": out, "argument2": a}
    return out


def mul(a, b):
    return {"type": "minecraft:mul", "argument1": a, "argument2": b}


def fabs(a):
    return {"type": "minecraft:abs", "argument": a}


def sq(a):
    return {"type": "minecraft:square", "argument": a}


def clamp(a, lo, hi):
    return {"type": "minecraft:clamp", "input": a, "min": lo, "max": hi}


def fmax(a, b):
    return {"type": "minecraft:max", "argument1": a, "argument2": b}


def cache2d(a):
    return {"type": "minecraft:cache_2d", "argument": a}


def interp(a):
    return {"type": "minecraft:interpolated", "argument": a}


def ygrad(from_y, to_y, from_v, to_v):
    return {"type": "minecraft:y_clamped_gradient", "from_y": from_y, "to_y": to_y,
            "from_value": from_v, "to_value": to_v}


NOISES = {
    # name: (firstOctave, amplitudes)
    "large": (-9, [1.0, 1.0, 0.5]),
    "medium": (-7, [1.0, 0.5, 0.25]),
    "detail": (-5, [1.0, 0.5]),
    "ridge": (-8, [1.0, 0.5, 0.25]),
    "canyon": (-8, [1.0, 0.4]),
    "cliff": (-8, [1.0, 0.5]),
    "dunes": (-6, [1.0, 0.3]),
    "patch": (-5, [1.0, 0.5, 0.5]),
    "volume": (-5, [1.0, 0.5, 0.25]),
    "biome": (-9, [1.0, 0.5]),
}


def terrain(b: Body):
    """Returns (final_density, initial_density, continents, erosion, temperature)."""
    n = lambda key, **kw: nz(mid(f"{b.id}/{key}"), **kw)  # noqa: E731
    t = b.terrain
    if b.floating:
        band = sq(ygrad(0, 256, -1.0, 1.0))
        blobs = add(mul(1.5, n("volume", xz=1.0, y=1.6)), -0.42, mul(-2.4, band))
        density = interp(blobs)
        return density, density, n("biome"), 0.0, n("biome")

    large = n("large")
    if t.get("lowland") is not None:
        large = fmax(large, t["lowland"])
    h = add(float(t.get("base", 64)), mul(float(t.get("large", 10)), large))
    if t.get("medium"):
        h = add(h, mul(float(t["medium"]), n("medium")))
    if t.get("detail"):
        h = add(h, mul(float(t["detail"]), n("detail")))
    if t.get("ridge"):
        mask = clamp(add(mul(2.0, n("large")), float(t.get("ridge_bias", 0.0))), 0.0, 1.0)
        ridge = sq(add(1.0, mul(-1.0, fabs(n("ridge")))))
        h = add(h, mul(float(t["ridge"]), mul(mask, ridge)))
    if t.get("canyon"):
        cut = clamp(add(1.0, mul(-float(t.get("canyon_sharp", 7)), fabs(n("canyon")))), 0.0, 1.0)
        h = add(h, mul(-float(t["canyon"]), cut))
    if t.get("cliff"):
        step = clamp(mul(float(t.get("cliff_sharp", 5)), n("cliff")), -1.0, 1.0)
        h = add(h, mul(float(t["cliff"]), step))
    if t.get("dunes"):
        dune = sq(add(1.0, mul(-1.0, fabs(n("dunes", xz=1.0)))))
        h = add(h, mul(float(t["dunes"]), dune))
    height = cache2d(h)
    # (H - y) / 8 : positive below the surface
    base_density = add(mul(height, 0.125), ygrad(-64, 320, 8.0, -40.0))
    final = base_density
    if t.get("overhang"):
        final = add(final, mul(float(t["overhang"]), n("volume", xz=1.0, y=1.0)))
    return interp(final), base_density, n("large"), n("medium"), n("biome")


def surface_rule(b: Body):
    def blk(name):
        return {"type": "minecraft:block", "result_state": state(name)}

    floor0 = {"type": "minecraft:stone_depth", "offset": 0, "add_surface_depth": False,
              "secondary_depth_range": 0, "surface_type": "floor"}
    floor_deep = {"type": "minecraft:stone_depth", "offset": 0, "add_surface_depth": True,
                  "secondary_depth_range": 0, "surface_type": "floor"}
    dry = {"type": "minecraft:water", "offset": -1, "surface_depth_multiplier": 0, "add_stone_depth": False}

    def layers(top, sub):
        top_seq = []
        for block, threshold in b.patches:
            top_seq.append({"type": "minecraft:condition",
                            "if_true": {"type": "minecraft:noise_threshold", "noise": mid(f"{b.id}/patch"),
                                        "min_threshold": threshold, "max_threshold": 10.0},
                            "then_run": blk(block)})
        top_seq.append(blk(top))
        return [
            {"type": "minecraft:condition", "if_true": floor0, "then_run": {"type": "minecraft:sequence", "sequence": [
                {"type": "minecraft:condition", "if_true": {"type": "minecraft:steep"},
                 "then_run": blk(b.steep or b.stone)},
                {"type": "minecraft:condition", "if_true": dry,
                 "then_run": {"type": "minecraft:sequence", "sequence": top_seq}},
                blk(b.underwater or sub),
            ]}},
            {"type": "minecraft:condition", "if_true": floor_deep, "then_run": blk(sub)},
        ]

    seq = []
    if not b.floating:
        seq.append({"type": "minecraft:condition", "if_true": {
            "type": "minecraft:vertical_gradient", "random_name": mid(f"{b.id}/bedrock_floor"),
            "true_at_and_below": {"above_bottom": 0}, "false_at_and_above": {"above_bottom": 5}},
                    "then_run": blk("minecraft:bedrock")})
    default_sub = b.sub or b.surface
    for biome in b.biomes:
        if biome.top or biome.sub:
            seq.append({"type": "minecraft:condition",
                        "if_true": {"type": "minecraft:biome", "biome_is": [biome_id(b, biome)]},
                        "then_run": {"type": "minecraft:sequence",
                                     "sequence": layers(biome.top or b.surface, biome.sub or default_sub)}})
    seq += layers(b.surface, default_sub)
    return {"type": "minecraft:sequence", "sequence": seq}


def biome_id(b: Body, biome: BiomeDef) -> str:
    return mid(b.id if not biome.suffix else f"{b.id}_{biome.suffix}")


def write_worldgen():
    out = DATA
    # shared carver
    write_json(os.path.join(out, "worldgen", "configured_carver", "lava_tubes.json"), {
        "type": "minecraft:cave",
        "config": {
            "probability": 0.09,
            "y": {"type": "minecraft:uniform", "min_inclusive": {"above_bottom": 8},
                  "max_inclusive": {"absolute": 140}},
            "yScale": {"type": "minecraft:uniform", "min_inclusive": 0.2, "max_exclusive": 0.9},
            "lava_level": {"above_bottom": 4},
            "replaceable": f"#{NS}:carver_replaceables",
            "horizontal_radius_multiplier": {"type": "minecraft:uniform", "min_inclusive": 0.8,
                                             "max_exclusive": 1.6},
            "vertical_radius_multiplier": {"type": "minecraft:uniform", "min_inclusive": 0.8,
                                           "max_exclusive": 1.3},
            "floor_level": {"type": "minecraft:uniform", "min_inclusive": -1.0, "max_exclusive": -0.4},
        },
    })

    for b in BODIES:
        # noise parameters
        for key, (octave, amps) in NOISES.items():
            write_json(os.path.join(out, "worldgen", "noise", b.id, f"{key}.json"),
                       {"firstOctave": octave, "amplitudes": amps})

        final, initial, continents, erosion, temperature = terrain(b)
        router = {
            "barrier": 0.0, "fluid_level_floodedness": 0.0, "fluid_level_spread": 0.0, "lava": 0.0,
            "temperature": temperature, "vegetation": 0.0, "continents": continents, "erosion": erosion,
            "depth": 0.0, "ridges": 0.0, "initial_density_without_jaggedness": initial, "final_density": final,
            "vein_toggle": 0.0, "vein_ridged": 0.0, "vein_gap": 0.0,
        }
        write_json(os.path.join(out, "worldgen", "noise_settings", f"{b.id}.json"), {
            "sea_level": b.sea_level,
            "disable_mob_generation": False,
            "aquifers_enabled": False,
            "ore_veins_enabled": False,
            "legacy_random_source": False,
            "default_block": state(b.stone),
            "default_fluid": state(b.fluid, {"level": "0"}),
            "noise": {"min_y": 0, "height": 256, "size_horizontal": 1, "size_vertical": 2},
            "noise_router": router,
            "spawn_target": [],
            "surface_rule": surface_rule(b),
        })

        write_json(os.path.join(out, "dimension_type", f"{b.id}.json"), {
            "ultrawarm": b.ultrawarm, "natural": False, "piglin_safe": False, "respawn_anchor_works": False,
            "bed_works": True, "has_raids": False, "has_skylight": True, "has_ceiling": False,
            "coordinate_scale": 1.0, "ambient_light": 0.0, "logical_height": 256, "effects": mid(b.id),
            "infiniburn": "#minecraft:infiniburn_overworld", "min_y": 0, "height": 256,
            "monster_spawn_light_level": {"type": "minecraft:uniform", "min_inclusive": 0, "max_inclusive": 7},
            "monster_spawn_block_light_limit": 0,
        })

        if len(b.biomes) == 1:
            source = {"type": "minecraft:fixed", "biome": biome_id(b, b.biomes[0])}
        else:
            entries = []
            for biome in b.biomes:
                p = {"temperature": [-1.0, 1.0], "humidity": [-1.0, 1.0], "continentalness": [-1.0, 1.0],
                     "erosion": [-1.0, 1.0], "weirdness": [-1.0, 1.0], "depth": 0.0, "offset": 0.0}
                p.update(biome.params or {})
                entries.append({"biome": biome_id(b, biome), "parameters": p})
            source = {"type": "minecraft:multi_noise", "biomes": entries}
        write_json(os.path.join(out, "dimension", f"{b.id}.json"), {
            "type": mid(b.id),
            "generator": {"type": "minecraft:noise", "settings": mid(b.id), "biome_source": source},
        })

        # features
        steps = {}
        for f in b.features:
            if f.configured is None:  # vanilla freeze_top_layer
                fid = FREEZE
            else:
                fid = mid(f"{b.id}/{f.name}")
                write_json(os.path.join(out, "worldgen", "configured_feature", b.id, f"{f.name}.json"), f.configured)
                write_json(os.path.join(out, "worldgen", "placed_feature", b.id, f"{f.name}.json"),
                           {"feature": fid, "placement": f.placement})
            steps.setdefault(f.step, []).append((fid, f.biomes))

        for biome in b.biomes:
            features = [[] for _ in range(11)]
            for step, entries in steps.items():
                for fid, only in entries:
                    if only is None or biome.suffix in only:
                        features[step].append(fid)
            effects = {"sky_color": b.sky, "fog_color": b.fog, "water_color": b.water,
                       "water_fog_color": b.water_fog,
                       "mood_sound": {"sound": "minecraft:ambient.cave", "tick_delay": 6000,
                                      "block_search_extent": 8, "offset": 2.0}}
            if b.particle:
                effects["particle"] = {"options": {"type": b.particle[0]}, "probability": b.particle[1]}
            spawners = {k: [] for k in ["monster", "creature", "ambient", "axolotls", "underground_water_creature",
                                        "water_creature", "water_ambient", "misc"]}
            for k, v in b.spawns.items():
                spawners[k] = v
            path = biome_id(b, biome).split(":")[1]
            write_json(os.path.join(out, "worldgen", "biome", f"{path}.json"), {
                "has_precipitation": False,
                "temperature": b.temperature,
                "downfall": 0.0,
                "effects": effects,
                "spawners": spawners,
                "spawn_costs": {},
                "carvers": {"air": [mid("lava_tubes")]} if b.caves else {},
                "features": features,
            })
            LANG[f"biome.{NS}.{path}"] = biome.name


# =============================================================================== assets

def block_texture(b: BlockDef):
    if b.style == "ore":
        base = BLOCK_BY_ID[b.ore_base]
        base_tex = tx.BLOCK_STYLES[base.style](base.id, base.color)
        return tx.tex_ore(b.id, base_tex, b.ore_colors)
    if b.style == "cluster":
        return tx.tex_cluster(b.id, b.color)
    return tx.BLOCK_STYLES[b.style](b.id, b.color)


def write_block_assets():
    for b in BLOCKS:
        save_png(os.path.join(ASSETS, "textures", "block", f"{b.id}.png"), block_texture(b))
        model = mid(f"block/{b.id}")
        if b.kind == "cluster":
            write_json(os.path.join(ASSETS, "models", "block", f"{b.id}.json"),
                       {"parent": "minecraft:block/cross", "textures": {"cross": model}})
            variants = {}
            for facing, rot in {"down": {"x": 180}, "east": {"x": 90, "y": 90}, "north": {"x": 90},
                                "south": {"x": 90, "y": 180}, "up": {}, "west": {"x": 90, "y": 270}}.items():
                variants[f"facing={facing}"] = dict({"model": model}, **rot)
            write_json(os.path.join(ASSETS, "blockstates", f"{b.id}.json"), {"variants": variants})
            write_json(os.path.join(ASSETS, "models", "item", f"{b.id}.json"),
                       {"parent": "minecraft:item/generated", "textures": {"layer0": model}})
        else:
            write_json(os.path.join(ASSETS, "models", "block", f"{b.id}.json"),
                       {"parent": "minecraft:block/cube_all", "textures": {"all": model}})
            if b.rotate:
                variant = [{"model": model}, {"model": model, "y": 90}, {"model": model, "y": 180},
                           {"model": model, "y": 270}]
            else:
                variant = {"model": model}
            write_json(os.path.join(ASSETS, "blockstates", f"{b.id}.json"), {"variants": {"": variant}})
            write_json(os.path.join(ASSETS, "models", "item", f"{b.id}.json"), {"parent": model})
        LANG[f"block.{NS}.{b.id}"] = b.name


def write_item_assets():
    for item_id, (name, art, ramp, secondary, tertiary) in ITEMS.items():
        save_png(os.path.join(ASSETS, "textures", "item", f"{item_id}.png"),
                 tx.render_art(art, ramp, secondary, tertiary))
        write_json(os.path.join(ASSETS, "models", "item", f"{item_id}.json"),
                   {"parent": "minecraft:item/generated", "textures": {"layer0": mid(f"item/{item_id}")}})
        LANG[f"item.{NS}.{item_id}"] = name
    for item_id, tip in ITEM_TOOLTIPS.items():
        LANG[f"item.{NS}.{item_id}.tooltip"] = tip


def write_entity_and_armor_textures():
    for tier, (body_c, accent, metal) in {1: (0xE8E8E8, 0xC83A2E, 0x8A9098),
                                         2: (0xB9C4CF, 0x2E6FC8, 0x6A7480),
                                         3: (0x4A4E57, 0xD9A93A, 0x2A2D33)}.items():
        save_png(os.path.join(ASSETS, "textures", "entity", "rocket", f"tier_{tier}.png"),
                 tx.rocket_texture(body_c, accent, metal))
    save_png(os.path.join(ASSETS, "textures", "models", "armor", "space_suit_layer_1.png"), tx.armor_layer(1))
    save_png(os.path.join(ASSETS, "textures", "models", "armor", "space_suit_layer_2.png"), tx.armor_layer(2))


SPHERES = {
    # id: (surface function, halo colour)
    "earth": (tx.earthlike(), 0x7AB8FF),
    "moon": (tx.rocky(0x9B9B9B, 0.2, dark=0x5A5A5A, dark_amount=0.45, crater_count=30), None),
    "mercury": (tx.rocky(0x8C8680, 0.22, crater_count=40), None),
    "venus": (tx.banded([0xE8D2A0, 0xDCC088, 0xEAD8AE, 0xD8B878], turbulence=0.5, bands=5, storms=0.1), 0xF0E0B0),
    "mars": (tx.rocky(0xC1502A, 0.18, dark=0x6A2C18, dark_amount=0.4, crater_count=12, bright=0xF4F0EA,
                      bright_amount=0.0), 0xE8B090),
    "phobos": (tx.rocky(0x6B605A, 0.25, crater_count=20), None),
    "deimos": (tx.rocky(0x9A8C7C, 0.15, crater_count=8), None),
    "ceres": (tx.rocky(0x6A6A6E, 0.2, crater_count=30, bright=0xF8F8F0, bright_amount=0.06), None),
    "vesta": (tx.rocky(0xA89E90, 0.22, dark=0x6A6058, dark_amount=0.3, crater_count=25), None),
    "psyche": (tx.rocky(0x9A9CA2, 0.25, crater_count=18), None),
    "bennu": (tx.rocky(0x3A3634, 0.35, crater_count=10, seed_scale=6.0), None),
    "jupiter": (tx.banded([0xE8D8C0, 0xC89A6A, 0xF0E4D0, 0xB07A50, 0xE0C8A8, 0x9A6A48], turbulence=0.18, bands=11,
                          spot=(0.35, -0.38, 0.16, 0xC0503A), storms=0.12), None),
    "io": (tx.rocky(0xE8D44A, 0.25, dark=0x8A4A1A, dark_amount=0.25, crater_count=0, bright=0xFFF8D0,
                    bright_amount=0.15), None),
    "europa": (tx.icy_lines(0xE2DACC, 0x9A5A3A, count=45), None),
    "ganymede": (tx.two_tone(0x6A6058, 0xB4AA9E, threshold=0.48, scale=2.0), None),
    "callisto": (tx.rocky(0x5C564F, 0.25, crater_count=45, bright=0xD8D4CC, bright_amount=0.05), None),
    "saturn": (tx.banded([0xEAD8A8, 0xD8C088, 0xF0E2BC, 0xC8AA70, 0xE4D0A0], turbulence=0.08, bands=13), None),
    "titan": (tx.banded([0xD99A3C, 0xC88A30, 0xE0A850], turbulence=0.3, bands=3), 0xE8B060),
    "enceladus": (tx.icy_lines(0xF4F8FC, 0x8AC0E8, count=12, variance=0.05), None),
    "mimas": (tx.rocky(0xBAB8B2, 0.15, crater_count=25), None),
    "rhea": (tx.rocky(0xC6C0B8, 0.15, crater_count=30), None),
    "iapetus": (tx.two_tone(0x3A2A1E, 0xE0DCD2, threshold=0.5, scale=0.6, sharpness=5), None),
    "uranus": (tx.banded([0xA8DCE4, 0x9AD4DE, 0xB4E4EA], turbulence=0.05, bands=4), 0xC8F0F4),
    "miranda": (tx.two_tone(0x8A8780, 0xC0BDB6, threshold=0.5, scale=3.0, sharpness=12), None),
    "ariel": (tx.rocky(0xB6B2AA, 0.15, crater_count=15), None),
    "umbriel": (tx.rocky(0x4C4A48, 0.15, crater_count=30), None),
    "titania": (tx.rocky(0xA0978E, 0.18, crater_count=20), None),
    "oberon": (tx.rocky(0x887D74, 0.2, crater_count=28), None),
    "neptune": (tx.banded([0x3A5CD0, 0x4A70E0, 0x3050C0, 0x5A80E8], turbulence=0.12, bands=6,
                          spot=(-0.3, -0.2, 0.1, 0x1A2A80)), 0x80A0FF),
    "triton": (tx.two_tone(0xE8D2CC, 0xC8B0A8, threshold=0.45, scale=4.0, sharpness=10, variance=0.1), None),
    "pluto": (tx.pluto_surface(), None),
    "charon": (tx.charon_surface(), None),
    "eris": (tx.rocky(0xF4F4F4, 0.06, crater_count=6), None),
    "haumea": (tx.rocky(0xE2F2FC, 0.08, crater_count=4, dark=0xA05050, dark_amount=0.08), None),
    "makemake": (tx.rocky(0xC8957A, 0.12, crater_count=6), None),
    "dysnomia": (tx.rocky(0x6A6866, 0.2, crater_count=10), None),
    "hiiaka": (tx.rocky(0xD8E0E8, 0.1, crater_count=5), None),
}


def write_sky_textures():
    env = os.path.join(ASSETS, "textures", "environment")
    for i, face in enumerate(tx.skybox_faces(256, GALACTIC_NORMAL)):
        save_png(os.path.join(env, "space", f"skybox_{i}.png"), face)
    save_png(os.path.join(env, "sun_core.png"), tx.sun_texture(64, core=True))
    save_png(os.path.join(env, "sun_glow.png"), tx.sun_texture(128, core=False))
    save_png(os.path.join(env, "phases.png"), tx.phase_sheet())
    save_png(os.path.join(env, "saturn_rings.png"), tx.ring_texture(256, [
        (0.47, 0.55, 0.25, 0xA89A80), (0.55, 0.78, 0.9, 0xE8DCC0), (0.78, 0.81, 0.06, 0x806850),
        (0.81, 0.915, 0.7, 0xD8CAA8), (0.915, 0.925, 0.1, 0x807060), (0.925, 0.97, 0.6, 0xD0C0A0)]))
    save_png(os.path.join(env, "uranus_rings.png"), tx.ring_texture(256, [
        (0.70, 0.71, 0.5, 0x9AA0A8), (0.76, 0.77, 0.5, 0x9AA0A8), (0.82, 0.83, 0.6, 0xA8B0B8),
        (0.94, 0.965, 0.85, 0xB8C0C8)]))
    for body_id, (fn, halo) in SPHERES.items():
        save_png(os.path.join(env, "bodies", f"{body_id}.png"),
                 tx.sphere(128, fn, tx.seed_of(body_id), radius=0.94, halo=halo))


def write_gui_textures():
    gui = os.path.join(ASSETS, "textures", "gui", "systems")
    env = os.path.join(ASSETS, "textures", "environment", "bodies")
    from PIL import Image
    import numpy as np

    def body_icon(name, size=32):
        img = Image.open(os.path.join(env, f"{name}.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
        return np.array(img, dtype=np.float64)

    def ringed(name, ring, tilt=0.35, alpha=1.0):
        canvas = np.zeros((32, 32, 4))
        planet = Image.open(os.path.join(env, f"{name}.png")).convert("RGBA").resize((20, 20), Image.LANCZOS)
        rimg = Image.open(os.path.join(ASSETS, "textures", "environment", ring)).convert("RGBA")
        rimg = rimg.resize((32, max(2, int(32 * tilt))), Image.LANCZOS)
        r = np.array(rimg, dtype=np.float64)
        r[..., 3] *= alpha
        p = np.array(planet, dtype=np.float64)
        top = (32 - r.shape[0]) // 2
        h = r.shape[0]
        back = r.copy()
        back[h // 2:, :, 3] = 0
        front = r.copy()
        front[:h // 2, :, 3] = 0

        def over(dst, src, y, x):
            hh, ww = src.shape[:2]
            region = dst[y:y + hh, x:x + ww]
            a = src[..., 3:4] / 255
            region[..., :3] = src[..., :3] * a + region[..., :3] * (1 - a)
            region[..., 3:4] = np.maximum(region[..., 3:4], src[..., 3:4])

        over(canvas, back, top, 0)
        over(canvas, p, 6, 6)
        over(canvas, front, top, 0)
        return canvas

    def rocks(colors, seed):
        import numpy as np
        r = np.random.default_rng(seed)
        canvas = np.zeros((32, 32, 4))
        for i, c in enumerate(colors):
            cx, cy = [(10, 12), (21, 9), (17, 21), (8, 23), (24, 22)][i % 5]
            rad = 3 + r.random() * 3
            col = tx.rgb(c)
            for y in range(32):
                for x in range(32):
                    d = math.hypot((x - cx) / 1.2, y - cy)
                    if d < rad:
                        shade = 0.7 + 0.5 * (1 - d / rad) - (x - cx) * 0.02
                        canvas[y, x, :3] = np.clip(col * shade, 0, 255)
                        canvas[y, x, 3] = 255
        return canvas

    for name in ["mercury", "venus", "earth", "mars", "jupiter", "neptune", "pluto"]:
        save_png(os.path.join(gui, f"{name}.png"), body_icon(name))
    save_png(os.path.join(gui, "saturn.png"), ringed("saturn", "saturn_rings.png"))
    save_png(os.path.join(gui, "uranus.png"), ringed("uranus", "uranus_rings.png", tilt=0.9, alpha=0.8))
    save_png(os.path.join(gui, "asteroids.png"), rocks([0x8A847C, 0x6A6A6E, 0xA89E90, 0x9A9CA2], 3))
    save_png(os.path.join(gui, "kuiper.png"), rocks([0xF4F4F4, 0xC8957A, 0xE2F2FC], 5))
    save_png(os.path.join(gui, "sun.png"), tx.sun_texture(32, core=True))


def write_icon():
    import numpy as np
    from PIL import Image
    size = 128
    img = np.zeros((size, size, 4))
    img[..., 3] = 255
    r = np.random.default_rng(11)
    for _ in range(140):
        x, y = r.integers(0, size, 2)
        b = r.integers(90, 255)
        img[y, x, :3] = b
    planet = tx.sphere(80, SPHERES["saturn"][0], tx.seed_of("saturn"))
    rings = Image.open(os.path.join(ASSETS, "textures", "environment", "saturn_rings.png")).convert("RGBA")
    rings = np.array(rings.resize((128, 36), Image.LANCZOS), dtype=np.float64)

    def over(dst, src, y, x):
        hh, ww = src.shape[:2]
        region = dst[y:y + hh, x:x + ww]
        a = src[..., 3:4] / 255
        region[..., :3] = src[..., :3] * a + region[..., :3] * (1 - a)

    back = rings.copy()
    back[18:, :, 3] = 0
    front = rings.copy()
    front[:18, :, 3] = 0
    over(img, back, 50, 0)
    over(img, planet, 28, 24)
    over(img, front, 50, 0)
    rocket = tx.render_art("rocket", "white", "red", "glass")
    big = np.kron(rocket, np.ones((3, 3, 1)))
    over(img, big, 76, 76)
    save_png(os.path.join(ASSETS, "icon.png"), img)


# =============================================================================== data (loot, tags, recipes...)

def write_loot_tables():
    for b in BLOCKS:
        path = os.path.join(DATA, "loot_table", "blocks", f"{b.id}.json")
        if b.drop is None:
            entry = {"type": "minecraft:item", "name": mid(b.id)}
            pool = {"rolls": 1, "bonus_rolls": 0, "entries": [entry],
                    "conditions": [{"condition": "minecraft:survives_explosion"}]}
        else:
            functions = []
            if b.drop.get("max", 1) > 1:
                functions.append({"function": "minecraft:set_count",
                                  "count": {"type": "minecraft:uniform", "min": float(b.drop.get("min", 1)),
                                            "max": float(b.drop["max"])}, "add": False})
            functions += [{"function": "minecraft:apply_bonus", "enchantment": "minecraft:fortune",
                           "formula": "minecraft:ore_drops"},
                          {"function": "minecraft:explosion_decay"}]
            silk = {"condition": "minecraft:match_tool", "predicate": {"predicates": {"minecraft:enchantments": [
                {"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}]}}}
            pool = {"rolls": 1, "bonus_rolls": 0, "entries": [{"type": "minecraft:alternatives", "children": [
                {"type": "minecraft:item", "name": mid(b.id), "conditions": [silk]},
                {"type": "minecraft:item", "name": b.drop["item"], "functions": functions}]}]}
        write_json(path, {"type": "minecraft:block", "pools": [pool], "random_sequence": mid(f"blocks/{b.id}")})


def tag(path, values):
    write_json(path, {"replace": False, "values": sorted(set(values))})


def write_tags():
    pick = [mid(b.id) for b in BLOCKS if b.tool == "pickaxe"]
    shovel = [mid(b.id) for b in BLOCKS if b.tool == "shovel"]
    stone_tool = [mid(b.id) for b in BLOCKS if b.level == 1]
    iron_tool = [mid(b.id) for b in BLOCKS if b.level == 2]
    tag(os.path.join(DATA_MC, "tags", "block", "mineable", "pickaxe.json"), pick)
    tag(os.path.join(DATA_MC, "tags", "block", "mineable", "shovel.json"), shovel)
    tag(os.path.join(DATA_MC, "tags", "block", "needs_stone_tool.json"), stone_tool)
    tag(os.path.join(DATA_MC, "tags", "block", "needs_iron_tool.json"), iron_tool)
    extra = {}
    for b in BLOCKS:
        for t in b.extra_tags:
            extra.setdefault(t, []).append(mid(b.id))
    for t, values in extra.items():
        ns, path = t.split(":")
        tag(os.path.join(RES, "data", ns, "tags", "block", f"{path}.json"), values)
    carvable = [mid(b.id) for b in BLOCKS if b.carvable] + ["minecraft:packed_ice", "minecraft:blue_ice"]
    tag(os.path.join(DATA, "tags", "block", "carver_replaceables.json"), carvable)
    tag(os.path.join(DATA_MC, "tags", "damage_type", "bypasses_armor.json"), [mid("vacuum")])
    tag(os.path.join(DATA_MC, "tags", "damage_type", "no_knockback.json"), [mid("vacuum")])
    # Common (convention) tags for compatibility with other mods.
    tag(os.path.join(DATA_C, "tags", "item", "ingots", "titanium.json"), [mid("titanium_ingot")])
    tag(os.path.join(DATA_C, "tags", "item", "ingots", "iridium.json"), [mid("iridium_ingot")])
    tag(os.path.join(DATA_C, "tags", "item", "raw_materials", "titanium.json"), [mid("raw_titanium")])
    tag(os.path.join(DATA_C, "tags", "item", "raw_materials", "iridium.json"), [mid("raw_iridium")])
    tag(os.path.join(DATA_C, "tags", "item", "ores", "titanium.json"),
        [mid("moon_titanium_ore"), mid("mars_titanium_ore")])
    tag(os.path.join(DATA_C, "tags", "item", "ores", "iridium.json"), [mid("psyche_iridium_ore")])
    tag(os.path.join(DATA_C, "tags", "item", "dusts", "sulfur.json"), [mid("sulfur")])
    tag(os.path.join(DATA_C, "tags", "block", "ores", "titanium.json"),
        [mid("moon_titanium_ore"), mid("mars_titanium_ore")])
    tag(os.path.join(DATA_C, "tags", "block", "ores", "iridium.json"), [mid("psyche_iridium_ore")])


def ing(x):
    if x.startswith("#"):
        return {"tag": x[1:]}
    return {"item": x if ":" in x else mid(x)}


def shaped(name, pattern, key, result, count=1, category="misc"):
    write_json(os.path.join(DATA, "recipe", f"{name}.json"), {
        "type": "minecraft:crafting_shaped", "category": category, "pattern": pattern,
        "key": {k: ing(v) for k, v in key.items()},
        "result": {"id": result if ":" in result else mid(result), "count": count}})


def shapeless(name, ingredients, result, count=1, category="misc"):
    write_json(os.path.join(DATA, "recipe", f"{name}.json"), {
        "type": "minecraft:crafting_shapeless", "category": category,
        "ingredients": [ing(i) for i in ingredients],
        "result": {"id": result if ":" in result else mid(result), "count": count}})


def cooking(name, ingredient, result, xp, kind="smelting", time=200):
    write_json(os.path.join(DATA, "recipe", f"{name}.json"), {
        "type": f"minecraft:{kind}", "category": "misc", "ingredient": ing(ingredient),
        "result": {"id": result if ":" in result else mid(result)}, "experience": xp,
        "cookingtime": time if kind == "smelting" else time // 2})


def stonecutting(name, ingredient, result, count=1):
    write_json(os.path.join(DATA, "recipe", f"{name}.json"), {
        "type": "minecraft:stonecutting", "ingredient": ing(ingredient),
        "result": {"id": result if ":" in result else mid(result), "count": count}})


def write_recipes():
    shaped("iron_plating", ["II", "II"], {"I": "minecraft:iron_ingot"}, "iron_plating")
    shaped("titanium_plating", ["II", "II"], {"I": "titanium_ingot"}, "titanium_plating")
    shaped("iridium_plating", ["II", "II"], {"I": "iridium_ingot"}, "iridium_plating")
    shaped("nose_cone", [" P ", "PRP", "PPP"], {"P": "iron_plating", "R": "minecraft:redstone_torch"}, "nose_cone")
    shaped("rocket_fin", ["I  ", "II ", "III"], {"I": "minecraft:iron_ingot"}, "rocket_fin", 2)
    shaped("rocket_engine", [" P ", "PBP", "F F"],
           {"P": "iron_plating", "B": "minecraft:blast_furnace", "F": "minecraft:fire_charge"}, "rocket_engine")
    shaped("advanced_rocket_engine", [" T ", "TET", "SCS"],
           {"T": "titanium_plating", "E": "rocket_engine", "S": "sulfur", "C": "solar_crystal"},
           "advanced_rocket_engine")
    shaped("fusion_engine", [" R ", "RER", "MCM"],
           {"R": "iridium_plating", "E": "advanced_rocket_engine", "M": "methane_ice",
            "C": "solar_crystal_block"}, "fusion_engine")
    shaped("rocket_tier_1", [" N ", "PGP", "FEF"],
           {"N": "nose_cone", "P": "iron_plating", "G": "minecraft:glass_pane", "F": "rocket_fin",
            "E": "rocket_engine"}, "rocket_tier_1", category="misc")
    shaped("rocket_tier_2", [" T ", "TRT", "TAT"],
           {"T": "titanium_plating", "R": "rocket_tier_1", "A": "advanced_rocket_engine"}, "rocket_tier_2")
    shaped("rocket_tier_3", [" I ", "IRI", "IFI"],
           {"I": "iridium_plating", "R": "rocket_tier_2", "F": "fusion_engine"}, "rocket_tier_3")
    shapeless("rocket_fuel", ["minecraft:iron_ingot", "#minecraft:coals", "#minecraft:coals",
                              "minecraft:blaze_powder"], "rocket_fuel")
    shapeless("rocket_fuel_from_sulfur", ["minecraft:iron_ingot", "sulfur", "sulfur", "#minecraft:coals"],
              "rocket_fuel")
    shapeless("rocket_fuel_from_methane", ["minecraft:iron_ingot", "methane_ice", "methane_ice"], "rocket_fuel", 2)
    shaped("space_helmet", ["WIW", "WGW"],
           {"W": "minecraft:white_wool", "I": "minecraft:iron_ingot", "G": "minecraft:glass_pane"}, "space_helmet",
           category="equipment")
    shaped("space_suit", ["W W", "IWI", "WWW"], {"W": "minecraft:white_wool", "I": "minecraft:iron_ingot"},
           "space_suit", category="equipment")
    shaped("space_pants", ["WIW", "W W", "W W"], {"W": "minecraft:white_wool", "I": "minecraft:iron_ingot"},
           "space_pants", category="equipment")
    shaped("space_boots", ["W W", "I I"], {"W": "minecraft:white_wool", "I": "minecraft:iron_ingot"},
           "space_boots", category="equipment")
    shapeless("star_chart", ["minecraft:map", "minecraft:compass", "minecraft:glowstone_dust"], "star_chart")
    shapeless("astronaut_ice_cream", ["minecraft:sugar", "minecraft:snowball", "minecraft:cocoa_beans"],
              "astronaut_ice_cream", 2)
    shapeless("gunpowder_from_sulfur", ["sulfur", "sulfur", "#minecraft:coals"], "minecraft:gunpowder", 2)
    shaped("launch_pad", ["CCC", "III"], {"C": "minecraft:smooth_stone", "I": "minecraft:iron_ingot"},
           "launch_pad", 6, category="building")

    for metal in ["titanium", "iridium"]:
        cooking(f"{metal}_ingot_from_raw", f"raw_{metal}", f"{metal}_ingot", 0.8)
        cooking(f"{metal}_ingot_from_raw_blasting", f"raw_{metal}", f"{metal}_ingot", 0.8, "blasting")
        shaped(f"{metal}_block", ["III", "III", "III"], {"I": f"{metal}_ingot"}, f"{metal}_block",
               category="building")
        shapeless(f"{metal}_ingot_from_block", [f"{metal}_block"], f"{metal}_ingot", 9)
    shaped("sulfur_block", ["SSS", "SSS", "SSS"], {"S": "sulfur"}, "sulfur_block", category="building")
    shapeless("sulfur_from_block", ["sulfur_block"], "sulfur", 9)
    shaped("solar_crystal_block", ["CC", "CC"], {"C": "solar_crystal"}, "solar_crystal_block", category="building")
    shaped("frost_crystal_block", ["CC", "CC"], {"C": "frost_crystal"}, "frost_crystal_block", category="building")

    # Ores can be smelted directly (e.g. after mining with Silk Touch).
    for b in BLOCKS:
        if b.style == "ore" and b.drop:
            target = {mid("raw_titanium"): mid("titanium_ingot"), mid("raw_iridium"): mid("iridium_ingot"),
                      "minecraft:raw_iron": "minecraft:iron_ingot", "minecraft:raw_gold": "minecraft:gold_ingot"
                      }.get(b.drop["item"], b.drop["item"])
            cooking(f"{target.split(':')[1]}_from_smelting_{b.id}", b.id, target, 0.7)
            cooking(f"{target.split(':')[1]}_from_blasting_{b.id}", b.id, target, 0.7, "blasting")

    # Bricks from every planet stone.
    for b in BLOCKS:
        if b.stone_for_bricks:
            shaped(b.id, ["SS", "SS"], {"S": b.stone_for_bricks}, b.id, 4, category="building")
            stonecutting(f"{b.id}_from_stonecutting", b.stone_for_bricks, b.id)


def write_damage_type():
    write_json(os.path.join(DATA, "damage_type", "vacuum.json"),
               {"message_id": f"{NS}.vacuum", "scaling": "never", "exhaustion": 0.0})
    LANG[f"death.attack.{NS}.vacuum"] = "%1$s tried to breathe in space"
    LANG[f"death.attack.{NS}.vacuum.player"] = "%1$s tried to breathe in space while fighting %2$s"


ADVANCEMENTS = []


def advancement(name, parent, icon, title, description, criteria, frame="task", requirements=None, hidden=False,
                xp=None):
    adv = {"display": {"icon": {"id": icon if ":" in icon else mid(icon)},
                       "title": {"translate": f"advancements.{NS}.{name}.title"},
                       "description": {"translate": f"advancements.{NS}.{name}.description"},
                       "frame": frame, "show_toast": True, "announce_to_chat": True, "hidden": hidden},
           "criteria": criteria}
    if parent:
        adv["parent"] = mid(parent)
    else:
        adv["display"]["background"] = f"{NS}:textures/block/moon_regolith.png"
        adv["display"]["show_toast"] = False
        adv["display"]["announce_to_chat"] = False
    if requirements:
        adv["requirements"] = requirements
    if xp:
        adv["rewards"] = {"experience": xp}
    write_json(os.path.join(DATA, "advancement", f"{name}.json"), adv)
    LANG[f"advancements.{NS}.{name}.title"] = title
    LANG[f"advancements.{NS}.{name}.description"] = description


def visit(*bodies):
    return {f"visit_{b}": {"trigger": "minecraft:changed_dimension", "conditions": {"to": mid(b)}} for b in bodies}


def has(*items):
    return {f"has_{i}": {"trigger": "minecraft:inventory_changed",
                         "conditions": {"items": [{"items": mid(i)}]}} for i in items}


def write_advancements():
    advancement("root", None, "rocket_tier_1", "Interplanetary Stuff", "The Solar System awaits",
                {"tick": {"trigger": "minecraft:tick"}})
    advancement("suit_up", "root", "space_helmet", "Suited Up", "Craft all four pieces of the space suit",
                has("space_helmet", "space_suit", "space_pants", "space_boots"))
    advancement("rocket_science", "root", "rocket_tier_1", "Rocket Science", "Build a Tier 1 Rocket",
                has("rocket_tier_1"))
    advancement("moon", "rocket_science", "moon_regolith", "One Small Step", "Land on the Moon", visit("moon"))
    advancement("mercury", "moon", "solar_crystal", "Too Close for Comfort", "Visit Mercury", visit("mercury"))
    advancement("venus", "moon", "venus_soil", "Under Pressure", "Visit Venus", visit("venus"))
    advancement("mars", "moon", "mars_sand", "The Red Planet", "Visit Mars", visit("mars"))
    advancement("mars_moons", "mars", "phobos_regolith", "Fear and Dread", "Visit Phobos and Deimos",
                visit("phobos", "deimos"))
    advancement("tier_2", "moon", "rocket_tier_2", "Titanium Tested", "Build a Tier 2 Rocket", has("rocket_tier_2"))
    advancement("asteroids", "tier_2", "psyche_nickel_iron", "Rock Hopper", "Land on any asteroid or Ceres",
                visit("ceres", "vesta", "psyche", "bennu"),
                requirements=[["visit_ceres", "visit_vesta", "visit_psyche", "visit_bennu"]])
    advancement("jupiter", "tier_2", "io_sulfur_crust", "King of the Planets", "Visit any moon of Jupiter",
                visit("io", "europa", "ganymede", "callisto"),
                requirements=[["visit_io", "visit_europa", "visit_ganymede", "visit_callisto"]])
    advancement("saturn", "tier_2", "titan_sand", "Lord of the Rings", "Visit any moon of Saturn",
                visit("titan", "enceladus", "mimas", "rhea", "iapetus"),
                requirements=[["visit_titan", "visit_enceladus", "visit_mimas", "visit_rhea", "visit_iapetus"]])
    advancement("tier_3", "tier_2", "rocket_tier_3", "Fusion Powered", "Build a Tier 3 Rocket", has("rocket_tier_3"))
    advancement("uranus", "tier_3", "miranda_regolith", "Sideways World", "Visit any moon of Uranus",
                visit("miranda", "ariel", "umbriel", "titania", "oberon"),
                requirements=[["visit_miranda", "visit_ariel", "visit_umbriel", "visit_titania", "visit_oberon"]])
    advancement("neptune", "tier_3", "triton_frost", "Cold as Triton", "Visit Triton", visit("triton"))
    advancement("pluto", "tier_3", "pluto_frost", "Still a Planet in Our Hearts", "Visit Pluto", visit("pluto"))
    advancement("kuiper", "tier_3", "eris_frost", "Edge of the Solar System", "Visit Eris, Haumea or Makemake",
                visit("eris", "haumea", "makemake"),
                requirements=[["visit_eris", "visit_haumea", "visit_makemake"]])
    all_bodies = [b.id for b in BODIES]
    advancement("grand_tour", "tier_3", "star_chart", "The Grand Tour", "Visit every destination in the mod",
                visit(*all_bodies), frame="challenge", xp=1000)
    home = {f"from_{b}": {"trigger": "minecraft:changed_dimension",
                          "conditions": {"from": mid(b), "to": "minecraft:overworld"}} for b in all_bodies}
    advancement("welcome_home", "moon", "minecraft:grass_block", "Welcome Home", "Return to Earth from space", home,
                requirements=[list(home.keys())])


# =============================================================================== language

def write_lang():
    LANG.update({
        "itemGroup.interplanetary.main": "Interplanetary Stuff",
        "itemGroup.interplanetary.blocks": "Interplanetary Blocks",
        "entity.interplanetary.rocket": "Rocket",
        "key.interplanetary.flight_computer": "Open Flight Computer",
        "category.interplanetary": "Interplanetary Stuff",
        "gamerule.interplanetarySpaceSuffocation": "Interplanetary: suffocate without a space suit",
        "gamerule.interplanetaryRocketsNeedFuel": "Interplanetary: rockets need fuel",
        "item.interplanetary.space_suit_piece.tooltip": "Wear all four pieces to breathe on other worlds.",
        "item.interplanetary.rocket.tier": "Tier %s",
        "item.interplanetary.rocket.range.1": "Range: Moon, Mercury, Venus, Mars, Phobos, Deimos",
        "item.interplanetary.rocket.range.2": "Range: + asteroids and the moons of Jupiter & Saturn",
        "item.interplanetary.rocket.range.3": "Range: the entire Solar System",
        "item.interplanetary.rocket.usage": "Place, fuel, board, then press the flight computer key",
        "message.interplanetary.rocket.no_room": "Not enough room to place the rocket here",
        "message.interplanetary.rocket.tank_full": "The fuel tank is full",
        "message.interplanetary.rocket.fuel": "Fuel: %s / %s",
        "message.interplanetary.rocket.boarded": "Welcome aboard! Press [%s] to open the flight computer",
        "message.interplanetary.rocket.liftoff": "Liftoff!",
        "message.interplanetary.rocket.bound_for": "Bound for %s",
        "message.interplanetary.rocket.touchdown": "Touchdown on %s!",
        "message.interplanetary.rocket.touchdown_unknown": "Touchdown!",
        "message.interplanetary.rocket.navigation_error": "Navigation error - returning to the surface",
        "message.interplanetary.rocket.not_seated": "You must be seated in a rocket to launch",
        "message.interplanetary.rocket.already_here": "You are already on %s",
        "message.interplanetary.rocket.tier_too_low": "%s needs a Tier %s rocket",
        "message.interplanetary.rocket.need_fuel": "Not enough fuel: this trip needs %s, the tank holds %s",
        "message.interplanetary.no_oxygen": "No breathable air on %s! Wear a full space suit",
        "hud.interplanetary.rocket": "Tier %s Rocket",
        "hud.interplanetary.fuel": "%s/%s",
        "hud.interplanetary.flight_computer": "[%s] Flight computer  -  [Sneak] Exit",
        "screen.interplanetary.star_map": "Flight Computer",
        "screen.interplanetary.launch": "Launch!",
        "screen.interplanetary.gravity": "Gravity: %s g",
        "screen.interplanetary.temperature": "Temperature: %s °C",
        "screen.interplanetary.atmosphere": "Atmosphere: %s",
        "screen.interplanetary.requirements": "Needs: Tier %s rocket, %s fuel",
        "screen.interplanetary.suit_required": "Space suit required",
        "screen.interplanetary.low_fuel": "Not enough fuel for this trip",
        "screen.interplanetary.rocket_status": "Rocket: Tier %s  -  Fuel %s/%s",
        "screen.interplanetary.view_only": "Board a rocket to launch. Viewing only.",
        "screen.interplanetary.you_are_here": "You are on %s",
        "screen.interplanetary.problem.not_seated": "Sit in a fuelled rocket to launch",
        "screen.interplanetary.problem.here": "You are already here",
        "screen.interplanetary.problem.tier": "Needs a Tier %s rocket",
        "commands.interplanetary.unknown": "Unknown destination: %s",
        "commands.interplanetary.missing_world": "The world %s is not loaded",
        "commands.interplanetary.travel": "Sent %s player(s) to %s",
        "commands.interplanetary.info.not_space": "This world is not part of the Solar System",
        "commands.interplanetary.destinations": "Destinations:",
        "body_type.interplanetary.home_planet": "Home planet",
        "body_type.interplanetary.planet": "Planet",
        "body_type.interplanetary.dwarf_planet": "Dwarf planet",
        "body_type.interplanetary.moon": "Moon",
        "body_type.interplanetary.asteroid": "Asteroid",
        "atmosphere.interplanetary.breathable": "Breathable",
        "atmosphere.interplanetary.none": "None (vacuum)",
        "atmosphere.interplanetary.trace": "Trace",
        "atmosphere.interplanetary.thin": "Thin",
        "atmosphere.interplanetary.thick": "Thick",
        "atmosphere.interplanetary.crushing": "Crushing",
        "body.interplanetary.earth": "Earth",
        "body.interplanetary.earth.desc": "Home. Breathable air, liquid water and everything you left behind.",
        "system.interplanetary.mercury": "Mercury",
        "system.interplanetary.mercury.desc": "The smallest planet and the closest to the Sun.",
        "system.interplanetary.venus": "Venus",
        "system.interplanetary.venus.desc": "Earth's scorching twin, hidden under thick clouds.",
        "system.interplanetary.earth": "Earth & Moon",
        "system.interplanetary.earth.desc": "Home, and our closest neighbour in space.",
        "system.interplanetary.mars": "Mars",
        "system.interplanetary.mars.desc": "The Red Planet and its two little moons.",
        "system.interplanetary.asteroids": "Asteroids",
        "system.interplanetary.asteroids.desc": "Rocky and metallic leftovers from the birth of the planets.",
        "system.interplanetary.jupiter": "Jupiter",
        "system.interplanetary.jupiter.desc": "The giant planet and its four Galilean moons.",
        "system.interplanetary.saturn": "Saturn",
        "system.interplanetary.saturn.desc": "The ringed jewel of the Solar System and its icy moons.",
        "system.interplanetary.uranus": "Uranus",
        "system.interplanetary.uranus.desc": "The sideways ice giant and its five large moons.",
        "system.interplanetary.neptune": "Neptune",
        "system.interplanetary.neptune.desc": "The windy blue giant. Its moon Triton orbits backwards.",
        "system.interplanetary.pluto": "Pluto & Charon",
        "system.interplanetary.pluto.desc": "A double world at the edge of the planetary realm.",
        "system.interplanetary.kuiper": "Kuiper Belt",
        "system.interplanetary.kuiper.desc": "Distant icy dwarf planets in the outer darkness.",
        "tag.item.c.ingots.titanium": "Titanium Ingots",
        "tag.item.c.ingots.iridium": "Iridium Ingots",
        "tag.item.c.raw_materials.titanium": "Raw Titanium",
        "tag.item.c.raw_materials.iridium": "Raw Iridium",
        "tag.item.c.ores.titanium": "Titanium Ores",
        "tag.item.c.ores.iridium": "Iridium Ores",
        "tag.item.c.dusts.sulfur": "Sulfur Dusts",
    })
    for b in BODIES:
        LANG[f"body.{NS}.{b.id}"] = b.name
        LANG[f"body.{NS}.{b.id}.desc"] = b.desc
    write_json(os.path.join(ASSETS, "lang", "en_us.json"), dict(sorted(LANG.items())))


# =============================================================================== java

JAVA_HEADER = """package com.randonaughtica.interplanetary.registry;

// GENERATED by tools/generate.py - do not edit by hand, edit the generator and re-run it.

import net.minecraft.block.AmethystClusterBlock;
import net.minecraft.block.Block;
import net.minecraft.block.ColoredFallingBlock;
import net.minecraft.block.MapColor;
import net.minecraft.sound.BlockSoundGroup;
import net.minecraft.util.ColorCode;

/** Every block of the mod, registered in creative-tab order. */
@SuppressWarnings("unused")
public final class PlanetBlocks {
"""


def write_java():
    lines = [JAVA_HEADER]
    for b in BLOCKS:
        field_name = b.id.upper()
        settings = (f"ModBlocks.settings(MapColor.{b.map_color}, {b.hardness}F, {b.resistance}F, "
                    f"BlockSoundGroup.{b.sound}, {'true' if b.requires_tool else 'false'})")
        if b.light:
            settings += f".luminance(state -> {b.light})"
        if b.slippery:
            settings += ".slipperiness(0.98F)"
        if b.kind == "cluster":
            settings += ".nonOpaque()"
            ctor = f"new AmethystClusterBlock(7.0F, 3.0F, {settings})"
            register = "registerCutout"
        elif b.kind == "falling":
            ctor = f"new ColoredFallingBlock(new ColorCode(0x{b.color:06X}), {settings})"
            register = "register"
        else:
            ctor = f"new Block({settings})"
            register = "register"
        lines.append(f"    public static final Block {field_name} = ModBlocks.{register}(\"{b.id}\",\n"
                     f"            {ctor});\n")
    lines.append("""
    private PlanetBlocks() {
    }

    public static void init() {
    }
}
""")
    with open(os.path.join(JAVA_PKG, "PlanetBlocks.java"), "w", encoding="utf-8") as f:
        f.write("".join(lines))


# =============================================================================== main

def clean():
    for path in [os.path.join(ASSETS, "blockstates"), os.path.join(ASSETS, "models"),
                 os.path.join(ASSETS, "textures"), os.path.join(DATA, "worldgen"),
                 os.path.join(DATA, "dimension"), os.path.join(DATA, "dimension_type"),
                 os.path.join(DATA, "loot_table"), os.path.join(DATA, "recipe"),
                 os.path.join(DATA, "advancement"), os.path.join(DATA, "tags"),
                 os.path.join(DATA_MC, "tags"), os.path.join(DATA_C, "tags")]:
        if os.path.isdir(path):
            shutil.rmtree(path)


def main():
    define_content()
    clean()
    write_worldgen()
    write_block_assets()
    write_item_assets()
    write_entity_and_armor_textures()
    write_sky_textures()
    write_gui_textures()
    write_icon()
    write_loot_tables()
    write_tags()
    write_recipes()
    write_damage_type()
    write_advancements()
    write_lang()
    write_java()
    print(f"Generated {len(BODIES)} worlds, {len(BLOCKS)} blocks, {len(ITEMS)} items, {len(LANG)} translations.")


if __name__ == "__main__":
    main()
