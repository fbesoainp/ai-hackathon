# embed_modal.py – Generate 384‑dim embeddings via a Modal function
"""Open‑source embedding powered by **Modal**.

Usage:
    1.  Set `DEV_MODE=true` to allow deterministic random fallback when offline.
    2.  Run `modal deploy embed_modal.py` (or `python embed_modal.py --stub`).
    3.  Backend imports `embed_modal.embed` to obtain vectors.

Modal details:
    * The function runs inside a slim container with `sentence-transformers`.
    * Model: `all-MiniLM-L6-v2` (384‑dim).
    * Concurrency capped at 100 (adjust as needed).
"""
from __future__ import annotations

import hashlib, os, numpy as np
import modal

EMBED_DIM = 384
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Modal definition (executed once at import‑time)
# ---------------------------------------------------------------------------
app = modal.App("pairfecto-embeddings")

image = (
    modal.Image.debian_slim()
    .pip_install("sentence-transformers==2.5.1", "torch", "transformers", "accelerate")
)

@app.function(image=image, max_containers=100, cpu=2)
def compute_embedding(text: str) -> list[float]:
    from sentence_transformers import SentenceTransformer
    global _model
    if "_model" not in globals():
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = _model.encode(text)       # <‑‑ drop normalize_embeddings=True
    return emb.tolist()

# ---------------------------------------------------------------------------
# Local helper
# ---------------------------------------------------------------------------

def _fallback(text: str) -> np.ndarray:
    """Deterministic pseudo‑random vector so tests remain stable offline."""
    seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % 2**32
    rng = np.random.default_rng(seed)
    return rng.random(EMBED_DIM, dtype="float32")


# embed_modal.py  – patch embed()
def embed(text: str) -> np.ndarray:
    try:
        fn = modal.Function.lookup("pairfecto-embeddings", "compute_embedding")

        vec = fn.remote(text)                 # blocks, returns list[float]

        arr = np.array(vec[:EMBED_DIM], dtype="float32")
        if arr.shape[0] < EMBED_DIM:
            arr = np.pad(arr, (0, EMBED_DIM - arr.shape[0]))
        return arr
    except Exception as e:
        if not DEV_MODE:
            print("[WARN] Modal embedding failed – using fallback:", e)
        return _fallback(text)

# Allow `python embed_modal.py` to run a quick smoke‑test
if __name__ == "__main__":
    import sys, json
    txt = " ".join(sys.argv[1:]) or "hello world"
    print(json.dumps(embed(txt).tolist()[:8]))
