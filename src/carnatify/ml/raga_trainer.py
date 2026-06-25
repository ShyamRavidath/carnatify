"""Training and evaluation pipeline for raga classification models."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from carnatify.config import MODELS_DIR
from carnatify.ml.raga_dataset import RagaDataset


class RagaTrainer:
    """Trains a raga model with early stopping and checkpointing.

    The model's ``feature_mode`` must match the dataset's ``mode``; this is not
    re-checked here since both come from the same configuration.
    """

    def __init__(
        self,
        model: nn.Module,
        device: str | torch.device = "cpu",
        learning_rate: float = 1e-3,
        epochs: int = 50,
        batch_size: int = 32,
        early_stopping_patience: int = 8,
        checkpoint_dir: str | Path = MODELS_DIR,
        verbose: bool = True,
    ):
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.early_stopping_patience = early_stopping_patience
        self.checkpoint_dir = Path(checkpoint_dir)
        self.verbose = verbose

        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _loader(self, dataset: Dataset, shuffle: bool) -> DataLoader:
        return DataLoader(dataset, batch_size=self.batch_size, shuffle=shuffle)

    def _run_epoch(self, loader: DataLoader, train: bool) -> tuple[float, float]:
        self.model.train(train)
        total_loss = 0.0
        correct = 0
        total = 0
        torch.set_grad_enabled(train)
        for inputs, targets in loader:
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            if train:
                self.optimizer.zero_grad()
            logits = self.model(inputs)
            loss = self.criterion(logits, targets)
            if train:
                loss.backward()
                self.optimizer.step()
            total_loss += float(loss.item()) * targets.size(0)
            correct += int((logits.argmax(dim=-1) == targets).sum().item())
            total += targets.size(0)
        torch.set_grad_enabled(True)
        avg_loss = total_loss / max(total, 1)
        accuracy = correct / max(total, 1)
        return avg_loss, accuracy

    def train(
        self,
        train_dataset: Dataset,
        val_dataset: Dataset | None = None,
        checkpoint_name: str = "raga_model.pt",
    ) -> dict:
        """Train the model, returning per-epoch metrics and confusion matrix data."""
        train_loader = self._loader(train_dataset, shuffle=True)
        val_loader = self._loader(val_dataset, shuffle=False) if val_dataset else None

        history: dict = {
            "train_loss": [],
            "train_accuracy": [],
            "val_loss": [],
            "val_accuracy": [],
            "best_epoch": 0,
            "best_val_loss": float("inf"),
        }

        best_val_loss = float("inf")
        epochs_without_improvement = 0
        checkpoint_path = self.checkpoint_dir / checkpoint_name

        for epoch in range(1, self.epochs + 1):
            train_loss, train_acc = self._run_epoch(train_loader, train=True)
            history["train_loss"].append(train_loss)
            history["train_accuracy"].append(train_acc)

            if val_loader is not None:
                val_loss, val_acc = self._run_epoch(val_loader, train=False)
                history["val_loss"].append(val_loss)
                history["val_accuracy"].append(val_acc)
                self._log(
                    f"Epoch {epoch:3d} | train_loss={train_loss:.4f} "
                    f"train_acc={train_acc:.3f} | val_loss={val_loss:.4f} "
                    f"val_acc={val_acc:.3f}"
                )
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    history["best_epoch"] = epoch
                    history["best_val_loss"] = best_val_loss
                    epochs_without_improvement = 0
                    self._save_checkpoint(checkpoint_path)
                else:
                    epochs_without_improvement += 1
                    if epochs_without_improvement >= self.early_stopping_patience:
                        self._log(
                            f"Early stopping at epoch {epoch} "
                            f"(no improvement for {self.early_stopping_patience} epochs)"
                        )
                        break
            else:
                self._log(
                    f"Epoch {epoch:3d} | train_loss={train_loss:.4f} "
                    f"train_acc={train_acc:.3f}"
                )
                self._save_checkpoint(checkpoint_path)

        history["checkpoint_path"] = str(checkpoint_path)
        if val_dataset is not None:
            history["confusion_matrix"] = self._confusion_matrix(val_dataset)
        return history

    @torch.no_grad()
    def evaluate(self, test_dataset: Dataset) -> dict:
        """Evaluate on a held-out set, returning overall and per-raga accuracy."""
        loader = self._loader(test_dataset, shuffle=False)
        self.model.eval()

        num_classes = self._num_classes(test_dataset)
        per_class_correct = np.zeros(num_classes, dtype=np.int64)
        per_class_total = np.zeros(num_classes, dtype=np.int64)
        confusion = np.zeros((num_classes, num_classes), dtype=np.int64)
        total_loss = 0.0
        total = 0

        for inputs, targets in loader:
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            logits = self.model(inputs)
            total_loss += float(self.criterion(logits, targets).item()) * targets.size(0)
            preds = logits.argmax(dim=-1)
            for t, p in zip(targets.cpu().numpy(), preds.cpu().numpy()):
                per_class_total[t] += 1
                confusion[t, p] += 1
                if t == p:
                    per_class_correct[t] += 1
            total += targets.size(0)

        per_class_accuracy = {}
        encoder = getattr(self.model, "label_encoder", None)
        for cls in range(num_classes):
            if per_class_total[cls] == 0:
                continue
            name = encoder.decode(cls) if encoder and len(encoder) > 0 else str(cls)
            per_class_accuracy[name] = float(
                per_class_correct[cls] / per_class_total[cls]
            )

        overall = float(per_class_correct.sum() / max(per_class_total.sum(), 1))
        return {
            "overall_accuracy": overall,
            "loss": total_loss / max(total, 1),
            "per_raga_accuracy": per_class_accuracy,
            "confusion_matrix": confusion.tolist(),
        }

    @torch.no_grad()
    def _confusion_matrix(self, dataset: Dataset) -> list[list[int]]:
        loader = self._loader(dataset, shuffle=False)
        self.model.eval()
        num_classes = self._num_classes(dataset)
        confusion = np.zeros((num_classes, num_classes), dtype=np.int64)
        for inputs, targets in loader:
            inputs = inputs.to(self.device)
            preds = self.model(inputs).argmax(dim=-1).cpu().numpy()
            for t, p in zip(targets.numpy(), preds):
                confusion[t, p] += 1
        return confusion.tolist()

    def _num_classes(self, dataset: Dataset) -> int:
        if isinstance(dataset, RagaDataset):
            n = dataset.num_classes
            if n > 0:
                return n
        return int(getattr(self.model, "num_ragas"))

    def _save_checkpoint(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), path)
