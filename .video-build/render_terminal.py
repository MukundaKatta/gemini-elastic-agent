"""Render scene 2 (terminal screencast) for the gemini-elastic-agent demo.

Renders a sequence of "terminal state" PNG frames showing pytest, smoke,
and curl output progressively, then stitches them into a single MP4
scene with deterministic per-frame timing.

Outputs:
    .video-build/terminal_state_*.png  (intermediate)
    .video-build/scene2_terminal.mp4   (~90s, 1920x1080, H.264, no audio)
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 1920, 1080

# Terminal palette (matches Apple Terminal "Pro" theme-ish).
BG = "#0b1020"
PROMPT = "#22d3ee"
FG = "#e2e8f0"
DIM = "#94a3b8"
GREEN = "#22c55e"
RED = "#f87171"
YELLOW = "#fbbf24"

MONO = "/System/Library/Fonts/SFNSMono.ttf"
if not Path(MONO).exists():
    MONO = "/System/Library/Fonts/Menlo.ttc"
SF = "/System/Library/Fonts/SFNS.ttf"

FONT_SIZE = 22
LINE_H = 30
PAD_X = 60
PAD_Y = 80


def mono(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(MONO, size)


def title_font(size: int = 26) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(SF, size)


# Each "line" is a tuple (text, color). lines accumulate frame to frame.
PROMPT_PREFIX = "$ "


def make_blank() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Header bar.
    d.rectangle([(0, 0), (W, 50)], fill="#111827")
    d.text((PAD_X, 12), "gemini-elastic-agent - demo terminal",
           font=title_font(22), fill=DIM)
    return img, d


def render_frame(lines: list[tuple[str, str]], path: Path) -> None:
    img, d = make_blank()
    y = PAD_Y
    for text, color in lines:
        d.text((PAD_X, y), text, font=mono(), fill=color)
        y += LINE_H
    img.save(path, "PNG", optimize=True)


# Build the running transcript line by line.
def build_states() -> list[list[tuple[str, str]]]:
    L: list[tuple[str, str]] = []
    states: list[list[tuple[str, str]]] = []

    def commit() -> None:
        # Snapshot the current line list into the state stream.
        states.append(list(L))

    # ---- pytest ----
    L.append(("$ pytest -v", PROMPT))
    commit()
    L.append(("============================= test session starts ==============================", DIM))
    L.append(("platform darwin -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0", DIM))
    L.append(("collected 14 items", DIM))
    L.append(("", FG))
    commit()
    pytest_lines = [
        "tests/test_agent.py::test_adk_importable PASSED                          [  7%]",
        "tests/test_agent.py::test_agent_constructs_with_four_tools PASSED        [ 14%]",
        "tests/test_agent.py::test_end_to_end_demo_question_quotes_verbatim PASSED[ 21%]",
        "tests/test_agent.py::test_no_hallucination_when_zero_hits PASSED         [ 28%]",
        "tests/test_tools.py::test_list_indices_returns_three_indices PASSED      [ 35%]",
        "tests/test_tools.py::test_list_indices_shape_matches_elastic PASSED      [ 42%]",
        "tests/test_tools.py::test_hybrid_search_known_query_returns_three_hits   [ 50%]",
        "tests/test_tools.py::test_hybrid_search_respects_k PASSED                [ 57%]",
        "tests/test_tools.py::test_hybrid_search_zero_hits_for_unknown_query      [ 64%]",
        "tests/test_tools.py::test_get_document_runbook_full_text PASSED          [ 71%]",
        "tests/test_tools.py::test_get_document_missing_returns_not_found PASSED  [ 78%]",
        "tests/test_tools.py::test_summarize_index_returns_synthesis_verbatim     [ 85%]",
        "tests/test_tools.py::test_summarize_index_no_hits_path PASSED            [ 92%]",
        "tests/test_tools.py::test_search_then_get_document_is_consistent PASSED  [100%]",
    ]
    # Add pytest lines in chunks of 3 for a streaming feel.
    chunk = 3
    for i in range(0, len(pytest_lines), chunk):
        for line in pytest_lines[i:i + chunk]:
            L.append((line, GREEN))
        commit()
    L.append(("", FG))
    L.append(("============================== 14 passed in 0.57s ==============================", GREEN))
    commit()
    L.append(("", FG))

    # ---- smoke ----
    L.append(("$ python smoke.py", PROMPT))
    commit()
    L.append(("== gemini-elastic-agent smoke ==", DIM))
    L.append(("stub_mode=1", DIM))
    L.append(("", FG))
    L.append(("> how do I rotate the production database credentials", FG))
    commit()
    smoke_pass = [
        "  [PASS] has ANSWER section",
        "  [PASS] has HITS section",
        "  [PASS] has KEY QUOTES section",
        "  [PASS] has CONFIDENCE section",
        "  [PASS] has NEXT STEP section",
        "  [PASS] quotes rotate-prod-db-creds.sh",
        "  [PASS] quotes 15 minutes verbatim",
        "  [PASS] cites doc-runbook-db-rotate-v3",
        "  [PASS] names ops-runbooks index",
    ]
    L.append(("--- CHECKS ---", DIM))
    commit()
    for line in smoke_pass:
        L.append((line, GREEN))
    L.append(("", FG))
    L.append(("9/9 PASS", GREEN))
    commit()
    L.append(("", FG))

    # ---- curl ----
    curl_cmd = ('$ curl -sS https://gemini-elastic-agent-1029931682737.us-central1'
                '.run.app/ask \\')
    curl_cmd2 = '    -X POST -H "Content-Type: application/json" \\'
    curl_cmd3 = '    -d \'{"question":"how do I rotate the production database credentials"}\' | jq -r .answer'
    L.append((curl_cmd, PROMPT))
    L.append((curl_cmd2, PROMPT))
    L.append((curl_cmd3, PROMPT))
    commit()
    # Trim transcript window to last ~28 lines for the curl response,
    # so the answer is fully on screen.
    L.clear()
    L.append(("$ curl ... /ask  | jq -r .answer", PROMPT))
    L.append(("", FG))
    answer = [
        ("ANSWER:", YELLOW),
        ("  Run rotate-prod-db-creds.sh on jumpbox-prod-1, then wait", FG),
        ("  15 minutes for replication lag to settle across the 4 replicas,", FG),
        ("  then confirm with health-check-db.sh.", FG),
        ("", FG),
        ("HITS:", YELLOW),
        ("  - ops-runbooks/doc-runbook-db-rotate-v3 - 0.94", FG),
        ("  - ops-runbooks/doc-runbook-vault-unseal - 0.61", FG),
        ("  - ops-runbooks/doc-runbook-backup-restore - 0.52", FG),
        ("", FG),
        ("KEY QUOTES:", YELLOW),
        ('  - "Run rotate-prod-db-creds.sh in jumpbox-prod-1."', FG),
        ('  - "Wait 15 minutes for replication lag to settle..."', FG),
        ('  - "Confirm with health-check-db.sh which must return PASS..."', FG),
        ("", FG),
        ("CONFIDENCE:", YELLOW),
        ("  high. the top hit scored 0.94, above the 0.7 threshold.", FG),
        ("", FG),
        ("NEXT STEP:", YELLOW),
        ("  Search incident-postmortems for prior failures of", FG),
        ("  rotate-prod-db-creds.sh in the last 90 days.", FG),
    ]
    # Reveal the answer in 4 chunks for a streaming feel.
    chunks = [
        answer[:5],
        answer[5:10],
        answer[10:15],
        answer[15:],
    ]
    accumulated: list[tuple[str, str]] = []
    for ch in chunks:
        accumulated.extend(ch)
        L_snapshot = [("$ curl ... /ask  | jq -r .answer", PROMPT), ("", FG)] + accumulated
        states.append(L_snapshot)
    return states


def render_frames(states: list[list[tuple[str, str]]]) -> list[Path]:
    paths: list[Path] = []
    for i, lines in enumerate(states):
        p = OUT / f"terminal_state_{i:03d}.png"
        render_frame(lines, p)
        paths.append(p)
    return paths


def build_scene_video(frames: list[Path], mp4: Path) -> None:
    # Target ~90s total. We have ~18 frames; weight them so first frames
    # linger longer (pytest streaming), and the curl-answer beats get a
    # nice "read it" pause.
    n = len(frames)
    # Default per-frame durations (seconds). Tune to land near 90s.
    # We'll bias: first prompt 2s, pytest beats 3s each, smoke beats 3s,
    # curl prompts 4s, answer chunks 6s.
    defaults = [3.0] * n
    # Heuristic: last 4 frames are the answer chunks - give 6s, ending 8s.
    if n >= 4:
        defaults[-4] = 6.0
        defaults[-3] = 6.0
        defaults[-2] = 6.0
        defaults[-1] = 8.0
    # First frame (pytest prompt) and curl prompt: 2s.
    defaults[0] = 2.0
    # Normalize total to ~90s.
    total = sum(defaults)
    target = 80.0
    scale = target / total
    durations = [round(d * scale, 2) for d in defaults]

    concat_file = OUT / "terminal_concat.txt"
    lines: list[str] = []
    for p, dur in zip(frames, durations):
        lines.append(f"file '{p.resolve()}'")
        lines.append(f"duration {dur}")
    # ffmpeg concat demuxer requires the last frame repeated without
    # duration for the final frame to render fully.
    lines.append(f"file '{frames[-1].resolve()}'")
    concat_file.write_text("\n".join(lines) + "\n")

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", "scale=1920:1080,format=yuv420p",
            "-r", "30",
            "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            str(mp4),
        ],
        check=True,
    )


def main() -> None:
    states = build_states()
    frames = render_frames(states)
    print(f"  rendered {len(frames)} terminal frames")
    mp4 = OUT / "scene2_terminal.mp4"
    build_scene_video(frames, mp4)
    print(f"  wrote {mp4.name}")


if __name__ == "__main__":
    main()
