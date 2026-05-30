"""
app/semantic/redundancy.py

Within-construct redundancy detection for Surveyor AI semantic layer.

RESPONSIBILITIES:
    Identify survey items that are semantically near-duplicate within
    the same construct block. High cosine similarity between two items
    in the same block suggests they are measuring the same thing with
    different words — producing redundant data and inflating apparent
    reliability without adding validity.

THRESHOLDS:
    >= 0.92 — HIGH redundancy. Strong signal. Confidence: 0.85.
               Items are near-paraphrases of each other.
    >= 0.85 — ELEVATED redundancy. Moderate signal. Confidence: 0.60.
               Items share substantial semantic content.
    <  0.85 — Normal within-construct similarity. Not flagged.

DESIGN NOTE:
    Only within-block pairs are checked. Cross-block similarity is
    handled by clustering.py. This separation keeps each module
    focused on one detection task.

    Redundancy detection runs in both STRUCTURED and UNSTRUCTURED mode.
    In UNSTRUCTURED mode, all items are treated as one block.

LIMITATIONS:
    Semantic similarity is not the same as psychometric redundancy.
    Two items can be semantically similar but tap different facets
    of a construct. All findings require expert review.
    Confidence scores reflect detection certainty, not confirmed redundancy.
"""

import numpy as np
from dataclasses import dataclass, field
from app.semantic.embedder import EmbeddingResult


@dataclass
class RedundantPair:
    """
    A pair of items flagged as potentially redundant.

    Attributes:
        item_id_a (int):        First item ID.
        item_id_b (int):        Second item ID.
        similarity (float):     Cosine similarity between the two items.
        level (str):            "HIGH" or "ELEVATED".
        confidence (float):     Detection confidence.
        same_block (bool):      True if both items are in the same block.
        block (int | None):     Block number if same_block, else None.
    """
    item_id_a: int
    item_id_b: int
    similarity: float
    level: str
    confidence: float
    same_block: bool
    block: int | None


@dataclass
class RedundancyResult:
    """
    Full redundancy analysis output.

    Attributes:
        mode (str):                     "STRUCTURED" or "UNSTRUCTURED".
        redundant_pairs (list):         All flagged RedundantPair objects.
        high_redundancy_pairs (list):   Subset at HIGH level.
        elevated_redundancy_pairs (list): Subset at ELEVATED level.
        affected_items (list[int]):     Unique item IDs involved in any pair.
    """
    mode: str
    redundant_pairs: list = field(default_factory=list)
    high_redundancy_pairs: list = field(default_factory=list)
    elevated_redundancy_pairs: list = field(default_factory=list)
    affected_items: list = field(default_factory=list)


class RedundancyDetector:
    """
    Detects semantically redundant item pairs within construct blocks.

    Usage:
        detector = RedundancyDetector()
        result = detector.detect(embedding_result)
    """

    HIGH_THRESHOLD = 0.92
    ELEVATED_THRESHOLD = 0.85

    def detect(self, embedding_result: EmbeddingResult) -> RedundancyResult:
        """
        Run redundancy detection on an EmbeddingResult.

        Args:
            embedding_result (EmbeddingResult): Output from EmbeddingEngine.

        Returns:
            RedundancyResult: All flagged redundant pairs.
        """
        er = embedding_result
        mode = er.mode

        # In UNSTRUCTURED mode, treat all items as one block
        if mode == "UNSTRUCTURED":
            block_groups = {0: er.item_ids}
        else:
            # Group item_ids by block
            block_groups = {}
            for item_id, block in er.block_map.items():
                if block not in block_groups:
                    block_groups[block] = []
                block_groups[block].append(item_id)

        all_pairs = []

        for block, item_ids in block_groups.items():
            if len(item_ids) < 2:
                continue

            # Get embeddings for this block's items in order
            vecs = []
            ids = []
            for item_id in item_ids:
                vec = er.embedding_for(item_id)
                if vec is not None:
                    vecs.append(vec)
                    ids.append(item_id)

            if len(vecs) < 2:
                continue

            matrix = np.array(vecs)

            # Compute pairwise similarities
            # Since embeddings are L2-normalized, dot product = cosine sim
            sim_matrix = matrix @ matrix.T

            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    sim = float(sim_matrix[i, j])

                    if sim >= self.HIGH_THRESHOLD:
                        all_pairs.append(RedundantPair(
                            item_id_a=ids[i],
                            item_id_b=ids[j],
                            similarity=round(sim, 4),
                            level="HIGH",
                            confidence=0.85,
                            same_block=(mode == "STRUCTURED"),
                            block=block if mode == "STRUCTURED" else None
                        ))
                    elif sim >= self.ELEVATED_THRESHOLD:
                        all_pairs.append(RedundantPair(
                            item_id_a=ids[i],
                            item_id_b=ids[j],
                            similarity=round(sim, 4),
                            level="ELEVATED",
                            confidence=0.60,
                            same_block=(mode == "STRUCTURED"),
                            block=block if mode == "STRUCTURED" else None
                        ))

        high = [p for p in all_pairs if p.level == "HIGH"]
        elevated = [p for p in all_pairs if p.level == "ELEVATED"]

        affected = sorted(set(
            item_id
            for pair in all_pairs
            for item_id in [pair.item_id_a, pair.item_id_b]
        ))

        return RedundancyResult(
            mode=mode,
            redundant_pairs=all_pairs,
            high_redundancy_pairs=high,
            elevated_redundancy_pairs=elevated,
            affected_items=affected
        )