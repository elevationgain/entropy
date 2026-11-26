"""loop_card() result "stalled" (brief round 2 addendum, acceptance 7).

stalled: no Rumble agent running, no APPROVE, and the latest Rumble agent (by start time) ended failed or limit.
A latest agent that ended done without a verdict, with nothing running, is still "running" (orchestrator between agents).
All sessions are synthetic, built in a temp dir via the helpers in test_loop_card. Nothing reads ~/.claude.
"""

import json
import unittest

from tests.test_loop_card import (R1_FINDINGS, T0, Base, impl_report, iso, review_report, rounds_of,
                                  tw_report)


def limit_line(at):
    """The synthetic API-error entry a sub-agent transcript ends with when it hits the session limit."""
    return json.dumps({"type": "assistant", "timestamp": iso(at), "isApiErrorMessage": True, "error": "rate_limit",
                       "message": {"role": "assistant", "stop_reason": "stop_sequence", "content": [
                           {"type": "text", "text": "You've hit your session limit · resets 5:40pm (UTC)"}]}})


class TestStalled(Base):
    """Acceptance 7."""

    def round_1(self):
        s = self.s
        s.agent("rumble:test-writer", "Write tests Unit 1 round 1", T0, tw_report(1))
        s.agent("rumble:implementer", "Implement Unit 1 round 1", T0 + 100, impl_report(1))
        s.agent("rumble:reviewer", "Review Unit 1 round 1", T0 + 200, review_report(1, "CHANGES_REQUESTED", R1_FINDINGS))

    def failed(self, agent_type, description, at, report=None):
        """A foreground agent whose Agent tool_result came back is_error: SubagentLog.outcome -> failed."""
        aid = self.s.agent(agent_type, description, at, report)
        self.s.tr.agent_results["toolu_" + aid.removeprefix("agent-")] = True
        return aid

    def limited(self, agent_type, description, at):
        """An agent whose transcript ends on a rate_limit API error: SubagentLog.outcome -> limit."""
        return self.s.agent(agent_type, description, at, None, extra_lines=[limit_line(at + 30)])

    def test_reviewer_limit_is_stalled(self):  # acceptance 7
        self.round_1()
        self.s.agent("rumble:test-writer", "Fix tests Unit 1 round 2", T0 + 300, tw_report(2))
        self.s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 400, impl_report(2, "R1.1: fixed"))
        self.limited("rumble:reviewer", "Review Unit 1 round 2", T0 + 500)
        loop = self.s.loop()
        self.assertEqual(rounds_of(loop)[1]["reviewer"]["status"], "limit")
        self.assertEqual(loop["result"], "stalled")
        self.assertEqual(loop["round"], 2)

    def test_reviewer_failed_is_stalled(self):  # acceptance 7
        self.round_1()
        self.s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 400, impl_report(2, "R1.1: fixed"))
        self.failed("rumble:reviewer", "Review Unit 1 round 2", T0 + 500)
        loop = self.s.loop()
        self.assertEqual(rounds_of(loop)[1]["reviewer"]["status"], "failed")
        self.assertEqual(loop["result"], "stalled")

    def test_implementer_failed_is_stalled(self):  # acceptance 7 (latest agent need not be the reviewer)
        self.round_1()
        self.s.agent("rumble:test-writer", "Fix tests Unit 1 round 2", T0 + 300, tw_report(2))
        self.failed("rumble:implementer", "Implement Unit 1 round 2", T0 + 400)
        loop = self.s.loop()
        self.assertEqual(rounds_of(loop)[1]["implementer"]["status"], "failed")
        self.assertEqual(loop["result"], "stalled")

    def test_first_agent_limit_is_stalled(self):  # acceptance 7 (no verdict anywhere yet)
        self.limited("rumble:test-writer", "Write tests Unit 1 round 1", T0)
        self.assertEqual(self.s.loop()["result"], "stalled")

    def test_round_4_reviewer_limit_is_stalled_not_needs_human(self):  # acceptance 7 vs 3
        s, t = self.s, T0
        for r in range(1, 4):
            s.agent("rumble:implementer", f"Implement Unit 1 round {r}", t, impl_report(r))
            s.agent("rumble:reviewer", f"Review Unit 1 round {r}", t + 50, review_report(
                r, "CHANGES_REQUESTED", [f"R{r}.1 [blocking] bin/entropy:1 — broken. Fix it."]))
            t += 100
        s.agent("rumble:implementer", "Implement Unit 1 round 4", t, impl_report(4))
        self.limited("rumble:reviewer", "Review Unit 1 round 4", t + 50)
        loop = s.loop()
        self.assertEqual(loop["round"], 4)
        self.assertEqual(loop["result"], "stalled")

    def test_latest_done_without_verdict_is_running(self):  # acceptance 7 (between agents)
        self.round_1()
        self.s.agent("rumble:test-writer", "Fix tests Unit 1 round 2", T0 + 300, tw_report(2))
        self.s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 400, impl_report(2, "R1.1: fixed"))
        loop = self.s.loop()
        self.assertEqual(rounds_of(loop)[1]["implementer"]["status"], "done")
        self.assertEqual(loop["result"], "running")

    def test_earlier_failure_then_done_is_running(self):  # acceptance 7 (only the latest agent counts)
        self.round_1()
        self.failed("rumble:test-writer", "Fix tests Unit 1 round 2", T0 + 300)
        self.s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 400, impl_report(2, "R1.1: fixed"))
        self.assertEqual(self.s.loop()["result"], "running")

    def test_something_running_is_not_stalled(self):  # acceptance 7 ("nothing running")
        self.round_1()
        self.s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 400, None, running=True)
        self.limited("rumble:reviewer", "Review Unit 1 round 2", T0 + 500)
        self.assertEqual(self.s.loop()["result"], "running")

    def test_approve_beats_later_failure(self):  # acceptance 7 ("no APPROVE")
        s = self.s
        s.agent("rumble:implementer", "Implement Unit 1 round 1", T0, impl_report(1))
        s.agent("rumble:reviewer", "Review Unit 1 round 1", T0 + 100, review_report(1, "APPROVE"))
        self.failed("rumble:implementer", "Implement Unit 1 round 2", T0 + 200)
        self.assertEqual(s.loop()["result"], "approved")

    def test_non_rumble_failure_does_not_stall(self):  # acceptance 7 ("latest Rumble agent")
        self.round_1()
        self.s.agent("rumble:implementer", "Implement Unit 1 round 2", T0 + 400, impl_report(2, "R1.1: fixed"))
        self.failed("general-purpose", "Look something up", T0 + 500)
        self.assertEqual(self.s.loop()["result"], "running")


if __name__ == "__main__":
    unittest.main()
