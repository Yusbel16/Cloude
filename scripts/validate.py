#!/usr/bin/env python3
"""Validate content/topics.json, brand/channel-dna.json and pipeline/state.json.

The line rules mirror Higgsfield's faceless-video validate_motion_script.py so a
script that passes here also passes the production gate:
  * 6 blocks, 20-23 words each (word = letters/apostrophes/hyphens run);
    blocks listed in a topic's measured_short_blocks may go down to 17 words,
    which is the production validator's --duration-retry-blocks floor after a
    take measured over 9.5 s
  * at most 2 sentences per block, no digits, no conversational filler
  * no content word repeated within 6 words
  * block 1 opens on a sentence of at most 8 words
  * no verbatim 5-word phrase shared by two blocks of the same topic
  * narration teaches only: no agency pitch, URL or call-back line in the spoken
    script outside the how-we-help pillar (already-posted topics are exempt)
Exit 1 on any problem so CI and the runbook can gate on it."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORD = re.compile(r"[^\W_]+(?:[-'’][^\W_]+)*", re.UNICODE)
SENT = re.compile(r"[.!?]+(?:\s|$)")
FILLER = re.compile(r"\b(?:you\s+know|y'?know|i\s+mean|sort\s+of|kinda|basically|um+|uh+|erm)\b", re.I)
STOP = set("a an and are as at be but by can did do does for from had has have he her here his how i if in into is it its just me my no not of on one or our out over she so than that the their them then there these they this those to up was we were what when why will with would you your".split())
NUMBERS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion trillion first second third fourth fifth sixth seventh eighth ninth tenth half quarter dozen".split())
BANNED = re.compile(r"\b(guarantee|guaranteed|number one|double your|triple your)\b", re.I)
# Narration teaches; the pitch lives in the caption. Only the how-we-help pillar may speak it.
PITCH = re.compile(r"lion\s+roar|dot\s+com|request\s+a\s+call|call\s+back|lionroar360", re.I)
PILLARS = {"growth-tips", "why-marketing", "website", "be-found", "follow-up", "social-content", "how-we-help"}
WMIN, WMAX, MAX_CAPTION, HOOK_WORDS, SHARED = 20, 23, 2200, 8, 5


def words(s):
    return [w.casefold() for w in WORD.findall(s)]


def shared_run(a, b):
    best = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def check_topic(t, hashtags, errors, posted=()):
    tid = t["id"]
    if t["pillar"] not in PILLARS:
        errors.append(f"{tid}: unknown pillar {t['pillar']}")
    script = t["script"]
    if len(script) != 6:
        errors.append(f"{tid}: script must have 6 blocks, has {len(script)}")
    toks = []
    short_ok = set(t.get("measured_short_blocks", []))
    for i, line in enumerate(script, 1):
        w = words(line)
        toks.append(w)
        wmin = 17 if i in short_ok else WMIN
        if not wmin <= len(w) <= WMAX:
            errors.append(f"{tid} block {i}: {len(w)} words (want {wmin}-{WMAX})")
        n_sent = max(1, len([p for p in SENT.split(line.strip()) if p.strip()]))
        if n_sent > 2:
            errors.append(f"{tid} block {i}: {n_sent} sentences (max 2)")
        if re.search(r"\d", line):
            errors.append(f"{tid} block {i}: digits are not allowed, write numbers as words")
        if FILLER.search(line):
            errors.append(f"{tid} block {i}: conversational filler")
        if BANNED.search(line):
            errors.append(f"{tid} block {i}: banned claim wording")
        if t["pillar"] != "how-we-help" and tid not in posted and PITCH.search(line):
            errors.append(f"{tid} block {i}: agency pitch in narration (teach only; the caption carries the CTA)")
        for k, tok in enumerate(w):
            if tok in STOP or tok in NUMBERS or len(tok) < 3:
                continue
            if tok in w[k + 1:k + 6]:
                errors.append(f"{tid} block {i}: '{tok}' repeated within 6 words")
                break
    if script:
        first = [p for p in SENT.split(script[0].strip()) if p.strip()]
        if first and len(words(first[0])) > HOOK_WORDS:
            errors.append(f"{tid} block 1: cold open is {len(words(first[0]))} words, max {HOOK_WORDS}")
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            if shared_run(toks[i], toks[j]) >= SHARED:
                errors.append(f"{tid}: blocks {i+1} and {j+1} share a {SHARED}+ word phrase")
    full_caption = t["caption"] + "\n\n" + " ".join(hashtags)
    if len(full_caption) > MAX_CAPTION:
        errors.append(f"{tid}: caption {len(full_caption)} chars > {MAX_CAPTION}")
    if "lionroar360.com" not in t["caption"] and "(786) 550-2777" not in t["caption"]:
        errors.append(f"{tid}: caption has no call to action")
    if BANNED.search(t["caption"]):
        errors.append(f"{tid}: banned claim wording in caption")


def main():
    errors = []
    topics = json.loads((ROOT / "content/topics.json").read_text(encoding="utf-8"))["topics"]
    hashtags = json.loads((ROOT / "content/hashtags.json").read_text(encoding="utf-8"))["default"]
    state = json.loads((ROOT / "pipeline/state.json").read_text(encoding="utf-8"))
    posted_ids = {p["topic_id"] for p in state.get("posted", [])}
    ids = set()
    for t in topics:
        if t["id"] in ids:
            errors.append(f"{t['id']}: duplicate id")
        ids.add(t["id"])
        check_topic(t, hashtags, errors, posted_ids)
    dna = json.loads((ROOT / "brand/channel-dna.json").read_text(encoding="utf-8"))
    for key in ("instagramPageId", "zapier_action"):
        if not dna["instagram"].get(key):
            errors.append(f"channel-dna.instagram.{key} missing")
    if dna["video"]["aspect"] != "9:16":
        errors.append("channel-dna.video.aspect must be 9:16 for Reels")
    if not dna["video"]["voice"].get("voice_id") or not dna["video"]["style"].get("preset_id"):
        errors.append("channel-dna.video voice_id / style.preset_id missing")
    for p in state.get("posted", []):
        if p["topic_id"] not in ids:
            errors.append(f"state.posted references unknown topic {p['topic_id']}")
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print(f"ok: {len(topics)} topics, {len(state.get('posted', []))} posted")


if __name__ == "__main__":
    main()
