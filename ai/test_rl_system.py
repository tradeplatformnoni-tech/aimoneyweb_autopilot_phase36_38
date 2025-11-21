#!/usr/bin/env python3
"""
NeoLight RL System Tests - Phase 3700-3900
===========================================
Unit tests and validation for RL framework.
Verifies system works correctly without disrupting trading.
"""

import json
import os
import unittest
from pathlib import Path

import numpy as np

from ai.rl_agent import PPOAgent
from ai.rl_environment import State, TradingEnvironment
from ai.rl_inference import RLInferenceEngine

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"


class TestRLEnvironment(unittest.TestCase):
    """Test RL environment."""

    def setUp(self):
        self.env = TradingEnvironment()

    def test_environment_initialization(self):
        """Test environment initializes correctly."""
        self.assertIsNotNone(self.env)
        self.assertEqual(self.env.state_size, 34)

    def test_get_state(self):
        """Test state computation."""
        state = self.env.get_state()
        self.assertIsInstance(state, State)
        self.assertEqual(len(state.market_features), 8)
        self.assertEqual(len(state.portfolio_features), 6)
        self.assertEqual(len(state.strategy_performance), 16)
        self.assertEqual(len(state.market_regime), 4)

    def test_get_state_vector(self):
        """Test state vector conversion."""
        state = self.env.get_state()
        state_vec = self.env.get_state_vector(state)
        self.assertEqual(len(state_vec), self.env.state_size)
        self.assertIsInstance(state_vec, np.ndarray)

    def test_compute_reward(self):
        """Test reward computation."""
        state = self.env.get_state()
        reward = self.env.compute_reward(None, state)
        self.assertIsInstance(reward, float)
        self.assertGreaterEqual(reward, -2.0)
        self.assertLessEqual(reward, 2.0)

    def test_step(self):
        """Test environment step."""
        state = self.env.get_state()
        action = np.ones(8) / 8.0  # Equal weights
        new_state, reward, done, info = self.env.step(action, None)

        self.assertIsInstance(new_state, State)
        self.assertIsInstance(reward, float)
        self.assertIsInstance(done, bool)
        self.assertIsInstance(info, dict)


class TestRLAgent(unittest.TestCase):
    """Test RL agent."""

    def setUp(self):
        self.agent = PPOAgent(
            state_size=34, action_size=8, use_torch=False
        )  # Use simplified for testing

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.state_size, 34)
        self.assertEqual(self.agent.action_size, 8)

    def test_select_action(self):
        """Test action selection."""
        state = np.random.randn(34).astype(np.float32)
        action, log_prob, value = self.agent.select_action(state)

        self.assertEqual(len(action), 8)
        self.assertAlmostEqual(np.sum(action), 1.0, places=5)
        self.assertTrue(all(a >= 0 for a in action))
        self.assertIsInstance(log_prob, float)
        self.assertIsInstance(value, float)

    def test_store_transition(self):
        """Test transition storage."""
        state = np.random.randn(34).astype(np.float32)
        action = np.ones(8) / 8.0
        reward = 0.5
        log_prob = -2.0
        value = 0.3

        self.agent.store_transition(state, action, reward, log_prob, value, False)
        self.assertEqual(len(self.agent.states), 1)
        self.assertEqual(len(self.agent.actions), 1)
        self.assertEqual(len(self.agent.rewards), 1)

    def test_train(self):
        """Test training."""
        # Store some transitions
        for i in range(10):
            state = np.random.randn(34).astype(np.float32)
            action = np.random.rand(8)
            action = action / np.sum(action)
            self.agent.store_transition(state, action, 0.5, -2.0, 0.3, False)

        metrics = self.agent.train(epochs=2, batch_size=5)
        self.assertIsInstance(metrics, dict)
        self.assertIn("policy_loss", metrics)

    def test_save_load(self):
        """Test model save/load."""
        # Save
        self.agent.save("test")
        self.assertTrue((STATE / "rl_model" / "checkpoint_test.pkl").exists())

        # Create new agent and load
        new_agent = PPOAgent(state_size=34, action_size=8, use_torch=False)
        success = new_agent.load("test")
        self.assertTrue(success)

        # Cleanup
        (STATE / "rl_model" / "checkpoint_test.pkl").unlink(missing_ok=True)


class TestRLInference(unittest.TestCase):
    """Test RL inference engine."""

    def setUp(self):
        self.engine = RLInferenceEngine()

    def test_engine_initialization(self):
        """Test inference engine initializes."""
        self.assertIsNotNone(self.engine)

    def test_generate_weights(self):
        """Test weight generation."""
        weights = self.engine.generate_weights(deterministic=True)

        self.assertIsInstance(weights, dict)
        self.assertEqual(len(weights), 8)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)
        self.assertTrue(all(w >= 0 for w in weights.values()))

    def test_save_weights(self):
        """Test weight saving."""
        weights = self.engine.generate_weights()
        self.engine.save_weights(weights)

        self.assertTrue(RUNTIME / "rl_strategy_weights.json").exists()

        # Verify content
        data = json.loads((RUNTIME / "rl_strategy_weights.json").read_text())
        self.assertEqual(data["source"], "rl_inference")
        self.assertIn("weights", data)
        self.assertIn("timestamp", data)


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def test_end_to_end(self):
        """Test end-to-end flow."""
        # 1. Environment generates state
        env = TradingEnvironment()
        state = env.get_state()
        state_vec = env.get_state_vector(state)

        # 2. Agent generates action
        agent = PPOAgent(state_size=34, action_size=8, use_torch=False)
        action, log_prob, value = agent.select_action(state_vec)

        # 3. Environment computes reward
        reward = env.compute_reward(None, state, action)

        # 4. Inference engine generates weights
        engine = RLInferenceEngine()
        weights = engine.generate_weights()

        # All should work
        self.assertIsNotNone(state_vec)
        self.assertIsNotNone(action)
        self.assertIsNotNone(reward)
        self.assertIsNotNone(weights)

    def test_weights_bridge_integration(self):
        """Test integration with weights_bridge."""
        # Generate RL weights
        engine = RLInferenceEngine()
        weights = engine.generate_weights()
        engine.save_weights(weights)

        # Check file exists
        rl_file = RUNTIME / "rl_strategy_weights.json"
        self.assertTrue(rl_file.exists())

        # Verify format
        data = json.loads(rl_file.read_text())
        self.assertIn("weights", data)
        self.assertIn("source", data)
        self.assertEqual(data["source"], "rl_inference")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestRLEnvironment))
    suite.addTests(loader.loadTestsFromTestCase(TestRLAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestRLInference))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
