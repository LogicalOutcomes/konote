"""
Generate KoNote icon PNGs from the brand SVGs.

Renders two icon families:
  "any" — favicon.svg (blue/grey K on white) for browser tabs and bookmarks
  "maskable" — favicon-white.svg (white K on brand blue) for phone home screens

Also generates the multi-resolution .ico file and copies PWA icons
to the portal directory.

Requirements: pip install cairosvg Pillow
  (On Windows, cairosvg also needs the GTK3 runtime / Cairo DLL)

Run:  python scripts/generate_favicon.py
"""
import os
import shutil
from io import BytesIO

from PIL import Image

try:
    import cairosvg
except ImportError:
    raise SystemExit(
        "cairosvg is required:  pip install cairosvg\n"
        "On Windows you also need GTK3 runtime — see "
        "https://github.com/niccokunzmann/cairosvg-wheels"
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_PATH = os.path.join(BASE_DIR, "static", "img", "favicon.svg")
SVG_WHITE_PATH = os.path.join(BASE_DIR, "static", "img", "favicon-white.svg")
IMG_DIR = os.path.join(BASE_DIR, "static", "img")
PORTAL_DIR = os.path.join(BASE_DIR, "static", "portal", "icons")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(PORTAL_DIR, exist_ok=True)

BRAND_BLUE = (49, 118, 170)  # #3176aa


def render_icon(svg_path, size, padding_pct=12, bg_color=(255, 255, 255)):
    """Render SVG K-mark centred on a square background with padding."""
    render_size = max(size * 2, 512)
    png_data = cairosvg.svg2png(
        url=svg_path, output_width=render_size, output_height=render_size
    )
    mark = Image.open(BytesIO(png_data)).convert("RGBA")

    bg = Image.new("RGB", (size, size), bg_color)

    pad = int(size * padding_pct / 100)
    inner = size - 2 * pad
    mark.thumbnail((inner, inner), Image.LANCZOS)

    # Centre the mark (with upward optical shift for maskable icons)
    x = (size - mark.width) // 2
    y = (size - mark.height) // 2
    if padding_pct >= 20:
        y -= int(size * 0.015)  # 1.5% upward shift
    bg.paste(mark, (x, y), mark)

    return bg


def main():
    if not os.path.exists(SVG_PATH):
        raise SystemExit(f"SVG not found: {SVG_PATH}")
    if not os.path.exists(SVG_WHITE_PATH):
        raise SystemExit(f"White SVG not found: {SVG_WHITE_PATH}")

    # --- "any" icons: blue/grey K on white (tabs, bookmarks) ---
    print("Generating 'any' icons (white background)...")
    any_sizes = {
        "favicon-16.png": 16,
        "favicon-32.png": 32,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }
    for filename, size in any_sizes.items():
        img = render_icon(SVG_PATH, size, padding_pct=12)
        img.save(os.path.join(IMG_DIR, filename), "PNG")
        print(f"  {filename} ({size}x{size})")

    # Multi-resolution .ico (16 + 32 + 48)
    ico_sizes = [16, 32, 48]
    ico_images = [
        render_icon(SVG_PATH, sz, padding_pct=12).convert("RGBA")
        for sz in ico_sizes
    ]
    ico_path = os.path.join(IMG_DIR, "favicon.ico")
    ico_images[0].save(
        ico_path, format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[1:],
    )
    print(f"  favicon.ico ({', '.join(str(s) for s in ico_sizes)})")

    # --- "maskable" icons: white K on brand blue (phone home screens) ---
    print("\nGenerating 'maskable' icons (blue background)...")
    maskable_sizes = {
        "apple-touch-icon.png": 180,
        "icon-192-maskable.png": 192,
        "icon-512-maskable.png": 512,
    }
    for filename, size in maskable_sizes.items():
        img = render_icon(SVG_WHITE_PATH, size, padding_pct=22, bg_color=BRAND_BLUE)
        img.save(os.path.join(IMG_DIR, filename), "PNG")
        print(f"  {filename} ({size}x{size})")

    # --- Copy PWA icons to portal directory ---
    print("\nCopying to portal/icons/...")
    for f in ("icon-192.png", "icon-512.png",
              "icon-192-maskable.png", "icon-512-maskable.png"):
        shutil.copy2(os.path.join(IMG_DIR, f), os.path.join(PORTAL_DIR, f))
        print(f"  portal/{f}")

    print(f"\nAll icons saved to {IMG_DIR}")


if __name__ == "__main__":
    main()
