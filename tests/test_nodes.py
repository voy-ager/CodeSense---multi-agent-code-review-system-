# tests/test_nodes.py — run: python -m unittest discover tests

import unittest
from unittest.mock import patch, MagicMock

from agent import nodes


def fake_llm(content=None, exc=None):
    llm = MagicMock()
    if exc:
        llm.invoke.side_effect = exc
    else:
        llm.invoke.return_value = MagicMock(content=content)
    return llm


class CallAgentTests(unittest.TestCase):
    def test_parses_fenced_json_and_tags_agent(self):
        with patch.object(nodes, "llm", fake_llm('```json\n[{"severity": "high"}]\n```')):
            out = nodes.call_agent("p", "security", "security_findings")
        self.assertEqual(out, {"security_findings": [{"severity": "high", "agent": "security"}]})

    def test_llm_error_marks_agent_failed(self):
        with patch.object(nodes, "llm", fake_llm(exc=RuntimeError("model_not_found"))):
            out = nodes.call_agent("p", "style", "style_findings")
        self.assertEqual(out, {"failed_agents": ["style"]})

    def test_bad_json_marks_agent_failed(self):
        with patch.object(nodes, "llm", fake_llm("not json")):
            out = nodes.call_agent("p", "testing", "test_findings")
        self.assertEqual(out, {"failed_agents": ["testing"]})


class SynthesizeTests(unittest.TestCase):
    def test_all_agents_failed_is_an_error_not_a_clean_pr(self):
        out = nodes.synthesize({"pr_url": "u", "failed_agents": ["security", "performance", "testing", "style"]})
        self.assertIn("error", out)

    def test_partial_failure_is_reported(self):
        out = nodes.synthesize({
            "pr_url": "u",
            "security_findings": [{"severity": "low"}, {"severity": "critical"}],
            "failed_agents": ["style"],
        })
        report = out["final_report"]
        self.assertEqual(report["findings"][0]["severity"], "critical")
        self.assertEqual(report["failed_agents"], ["style"])
        self.assertIn("Incomplete", report["summary"])


if __name__ == "__main__":
    unittest.main()
