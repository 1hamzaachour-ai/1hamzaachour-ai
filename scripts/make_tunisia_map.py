"""Draw the stand-in portrait: a shaded-relief ASCII locator map of Tunisia.

Tunisia's real terrain is hillshaded (lit from the north-west, high ground in
denser glyphs), the neighbouring coastlines are dotted in for context, and Tunis
gets a pin. make_ascii_svg.py then types it in.

Data, kept in data/maps/:
  tunisia-region.geojson  Natural Earth 1:10m countries (public domain)
  tunisia-dem.png         elevation from AWS Terrain Tiles (Mapzen terrarium: SRTM,
                          ETOPO1 and others), fetched on the first run, then cached

    python scripts/make_tunisia_map.py           # -> assets/ascii-portrait.svg
"""
from __future__ import annotations

import argparse
import io
import json
import math
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw

import make_ascii_svg

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "data" / "maps"
REGION = MAPS / "tunisia-region.geojson"
DEM = MAPS / "tunisia-dem.png"

CENTER = (9.55, 33.8)     # lon, lat at the middle of the view
SPAN_LAT = 8.2            # degrees of latitude, top to bottom
TUNIS = (10.18, 36.81)
RASTER_H = 1000           # px, before downsampling to characters
EXAGGERATION = 10         # Tunisia's relief is gentle; steepen it so the hills read

DEM_BOUNDS = (7.3, 30.1, 11.8, 37.6)   # west, south, east, north
DEM_RES = 0.0125                        # degrees per pixel, ~1.2 km
DEM_STEP = 8                            # metres per grey level: 0-255 -> 0-2040 m
TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ZOOM = 7


def fetch_dem() -> None:
    """One-off: mosaic Terrain Tiles around Tunisia and resample them onto a lon/lat grid."""
    world = 256 * 2 ** ZOOM

    def mercator(lon, lat):
        return (lon + 180) / 360 * world, (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * world

    west, south, east, north = DEM_BOUNDS
    (x0, y0), (x1, y1) = mercator(west, north), mercator(east, south)
    tx0, ty0, tx1, ty1 = int(x0 // 256), int(y0 // 256), int(x1 // 256), int(y1 // 256)
    mosaic = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256), np.float32)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            resp = requests.get(TILES.format(z=ZOOM, x=tx, y=ty), timeout=30)
            resp.raise_for_status()
            rgb = np.asarray(Image.open(io.BytesIO(resp.content)).convert("RGB"), np.float32)
            mosaic[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = (
                rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768)      # terrarium encoding

    lons = west + (np.arange(round((east - west) / DEM_RES)) + 0.5) * DEM_RES
    lats = north - (np.arange(round((north - south) / DEM_RES)) + 0.5) * DEM_RES
    mx, my = mercator(*np.meshgrid(lons, lats))
    elev = cv2.remap(mosaic, np.float32(mx - tx0 * 256), np.float32(my - ty0 * 256), cv2.INTER_LINEAR)
    MAPS.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.uint8(np.clip(np.round(elev / DEM_STEP), 0, 255))).save(DEM, optimize=True)
    print(f"cached {DEM.relative_to(ROOT)} from {(tx1 - tx0 + 1) * (ty1 - ty0 + 1)} terrain tiles")


def rasterize(aspect: float):
    """Tunisia mask, neighbouring-land mask and elevation (m) on one equirectangular raster."""
    h = RASTER_H
    w = round(h * aspect)
    k = h / SPAN_LAT
    coslat = math.cos(math.radians(CENTER[1]))
    left = CENTER[0] - w / (k * coslat) / 2
    top = CENTER[1] + SPAN_LAT / 2

    def project(lon: float, lat: float) -> tuple[float, float]:
        return (lon - left) * k * coslat, (top - lat) * k

    focus, context = Image.new("L", (w, h)), Image.new("L", (w, h))
    for feature in json.loads(REGION.read_text(encoding="utf-8"))["features"]:
        draw = ImageDraw.Draw(focus if feature["properties"]["role"] == "focus" else context)
        for outer, *holes in feature["geometry"]["coordinates"]:
            draw.polygon([project(*p) for p in outer], fill=255)
            for hole in holes:
                draw.polygon([project(*p) for p in hole], fill=0)
    tun = np.asarray(focus) > 0
    near = (np.asarray(context) > 0) & ~tun

    west, _, _, north = DEM_BOUNDS
    jj, ii = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    lon, lat = left + jj / (k * coslat), top - ii / k
    dem = np.asarray(Image.open(DEM), np.float32) * DEM_STEP
    elev = cv2.remap(dem, np.float32((lon - west) / DEM_RES - 0.5), np.float32((north - lat) / DEM_RES - 0.5),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    tx, ty = project(*TUNIS)
    return tun, near, elev, (tx / w, ty / h)


def relief(tun: np.ndarray, near: np.ndarray, elev: np.ndarray) -> Image.Image:
    """Hillshade lit from the north-west plus a lift for altitude; white outside Tunisia."""
    metres_per_px = SPAN_LAT * 111_320 / RASTER_H
    z = cv2.GaussianBlur(elev, (0, 0), 2.0) * EXAGGERATION
    gy, gx = np.gradient(z, metres_per_px)
    normal = np.dstack([-gx, -gy, np.ones_like(gx)])
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    light = np.array([-1.0, -1.0, math.sqrt(2)]) / 2           # from the NW, 45 degrees up
    ink = 0.42 + 0.30 * np.clip(elev / 1200, 0, 1) + 1.4 * (normal @ light - light[2])
    ink = np.clip(ink, 0.25, 1.0)

    # The chotts: salt flats far inland and barely above sea level print as sparse texture.
    sea_km = cv2.distanceTransform(np.uint8(tun | near), cv2.DIST_L2, 5) * metres_per_px / 1000
    ink = np.where((elev < 30) & (sea_km > 50), 0.12, ink)
    return Image.fromarray(np.uint8(255 * (1 - np.where(tun, ink, 0.0))))


def outline(lines: list[str], tun: np.ndarray, placement, lift: int = 2) -> list[str]:
    """Push Tunisia's edge cells a few glyphs denser so the silhouette stays crisp."""
    c0, r0, gc, gr = placement
    home = np.pad(cv2.resize(tun.astype(np.float32), (gc, gr), interpolation=cv2.INTER_AREA) >= 0.5, 1)
    edge = home[1:-1, 1:-1] & ~(home[:-2, 1:-1] & home[2:, 1:-1] & home[1:-1, :-2] & home[1:-1, 2:])
    ramp = make_ascii_svg.RAMP
    grid = [list(line) for line in lines]
    for r, c in zip(*np.nonzero(edge)):
        ch = grid[r0 + r][c0 + c]
        if ch != " ":
            grid[r0 + r][c0 + c] = ramp[min(len(ramp) - 1, ramp.index(ch) + lift)]
    return ["".join(row) for row in grid]


def dot_coastlines(lines: list[str], near: np.ndarray, tun: np.ndarray, placement) -> list[str]:
    """Dot the neighbours' coastlines: their land cells that touch open sea."""
    c0, r0, gc, gr = placement

    def cover(mask):
        return cv2.resize(mask.astype(np.float32), (gc, gr), interpolation=cv2.INTER_AREA) >= 0.3

    land, home = cover(near), cover(tun)
    sea = np.pad(~land & ~home, 1)
    coast = land & (sea[:-2, 1:-1] | sea[2:, 1:-1] | sea[1:-1, :-2] | sea[1:-1, 2:])
    grid = [list(line) for line in lines]
    for r, c in zip(*np.nonzero(coast)):
        if grid[r0 + r][c0 + c] == " ":
            grid[r0 + r][c0 + c] = "."
    return ["".join(row) for row in grid]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=make_ascii_svg.OUT)
    parser.add_argument("--cols", type=int, default=96)
    parser.add_argument("--save-image", type=Path, help="also save the shaded grayscale relief")
    args = parser.parse_args()

    if not DEM.exists():
        fetch_dem()
    _, _, aw, ah = make_ascii_svg.AREA
    tun, near, elev, (fx, fy) = rasterize(aw / ah)
    img = relief(tun, near, elev)
    if args.save_image:
        img.save(args.save_image)

    lines, placement = make_ascii_svg.to_grid(img, args.cols)
    lines = dot_coastlines(outline(lines, tun, placement), near, tun, placement)
    c0, r0, gc, gr = placement
    svg_text = make_ascii_svg.render(lines, "~/tunisia.ascii", note="36.8°N 10.2°E",
                                     pin=(c0 + fx * gc, r0 + fy * gr, "Tunis"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(svg_text, encoding="utf-8")
    print(f"wrote {args.out.relative_to(ROOT)} ({args.out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
