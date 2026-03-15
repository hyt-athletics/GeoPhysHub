import ctypes
import os
import platform
from typing import Any, Callable, Optional, Union


class CBridge:
    def __init__(self, lib_path: Optional[str] = None):
        self._lib = None
        self._lib_path = None
        if lib_path:
            self.load_library(lib_path)

    def load_library(self, lib_path: str) -> None:
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Library not found: {lib_path}")
        
        self._lib_path = lib_path
        
        if platform.system() == 'Windows':
            self._lib = ctypes.CDLL(lib_path)
        else:
            self._lib = ctypes.CDLL(lib_path)

    def get_function(self, func_name: str) -> Any:
        if not self._lib:
            raise RuntimeError("No library loaded. Call load_library first.")
        
        try:
            return getattr(self._lib, func_name)
        except AttributeError:
            raise AttributeError(f"Function '{func_name}' not found in library.")

    def allocate_buffer(self, size: int) -> ctypes.Array:
        return (ctypes.c_char * size)()

    def allocate_int_buffer(self, size: int) -> ctypes.Array:
        return (ctypes.c_int * size)()

    def allocate_double_buffer(self, size: int) -> ctypes.Array:
        return (ctypes.c_double * size)()

    def call_function(self, func_name: str, *args) -> Any:
        func = self.get_function(func_name)
        return func(*args)

    @property
    def lib_path(self) -> Optional[str]:
        return self._lib_path

    @property
    def is_loaded(self) -> bool:
        return self._lib is not None
