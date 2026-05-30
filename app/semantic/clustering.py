"""
app/semantic/clustering.py

Construct block clustering analysis for Surveyor AI semantic layer.

RESPONSIBILITIES:
    In STRUCTURED mode:
        - Compute per-item similarity to own block centroid
        - Compute per-item similarity to all other block centroids
        - Identify items that are more similar to a foreign block
          than to their own block (cross-block affinity)
        - Compute block cohesion scores (mean intra-block similarity)

    In UNSTRUCTURED mode:
        - Report that structured clustering is unavailable
        - Return empty results — do not fabricate structure

DESIGN NOTE:
    This module produces ClusteringResult — a data container.
    It does NOT produce violations or signals.
    P018 reads ClusteringResult and decides what to flag.
    Separation of detection from judgment is maintained.

LIMITATIONS:
    Cross-block affinity is a linguistic signal, not a construct
    validity measure. An item may embed closer to a foreign block
    because it uses similar vocabulary, not because it measures
    the wrong construct. All findings require expert verification.
"""

import numpy as np
from dataclasses import dataclass, field
from app.semantic.embedder import EmbeddingResult


@dataclass
class ItemClusterProfile:
    """
    Clustering profile for a single survey item.

    Attributes:
        item_id (int):
            The item's ID.
        own_block (int):
            The block this item belongs to.
        own_block_similarity (float):
            Cosine similarity to own block centroid.
        best_foreign_block (int | None):
            Block number of highest foreign similarity. None if only one block.
        best_foreign_similarity (float | None):
            Similarity to best foreign block centroid.
        cross_block_affinity (bool):
            True if best_foreign_similarity > own_block_similarity.
            Indicates item may be linguistically closer to another construct.
    """
    item_id: int
    own_block: int
    own_block_similarity: float
    best_foreign_block: int | None
    best_foreign_similarity: float | None
    cross_block_affinity: bool


@dataclass
class BlockCohesion:
    """
    Cohesion summary for a single construct block.

    Attributes:
        block (int):            Block number.
        item_count (int):       Number of items in block.
        mean_similarity (float): Mean cosine similarity of items to centroid.
        min_similarity (float): Lowest item-centroid similarity in block.
        max_similarity (float): Highest item-centroid similarity in block.
        low_cohesion (bool):    True if mean_similarity < 0.50.
    """
    block: int
    item_count: int
    mean_similarity: float
    min_similarity: float
    max_similarity: float
    low_cohesion: bool


@dataclass
class ClusteringResult:
    """
    Full clustering analysis output.

    Attributes:
        mode (str):
            "STRUCTURED" or "UNSTRUCTURED".
        item_profiles (list[ItemClusterProfile]):
            Per-item clustering profiles. Empty in UNSTRUCTURED mode.
        block_cohesion (list[BlockCohesion]):
            Per-block cohesion summaries. Empty in UNSTRUCTURED mode.
        cross_affinity_items (list[int]):
            Item IDs with cross_block_affinity=True.
        low_cohesion_blocks (list[int]):
            Block numbers with low_cohesion=True.
    """
    mode: str
    item_profiles: list = field(default_factory=list)
    block_cohesion: list = field(default_factory=list)
    cross_affinity_items: list = field(default_factory=list)
    low_cohesion_blocks: list = field(default_factory=list)


class ClusteringAnalyzer:
    """
    Analyzes embedding structure against construct block assignments.

    Usage:
        analyzer = ClusteringAnalyzer()
        result = analyzer.analyze(embedding_result)
    """

    # Mean block similarity below this = low cohesion flag
    LOW_COHESION_THRESHOLD = 0.50

    def analyze(self, embedding_result: EmbeddingResult) -> ClusteringResult:
        """
        Run clustering analysis on an EmbeddingResult.

        Args:
            embedding_result (EmbeddingResult): Output from EmbeddingEngine.

        Returns:
            ClusteringResult: Full clustering analysis.
        """
        if embedding_result.mode == "UNSTRUCTURED":
            return ClusteringResult(
                mode="UNSTRUCTURED",
                item_profiles=[],
                block_cohesion=[],
                cross_affinity_items=[],
                low_cohesion_blocks=[]
            )

        item_profiles = self._build_item_profiles(embedding_result)
        block_cohesion = self._build_block_cohesion(
            item_profiles, embedding_result
        )

        cross_affinity_items = [
            p.item_id for p in item_profiles if p.cross_block_affinity
        ]
        low_cohesion_blocks = [
            b.block for b in block_cohesion if b.low_cohesion
        ]

        return ClusteringResult(
            mode="STRUCTURED",
            item_profiles=item_profiles,
            block_cohesion=block_cohesion,
            cross_affinity_items=cross_affinity_items,
            low_cohesion_blocks=low_cohesion_blocks
        )

    def _build_item_profiles(
        self, er: EmbeddingResult
    ) -> list:
        """Build ItemClusterProfile for every item."""
        profiles = []
        blocks = list(er.block_centroids.keys())

        for item_id in er.item_ids:
            own_block = er.block_map.get(item_id)
            if own_block is None:
                continue

            vec = er.embedding_for(item_id)
            if vec is None:
                continue

            own_sim = er.cosine_similarity(
                vec, er.block_centroids[own_block]
            )

            # Similarities to all foreign blocks
            foreign_sims = {}
            for block in blocks:
                if block == own_block:
                    continue
                foreign_sims[block] = er.cosine_similarity(
                    vec, er.block_centroids[block]
                )

            if foreign_sims:
                best_foreign_block = max(
                    foreign_sims, key=foreign_sims.get
                )
                best_foreign_sim = foreign_sims[best_foreign_block]
                cross_affinity = best_foreign_sim > own_sim
            else:
                best_foreign_block = None
                best_foreign_sim = None
                cross_affinity = False

            profiles.append(ItemClusterProfile(
                item_id=item_id,
                own_block=own_block,
                own_block_similarity=round(own_sim, 4),
                best_foreign_block=best_foreign_block,
                best_foreign_similarity=(
                    round(best_foreign_sim, 4)
                    if best_foreign_sim is not None else None
                ),
                cross_block_affinity=cross_affinity
            ))

        return profiles

    def _build_block_cohesion(
        self,
        profiles: list,
        er: EmbeddingResult
    ) -> list:
        """Build BlockCohesion summary for each block."""
        block_sims = {}
        for profile in profiles:
            b = profile.own_block
            if b not in block_sims:
                block_sims[b] = []
            block_sims[b].append(profile.own_block_similarity)

        cohesion_list = []
        for block, sims in sorted(block_sims.items()):
            mean_sim = float(np.mean(sims))
            cohesion_list.append(BlockCohesion(
                block=block,
                item_count=len(sims),
                mean_similarity=round(mean_sim, 4),
                min_similarity=round(min(sims), 4),
                max_similarity=round(max(sims), 4),
                low_cohesion=mean_sim < self.LOW_COHESION_THRESHOLD
            ))

        return cohesion_list