"""
app/semantic/embedder.py

Embedding engine for Surveyor AI semantic layer.

RESPONSIBILITIES:
    Load the sentence-transformers model once, compute embeddings
    for all survey items, detect instrument mode, and return a
    structured EmbeddingResult.

DESIGN DECISIONS:
    - Embeddings are NOT stored in item dicts — they are not
      JSON-serializable and would break the reporting layer.
    - Embeddings live in EmbeddingResult, passed alongside item
      dicts through the pipeline.
    - Mode detection is automatic:
        STRUCTURED   — all items have non-None construct_block
        UNSTRUCTURED — any item has None construct_block
    - Model is loaded once per EmbeddingEngine instance.
      In the API, instantiate once at startup, not per request.

MODEL:
    all-MiniLM-L6-v2 — 80MB, fast on CPU, strong on short sentences.
    Produces 384-dimensional vectors. Well-suited for survey items
    which are typically 10-30 words.

LIMITATIONS:
    - Embeddings reflect surface linguistic similarity, not construct
      validity. Two items can be semantically similar without measuring
      the same construct, and vice versa.
    - All outputs from this layer are signals for expert review,
      not confirmed findings.
"""

import numpy as np
from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer
from typing import Optional


MODEL_NAME = "all-MiniLM-L6-v2"


@dataclass
class EmbeddingResult:
    """
    Container for all embedding data produced by EmbeddingEngine.

    Attributes:
        item_ids (list[int]):
            Ordered list of item IDs matching the embedding matrix rows.
        embeddings (np.ndarray):
            Matrix of shape (n_items, embedding_dim).
            Row i corresponds to item_ids[i].
        block_centroids (dict[int, np.ndarray]):
            Maps construct_block number to mean embedding vector
            for that block. Empty dict in UNSTRUCTURED mode.
        mode (str):
            "STRUCTURED" or "UNSTRUCTURED".
        block_map (dict[int, int]):
            Maps item_id -> construct_block.
            Empty dict in UNSTRUCTURED mode.
    """
    item_ids: list
    embeddings: np.ndarray
    block_centroids: dict
    mode: str
    block_map: dict

    def embedding_for(self, item_id: int) -> Optional[np.ndarray]:
        """Return the embedding vector for a given item_id."""
        if item_id not in self.item_ids:
            return None
        idx = self.item_ids.index(item_id)
        return self.embeddings[idx]

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def similarity_to_centroid(self, item_id: int) -> Optional[float]:
        """
        Return cosine similarity between an item's embedding and
        its block centroid. Returns None in UNSTRUCTURED mode or
        if item has no block assignment.
        """
        if self.mode == "UNSTRUCTURED":
            return None
        block = self.block_map.get(item_id)
        if block is None:
            return None
        centroid = self.block_centroids.get(block)
        if centroid is None:
            return None
        vec = self.embedding_for(item_id)
        if vec is None:
            return None
        return self.cosine_similarity(vec, centroid)


class EmbeddingEngine:
    """
    Loads the sentence-transformers model and computes embeddings
    for survey items.

    Usage:
        engine = EmbeddingEngine()
        result = engine.embed(items)
    """

    def __init__(self, model_name: str = MODEL_NAME):
        """
        Load the model. Call once — not per request.

        Args:
            model_name (str): sentence-transformers model identifier.
        """
        self._model = SentenceTransformer(model_name)

    def embed(self, items: list) -> EmbeddingResult:
        """
        Compute embeddings for all items and detect instrument mode.

        Args:
            items (list): Item dicts from SurveyParser. Must contain
                         'item_id', 'text', 'construct_block'.

        Returns:
            EmbeddingResult: Full embedding data for the instrument.
        """
        if not items:
            raise ValueError("Cannot embed an empty item list.")

        # --- Detect mode ---
        has_blocks = all(
            item.get("construct_block") is not None
            for item in items
        )
        mode = "STRUCTURED" if has_blocks else "UNSTRUCTURED"

        # --- Extract texts and IDs ---
        item_ids = [item["item_id"] for item in items]
        texts = [item["text"] for item in items]

        # --- Compute embeddings ---
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True   # L2-normalized: dot product = cosine sim
        )

        # --- Build block map and centroids (STRUCTURED only) ---
        block_map = {}
        block_centroids = {}

        if mode == "STRUCTURED":
            for item, vec in zip(items, embeddings):
                block_map[item["item_id"]] = item["construct_block"]

            # Group embeddings by block
            block_vectors = {}
            for item_id, block in block_map.items():
                idx = item_ids.index(item_id)
                if block not in block_vectors:
                    block_vectors[block] = []
                block_vectors[block].append(embeddings[idx])

            # Compute mean centroid per block
            for block, vecs in block_vectors.items():
                block_centroids[block] = np.mean(vecs, axis=0)

        return EmbeddingResult(
            item_ids=item_ids,
            embeddings=embeddings,
            block_centroids=block_centroids,
            mode=mode,
            block_map=block_map
        )