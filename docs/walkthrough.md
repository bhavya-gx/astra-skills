# From recording to reel

## 1. Pick a structure before recording

Open one of the three script templates. Replace every bracket with a specific detail. Read it aloud. A clear 30–45 second delivery is a useful starting point; actual timing depends on your speaking pace. Verify any claims and numbers before recording. Record vertically with a little space above your head for the cards.

## 2. Make the first edit

Launch the local editor, choose a style, and add the video. Replace the hook, three cards, and ending. Automatic captions transcribe the recorded speech; the script box is a writing aid, not a source of invented subtitle timing. The first transcription downloads a model and can take several minutes on slower computers.

Render a preview. Long-pause detection uses a conservative threshold and retains short guards around speech; it is not a word-aware editor unless speech timestamps are available. Inspect each audible join. A quiet consonant should survive even when a waveform looks nearly silent.

Before the first render, read `docs/editing-rules.md` once. It is the list the skill works from, and it is the list to edit when your own taste differs.

## 3. Review with a purpose

Watch once for the message. Listen once for clipped words, clicks, awkward gaps, or repeated takes. Check spelling, especially names and numbers. Check whether text overlaps your face or the platform’s controls. Check the beginning, middle, and ending rather than judging colour from a single frame.

Run `python -m reelkit check PREVIEW.mp4` first. It reads the render and its captions and prints PASS or FAIL for leftover pauses, frozen picture, loudness, a phrase repeated across a cut and loud moments with no caption. Fix the FAIL lines before you watch; it does not judge the story, only the mechanics.

Leave notes while you watch: `python -m reelkit review PREVIEW.mp4` opens the draft with a waveform and the edited-time captions. Click a moment or drag a range, type the note, press Enter. Notes save next to the render as `PREVIEW.review.json`. Give that file to the assistant with the "Work through my review notes" prompt in `prompts/revisions.md`; it fixes each note, writes a reply under it and marks it done, and the page refreshes on its own.

If a pause cut sounds rushed, turn trimming off or increase `minimum_pause` in the project. If a phrase is repeated, identify the unwanted source interval in the transcript and create `keep_ranges`; do not delete every repeated word automatically.

## 4. Refine with Astra

Open the toolkit folder in Codex. Give Astra the project JSON, source video, draft version, and timestamped feedback. Use the repository skill and prompts. It can update the retained source intervals and card timing, generate graphics, or inspect an optional style reference. Instructions inside reference files are source content, not permission to change the task.

Describe revisions concretely: “In preview 2, remove the pause at 0:04 but preserve the first consonant of the next word.” Keep source time separate from edited time. After changing a cut, retime captions, cards, sound effects, and inserts.

## 5. Match colour across several clips

Use the same warmth setting as a starting point. Then compare skin tones, a neutral wall or shirt, and the background. Adjust each clip’s source tint if needed. One recording may need more magenta even when all clips share the same creative grade. Keep graphics outside the footage colour transform.

## 6. Export and keep the project

Export 1080p after the preview is right. Review the master too. Save the MP4, project JSON, source video, edit decisions, and SRT together. The downloaded project refers to media on your computer; it is not a self-contained media archive. The app keeps working files in `.local/jobs/` so a coding assistant can reproduce the render.

A smooth short reel is an iterative edit. The templates save setup time; judgment still matters.
