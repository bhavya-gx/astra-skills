# Troubleshooting

**The launcher does not open.** Extract the ZIP first. Install Python from python.org if needed. Open a terminal in this folder and run `python3 bootstrap.py`, or `py bootstrap.py` on Windows. This avoids depending on executable permission surviving the download. Leave the terminal running while the browser is open.

**First setup fails.** Read the terminal error. Use a current 64-bit Python 3.12+ installation and an internet connection. Run the same command again; the environment is inside `.venv/`. Linux may require the distribution's `python3-venv` package. To try only graphics and rendering, use `python3 bootstrap.py --lite`.

**No browser opened.** Copy the `http://127.0.0.1:...` URL printed by the launcher into a browser on the same computer. Do not expose this development server to the internet.

**Speech model cannot load.** The first transcription needs access to Hugging Face. Retry online, use a source-timed SRT, or turn off automatic captions. Subsequent use can reuse the local model cache. No audio is sent to a transcription service by this toolkit.

**Captions are inaccurate.** Review proper nouns, figures, and unfamiliar terms. Provide a corrected source-timed SRT to override the transcript. A pasted spoken script is not an aligned transcript.

**Background blur model checksum changed.** Do not bypass the checksum. Check the upstream model release and update the pinned checksum only after verifying the intended asset. You can render with portrait blur disabled in the meantime.

**A cut clips a quiet word.** Reduce `threshold_db` (for example, −45), increase `minimum_pause`, provide accurate speech timestamps, or use manual keep ranges. Never aim for literally zero silent samples: those can occur inside words.

**The video looks green or too orange.** Use tint for the source correction and warmth for the shared look. Compare representative frames. The starter rejects recognized HDR transfer functions; export an SDR/Rec.709 copy for this workflow.

**Text covers my face.** Move the title or caption position and rerender. The template does not track head position automatically. Keep enough clear space when recording.

**Non-English text shows missing characters.** The bundled typography is intended for English/Latin-script examples. Choose a font with the required glyph coverage in `reelkit/graphics.py`; retest wrapping and placement.

**The check fails on loudness for a quiet recording.** The renderer normalises dialogue to −16 LUFS, so a FAIL here usually means the file was not rendered by this toolkit or was re-encoded afterwards. Re-export from the project, or pass `--target-lufs` and `--tolerance` when checking a file made elsewhere.

**The check reports a repeat that is intentional.** Repetition on purpose is fine. The check cannot tell; read the line and keep it. With `edit-decisions.json` beside the render the scan limits itself to the cuts, where accidental retakes live.

**The review page shows no waveform.** The file has no audio track, or the bundled FFmpeg could not decode it. The page still plays the video and saves notes. Open the render or its folder with `python -m reelkit review PATH`; the page only serves videos inside that folder.

**Rendering takes time.** Start with 540p previews. Portrait matting is slower; enable it after the layout is right. Disk use grows with saved working videos. Keep the source and the renders you need, then remove obsolete jobs from `.local/jobs/` yourself.

**I downloaded the project but it cannot find footage.** Keep the original media and update the project path. JSON downloads contain settings, not copies of your source video.

**Windows or Linux differs from the report.** The cross-platform launchers and CI workflow are included, but see `release/TEST-REPORT.md` for platforms actually tested. Report OS, Python version, exact command, and the relevant error; do not attach private source footage unless you intend to share it.
