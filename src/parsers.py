import lasio
import numpy as np
from typing import Optional
from .models import GeoPhysDataModel


class LASParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._las: Optional[lasio.LASFile] = None

    def parse(self) -> GeoPhysDataModel:
        try:
            self._las = lasio.read(self.file_path)
            
            well_name = self._extract_well_name()
            depth = self._extract_depth()
            curves = self._extract_curves(depth)
            
            return GeoPhysDataModel(
                well_name=well_name,
                depth=depth,
                curves=curves
            )
        except Exception as e:
            raise LASParserError(f"Failed to parse LAS file: {str(e)}") from e

    def _extract_well_name(self) -> str:
        if not self._las:
            return ""
        
        well_name_fields = ['WELL', 'NAME', 'UWI', 'API']
        for field in well_name_fields:
            if hasattr(self._las.well, field):
                value = getattr(self._las.well, field).value
                if value and str(value).strip():
                    return str(value).strip()
        
        return ""

    def _extract_depth(self) -> np.ndarray:
        if not self._las:
            return np.array([])
        
        depth_curve_names = ['DEPTH', 'DEPT', 'MD', 'TVD']
        for name in depth_curve_names:
            if name in self._las.curves:
                return np.array(self._las[name])
        
        if self._las.curves and len(self._las.curves) > 0:
            return np.array(self._las.curves[0].data)
        
        return np.array([])

    def _extract_curves(self, depth: np.ndarray) -> dict:
        if not self._las:
            return {}
        
        curves = {}
        depth_curve_names = ['DEPTH', 'DEPT', 'MD', 'TVD']
        
        for curve in self._las.curves:
            if curve.mnemonic not in depth_curve_names:
                curves[curve.mnemonic] = np.array(self._las[curve.mnemonic])
        
        return curves


class LASParserError(Exception):
    pass
