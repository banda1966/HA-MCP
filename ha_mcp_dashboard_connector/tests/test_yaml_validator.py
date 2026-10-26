import unittest
from unittest.mock import patch

class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Keep unit tests runnable without downloading the MCP SDK.
        import sys, types
        mcp = types.ModuleType("mcp")
        server = types.ModuleType("mcp.server")
        fastmcp = types.ModuleType("mcp.server.fastmcp")
        class FakeFastMCP:
            def __init__(self, *a, **k): pass
            def tool(self): return lambda fn: fn
            def streamable_http_app(self): return None
        fastmcp.FastMCP = FakeFastMCP
        sys.modules.setdefault("mcp", mcp)
        sys.modules.setdefault("mcp.server", server)
        sys.modules.setdefault("mcp.server.fastmcp", fastmcp)
        import src.server as server_module
        cls.server_module = server_module

    def test_valid_dashboard(self):
        result = self.server_module.validate_dashboard_yaml("title: Home\nviews:\n  - title: Overview\n    path: overview\n    cards: []\n")
        self.assertTrue(result["valid"])

    def test_duplicate_paths_rejected(self):
        result = self.server_module.validate_dashboard_yaml("views:\n  - title: A\n    path: same\n    cards: []\n  - title: B\n    path: same\n    cards: []\n")
        self.assertFalse(result["valid"])
        self.assertIn("Duplicate view path: same", result["errors"])

    def test_invalid_yaml_rejected(self):
        result = self.server_module.validate_dashboard_yaml("views: [\n")
        self.assertFalse(result["valid"])

if __name__ == "__main__":
    unittest.main()
