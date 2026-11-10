# Security

## Reporting

Report a vulnerability privately through GitHub's **Report a vulnerability** button on the Security tab of this repository. Do not open a public issue for security problems. Expect an acknowledgement within a week.

## What the toolkit does and does not do

- The local editor binds to `127.0.0.1` only, uses a per-session token for uploads and renders, rejects paths outside its working folders, and is not designed to be exposed to a network. Do not port-forward it.
- Your footage, transcripts, and renders stay on your computer. The toolkit sends no audio or video to any service.
- The first setup downloads Python packages from PyPI and, on first use, a speech model and a portrait-matting model from Hugging Face. The matting download is checked against a pinned SHA-256.
- Colour values and file paths from a project JSON are validated before they reach FFmpeg filter graphs.

## Supported versions

Only the latest release receives fixes.
