"""Run this project's shared verifier from any working directory."""
from pathlib import Path
import os
import platform
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))

from portfolio_common.verification import main


if __name__ == "__main__":
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("Project 01's strict numerical profile requires an x86-64 AVX2/FMA CPU.")
    # Pin CPU dispatch before NumPy/SciPy load in the notebook subprocess.
    # Finite-difference ARIMA optimization amplifies CPU-dependent rounding.
    os.environ.update({
        "OPENBLAS_CORETYPE": "Haswell",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NPY_DISABLE_CPU_FEATURES": (
            "AVX512F,AVX512_SKX,AVX512_CLX,AVX512_CNL,AVX512_ICL,AVX512_SPR"
        ),
    })
    main(ROOT)
