#!/usr/bin/env python3
"""Scans a game log (e.g. from ./gradlew runGametest) for problems caused by this mod.

Fails if Minecraft logged an error while loading or running the mod's data. Also echoes the
terrain previews printed by the game tests so they are easy to find in CI output.
Usage: python3 tools/check_logs.py build/gametest.log
"""
import re
import sys

BENIGN = (
    "Failed to load properties from file",
    "Ambiguity between arguments",
)


def main(path: str) -> int:
    try:
        open(path).close()
    except FileNotFoundError:
        print(f"{path} not found - the game tests did not run (see the earlier steps).")
        return 1
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    problems = []
    in_terrain = False
    for i, line in enumerate(lines):
        level_error = "/ERROR]" in line or " ERROR " in line
        mentions_mod = "interplanetary" in line.lower()
        if "[gametest]" in line:
            in_terrain = True
            print(line)
            continue
        if in_terrain:
            if line.startswith("    "):
                print(line)
                continue
            in_terrain = False
        if any(b in line for b in BENIGN):
            continue
        if level_error:
            context = "\n".join(lines[i:i + 6])
            problems.append(context)
        elif mentions_mod and re.search(r"(Couldn't|Failed|Unknown|Missing|Invalid|Exception)", line):
            problems.append(line)

    if problems:
        print(f"\n{len(problems)} problem(s) in {path}:")
        for p in problems:
            print("----\n" + p)
        return 1
    print(f"\nNo errors found in {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "build/gametest.log"))
