#!/usr/bin/env python3
"""Validate content/topics.json, brand/channel-dna.json and pipeline/state.json.
Exit 1 on any problem so CI and the runbook can gate on it."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIN_WORDS, MAX_WORDS = 14, 26
MAX_CAPTION = 2200
PILLARS = {"why-marketing", "website", "be-found", "follow-up", "social-content", "how-we-help"}
BANNED = re.compile(r"\b(guarantee|guaranteed|#1|number one|double your|triple your|\d+%|\d+x)\b", re.I)

errors = []
topics = json.loads((ROOT / "content/topics.json").read_text(encoding="utf-8"))["topics"]
hashtags = json.loads((ROOT / "content/hashtags.json").read_text(encoding="utf-8"))["default"]
ids = set()
for t in topics:
    if t["id"] in ids:
        errors.append(f"{t['id']}: duplicate id")
    ids.add(t["id"])
    if t["pillar"] not in PILLARS:
        errors.append(f"{t['id']}: unknown pillar {t['pillar']}")
    if len(t["script"]) != 6:
        errors.append(f"{t['id']}: script must have 6 blocks, has {len(t['script'])}")
    for i, line in enumerate(t["script"], 1):
        n = len(line.split())
        if not MIN_WORDS <= n <= MAX_WORDS:
            errors.append(f"{t['id']} block {i}: {n} words (want {MIN_WORDS}-{MAX_WORDS})")
        if BANNED.search(line):
            errors.append(f"{t['id']} block {i}: banned claim wording: {line[:60]}")
    full_caption = t["caption"] + "\n\n" + " ".join(hashtags)
    if len(full_caption) > MAX_CAPTION:
        errors.append(f"{t['id']}: caption {len(full_caption)} chars > {MAX_CAPTION}")
    if "lionroar360.com" not in t["caption"] and "(786) 550-2777" not in t["caption"]:
        errors.append(f"{t['id']}: caption has no call to action")
    if BANNED.search(t["caption"]):
        errors.append(f"{t['id']}: banned claim wording in caption")

dna = json.loads((ROOT / "brand/channel-dna.json").read_text(encoding="utf-8"))
for key in ("instagramPageId", "zapier_action"):
    if not dna["instagram"].get(key):
        errors.append(f"channel-dna.instagram.{key} missing")
if dna["video"]["aspect"] != "9:16":
    errors.append("channel-dna.video.aspect must be 9:16 for Reels")
if not dna["video"]["voice"].get("voice_id"):
    errors.append("channel-dna.video.voice.voice_id missing")

state = json.loads((ROOT / "pipeline/state.json").read_text(encoding="utf-8"))
for p in state.get("posted", []):
    if p["topic_id"] not in ids:
        errors.append(f"state.posted references unknown topic {p['topic_id']}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"ok: {len(topics)} topics, {len(state.get('posted', []))} posted")
