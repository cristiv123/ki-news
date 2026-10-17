#!/usr/bin/env python3
"""Rebuild the ki-news static site from the bilingual digest source.

Reads every <id>.meta.json (+ matching <id>.sentences.json) from the source
directory (default: C:\\claude\\ki-news-source), copies them into this repo
under data/, and regenerates index.html (grouped by topic) plus one
videos/<id>.html page per video with a German/Romanian sentence table.

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
DEFAULT_SOURCE = Path(r"C:\claude\ki-news-source")

TOPIC_ORDER = ["claude-ai", "ki-zukunft"]
TOPIC_LABELS = {
    "claude-ai": "Claude AI",
    "ki-zukunft": "KI Zukunft",
}

PAGE_TEMPLATE = """<!doctype html>
<html lang="ro">
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
  <p class="topic-tag">{topic_label}</p>
  <h1>{title}</h1>
  <p class="meta">
    <a class="yt-link" href="{youtube_url}" target="_blank" rel="noopener">▶ Vezi pe YouTube</a>
    <span class="badge">{language_label}</span>
    <span class="badge">{subtitle_type_label}</span>
    <span class="badge">{sentence_count} propoziții</span>
  </p>
  <img class="thumb" src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="">
  <p style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border);">
    <a href="../{docx_filename}" style="color: var(--accent); text-decoration: none; font-weight: 600;">⬇ Descarcă transcript Word (DE/RO)</a>
  </p>
  <table class="sentence-table">
    <thead><tr><th>Deutsch</th><th>Română</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</main>
</body>
</html>
"""

ROW_TEMPLATE = """      <tr><td class="de">{de}</td><td class="ro">{ro}</td></tr>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ki-news — învață germană din știri AI</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>ki-news</h1>
  <p class="subtitle">Transcripturi bilingve (DE/RO), propoziție cu propoziție, din podcasturi și video-uri germane despre Claude AI și viitorul inteligenței artificiale.</p>
</header>
<main>
{sections}
</main>
</body>
</html>
"""

SECTION_TEMPLATE = """  <section>
    <h2>{topic_label}</h2>
    <div class="grid">
{cards}
    </div>
  </section>
"""

CARD_TEMPLATE = """      <a class="card" href="videos/{video_id}.html">
        <img src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="">
        <div class="card-body">
          <h3>{title}</h3>
          <p class="meta"><span class="badge">{language_label}</span><span class="badge">{subtitle_type_label}</span></p>
        </div>
      </a>
"""


def load_entries(source_dir: Path):
    entries = []
    for meta_path in sorted(source_dir.glob("*.meta.json")):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        sentences_path = source_dir / meta["sentences_file"]
        if not sentences_path.exists():
            print(f"SKIP {meta_path.name}: sentences file not found ({sentences_path})")
            continue
        with open(sentences_path, "r", encoding="utf-8") as f:
            sentences = json.load(f)
        meta["_sentences"] = sentences
        entries.append(meta)
    entries.sort(key=lambda m: m.get("upload_date", ""), reverse=True)
    return entries


def language_label(meta):
    base = meta.get("source_language", "?").upper()
    if meta.get("translated_to_german"):
        return f"{base} → DE (tradus)"
    return base


def build(source_dir: Path):
    entries = load_entries(source_dir)
    if not entries:
        print(f"No video metadata found in {source_dir}")
        return

    DATA_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)

    by_topic = {t: [] for t in TOPIC_ORDER}

    for meta in entries:
        video_id = meta["video_id"]
        title = html.escape(meta["title"])
        docx_filename = html.escape(f"{title.replace(' — ki-news', '')}.docx")
        topic = meta.get("topic", "other")
        topic_label = html.escape(TOPIC_LABELS.get(topic, topic))
        lang_label = html.escape(language_label(meta))
        subtitle_type_label = (
            "subtitrare manuală" if meta.get("subtitle_type") == "manual" else "subtitrare automată"
        )
        youtube_url = html.escape(meta["youtube_url"])
        sentences = meta["_sentences"]

        rows = "".join(
            ROW_TEMPLATE.format(de=html.escape(s["de"]), ro=html.escape(s["ro"]))
            for s in sentences
        )

        page = PAGE_TEMPLATE.format(
            title=title,
            topic_label=topic_label,
            youtube_url=youtube_url,
            language_label=lang_label,
            subtitle_type_label=subtitle_type_label,
            sentence_count=len(sentences),
            video_id=html.escape(video_id),
            docx_filename=docx_filename,
            rows=rows,
        )
        (VIDEOS_DIR / f"{video_id}.html").write_text(page, encoding="utf-8")

        shutil.copy2(source_dir / meta["sentences_file"], DATA_DIR / meta["sentences_file"])
        meta_public = {k: v for k, v in meta.items() if k != "_sentences"}
        (DATA_DIR / f"{video_id}.meta.json").write_text(
            json.dumps(meta_public, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        card = CARD_TEMPLATE.format(
            video_id=html.escape(video_id),
            title=title,
            language_label=lang_label,
            subtitle_type_label=subtitle_type_label,
        )
        by_topic.setdefault(topic, []).append(card)

    sections = []
    for topic in TOPIC_ORDER:
        cards = by_topic.get(topic, [])
        if not cards:
            continue
        sections.append(
            SECTION_TEMPLATE.format(
                topic_label=html.escape(TOPIC_LABELS.get(topic, topic)),
                cards="".join(cards),
            )
        )
    # any topics not in TOPIC_ORDER
    for topic, cards in by_topic.items():
        if topic in TOPIC_ORDER or not cards:
            continue
        sections.append(
            SECTION_TEMPLATE.format(topic_label=html.escape(topic), cards="".join(cards))
        )

    index_html = INDEX_TEMPLATE.format(sections="".join(sections))
    (REPO_DIR / "index.html").write_text(index_html, encoding="utf-8")

    print(f"Built {len(entries)} video page(s) into {REPO_DIR}")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    build(src)
