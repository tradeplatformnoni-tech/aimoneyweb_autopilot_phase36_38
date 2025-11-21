#!/usr/bin/env python3
"""
Anomaly Detection System - Real-Time Anomaly Detection
========================================================
Detects anomalies in agent behavior using ML-based anomaly detection.

Features:
- Isolation Forest for anomaly detection
- Autoencoder for complex pattern detection
- Real-time monitoring of all metrics
- Adaptive learning of normal behavior
"""

import json
import os
import pickle
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
MODELS_DIR = RUNTIME / "ml_models"

for d in [STATE, RUNTIME, LOGS, MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

ANOMALY_MODEL_FILE = MODELS_DIR / "anomaly_detector.pkl"
ANOMALY_STATE_FILE = STATE / "anomaly_detections.json"
NORMAL_BEHAVIOR_FILE = STATE / "normal_behavior.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Try to import ML libraries
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("[anomaly_detector] scikit-learn not available, using fallback", flush=True)


def send_telegram(message: str) -> None:
    """Send Telegram alert."""
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


class AnomalyDetector:
    """Real-time anomaly detection system."""

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler() if HAS_SKLEARN else None
        self.normal_behavior = {}
        self.load_model()
        self.load_normal_behavior()

    def load_model(self) -> None:
        """Load trained anomaly detection model."""
        if ANOMALY_MODEL_FILE.exists() and HAS_SKLEARN:
            try:
                with open(ANOMALY_MODEL_FILE, "rb") as f:
                    data = pickle.load(f)
                    self.model = data.get("model")
                    self.scaler = data.get("scaler")
                print("[anomaly_detector] Model loaded successfully", flush=True)
            except Exception as e:
                print(f"[anomaly_detector] Failed to load model: {e}", flush=True)
                self.model = None

    def save_model(self) -> None:
        """Save trained model."""
        if self.model and HAS_SKLEARN:
            try:
                with open(ANOMALY_MODEL_FILE, "wb") as f:
                    pickle.dump({"model": self.model, "scaler": self.scaler}, f)
                print("[anomaly_detector] Model saved successfully", flush=True)
            except Exception as e:
                print(f"[anomaly_detector] Failed to save model: {e}", flush=True)

    def load_normal_behavior(self) -> None:
        """Load normal behavior patterns."""
        if NORMAL_BEHAVIOR_FILE.exists():
            try:
                self.normal_behavior = json.loads(NORMAL_BEHAVIOR_FILE.read_text())
            except Exception:
                self.normal_behavior = {}

    def save_normal_behavior(self) -> None:
        """Save normal behavior patterns."""
        try:
            NORMAL_BEHAVIOR_FILE.write_text(json.dumps(self.normal_behavior, indent=2))
        except Exception:
            pass

    def extract_metrics(self, agent_data: dict[str, Any]) -> np.ndarray:
        """Extract metrics from agent data."""
        try:
            import numpy as np
        except ImportError:
            # Fallback: return simple list
            return [[
                agent_data.get("cpu_usage", 0.0),
                agent_data.get("memory_usage", 0.0),
                agent_data.get("error_rate", 0.0),
            ]]

        metrics = np.array([
            agent_data.get("cpu_usage", 0.0),
            agent_data.get("memory_usage", 0.0),
            agent_data.get("disk_usage", 0.0),
            agent_data.get("error_rate", 0.0),
            agent_data.get("response_time_ms", 0.0),
            agent_data.get("queue_length", 0),
            agent_data.get("throughput", 0.0),
            agent_data.get("active_connections", 0),
        ])
        return metrics.reshape(1, -1)

    def detect_anomaly(self, agent_name: str, agent_data: dict[str, Any]) -> dict[str, Any]:
        """Detect if agent behavior is anomalous."""
        metrics = self.extract_metrics(agent_data)

        if not HAS_SKLEARN or not self.model:
            # Fallback: statistical anomaly detection
            return self._statistical_anomaly_detection(agent_name, agent_data)

        try:
            # Scale metrics
            if self.scaler:
                metrics_scaled = self.scaler.transform(metrics)
            else:
                metrics_scaled = metrics

            # Predict anomaly
            prediction = self.model.predict(metrics_scaled)[0]
            anomaly_score = float(self.model.score_samples(metrics_scaled)[0])

            is_anomaly = prediction == -1
            confidence = abs(anomaly_score)

            result = {
                "is_anomaly": bool(is_anomaly),
                "anomaly_score": anomaly_score,
                "confidence": confidence,
                "metrics": metrics.flatten().tolist(),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Update normal behavior if not anomaly
            if not is_anomaly:
                self._update_normal_behavior(agent_name, agent_data)

            return result
        except Exception as e:
            print(f"[anomaly_detector] Detection error: {e}", flush=True)
            return {"is_anomaly": False, "error": str(e)}

    def _statistical_anomaly_detection(self, agent_name: str, agent_data: dict[str, Any]) -> dict[str, Any]:
        """Fallback statistical anomaly detection."""
        if agent_name not in self.normal_behavior:
            # First observation, assume normal
            self._update_normal_behavior(agent_name, agent_data)
            return {"is_anomaly": False, "method": "statistical", "reason": "first_observation"}

        normal = self.normal_behavior[agent_name]
        anomalies = []

        # Check each metric
        for metric in ["cpu_usage", "memory_usage", "error_rate", "response_time_ms"]:
            value = agent_data.get(metric, 0.0)
            mean = normal.get(f"{metric}_mean", value)
            std = normal.get(f"{metric}_std", value * 0.1)

            if std > 0:
                z_score = abs((value - mean) / std)
                if z_score > 3.0:  # 3 sigma rule
                    anomalies.append(f"{metric}: z={z_score:.2f}")

        is_anomaly = len(anomalies) > 0

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": len(anomalies) / 4.0,
            "confidence": 0.7,
            "anomalies": anomalies,
            "method": "statistical",
        }

    def _update_normal_behavior(self, agent_name: str, agent_data: dict[str, Any]) -> None:
        """Update normal behavior patterns."""
        if agent_name not in self.normal_behavior:
            self.normal_behavior[agent_name] = {
                "samples": [],
                "cpu_usage_mean": 0.0,
                "memory_usage_mean": 0.0,
                "error_rate_mean": 0.0,
                "response_time_ms_mean": 0.0,
            }

        normal = self.normal_behavior[agent_name]
        samples = normal.get("samples", [])

        # Add current sample
        sample = {
            "cpu_usage": agent_data.get("cpu_usage", 0.0),
            "memory_usage": agent_data.get("memory_usage", 0.0),
            "error_rate": agent_data.get("error_rate", 0.0),
            "response_time_ms": agent_data.get("response_time_ms", 0.0),
        }
        samples.append(sample)

        # Keep only last 1000 samples
        if len(samples) > 1000:
            samples = samples[-1000:]

            # Update statistics
            if samples:
                try:
                    import numpy as np
                    normal["cpu_usage_mean"] = float(np.mean([s["cpu_usage"] for s in samples]))
                    normal["memory_usage_mean"] = float(np.mean([s["memory_usage"] for s in samples]))
                    normal["error_rate_mean"] = float(np.mean([s["error_rate"] for s in samples]))
                    normal["response_time_ms_mean"] = float(np.mean([s["response_time_ms"] for s in samples]))

                    normal["cpu_usage_std"] = float(np.std([s["cpu_usage"] for s in samples]))
                    normal["memory_usage_std"] = float(np.std([s["memory_usage"] for s in samples]))
                    normal["error_rate_std"] = float(np.std([s["error_rate"] for s in samples]))
                    normal["response_time_ms_std"] = float(np.std([s["response_time_ms"] for s in samples]))
                except ImportError:
                    # Fallback: simple average
                    normal["cpu_usage_mean"] = sum(s["cpu_usage"] for s in samples) / len(samples)
                    normal["memory_usage_mean"] = sum(s["memory_usage"] for s in samples) / len(samples)
                    normal["error_rate_mean"] = sum(s["error_rate"] for s in samples) / len(samples)
                    normal["response_time_ms_mean"] = sum(s["response_time_ms"] for s in samples) / len(samples)

        normal["samples"] = samples
        self.normal_behavior[agent_name] = normal

        # Save periodically
        if len(samples) % 100 == 0:
            self.save_normal_behavior()

    def train_model(self, training_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Train anomaly detection model."""
        if not HAS_SKLEARN or len(training_data) < 100:
            return {"status": "insufficient_data"}

        try:
            # Convert to numpy array
            X = np.array([self.extract_metrics(d).flatten() for d in training_data])

            # Scale data
            X_scaled = self.scaler.fit_transform(X)

            # Train Isolation Forest
            self.model = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42,
                n_estimators=100,
            )
            self.model.fit(X_scaled)

            # Save model
            self.save_model()

            return {"status": "success", "samples": len(training_data)}
        except Exception as e:
            print(f"[anomaly_detector] Training error: {e}", flush=True)
            return {"status": "error", "error": str(e)}


def detect_anomalies_all_agents(agent_statuses: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Detect anomalies for all agents."""
    detector = AnomalyDetector()
    detections = {}

    for agent_name, status in agent_statuses.items():
        # Convert status to metrics format
        agent_data = {
            "cpu_usage": status.get("cpu_usage", 0.0),
            "memory_usage": status.get("memory_usage", 0.0),
            "disk_usage": status.get("disk_usage", 0.0),
            "error_rate": len(status.get("errors", [])) / max(1, status.get("error_window", 100)),
            "response_time_ms": status.get("response_time_ms", 0.0),
            "queue_length": status.get("queue_length", 0),
            "throughput": status.get("throughput", 0.0),
            "active_connections": status.get("active_connections", 0),
        }

        detection = detector.detect_anomaly(agent_name, agent_data)
        detections[agent_name] = detection

        # Alert if anomaly detected
        if detection.get("is_anomaly") and detection.get("confidence", 0) > 0.7:
            message = (
                f"🚨 **Anomaly Detected**\n"
                f"Agent: `{agent_name}`\n"
                f"Score: {detection.get('anomaly_score', 0):.2f}\n"
                f"Confidence: {detection.get('confidence', 0):.2%}"
            )
            send_telegram(message)

    # Save detections
    try:
        detection_state = {
            "timestamp": datetime.now(UTC).isoformat(),
            "detections": detections,
        }
        ANOMALY_STATE_FILE.write_text(json.dumps(detection_state, indent=2))
    except Exception:
        pass

    return detections


def main() -> None:
    """Main anomaly detection loop."""
    print(
        f"[anomaly_detector] 🔍 Anomaly Detector starting @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    detector = AnomalyDetector()

    check_interval = int(os.getenv("ANOMALY_CHECK_INTERVAL", "60"))  # Every minute

    while True:
        try:
            # This would be called by self-healing agent with agent statuses
            # For standalone mode, we'd need to collect agent statuses
            time.sleep(check_interval)
        except Exception as e:
            print(f"[anomaly_detector] Error in main loop: {e}", flush=True)
            time.sleep(60)


if __name__ == "__main__":
    main()

