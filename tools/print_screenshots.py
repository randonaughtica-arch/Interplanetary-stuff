#!/usr/bin/env python3
"""Prints screenshots as small base64 JPEG lines (prefixed with @@IMG) so they can be read from CI logs."""
import base64
import io
import os
import sys

from PIL import Image

folder = sys.argv[1] if len(sys.argv) > 1 else "run/screenshots"
if not os.path.isdir(folder):
    print(f"No screenshots in {folder}")
    sys.exit(0)
for name in sorted(os.listdir(folder)):
    if not name.endswith(".png"):
        continue
    image = Image.open(os.path.join(folder, name)).convert("RGB")
    image.thumbnail((480, 270))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=70)
    print(f"@@IMG {name} {base64.b64encode(buffer.getvalue()).decode()}")
