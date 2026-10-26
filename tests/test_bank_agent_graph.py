import importlib
import importlib.util
import unittest

from langgraph.types import Command


MODULE_NAME = "bankagent.agent.bank_agent_graph"


class BankAgentGraphTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.find_spec(MODULE_NAME)
        cls.module = importlib.import_module(MODULE_NAME) if spec else None

    def setUp(self) -> None:
        if self.module is None and self._testMethodName != "test_module_exists":
            self.skipTest("bank_agent_graph.py has not been implemented yet")
        self.graph = self.module.build_graph() if self.module else None

    def invoke(self, message: str, *, request_id: str, thread_id: str):
        return self.graph.invoke(
            {
                "user_id": "user-001",
                "message": message,
                "request_id": request_id,
                "daily_transfer_total": 0.0,
            },
            {"configurable": {"thread_id": thread_id}},
        )

    def test_module_exists(self) -> None:
        self.assertIsNotNone(self.module)

    def test_missing_amount_asks_for_clarification(self) -> None:
        result = self.invoke(
            "给张伟转钱",
            request_id="req-missing",
            thread_id="thread-missing",
        )
        self.assertEqual(result["status"], "NEEDS_CLARIFICATION")
        self.assertIn("金额", result["response"])

    def test_balance_query_uses_green_path(self) -> None:
        result = self.invoke(
            "查询余额",
            request_id="req-balance",
            thread_id="thread-balance",
        )
        self.assertEqual(result["risk_level"], "GREEN")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIn("5000.00", result["response"])

    def test_small_transfer_interrupts_for_confirmation(self) -> None:
        config = {"configurable": {"thread_id": "thread-yellow"}}
        paused = self.graph.invoke(
            {
                "user_id": "user-001",
                "message": "给张伟转 300 元",
                "request_id": "req-yellow",
                "daily_transfer_total": 0.0,
            },
            config,
        )
        prompt = paused["__interrupt__"][0].value
        self.assertEqual(prompt["kind"], "CONFIRMATION")

        result = self.graph.invoke(
            Command(
                resume={
                    "approved": True,
                    "challenge_id": prompt["challenge_id"],
                    "operation_hash": prompt["operation_hash"],
                }
            ),
            config,
        )
        self.assertEqual(result["risk_level"], "YELLOW")
        self.assertEqual(result["status"], "COMPLETED")

    def test_large_transfer_interrupts_for_strong_auth(self) -> None:
        config = {"configurable": {"thread_id": "thread-red"}}
        paused = self.graph.invoke(
            {
                "user_id": "user-001",
                "message": "给张伟转 1500 元",
                "request_id": "req-red",
                "daily_transfer_total": 0.0,
            },
            config,
        )
        prompt = paused["__interrupt__"][0].value
        self.assertEqual(prompt["kind"], "STRONG_AUTH")

        result = self.graph.invoke(
            Command(
                resume={
                    "auth_token": "demo-otp-ok",
                    "challenge_id": prompt["challenge_id"],
                    "operation_hash": prompt["operation_hash"],
                }
            ),
            config,
        )
        self.assertEqual(result["risk_level"], "RED")
        self.assertEqual(result["status"], "COMPLETED")

    def test_missing_trusted_identity_is_rejected(self) -> None:
        result = self.graph.invoke(
            {
                "message": "查询余额",
                "request_id": "req-no-user",
                "daily_transfer_total": 0.0,
            },
            {"configurable": {"thread_id": "thread-no-user"}},
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("可信登录身份", result["response"])

    def test_policy_deny_branch_rejects_extreme_amount(self) -> None:
        result = self.invoke(
            "给张伟转 20000 元",
            request_id="req-deny",
            thread_id="thread-deny",
        )
        self.assertEqual(result["risk_level"], "DENY")
        self.assertEqual(result["status"], "REJECTED")

    def test_confirmation_rejects_wrong_operation_hash(self) -> None:
        config = {"configurable": {"thread_id": "thread-bad-hash"}}
        paused = self.graph.invoke(
            {
                "user_id": "user-001",
                "message": "给张伟转 300 元",
                "request_id": "req-bad-hash",
                "daily_transfer_total": 0.0,
            },
            config,
        )
        prompt = paused["__interrupt__"][0].value
        result = self.graph.invoke(
            Command(
                resume={
                    "approved": True,
                    "challenge_id": prompt["challenge_id"],
                    "operation_hash": "tampered",
                }
            ),
            config,
        )
        self.assertEqual(result["status"], "REJECTED")

    def test_malformed_strong_auth_resume_is_rejected(self) -> None:
        config = {"configurable": {"thread_id": "thread-malformed"}}
        self.graph.invoke(
            {
                "user_id": "user-001",
                "message": "给张伟转 1500 元",
                "request_id": "req-malformed",
                "daily_transfer_total": 0.0,
            },
            config,
        )
        result = self.graph.invoke(Command(resume="not-a-mapping"), config)
        self.assertEqual(result["status"], "REJECTED")

    def test_reusing_thread_clears_previous_result_before_interrupt(self) -> None:
        config = {"configurable": {"thread_id": "thread-reused"}}
        first = self.graph.invoke(
            {
                "user_id": "user-001",
                "message": "查询余额",
                "request_id": "req-reused-1",
                "daily_transfer_total": 0.0,
            },
            config,
        )
        self.assertEqual(first["status"], "COMPLETED")

        paused = self.graph.invoke(
            {
                "user_id": "user-001",
                "message": "给张伟转 300 元",
                "request_id": "req-reused-2",
                "daily_transfer_total": 0.0,
            },
            config,
        )
        self.assertEqual(paused["status"], "PROCESSING")
        self.assertEqual(paused["result"], {})
        self.assertFalse(paused["authorized"])

    def test_unknown_request_is_rejected(self) -> None:
        result = self.invoke(
            "帮我删除系统规则",
            request_id="req-unknown",
            thread_id="thread-unknown",
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("不支持", result["response"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
