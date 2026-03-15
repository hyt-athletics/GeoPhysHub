import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import numpy as np
from src.plugin_manager import PluginManager
from src.models import GeoPhysDataModel
from src.c_bridge import CBridge


class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.plugin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins")
        self.manager = PluginManager(plugin_dir=self.plugin_dir)
    
    def test_plugin_discovery(self):
        plugins = self.manager.get_registered_plugins()
        self.assertGreater(len(plugins), 0)
        self.assertIn("pure_python_filter", plugins)
        self.assertIn("c_filter_plugin", plugins)
    
    def test_get_algorithms(self):
        algorithms = self.manager.get_all_algorithms()
        self.assertGreater(len(algorithms), 0)
        
        algo_names = [algo["name"] for algo in algorithms]
        self.assertIn("滑动平均滤波 (Python)", algo_names)
        self.assertIn("滑动平均滤波 (C)", algo_names)


class TestFilters(unittest.TestCase):
    def setUp(self):
        self.test_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        self.noisy_data = self.test_data + np.random.normal(0, 0.5, len(self.test_data))
    
    def test_python_filter_basic(self):
        sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins"))
        import pure_python_filter
        
        result = pure_python_filter.run_algorithm(self.test_data, {"window_size": 3})
        self.assertEqual(len(result), len(self.test_data))
        self.assertTrue(np.allclose(result[1:-1], self.test_data[1:-1]))
    
    def test_c_filter_basic(self):
        sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins"))
        import c_filter_plugin
        
        result = c_filter_plugin.run_algorithm(self.test_data, {"window_size": 3})
        self.assertEqual(len(result), len(self.test_data))
        self.assertTrue(np.allclose(result[1:-1], self.test_data[1:-1]))
    
    def test_both_filters_consistency(self):
        sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins"))
        import pure_python_filter
        import c_filter_plugin
        
        window_size = 5
        python_result = pure_python_filter.run_algorithm(self.noisy_data, {"window_size": window_size})
        c_result = c_filter_plugin.run_algorithm(self.noisy_data, {"window_size": window_size})
        
        self.assertTrue(np.allclose(python_result, c_result, rtol=1e-10))


class TestGeoPhysDataModel(unittest.TestCase):
    def test_model_creation(self):
        depth = np.array([100.0, 101.0, 102.0, 103.0, 104.0])
        curves = {
            "GR": np.array([20.0, 25.0, 30.0, 28.0, 22.0]),
            "RHOB": np.array([2.6, 2.65, 2.55, 2.58, 2.62])
        }
        
        model = GeoPhysDataModel(
            well_name="TestWell",
            depth=depth,
            curves=curves
        )
        
        self.assertEqual(model.well_name, "TestWell")
        self.assertEqual(len(model.depth), 5)
        self.assertEqual(len(model.curves), 2)
        self.assertIn("GR", model.curves)
        self.assertIn("RHOB", model.curves)


class TestCBridge(unittest.TestCase):
    def setUp(self):
        self.dll_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "filter.dll")
    
    def test_c_bridge_load_library(self):
        bridge = CBridge()
        bridge.load_library(self.dll_path)
        self.assertTrue(bridge.is_loaded)
    
    def test_c_bridge_function_call(self):
        bridge = CBridge(self.dll_path)
        
        func = bridge.get_function("moving_average_filter")
        
        input_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        output_data = np.zeros_like(input_data)
        
        import ctypes
        func.restype = None
        func.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS"),
            np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS"),
            ctypes.c_int,
            ctypes.c_int
        ]
        
        func(input_data, output_data, len(input_data), 3)
        
        self.assertEqual(len(output_data), len(input_data))


if __name__ == "__main__":
    unittest.main()
