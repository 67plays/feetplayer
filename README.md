# feetplayer

The media stack [FeetBrowser](https://github.com/JuiceyDew/FeetBrowser) plays
sound and video with, in its own repository. Every decoder in here was written
from scratch for that browser, under a licence whose condition 2 says that
where the Software requires an H.264 decoder, the Licensee shall grow one.

It was extracted rather than written: this is the same code, at the same
commits, moved so that the browser is a browser and the codecs are a library.

## What is in it

**Three decoders in FORTRAN 77**, about 14,800 lines of it, compiled by
gfortran into a shared library and called through `ctypes`:

  * **H.264/AVC** (`fortran/h264*.f`) -- I, P and B slices, CABAC and CAVLC,
    4:2:0 8-bit, Baseline, Main and High profile. Every intra prediction mode,
    both transform sizes, scaling matrices, quarter-sample motion
    compensation, explicit and implicit weighted prediction, bi-prediction,
    spatial and temporal direct, up to four reference frames, the deblocking
    filter. Not interlace, not SP/SI slices.
  * **AAC-LC**, the instep (`fortran/inst*.f`) -- the filterbank, both window
    shapes, TNS, mid/side and intensity stereo, PNS.
  * **MPEG-1/2 Layer III**, the ball (`fortran/ball*.f`) -- the bit
    reservoir, both block types, the alias reduction, the polyphase
    synthesis, MPEG-2 LSF.

Fortran because the entropy layer of a codec is a serial dependency chain --
one table lookup, one subtract, one compare, per *bit*, and a bitstream is
millions of bits. Python does that at a few hundred thousand bins a second.
Fortran does it at 120 million. And because the licence says that where two
implementation languages are available and one of them is the obvious choice,
the other one shall be selected.

**The containers** (`mediacodec.py`) -- MP4/MOV, AVI, WebM and WAV, parsed
here: sample tables, composition offsets, the bit reservoir's neighbours, and
an honest refusal with the dimensions and the codec name in it for everything
there is no decoder for.

**The audio output** (`heel.py`) -- a ring buffer, a polyphase resampler, a
mixer, and an audio clock, over one backend per platform: `coreaudio.py`
(macOS), `winmm.py` (Windows), `alsa.py` (Linux), each of them `ctypes`
against the system library and none of them a wheel off PyPI.

**The joiner** (`arch.py`) -- what plays a decoded stream out of a device and
keeps a clock the pictures can be hung off.

Everything is named after part of the foot because condition 3 of the licence
requires it. The ankle is a leg part and everybody knows it.

## Installing

```
pip install git+https://github.com/67plays/feetplayer
```

gfortran is a build-time requirement and never a runtime one. With one on
`PATH` at install time the three libraries are compiled into the package;
without one they are compiled on first use into the temporary directory; with
no gfortran anywhere the decoders report themselves unavailable, by name and
with a reason, and everything that does not need them keeps working. That is
a path the suite tests on purpose.

There are no Python dependencies. The decoders are Fortran and the audio
output is `ctypes` against libraries the operating system already has.

Two codecs are the exception, and they are optional. Motion JPEG and
QuickTime `png ` are still-image formats in a container costume, so they use
the JPEG and PNG decoders in `feetbrowser_engine` -- FeetBrowser's Rust
extension -- rather than carrying a second copy of a JPEG decoder and a
second copy of its bugs. It is deliberately not a dependency: FeetBrowser
depends on this package, and depending back on FeetBrowser's own extension
would make a cycle, so installing feetplayer would fetch a second engine
beside the one a browser checkout had already built.

Without it, those two codecs refuse by name the way any codec we never wrote
refuses, and everything else -- H.264, AAC, MP3, PCM, every container -- is
unaffected. If you want them:

```
pip install "git+https://github.com/JuiceyDew/FeetBrowser#subdirectory=rust"
```

which needs a Rust toolchain.

## Using it

```python
from feetplayer import mediacodec, arch

track = mediacodec.open_video(open("clip.mp4", "rb").read())
frame = track.frame(0)          # frame.rgba: 4 bytes per pixel

player = arch.AudioPlayer(data=open("clip.mp4", "rb").read())
player.play()
```

`mediacodec.probe(data)` answers what a file is without decoding it, and says
why not when there is no decoder for it.

## Tests

```
./test.sh
```

No pytest: every suite is a file of `test_*` functions with a `main()` that
runs them and prints one line each. The H.264, AAC and MP3 suites compare
against ground truth a reference decoder produced offline -- pixel-exact for
H.264, which is a bit-exact specification, and inside a measured tolerance
for the two transforms that are not. `live_*` functions are the half that
needs a real speaker; they say so and skip where there is none.
