# Molt Server Plugins

This directory contains plugins that extend Molt Server functionality.

## Quick Start

### Creating Your First Plugin

1. **Create a plugin directory:**
   ```bash
   mkdir -p plugins/myplugin
   ```

2. **Create `plugin.py`:**
   ```python
   from plugin_manager import Plugin

   class MyPlugin(Plugin):
       def __init__(self):
           super().__init__(
               name='myplugin',
               version='1.0.0',
               description='My first plugin'
           )
       
       def on_startup(self, server):
           print(f"[MyPlugin] Started!")
       
       def on_shutdown(self):
           print(f"[MyPlugin] Goodbye!")

   plugin = MyPlugin()
   ```

3. **Restart the server** - Your plugin will be automatically loaded!

## Plugin Structure

```
myplugin/
└── plugin.py    # Required: Main plugin code
```

### Required Elements

- **`plugin.py`**: Must exist in your plugin directory
- **`plugin` variable**: Must expose your plugin instance at module level

### Plugin Template

```python
from plugin_manager import Plugin

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__(
            name='myplugin',           # Unique identifier
            version='1.0.0',           # Semantic version
            description='Description'  # What your plugin does
        )
    
    def on_startup(self, server):
        """Called when server starts."""
        # Initialize your plugin
        pass
    
    def on_request(self, request):
        """Called on each HTTP request."""
        # Optional: intercept/modify requests
        pass
    
    def on_shutdown(self):
        """Called when server stops."""
        # Cleanup resources
        pass
    
    def register_routes(self, server):
        """Register custom API routes."""
        # Add custom endpoints
        pass

# IMPORTANT: Expose plugin instance
plugin = MyPlugin()
```

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| botreports | BotReports integration | 1.0.0 |

## Development Tips

1. **Test incrementally**: Start with `on_startup()` to verify loading
2. **Use logging**: Print statements appear in server logs
3. **Check the example**: See `botreports/plugin.py` for a working example
4. **Read the docs**: See `docs/PLUGIN_SYSTEM.md` for detailed guide

## Troubleshooting

**Plugin not loading?**
- Ensure directory name matches plugin name
- Check that `plugin.py` exists
- Verify `plugin` variable is defined at module level
- Check server logs for errors

**Import errors?**
- Use relative imports from `plugin_manager`
- Avoid circular imports

## Contributing

When creating plugins:
- Use semantic versioning
- Include a description
- Clean up resources in `on_shutdown()`
- Document your plugin's features

---

For detailed documentation, see `docs/PLUGIN_SYSTEM.md`
