"""Offline ranking-quality utilities used before model deployment."""
from __future__ import annotations


def recall_at_k(relevance: list[int], k: int = 10) -> float:
    """Recall for a relevance-sorted result list with binary labels."""
    positives = sum(relevance)
    return 0.0 if positives == 0 else sum(relevance[:k]) / positives


def ndcg_at_k(relevance: list[int], k: int = 10) -> float:
    import math
    dcg = sum(label / math.log2(index + 2) for index, label in enumerate(relevance[:k]))
    ideal = sum(1 / math.log2(index + 2) for index in range(min(sum(relevance), k)))
    return 0.0 if ideal == 0 else dcg / ideal
