"""Offline trainer for event-aware implicit-feedback data.

Expected CSV columns: user_feature_0..7, item_feature_0..9, label.  Labels are
click/purchase outcomes (1/0), sampled with time-aware negative examples.
"""
from __future__ import annotations

from pathlib import Path

import typer

from .model import TwoTowerRanker, torch

app = typer.Typer(help="Train and export the two-tower event recommendation model.")


@app.callback()
def main() -> None:
    """Offline model-training commands."""


@app.command()
def train(dataset: Path = typer.Argument(..., exists=True), output: Path = Path("artifacts/two_tower.pt"), epochs: int = 15) -> None:
    if torch is None:
        raise typer.BadParameter("PyTorch is not installed. Install requirements-ml.txt.")
    import csv
    rows = list(csv.DictReader(dataset.open(encoding="utf-8")))
    if not rows:
        raise typer.BadParameter("Dataset contains no examples")
    user = torch.tensor([[float(r[f"user_feature_{i}"]) for i in range(8)] for r in rows], dtype=torch.float32)
    item = torch.tensor([[float(r[f"item_feature_{i}"]) for i in range(10)] for r in rows], dtype=torch.float32)
    labels = torch.tensor([float(r["label"]) for r in rows], dtype=torch.float32)
    model = TwoTowerRanker()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = loss_fn(model(user, item), labels)
        loss.backward()
        optimizer.step()
    output.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    torch.jit.script(model).save(str(output))
    typer.echo(f"Saved TorchScript model to {output}; final loss={loss.item():.4f}")


if __name__ == "__main__":
    app()
