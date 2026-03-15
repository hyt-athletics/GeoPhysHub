import pluggy
import numpy as np

hookspec = pluggy.HookspecMarker("geophyshub")


@hookspec
def get_algo_name() -> str:
    """返回算法名称"""
    pass


@hookspec
def get_param_ui() -> dict:
    """返回算法参数的UI配置字典"""
    pass


@hookspec
def run_algorithm(data: np.ndarray, params: dict) -> np.ndarray:
    """
    执行算法
    
    Args:
        data: 输入数据
        params: 算法参数字典
        
    Returns:
        处理后的数据
    """
    pass
