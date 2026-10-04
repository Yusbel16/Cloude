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
   phones, websites on screens, a lion motif is welcome but not required. The final scene
   illustrates the action the script asks the viewer to take, never the agency: no logo
   reveal, no phone number, no web address on screen (owner decision: teach, do not advertise).
4. Deliver per Phase 9: `media_upload` → PUT → `media_confirm`. Keep the **confirmed hosted
   video URL**. Run the FINAL QC CHECKLIST. If the run fails unrecoverably, record it:
   `python3 scripts/record_post.py failed --id <topic_id> --reason "<phase and cause>"`, commit,
   push, and report. Never publish a partial video.
5. If the workflow printed a CHANNEL DNA object with `style_key_urls` or `assets` and the
   DNA file still has them empty, copy those values into `brand/channel-dna.json`.

## 3. Publish to Instagram (Zapier raw requests to the Instagram Graph API)

Do NOT use Zapier's packaged `publish_video` action: it times out while Instagram transcodes a 60-second
2K file ("Video is still processing") and leaves nothing published. Use the three-step Graph API flow
through Zapier's raw-request actions on the Instagram for Business app (authentication is automatic):

1. Create the Reel container (write action `_zap_raw_request`, tool `instagram_for_business_make_api_mutating_request`):
   ```
   POST https://graph.facebook.com/v21.0/17841409674763599/media
   querystring: media_type=REELS, share_to_feed=true, video_url=<confirmed hosted mp4 url>, caption=<caption>
   fail_on_errors=true  -> returns {"id": "<container id>"}
   ```
2. Poll until FINISHED (read action, tool `instagram_for_business_make_api_get_request`), about every 30 s,
   up to 10 minutes:
   ```
   GET https://graph.facebook.com/v21.0/<container id>?fields=status_code,status
   ```
   `IN_PROGRESS` means wait; `ERROR` means stop, record a failure and report the `status` text.
3. Publish:
   ```
   POST https://graph.facebook.com/v21.0/17841409674763599/media_publish
   querystring: creation_id=<container id>   -> returns {"id": "<media id>"}
   ```
4. Read the permalink for the log:
   ```
   GET https://graph.facebook.com/v21.0/<media id>?fields=permalink,timestamp
   ```
Never create a second container for the same video unless the first one reports `ERROR`; a
container that is still processing will finish on its own.

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
- The assembler's own speech window is a hard 7.8 to 9.5 s per take (no soft band); a 7.7 s take fails
  assembly, so aim for 8.0 to 9.0 s when picking takes.
- `finish_video.sh` writes the voice files as `voiceNN.wav` but its sidecar names them `v_00N.wav`;
  symlink one name to the other before `audio_to_captions.py` or the caption step fails.
- Use `audio_to_captions.py --model medium` for the caption clock; the small model mis-hears this voice.
- Higgsfield recommended the "IN THE DARK" preset instead of submitting the clips; resubmit the same
  requests with `declined_preset_id` from the error.
- Re-record the voice BEFORE generating video. Clips cost far more than takes.

## Lessons learned on the second run (2026-10-04, tip-01)

- The caption scripts now live in `${HF_WORKFLOWS}/video-montage/scripts/` (`audio_to_captions.py`,
  `burn_caps_clean.sh`, `fetch_fonts.sh`); the old `subtitles/` folder no longer exists in the sandbox.
- When a spoken line contains numbers ("two hundred dollars"), Whisper writes digits ("$200") and the
  caption aligner's similarity gate fails at the default 0.75 even though the take is word-perfect.
  Pass `--minimum-similarity 0.6` for that run; the caption text still comes from the authored script.
- The sandbox is recycled whenever the Higgsfield connector reconnects, which kills background jobs
  mid-chain. Checkpoint after assembly: tar `final_clean.mp4`, its sidecar, poster, `work/voices` and the
  manifest, PUT it to a `media_upload` slot (`.tar`), `media_confirm` it with type `file`, and resume
  the caption and burn stage from that tar if the chain dies. Keep each stage under ~3 minutes.
- Never run `ffmpeg` inside a `while read` loop without `-nostdin`: it eats the next line of the list
  (the second voice URL lost its first character). Use `for u in $(cat voices.txt)` instead.
- A presigned upload URL can start returning 400 after a few hours; request a fresh `media_upload`
  slot and PUT again rather than retrying the old one.
- Densify to 23 words with longer words when a take is RUSHED; the engine's pace is bimodal, so one
  re-roll of the same text often lands in the window (block 1 went 7.09 s to 8.13 s).

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
