# Contributing

Start with the README and a demo render. For a code change, explain the user-visible problem and test the behaviour that changed. Timeline changes should cover source/output mapping and audio duration. Layout changes should include a preview image. Keep fonts, assets, and fixtures distributable with clear provenance.

Run `python -m unittest discover -s tests -v` and `python -m reelkit demo --template all` using the project environment. Do not commit `.local`, `.cache`, `.venv`, your raw footage, or private transcripts. Keep new dependencies proportionate to the feature.

`main` is protected. Fork the repository, open a pull request, and wait for the checks and a maintainer review. Nobody pushes to `main` directly, including the maintainer. The two skill files (`.agents/skills/reel-edit/SKILL.md` and `.claude/skills/reel-edit/SKILL.md`) must stay identical; a test enforces it.

Want your own version? Click **Use this template** instead of forking. You get a clean copy with no link back to this repository, and you can change anything.
