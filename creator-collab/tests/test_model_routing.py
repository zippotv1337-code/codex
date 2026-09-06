from __future__ import annotations

import unittest

from creator_ops.model_routing import ModelRoutingPolicy


class ModelRoutingTests(unittest.TestCase):
    def test_astra_high_is_preferred_but_never_required(self) -> None:
        policy = ModelRoutingPolicy.load()
        self.assertEqual(policy.preferred_model, "gpt-6-astra")
        self.assertEqual(policy.reasoning_effort, "high")
        self.assertFalse(policy.preferred_required)
        self.assertTrue(policy.capability_based)
        resolved = policy.resolve({"gpt-6-astra", "gpt-5.6-sol"})
        self.assertEqual(resolved["selected_model"], "gpt-6-astra")
        self.assertEqual(resolved["selection_source"], "preferred-capability")

    def test_stable_model_is_used_when_astra_is_unavailable(self) -> None:
        policy = ModelRoutingPolicy.load()
        resolved = policy.resolve({"gpt-5.6-sol"})
        self.assertEqual(resolved["selected_model"], "gpt-5.6-sol")
        self.assertEqual(resolved["selection_source"], "stable-fallback")

    def test_unknown_runtime_keeps_control_plane_operable(self) -> None:
        policy = ModelRoutingPolicy.load()
        resolved = policy.resolve(set())
        self.assertIsNone(resolved["selected_model"])
        self.assertEqual(resolved["selection_source"], "runtime-default")


if __name__ == "__main__":
    unittest.main()
