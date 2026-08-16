#!/usr/bin/env bash
# Run the feetplayer test suite.
#
# Nothing here needs a display and nothing here needs a speaker. The Fortran
# decoders are compiled on demand by the modules themselves, so the first run
# on a machine takes a few seconds longer than the rest; where there is no
# gfortran the three decoder suites say so and skip, which is a path worth
# running too.
#
# The one outside requirement is feetbrowser-engine, the Rust image decoders
# mediacodec.py hands a Motion JPEG frame to. It is built into a local .venv
# here, the same way FeetBrowser's own test.sh builds it.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi

# Building it takes minutes, so it is built once and then left alone. Pass
# any argument to pip by re-running with the venv removed.
if ! .venv/bin/python -c "import feetbrowser_engine" 2>/dev/null; then
  .venv/bin/pip install -q "feetbrowser-engine @ git+https://github.com/JuiceyDew/FeetBrowser@10d092ecd99543725143d6ab284e5166d4930bea#subdirectory=rust"
fi

if ! .venv/bin/python -c "import pyflakes" 2>/dev/null; then
  .venv/bin/pip install -q pyflakes
fi

.venv/bin/python -m pyflakes feetplayer tests setup.py

# Every suite below runs behind a deadline. A decoder that loops forever on a
# malformed stream is exactly the failure that otherwise says nothing at all;
# the watchdog turns it into every thread's stack and a non-zero exit. See
# tests/watchdog.py; FEETBROWSER_TEST_TIMEOUT overrides the number.
run=".venv/bin/python tests/watchdog.py 900"

$run tests/test_audio.py   # plays real sound where there is a device, skips elsewhere
$run tests/test_h264.py    # the Fortran H.264 decoder, or the skip where there is no gfortran
$run tests/test_aac.py     # the Fortran AAC decoder, against FFmpeg's samples
$run tests/test_mp3.py     # the Fortran MPEG Layer III decoder, likewise
$run tests/test_pcm.py     # uncompressed sound, against the waveform it was made from
