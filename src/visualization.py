import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from typing import Dict, List, Optional, Tuple
import platform
import warnings

# 忽略字体警告
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# 设置中文字体
def setup_chinese_font():
    system = platform.system()
    
    if system == 'Windows':
        # Windows系统常用中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi', 'FangSong']
    elif system == 'Darwin':
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'STHeiti']
    else:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Droid Sans Fallback', 'Noto Sans CJK SC']
    
    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False

setup_chinese_font()


class WellPlotter:
    def __init__(self, depth: np.ndarray, curves: Dict[str, np.ndarray]):
        self.depth = depth
        self.curves = curves
        self._validate_data()

    def _validate_data(self):
        if self.depth is None or len(self.depth) == 0:
            raise ValueError("Depth data is required and cannot be empty")
        
        if not self.curves:
            raise ValueError("No curves available for plotting")

        for curve_name, curve_data in self.curves.items():
            if len(curve_data) != len(self.depth):
                raise ValueError(f"Curve '{curve_name}' has length {len(curve_data)}, expected {len(self.depth)}")

    def plot_single_curve(self, curve_name: str, processed_curve: Optional[np.ndarray] = None, 
                          figsize: Tuple[int, int] = (8, 10)) -> plt.Figure:
        if curve_name not in self.curves:
            raise ValueError(f"Curve '{curve_name}' not found")

        fig, ax = plt.subplots(figsize=figsize)
        
        ax.plot(self.curves[curve_name], self.depth, label='原始曲线', color='blue', linewidth=1.5)
        
        if processed_curve is not None:
            if len(processed_curve) != len(self.depth):
                raise ValueError(f"Processed curve has length {len(processed_curve)}, expected {len(self.depth)}")
            ax.plot(processed_curve, self.depth, label='处理后曲线', color='red', linewidth=1.5, linestyle='--')

        ax.set_xlabel(curve_name)
        ax.set_ylabel('深度 (m)')
        ax.set_title(f'测井曲线: {curve_name}')
        
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        return fig

    def plot_multiple_curves(self, curve_names: List[str], processed_curves: Optional[Dict[str, np.ndarray]] = None,
                             figsize: Tuple[int, int] = None) -> plt.Figure:
        if not curve_names:
            raise ValueError("No curve names provided")

        if figsize is None:
            figsize = (3 * len(curve_names), 10)

        fig, axes = plt.subplots(ncols=len(curve_names), figsize=figsize, sharey=True)
        
        if len(curve_names) == 1:
            axes = [axes]

        for i, curve_name in enumerate(curve_names):
            if curve_name not in self.curves:
                raise ValueError(f"Curve '{curve_name}' not found")

            ax = axes[i]
            ax.plot(self.curves[curve_name], self.depth, label='原始曲线', color='blue', linewidth=1.5)

            if processed_curves and curve_name in processed_curves:
                processed_curve = processed_curves[curve_name]
                if len(processed_curve) != len(self.depth):
                    raise ValueError(f"Processed curve '{curve_name}' has length {len(processed_curve)}, expected {len(self.depth)}")
                ax.plot(processed_curve, self.depth, label='处理后曲线', color='red', linewidth=1.5, linestyle='--')

            ax.set_xlabel(curve_name)
            ax.set_title(curve_name)
            ax.grid(True, alpha=0.3)
            ax.legend()

        axes[0].set_ylabel('深度 (m)')
        axes[0].invert_yaxis()
        
        plt.tight_layout()
        return fig

    def plot_full_view(self, processed_curves: Optional[Dict[str, np.ndarray]] = None,
                       figsize: Tuple[int, int] = None) -> plt.Figure:
        curve_names = list(self.curves.keys())
        return self.plot_multiple_curves(curve_names, processed_curves, figsize)
