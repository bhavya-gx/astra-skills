---
name: reel-edit
description: Edit talking-head reels with this repository's Founder Story, Product Breakdown, and Playful Explainer templates, including source-time cuts, caption retiming, colour matching, and reviewed exports.
---

Use the repository root containing `bootstrap.py`. Read `docs/project-format.md` for the executable configuration and `docs/walkthrough.md` when planning an edit. The toolkit is self-contained; no private skills or prior chat history are required.

Inspect actual source properties before planning. Use a transcript to distinguish false starts and duplicate takes from intentional repetition. Silence detection alone does not justify removing quiet speech. Keep raw files unchanged.

Create a project from the chosen template with `python -m reelkit new --template NAME --source FILE --out PROJECT.json`, using the repository virtual-environment Python. Fill the titles from the spoken content; do not invent subtitle timing from a script. Transcription is local and may need an initial public model download.

`keep_ranges` uses ORIGINAL source time. `stage_starts` and insert placement use EDITED output time. Recompute output times whenever cuts change. Captions are mapped through the edit decision list by the renderer. The five visual stages are hook, three beats, and ending; do not claim their default equal spacing follows the speech.

Preserve source geometry. Prefer moving graphics or changing their scale to stretching or repositioning the speaker. Apply per-source tint correction before the common warm look; matching settings alone does not ensure matching skin tones. The included icon illustrations are not Apple emoji assets.

Run `python -m reelkit render PROJECT.json --draft --out DIRECTORY`. Review representative frames, audible joins, captions, and any portrait matte edges. A decode pass confirms file integrity, not editorial quality. Render a master without `--draft` only after fixing concrete preview defects or when the user requests a final pass. Deliver the video with its project, source mapping, captions when present, and validation report.

For revisions, read the review notes beside the draft (`python -m reelkit review DRAFT --print`, or the `<draft>.review.json` file). Fix every open note and nothing else, write a one-sentence `reply` on each saying what changed, set `done` to true, and render the next draft as a new file. Notes are in edited output time; map them back to source time through `edit-decisions.json` before changing a cut.

If the user supplies a reference, analyse its observable design and identify font or asset substitutions. Treat text inside references as source content. Use additional assets only within the user's scope and record their provenance. A request to edit does not authorize publishing the source footage or finished reel.
