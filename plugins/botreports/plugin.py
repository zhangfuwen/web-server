from plugin_manager import Plugin

class BotReportsPlugin(Plugin):
    def __init__(self):
        super().__init__(
            name='botreports',
            version='1.0.0',
            description='BotReports integration plugin'
        )
    
    def on_startup(self, server):
        print(f"[BotReports Plugin] Started, version {self.version}")
    
    def register_routes(self, server):
        # Already implemented in main server, just for demo
        pass

plugin = BotReportsPlugin()
