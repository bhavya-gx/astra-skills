# Editable project format

A project is JSON. Start from a supplied template with:

```sh
.venv/bin/python -m reelkit new --template founder-story --source input.mov --out my-project.json
.venv/bin/python -m reelkit render my-project.json --draft --out my-preview
.venv/bin/python -m reelkit render my-project.json --out my-master
```

On Windows use `.venv\Scripts\python.exe`. Relative media paths resolve against the project JSON's folder when rendering from the CLI.

| Field | Meaning |
| --- | --- |
| `template` | `founder-story`, `product-breakdown`, or `playful-explainer` |
| `source` | Local source-video path |
| `hook`, `subhead`, `beats`, `cta` | Opening, three `{title, text}` cards, and ending |
| `title_y`, `caption_y` | Fractions of frame height measured from the top; do not use pixels |
| `accent` | Six-digit hex colour |
| `warmth` | 0–1 shared warm creative grade |
| `tint` | −1 to 1 source correction, green to magenta |
| `tighten_pauses` | Conservative amplitude-based pause removal |
| `minimum_pause` | Minimum silence length in seconds, default 0.50 |
| `threshold_db` | Silence threshold, default −38 dBFS; lower it for quiet voices |
| `noise_reduction`, `sound_effects` | Toggle the audio treatments |
| `auto_captions` | Local faster-whisper transcription; initial model download required |
| `captions_srt` | SRT timed against the ORIGINAL source; overrides transcription |
| `keep_ranges` | Optional ordered source-time intervals, e.g. `[[0,3.2],[4.1,10]]`; overrides automatic pause removal |
| `stage_starts` | Optional five OUTPUT-time starts for hook, beats 1–3, ending; first must be 0, e.g. `[0,2.5,8,14,21]` |
| `portrait_blur` | Real MODNet portrait matte and background blur; slower than a normal render |
| `insert` | Optional full-frame visual, with `{ "source": "demo.mp4", "start": 5, "end": 8 }`; times refer to edited OUTPUT |

The insert is silent, contains the full image/video within the frame, and loops if shorter than its assigned interval. It appears underneath the titles and captions. If an image is too short to understand, extend its interval. Use assets you can distribute and record their source/license.

Each render saves `project.json`, `edit-decisions.json`, `result.json`, `validation.json`, a video, and `captions.srt` when there are captions. Review notes left with `python -m reelkit review` save beside the video as `<video>.review.json`: a list of `{start, end, note, words, done, reply}` in edited OUTPUT time. The `work/` subfolder contains graph files, commands, analysis audio, the assembly, and the transparent overlay. Cuts are quantized to 30 fps. Existing exported videos are renamed with a `previous-` prefix before a successful replacement.

The render stages are source inspection → transcript/SRT → retained intervals → frame-exact video selection and audio joins → original-aspect composition and colour → optional portrait blur/insert → graphics and sound → full decode validation → export promotion.

This format intentionally covers the three starter styles. A complex custom motion design can use an additional renderer; avoid stretching these fields into a universal editing language.

Automatic captions preserve word timestamps so deleted source words are removed from the caption text. An imported SRT supplies phrase timing only: if you cut through a captioned phrase, review and correct that cue manually.
