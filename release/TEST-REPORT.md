# Verification report, v0.1.0

Prepared 2026-11-09. This records checks actually completed during packaging; it is not a claim that every possible source or operating system has been tested.

## Completed

- Fresh isolated installation with the actual `bootstrap.py --check` path on macOS arm64, Python 3.14.7. Core, caption, and portrait dependencies installed successfully. Exact installed versions are recorded in `ENVIRONMENT.json`.
- All three illustrated 10-second template demos rendered at 540×960 / 30 fps with 48 kHz audio. Each passed geometry, duration, and full-decode checks. Opening, middle, and closing graphic states were visually reviewed.
- The local browser editor loaded, changed templates, accepted a custom hook, rendered the sample, and displayed export links. The normal file-chooser upload path was also exercised with the public illustrated sample, then rendered using default settings. Browser playback was checked.
- Local faster-whisper transcription and MODNet portrait separation were exercised on a short private test clip. The 1080×1920 export combined a source cut, captions, portrait blur, a silent visual insert, and synthesized effects. It produced a 5.5-second master with 48 kHz audio and passed full decoding. The private source, transcript, and test output are not in this package.
- 18 unit/integration tests passed with `REELKIT_INTEGRATION=1`: frame-based source/output mapping, removed caption words, SRT roundtrip, silence guards, no-cut behaviour on silent audio, template validation, explicit stage timing, subtitle retiming, caption-free rerender cleanup, corrupt/truncated export rejection, upload/session boundaries, static path containment, and HTTP range playback support.
- A separately corrupted H.264 packet fixture was correctly rejected by the stricter decoder validation after an independent review found the original check insufficient.
- The repository skill passed its frontmatter/name validation.
- Independent review findings about unavailable caption controls, stale SRT files, oversized caption caching, decode error handling, and static-route containment were addressed.

## Release checks

The archive builder includes only the documented source directories, scans text for personal paths and common secret patterns, records per-file hashes, and checks archive CRCs. The final extracted-archive smoke test is recorded in `ARCHIVE-CHECK.md`.

## Limits and pending external checks

- Windows and Linux launchers and a three-OS GitHub Actions workflow are included. Those OS runs have **not** been executed in this local Mac environment. Run the workflow after publication before expanding platform support claims.
- The GUI is a local starter, not a hosted multi-user service or a full timeline editor. No cloud deployment was performed.
- Typography is designed around English/Latin-script examples. HDR input, unusual media, very long clips, and arbitrary non-Latin fonts need additional verification. The source limit is ten minutes; the browser upload limit is 600 MB.
- Pause cutting is conservative. Automatic recognition, phrase-level SRT edits, matte edges, and subjective pacing still require review. Card timing defaults to five evenly spaced sections and is configurable.
- Neither the toolkit nor the template demos have been published to GitHub yet. This package provides the source and publishing handoff.
