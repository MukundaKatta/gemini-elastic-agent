"""Render scene 1 (title card) for the gemini-elastic-agent demo video.

Outputs:
    .video-build/title.png
    .video-build/scene1_title.mp4   (30s, 1920x1080, H.264, no audio)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 1920, 1080

# Elastic-ish palette: deep ink + amber accent.
BG = "#0b1220"
FG = "#f8fafc"
FG_MUTED = "#94a3b8"
ACCENT = "#f59e0b"     # amber
ACCENT_2 = "#22d3ee"   # cyan

SF = "/System/Library/Fonts/SFNS.ttf"
MONO = "/System/Library/Fonts/SFNSMono.ttf"
if not Path(MONO).exists():
    MONO = "/System/Library/Fonts/Menlo.ttc"


def font(size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(MONO if mono else SF, size)


def render_title_png(path: Path) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Bottom footer panel.
    d.rectangle([(0, H - 64), (W, H)], fill="#111827")
    d.text((48, H - 50), "MIT", font=font(22), fill=FG_MUTED)
    d.text((W - 470, H - 50),
           "github.com/MukundaKatta/gemini-elastic-agent",
           font=font(22), fill=FG_MUTED)

    # Project name + thick amber underline.
    d.text((96, 260), "gemini-elastic-agent", font=font(116), fill=FG)
    d.rectangle([(96, 410), (380, 422)], fill=ACCENT)

    # Tagline.
    d.text((96, 470), "ADK agent with verbatim citations", font=font(46), fill=FG_MUTED)
    d.text((96, 530), "from Elastic hybrid search", font=font(46), fill=FG_MUTED)

    # Hackathon line.
    d.text((96, 660), "Google Cloud Rapid Agent Hackathon", font=font(32), fill=FG)
    d.text((96, 705), "Elastic partner track", font=font(32), fill=FG)

    # URLs in mono, cyan accent.
    d.text((96, 800),
           "github.com/MukundaKatta/gemini-elastic-agent",
           font=font(28, mono=True), fill=ACCENT_2)
    d.text((96, 845),
           "gemini-elastic-agent-1029931682737.us-central1.run.app",
           font=font(28, mono=True), fill=ACCENT_2)

    img.save(path, "PNG", optimize=True)


def render_title_video(png: Path, mp4: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(png),
            "-t", f"{duration:.2f}",
            "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-vf", "scale=1920:1080",
            str(mp4),
        ],
        check=True,
    )


def main() -> None:
    png = OUT / "title.png"
    mp4 = OUT / "scene1_title.mp4"
    render_title_png(png)
    print(f"  wrote {png.name}")
    render_title_video(png, mp4, duration=20.0)
    print(f"  wrote {mp4.name}")


if __name__ == "__main__":
    main()
