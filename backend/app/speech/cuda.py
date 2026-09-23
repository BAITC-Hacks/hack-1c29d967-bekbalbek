"""Load CUDA wheel libraries before CTranslate2 initializes."""

import ctypes
import importlib.util
import os
from pathlib import Path

_LIBS = (
    ("nvidia.cublas", "libcublasLt.so.12"),
    ("nvidia.cublas", "libcublas.so.12"),
    ("nvidia.cudnn", "libcudnn.so.9"),
    ("nvidia.cuda_nvrtc", "libnvrtc.so.12"),
)


def _wheel_lib_dir(package: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(package)
    except (ModuleNotFoundError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations))) / "lib"


def preload_cuda_libs() -> bool:
    """Return whether all required CUDA libraries are available; CPU remains usable."""
    ok = True
    for package, soname in _LIBS:
        lib_dir = _wheel_lib_dir(package)
        path = lib_dir / soname if lib_dir else None
        if path is None or not path.exists():
            ok = False
            continue
        try:
            ctypes.CDLL(str(path), mode=os.RTLD_GLOBAL)
        except OSError:
            ok = False
    return ok
