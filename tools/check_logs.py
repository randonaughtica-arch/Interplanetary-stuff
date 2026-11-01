#!/usr/bin/env python3
"""Scans a game log for problems caused by this mod.

Fails if Minecraft logged an error (other than known harmless ones), or if a required marker line
is missing. Also echoes the [selftest] terrain previews so they are easy to find in CI output.
Usage: python3 tools/check_logs.py LOG [--require TEXT]...
"""
import re
import sys

BENIGN = (
    "Failed to load properties from file",
    "No data fixer registered for",  # logged for every modded entity type
    "Ambiguity between arguments",
)


def main(argv) -> int:
    path = argv[0]
    required = [argv[i + 1] for i, a in enumerate(argv) if a == "--require"]
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        print(f"{path} not found - the game did not run (see the earlier steps).")
        return 1

    problems = []
    echo = False
    for i, line in enumerate(lines):
        if "[selftest]" in line:
            echo = True
            print(line)
        elif echo and line.startswith("    "):
            print(line)
            continue
        else:
            echo = False
        if any(b in line for b in BENIGN):
            continue
        if "/ERROR]" in line:
            problems.append("\n".join(lines[i:i + 8]))
        elif "interplanetary" in line.lower() and re.search(r"(Couldn't|Failed|Unknown|Missing|Invalid|Exception)", line) \
                and "[selftest]" not in line:
            problems.append(line)

    for marker in required:
        if not any(marker in line for line in lines):
            problems.append(f"required log line not found: {marker!r}")

    if problems:
        print(f"\n{len(problems)} problem(s) in {path}:")
        for p in problems:
            print("----\n" + p)
        return 1
    print(f"\nNo errors found in {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["build/gametest.log"]))
