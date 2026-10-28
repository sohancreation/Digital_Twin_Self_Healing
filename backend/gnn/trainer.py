"""
Training and validation pipeline for Bridge-Aware GNN Cyber-Resilience models.
Implements multi-task optimization for simultaneous 5-class attack classification
and continuous behavioral trust prediction.
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from .model import DualHeadGNNClassifier
from .dataset import GraphSnapshotDataset, GraphSnapshotBatch


class GNNTrainer:
    """
    Coordinates training, validation, metric evaluation, and model checkpointing
    for DualHeadGNNClassifier.
    """

    def __init__(
        self,
        model: DualHeadGNNClassifier,
        lr: float = 3e-4,
        weight_decay: float = 1e-4,
        loss_alpha: float = 0.65,  # Classification vs trust MSE weight
        class_weights: Optional[torch.Tensor] = None,
        device: Optional[torch.device] = None,
    ):
        self.device = device or torch.device("cpu")
        self.model = model.to(self.device)
        self.loss_alpha = loss_alpha

        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=lr,
            weight_decay=weight_decay,
        )
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=50,
            eta_min=1e-5,
        )

        if class_weights is not None:
            self.ce_loss = nn.CrossEntropyLoss(weight=class_weights.to(self.device))
        else:
            self.ce_loss = nn.CrossEntropyLoss()
        self.mse_loss = nn.MSELoss()

    def train_epoch(self, dataloader: DataLoader) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        total_ce = 0.0
        total_mse = 0.0
        n_batches = 0

        for batch in dataloader:
            if not isinstance(batch, GraphSnapshotBatch):
                continue
            x = batch.x.to(self.device)
            edge_index = batch.edge_index.to(self.device)
            edge_attr = batch.edge_attr.to(self.device)
            bridge_mask = batch.bridge_mask.to(self.device)
            labels_att = batch.labels_attack.to(self.device)
            labels_tr = batch.labels_trust.to(self.device)

            self.optimizer.zero_grad()
            logits, trust_pred, _ = self.model(x, edge_index, edge_attr, bridge_mask)

            loss_cls = self.ce_loss(logits, labels_att)
            loss_reg = self.mse_loss(trust_pred, labels_tr)
            loss = (self.loss_alpha * loss_cls) + ((1.0 - self.loss_alpha) * loss_reg)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=2.0)
            self.optimizer.step()

            total_loss += loss.item()
            total_ce += loss_cls.item()
            total_mse += loss_reg.item()
            n_batches += 1

        self.scheduler.step()
        n = max(1, n_batches)
        return {
            "loss": total_loss / n,
            "loss_cls": total_ce / n,
            "loss_reg": total_mse / n,
            "lr": self.optimizer.param_groups[0]["lr"],
        }

    @torch.no_grad()
    def evaluate(self, dataloader: DataLoader, return_raw_outputs: bool = False) -> Dict[str, Any]:
        self.model.eval()
        all_preds = []
        all_targets = []
        all_probs = []
        all_trust_preds = []
        all_trust_targets = []

        total_loss = 0.0
        n_batches = 0

        for batch in dataloader:
            if not isinstance(batch, GraphSnapshotBatch):
                continue
            x = batch.x.to(self.device)
            edge_index = batch.edge_index.to(self.device)
            edge_attr = batch.edge_attr.to(self.device)
            bridge_mask = batch.bridge_mask.to(self.device)
            labels_att = batch.labels_attack.to(self.device)
            labels_tr = batch.labels_trust.to(self.device)

            logits, trust_pred, _ = self.model(x, edge_index, edge_attr, bridge_mask)

            loss_cls = self.ce_loss(logits, labels_att)
            loss_reg = self.mse_loss(trust_pred, labels_tr)
            loss = (self.loss_alpha * loss_cls) + ((1.0 - self.loss_alpha) * loss_reg)
            total_loss += loss.item()
            n_batches += 1

            probs = F.softmax(logits, dim=-1).cpu().numpy()
            preds = np.argmax(probs, axis=-1)

            all_preds.extend(preds)
            all_probs.extend(probs)
            all_targets.extend(labels_att.cpu().numpy())
            all_trust_preds.extend(trust_pred.cpu().numpy())
            all_trust_targets.extend(labels_tr.cpu().numpy())

        all_preds = np.array(all_preds)
        all_targets = np.array(all_targets)
        all_probs = np.array(all_probs)
        all_trust_preds = np.array(all_trust_preds)
        all_trust_targets = np.array(all_trust_targets)

        # Classification metrics
        acc = float(np.mean(all_preds == all_targets)) if len(all_targets) > 0 else 0.0

        classes = [0, 1, 2, 3, 4]
        class_names = ["normal", "dos", "compromised_node", "node_failure", "on_off"]
        f1_scores = []
        per_class_metrics = {}

        # 5x5 Confusion Matrix
        conf_mat = np.zeros((5, 5), dtype=int)
        for t, p in zip(all_targets, all_preds):
            if 0 <= t < 5 and 0 <= p < 5:
                conf_mat[t, p] += 1

        # Per-class precision, recall, F1, and one-vs-rest ROC-AUC
        roc_auc_per_class = {}
        for c, name in zip(classes, class_names):
            tp = int(np.sum((all_preds == c) & (all_targets == c)))
            fp = int(np.sum((all_preds == c) & (all_targets != c)))
            fn = int(np.sum((all_preds != c) & (all_targets == c)))

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (fn + tp) if (fn + tp) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

            # One-vs-Rest ROC-AUC calculation
            binary_target = (all_targets == c).astype(int)
            class_scores = all_probs[:, c] if len(all_probs) > 0 else np.zeros(len(all_targets))
            if np.sum(binary_target) > 0 and np.sum(1 - binary_target) > 0:
                try:
                    from sklearn.metrics import roc_auc_score
                    auc_val = float(roc_auc_score(binary_target, class_scores))
                except Exception:
                    auc_val = 0.5
            else:
                auc_val = 1.0

            f1_scores.append(f1)
            roc_auc_per_class[name] = auc_val
            per_class_metrics[name] = {
                "precision": float(prec),
                "recall": float(rec),
                "f1": float(f1),
                "roc_auc": float(auc_val),
                "support": int(np.sum(all_targets == c)),
            }

        macro_f1 = float(np.mean(f1_scores))
        macro_auc = float(np.mean(list(roc_auc_per_class.values())))

        # Trust regression metrics
        trust_mae = float(np.mean(np.abs(all_trust_preds - all_trust_targets))) if len(all_trust_targets) > 0 else 0.0
        trust_rmse = float(np.sqrt(np.mean((all_trust_preds - all_trust_targets) ** 2))) if len(all_trust_targets) > 0 else 0.0
        ss_tot = float(np.sum((all_trust_targets - np.mean(all_trust_targets)) ** 2)) if len(all_trust_targets) > 0 else 0.0
        ss_res = float(np.sum((all_trust_targets - all_trust_preds) ** 2)) if len(all_trust_targets) > 0 else 0.0
        trust_r2 = float(1.0 - (ss_res / max(1e-6, ss_tot))) if ss_tot > 0 else 0.0

        n = max(1, n_batches)
        result = {
            "val_loss": total_loss / n,
            "accuracy": acc,
            "macro_f1": macro_f1,
            "macro_auc": macro_auc,
            "trust_mae": trust_mae,
            "trust_rmse": trust_rmse,
            "trust_r2": trust_r2,
            "per_class": per_class_metrics,
            "confusion_matrix": conf_mat.tolist(),
        }

        if return_raw_outputs:
            result["all_preds"] = all_preds.tolist()
            result["all_targets"] = all_targets.tolist()
            result["all_probs"] = all_probs.tolist()
            result["all_trust_preds"] = all_trust_preds.tolist()
            result["all_trust_targets"] = all_trust_targets.tolist()

        return result

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 40,
        checkpoint_path: Optional[Path] = None,
        early_stopping_patience: int = 10,
    ) -> Dict[str, Any]:
        best_f1 = -1.0
        best_loss = float("inf")
        best_epoch = 0
        patience_counter = 0
        history = []
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=epochs,
            eta_min=1e-5,
        )

        for ep in range(1, epochs + 1):
            t_start = time.perf_counter()
            train_metrics = self.train_epoch(train_loader)
            val_metrics = self.evaluate(val_loader)
            dur = time.perf_counter() - t_start

            record = {
                "epoch": ep,
                "duration_s": dur,
                **train_metrics,
                **val_metrics,
            }
            history.append(record)

            curr_f1 = val_metrics["macro_f1"]
            curr_loss = val_metrics["val_loss"]
            is_better = (curr_f1 > best_f1 + 1e-6) or (abs(curr_f1 - best_f1) <= 1e-6 and curr_loss < best_loss)

            if is_better:
                best_f1 = curr_f1
                best_loss = curr_loss
                best_epoch = ep
                patience_counter = 0
                if checkpoint_path:
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    torch.save(
                        {
                            "epoch": ep,
                            "model_state_dict": self.model.state_dict(),
                            "best_macro_f1": best_f1,
                            "metrics": val_metrics,
                        },
                        checkpoint_path,
                    )
            else:
                patience_counter += 1

            if ep == 1 or ep % 5 == 0 or ep == epochs or is_better:
                print(
                    f"Epoch {ep:3d}/{epochs:3d} | "
                    f"Train Loss: {train_metrics['loss']:.4f} | "
                    f"Val Loss: {val_metrics['val_loss']:.4f} | "
                    f"Val Acc: {val_metrics['accuracy']*100:.2f}% | "
                    f"Val F1: {val_metrics['macro_f1']*100:.2f}% | "
                    f"Trust R2: {val_metrics['trust_r2']:.4f} | "
                    f"LR: {train_metrics['lr']:.2e} ({dur:.1f}s)"
                    f"{' *BEST*' if is_better else ''}"
                )

            if early_stopping_patience is not None and patience_counter >= early_stopping_patience:
                print(f"Early stopping triggered at epoch {ep} (patience={early_stopping_patience})")
                break

        return {
            "best_epoch": best_epoch,
            "best_macro_f1": best_f1,
            "history": history,
        }
