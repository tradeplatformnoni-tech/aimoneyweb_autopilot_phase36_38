#!/usr/bin/env python3
"""
NeoLight RL Agent - Phase 3700-3900
====================================
Proximal Policy Optimization (PPO) agent for strategy weight allocation.
World-class implementation with neural network policy.
"""

import json
import logging
import os
import pickle
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

HAS_TORCH = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim

    HAS_TORCH = True
except ImportError:
    pass  # Will use simplified implementation

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "rl_agent.log"
logger = logging.getLogger("rl_agent")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Constants
NUM_STRATEGIES = 8
STATE_SIZE = 34
ACTION_SIZE = NUM_STRATEGIES

if HAS_TORCH:

    class PolicyNetwork(nn.Module):
        """Neural network policy for PPO."""

        def __init__(
            self,
            state_size: int = STATE_SIZE,
            action_size: int = ACTION_SIZE,
            hidden_size: int = 128,
        ):
            super(PolicyNetwork, self).__init__()
            self.fc1 = nn.Linear(state_size, hidden_size)
            self.fc2 = nn.Linear(hidden_size, hidden_size)
            self.fc3 = nn.Linear(hidden_size, action_size)
            self.dropout = nn.Dropout(0.2)

        def forward(self, state):
            x = F.relu(self.fc1(state))
            x = self.dropout(x)
            x = F.relu(self.fc2(x))
            x = self.dropout(x)
            # Output logits for each strategy
            logits = self.fc3(x)
            return logits

    class ValueNetwork(nn.Module):
        """Value network for PPO."""

        def __init__(self, state_size: int = STATE_SIZE, hidden_size: int = 128):
            super(ValueNetwork, self).__init__()
            self.fc1 = nn.Linear(state_size, hidden_size)
            self.fc2 = nn.Linear(hidden_size, hidden_size)
            self.fc3 = nn.Linear(hidden_size, 1)
            self.dropout = nn.Dropout(0.2)

        def forward(self, state):
            x = F.relu(self.fc1(state))
            x = self.dropout(x)
            x = F.relu(self.fc2(x))
            x = self.dropout(x)
            value = self.fc3(x)
            return value
else:
    # Placeholder classes when PyTorch not available
    class PolicyNetwork:
        pass

    class ValueNetwork:
        pass


class SimplePolicy:
    """Simplified policy without PyTorch (fallback)."""

    def __init__(self, state_size: int = STATE_SIZE, action_size: int = ACTION_SIZE):
        self.state_size = state_size
        self.action_size = action_size
        # Simple linear policy with random initialization
        self.weights = np.random.randn(state_size, action_size) * 0.1
        self.bias = np.random.randn(action_size) * 0.1

    def predict(self, state: np.ndarray) -> np.ndarray:
        """Predict action (strategy weights)."""
        logits = np.dot(state, self.weights) + self.bias
        # Softmax to get probabilities
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        return probs


class PPOAgent:
    """
    Proximal Policy Optimization agent for strategy weight allocation.
    Learns optimal strategy weights based on market state and trade outcomes.
    """

    def __init__(
        self,
        state_size: int = STATE_SIZE,
        action_size: int = ACTION_SIZE,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        use_torch: bool = True,
    ):
        """
        Initialize PPO agent.

        Args:
            state_size: Size of state vector
            action_size: Number of strategies (actions)
            learning_rate: Learning rate for optimizer
            gamma: Discount factor
            epsilon: PPO clipping parameter
            value_coef: Value loss coefficient
            entropy_coef: Entropy bonus coefficient
            use_torch: Whether to use PyTorch (if available)
        """
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.use_torch = use_torch and HAS_TORCH

        # Initialize networks
        if self.use_torch:
            self.policy_net = PolicyNetwork(state_size, action_size)
            self.value_net = ValueNetwork(state_size)
            self.policy_optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
            self.value_optimizer = optim.Adam(self.value_net.parameters(), lr=learning_rate)
            logger.info("✅ PPO Agent initialized with PyTorch")
        else:
            self.policy = SimplePolicy(state_size, action_size)
            logger.info("✅ PPO Agent initialized with simplified policy (PyTorch not available)")

        # Training buffers
        self.states: list[np.ndarray] = []
        self.actions: list[np.ndarray] = []
        self.rewards: list[float] = []
        self.log_probs: list[float] = []
        self.values: list[float] = []
        self.dones: list[bool] = []

        # Model directory
        self.model_dir = STATE / "rl_model"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"PPO Agent: state_size={state_size}, action_size={action_size}, lr={learning_rate}"
        )

    def select_action(
        self, state: np.ndarray, deterministic: bool = False
    ) -> tuple[np.ndarray, float, float]:
        """
        Select action (strategy weights) given state.

        Args:
            state: State vector
            deterministic: If True, return mean action; if False, sample from distribution

        Returns:
            (action, log_prob, value)
        """
        state_tensor = None
        if self.use_torch:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)

        if self.use_torch:
            # Get policy logits
            with torch.no_grad():
                logits = self.policy_net(state_tensor)
                value = self.value_net(state_tensor).item()

                # Create probability distribution
                dist = torch.distributions.Categorical(logits=logits)

                if deterministic:
                    action_idx = torch.argmax(logits, dim=1).item()
                    action = torch.zeros(self.action_size)
                    action[action_idx] = 1.0
                    log_prob = dist.log_prob(torch.tensor(action_idx)).item()
                else:
                    # Sample action
                    action_idx = dist.sample().item()
                    action = torch.zeros(self.action_size)
                    action[action_idx] = 1.0
                    log_prob = dist.log_prob(torch.tensor(action_idx)).item()

                # Convert to numpy
                action_np = action.numpy()
        else:
            # Simplified policy
            probs = self.policy.predict(state)
            if deterministic:
                action_idx = np.argmax(probs)
            else:
                action_idx = np.random.choice(self.action_size, p=probs)

            action_np = np.zeros(self.action_size)
            action_np[action_idx] = 1.0
            log_prob = np.log(probs[action_idx] + 1e-8)
            value = 0.0  # Simplified value estimate

        # Normalize to sum to 1.0 (strategy weights)
        action_np = action_np / (np.sum(action_np) + 1e-8)

        return action_np, float(log_prob), float(value)

    def store_transition(
        self,
        state: np.ndarray,
        action: np.ndarray,
        reward: float,
        log_prob: float,
        value: float,
        done: bool,
    ):
        """Store transition for training."""
        self.states.append(state.copy())
        self.actions.append(action.copy())
        self.rewards.append(reward)
        self.log_probs.append(log_prob)
        self.values.append(value)
        self.dones.append(done)

    def compute_returns(self) -> list[float]:
        """Compute discounted returns."""
        returns = []
        G = 0
        for reward, done in zip(reversed(self.rewards), reversed(self.dones)):
            if done:
                G = 0
            G = reward + self.gamma * G
            returns.insert(0, G)
        return returns

    def compute_advantages(self, returns: list[float]) -> list[float]:
        """Compute advantages (returns - values)."""
        advantages = []
        for ret, val in zip(returns, self.values):
            adv = ret - val
            advantages.append(adv)
        return advantages

    def train(self, epochs: int = 10, batch_size: int = 64) -> dict[str, float]:
        """
        Train agent on stored transitions.

        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training

        Returns:
            Training metrics
        """
        if len(self.states) == 0:
            logger.warning("No transitions to train on")
            return {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        # Compute returns and advantages
        returns = self.compute_returns()
        advantages = self.compute_advantages(returns)

        # Normalize advantages
        if len(advantages) > 1:
            adv_mean = np.mean(advantages)
            adv_std = np.std(advantages) + 1e-8
            advantages = [(a - adv_mean) / adv_std for a in advantages]

        metrics = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        if self.use_torch:
            # Convert to tensors
            states_t = torch.FloatTensor(np.array(self.states))
            actions_t = torch.FloatTensor(np.array(self.actions))
            returns_t = torch.FloatTensor(returns)
            advantages_t = torch.FloatTensor(advantages)
            old_log_probs_t = torch.FloatTensor(self.log_probs)

            # Training loop
            for epoch in range(epochs):
                # Shuffle data
                indices = torch.randperm(len(self.states))

                for i in range(0, len(self.states), batch_size):
                    batch_indices = indices[i : i + batch_size]
                    batch_states = states_t[batch_indices]
                    batch_actions = actions_t[batch_indices]
                    batch_returns = returns_t[batch_indices]
                    batch_advantages = advantages_t[batch_indices]
                    batch_old_log_probs = old_log_probs_t[batch_indices]

                    # Get current policy
                    logits = self.policy_net(batch_states)
                    values = self.value_net(batch_states).squeeze()

                    # Compute action probabilities
                    dist = torch.distributions.Categorical(logits=logits)
                    action_indices = torch.argmax(batch_actions, dim=1)
                    new_log_probs = dist.log_prob(action_indices)
                    entropy = dist.entropy().mean()

                    # PPO clipped objective
                    ratio = torch.exp(new_log_probs - batch_old_log_probs)
                    surr1 = ratio * batch_advantages
                    surr2 = (
                        torch.clamp(ratio, 1 - self.epsilon, 1 + self.epsilon) * batch_advantages
                    )
                    policy_loss = -torch.min(surr1, surr2).mean() - self.entropy_coef * entropy

                    # Value loss
                    value_loss = F.mse_loss(values, batch_returns)

                    # Update networks
                    self.policy_optimizer.zero_grad()
                    policy_loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 0.5)
                    self.policy_optimizer.step()

                    self.value_optimizer.zero_grad()
                    value_loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.value_net.parameters(), 0.5)
                    self.value_optimizer.step()

                    metrics["policy_loss"] += policy_loss.item()
                    metrics["value_loss"] += value_loss.item()
                    metrics["entropy"] += entropy.item()

            # Average metrics
            num_batches = (len(self.states) // batch_size) * epochs
            if num_batches > 0:
                metrics["policy_loss"] /= num_batches
                metrics["value_loss"] /= num_batches
                metrics["entropy"] /= num_batches
        else:
            # Simplified REINFORCE-style update for fallback mode
            states_np = np.array(self.states)
            actions_np = np.array(self.actions)
            returns_np = np.array(returns)
            advantages_np = np.array(advantages)

            if len(states_np) > 0:
                logits = states_np @ self.policy.weights + self.policy.bias
                logits -= logits.max(axis=1, keepdims=True)
                exp_logits = np.exp(logits)
                probs = exp_logits / (np.sum(exp_logits, axis=1, keepdims=True) + 1e-8)

                action_indices = np.argmax(actions_np, axis=1)
                one_hot = np.zeros_like(probs)
                one_hot[np.arange(len(probs)), action_indices] = 1.0

                advantages_vec = advantages_np.reshape(-1, 1)
                grad_logits = (one_hot - probs) * advantages_vec
                grad_weights = states_np.T @ grad_logits / len(states_np)
                grad_bias = grad_logits.mean(axis=0)

                self.policy.weights += self.learning_rate * grad_weights
                self.policy.bias += self.learning_rate * grad_bias

                selected_probs = probs[np.arange(len(probs)), action_indices]
                policy_loss = -(advantages_np * np.log(selected_probs + 1e-8)).mean()
                entropy = -np.sum(probs * np.log(probs + 1e-8), axis=1).mean()

                metrics["policy_loss"] = float(policy_loss)
                metrics["value_loss"] = 0.0
                metrics["entropy"] = float(entropy)
            else:
                metrics = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        # Clear buffers
        self.clear_buffer()

        logger.info(f"Training complete: {metrics}")
        return metrics

    def clear_buffer(self):
        """Clear training buffers."""
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.log_probs.clear()
        self.values.clear()
        self.dones.clear()

    def save(self, checkpoint_name: str = "latest"):
        """Save agent to disk."""
        checkpoint_path = self.model_dir / f"checkpoint_{checkpoint_name}.pkl"
        config_path = self.model_dir / "config.json"

        try:
            if self.use_torch:
                checkpoint = {
                    "policy_state_dict": self.policy_net.state_dict(),
                    "value_state_dict": self.value_net.state_dict(),
                    "policy_optimizer": self.policy_optimizer.state_dict(),
                    "value_optimizer": self.value_optimizer.state_dict(),
                    "state_size": self.state_size,
                    "action_size": self.action_size,
                    "learning_rate": self.learning_rate,
                    "gamma": self.gamma,
                    "epsilon": self.epsilon,
                }
                torch.save(checkpoint, checkpoint_path)
            else:
                checkpoint = {
                    "policy_weights": self.policy.weights,
                    "policy_bias": self.policy.bias,
                    "state_size": self.state_size,
                    "action_size": self.action_size,
                }
                with open(checkpoint_path, "wb") as f:
                    pickle.dump(checkpoint, f)

            config = {
                "state_size": self.state_size,
                "action_size": self.action_size,
                "learning_rate": self.learning_rate,
                "gamma": self.gamma,
                "epsilon": self.epsilon,
                "use_torch": self.use_torch,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            config_path.write_text(json.dumps(config, indent=2))

            logger.info(f"✅ Saved checkpoint: {checkpoint_path}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load(self, checkpoint_name: str = "latest"):
        """Load agent from disk."""
        checkpoint_path = self.model_dir / f"checkpoint_{checkpoint_name}.pkl"
        config_path = self.model_dir / "config.json"

        if not checkpoint_path.exists():
            logger.warning(f"Checkpoint not found: {checkpoint_path}")
            return False

        try:
            if self.use_torch:
                checkpoint = torch.load(checkpoint_path, map_location="cpu")
                self.policy_net.load_state_dict(checkpoint["policy_state_dict"])
                self.value_net.load_state_dict(checkpoint["value_state_dict"])
                self.policy_optimizer.load_state_dict(checkpoint["policy_optimizer"])
                self.value_optimizer.load_state_dict(checkpoint["value_optimizer"])
            else:
                with open(checkpoint_path, "rb") as f:
                    checkpoint = pickle.load(f)
                self.policy.weights = checkpoint["policy_weights"]
                self.policy.bias = checkpoint["policy_bias"]

            logger.info(f"✅ Loaded checkpoint: {checkpoint_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False


def main():
    """Test agent."""
    agent = PPOAgent()
    state = np.random.randn(STATE_SIZE).astype(np.float32)
    action, log_prob, value = agent.select_action(state)
    print(f"Action (strategy weights): {action}")
    print(f"Sum: {np.sum(action)}")
    print(f"Log prob: {log_prob}, Value: {value}")


if __name__ == "__main__":
    main()
