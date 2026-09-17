import os
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext
from wheel.bdist_wheel import bdist_wheel

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
# NOTE: REMEMBER TO UPDATE THE FALLBACK VERSION IN sentiment_service/__init__.py WHEN RELEASING #
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
MAJOR_VERSION = 1
MINOR_VERSION = 0
PATCH_VERSION = 0
IS_DEV_VERSION = True


install_requires = ["pydantic>=1.9.1", "wheel", "regex"]


# A CMakeExtension needs a sourcedir instead of a file list.
# The name must be the _single_ output extension from the CMake build.
# If you need multiple extensions, see scikit-build.
class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=""):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    def build_extension(self, ext):
        # build/lib.linux-x86_64-3.8
        os.makedirs(self.build_lib, exist_ok=True)
        cmake_args = os.environ.get("BIRCHSUMM_CMAKE_ARGS", "").split()

        debug = int(os.environ.get("DEBUG", 0)) if self.debug is None else self.debug
        cfg = "Debug" if debug else "Release"
        cmake_args.append(f"-DCMAKE_BUILD_TYPE={cfg}")

        cmake_args.append(
            f"-DCMAKE_INSTALL_PREFIX={Path(self.build_lib).resolve()/ 'birchsumm'}"
        )
        # Set Python_EXECUTABLE instead if you use PYBIND11_FINDPYTHON
        if "PYTHON_EXECUTABLE" not in cmake_args:
            print(f"Setting PYTHON_EXECUTABLE to {sys.executable}")
            cmake_args.append(f"-DPYTHON_EXECUTABLE={sys.executable}")

        build_args = []

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in os.environ:
            # self.parallel is a Python 3 only way to set parallel jobs by hand
            # using -j in the build_ext call, not supported by pip or PyPA-build.
            if hasattr(self, "parallel") and self.parallel:
                # CMake 3.12+ only.
                build_args += [f"-j{self.parallel}"]

        build_temp = os.path.join(self.build_temp, ext.name)
        if not os.path.exists(build_temp):
            os.makedirs(build_temp)

        subprocess.check_call(["cmake", ext.sourcedir] + cmake_args, cwd=build_temp)
        subprocess.check_call(["make"] + build_args + ["install"], cwd=build_temp)


tests_requires = ["pandas", "pytest"]

project_root = Path(__file__).parent


def discover_version() -> str:
    version = f"{MAJOR_VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"

    return version


CUR_VERSION = discover_version()


all_requires = sorted(install_requires + tests_requires + ["jupyterlab", "matplotlib"])
setup(
    name="summarization_service",
    version=CUR_VERSION,
    python_requires=">=3.7.0",
    description="Birch summarization service",
    author="Birch Technology",
    long_description=(project_root / "summ_service_jit" / "README.md").read_text(
        encoding="utf-8"
    ),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["summ_service_jit*"]),
    install_requires=install_requires,
    extras_require={"tests": tests_requires, "all": all_requires},
    ext_modules=[CMakeExtension("_birchsumm", "summ_service_jit")],
    cmdclass={"build_ext": CMakeBuild, "bdist_wheel": bdist_wheel},
)
