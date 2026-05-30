"""
tests/test_semantic.py

Tests for the semantic layer: embedder, clustering, redundancy.
"""

import numpy as np
import pytest
from app.semantic.embedder import EmbeddingEngine, EmbeddingResult
from app.semantic.clustering import ClusteringAnalyzer
from app.semantic.redundancy import RedundancyDetector


def make_embedding_result(embeddings, item_ids, block_map):
    """Build a minimal EmbeddingResult for testing."""
    block_centroids = {}
    block_groups = {}
    for item_id, block in block_map.items():
        if block not in block_groups:
            block_groups[block] = []
        idx = item_ids.index(item_id)
        block_groups[block].append(embeddings[idx])

    for block, vecs in block_groups.items():
        block_centroids[block] = np.mean(vecs, axis=0)

    return EmbeddingResult(
        item_ids=item_ids,
        embeddings=np.array(embeddings),
        block_centroids=block_centroids,
        mode="STRUCTURED",
        block_map=block_map
    )


class TestEmbeddingEngine:

    def test_embed_returns_correct_shape(self):
        """EmbeddingEngine produces correct embedding shape."""
        items = [
            {"item_id": 1, "text": "I lead my team effectively.",
             "construct_block": 1},
            {"item_id": 2, "text": "I reward good performance.",
             "construct_block": 1},
            {"item_id": 3, "text": "I punish non-compliance.",
             "construct_block": 2},
        ]
        engine = EmbeddingEngine()
        result = engine.embed(items)
        assert result.embeddings.shape == (3, 384)
        assert result.mode == "STRUCTURED"
        assert sorted(result.block_centroids.keys()) == [1, 2]

    def test_unstructured_mode_detected(self):
        """Items with None construct_block trigger UNSTRUCTURED mode."""
        items = [
            {"item_id": 1, "text": "I lead my team.", "construct_block": None},
            {"item_id": 2, "text": "I reward good work.", "construct_block": None},
        ]
        engine = EmbeddingEngine()
        result = engine.embed(items)
        assert result.mode == "UNSTRUCTURED"
        assert result.block_centroids == {}
        assert result.block_map == {}

    def test_similarity_to_centroid_returns_none_in_unstructured(self):
        """similarity_to_centroid returns None in UNSTRUCTURED mode."""
        items = [
            {"item_id": 1, "text": "I lead.", "construct_block": None},
        ]
        engine = EmbeddingEngine()
        result = engine.embed(items)
        assert result.similarity_to_centroid(1) is None

    def test_embeddings_are_normalized(self):
        """Embeddings are L2-normalized (norm ~= 1.0)."""
        items = [
            {"item_id": 1, "text": "I lead my team.", "construct_block": 1},
        ]
        engine = EmbeddingEngine()
        result = engine.embed(items)
        norm = np.linalg.norm(result.embeddings[0])
        assert abs(norm - 1.0) < 1e-5


class TestRedundancyDetector:

    def test_high_redundancy_detected_on_near_duplicates(self):
        """RedundancyDetector fires HIGH on near-identical items."""
        engine = EmbeddingEngine()
        # Two near-identical items — should produce similarity >= 0.92
        items = [
            {"item_id": 1,
             "text": "I reward my staff for excellent performance.",
             "construct_block": 1},
            {"item_id": 2,
             "text": "I give rewards to my staff for excellent performance.",
             "construct_block": 1},
            {"item_id": 3,
             "text": "I punish non-compliant personnel.",
             "construct_block": 2},
        ]
        er = engine.embed(items)
        detector = RedundancyDetector()
        result = detector.detect(er)
        assert len(result.high_redundancy_pairs) >= 1
        pair = result.high_redundancy_pairs[0]
        assert pair.similarity >= 0.92

    def test_no_redundancy_on_diverse_items(self):
        """RedundancyDetector returns no pairs for semantically diverse items."""
        engine = EmbeddingEngine()
        items = [
            {"item_id": 1, "text": "I lead my team effectively.",
             "construct_block": 1},
            {"item_id": 2, "text": "I punish non-compliance harshly.",
             "construct_block": 1},
            {"item_id": 3, "text": "I inspire trust through expertise.",
             "construct_block": 1},
        ]
        er = engine.embed(items)
        detector = RedundancyDetector()
        result = detector.detect(er)
        assert len(result.high_redundancy_pairs) == 0

    def test_unstructured_mode_runs_without_error(self):
        """RedundancyDetector handles UNSTRUCTURED mode cleanly."""
        engine = EmbeddingEngine()
        items = [
            {"item_id": 1, "text": "I lead my team.", "construct_block": None},
            {"item_id": 2, "text": "I reward my team.", "construct_block": None},
        ]
        er = engine.embed(items)
        detector = RedundancyDetector()
        result = detector.detect(er)
        assert result.mode == "UNSTRUCTURED"


class TestClusteringAnalyzer:

    def test_structured_mode_produces_profiles(self):
        """ClusteringAnalyzer produces item profiles in STRUCTURED mode."""
        engine = EmbeddingEngine()
        items = [
            {"item_id": 1, "text": "I lead my team effectively.",
             "construct_block": 1},
            {"item_id": 2, "text": "I reward good performance.",
             "construct_block": 1},
            {"item_id": 3, "text": "I punish non-compliance.",
             "construct_block": 2},
            {"item_id": 4, "text": "I sanction rule violations.",
             "construct_block": 2},
        ]
        er = engine.embed(items)
        analyzer = ClusteringAnalyzer()
        result = analyzer.analyze(er)
        assert result.mode == "STRUCTURED"
        assert len(result.item_profiles) == 4
        assert len(result.block_cohesion) == 2

    def test_unstructured_mode_returns_empty(self):
        """ClusteringAnalyzer returns empty results in UNSTRUCTURED mode."""
        engine = EmbeddingEngine()
        items = [
            {"item_id": 1, "text": "I lead.", "construct_block": None},
            {"item_id": 2, "text": "I reward.", "construct_block": None},
        ]
        er = engine.embed(items)
        analyzer = ClusteringAnalyzer()
        result = analyzer.analyze(er)
        assert result.mode == "UNSTRUCTURED"
        assert result.item_profiles == []
        assert result.block_cohesion == []