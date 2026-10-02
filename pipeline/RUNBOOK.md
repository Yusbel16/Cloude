# RUNBOOK — produce and publish one LionRoar360 Reel

This file is the exact procedure the scheduled Claude session follows every 2 days.
It is written to run **hands-off**: nothing in it waits for a human answer.
Tools used: Higgsfield MCP (video), Zapier MCP (Instagram publish), git (state).

## 0. Prepare the checkout

```
git fetch origin main claude/instagram-video-automation-dof2uv 2>/dev/null
# Work on main if this runbook already lives there, otherwise on the automation branch.
if git cat-file -e origin/main:pipeline/RUNBOOK.md 2>/dev/null; then git checkout -B main origin/main; \
else git checkout -B claude/instagram-video-automation-dof2uv origin/claude/instagram-video-automation-dof2uv; fi
python3 scripts/validate.py
```
If validate fails, stop and report; do not generate anything.

## 1. Pick the topic and build the brief

```
python3 scripts/next_topic.py > /tmp/brief.json && cat /tmp/brief.json
python3 scripts/record_post.py start --id <topic_id>
```
The brief carries: the six narration blocks (authored, verbatim, do not rewrite), the full
caption, and the locked channel DNA from `brand/channel-dna.json`.

## 2. Generate the video (Higgsfield `faceless-video` workflow)

1. `get_workflow_instructions({ workflow: "faceless-video" })` and follow its phases 0 → 9.
2. Every intake parameter is already decided; state each as a plain statement and do not ask:
   - Channel type: **Explainer**. Motion mode: **Animated**.
   - Style: the `video.style.name` from the DNA (currently **Paper Diorama**,
     preset id `83d276f6-e3aa-49b8-82f2-1a0bb7d0a370`). Resolve it with
     `resolve_explainer_preset` to get the style reference `media_id`.
   - Duration **1 minute** (6 blocks × 10 s), aspect **9:16**, subtitles **yes**, thumbnail **no**.
   - Topic: **"My topic", pasted script** = the six `script_blocks` from the brief, one block per
     line, title = brief `title`. Narrate the authored wording; if the topic carries
     `measured_short_blocks`, pass them as `--duration-retry-blocks` to the validator.
   - Hands-off concurrency: after SCRIPT LOCK submit the six narration takes AND the six clips before
     waiting on either. Measure takes with `measure_narration_takes.py`; rewrite only failing lines.
   - Voice: `video.voice` from the DNA (currently **Fraser**,
     `voice_id 6705e465-7b52-5915-a1d8-b1222885e01d`, `voice_type preset`). Skip the picker.
   - If the DNA carries `style_key_urls` / `assets`, hand the whole `video` object to the
     workflow as CHANNEL DNA so it reuses the style key and skips Phase 0 and 1.
3. Brand guardrails for every scene prompt: use `video.style.formula` from the DNA byte-identical in
   every image and clip prompt, with its `palette_lock` (website palette: ink black, off-white paper,
   one soft violet accent, no sepia or gold). Premium editorial feel, no faces of real people, no competitor logos, no text
   claims that are not in the script. Scenes illustrate small-business life: storefronts,
   phones, websites on screens, a lion motif is welcome but not required.
4. Deliver per Phase 9: `media_upload` → PUT → `media_confirm`. Keep the **confirmed hosted
   video URL**. Run the FINAL QC CHECKLIST. If the run fails unrecoverably, record it:
   `python3 scripts/record_post.py failed --id <topic_id> --reason "<phase and cause>"`, commit,
   push, and report. Never publish a partial video.
5. If the workflow printed a CHANNEL DNA object with `style_key_urls` or `assets` and the
   DNA file still has them empty, copy those values into `brand/channel-dna.json`.

## 3. Publish to Instagram (Zapier)

```
execute_zapier_write_action({
  selected_api: "InstagramBusinessCLIAPI",
  action: "publish_video",
  tool_name: "instagram_for_business_publish_video",
  params: {
    instagramPageId: "17841409674763599",   // LionRoar360
    video: "<confirmed hosted mp4 url>",
    caption: "<caption from the brief>"
  }
})
```
Read the response. A success carries a media/post id (and sometimes a permalink).
If Zapier returns an error, retry once after 60 seconds (Instagram sometimes needs the
file to finish processing). If it fails again, record a failure and report; do not post twice.

## 4. Record and push

```
python3 scripts/record_post.py posted --id <topic_id> --video-url "<url>" --post-id "<id>" --permalink "<permalink or omit>"
python3 scripts/validate.py
git add -A && git commit -m "Post <topic_id>: <title>" && git push -u origin HEAD
```

## 5. Report (one short message)

Topic id and title, the Instagram post id or permalink, the hosted video URL, credits used if
shown, and anything that needed a retry. If nothing was published, say exactly which step
failed and why.

## Lessons learned on the first run (2026-10-02)

- **Do not wrap narration lines in the `[ delivery ... ] [00:00-00:09]` bracket with this voice.** The
  ElevenLabs engine behind `text2speech_v2` spoke fragments of the bracket out loud ("steady knowing
  tone", "reassuring clarifying") and mangled the first words of five of six takes. Send the authored
  line as plain text. After every take, transcribe it with faster-whisper in the sandbox and compare it
  to the script before measuring; a take whose opening words differ is regenerated, never shipped.
- Plain-text takes read faster (about 2.9 to 3.0 words per second). When the measurement script says
  RUSHED, re-roll the same text once or swap in longer words; the duration is bimodal so one re-roll
  usually lands inside the window.
- `finish_video.sh` writes the voice files as `voiceNN.wav` but its sidecar names them `v_00N.wav`;
  symlink one name to the other before `audio_to_captions.py` or the caption step fails.
- Use `audio_to_captions.py --model medium` for the caption clock; the small model mis-hears this voice.
- Higgsfield recommended the "IN THE DARK" preset instead of submitting the clips; resubmit the same
  requests with `declined_preset_id` from the error.
- Re-record the voice BEFORE generating video. Clips cost far more than takes.

## Rules that never change

- One Reel per run. Never run the loop twice in one session.
- Script lines change only through the narrator measurement loop (a take outside 7.8-9.5 s or with a pause
  is REWRITTEN, never time-stretched). When a line is rewritten, write the final wording back into
  `content/topics.json` in the same commit and list blocks that went below 20 words in that topic's
  `measured_short_blocks` so `scripts/validate.py` and the production validator
  (`--duration-retry-blocks`) agree. Captions must show exactly what was spoken.
- No invented statistics, guarantees or client results. The validator blocks the common words.
- Keep the two-day cadence; if a run fails, the next scheduled run picks the same topic again
  because it was never marked posted.
