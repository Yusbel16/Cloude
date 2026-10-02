#!/usr/bin/env python3
"""Pick the next topic to produce and print a production brief as JSON.

Selection rules:
  1. Skip topics already in pipeline/state.json "posted" or "in_progress".
  2. Rotate pillars so two consecutive posts never share a pillar when avoidable.
  3. Within the eligible set keep calendar order.
Usage:  python3 scripts/next_topic.py            # prints brief JSON
        python3 scripts/next_topic.py --id web-01 # force a topic
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOPICS = ROOT / "content" / "topics.json"
STATE = ROOT / "pipeline" / "state.json"
DNA = ROOT / "brand" / "channel-dna.json"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pick(topics, state, forced_id=None):
    used = {p["topic_id"] for p in state.get("posted", [])}
    used |= {p["topic_id"] for p in state.get("in_progress", [])}
    eligible = [t for t in topics if t["id"] not in used]
    if forced_id:
        match = [t for t in topics if t["id"] == forced_id]
        if not match:
            sys.exit(f"unknown topic id {forced_id}")
        return match[0]
    if not eligible:
        # Calendar exhausted: start a second lap, oldest post first.
        posted_order = [p["topic_id"] for p in state.get("posted", [])]
        eligible = sorted(topics, key=lambda t: posted_order.index(t["id"]) if t["id"] in posted_order else -1)
    last_pillar = state["posted"][-1]["pillar"] if state.get("posted") else None
    for t in eligible:
        if t["pillar"] != last_pillar:
            return t
    return eligible[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", dest="forced_id")
    args = ap.parse_args()
    topics = load(TOPICS)["topics"]
    state = load(STATE)
    dna = load(DNA)
    topic = pick(topics, state, args.forced_id)
    brief = {
        "topic_id": topic["id"],
        "pillar": topic["pillar"],
        "title": topic["title"],
        "script_blocks": topic["script"],
        "narration_text": "\n".join(topic["script"]),
        "word_count": sum(len(l.split()) for l in topic["script"]),
        "caption": topic["caption"] + "\n\n" + " ".join(load(ROOT / "content" / "hashtags.json")["default"]),
        "video": dna["video"],
        "instagram": dna["instagram"],
    }
    print(json.dumps(brief, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
