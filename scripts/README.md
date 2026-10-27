# Profile art

The terminal header on the profile is three animated SVGs. GitHub strips scripts
and most CSS from READMEs but plays CSS keyframes and SMIL inside an SVG shown as
an `<img>`, so all the motion lives in the files below.

| File | Made by | Refreshed |
| --- | --- | --- |
| `assets/contrib-heatmap.svg` | `fetch_contributions.py` + `render_heatmap_svg.py` | daily, by the **Update profile art** workflow |
| `assets/info-card.svg` | `make_info_card.py` | by hand, when the details in `INFO` change |
| `assets/ascii-portrait.svg` | `make_tunisia_map.py`, or `prep_photo.py` + `make_ascii_svg.py` | by hand |

`terminal_theme.py` holds the shared window look. `STATIC=1` before any generator
writes a frozen final frame, which is handy for previews.

## Setup (local, Windows)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\pip install -r scripts\requirements-portrait.txt
```

The daily workflow only installs `requirements.txt` (requests + beautifulsoup4).

## Swap the Tunisia map for your photo

Use a clear, front-facing head-and-shoulders photo. Put it in the repo root:
`.gitignore` keeps photos there out of git, so only the ASCII version is published.

```powershell
.venv\Scripts\python scripts\prep_photo.py my-photo.jpg   # cut-out + contrast -> source-prepped.png
.venv\Scripts\python scripts\make_ascii_svg.py            # -> assets\ascii-portrait.svg
```

Tweak with `--cols` (detail), `--gamma` (mid-tones) and `--clip` (contrast) if the
face looks flat. Go back to the map with `.venv\Scripts\python scripts\make_tunisia_map.py`.

Then update the portrait's `alt` text in the root `README.md`, and commit.

## Data credits

- Contributions: scraped from the public calendar at `github.com/users/<user>/contributions`.
- Borders: [Natural Earth](https://www.naturalearthdata.com/) 1:10m countries (public domain).
- Elevation: [AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (Mapzen; SRTM, ETOPO1 and others).
