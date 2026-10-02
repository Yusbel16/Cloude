#!/usr/bin/env python3
"""Record a production step in pipeline/state.json.

  python3 scripts/record_post.py start  --id web-01
  python3 scripts/record_post.py ready  --id web-01 --video-url https://...   # rendered, not yet published
  python3 scripts/record_post.py posted --id web-01 --video-url https://... [--post-id 1784...] [--permalink https://instagram.com/p/...]
  python3 scripts/record_post.py failed --id web-01 --reason "phase 4 retry ladder exhausted"
"""
import argparse
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "pipeline" / "state.json"
TOPICS = ROOT / "content" / "topics.json"


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("event", choices=["start", "ready", "posted", "failed"])
    ap.add_argument("--id", required=True)
    ap.add_argument("--video-url")
    ap.add_argument("--post-id")
    ap.add_argument("--permalink")
    ap.add_argument("--reason")
    a = ap.parse_args()

    state = json.loads(STATE.read_text(encoding="utf-8"))
    topics = {t["id"]: t for t in json.loads(TOPICS.read_text(encoding="utf-8"))["topics"]}
    if a.id not in topics:
        raise SystemExit(f"unknown topic id {a.id}")
    pillar = topics[a.id]["pillar"]
    state["in_progress"] = [p for p in state.get("in_progress", []) if p["topic_id"] != a.id]

    if a.event == "start":
        state["in_progress"].append({"topic_id": a.id, "pillar": pillar, "started_at": now()})
    elif a.event == "ready":
        if not a.video_url:
            raise SystemExit("--video-url is required for ready")
        state["in_progress"].append({"topic_id": a.id, "pillar": pillar, "started_at": now(),
                                     "status": "rendered, awaiting publish", "video_url": a.video_url})
    elif a.event == "posted":
        if not a.video_url:
            raise SystemExit("--video-url is required for posted")
        state.setdefault("posted", []).append({
            "topic_id": a.id, "pillar": pillar, "posted_at": now(),
            "video_url": a.video_url, "post_id": a.post_id, "permalink": a.permalink,
        })
    else:
        state.setdefault("failures", []).append({"topic_id": a.id, "pillar": pillar, "failed_at": now(), "reason": a.reason or ""})

    state["updated_at"] = now()
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"recorded {a.event} for {a.id}")


if __name__ == "__main__":
    main()
