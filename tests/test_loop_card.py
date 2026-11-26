"""loop_card(): a session's sub-agent logs as detail.loop (Rumble runs and generic sub-agent loops).

All sessions are synthetic, built in a temp dir. Nothing reads ~/.claude.
"""

import builtins
import importlib.machinery
import importlib.util
import json
import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timezone
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_loader = importlib.machinery.SourceFileLoader("entropy", os.path.join(ROOT, "bin", "entropy"))
_spec = importlib.util.spec_from_loader("entropy", _loader)
entropy = importlib.util.module_from_spec(_spec)
_loader.exec_module(entropy)

T0 = 1_790_000_000  # fixed epoch; every event is T0 + offset seconds


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def review_report(n, verdict, findings=(), withdrawn="none", unresolved="none"):
    lines = [f"## Review — round {n}", f"Verdict: {verdict}", "", "Testing strategy:",
             "- New server logic ships with tests: met", "Test integrity: clean",
             "Checks run: python3 -m unittest: pass", "", "Findings:"]
    lines += [f"- {f}" for f in findings] or ["none"]
    lines += ["Test disputes: none", "", f"Withdrawn: {withdrawn}", f"Unresolved: {unresolved}"]
    return "\n".join(lines)


def impl_report(n, addressed="none"):
    return "\n".join([f"## Implementer report — round {n}", "Changed: bin/entropy — loop_card",
                      "Tests added/changed: none", "Test evidence: none", "Test changes: none",
                      "Commands run: gate: pass", "Not run: none", f"Findings addressed: {addressed}",
                      "Test disputes: none", "Assumptions: none", "Open concerns: none"])


def tw_report(n, red=("tests/test_x.py::test_a — red (missing)",), addressed="none"):
    return "\n".join([f"## Test-writer report — round {n}", "Files: tests/test_x.py",
                      "Tests: tests/test_x.py::test_a — criterion 1", "Red evidence: " + "\n".join(red),
                      "Not covered: none", "Test changes: none", "Commands run: unittest: fail",
                      f"Findings addressed: {addressed}", "Assumptions: none", "Open concerns: none"])


class Session:
    """A synthetic <session>.jsonl with <session>/subagents/agent-<id>.{jsonl,meta.json}, plus a parent
    Transcript whose pending / agent_results say which foreground agents are still running."""

    def __init__(self, tmp, name="sess"):
        self.path = os.path.join(tmp, name + ".jsonl")
        self.dir = os.path.join(tmp, name, "subagents")
        os.makedirs(self.dir)
        open(self.path, "w").close()
        self.tr = entropy.Transcript(self.path)
        self.n = 0

    def agent(self, agent_type, description, at, report=None, running=False, tools=2,
              as_text=False, meta=True, extra_lines=()):
        """Write one sub-agent. `report` goes in a SubagentHandback (or a final assistant text if as_text)."""
        self.n += 1
        aid = f"a{self.n:02d}{agent_type.replace(':', '').replace('-', '')}"
        use = f"toolu_{aid}"
        lines = [{"type": "user", "timestamp": iso(at), "message": {"role": "user", "content": description}}]
        t = at
        for i in range(tools):
            t += 5
            lines.append({"type": "assistant", "timestamp": iso(t), "message": {
                "role": "assistant", "stop_reason": "tool_use",
                "content": [{"type": "tool_use", "id": f"{aid}_t{i}", "name": "Bash", "input": {"command": "ls"}}]}})
            t += 1
            lines.append({"type": "user", "timestamp": iso(t), "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": f"{aid}_t{i}", "content": "ok"}]}})
        lines += list(extra_lines)
        if report is not None:
            t += 5
            if as_text:
                lines.append({"type": "assistant", "timestamp": iso(t), "message": {
                    "role": "assistant", "stop_reason": "end_turn", "content": [{"type": "text", "text": report}]}})
            else:
                lines.append({"type": "assistant", "timestamp": iso(t), "message": {
                    "role": "assistant", "stop_reason": "tool_use", "content": [
                        {"type": "tool_use", "id": f"{aid}_h", "name": "SubagentHandback", "input": {"message": report}}]}})
        p = os.path.join(self.dir, f"agent-{aid}.jsonl")
        with open(p, "w") as fh:
            for ln in lines:
                fh.write((ln if isinstance(ln, str) else json.dumps(ln)) + "\n")
        if meta:
            with open(p[:-6] + ".meta.json", "w") as fh:
                if isinstance(meta, str):
                    fh.write(meta)
                else:
                    json.dump({"agentType": agent_type, "description": description, "toolUseId": use,
                               "requestShape": "foreground"}, fh)
        if running:
            self.tr.pending[use] = ("Agent", {"description": description})
        else:
            self.tr.agent_results[use] = False
        return f"agent-{aid}"

    def loop(self, now=None):
        logs = entropy.session_subagents(self.path)
        return entropy.loop_card(logs, self.tr, now or time.time())


def rounds_of(loop):
    rs = loop["rounds"]
    return list(rs.values()) if isinstance(rs, dict) else rs


def verdict_of(rnd):
    rv = rnd.get("reviewer") or {}
    return rnd.get("verdict") or rv.get("verdict")


def findings_of(rnd):
    rv = rnd.get("reviewer") or {}
    return rv.get("findings") if rv.get("findings") is not None else rnd.get("findings")


def ledger(loop):
    f = loop["findings"]
    return f if isinstance(f, dict) else {e["id"]: e for e in f}


def lanes_of(loop):
    lanes = loop["lanes"]
    if isinstance(lanes, dict):
        return {k: (v.get("agents") if isinstance(v, dict) else v) for k, v in lanes.items()}
    out = {}
    for ln in lanes:
        key = next(ln[k] for k in ("agent_type", "agentType", "type", "name") if k in ln)
        out[key] = ln.get("agents") or ln.get("slots")
    return out


R1_FINDINGS = [
    "R1.1 [blocking] [implementer] bin/entropy:420 — loop_card drops round 2. Group by description.",
    "R1.2 [blocking] [test-writer] tests/test_loop_card.py:88 — asserts nothing. Check the verdict.",
    "R1.3 [nit] [implementer] web/index.html:12 — stray space. Remove it.",
]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="entropy-loop-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.s = Session(self.tmp)

    def two_rounds(self, r2_review="APPROVE", r2_running=False, r2_withdrawn="none", r2_unresolved="none"):
        s = self.s
        ids = {}
        ids["tw1"] = s.agent("rumble:test-writer", "Write tests Unit 1 round 1", T0, tw_report(1))
        ids["im1"] = s.agent("rumble:implementer", "Implement Unit 1 round 1", T0 + 100, impl_report(1))
        ids["rv1"] = s.agent("rumble:reviewer", "Review Unit 1 round 1", T0 + 200,
                             review_report(1, "CHANGES_REQUESTED", R1_FINDINGS))
        ids["tw2"] = s.agent("rumble:test-writer", "Fix tests Unit 1 round 2", T0 + 300,
                             tw_report(2, addressed="R1.2: disputed — the assertion checks the verdict already"))
        ids["im2"] = s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 400,
                             impl_report(2, addressed="R1.1: fixed"))
        if r2_running:
            ids["rv2"] = s.agent("rumble:reviewer", "Review Unit 1 round 2", T0 + 500, None, running=True)
        else:
            ids["rv2"] = s.agent("rumble:reviewer", "Review Unit 1 round 2", T0 + 500,
                                 review_report(2, r2_review, withdrawn=r2_withdrawn, unresolved=r2_unresolved))
        return ids


class TestRumbleRounds(Base):
    """Criterion 1: a 2-round split Rumble run -> kind rumble, 2 rounds, slots, verdict and findings parsed."""

    def test_kind_rounds_and_slots(self):  # criterion 1
        ids = self.two_rounds()
        loop = self.s.loop()
        self.assertEqual(loop["kind"], "rumble")
        rs = rounds_of(loop)
        self.assertEqual(len(rs), 2)
        for i, rnd in enumerate(rs, 1):
            for slot, key in (("test_writer", "tw"), ("implementer", "im"), ("reviewer", "rv")):
                self.assertIsInstance(rnd.get(slot), dict, f"round {i} {slot}")
                self.assertIn(rnd[slot]["id"], (ids[f"{key}{i}"], ids[f"{key}{i}"].removeprefix("agent-")))
                self.assertEqual(rnd[slot]["status"], "done")
                self.assertEqual(rnd[slot]["tools"], 3)  # 2 Bash + the handback
                self.assertIsNotNone(rnd[slot]["started_at"])
                self.assertIn("elapsed_s", rnd[slot])
        self.assertEqual(loop["round"], 2)
        self.assertEqual(loop["max_rounds"], 4)
        self.assertEqual(loop["mode"], "split")

    def test_reviewer_verdict_and_findings_parsed(self):  # criterion 1
        self.two_rounds()
        r1, r2 = rounds_of(self.s.loop())
        self.assertEqual(verdict_of(r1), "CHANGES_REQUESTED")
        self.assertEqual(verdict_of(r2), "APPROVE")
        f1 = findings_of(r1)
        self.assertEqual([f["id"] for f in f1], ["R1.1", "R1.2", "R1.3"])
        by = {f["id"]: f for f in f1}
        self.assertEqual(by["R1.1"]["severity"], "blocking")
        self.assertEqual(by["R1.1"]["owner"], "implementer")
        self.assertEqual(by["R1.2"]["owner"], "test-writer")
        self.assertEqual(by["R1.3"]["severity"], "nit")
        self.assertFalse(findings_of(r2))

    def test_ledger_entries(self):  # criterion 1 (findings ledger)
        self.two_rounds()
        led = ledger(self.s.loop())
        self.assertEqual(set(led), {"R1.1", "R1.2", "R1.3"})
        self.assertEqual(led["R1.1"]["severity"], "blocking")
        self.assertEqual(led["R1.2"]["owner"], "test-writer")
        self.assertEqual(led["R1.3"]["severity"], "nit")

    def test_report_from_final_assistant_text(self):  # criterion 1 (handback fallback)
        s = self.s
        s.agent("rumble:implementer", "Implement Unit 1 round 1", T0, impl_report(1), as_text=True)
        s.agent("rumble:reviewer", "Review Unit 1 round 1", T0 + 100,
                review_report(1, "CHANGES_REQUESTED", R1_FINDINGS[:1]), as_text=True)
        loop = s.loop()
        (r1,) = rounds_of(loop)
        self.assertEqual(verdict_of(r1), "CHANGES_REQUESTED")
        self.assertEqual([f["id"] for f in findings_of(r1)], ["R1.1"])
        self.assertEqual(loop["mode"], "inline")

    def test_latest_handback_wins(self):  # criterion 1 (latest SubagentHandback)
        s = self.s
        first = {"type": "assistant", "timestamp": iso(T0 + 30), "message": {
            "role": "assistant", "stop_reason": "tool_use", "content": [
                {"type": "tool_use", "id": "h0", "name": "SubagentHandback",
                 "input": {"message": review_report(1, "APPROVE")}}]}}
        s.agent("rumble:reviewer", "Review Unit 1 round 1", T0,
                review_report(1, "CHANGES_REQUESTED", R1_FINDINGS[:1]), extra_lines=[first])
        (r1,) = rounds_of(s.loop())
        self.assertEqual(verdict_of(r1), "CHANGES_REQUESTED")

    def test_round_from_report_heading_when_description_has_none(self):  # criterion 1 (grouping fallback)
        s = self.s
        s.agent("rumble:implementer", "Implement Unit 1", T0, impl_report(1))
        s.agent("rumble:reviewer", "Review Unit 1", T0 + 100, review_report(1, "CHANGES_REQUESTED", R1_FINDINGS))
        s.agent("rumble:implementer", "Implement Unit 1 again", T0 + 200, impl_report(2, "R1.1: fixed"))
        s.agent("rumble:reviewer", "Review Unit 1 again", T0 + 300, review_report(2, "APPROVE"))
        rs = rounds_of(s.loop())
        self.assertEqual(len(rs), 2)
        self.assertEqual(verdict_of(rs[0]), "CHANGES_REQUESTED")
        self.assertEqual(verdict_of(rs[1]), "APPROVE")

    def test_round_from_spawn_order_without_any_round(self):  # criterion 1 (grouping fallback)
        s = self.s
        s.agent("rumble:implementer", "Implement", T0, "done")
        s.agent("rumble:reviewer", "Review", T0 + 100, "Verdict: CHANGES_REQUESTED")
        s.agent("rumble:implementer", "Implement", T0 + 200, "done")
        s.agent("rumble:reviewer", "Review", T0 + 300, None, running=True)
        loop = s.loop()
        rs = rounds_of(loop)
        self.assertEqual(len(rs), 2)
        self.assertEqual(rs[1]["implementer"]["status"], "done")
        self.assertEqual(rs[1]["reviewer"]["status"], "running")
        self.assertEqual(loop["round"], 2)

    def test_any_rumble_agent_makes_it_rumble(self):  # criterion 1 (detection)
        s = self.s
        s.agent("general-purpose", "Explore the repo", T0, "found it")
        s.agent("rumble:reviewer", "Review Unit 1 round 1", T0 + 100, review_report(1, "APPROVE"))
        self.assertEqual(s.loop()["kind"], "rumble")


class TestFindingStatus(Base):
    """Criterion 2: ledger status follows later reports."""

    def test_fixed_disputed_withdrawn(self):  # criterion 2
        self.two_rounds(r2_review="CHANGES_REQUESTED", r2_withdrawn="R1.3 — moot after the rewrite")
        led = ledger(self.s.loop())
        self.assertEqual(led["R1.1"]["status"], "fixed")
        self.assertEqual(led["R1.2"]["status"], "disputed")
        self.assertEqual(led["R1.3"]["status"], "withdrawn")

    def test_fixed_while_reviewer_still_running(self):  # criterion 2
        self.two_rounds(r2_running=True)
        led = ledger(self.s.loop())
        self.assertEqual(led["R1.1"]["status"], "fixed")
        self.assertEqual(led["R1.3"]["status"], "open")

    def test_unresolved_and_first_round(self):  # criterion 2 (ledger statuses)
        self.two_rounds(r2_review="CHANGES_REQUESTED", r2_unresolved="R1.2 — needs a human call on scope")
        led = ledger(self.s.loop())
        self.assertEqual(led["R1.2"]["status"], "unresolved")
        e = led["R1.1"]
        self.assertEqual(e.get("first_round", e.get("round")), 1)


class TestResult(Base):
    """Criterion 3: run result."""

    def rounds(self, n, last_verdict):
        s, t = self.s, T0
        for r in range(1, n + 1):
            s.agent("rumble:implementer", f"Implement Unit 1 round {r}", t, impl_report(r))
            v = last_verdict if r == n else "CHANGES_REQUESTED"
            f = [] if v == "APPROVE" else [f"R{r}.1 [blocking] bin/entropy:1 — broken. Fix it."]
            s.agent("rumble:reviewer", f"Review Unit 1 round {r}", t + 50, review_report(r, v, f))
            t += 100

    def test_round_4_changes_requested_needs_human(self):  # criterion 3
        self.rounds(4, "CHANGES_REQUESTED")
        loop = self.s.loop()
        self.assertEqual(loop["round"], 4)
        self.assertEqual(loop["result"], "needs_human")

    def test_approve_is_approved(self):  # criterion 3
        self.rounds(1, "APPROVE")
        self.assertEqual(self.s.loop()["result"], "approved")

    def test_approve_after_changes_is_approved(self):  # criterion 3
        self.rounds(3, "APPROVE")
        self.assertEqual(self.s.loop()["result"], "approved")

    def test_reviewer_running_is_running(self):  # criterion 3
        self.two_rounds(r2_running=True)
        loop = self.s.loop()
        self.assertEqual(loop["result"], "running")
        self.assertEqual(rounds_of(loop)[1]["reviewer"]["status"], "running")

    def test_round_1_changes_requested_not_needs_human(self):  # criterion 3 (needs_human only at round 4)
        self.rounds(1, "CHANGES_REQUESTED")
        self.assertEqual(self.s.loop()["result"], "changes_requested")


class TestGenericAndNull(Base):
    """Criterion 4: non-Rumble sub-agents -> kind agents, lanes by agentType; none -> null."""

    def test_lanes_by_agent_type(self):  # criterion 4
        s = self.s
        e1 = s.agent("Explore", "Find the socket code", T0, "found")
        e2 = s.agent("Explore", "Find the sidebar code", T0 + 10, "found")
        g1 = s.agent("general-purpose", "Write the parser", T0 + 20, None, running=True)
        loop = s.loop()
        self.assertEqual(loop["kind"], "agents")
        lanes = lanes_of(loop)
        self.assertEqual(set(lanes), {"Explore", "general-purpose"})
        self.assertEqual([a["id"] in (e1, e1.removeprefix("agent-")) or a["id"] in (e2, e2.removeprefix("agent-"))
                          for a in lanes["Explore"]], [True, True])
        (g,) = lanes["general-purpose"]
        self.assertIn(g["id"], (g1, g1.removeprefix("agent-")))
        self.assertEqual(g["status"], "running")
        self.assertEqual({a["status"] for a in lanes["Explore"]}, {"done"})
        self.assertNotIn("rounds", loop)
        self.assertFalse(loop.get("findings"))

    def test_no_subagents_is_none(self):  # criterion 4
        self.assertIsNone(entropy.loop_card([], self.s.tr, time.time()))
        self.assertIsNone(self.s.loop())

    def test_tr_none_allowed(self):  # criterion 4 (tr may be None)
        self.s.agent("Explore", "Look around", T0, "found", as_text=True)
        loop = entropy.loop_card(entropy.session_subagents(self.s.path), None, time.time())
        self.assertEqual(loop["kind"], "agents")


class TestMalformed(Base):
    """Criterion 5: malformed or missing reports never raise; the slot just has no parsed fields."""

    def assert_reviewer_unparsed(self, loop):
        rs = rounds_of(loop)
        self.assertTrue(rs)
        rv = rs[-1].get("reviewer")
        self.assertIsInstance(rv, dict)
        self.assertFalse(verdict_of(rs[-1]))
        self.assertFalse(findings_of(rs[-1]))

    def test_no_report_at_all(self):  # criterion 5
        self.s.agent("rumble:reviewer", "Review Unit 1 round 1", T0, None, tools=1)
        loop = self.s.loop()
        self.assertEqual(loop["kind"], "rumble")
        self.assert_reviewer_unparsed(loop)

    def test_garbage_report_text(self):  # criterion 5
        self.s.agent("rumble:reviewer", "Review Unit 1 round 1", T0, "lol\nVerdict:\n- R1.x [huge] — ???\nWithdrawn")
        self.assert_reviewer_unparsed(self.s.loop())

    def test_handback_input_shapes(self):  # criterion 5
        bad = [{"message": None}, {"message": 42}, {"message": ["Verdict: APPROVE"]}, {}, "Verdict: APPROVE", None]
        for i, inp in enumerate(bad):
            with self.subTest(input=inp):
                s = Session(self.tmp, f"s{i}")
                ln = {"type": "assistant", "timestamp": iso(T0 + 30), "message": {
                    "role": "assistant", "stop_reason": "tool_use", "content": [
                        {"type": "tool_use", "id": "h", "name": "SubagentHandback", "input": inp}]}}
                s.agent("rumble:reviewer", "Review Unit 1 round 1", T0, None, extra_lines=[ln])
                loop = s.loop()
                self.assertEqual(loop["kind"], "rumble")
                self.assertFalse(verdict_of(rounds_of(loop)[-1]))

    def test_bad_lines_and_bad_meta(self):  # criterion 5
        s = self.s
        weird = ["not json", json.dumps({"type": "assistant", "message": {"content": "plain string"}}),
                 json.dumps({"type": "assistant", "timestamp": iso(T0 + 20), "message": {"content": [{"type": "text"}]}}),
                 json.dumps({"type": "assistant", "timestamp": iso(T0 + 21), "message": None})]
        s.agent("rumble:reviewer", "Review Unit 1 round 1", T0, review_report(1, "APPROVE"), extra_lines=weird)
        s.agent("rumble:implementer", "x", T0 + 100, impl_report(2, "R9.9 fixed; nonsense"), meta="{not json")
        s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 200, impl_report(2, "garbage, R1.1 maybe"))
        loop = s.loop()  # must not raise
        self.assertEqual(loop["kind"], "rumble")
        self.assertEqual(verdict_of(rounds_of(loop)[0]), "APPROVE")

    def test_unmatched_finding_lines_ignored(self):  # criterion 5 (non-matching lines ignored)
        f = ["R1.1 [blocking] [implementer] bin/entropy:3 — real. Fix.", "Rx [blocking] nope", "just prose",
             "R1.2 [severe] bin/entropy:4 — bad severity"]
        self.s.agent("rumble:reviewer", "Review Unit 1 round 1", T0, review_report(1, "CHANGES_REQUESTED", f))
        (r1,) = rounds_of(self.s.loop())
        self.assertEqual([x["id"] for x in findings_of(r1)], ["R1.1"])


class TestIncremental(Base):
    """Brief: parsing is incremental; loop_card reads nothing, the handback is kept on SubagentLog as it folds."""

    def test_loop_card_reads_no_files(self):
        self.two_rounds()
        logs = entropy.session_subagents(self.s.path)
        real_open = builtins.open

        def guard(path, *a, **k):
            if str(path).endswith((".jsonl", ".json")):
                raise AssertionError(f"loop_card re-read {path}")
            return real_open(path, *a, **k)

        with mock.patch("builtins.open", guard):
            loop = entropy.loop_card(logs, self.s.tr, time.time())
        self.assertEqual(verdict_of(rounds_of(loop)[1]), "APPROVE")

    def test_appended_handback_is_picked_up(self):
        aid = self.s.agent("rumble:reviewer", "Review Unit 1 round 1", T0, None, running=True)
        self.assertFalse(verdict_of(rounds_of(self.s.loop())[0]))
        with open(os.path.join(self.s.dir, aid + ".jsonl"), "a") as fh:
            fh.write(json.dumps({"type": "assistant", "timestamp": iso(T0 + 60), "message": {
                "role": "assistant", "stop_reason": "tool_use", "content": [
                    {"type": "tool_use", "id": "h", "name": "SubagentHandback",
                     "input": {"message": review_report(1, "APPROVE")}}]}}) + "\n")
        self.assertEqual(verdict_of(rounds_of(self.s.loop())[0]), "APPROVE")


if __name__ == "__main__":
    unittest.main()
