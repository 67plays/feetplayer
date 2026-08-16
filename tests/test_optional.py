"""The one dependency this package has, and the fact that it is optional.

`feetbrowser_engine` is FeetBrowser's Rust extension. Two codecs here use
it -- Motion JPEG and QuickTime `png `, both of which are a container format
wrapped around a still image whose decoder was already written for `<img>`.
Nothing else does.

That makes it the only thing in feetplayer that comes from outside
feetplayer, and it is deliberately not a dependency: FeetBrowser depends on
this package, so depending back on FeetBrowser's own extension would be a
cycle, and the practical form of that cycle is a user whose checkout built
one engine with maturin and whose `pip install` then fetched a second,
older one under the same import name.

So the contract this file exists to hold is: with the engine absent,
importing the stack works, H.264, AAC, MP3 and PCM decode exactly as they
otherwise would, and the two codecs that genuinely cannot work say so by
name. A refusal that named nothing, or an ImportError at module scope,
would both be failures of it.

Absence is simulated rather than arranged. `sys.modules["feetbrowser_engine"]
= None` is the documented way to make `import feetbrowser_engine` raise, and
it is used here because the alternative -- a suite that only means anything
in a virtualenv somebody remembered not to install something into -- is a
suite that passes for the wrong reason on most machines. The CI job that
installs into a genuinely empty venv is the other half of this, and neither
half is sufficient alone.
"""
import contextlib
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feetplayer import mediacodec

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

# What a refusal has to contain: the codec's name, so the message says which
# file will not play, and the module's name, so it says what to install.
NAMED = "feetbrowser_engine"


def _read(*parts):
    with open(os.path.join(FIXTURES, *parts), "rb") as handle:
        return handle.read()


@contextlib.contextmanager
def _without_engine():
    """`import feetbrowser_engine` raises inside this block.

    A `None` in `sys.modules` is what the import system treats as "this was
    looked for and is not there", which is exactly the state being modelled
    and is why this does not need to touch the filesystem or the path. The
    previous value is restored rather than deleted, because on a machine
    that does have the engine installed something else may already hold a
    reference to it and the next test would otherwise import a second copy.
    """
    missing = object()
    previous = sys.modules.get("feetbrowser_engine", missing)
    sys.modules["feetbrowser_engine"] = None
    try:
        yield
    finally:
        if previous is missing:
            del sys.modules["feetbrowser_engine"]
        else:
            sys.modules["feetbrowser_engine"] = previous


def _refusal(codec, name):
    """The MediaError from building `codec` with no engine, as a string."""
    try:
        codec(320, 240)
    except mediacodec.MediaError as exc:
        reason = str(exc)
    else:
        raise AssertionError("%s built a decoder with no engine" % name)
    assert name in reason, "%s: the refusal does not name it: %r" % (
        name, reason)
    assert NAMED in reason, (
        "%s: the refusal does not say what is missing: %r" % (name, reason))
    return reason


def test_motion_jpeg_refuses_by_name_when_the_engine_is_missing():
    with _without_engine():
        reason = _refusal(mediacodec._Mjpeg, "MJPEG")
    print("  ok  MJPEG refused: %s" % reason)


def test_quicktime_png_refuses_by_name_when_the_engine_is_missing():
    with _without_engine():
        reason = _refusal(mediacodec._PngFrames, "QuickTime PNG")
    print("  ok  QuickTime PNG refused: %s" % reason)


def test_the_refusal_happens_at_open_time_not_at_the_first_frame():
    """A player that opens a file and then fails on frame one has already
    drawn a window and started a clock. The two codecs raise from their
    constructors, which is where every other missing decoder raises, so the
    container turns it into the same "no decoder" answer `probe()` gives for
    VP9 -- before anything is presented."""
    with _without_engine():
        for codec, name in ((mediacodec._Mjpeg, "MJPEG"),
                            (mediacodec._PngFrames, "QuickTime PNG")):
            try:
                codec(320, 240)
            except mediacodec.MediaError:
                pass
            else:
                raise AssertionError("%s deferred its refusal" % name)


def test_h264_decodes_with_no_engine_installed():
    """The reason the package exists, on the machine that is missing the
    thing the package does not depend on. Pixel-exact, because H.264 is
    bit-exact in the YUV domain and a tolerance here would hide a bug."""
    from feetplayer import h264
    if not h264.available():
        print("  .. no H.264 decoder here: %s" % h264.unavailable_reason())
        return
    with _without_engine():
        width, height, got = h264.Decoder().decode_i420(
            _read("h264", "qcif-high.264"))
        track = mediacodec.open_video(_read("h264", "qcif.mp4"))
        frame = track.frame(0)
    truth = zlib.decompress(_read("h264", "qcif-high.i420.z"))
    assert (width, height) == (176, 144), (width, height)
    assert got == truth, "the decoded picture is not the ground truth"
    assert len(frame.rgba) == track.width * track.height * 4, len(frame.rgba)
    print("  ok  H.264 %dx%d pixel-exact, and an MP4 frame, with no engine"
          % (width, height))


def test_aac_decodes_with_no_engine_installed():
    from feetplayer import aac
    if not aac.available():
        print("  .. no AAC decoder here: %s" % aac.unavailable_reason())
        return
    with _without_engine():
        track = mediacodec.open_audio(_read("aac", "stereo.mp4"))
        samples = track.frame(0).samples
    assert samples, "AAC frame 0 decoded to nothing"
    print("  ok  AAC %d Hz, %d ch, %d bytes with no engine"
          % (track.sample_rate, track.channels, len(samples)))


def test_mp3_decodes_with_no_engine_installed():
    from feetplayer import ball
    if not ball.available():
        print("  .. no MP3 decoder here: %s" % ball.unavailable_reason())
        return
    with _without_engine():
        track = mediacodec.open_audio(_read("mp3", "lowrate.mp3"))
        samples = track.frame(0).samples
    assert samples, "MP3 frame 0 decoded to nothing"
    print("  ok  MP3 %d Hz, %d ch, %d bytes with no engine"
          % (track.sample_rate, track.channels, len(samples)))


def test_pcm_decodes_with_no_engine_installed():
    """PCM is the one that never had a compiled decoder at all, so if the
    engine were reaching it, it would be through the container and not the
    codec -- which is the mistake this test is placed to catch."""
    with _without_engine():
        track = mediacodec.open_audio(_read("pcm", "s16le.wav"))
        samples = track.frame(0).samples
    assert samples, "PCM frame 0 read as nothing"
    print("  ok  PCM %d Hz, %d ch, %d bytes with no engine"
          % (track.sample_rate, track.channels, len(samples)))


def test_the_whole_module_imports_with_no_engine_installed():
    """The failure this guards against is a top-level import creeping back
    in, which would not show up in any test above -- they all run in a
    process where `mediacodec` was imported before the engine was hidden."""
    import importlib
    with _without_engine():
        for name in list(sys.modules):
            if name.startswith("feetplayer"):
                del sys.modules[name]
        try:
            fresh = importlib.import_module("feetplayer.mediacodec")
            # Imported is not the same as working, so ask it something: a
            # container it knows, and one it does not.
            assert fresh.sniff(_read("h264", "qcif.mp4")) == "MP4"
            assert not fresh.sniff(b"not a media file at all")
            try:
                fresh.probe(b"not a media file at all")
            except fresh.MediaError:
                pass
            else:
                raise AssertionError("probe() accepted a non-container")
        finally:
            for name in list(sys.modules):
                if name.startswith("feetplayer"):
                    del sys.modules[name]
    importlib.import_module("feetplayer.mediacodec")
    print("  ok  feetplayer.mediacodec imports from cold with no engine")


def test_the_pixel_cap_is_our_own_number():
    """`MAX_PIXELS` used to be imported from the engine, which meant a bounds
    check on a header pulled in an image library. It is defined here now, and
    the value matches the browser's on purpose: the two limits describing the
    same thing differently would be worse than either limit."""
    assert mediacodec.MAX_PIXELS == 20000000, mediacodec.MAX_PIXELS
    with _without_engine():
        try:
            mediacodec._check_size(40000, 40000)
        except mediacodec.MediaError as exc:
            assert "cap" in str(exc), exc
        else:
            raise AssertionError("1.6 gigapixels was allowed")
        mediacodec._check_size(1920, 1080)
    print("  ok  the %d pixel cap is enforced with no engine"
          % mediacodec.MAX_PIXELS)


def test_nothing_imports_the_engine_at_module_scope():
    """Read as text, because an import that only runs on one platform or
    inside one branch is still a dependency and would not show up by
    inspecting the imported module."""
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "feetplayer")
    offenders = []
    for name in sorted(os.listdir(path)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(path, name), "r") as handle:
            for number, line in enumerate(handle, 1):
                stripped = line.strip()
                if not stripped.startswith(("import ", "from ")):
                    continue
                if "feetbrowser" not in stripped:
                    continue
                if line[:1].strip():             # column zero: module scope
                    offenders.append("%s:%d: %s" % (name, number, stripped))
    assert not offenders, "imported where it cannot be caught:\n  %s" % (
        "\n  ".join(offenders))
    print("  ok  no module-scope import of the engine in any of feetplayer")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok  {t.__name__}")
        except Exception as e:
            failed += 1
            import traceback
            traceback.print_exc()
            print(f" FAIL {t.__name__}: {e}")
    if failed:
        print(f"\n{failed} FAILED")
        sys.exit(1)
    print(f"\nALL {len(tests)} OPTIONAL-DEPENDENCY TESTS PASSED")


if __name__ == "__main__":
    main()
