# Molt Server Plugin System

## Overview

The Molt Server plugin system allows developers to extend server functionality without modifying the core codebase. Plugins can hook into server lifecycle events and register custom API routes.

## Architecture

### Plugin Manager

The `PluginManager` class (in `plugin_manager.py`) handles:
- **Discovery**: Automatically finds plugins in the `plugins/` directory
- **Loading**: Dynamically loads plugin modules at startup
- **Lifecycle Management**: Calls startup/shutdown hooks
- **Route Registration**: Allows plugins to register API endpoints

### Plugin Lifecycle

1. **Load** (`load_plugins()`): Scans `plugins/` directory and loads all valid plugins
2. **Register Routes** (`register_routes()`): Plugins can add custom API endpoints
3. **Startup** (`startup()`): Called when server starts - plugins can initialize resources
4. **Request** (`on_request()`): Called on each request - plugins can intercept/modify
5. **Shutdown** (`shutdown()`): Called when server stops - plugins can cleanup

## Plugin Development Guide

### Creating a Plugin

1. Create a directory in `plugins/` with your plugin name:
   ```
   plugins/
   └── myplugin/
       └── plugin.py
   ```

2. Create `plugin.py` with your plugin class:

```python
from plugin_manager import Plugin

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__(
            name='myplugin',
            version='1.0.0',
            description='My custom plugin'
        )
    
    def on_startup(self, server):
        """Called when server starts."""
        print(f"[MyPlugin] Starting up...")
        # Initialize resources, connections, etc.
    
    def on_request(self, request):
        """Called on each request."""
        # Log, modify, or intercept requests
        pass
    
    def on_shutdown(self):
        """Called when server stops."""
        print(f"[MyPlugin] Shutting down...")
        # Cleanup resources
    
    def register_routes(self, server):
        """Register custom API routes."""
        # Add custom endpoints to the server
        pass

# Required: expose plugin instance as 'plugin'
plugin = MyPlugin()
```

### Plugin Base Class

All plugins inherit from the `Plugin` base class which provides:
- `name`: Plugin identifier
- `version`: Version string
- `description`: Human-readable description

### Available Hooks

| Hook | When Called | Purpose |
|------|-------------|---------|
| `on_startup(server)` | Server startup | Initialize resources, start background tasks |
| `on_request(request)` | Every HTTP request | Logging, authentication, request modification |
| `on_shutdown()` | Server shutdown | Cleanup, save state, close connections |
| `register_routes(server)` | After server init | Add custom API endpoints |

### Example: Adding a Custom API Route

```python
from plugin_manager import Plugin
import json

class APIPlugin(Plugin):
    def __init__(self):
        super().__init__(
            name='api',
            version='1.0.0',
            description='Custom API endpoints'
        )
    
    def register_routes(self, server):
        # Note: You'll need to extend the request handler
        # to support dynamic route registration
        pass
    
    def on_startup(self, server):
        print("[API Plugin] Custom endpoints ready")
```

## Best Practices

1. **Error Handling**: Always wrap plugin code in try/except to prevent crashes
2. **Logging**: Use the server's logger for consistent logging
3. **Resources**: Clean up all resources in `on_shutdown()`
4. **Dependencies**: List plugin dependencies in a `requirements.txt` in your plugin folder
5. **Versioning**: Use semantic versioning for your plugin

## Plugin Directory Structure

```
plugins/
├── __init__.py              # Package marker
├── README.md                # Plugin development guide
├── botreports/              # Example plugin
│   └── plugin.py
└── myplugin/                # Your plugin
    ├── plugin.py            # Main plugin code
    ├── requirements.txt     # Plugin-specific dependencies
    └── README.md            # Plugin documentation
```

## Loading Order

Plugins are loaded in alphabetical order by directory name. If plugins depend on each other, name them accordingly (e.g., `01_base`, `02_extended`).

## Debugging

To debug plugins:
1. Check server logs for load errors
2. Verify `plugin` variable is exposed in your `plugin.py`
3. Ensure your plugin directory contains `plugin.py`

## Security Considerations

- Plugins run with the same permissions as the server
- Review plugin code before deploying to production
- Consider sandboxing untrusted plugins
