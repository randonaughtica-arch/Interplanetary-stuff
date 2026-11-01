#!/usr/bin/env python3
"""Static checks for the mod's resources. Run from the repository root: python3 tools/validate.py

Catches broken references that Minecraft would only report at runtime: missing models, textures,
translations, loot tables, worldgen entries and so on.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "src", "main", "resources")
JAVA = os.path.join(ROOT, "src", "main", "java")
NS = "interplanetary"
ASSETS = os.path.join(RES, "assets", NS)
DATA = os.path.join(RES, "data", NS)

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def load(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        err(f"invalid JSON {os.path.relpath(path, ROOT)}: {e}")
        return None


def split(identifier: str, default_ns: str = "minecraft"):
    if ":" in identifier:
        ns, path = identifier.split(":", 1)
    else:
        ns, path = default_ns, identifier
    return ns, path


def walk_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(k)
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def java_sources() -> str:
    text = []
    for path in glob.glob(os.path.join(JAVA, "**", "*.java"), recursive=True):
        with open(path, encoding="utf-8") as f:
            text.append(f.read())
    return "\n".join(text)


def main() -> int:
    # 1. every JSON parses
    jsons = {}
    for path in glob.glob(os.path.join(RES, "**", "*.json"), recursive=True):
        data = load(path)
        if data is not None:
            jsons[path] = data

    lang = jsons.get(os.path.join(ASSETS, "lang", "en_us.json"), {})
    src = java_sources()

    blocks = re.findall(r'ModBlocks\.register(?:Cutout)?\("([a-z0-9_]+)"', src)
    items = re.findall(r'register\("([a-z0-9_]+)",\s*new ', open(os.path.join(
        JAVA, "com", "randonaughtica", "interplanetary", "registry", "ModItems.java"), encoding="utf-8").read())
    items += re.findall(r'register\("([a-z0-9_]+)",\s*simple\(\)', open(os.path.join(
        JAVA, "com", "randonaughtica", "interplanetary", "registry", "ModItems.java"), encoding="utf-8").read())
    if len(blocks) < 50:
        err(f"only found {len(blocks)} registered blocks - is PlanetBlocks.java generated?")
    known_blocks = {f"{NS}:{b}" for b in blocks}
    known_items = known_blocks | {f"{NS}:{i}" for i in items}

    # 2. blocks: blockstate, model, loot table, translation
    for b in blocks:
        bs = os.path.join(ASSETS, "blockstates", f"{b}.json")
        if not os.path.exists(bs):
            err(f"block {b}: missing blockstate")
        if not os.path.exists(os.path.join(DATA, "loot_table", "blocks", f"{b}.json")):
            err(f"block {b}: missing loot table")
        if f"block.{NS}.{b}" not in lang:
            err(f"block {b}: missing translation")
        if not os.path.exists(os.path.join(ASSETS, "models", "item", f"{b}.json")):
            err(f"block {b}: missing item model")
    for i in items:
        if not os.path.exists(os.path.join(ASSETS, "models", "item", f"{i}.json")):
            err(f"item {i}: missing item model")
        if f"item.{NS}.{i}" not in lang:
            err(f"item {i}: missing translation")

    # 3. models -> textures / parents
    def model_exists(ref):
        ns, path = split(ref)
        if ns != NS:
            return True
        return os.path.exists(os.path.join(ASSETS, "models", f"{path}.json"))

    def texture_exists(ref):
        ns, path = split(ref)
        if ns != NS:
            return True
        return os.path.exists(os.path.join(ASSETS, "textures", f"{path}.png"))

    for path, data in jsons.items():
        rel = os.path.relpath(path, ASSETS)
        if rel.startswith("blockstates"):
            for s in walk_strings(data):
                if s.startswith(f"{NS}:block/") and not model_exists(s):
                    err(f"{rel}: missing model {s}")
        elif rel.startswith("models"):
            parent = data.get("parent")
            if parent and not model_exists(parent):
                err(f"{rel}: missing parent {parent}")
            for t in data.get("textures", {}).values():
                if not t.startswith("#") and not texture_exists(t):
                    err(f"{rel}: missing texture {t}")

    # 4. textures referenced from Java
    for ref in set(re.findall(r'id\("(textures/[^"]+\.png)"\)', src)):
        if not os.path.exists(os.path.join(ASSETS, ref)):
            err(f"Java references missing texture {ref}")
    for ref in set(re.findall(r'id\("(textures/[^"]+?)" \+', src)):
        if not glob.glob(os.path.join(ASSETS, ref) + "*"):
            err(f"Java references missing texture prefix {ref}")
    for body in set(re.findall(r'tex\("([a-z_]+)"\)', src)):
        if not os.path.exists(os.path.join(ASSETS, "textures", "environment", "bodies", f"{body}.png")):
            err(f"sky texture for {body} is missing")
    for body in set(re.findall(r'new CelestialBody\("([a-z_]+)"', src)):
        if not os.path.exists(os.path.join(ASSETS, "textures", "environment", "bodies", f"{body}.png")):
            err(f"body texture for {body} is missing")
        if body != "earth" and not os.path.exists(os.path.join(DATA, "dimension", f"{body}.json")):
            err(f"body {body} has no dimension")
        for key in (f"body.{NS}.{body}", f"body.{NS}.{body}.desc"):
            if key not in lang:
                err(f"missing translation {key}")
    for system in set(re.findall(r'new StarSystem\("([a-z_]+)"', src)):
        if not os.path.exists(os.path.join(ASSETS, "textures", "gui", "systems", f"{system}.png")):
            err(f"star map icon for {system} is missing")
        for key in (f"system.{NS}.{system}", f"system.{NS}.{system}.desc"):
            if key not in lang:
                err(f"missing translation {key}")

    # 5. translation keys used literally in Java
    for key in set(re.findall(r'Text\.(?:translatable|keybind)\("([a-z0-9_.]+)"', src)):
        if key.endswith("."):
            continue
        if key not in lang:
            err(f"missing translation {key}")
    for prefix in ("item.interplanetary.rocket.range.",):
        for tier in (1, 2, 3):
            if f"{prefix}{tier}" not in lang:
                err(f"missing translation {prefix}{tier}")

    # 6. worldgen references
    def data_exists(kind, ref):
        ns, path = split(ref)
        if ns != NS:
            return True
        return os.path.exists(os.path.join(DATA, kind, f"{path}.json"))

    for path, data in jsons.items():
        rel = os.path.relpath(path, DATA)
        if rel.startswith("worldgen/biome"):
            for step in data["features"]:
                for f in step:
                    if not data_exists("worldgen/placed_feature", f):
                        err(f"{rel}: missing placed feature {f}")
            for carvers in data.get("carvers", {}).values():
                for c in carvers:
                    if not data_exists("worldgen/configured_carver", c):
                        err(f"{rel}: missing carver {c}")
            if len(data["features"]) != 11:
                err(f"{rel}: expected 11 feature steps")
        elif rel.startswith("worldgen/placed_feature"):
            if not data_exists("worldgen/configured_feature", data["feature"]):
                err(f"{rel}: missing configured feature {data['feature']}")
        elif rel.startswith("dimension/"):
            gen = data["generator"]
            if not data_exists("worldgen/noise_settings", gen["settings"]):
                err(f"{rel}: missing noise settings")
            if not data_exists("dimension_type", data["type"]):
                err(f"{rel}: missing dimension type")
            src_biomes = gen["biome_source"]
            biome_refs = [src_biomes["biome"]] if "biome" in src_biomes else [b["biome"] for b in src_biomes["biomes"]]
            for b in biome_refs:
                if not data_exists("worldgen/biome", b):
                    err(f"{rel}: missing biome {b}")
        elif rel.startswith("worldgen/noise_settings"):
            for s in walk_strings(data):
                if s.startswith(f"{NS}:") and "/" in s and not s.endswith("bedrock_floor"):
                    if not data_exists("worldgen/noise", s) and s.split(":")[1].split("/")[0] in {
                            os.path.basename(p)[:-5] for p in glob.glob(os.path.join(DATA, "dimension", "*.json"))}:
                        err(f"{rel}: missing noise {s}")

        # block / item references anywhere in data
        if rel.startswith(("worldgen", "recipe", "loot_table", "advancement", "tags")) or "tags" in path:
            for s in walk_strings(data):
                if not s.startswith(f"{NS}:") or "/" in s:
                    continue
                if s in known_items:
                    continue
                if rel.startswith("worldgen") and data_exists("worldgen/biome", s):
                    continue
                if s.startswith(f"{NS}:") and (data_exists("damage_type", s) or data_exists("advancement", s)
                                                or data_exists("worldgen/configured_carver", s)
                                                or os.path.exists(os.path.join(DATA, "dimension", s.split(':')[1] + '.json'))
                                                or s.split(':')[1] in ("crater", "boulder")):
                    continue
                err(f"{rel}: unknown reference {s}")

    for path in glob.glob(os.path.join(RES, "data", "*", "tags", "**", "*.json"), recursive=True):
        data = jsons.get(path)
        if not data:
            continue
        for v in data.get("values", []):
            if v.startswith(f"{NS}:") and v not in known_items and not data_exists("damage_type", v):
                err(f"{os.path.relpath(path, RES)}: unknown entry {v}")

    if errors:
        print(f"{len(errors)} problem(s) found:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"OK: {len(jsons)} JSON files, {len(blocks)} blocks, {len(items)} items, {len(lang)} translations checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
