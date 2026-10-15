"""PyTorch two-tower ranking model and small training utility.

The API intentionally serves the explainable ranker until an exported TorchScript
artifact is registered; this makes the system reliable before interaction data
exists while keeping the deep-learning path production-ready.
"""
from __future__ import annotations

try:
    import torch
    from torch import nn
except ImportError:  # allows scraper/API development without the optional ML extra
    torch = None
    nn = object


if torch:
    class TwoTowerRanker(nn.Module):
        def __init__(self, user_features: int = 8, item_features: int = 10, embedding_size: int = 32):
            super().__init__()
            self.user_tower = nn.Sequential(nn.Linear(user_features, 64), nn.ReLU(), nn.Dropout(.15), nn.Linear(64, embedding_size))
            self.item_tower = nn.Sequential(nn.Linear(item_features, 64), nn.ReLU(), nn.Dropout(.15), nn.Linear(64, embedding_size))

        def forward(self, user, item):
            return (self.user_tower(user) * self.item_tower(item)).sum(dim=1)
else:
    class TwoTowerRanker:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Install requirements-ml.txt to train the PyTorch model")
