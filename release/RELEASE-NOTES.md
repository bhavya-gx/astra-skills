# Video Skills v0.2.0

Same one prompt, more of the workflow. The repository is now **Video Skills** (formerly Astra Skills): the skills run in Codex with GPT-6 Astra and in Claude Code, and the name says what it is. The old address redirects.

## New

- **Review with notes.** `python -m reelkit review PREVIEW.mp4` opens a draft in the browser with a waveform and its captions. Click a moment or drag a range, type the note, press Enter. Notes save beside the render as `PREVIEW.review.json`; the assistant works through them with the "Work through my review notes" prompt, replies under each and marks it done. `--print` gives the notes as text. Nothing is uploaded.
- **Edit check.** `python -m reelkit check RENDER` prints PASS or FAIL for a pause left in the cut, a frozen picture, loudness off target (−16 LUFS, true peak under −1 dBTP), a phrase repeated across a cut, and loud stretches with no caption. Exit code 1 on any FAIL.
- **Editing rules.** `docs/editing-rules.md`, the list the `reel-edit` skill applies before a cut and before a delivery. Copy it, cross out what is not you.
- **Reference script skill.** `reference-script` writes your version of a reel you admire, beat for beat, from your own facts file (`voice/facts-interview.md`, with a fictional filled example). Anything missing is marked `[CHECK]`, never invented.
- **Two single-purpose reel skills.** `pale-yellow-reel` (one shot, fixed lettering, four seconds) and `pink-broll-reel` (three portrait shots under a fixed title). Public copies carry the style settings and renderer; personal lettering and audio stay local.

## Unchanged

The three templates, the local editor, the renderer and the project format. Both new commands use only the standard library and the bundled FFmpeg; no new dependency. The `reelkit` package name stays.

## Install

Use this repository as a template, or download the archive, extract it and open `START-HERE.html`. Python 3.10 or newer (3.12 recommended); the first setup needs internet for dependencies and, on first use, the speech and portrait models. The editor needs no AI account. Codex or Claude Code is needed for the skills, with your own access.

Original code, documentation and artwork are MIT licensed. Included fonts keep their SIL Open Font Licenses. AI model access is separate.

## v0.1.0 (9 November 2026)

First release: the `reel-edit` skill, the first-edit and revision prompts, the local editor, three templates with fill-in scripts, local captions, pause trimming, noise reduction, warm grade and tint, optional portrait blur, original icons and sound effects, draft and master exports. Its archive is named `astra-skills-v0.1.0.zip`.
