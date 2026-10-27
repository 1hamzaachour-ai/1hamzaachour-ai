"""Prep a photo for make_ascii_svg.py: cut out the subject, boost local contrast, set it on white.

A flatly lit face turns into a dark blob in ASCII. rembg isolates you from the
background, CLAHE (contrast-limited adaptive histogram equalisation) gives the
face real highlights and shadows, and a pure-white backdrop maps to the blank
end of the glyph ramp. The subject is inverted so lit skin prints dense (bright
on the dark panel), and the result is cropped to the subject.

    python scripts/prep_photo.py my-photo.jpg     # -> source-prepped.png (git-ignored)
    python scripts/make_ascii_svg.py              # -> assets/ascii-portrait.svg

The first run downloads rembg's person-segmentation model (~170 MB) into ~/.rembg.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "source-prepped.png"


def prep(photo: Path, clip: float = 2.5, model: str = "u2net_human_seg", margin: float = 0.04,
         negative: bool = False) -> Image.Image:
    rgb = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
    alpha = np.asarray(remove(rgb, session=new_session(model)))[..., 3].astype(np.float32) / 255

    gray = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2GRAY)
    gray = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(gray).astype(np.float32)
    if not negative:
        # Glyphs print light on the dark panel, so dense must mean bright: invert the subject,
        # but keep its darkest parts at a faint dot so the silhouette never vanishes.
        gray = np.minimum(255 - gray, 232)
    out = gray * alpha + 255 * (1 - alpha)

    ys, xs = np.nonzero(alpha > 0.5)
    if len(xs):
        pad = int(margin * max(xs.max() - xs.min(), ys.max() - ys.min()))
        out = out[max(0, ys.min() - pad):ys.max() + pad + 1, max(0, xs.min() - pad):xs.max() + pad + 1]
    return Image.fromarray(np.uint8(np.clip(out, 0, 255)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("photo", type=Path)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--clip", type=float, default=2.5, help="CLAHE clip limit: higher = punchier contrast")
    parser.add_argument("--model", default="u2net_human_seg", help="rembg model (u2net, isnet-general-use, ...)")
    parser.add_argument("--negative", action="store_true", help="map dark pixels to dense glyphs, like a photo negative")
    args = parser.parse_args()

    prep(args.photo, args.clip, args.model, negative=args.negative).save(args.out)
    print(f"wrote {args.out} -- now run: python scripts/make_ascii_svg.py")


if __name__ == "__main__":
    main()
