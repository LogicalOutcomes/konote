"""
Generate KoNote icon PNGs from the brand SVG.

Renders static/img/favicon.svg onto a white background at each
required size.  Also generates the multi-resolution .ico file and
copies icons to the portal directory.

Requirements: pip install cairosvg Pillow

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
IMG_DIR = os.path.join(BASE_DIR, "static", "img")
PORTAL_DIR = os.path.join(BASE_DIR, "static", "portal", "icons")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(PORTAL_DIR, exist_ok=True)


def render_icon(svg_path, size, padding_pct=12):
    """Render the SVG K mark centred on a white square with padding."""
    # Render SVG at high res, then resize
    render_size = max(size * 2, 512)
    png_data = cairosvg.svg2png(
        url=svg_path,
        output_width=render_size,
        output_height=render_size,
    )
    mark = Image.open(BytesIO(png_data)).convert("RGBA")

    # Create white background
    bg = Image.new("RGB", (size, size), (255, 255, 255))

    # Scale mark to fit with padding
    pad = int(size * padding_pct / 100)
    inner = size - 2 * pad
    mark.thumbnail((inner, inner), Image.LANCZOS)

    # Centre the mark
    x = (size - mark.width) // 2
    y = (size - mark.height) // 2
    bg.paste(mark, (x, y), mark)  # use alpha as mask

    return bg


def main():
    if not os.path.exists(SVG_PATH):
        raise SystemExit(f"SVG not found: {SVG_PATH}")

    sizes = {
        "favicon-16.png": 16,
        "favicon-32.png": 32,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }

    for filename, size in sizes.items():
        img = render_icon(SVG_PATH, size)
        img.save(os.path.join(IMG_DIR, filename), "PNG")
        print(f"  {filename} ({size}x{size})")

    # Multi-resolution .ico (16 + 32 + 48)
    ico_sizes = [16, 32, 48]
    ico_images = []
    for sz in ico_sizes:
        ico_images.append(render_icon(SVG_PATH, sz).convert("RGBA"))

    ico_path = os.path.join(IMG_DIR, "favicon.ico")
    ico_images[0].save(
        ico_path, format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[1:],
    )
    print(f"  favicon.ico ({', '.join(str(s) for s in ico_sizes)})")

    # Copy PWA icons to portal directory
    for f in ("icon-192.png", "icon-512.png"):
        src = os.path.join(IMG_DIR, f)
        dst = os.path.join(PORTAL_DIR, f)
        shutil.copy2(src, dst)
        print(f"  portal/{f} (copied)")

    print(f"\nAll icons saved to {IMG_DIR}")


if __name__ == "__main__":
    main()
