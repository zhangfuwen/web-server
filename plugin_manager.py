import os
import importlib.util
import json

class Plugin:
    def __init__(self, name, version, description):
        self.name = name
        self.version = version
        self.description = description
    
    def on_startup(self, app):
        """Called when server starts."""
        pass
    
    def on_request(self, request):
        """Called on each request."""
        pass
    
    def on_shutdown(self):
        """Called when server stops."""
        pass

class PluginManager:
    def __init__(self, plugins_dir='plugins'):
        self.plugins_dir = plugins_dir
        self.plugins = {}
    
    def load_plugins(self):
        """Load all plugins from plugins directory."""
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            return
        
        for name in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, name, 'plugin.py')
            if os.path.exists(plugin_path):
                self.load_plugin(name, plugin_path)
    
    def load_plugin(self, name, path):
        """Load a single plugin."""
        spec = importlib.util.spec_from_file_location(f"plugins.{name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'plugin'):
            self.plugins[name] = module.plugin
    
    def register_routes(self, server):
        """Let plugins register API routes."""
        for name, plugin in self.plugins.items():
            if hasattr(plugin, 'register_routes'):
                plugin.register_routes(server)
    
    def startup(self, server):
        """Call on_startup for all plugins."""
        for plugin in self.plugins.values():
            plugin.on_startup(server)
    
    def shutdown(self):
        """Call on_shutdown for all plugins."""
        for plugin in self.plugins.values():
            plugin.on_shutdown()

# Global instance
plugin_manager = PluginManager()
