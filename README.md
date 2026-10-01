# LionRoar360 Instagram video automation

Produces a high-quality, narrated explainer Reel every 2 days and publishes it to the
**@lionroar360** Instagram account. The videos teach business owners why marketing, a
high-quality website, being found online and fast follow-up grow a business, and how
Lion Roar 360 helps.

| Part | Where |
|---|---|
| Brand voice, services, tone, CTAs (from lionroar360.com) | `brand/brand-brief.md` |
| Locked production settings (style, voice, Instagram account, cadence) | `brand/channel-dna.json` |
| 30 finished scripts and captions across six content pillars | `content/topics.json`, `content/hashtags.json` |
| Step-by-step procedure the scheduled session follows | `pipeline/RUNBOOK.md` |
| What has been posted | `pipeline/state.json` |
| Helpers: pick next topic, record a post, validate everything | `scripts/` |

## How it runs

A Claude Code **Routine** fires every two days at 10:52 AM Eastern, opens a fresh session with
the Higgsfield and Zapier connectors, and follows `pipeline/RUNBOOK.md`:

1. `scripts/next_topic.py` picks the next unposted topic, rotating pillars.
2. Higgsfield's `faceless-video` workflow renders a 60-second 9:16 animated explainer
   (Paper Diorama style, Fraser narrator, burned captions) from the authored script.
3. Zapier publishes the hosted MP4 to Instagram as a Reel with the caption.
4. `scripts/record_post.py` logs the post and the session commits and pushes `state.json`.

## Editing content

- Add or edit topics in `content/topics.json` (six blocks of 14 to 26 words each, one CTA).
- Run `python3 scripts/validate.py` before committing. It rejects guarantee-style claims.
- Change the look or voice in `brand/channel-dna.json`; the next run picks it up.
- To force a specific topic for the next run: `python3 scripts/next_topic.py --id web-01`.

## Pausing

Disable the Routine in the Claude app (Routines list) or ask Claude to disable it.
Nothing posts while it is off.
