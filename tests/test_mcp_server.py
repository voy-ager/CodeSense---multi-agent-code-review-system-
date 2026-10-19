# tests/test_mcp_server.py — run: python -m unittest discover tests

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import mcp
from mcp import StdioServerParameters

import mcp_server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class InProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_is_listed_read_only(self):
        tools = await mcp_server.server.list_tools()
        tool = next(t for t in tools if t.name == "review_pull_request")
        self.assertTrue(tool.annotations.read_only_hint)
        self.assertIn("pr_url", tool.input_schema["properties"])

    async def test_rejects_non_github_urls(self):
        async with mcp.Client(mcp_server.server) as client:
            result = await client.call_tool("review_pull_request", {"pr_url": "https://evil.com/pull/1"})
        self.assertTrue(result.is_error)
        self.assertIn("GitHub pull request", result.content[0].text)

    async def test_returns_report_for_canonical_url(self):
        graph = MagicMock()
        graph.ainvoke = AsyncMock(return_value={"final_report": {"total_findings": 2}})
        with patch.object(mcp_server, "_graph", graph):
            async with mcp.Client(mcp_server.server) as client:
                result = await client.call_tool("review_pull_request",
                                                {"pr_url": "https://github.com/psf/requests/pull/6746/files"})
        self.assertFalse(result.is_error)
        self.assertEqual(graph.ainvoke.call_args.args[0]["pr_url"], "https://github.com/psf/requests/pull/6746")
        self.assertEqual(result.structured_content["total_findings"], 2)


class StdioTests(unittest.TestCase):
    def test_server_speaks_mcp_over_stdio(self):
        """Spawns the real server process: proves nothing pollutes stdout."""
        async def run():
            params = StdioServerParameters(command=sys.executable, args=[os.path.join(ROOT, "mcp_server.py")], cwd=ROOT)
            async with mcp.Client(params) as client:
                return [t.name for t in (await client.list_tools()).tools]
        self.assertEqual(asyncio.run(asyncio.wait_for(run(), 60)), ["review_pull_request"])


class MissingKeyTests(unittest.TestCase):
    def test_server_starts_without_groq_key(self):
        """Regression (first CI run): the MCP SDK starts servers with a minimal environment,
        so a missing GROQ_API_KEY must not crash the server at import time."""
        env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
        code = ("import os, sys; os.environ.pop('GROQ_API_KEY', None); "
                "import dotenv; dotenv.load_dotenv = lambda *a, **k: False; "   # ignore any local .env
                "import mcp_server; print('imported')")
        import subprocess
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-500:])
        self.assertIn("imported", out.stdout)


if __name__ == "__main__":
    unittest.main()
