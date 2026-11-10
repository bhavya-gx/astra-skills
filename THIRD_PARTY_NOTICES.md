# Third-party notices

The MIT license in this repository covers the original toolkit code, documentation, icons, demo illustration, and synthesized sound effects. It does not relicense dependencies, fonts, model weights, personal footage, or external assets added by a user.

## Bundled fonts

- **Inter Tight**, unmodified font file: Google Fonts / Inter Project Authors. SIL OFL 1.1; see `assets/fonts/InterTight-OFL.txt`. Upstream: https://github.com/google/fonts/tree/main/ofl/intertight
- **Instrument Serif**, unmodified font file: Instrument Serif Project Authors. SIL OFL 1.1; see `assets/fonts/InstrumentSerif-OFL.txt`. Upstream: https://github.com/google/fonts/tree/main/ofl/instrumentserif

## Dependencies installed separately

- Python: https://www.python.org/psf/license/
- Pillow: HPND; https://github.com/python-pillow/Pillow/blob/main/LICENSE
- imageio-ffmpeg: BSD-2-Clause; https://github.com/imageio/imageio-ffmpeg
- FFmpeg: LGPL/GPL depending on build; the installed imageio-ffmpeg wheel supplies its executable and associated notices. The toolkit ZIP does not contain an FFmpeg binary. https://ffmpeg.org/legal.html
- faster-whisper: MIT; https://github.com/SYSTRAN/faster-whisper
- CTranslate2: MIT; https://github.com/OpenNMT/CTranslate2
- NumPy: BSD-3-Clause; https://numpy.org/doc/stable/license.html
- ONNX Runtime: MIT; https://github.com/microsoft/onnxruntime

## Models downloaded on first use

- Whisper base, converted for faster-whisper: https://huggingface.co/Systran/faster-whisper-base ; upstream Whisper is MIT licensed: https://github.com/openai/whisper
- MODNet ONNX: https://huggingface.co/Xenova/modnet ; upstream MODNet is Apache-2.0: https://github.com/ZHKKKe/MODNet . The downloader verifies the tested file's SHA-256. Weights are not bundled in this repository.

The package contains no Apple emoji font, commercial font, downloaded creator reference reel, private transcript, or third-party product screenshot. Icons are original geometric illustrations. Demonstration products and claims in the writing templates are explicitly fictional.
