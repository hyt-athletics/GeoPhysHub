import pluggy
import numpy as np
from src import hookspecs

hookimpl = pluggy.HookimplMarker("geophyshub")


@hookimpl
def get_algo_name() -> str:
    return "滑动平均滤波 (Python)"


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
    
    if window_size % 2 == 0:
        window_size += 1
    
    half_window = window_size // 2
    n = len(data)
    result = np.zeros_like(data)
    
    for i in range(n):
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        result[i] = np.mean(data[start:end])
    
    return result
