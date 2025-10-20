import os, json, time, joblib
from typing import Dict, Any

META_PATH = "models/federated_meta.json"
MODEL_PATH = "models/federated_model.pkl"

def _load_meta() -> Dict[str, Any]:
    if os.path.exists(META_PATH):
        return json.load(open(META_PATH))
    return {"peers": {}, "best_score": -1e9, "last_update": None}

def _save_meta(meta: Dict[str, Any]): json.dump(meta, open(META_PATH, "w"))

def accept_update(peer_id: str, score: float, weights: Dict[str, float]):
    os.makedirs("models", exist_ok=True)
    meta = _load_meta()
    meta["peers"][peer_id] = {"score": score, "ts": time.time()}
    if score >= meta.get("best_score", -1e9):
        joblib.dump({"weights": weights, "score": score, "peer": peer_id, "ts": time.time()}, MODEL_PATH)
        meta["best_score"] = score
        meta["last_update"] = time.time()
    _save_meta(meta)
    return {"ok": True, "best_score": meta["best_score"], "peers": len(meta["peers"])}

def best_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return {"weights": {"w": 0.0}, "score": 0.0, "peer": "none", "ts": 0}
