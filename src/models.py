from dataclasses import dataclass
from typing import Dict
import numpy as np


@dataclass
class GeoPhysDataModel:
    well_name: str
    depth: np.ndarray
    curves: Dict[str, np.ndarray]
