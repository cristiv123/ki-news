#!/usr/bin/env python3
"""Rebuild the ki-news static site from transcript metadata.

Reads every <name>.json / <name>.txt pair from the source transcripts
directory (default: C:\\claude\\youtube-transcripts), copies them into this
repo under data/, and regenerates index.html plus one videos/<id>.html page
per video.

Usage:
    python build_site.py [source_dir]
"""
import json
import html
import shutil
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
VIDEOS_DIR = REPO_DIR / "videos"
DEFAULT_SOURCE = Path(r"C:\claude\youtube-transcripts")

PAGE_TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — ki-news</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header>
  <a class="back" href="../index.html">&larr; toate videoclipurile</a>
</header>
<main>
  <h1>{title}</h1>
  <p class="meta">
    <a class="yt-link" href="{youtube_url}" target="_blank" rel="noopener">▶ Vezi pe YouTube</a>
    <span class="badge">{language}</span>
    <span class="badge">{subtitle_type_label}</span>
  </p>
  <img class="thumb" src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="">
  <pre class="transcript">{transcript}</pre>
</main>
</body>
</html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ki-news — transcripturi video</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>ki-news</h1>
  <p class="subtitle">Transcripturi curate ale unor videoclipuri YouTube.</p>
</header>
<main>
  <div class="grid">
{cards}
  </div>
</main>
</body>
</html>
"""

CARD_TEMPLATE = """    <a class="card" href="videos/{video_id}.html">
      <img src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="">
      <div class="card-body">
        <h2>{title}</h2>
        <p class="meta"><span class="badge">{language}</span><span class="badge">{subtitle_type_label}</span></p>
      </div>
    </a>
"""


def load_entries(source_dir: Path):
    entries = []
    for json_path in sorted(source_dir.glob("*.json")):
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        txt_path = json_path.parent / meta["txt_file"]
        if not txt_path.exists():
            print(f"SKIP {json_path.name}: txt file not found ({txt_path})")
            continue
        with open(txt_path, "r", encoding="utf-8") as f:
            transcript = f.read()
        meta["_transcript"] = transcript
        entries.append(meta)
    return entries


def build(source_dir: Path):
    entries = load_entries(source_dir)
    if not entries:
        print(f"No video metadata found in {source_dir}")
        return

    DATA_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)

    cards = []
    for meta in entries:
        video_id = meta["video_id"]
        title = html.escape(meta["title"])
        language = html.escape(meta.get("language", "?"))
        subtitle_type_label = (
            "subtitrare manuală" if meta.get("subtitle_type") == "manual" else "subtitrare automată"
        )
        youtube_url = html.escape(meta["youtube_url"])
        transcript = html.escape(meta["_transcript"])

        page = PAGE_TEMPLATE.format(
            lang=language,
            title=title,
            youtube_url=youtube_url,
            language=language,
            subtitle_type_label=subtitle_type_label,
            video_id=html.escape(video_id),
            transcript=transcript,
        )
        (VIDEOS_DIR / f"{video_id}.html").write_text(page, encoding="utf-8")

        shutil.copy2(
            source_dir / meta["txt_file"],
            DATA_DIR / meta["txt_file"],
        )
        meta_public = {k: v for k, v in meta.items() if k != "_transcript"}
        (DATA_DIR / f"{video_id}.json").write_text(
            json.dumps(meta_public, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        cards.append(
            CARD_TEMPLATE.format(
                video_id=html.escape(video_id),
                title=title,
                language=language,
                subtitle_type_label=subtitle_type_label,
            )
        )

    index_html = INDEX_TEMPLATE.format(cards="".join(cards))
    (REPO_DIR / "index.html").write_text(index_html, encoding="utf-8")

    print(f"Built {len(entries)} video page(s) into {REPO_DIR}")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    build(src)
