# Editing rules for talking-head reels

Every rule here came from a draft that was sent back. The skill reads this file before planning a cut and before delivering a render. The starter renderer handles some of it on its own (pause trimming, caption retiming, loudness, full-decode validation); the rest is the assistant's editorial call, with the user's review.

## Before anything renders

- Show the edit decision list first: the cuts with source timestamps, the hook, the three cards and the ending, and where each card lands on the transcript. Wait for approval before the first full render.
- Render a 540×960 preview first. A 1080×1920 master comes only after the preview is approved or a concrete defect was fixed.
- Originals stay untouched. Every render round is a new file (`preview-v2.mp4`, never an overwrite). The renderer renames a replaced export with a `previous-` prefix; keep those until the user says otherwise.
- Nothing on screen says anything the person did not say. Real numbers, real names, real screenshots. No invented proof.

## The cut

- Transcribe the whole recording before cutting. Never scrub by waveform alone; quiet consonants look like silence.
- Cut on word boundaries and sentence ends, never on transcription segment edges, or clips start and stop mid-sentence.
- When a line was said two or three times, keep the last complete take unless an earlier one is clearly better. Drop false starts, "let me redo that", anything said to the camera operator, and the dead air before the first word and after the last.
- Keep the person's own phrasing, asides and accents. Only repeats, false starts and empty filler go.
- Pauses up to 0.5 s stay. Longer pauses come down to a short beat, not to zero; a cut to zero silence sounds like a jump.
- After the cut, scan the final transcript for any word or phrase said twice within ten seconds. `python -m reelkit check` does this from the captions; read the line and decide whether the repeat is a retake or on purpose.

## Pace

- First word by frame 6 (0.2 s). No logo, no breath, no "so".
- Something changes on screen every 1.5 to 2 s: a card, a caption beat, a punch-in. No empty shot over 1.5 s.
- Every shot earns its place. If a sentence does not move the story, it goes, however well it was delivered.
- Leave a few sentences bare. A card lands harder after a stretch with nothing on screen.

## Captions

- One to three words at a time, landing two frames before they are heard, cleared about 0.4 s after the last word, never held through a pause, never overlapping the next beat.
- Claim words and numbers bold, the rest regular. Never a caption that says a different word than the audio.
- Keep captions out of the top 13% and bottom 20% of a 9:16 frame and clear of the right rail where the platform buttons sit. Never over the face.
- Names spelled the way their owners spell them. Check every proper noun and figure against the source, not the transcript.
- A dark backing behind text over bright areas; no outlines, no drop shadows that read as a second colour.

## Type, cards and colour

- One type family, two weights: thin for most text, heavy for the claim. White text, flat, with a soft broad shadow.
- Cards are translucent dark glass with a thin border; colour lives in small tiles and pills, not in the card.
- Icons are drawn or licensed; never emoji from the operating system, never a recreated brand mark. Brand marks are the real file or nothing.
- Keep the camera colour. Correct tint per source so skin matches across clips, then one shared warm grade. Do not fix exposure with the grade; fix it in the next recording.

## Face and framing

- Never cover the face. Text that needs to sit higher goes behind the head, not over it.
- Keep the source geometry. Move or scale the graphics; never stretch or reposition the person to make room.
- Punch-ins are small (1.0 to 1.08) and quick (five frames), on the key number or claim, at most every third line.

## Motion and sound

- One designed move per scene change. Transitions only on cuts, never inside a sentence.
- Counters land on the number as it is said. Cards enter on the phrase, not before it.
- Music ducks about 10 dB under the voice. Two to four sound effects per beat at most, none on top of a word, no effect twice in one reel.
- Master at −16 LUFS integrated (the renderer's target) with true peak under −1 dBTP. Fix voice loudness before adding effects, not after.

## Before delivery

- Run `python -m reelkit check RENDER` and read every FAIL.
- Pull a contact sheet (one frame a second) and look: captions readable, nothing on the face, hook visible, no cut mid-word.
- Transcribe the finished render and read it against the plan: every line present, in order, no leftover repeat, no chopped word.
- Deliver the render, the project JSON, the cut list (what was removed and why), the captions file and the check result. The captions stay editable; offer the SRT.
- Edit only what was asked. Flag anything else you noticed; do not fix it unasked.

## Where edits go wrong

- Cutting on transcription segment edges instead of word times.
- Trusting the transcript for names and numbers.
- Judging colour from one frame instead of the start, middle and end.
- Rendering a master before the preview was approved, or delivering a preview as the master.
- Fixing things nobody asked about, and breaking something that was approved.
