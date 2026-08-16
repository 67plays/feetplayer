"""Compile the three Fortran decoders into the wheel, at build time.

Everything about the build itself is in `h264.build_library`,
`aac.build_library` and `ball.build_library`, which is where it already was:
those are the entry points FeetBrowser's three packagers call, they own the
flag sets and the check that the result is fit to ship, and nothing here
repeats any of it. This file only says where the libraries go -- beside the
Python inside the package, which is where `prebuilt_path()` looks -- and
that a wheel with a shared library in it is not a pure-Python wheel.

A machine with no gfortran still builds and still installs. That is not a
convenience, it is the same arrangement the modules have at runtime: without
a compiler the decoder reports itself unavailable and everything that does
not need it keeps working, and a suite runs against that path on purpose.
The one difference between the two is when the compiling happens, and a
package that only ever compiled on first play would do it into the
temporary directory of whoever ran it first.
"""
import os
import sys

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.dist import Distribution

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feetplayer import aac, ball, h264                        # noqa: E402

DECODERS = ((h264, "H.264"), (aac, "AAC"), (ball, "MP3"))


class BuildWithFortran(build_py):
    def run(self):
        build_py.run(self)
        into = os.path.join(self.build_lib, "feetplayer")
        for module, what in DECODERS:
            out = os.path.join(into, module.prebuilt_name())
            try:
                module.build_library(out, report=lambda line, what=what:
                                     print("%s: %s" % (what, line)))
            except Exception as exc:
                print("no %s decoder in this build: %s" % (what, exc))


class HasLibraries(Distribution):
    """A wheel carrying a .so/.dylib/.dll is for one platform, not for all.

    setuptools works this out from `ext_modules`, which are the extensions it
    built itself; these were built by gfortran, so it has to be told.
    """

    def has_ext_modules(self):
        return True


setup(cmdclass={"build_py": BuildWithFortran}, distclass=HasLibraries)
