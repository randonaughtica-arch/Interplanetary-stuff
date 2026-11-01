"""Procedural texture generation for Interplanetary Stuff.

Every texture in the mod is generated here (no external art), so it can be tweaked and
re-generated with ``python3 tools/generate.py``. Requires numpy and Pillow.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from PIL import Image


# --------------------------------------------------------------------------- helpers

def seed_of(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def rgb(h: int) -> np.ndarray:
    return np.array([(h >> 16) & 255, (h >> 8) & 255, h & 255], dtype=np.float64)


def shade(color: np.ndarray, factor) -> np.ndarray:
    return np.clip(color * factor, 0, 255)


def mix(a, b, t):
    return a * (1 - t) + b * t


def to_image(arr: np.ndarray) -> Image.Image:
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.shape[-1] == 3:
        return Image.fromarray(arr, "RGB")
    return Image.fromarray(arr, "RGBA")


def tile_noise(r: np.random.Generator, size: int, cells: int) -> np.ndarray:
    """Tileable value noise in [0, 1]."""
    grid = r.random((cells, cells))
    coords = (np.arange(size) + 0.5) * cells / size - 0.5
    i0 = np.floor(coords).astype(int)
    f = coords - i0
    f = f * f * (3 - 2 * f)
    i0m = i0 % cells
    i1m = (i0 + 1) % cells
    y0, x0 = np.meshgrid(i0m, i0m, indexing="ij")
    y1, x1 = np.meshgrid(i1m, i1m, indexing="ij")
    fy, fx = np.meshgrid(f, f, indexing="ij")
    a = grid[y0, x0]
    b = grid[y0, x1]
    c = grid[y1, x0]
    d = grid[y1, x1]
    return mix(mix(a, b, fx), mix(c, d, fx), fy)


def fbm(r, size, octaves=((2, 0.5), (4, 0.3), (8, 0.2))):
    total = np.zeros((size, size))
    weight = 0.0
    for cells, amp in octaves:
        total += tile_noise(r, size, cells) * amp
        weight += amp
    return total / weight


class Noise3:
    """Vectorised 3D value noise for sphere and skybox textures."""

    def __init__(self, seed: int, size: int = 64):
        self.r = np.random.default_rng(seed)
        self.size = size
        self.grid = self.r.random((size, size, size))

    def sample(self, x, y, z):
        s = self.size
        xi = np.floor(x).astype(int)
        yi = np.floor(y).astype(int)
        zi = np.floor(z).astype(int)
        fx = x - xi
        fy = y - yi
        fz = z - zi
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)
        fz = fz * fz * (3 - 2 * fz)
        g = self.grid

        def at(dx, dy, dz):
            return g[(xi + dx) % s, (yi + dy) % s, (zi + dz) % s]

        c00 = mix(at(0, 0, 0), at(1, 0, 0), fx)
        c10 = mix(at(0, 1, 0), at(1, 1, 0), fx)
        c01 = mix(at(0, 0, 1), at(1, 0, 1), fx)
        c11 = mix(at(0, 1, 1), at(1, 1, 1), fx)
        return mix(mix(c00, c10, fy), mix(c01, c11, fy), fz)

    def fbm(self, x, y, z, octaves=4, scale=1.0):
        total = 0.0
        amp = 1.0
        norm = 0.0
        freq = scale
        for i in range(octaves):
            total = total + self.sample(x * freq + i * 17.3, y * freq + i * 9.1, z * freq + i * 3.7) * amp
            norm += amp
            amp *= 0.5
            freq *= 2.0
        return total / norm


# --------------------------------------------------------------------------- block textures (16x16)

def _grain(r, base, amount=0.10):
    n = r.random((16, 16))
    return base[None, None, :] * (1 + (n[..., None] - 0.5) * 2 * amount)


def tex_regolith(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    img = _grain(r, base, 0.09)
    blot = fbm(r, 16, ((4, 0.6), (8, 0.4)))
    img *= (0.9 + blot * 0.2)[..., None]
    # small pits and bright grains
    for _ in range(9):
        x, y = r.integers(0, 16, 2)
        img[y, x] = shade(base, 0.72 + r.random() * 0.08)
        img[(y + 1) % 16, (x + 1) % 16] = shade(base, 1.12)
    for _ in range(6):
        x, y = r.integers(0, 16, 2)
        img[y, x] = shade(base, 1.18 + r.random() * 0.08)
    return img


def tex_sand(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    img = _grain(r, base, 0.06)
    ripple = np.sin((np.arange(16)[:, None] * 0.8 + fbm(r, 16, ((4, 1.0),)) * 6)) * 0.035
    img *= (1 + ripple)[..., None]
    for _ in range(10):
        x, y = r.integers(0, 16, 2)
        img[y, x] = shade(base, 0.86 if r.random() < 0.5 else 1.12)
    return img


def tex_soil(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((4, 0.5), (8, 0.5)))
    img = base[None, None, :] * (0.78 + n[..., None] * 0.42)
    img = img * (1 + (r.random((16, 16, 1)) - 0.5) * 0.12)
    return img


def tex_stone(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((2, 0.35), (4, 0.4), (8, 0.25)))
    img = base[None, None, :] * (0.8 + n[..., None] * 0.36)
    img = img * (1 + (r.random((16, 16, 1)) - 0.5) * 0.07)
    # darker crack-like streaks
    for _ in range(3):
        x, y = r.integers(0, 16, 2)
        length = r.integers(2, 5)
        dx, dy = [(1, 0), (0, 1), (1, 1), (1, -1)][r.integers(0, 4)]
        for i in range(length):
            img[(y + dy * i) % 16, (x + dx * i) % 16] = shade(base, 0.7)
    return img


def tex_basalt(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    cols = np.repeat(r.random(16)[None, :], 16, axis=0)
    n = fbm(r, 16, ((4, 0.5), (8, 0.5)))
    img = base[None, None, :] * (0.78 + cols[..., None] * 0.18 + n[..., None] * 0.14)
    for x in range(0, 16, 4):
        img[:, x] *= 0.82
    return img


def tex_bricks(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    stone = tex_stone(name + "_b", c) * 1.05
    img = stone.copy()
    mortar = shade(base, 0.62)
    for y in range(16):
        row = y // 4
        offset = 4 if row % 2 else 0
        for x in range(16):
            if y % 4 == 3 or (x + offset) % 8 == 7:
                img[y, x] = mortar
            elif y % 4 == 0 or (x + offset) % 8 == 0:
                img[y, x] = img[y, x] * 1.08
    # per-brick tint
    for row in range(4):
        offset = 4 if row % 2 else 0
        for b in range(-1, 2):
            tint = 0.93 + r.random() * 0.14
            x0 = b * 8 - offset
            for y in range(row * 4, row * 4 + 3):
                for x in range(x0, x0 + 7):
                    if 0 <= x < 16:
                        img[y, x] = img[y, x] * tint
    return img


def tex_polished(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((2, 0.5), (4, 0.5)))
    img = base[None, None, :] * (0.95 + n[..., None] * 0.1)
    img[0, :] = shade(base, 1.15)
    img[:, 0] = shade(base, 1.15)
    img[15, :] = shade(base, 0.75)
    img[:, 15] = shade(base, 0.75)
    return img


def tex_ice(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((2, 0.6), (4, 0.4)))
    diag = (np.arange(16)[:, None] + np.arange(16)[None, :]) % 16
    img = base[None, None, :] * (0.9 + n[..., None] * 0.14 + (diag[..., None] < 3) * 0.06)
    for _ in range(2):
        x, y = r.integers(0, 16, 2)
        for i in range(r.integers(4, 8)):
            img[(y + i) % 16, (x + (i // 2)) % 16] = shade(base, 1.18)
    img[0, :] = shade(base, 1.1)
    img[:, 0] = shade(base, 1.08)
    return img


def tex_frost(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((4, 0.5), (8, 0.5)))
    img = base[None, None, :] * (0.93 + n[..., None] * 0.1)
    for _ in range(12):
        x, y = r.integers(0, 16, 2)
        img[y, x] = np.minimum(base * 1.1 + 12, 255)
    for _ in range(5):
        x, y = r.integers(0, 16, 2)
        img[y, x] = shade(base, 0.88)
    return img


def tex_lineae(name, c, line_color=0x9A5A3A):
    img = tex_ice(name, c)
    r = np.random.default_rng(seed_of(name) + 1)
    lc = rgb(line_color)
    for _ in range(3):
        y = r.integers(0, 16)
        slope = r.random() * 0.8 - 0.4
        for x in range(16):
            yy = int(round(y + slope * x)) % 16
            img[yy, x] = mix(img[yy, x], lc, 0.75)
            img[(yy + 1) % 16, x] = mix(img[(yy + 1) % 16, x], lc, 0.3)
    return img


def tex_metal(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((2, 0.5), (8, 0.5)))
    img = base[None, None, :] * (0.92 + n[..., None] * 0.1)
    brush = (r.random((16, 1, 1)) - 0.5) * 0.06
    img = img * (1 + brush)
    for i in range(16):
        img[0, i] = img[i, 0] = shade(base, 1.2)
        img[15, i] = img[i, 15] = shade(base, 0.68)
        img[7, i] = shade(base, 0.8)
        img[8, i] = shade(base, 1.1)
    for (x, y) in [(2, 2), (13, 2), (2, 13), (13, 13)]:
        img[y, x] = shade(base, 1.35)
        img[y + 1, x + 1] = shade(base, 0.6)
    return img


def tex_launch_pad(name, c):
    img = tex_metal(name, c)
    stripe = rgb(0xE0B020)
    dark = rgb(0x202020)
    for y in range(16):
        for x in range(16):
            if (x in (1, 14) or y in (1, 14)) and 1 <= x <= 14 and 1 <= y <= 14:
                img[y, x] = stripe if (x + y) // 2 % 2 == 0 else dark
    return img


def tex_crystal_block(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    img = np.zeros((16, 16, 3))
    for y in range(16):
        for x in range(16):
            facet = ((x // 4) + (y // 4) * 3 + (x + y) // 6) % 5
            img[y, x] = shade(base, 0.8 + facet * 0.1)
    img = img * (1 + (r.random((16, 16, 1)) - 0.5) * 0.08)
    for _ in range(8):
        x, y = r.integers(0, 16, 2)
        img[y, x] = np.minimum(base * 1.3 + 30, 255)
    return img


def tex_salt(name, c):
    img = tex_crystal_block(name, c)
    return img * 0.98


def tex_sulfur(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((4, 0.5), (8, 0.5)))
    img = base[None, None, :] * (0.8 + n[..., None] * 0.35)
    for _ in range(14):
        x, y = r.integers(0, 15, 2)
        img[y, x] = np.minimum(base * 1.2 + 10, 255)
        img[y + 1, x + 1] = shade(base, 0.7)
    return img


def tex_pumice(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    img = _grain(r, base, 0.06)
    for _ in range(18):
        x, y = r.integers(0, 16, 2)
        img[y, x] = shade(base, 0.62)
        img[y, (x + 1) % 16] = shade(base, 0.8)
    return img


def tex_tholin(name, c):
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    n = fbm(r, 16, ((2, 0.4), (4, 0.4), (8, 0.2)))
    img = base[None, None, :] * (0.7 + n[..., None] * 0.55)
    return img


def tex_nickel_iron(name, c):
    """Widmanstätten pattern, like an etched iron meteorite."""
    r = np.random.default_rng(seed_of(name))
    base = rgb(c)
    img = base[None, None, :] * (0.92 + fbm(r, 16, ((4, 1.0),))[..., None] * 0.12)
    for _ in range(7):
        x0, y0 = r.integers(0, 16, 2)
        dx, dy = [(1, 0), (1, 2), (2, 1), (1, -2), (2, -1)][r.integers(0, 5)]
        for i in range(10):
            x = (x0 + (dx * i) // 2) % 16
            y = (y0 + (dy * i) // 2) % 16
            img[y, x] = shade(base, 1.2 if i % 2 == 0 else 0.8)
    return img


ORE_SHAPES = [
    [(3, 3), (4, 3), (3, 4), (4, 4), (5, 4)],
    [(10, 2), (11, 2), (11, 3), (12, 3)],
    [(6, 9), (7, 9), (7, 10), (8, 10), (6, 10)],
    [(12, 11), (13, 11), (12, 12), (13, 12), (11, 12)],
    [(2, 12), (3, 12), (3, 13)],
    [(9, 6), (10, 6), (10, 7)],
]


def tex_ore(name, base_tex, ore_colors):
    r = np.random.default_rng(seed_of(name))
    img = base_tex.copy()
    dark, mid, light = (rgb(c) for c in ore_colors)
    for shape in ORE_SHAPES:
        for i, (x, y) in enumerate(shape):
            img[y, x] = light if i == 0 else (mid if r.random() < 0.7 else dark)
        x, y = shape[-1]
        if y + 1 < 16:
            img[y + 1, x] = shade(img[y + 1, x], 0.7)
    return img


def tex_cluster(name, c):
    """Cross-model crystal cluster sprite (RGBA)."""
    base = rgb(c)
    img = np.zeros((16, 16, 4))
    spikes = [(7, 2, 14, 2), (4, 6, 14, 1), (10, 5, 14, 1), (2, 10, 14, 1), (12, 9, 14, 1)]
    for (x, top, bottom, half) in spikes:
        for y in range(top, bottom + 1):
            w = half if y > top + 1 else 0
            for xx in range(x - w, x + w + 1):
                if 0 <= xx < 16:
                    t = (y - top) / max(1, bottom - top)
                    col = shade(base, 1.35 - t * 0.5 + (0.15 if xx == x - w else 0))
                    img[y, xx, :3] = np.minimum(col + 10, 255)
                    img[y, xx, 3] = 255
    for (x, y) in [(7, 2), (4, 6), (10, 5)]:
        img[y, x, :3] = 255
    return img


BLOCK_STYLES = {
    "regolith": tex_regolith,
    "sand": tex_sand,
    "soil": tex_soil,
    "stone": tex_stone,
    "basalt": tex_basalt,
    "bricks": tex_bricks,
    "polished": tex_polished,
    "ice": tex_ice,
    "frost": tex_frost,
    "lineae": tex_lineae,
    "metal": tex_metal,
    "launch_pad": tex_launch_pad,
    "crystal_block": tex_crystal_block,
    "salt": tex_salt,
    "sulfur": tex_sulfur,
    "pumice": tex_pumice,
    "tholin": tex_tholin,
    "nickel_iron": tex_nickel_iron,
}


# --------------------------------------------------------------------------- item textures (pixel art)

RAMPS = {
    "titanium": [0x2A3440, 0x56677A, 0x8A9BAE, 0xBFCCD9, 0xEEF4FA],
    "titanium_raw": [0x262A30, 0x4A525C, 0x707C88, 0x98A4AF, 0xC4CDD4],
    "iridium": [0x34363C, 0x6A6E78, 0xA4A9B4, 0xD6DAE2, 0xFFFFFF],
    "iridium_raw": [0x302E2A, 0x5E5A52, 0x928C80, 0xC2BCAE, 0xE8E2D2],
    "iron": [0x3A3A3A, 0x6E6E6E, 0xA8A8A8, 0xD8D8D8, 0xFFFFFF],
    "solar": [0x6A3A00, 0xB86E00, 0xF0A818, 0xFFD860, 0xFFF8C8],
    "frost": [0x1E4A6A, 0x3E86B0, 0x78C0E4, 0xB8E6FA, 0xF0FCFF],
    "sulfur": [0x5A4A00, 0x9A8608, 0xD4C020, 0xF0E050, 0xFFF8A0],
    "red": [0x4A0E0A, 0x8A1E16, 0xC8382A, 0xE8604A, 0xFFA08A],
    "blue": [0x0A1E4A, 0x163E8A, 0x2E6FC8, 0x5A98E8, 0xA8D0FF],
    "gold": [0x4A3000, 0x8A6010, 0xD9A93A, 0xF0CC60, 0xFFF0B0],
    "white": [0x404448, 0x8A9096, 0xC8CDD2, 0xE8ECEF, 0xFFFFFF],
    "dark": [0x101114, 0x24262C, 0x3C4049, 0x5A5E68, 0x80848E],
    "glass": [0x0A2A4A, 0x2A5A8A, 0x5A9AD0, 0x9ACFF4, 0xE0F6FF],
    "flame": [0x6A1A00, 0xC04000, 0xF08010, 0xFFC040, 0xFFF0A0],
    "cyan": [0x003A4A, 0x00708A, 0x10B0C8, 0x60E0F0, 0xC0FFFF],
    "paper": [0x0A1430, 0x16244A, 0x22366A, 0x30508E, 0x6A8AC0],
    "wafer": [0x2A1408, 0x4A2810, 0x6E3E1E, 0x8E5A30, 0xAE7A48],
    "cream": [0x8A7A6A, 0xC8B8A8, 0xEAE0D2, 0xF8F2EA, 0xFFFFFF],
    "pink": [0x7A2A40, 0xB8506A, 0xE07890, 0xF4A8B8, 0xFFD8E0],
    "brown": [0x2A1408, 0x50301A, 0x704A2E, 0x946A48, 0xB88C68],
}

# Letters pick a ramp: digits use the item's primary ramp, letters a-e the secondary,
# f-j the tertiary. Within each group the order is darkest -> brightest.
ITEM_ART = {
    "ingot": [
        "................",
        "................",
        "................",
        "................",
        "......00000.....",
        "....004444300...",
        "..0034443332100.",
        ".033333332221100",
        "0333322222111100",
        "0222222211110000",
        ".00111111100....",
        "...0000000......",
        "................",
        "................",
        "................",
        "................",
    ],
    "raw": [
        "................",
        "................",
        "................",
        ".....000........",
        "....03430.000...",
        "...0343320343...",
        "..03322321332.0.",
        "..0322122221220.",
        ".03321112212210.",
        ".03211012221110.",
        ".0221100122110..",
        "..0111000111100.",
        "...000...00000..",
        "................",
        "................",
        "................",
    ],
    "plate": [
        "................",
        "................",
        "..000000000000..",
        "..044444444430..",
        "..043333333320..",
        "..0342333324220.",
        "..034333333322..",
        "..033333333322..",
        "..033333333322..",
        "..033333333322..",
        "..034333333422..",
        "..0332333332220.",
        "..022222222221..",
        "..000000000000..",
        "................",
        "................",
    ],
    "shard": [
        "................",
        "........0.......",
        ".......040......",
        "......04430.....",
        "......04330.....",
        ".....0443320....",
        ".....0433320....",
        "....044332210...",
        "....043322210...",
        "....043322110...",
        ".....0322110....",
        ".....0321110....",
        "......02110.....",
        ".......010......",
        "........0.......",
        "................",
    ],
    "dust": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "........0.......",
        ".......040......",
        "......03430.....",
        ".....0334320....",
        "....033343220...",
        "...03334332210..",
        "..0333222222210.",
        "..0222211111110.",
        "...00000000000..",
        "................",
        "................",
    ],
    "canister": [
        "................",
        ".....ffff.......",
        "....fhiihf......",
        "....0ghhg0......",
        "...0044430......",
        "...04433320.....",
        "...043cdc20.....",
        "...043ded20.....",
        "...043cdc20.....",
        "...043cdc20.....",
        "...04333320.....",
        "...03332210.....",
        "...03222210.....",
        "...02211110.....",
        "....000000......",
        "................",
    ],
    "nose_cone": [
        "................",
        ".......00.......",
        "......0440......",
        "......0430......",
        ".....043320.....",
        ".....043320.....",
        "....04333220....",
        "....04332220....",
        "...0433322210...",
        "...0433222210...",
        "..043332222110..",
        "..043322221110..",
        "..ffffffffffff..",
        "..fhhhhhhhhhhf..",
        "..ffffffffffff..",
        "................",
    ],
    "fin": [
        "................",
        "...0............",
        "...00...........",
        "...040..........",
        "...0430.........",
        "...04330........",
        "...043320.......",
        "...0433320......",
        "...04333320.....",
        "...043333220....",
        "...0433322220...",
        "...04332222210..",
        "...0ffffffffff..",
        "...0ghhhhhhhhg..",
        "...0ffffffffff..",
        "................",
    ],
    "engine": [
        "................",
        "....00000000....",
        "....04444430....",
        "....04333320....",
        "....04333220....",
        "....03322210....",
        "....00222100....",
        "......0210......",
        ".....043210.....",
        "....04332210....",
        "...0433222110...",
        "..043322221110..",
        "..000000000000..",
        "...abcdddcba....",
        ".....bcdcb......",
        "......bcb.......",
    ],
    "rocket": [
        ".......00.......",
        "......0ab0......",
        ".....0aabb0.....",
        ".....0abbc0.....",
        ".....043320.....",
        ".....0fgg20.....",
        ".....0ghg20.....",
        ".....0ggf20.....",
        ".....043320.....",
        ".....043210.....",
        "....a043320a....",
        "...ab043320ba...",
        "...ab033210ba...",
        "...a.002200.a...",
        "......0dd0......",
        ".......cc.......",
    ],
    "helmet": [
        "................",
        "................",
        ".....000000.....",
        "....04444430....",
        "...0444333320...",
        "..044333333220..",
        "..04afffffg220..",
        "..03fggggghg20..",
        "..03fgggghhg20..",
        "..03fgggghhg20..",
        "..03ffggggff20..",
        "..033fffffff20..",
        "..0332222222210.",
        "..0aaaaaaaaaaa..",
        "..00000000000...",
        "................",
    ],
    "suit": [
        "................",
        "..000......000..",
        ".04440000004440.",
        ".0433344443332..",
        ".043333333333320",
        ".0aa3333333aa320",
        "..0a33fghf33a20.",
        "..0333fhgf33320.",
        "..0333333333320.",
        "...03333333320..",
        "...0aaaaaaaaa0..",
        "...0333333332...",
        "...0333333332...",
        "...0322222221...",
        "....000000000...",
        "................",
    ],
    "pants": [
        "................",
        "...0000000000...",
        "...0aaaaaaaaa0..",
        "...04443333320..",
        "...04333333220..",
        "...04332033220..",
        "...0433200322...",
        "...043320.3320..",
        "...043320.3320..",
        "...0aa320.3aa0..",
        "...043320.3320..",
        "...043220.3220..",
        "...033220.3220..",
        "...022210.2210..",
        "...00000..0000..",
        "................",
    ],
    "boots": [
        "................",
        "................",
        "................",
        "................",
        "...00000..00000.",
        "...04430..04430.",
        "...04330..04330.",
        "...0aa30..0aa30.",
        "...04330..04330.",
        "...043320.043320",
        "...0433320043332",
        "...0332222033222",
        "...0ffffff0fffff",
        "...0000000000000",
        "................",
        "................",
    ],
    "chart": [
        "................",
        "..000000000000..",
        "..0aaaaaaaaaa0..",
        ".0a2222224222a0.",
        ".0a2242222222a0.",
        ".0a2222222232a0.",
        ".0a2232222222a0.",
        ".0a2222242222a0.",
        ".0a2222222222a0.",
        ".0a2422222322a0.",
        ".0a2222223222a0.",
        ".0a2232222222a0.",
        ".0a2222222242a0.",
        "..0aaaaaaaaaa0..",
        "..000000000000..",
        "................",
    ],
    "ice_cream": [
        "................",
        "................",
        "................",
        "...0000000000...",
        "..033333333320..",
        "..022222222210..",
        "..0dddddddddd0..",
        "..0cccccccccc0..",
        "..0ihhhhhhhhh0..",
        "..0hhggghhggh0..",
        "..0cccbcccccb0..",
        "..033333333320..",
        "..022222222210..",
        "...0000000000...",
        "................",
        "................",
    ],
}


def render_art(art_name, ramp, secondary=None, tertiary=None):
    rows = ITEM_ART[art_name]
    img = np.zeros((16, 16, 4))
    ramps = [RAMPS[ramp], RAMPS[secondary or ramp], RAMPS[tertiary or secondary or ramp]]
    for y, row in enumerate(rows):
        assert len(row) == 16, (art_name, y, len(row))
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            if ch.isdigit():
                color = ramps[0][int(ch)]
            elif "a" <= ch <= "e":
                color = ramps[1][ord(ch) - ord("a")]
            else:
                color = ramps[2][ord(ch) - ord("f")]
            img[y, x, :3] = rgb(color)
            img[y, x, 3] = 255
    return img


# --------------------------------------------------------------------------- spheres (planets & moons)

def sphere(size, surface_fn, seed, radius=0.94, halo=None, tilt=0.3, limb=0.45):
    """Render a lit-from-the-front sphere. surface_fn(X, Y, Z, n3) -> (h, w, 3) colours."""
    n3 = Noise3(seed)
    c = (np.arange(size) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(c, -c)
    x = x / radius
    y = y / radius
    rr = x * x + y * y
    inside = rr <= 1.0
    z = np.sqrt(np.clip(1 - rr, 0, 1))
    # rotate the sphere so features are not centred on the pole
    ct, st = math.cos(tilt), math.sin(tilt)
    Y = y * ct - z * st
    Z = y * st + z * ct
    X = x
    col = surface_fn(X, Y, Z, n3)
    light = (1 - limb) + limb * np.sqrt(z)
    col = col * light[..., None]
    alpha = np.clip((1.0 - np.sqrt(rr)) * size * radius * 0.5 + 0.5, 0, 1) * 255
    img = np.zeros((size, size, 4))
    img[..., :3] = col
    img[..., 3] = np.where(inside, alpha, 0)
    if halo is not None:
        d = np.sqrt(rr)
        glow = np.clip(1 - (d - 1) / 0.06, 0, 1) * (d > 1)
        hc = rgb(halo)
        img[..., :3] = np.where((d > 1)[..., None], hc, img[..., :3])
        img[..., 3] = np.where(d > 1, glow * 160, img[..., 3])
    return img


def rocky(base, variance=0.25, dark=None, dark_amount=0.0, crater_count=25, seed_scale=3.0,
          bright=None, bright_amount=0.0):
    b = rgb(base)
    d = rgb(dark) if dark is not None else b * 0.6
    br = rgb(bright) if bright is not None else b * 1.3

    def fn(X, Y, Z, n3):
        n = n3.fbm(X * seed_scale + 20, Y * seed_scale + 20, Z * seed_scale + 20, 5)
        col = b[None, None, :] * (1 - variance + n[..., None] * variance * 2)
        if dark_amount > 0:
            m = n3.fbm(X * 1.6 + 40, Y * 1.6 + 40, Z * 1.6 + 40, 3)
            t = np.clip((m - (1 - dark_amount)) * 6, 0, 1)
            col = mix(col, d[None, None, :] * (0.8 + n[..., None] * 0.4), t[..., None])
        if bright_amount > 0:
            m = n3.fbm(X * 2.2 + 70, Y * 2.2 + 70, Z * 2.2 + 70, 3)
            t = np.clip((m - (1 - bright_amount)) * 6, 0, 1)
            col = mix(col, br[None, None, :], t[..., None])
        # craters
        r = np.random.default_rng(int(base) + crater_count)
        for _ in range(crater_count):
            v = r.normal(size=3)
            v /= np.linalg.norm(v)
            size = 0.04 + r.random() ** 3 * 0.22
            dot = X * v[0] + Y * v[1] + Z * v[2]
            dist = np.arccos(np.clip(dot, -1, 1))
            inner = dist < size
            rim = (dist >= size) & (dist < size * 1.25)
            col = np.where(inner[..., None], col * 0.82, col)
            col = np.where(rim[..., None], np.minimum(col * 1.15, 255), col)
        return col

    return fn


def banded(colors, turbulence=0.15, bands=9.0, spot=None, storms=0.0):
    cs = [rgb(c) for c in colors]

    def fn(X, Y, Z, n3):
        n = n3.fbm(X * 4 + 10, Y * 4 + 10, Z * 4 + 10, 4)
        lat = Y + (n - 0.5) * turbulence
        t = (np.sin(lat * bands) + 1) / 2
        idx = np.clip(((lat + 1) / 2 * (len(cs) - 1) * 3) % (len(cs) - 1), 0, len(cs) - 1.001)
        i0 = np.floor(idx).astype(int)
        f = idx - i0
        stack = np.stack(cs)
        col = mix(stack[i0], stack[np.minimum(i0 + 1, len(cs) - 1)], f[..., None])
        col = col * (0.88 + t[..., None] * 0.2)
        if spot is not None:
            sx, sy, sr, sc = spot
            v = np.array([sx, sy, math.sqrt(max(0.0, 1 - sx * sx - sy * sy))])
            d = np.sqrt(((X - v[0]) / 1.6) ** 2 + (Y - v[1]) ** 2 + ((Z - v[2]) / 1.6) ** 2)
            m = np.clip(1 - d / sr, 0, 1) ** 0.7
            col = mix(col, rgb(sc)[None, None, :], m[..., None])
        if storms > 0:
            s = n3.fbm(X * 9 + 3, Y * 9 + 3, Z * 9 + 3, 2)
            col = col * (1 + (s[..., None] - 0.5) * storms)
        return col

    return fn


def earthlike():
    ocean = rgb(0x1B4F9A)
    deep = rgb(0x0E2E66)
    land = rgb(0x4E7A34)
    desert = rgb(0xB89A62)
    ice = rgb(0xF2F6FA)
    cloud = rgb(0xFFFFFF)

    def fn(X, Y, Z, n3):
        n = n3.fbm(X * 1.8 + 5, Y * 1.8 + 5, Z * 1.8 + 5, 6)
        landmask = np.clip((n - 0.53) * 18, 0, 1)
        d = n3.fbm(X * 3 + 50, Y * 3 + 50, Z * 3 + 50, 3)
        land_col = mix(land[None, None, :], desert[None, None, :], np.clip((d - 0.5) * 4, 0, 1)[..., None])
        sea = mix(deep[None, None, :], ocean[None, None, :], np.clip((n - 0.3) * 4, 0, 1)[..., None])
        col = mix(sea, land_col, landmask[..., None])
        polar = np.clip((np.abs(Y) - 0.82) * 12, 0, 1)
        col = mix(col, ice[None, None, :], polar[..., None])
        c = n3.fbm(X * 4 + 90, Y * 6 + 90, Z * 4 + 90, 5)
        clouds = np.clip((c - 0.52) * 4, 0, 0.85)
        col = mix(col, cloud[None, None, :], clouds[..., None])
        return col

    return fn


def icy_lines(base, line, count=40, variance=0.12):
    b = rgb(base)
    lc = rgb(line)

    def fn(X, Y, Z, n3):
        n = n3.fbm(X * 3 + 1, Y * 3 + 1, Z * 3 + 1, 4)
        col = b[None, None, :] * (1 - variance + n[..., None] * variance * 2)
        r = np.random.default_rng(int(base) % 1000 + count)
        for _ in range(count):
            v = r.normal(size=3)
            v /= np.linalg.norm(v)
            d = np.abs(X * v[0] + Y * v[1] + Z * v[2])
            m = np.clip(1 - d / 0.012, 0, 1) * (0.5 + r.random() * 0.5)
            col = mix(col, lc[None, None, :], m[..., None])
        return col

    return fn


def two_tone(a, b, threshold=0.5, scale=1.4, sharpness=8.0, variance=0.15, craters=10):
    ca = rgb(a)
    cb = rgb(b)

    def fn(X, Y, Z, n3):
        n = n3.fbm(X * scale + 3, Y * scale + 3, Z * scale + 3, 4)
        t = np.clip((n - threshold) * sharpness + 0.5, 0, 1)
        d = n3.fbm(X * 6 + 9, Y * 6 + 9, Z * 6 + 9, 3)
        col = mix(ca[None, None, :], cb[None, None, :], t[..., None]) * (1 - variance + d[..., None] * variance * 2)
        return col

    return fn


def pluto_surface():
    tan = rgb(0xD9C2A6)
    heart = rgb(0xF4EEE6)
    dark = rgb(0x6A3422)

    def fn(X, Y, Z, n3):
        n = n3.fbm(X * 3 + 2, Y * 3 + 2, Z * 3 + 2, 4)
        col = tan[None, None, :] * (0.85 + n[..., None] * 0.3)
        # Cthulhu: dark equatorial belt
        belt = np.clip((0.25 - np.abs(Y + 0.1)) * 6, 0, 1) * np.clip((n - 0.35) * 4, 0, 1) * (X < 0.1)
        col = mix(col, dark[None, None, :], belt[..., None])
        # Tombaugh Regio: the heart
        hx, hy = 0.32, -0.05
        d1 = np.sqrt((X - hx + 0.12) ** 2 + (Y - hy - 0.08) ** 2)
        d2 = np.sqrt((X - hx - 0.12) ** 2 + (Y - hy - 0.08) ** 2)
        tri = (Y < hy + 0.1) & (np.abs(X - hx) < (Y - hy + 0.38) * 0.75)
        heart_mask = ((d1 < 0.19) | (d2 < 0.19) | tri) & (Z > 0)
        col = np.where(heart_mask[..., None], heart * (0.95 + n[..., None] * 0.1), col)
        return col

    return fn


def charon_surface():
    grey = rgb(0x9A9692)
    red = rgb(0x7A3A28)

    def fn(X, Y, Z, n3):
        n = n3.fbm(X * 3 + 8, Y * 3 + 8, Z * 3 + 8, 4)
        col = grey[None, None, :] * (0.82 + n[..., None] * 0.36)
        pole = np.clip((Y - 0.62) * 6 + (n - 0.5), 0, 1)
        col = mix(col, red[None, None, :], pole[..., None])
        return col

    return fn


def sun_texture(size, core=True):
    c = (np.arange(size) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(c, c)
    d = np.sqrt(x * x + y * y)
    img = np.zeros((size, size, 4))
    if core:
        a = np.clip((0.92 - d) * size * 0.25, 0, 1)
        z = np.sqrt(np.clip(1 - (d / 0.92) ** 2, 0, 1))
        col = np.stack([np.full_like(d, 255), 240 + 15 * z, 200 + 55 * z], axis=-1)
        img[..., :3] = col
        img[..., 3] = a * 255
    else:
        glow = np.clip(np.exp(-d * 4.2) - np.exp(-4.2), 0, 1) / (1 - math.exp(-4.2))
        glow = glow ** 1.3
        img[..., :3] = 255
        img[..., 3] = glow * 255
    return img


def ring_texture(size, profile):
    """profile: list of (inner, outer, alpha, color) radial bands in [0, 1] of the half-size."""
    c = (np.arange(size) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(c, c)
    d = np.sqrt(x * x + y * y)
    img = np.zeros((size, size, 4))
    r = np.random.default_rng(7)
    fine = 0.85 + 0.15 * np.sin(d * 240 + r.random() * 6) * np.sin(d * 90)
    for inner, outer, alpha, color in profile:
        m = (d >= inner) & (d < outer)
        col = rgb(color)
        img[..., :3] = np.where(m[..., None], col[None, None, :] * fine[..., None], img[..., :3])
        img[..., 3] = np.where(m, alpha * 255 * fine, img[..., 3])
    return img


def phase_sheet(frame=64, grid=4, radius=0.94):
    frames = grid * grid
    sheet = np.zeros((frame * grid, frame * grid, 4))
    c = (np.arange(frame) + 0.5) / frame * 2 - 1
    x, y = np.meshgrid(c, -c)
    x = x / radius
    y = y / radius
    rr = x * x + y * y
    inside = rr <= 1.0
    z = np.sqrt(np.clip(1 - rr, 0, 1))
    edge = np.clip((1.0 - np.sqrt(rr)) * frame * radius * 0.5 + 0.5, 0, 1)
    for f in range(frames):
        psi = f / (frames - 1) * math.pi
        lit = x * math.sin(psi) + z * math.cos(psi)
        shadow = np.clip((0.06 - lit) / 0.12, 0, 1) * 0.93
        a = np.where(inside, shadow * edge, 0) * 255
        gx, gy = f % grid, f // grid
        sheet[gy * frame:(gy + 1) * frame, gx * frame:(gx + 1) * frame, 3] = a
    return sheet


def skybox_faces(size, galactic_normal, seed=1234):
    """Six cube faces matching SpaceSkyRenderer#drawSkybox (vanilla End-sky face layout)."""
    n = np.array(galactic_normal, dtype=np.float64)
    n /= np.linalg.norm(n)
    # Galactic centre direction: in the plane, pick a direction.
    a = np.cross(n, [0, 1, 0])
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    centre = a * 0.8 + b * 0.6
    centre /= np.linalg.norm(centre)

    noise = Noise3(seed, 64)
    neb = Noise3(seed + 1, 64)
    r = np.random.default_rng(seed)

    def rx(t):
        c, s = math.cos(t), math.sin(t)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

    def rz(t):
        c, s = math.cos(t), math.sin(t)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

    rots = [np.eye(3), rx(math.pi / 2), rx(-math.pi / 2), rx(math.pi), rz(math.pi / 2), rz(-math.pi / 2)]
    coords = (np.arange(size) + 0.5) / size * 200 - 100
    uu, vv = np.meshgrid(coords, coords)  # uu varies along x (u), vv along y (v)
    faces = []
    for rot in rots:
        pts = np.stack([uu, np.full_like(uu, -100.0), vv], axis=-1)
        d = pts @ rot.T
        d /= np.linalg.norm(d, axis=-1, keepdims=True)
        X, Y, Z = d[..., 0], d[..., 1], d[..., 2]
        lat = X * n[0] + Y * n[1] + Z * n[2]
        band = np.exp(-(lat ** 2) / (2 * 0.13 ** 2))
        cang = np.clip(X * centre[0] + Y * centre[1] + Z * centre[2], -1, 1)
        core = np.exp(-(np.arccos(cang) ** 2) / 0.35)
        fine = noise.fbm(X * 6 + 50, Y * 6 + 50, Z * 6 + 50, 5)
        dust = noise.fbm(X * 10 + 7, Y * 10 + 7, Z * 10 + 7, 4)
        lanes = np.clip(1 - np.clip((dust - 0.45) * 3, 0, 1) * np.exp(-(lat ** 2) / (2 * 0.04 ** 2)) * 1.2, 0, 1)
        milky = band * (0.35 + fine * 0.9) * (1 + core * 1.6) * lanes
        col = np.zeros(d.shape)
        col += milky[..., None] * np.array([150, 140, 130])[None, None, :]
        col += (core * band)[..., None] * np.array([60, 40, 10])[None, None, :]
        # faint coloured nebulae
        nb = neb.fbm(X * 2.5 + 30, Y * 2.5 + 30, Z * 2.5 + 30, 5)
        hue = neb.fbm(X * 1.2 + 80, Y * 1.2 + 80, Z * 1.2 + 80, 2)
        cloud = np.clip((nb - 0.56) * 3.2, 0, 1) ** 1.5
        neb_col = mix(np.array([90, 40, 120])[None, None, :], np.array([30, 70, 140])[None, None, :], hue[..., None])
        neb_col = mix(neb_col, np.array([140, 40, 70])[None, None, :], np.clip((hue - 0.6) * 4, 0, 1)[..., None])
        col += cloud[..., None] * neb_col * 0.75
        # dim background stars (more of them near the band)
        density = 0.004 + band * 0.02
        stars = r.random(d.shape[:2]) < density
        bright = r.random(d.shape[:2]) * 120 + 40
        col += (stars * bright)[..., None] * np.array([1.0, 1.0, 1.05])[None, None, :]
        faces.append(np.clip(col, 0, 255))
    return faces


def armor_layer(layer):
    """Space suit armour texture (64x32)."""
    img = np.zeros((32, 64, 4))
    r = np.random.default_rng(99 + layer)
    white = rgb(0xE9ECEF)
    grey = rgb(0xA9B0B8)
    dark = rgb(0x4A5058)
    orange = rgb(0xE07A20)
    blue = rgb(0x2E6FC8)

    def fill(x0, y0, x1, y1, color, noise=0.05):
        for y in range(y0, y1):
            for x in range(x0, x1):
                img[y, x, :3] = color * (1 + (r.random() - 0.5) * noise)
                img[y, x, 3] = 255

    if layer == 1:
        # helmet
        fill(0, 0, 32, 16, white)
        for x in range(0, 32):
            img[15, x, :3] = grey
        # visor on the front face (8..16, 8..16)
        for y in range(9, 15):
            for x in range(9, 15):
                t = (y - 9) / 5
                img[y, x, :3] = mix(rgb(0xF0C040), rgb(0x203050), 0.3 + t * 0.6)
        img[10, 10, :3] = 255
        img[10, 11, :3] = 255
        # chest (body 16..40, 16..32) and arms (40..56, 16..32)
        fill(16, 16, 40, 32, white)
        fill(40, 16, 56, 32, white)
        for x in range(40, 56):
            img[24, x, :3] = orange
            img[25, x, :3] = orange
            img[31, x, :3] = grey
        # control panel on the chest front (20..28, 20..32)
        fill(21, 22, 27, 26, dark, 0)
        img[23, 22, :3] = rgb(0x40E040)
        img[23, 24, :3] = rgb(0xE04040)
        img[24, 25, :3] = rgb(0x4080FF)
        for x in range(16, 40):
            img[31, x, :3] = grey
        # boots: lower part of the leg box (0..16, 16..32)
        for y in range(16, 32):
            for x in range(0, 16):
                if y >= 26 or y < 20:
                    img[y, x, :3] = dark * (1 + (r.random() - 0.5) * 0.08) if y >= 26 else grey
                    img[y, x, 3] = 255
        for x in range(0, 16):
            img[26, x, :3] = grey
    else:
        # leggings: legs (0..16, 16..32) and waist (16..40, 16..32)
        fill(0, 16, 16, 32, white)
        fill(16, 16, 40, 32, white)
        for y in range(16, 32):
            img[y, 4, :3] = blue
            img[y, 12, :3] = blue
        for x in range(16, 40):
            img[22, x, :3] = grey
            img[23, x, :3] = dark
    return img


def rocket_texture(body, accent, metal, window=0x7EC8F0):
    """128x128 texture matching RocketEntityModel's UV layout."""
    img = np.zeros((128, 128, 4))
    r = np.random.default_rng(body)
    B, A, M, W = rgb(body), rgb(accent), rgb(metal), rgb(window)

    def box(u, v, dx, dy, dz, color, pattern=None):
        w = 2 * (dx + dz)
        h = dz + dy
        for y in range(v, v + h):
            for x in range(u, u + w):
                c = color * (1 + (r.random() - 0.5) * 0.05)
                if pattern is not None:
                    c = pattern(x - u, y - v, c, dx, dy, dz)
                img[y, x, :3] = c
                img[y, x, 3] = 255

    def body_pattern(x, y, c, dx, dy, dz):
        side_y = y - dz
        if side_y < 0:
            return c * 0.95
        if side_y in (2, 3):
            return A
        if side_y in (dy - 4, dy - 3):
            return A
        if side_y % 9 == 6:
            return c * 0.8
        if x % (dx + dz) == 0:
            return c * 0.85
        return c

    def nozzle_pattern(x, y, c, dx, dy, dz):
        # bottom face glows
        if y < dz and dz + dx <= x < dz + 2 * dx:
            cx, cy = x - dz - dx - dx / 2 + 0.5, y - dz / 2 + 0.5
            if cx * cx + cy * cy < (dx / 2 - 1) ** 2:
                return rgb(0xFF9A30)
            return M * 0.5
        if y - dz == dy - 1:
            return M * 0.6
        return c

    def accent_pattern(x, y, c, dx, dy, dz):
        if (y - dz) == 0:
            return c * 1.15
        return c

    def window_pattern(x, y, c, dx, dy, dz):
        if y >= dz and dz <= x < dz + dx:
            sy = y - dz
            sx = x - dz
            if sx in (0, dx - 1) or sy in (0, dy - 1):
                return M
            if sx + sy < 3:
                return np.minimum(W * 1.3, 255)
            return W
        return M

    box(0, 0, 16, 34, 16, B, body_pattern)
    box(64, 0, 12, 16, 12, B, body_pattern)
    box(64, 28, 10, 6, 10, M, nozzle_pattern)
    box(0, 50, 8, 8, 8, A, accent_pattern)
    box(32, 50, 4, 6, 4, A, accent_pattern)
    box(48, 50, 2, 4, 2, M)
    box(0, 66, 6, 18, 2, A, accent_pattern)
    box(16, 66, 2, 18, 6, A, accent_pattern)
    box(32, 66, 6, 6, 1, M, window_pattern)
    return img
