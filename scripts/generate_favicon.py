"""
Generate KoNote favicon and icon PNGs — balanced rounded K.
Run: python scripts/generate_favicon.py
Outputs to static/img/
"""
from PIL import Image, ImageDraw
import os

# Warm blue gradient — friendly, not corporate
BLUE_LIGHT = (74, 144, 217)   # #4A90D9 — top-left
BLUE_DARK = (37, 96, 199)     # #2560C7 — bottom-right
WHITE = (255, 255, 255)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE_DIR, "static", "img")
os.makedirs(IMG_DIR, exist_ok=True)


def draw_round_line(draw, p1, p2, width, fill):
    """Draw a thick line with round end caps."""
    draw.line([p1, p2], fill=fill, width=width)
    r = width // 2
    for x, y in [p1, p2]:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def make_gradient_bg(size):
    """Create a rounded-rect blue gradient background."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s = size / 512.0
    radius = max(int(96 * s), 1)

    if size >= 64:
        draw = ImageDraw.Draw(img)
        for y in range(size):
            for x in range(size):
                t = (x + y) / (2 * size)
                r = int(BLUE_LIGHT[0] * (1 - t) + BLUE_DARK[0] * t)
                g = int(BLUE_LIGHT[1] * (1 - t) + BLUE_DARK[1] * t)
                b = int(BLUE_LIGHT[2] * (1 - t) + BLUE_DARK[2] * t)
                draw.point((x, y), fill=(r, g, b, 255))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, size - 1, size - 1], radius=radius, fill=255,
        )
        img.putalpha(mask)
    else:
        mid = tuple((a + b) // 2 for a, b in zip(BLUE_LIGHT, BLUE_DARK))
        ImageDraw.Draw(img).rounded_rectangle(
            [0, 0, size - 1, size - 1], radius=radius, fill=mid,
        )
    return img


def draw_k(img, size):
    """Balanced, friendly rounded-stroke K.

    Key fixes:
    - Shorter, steeper arms (42 degrees vs 39) so they don't look too long
    - Thicker stroke (80px vs 72) for more visual presence
    - Perfectly centred in the square — equal margins on all sides
    """
    draw = ImageDraw.Draw(img)
    s = size / 512.0
    w = max(int(80 * s), 2)

    strokes = [
        [(150, 100), (150, 412)],   # stem
        [(190, 256), (362, 100)],   # upper arm — 42 degrees, shorter
        [(190, 256), (362, 412)],   # lower arm — 42 degrees, shorter
    ]
    for p1, p2 in strokes:
        sp1 = (int(p1[0] * s), int(p1[1] * s))
        sp2 = (int(p2[0] * s), int(p2[1] * s))
        draw_round_line(draw, sp1, sp2, w, WHITE)


def main():
    sizes = {
        "favicon-16.png": 16,
        "favicon-32.png": 32,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }

    for filename, size in sizes.items():
        img = make_gradient_bg(size)
        draw_k(img, size)
        img.save(os.path.join(IMG_DIR, filename), "PNG")
        print(f"  {filename} ({size}x{size})")

    # Multi-resolution .ico (16 + 32 + 48)
    ico_sizes = [16, 32, 48]
    ico_images = []
    for sz in ico_sizes:
        img = make_gradient_bg(sz)
        draw_k(img, sz)
        ico_images.append(img.convert("RGBA"))

    ico_path = os.path.join(IMG_DIR, "favicon.ico")
    ico_images[0].save(
        ico_path, format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[1:],
    )
    print(f"  favicon.ico ({', '.join(str(s) for s in ico_sizes)})")
    print(f"\nAll icons saved to {IMG_DIR}")


if __name__ == "__main__":
    main()
