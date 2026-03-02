"""
Generate maskable KoNote icon PNGs from existing source icon.

Uses the existing icon-512.png to create maskable variants with:
- Brand blue (#3176aa) background
- All-white K-mark (simplified for contrast)
- 22% padding for maskable safe zone
- 1.5% upward optical shift

Also regenerates apple-touch-icon with maskable treatment (iOS always masks).

Run:  python scripts/generate_maskable_icons.py
"""
import os
import shutil

from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_512 = os.path.join(BASE_DIR, "static", "img", "icon-512.png")
IMG_DIR = os.path.join(BASE_DIR, "static", "img")
PORTAL_DIR = os.path.join(BASE_DIR, "static", "portal", "icons")

BRAND_BLUE = (49, 118, 170)
PADDING_PCT = 22


def extract_mark_as_white(source_img):
    """Extract K-mark from white-background icon, convert to white RGBA."""
    rgba = source_img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > 240 and g > 240 and b > 240:
                # Near-white background -> transparent
                pixels[x, y] = (0, 0, 0, 0)
            else:
                # K-mark pixels -> white, keep alpha
                pixels[x, y] = (255, 255, 255, a)
    return rgba


def render_maskable(white_mark, size):
    """Render white K-mark on blue background with safe-zone padding."""
    bg = Image.new("RGBA", (size, size), BRAND_BLUE + (255,))

    pad = int(size * PADDING_PCT / 100)
    inner = size - 2 * pad

    mark = white_mark.copy()
    mark.thumbnail((inner, inner), Image.LANCZOS)

    # Centre with 1.5% upward optical shift
    x = (size - mark.width) // 2
    y = (size - mark.height) // 2 - int(size * 0.015)

    bg.paste(mark, (x, y), mark)
    return bg.convert("RGB")


def main():
    if not os.path.exists(ICON_512):
        raise SystemExit(f"Source icon not found: {ICON_512}")

    source = Image.open(ICON_512).convert("RGB")
    white_mark = extract_mark_as_white(source.copy())

    maskable_sizes = {
        "apple-touch-icon.png": 180,
        "icon-192-maskable.png": 192,
        "icon-512-maskable.png": 512,
    }

    for filename, size in maskable_sizes.items():
        img = render_maskable(white_mark, size)
        path = os.path.join(IMG_DIR, filename)
        img.save(path, "PNG")
        print(f"  {filename} ({size}x{size})")

    # Copy maskable PWA icons to portal directory
    os.makedirs(PORTAL_DIR, exist_ok=True)
    for f in ("icon-192-maskable.png", "icon-512-maskable.png"):
        src = os.path.join(IMG_DIR, f)
        dst = os.path.join(PORTAL_DIR, f)
        shutil.copy2(src, dst)
        print(f"  portal/{f} (copied)")

    print(f"\nMaskable icons saved to {IMG_DIR}")


if __name__ == "__main__":
    main()
