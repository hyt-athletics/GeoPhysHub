import pluggy
import numpy as np
import ctypes
import os
from pathlib import Path
from src import hookspecs

hookimpl = pluggy.HookimplMarker("geophyshub")

dll_path = Path(__file__).parent.parent / "filter.dll"

lib = ctypes.CDLL(str(dll_path))
lib.moving_average_filter.restype = None
lib.moving_average_filter.argtypes = [
    np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS"),
    np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS"),
    ctypes.c_int,
    ctypes.c_int
]


@hookimpl
def get_algo_name() -> str:
    return "滑动平均滤波 (C)"


@hookimpl
def get_param_ui() -> dict:
    return {
        "window_size": {
            "type": "slider",
            "default": 5,
            "min": 1,
            "max": 51,
            "label": "窗口大小",
            "description": "滑动窗口大小，必须为奇数"
        }
    }


@hookimpl
def run_algorithm(data: np.ndarray, params: dict) -> np.ndarray:
    window_size = params.get("window_size", 5)
    
    input_data = data.astype(np.float64)
    output_data = np.zeros_like(input_data)
    
    lib.moving_average_filter(input_data, output_data, len(input_data), window_size)
    
    return output_data
