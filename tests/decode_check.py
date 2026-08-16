"""Decode a real file with each decoder, out of the installed package.

Not a test suite -- nothing here starts with `test_`, and the suites beside
it are what hold the decoders to their ground truth. This is the other
question, the one a suite run from a checkout cannot answer: whether what
`pip install` put in site-packages works. So it deliberately does not put the
repository on `sys.path`; it imports `feetplayer` the way anybody else would.

It says which file each decoder was loaded from, because a library the
install compiled and one compiled thirty seconds ago behave identically and
a check that video works has to be able to say which of the two answered.

The H.264 comparison is exact, on the same argument the suite makes: H.264 is
bit-exact in the YUV domain, so a single differing luma sample is a bug and a
threshold here would be a way of not finding it.
"""
import os
import sys
import zlib

import feetplayer
from feetplayer import aac, arch, ball, h264, heel, mediacodec

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _read(*parts):
    with open(os.path.join(FIXTURES, *parts), "rb") as handle:
        return handle.read()


def main():
    print("feetplayer %s from %s"
          % (feetplayer.__version__, os.path.dirname(feetplayer.__file__)))
    failed = []

    for module, what in ((h264, "H.264"), (aac, "AAC"), (ball, "MP3")):
        if module.available():
            print("  ok  %-6s loaded from %s" % (what, module.library_path()))
        else:
            failed.append("%s: %s" % (what, module.unavailable_reason()))
    if failed:
        print("\n%d FAILED\n  %s" % (len(failed), "\n  ".join(failed)))
        sys.exit(1)

    width, height, got = h264.Decoder().decode_i420(_read("h264",
                                                          "qcif-high.264"))
    truth = zlib.decompress(_read("h264", "qcif-high.i420.z"))
    assert (width, height) == (176, 144), (width, height)
    assert got == truth, "the decoded picture is not the ground truth"
    print("  ok  H.264  %dx%d, %d bytes of I420, pixel-exact"
          % (width, height, len(got)))

    track = mediacodec.open_video(_read("h264", "qcif.mp4"))
    frame = track.frame(0)
    print("  ok  MP4    %s, %dx%d, %d frames, frame 0 is %d bytes of RGBA"
          % (track.codec_name, track.width, track.height, track.frame_count,
             len(frame.rgba)))

    track = mediacodec.open_audio(_read("aac", "stereo.mp4"))
    samples = track.frame(0).samples
    assert samples, "AAC frame 0 decoded to nothing"
    print("  ok  AAC    %d Hz, %d channels, %d bytes of float in frame 0"
          % (track.sample_rate, track.channels, len(samples)))

    track = mediacodec.open_audio(_read("mp3", "lowrate.mp3"))
    samples = track.frame(0).samples
    assert samples, "MP3 frame 0 decoded to nothing"
    print("  ok  MP3    %d Hz, %d channels, %d bytes of float in frame 0"
          % (track.sample_rate, track.channels, len(samples)))

    # And the output stack on a machine with no speaker: the null device
    # consumes frames exactly the way a real one does.
    output = heel.Output(heel.NullDevice(), threaded=False)
    player = arch.AudioPlayer(data=_read("mp3", "lowrate.mp3"), output=output,
                             threaded=False)
    player.play()
    for _ in range(20):
        player.pump()
    print("  ok  heel   played to %.3fs through the null device"
          % player.position())
    player.close()
    output.close()

    print("\nthe installed package decodes")


if __name__ == "__main__":
    main()
