# tests/test_nodes.py — run: python -m unittest discover tests

import unittest
from unittest.mock import patch, MagicMock

from agent import nodes

GOOD = '[{"severity": "high", "file": "a.py", "line": 3, "issue": "Bug", "fix": "Fix it", "category": "Logic"}]'


def fake_llm(content=None, exc=None):
    llm = MagicMock()
    if exc:
        llm.invoke.side_effect = exc
    else:
        llm.invoke.return_value = MagicMock(content=content)
    return llm


class CallAgentTests(unittest.TestCase):
    def call(self, content=None, exc=None, agent="security", key="security_findings"):
        llm = fake_llm(content, exc)
        with patch.object(nodes, "llm", llm):
            return nodes.call_agent("prompt", "n0nce", agent, key), llm

    def test_parses_fenced_json_and_tags_agent(self):
        out, _ = self.call(f"```json\n{GOOD}\n```")
        self.assertEqual(out["security_findings"][0]["agent"], "security")
        self.assertEqual(out["security_findings"][0]["severity"], "high")

    def test_llm_error_marks_agent_failed(self):
        out, _ = self.call(exc=RuntimeError("model_not_found"), agent="style", key="style_findings")
        self.assertEqual(out, {"failed_agents": ["style"]})

    def test_bad_json_marks_agent_failed(self):
        out, _ = self.call("not json", agent="testing", key="test_findings")
        self.assertEqual(out, {"failed_agents": ["testing"]})

    def test_non_array_json_marks_agent_failed(self):
        out, _ = self.call('"just a string"')
        self.assertEqual(out, {"failed_agents": ["security"]})

    def test_system_guard_sent_with_nonce(self):
        _, llm = self.call(GOOD)
        system, human = llm.invoke.call_args.args[0]
        self.assertIn("<<<DIFF-n0nce>>>", system.content)
        self.assertIn("untrusted data", system.content)
        self.assertEqual(human.content, "prompt")


class ValidationTests(unittest.TestCase):
    def test_normalises_and_drops_malformed(self):
        raw = [
            {"severity": "ERROR", "issue": "x", "fix": "y", "line": "12"},   # alias + str line
            {"severity": "bogus", "issue": "x", "fix": "y"},                 # unknown severity
            {"severity": "low", "issue": "  ", "fix": "y"},                  # empty issue
            {"severity": "low", "fix": "y"},                                 # missing issue
            "not a dict",
            {"severity": "warning", "issue": "x", "fix": "y", "line": "abc"},
        ]
        out = nodes.validate_findings(raw)
        self.assertEqual([f["severity"] for f in out], ["high", "medium"])
        self.assertEqual([f["line"] for f in out], [12, 0])

    def test_caps_findings_per_agent(self):
        raw = [{"severity": "low", "issue": f"i{i}", "fix": "f"} for i in range(100)]
        self.assertEqual(len(nodes.validate_findings(raw)), nodes.MAX_FINDINGS_PER_AGENT)


class PromptTests(unittest.TestCase):
    def test_agents_wrap_diff_and_truncate_for_llm(self):
        big = "+x\n" * 10_000
        with patch.object(nodes, "call_agent", return_value={}) as call:
            nodes.security_agent({"raw_diff": big})
        prompt, nonce = call.call_args.args[:2]
        self.assertIn(f"<<<DIFF-{nonce}>>>", prompt)
        self.assertIn(f"<<<END-{nonce}>>>", prompt)
        self.assertIn("[diff truncated]", prompt)
        self.assertLess(len(prompt), nodes.MAX_LLM_DIFF_CHARS + 3000)

    def test_nonce_differs_per_call(self):
        with patch.object(nodes, "call_agent", return_value={}) as call:
            nodes.style_agent({"raw_diff": "+a"})
            nodes.style_agent({"raw_diff": "+a"})
        self.assertNotEqual(call.call_args_list[0].args[1], call.call_args_list[1].args[1])


class SynthesizeTests(unittest.TestCase):
    def test_all_agents_failed_is_an_error_not_a_clean_pr(self):
        out = nodes.synthesize({"pr_url": "u", "failed_agents": ["security", "performance", "testing", "style"]})
        self.assertIn("error", out)

    def test_static_failure_alone_is_not_fatal(self):
        out = nodes.synthesize({"pr_url": "u", "failed_agents": ["static"]})
        self.assertIn("final_report", out)

    def test_partial_failure_is_reported(self):
        out = nodes.synthesize({
            "pr_url": "u",
            "security_findings": [{"severity": "low", "line": 1, "agent": "security"},
                                  {"severity": "critical", "line": 2, "agent": "security"}],
            "failed_agents": ["style"],
        })
        report = out["final_report"]
        self.assertEqual(report["findings"][0]["severity"], "critical")
        self.assertEqual(report["failed_agents"], ["style"])
        self.assertIn("Incomplete", report["summary"])

    def test_dedupes_static_over_llm_and_counts_after_dedupe(self):
        static = {"severity": "critical", "file": "a.py", "line": 4, "category": "Hardcoded Secret",
                  "agent": "security", "source": "static"}
        llm_dup = {"severity": "high", "file": "a.py", "line": 4, "category": "hardcoded secret", "agent": "security"}
        style = {"severity": "low", "file": "a.py", "line": 9, "category": "Naming", "agent": "style"}
        report = nodes.synthesize({"pr_url": "u", "static_findings": [static],
                                   "security_findings": [llm_dup], "style_findings": [style]})["final_report"]
        self.assertEqual(report["total_findings"], 2)
        self.assertEqual(report["findings"][0].get("source"), "static")
        self.assertEqual(report["by_agent"], {"security": 1, "performance": 0, "testing": 0, "style": 1})

    def test_reports_truncation_and_head_sha(self):
        report = nodes.synthesize({"pr_url": "u", "raw_diff": "x" * (nodes.MAX_LLM_DIFF_CHARS + 1),
                                   "pr_metadata": {"head_sha": "abc"}})["final_report"]
        self.assertTrue(report["diff_truncated"])
        self.assertEqual(report["head_sha"], "abc")


if __name__ == "__main__":
    unittest.main()


class QaRegressionTests(unittest.TestCase):
    def call(self, content):
        with patch.object(nodes, "llm", fake_llm(content)):
            return nodes.call_agent("p", "n", "security", "security_findings")

    def test_h2_wrapped_findings_are_unwrapped(self):
        out = self.call('{"findings": ' + GOOD + '}')
        self.assertEqual(len(out["security_findings"]), 1)

    def test_h2_all_malformed_output_is_a_failure_not_clean(self):
        self.assertEqual(self.call('[{"severity": "urgent-ish", "issue": "x", "fix": "y"}, {"nope": 1}]'),
                         {"failed_agents": ["security"]})
        self.assertEqual(self.call('{"result": "looks fine"}'), {"failed_agents": ["security"]})

    def test_h2_empty_array_is_still_a_clean_result(self):
        self.assertEqual(self.call("[]"), {"security_findings": []})

    def test_h2_severity_punctuation_normalised(self):
        out = nodes.validate_findings([{"severity": "Critical!", "issue": "x", "fix": "y"}])
        self.assertEqual(out[0]["severity"], "critical")

    def test_m5_static_findings_survive_total_llm_failure(self):
        secret = {"severity": "critical", "file": "a.py", "line": 1, "category": "Hardcoded Secret",
                  "agent": "security", "source": "static", "issue": "AWS key", "fix": "rotate"}
        out = nodes.synthesize({"pr_url": "u", "static_findings": [secret],
                                "failed_agents": ["security", "performance", "testing", "style"]})
        report = out["final_report"]
        self.assertEqual(report["findings"][0]["category"], "Hardcoded Secret")
        self.assertIn("Incomplete", report["summary"])

    def test_m6_distinct_issues_without_line_or_category_are_kept(self):
        a = {"severity": "critical", "file": "app.py", "line": 0, "category": "", "issue": "SQL injection", "agent": "security"}
        b = {"severity": "high", "file": "app.py", "line": 0, "category": "", "issue": "eval() on input", "agent": "security"}
        self.assertEqual(nodes.synthesize({"pr_url": "u", "security_findings": [a, b]})["final_report"]["total_findings"], 2)

    def test_m6_merge_keeps_highest_severity(self):
        static = {"severity": "high", "file": "a.py", "line": 4, "category": "Hardcoded Secret", "agent": "security", "source": "static"}
        llm = {"severity": "critical", "file": "a.py", "line": 4, "category": "hardcoded secret", "agent": "security"}
        f = nodes.synthesize({"pr_url": "u", "static_findings": [static], "security_findings": [llm]})["final_report"]["findings"]
        self.assertEqual((len(f), f[0]["severity"], f[0]["source"]), (1, "critical", "static"))
