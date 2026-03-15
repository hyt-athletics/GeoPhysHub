import pluggy
import importlib.util
import os
from pathlib import Path
from typing import List, Any, Dict, Optional
import numpy as np
from . import hookspecs


class PluginManager:
    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugin_manager = pluggy.PluginManager("geophyshub")
        self.plugin_manager.add_hookspecs(hookspecs)
        self.plugins = {}
        
        if plugin_dir is None:
            plugin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins")
        self.plugin_dir = plugin_dir
        
        self._discover_and_load_plugins()
    
    def _discover_and_load_plugins(self):
        plugin_dir_path = Path(self.plugin_dir)
        if not plugin_dir_path.exists():
            plugin_dir_path.mkdir(parents=True, exist_ok=True)
            return
        
        for plugin_file in plugin_dir_path.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            plugin_name = plugin_file.stem
            try:
                self._load_plugin_from_file(plugin_file, plugin_name)
            except Exception as e:
                print(f"Failed to load plugin {plugin_name}: {e}")
    
    def _load_plugin_from_file(self, plugin_file: Path, plugin_name: str):
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.plugin_manager.register(module, name=plugin_name)
            self.plugins[plugin_name] = module
    
    def get_registered_plugins(self) -> List[str]:
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found")
        
        return {
            "name": plugin_name,
            "module": self.plugins[plugin_name]
        }
    
    def call_get_algo_name(self) -> List[str]:
        results = self.plugin_manager.hook.get_algo_name()
        return [name for name in results if name]
    
    def call_get_param_ui(self) -> List[Dict]:
        results = self.plugin_manager.hook.get_param_ui()
        return [ui for ui in results if ui]
    
    def call_run_algorithm(self, data: np.ndarray, params: Dict) -> np.ndarray:
        results = self.plugin_manager.hook.run_algorithm(data=data, params=params)
        if results:
            return results[0]
        return data
    
    def get_all_algorithms(self) -> List[Dict]:
        algorithms = []
        for plugin_name in self.plugins:
            try:
                algo_name = self._call_plugin_hook(plugin_name, "get_algo_name")
                param_ui = self._call_plugin_hook(plugin_name, "get_param_ui")
                if algo_name:
                    algorithms.append({
                        "name": algo_name,
                        "plugin": plugin_name,
                        "param_ui": param_ui or {}
                    })
            except Exception as e:
                print(f"Error getting info for plugin {plugin_name}: {e}")
        return algorithms
    
    def _call_plugin_hook(self, plugin_name: str, hook_name: str, **kwargs) -> Any:
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return None
        
        hook_func = getattr(plugin, hook_name, None)
        if not hook_func:
            return None
        
        try:
            return hook_func(**kwargs)
        except Exception as e:
            print(f"Error calling {hook_name} on {plugin_name}: {e}")
            return None
