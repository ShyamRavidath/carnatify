"""Tests for the raga classification module."""

import numpy as np
import pytest
import torch

from carnatify.schemas import AudioFeatures, RagaPrediction
from carnatify.ml.raga_dataset import (
    DEFAULT_CONTOUR_LENGTH,
    AddGaussianNoise,
    PitchShiftContour,
    PitchShiftPCD,
    RagaDataset,
    RagaLabelEncoder,
    default_augmentation,
    features_to_vector,
    fixed_length_contour,
)
from carnatify.ml.raga_model import RagaCNN, RagaTDNN
from carnatify.ml.raga_trainer import RagaTrainer


RAGAS = ["kalyani", "todi", "shankarabharanam", "bhairavi"]


def make_features(seed: int = 0) -> AudioFeatures:
    rng = np.random.default_rng(seed)
    pcd = rng.random(12).astype(np.float32)
    pcd /= pcd.sum()
    contour = rng.normal(0, 300, size=5000).astype(np.float32)
    return AudioFeatures(
        pitch_contour=np.abs(contour) + 100,
        tonic_hz=146.0,
        normalized_pitch_contour=contour,
        pitch_class_distribution=pcd,
        sample_rate=44100,
        duration_seconds=10.0,
    )


def make_dataset(mode: str, n: int = 40) -> RagaDataset:
    features = [make_features(i) for i in range(n)]
    labels = [RAGAS[i % len(RAGAS)] for i in range(n)]
    encoder = RagaLabelEncoder(RAGAS)
    return RagaDataset(features, labels, label_encoder=encoder, mode=mode)


class TestLabelEncoder:
    def test_roundtrip(self):
        encoder = RagaLabelEncoder(RAGAS)
        for name in RAGAS:
            assert encoder.decode(encoder.encode(name)) == name

    def test_deterministic_sorted_order(self):
        e1 = RagaLabelEncoder(["c", "a", "b"])
        e2 = RagaLabelEncoder(["b", "c", "a"])
        assert e1.classes == e2.classes == ["a", "b", "c"]

    def test_unknown_raga_raises(self):
        encoder = RagaLabelEncoder(RAGAS)
        with pytest.raises(KeyError):
            encoder.encode("nonexistent")

    def test_save_load(self, tmp_path):
        encoder = RagaLabelEncoder(RAGAS)
        path = tmp_path / "labels.json"
        encoder.save(path)
        loaded = RagaLabelEncoder.load(path)
        assert loaded.classes == encoder.classes


class TestFeatureHelpers:
    def test_fixed_length_pad(self):
        out = fixed_length_contour(np.ones(100, dtype=np.float32), length=400)
        assert out.shape == (400,)
        assert out.sum() == pytest.approx(100.0)

    def test_fixed_length_crop(self):
        out = fixed_length_contour(np.ones(800, dtype=np.float32), length=400)
        assert out.shape == (400,)

    def test_features_to_vector_pcd(self):
        feats = make_features()
        vec = features_to_vector(feats, mode="pcd")
        assert vec.shape == (12,)

    def test_features_to_vector_contour(self):
        feats = make_features()
        vec = features_to_vector(feats, mode="contour")
        assert vec.shape == (DEFAULT_CONTOUR_LENGTH,)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            features_to_vector(make_features(), mode="bogus")


class TestAugmentation:
    def test_pcd_pitch_shift_preserves_mass(self):
        x = np.array([0.5, 0.3, 0.2] + [0.0] * 9, dtype=np.float32)
        out = PitchShiftPCD()(x)
        assert out.shape == x.shape
        assert out.sum() == pytest.approx(x.sum())

    def test_contour_pitch_shift_leaves_unvoiced(self):
        x = np.array([0.0, 100.0, 0.0, 200.0], dtype=np.float32)
        out = PitchShiftContour(max_cents=50.0)(x)
        assert out[0] == 0.0
        assert out[2] == 0.0

    def test_gaussian_noise_changes_values(self):
        x = np.ones(50, dtype=np.float32)
        out = AddGaussianNoise(std=0.1)(x)
        assert out.shape == x.shape
        assert not np.allclose(out, x)

    def test_default_augmentation_runs(self):
        aug = default_augmentation("pcd")
        x = make_features().pitch_class_distribution
        assert aug(x).shape == x.shape


class TestDataset:
    def test_pcd_item_shape(self):
        ds = make_dataset("pcd")
        x, y = ds[0]
        assert x.shape == (12,)
        assert y.dtype == torch.long

    def test_contour_item_shape(self):
        ds = make_dataset("contour")
        x, y = ds[0]
        assert x.shape == (1, DEFAULT_CONTOUR_LENGTH)

    def test_length_and_num_classes(self):
        ds = make_dataset("pcd", n=20)
        assert len(ds) == 20
        assert ds.num_classes == len(RAGAS)

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            RagaDataset([make_features()], ["a", "b"], mode="pcd")

    def test_transform_applied(self):
        features = [make_features(i) for i in range(4)]
        labels = [RAGAS[i] for i in range(4)]
        ds = RagaDataset(
            features,
            labels,
            label_encoder=RagaLabelEncoder(RAGAS),
            mode="pcd",
            transform=AddGaussianNoise(std=0.5),
        )
        x, _ = ds[0]
        raw = features_to_vector(features[0], mode="pcd")
        assert not np.allclose(x.numpy(), raw)


class TestModels:
    def test_tdnn_forward_shape(self):
        model = RagaTDNN(num_ragas=len(RAGAS))
        out = model(torch.randn(8, 12))
        assert out.shape == (8, len(RAGAS))

    def test_cnn_forward_shape(self):
        model = RagaCNN(num_ragas=len(RAGAS), input_length=DEFAULT_CONTOUR_LENGTH)
        out = model(torch.randn(4, 1, DEFAULT_CONTOUR_LENGTH))
        assert out.shape == (4, len(RAGAS))

    def test_tdnn_predict_sorted(self):
        encoder = RagaLabelEncoder(RAGAS)
        model = RagaTDNN(num_ragas=len(RAGAS), label_encoder=encoder)
        preds = model.predict(make_features())
        assert all(isinstance(p, RagaPrediction) for p in preds)
        confidences = [p.confidence for p in preds]
        assert confidences == sorted(confidences, reverse=True)
        assert all(p.raga_name in RAGAS for p in preds)

    def test_cnn_predict_sorted(self):
        encoder = RagaLabelEncoder(RAGAS)
        model = RagaCNN(num_ragas=len(RAGAS), label_encoder=encoder)
        preds = model.predict(make_features())
        confidences = [p.confidence for p in preds]
        assert confidences == sorted(confidences, reverse=True)

    def test_predict_respects_top_k(self):
        encoder = RagaLabelEncoder(RAGAS)
        model = RagaTDNN(num_ragas=len(RAGAS), label_encoder=encoder)
        preds = model.predict(make_features(), top_k=2)
        assert len(preds) == 2

    def test_save_load_roundtrip(self, tmp_path):
        model = RagaTDNN(num_ragas=len(RAGAS))
        path = tmp_path / "model.pt"
        model.save(path)
        loaded = RagaTDNN(num_ragas=len(RAGAS))
        loaded.load(path)
        x = torch.randn(2, 12)
        model.eval()
        loaded.eval()
        with torch.no_grad():
            assert torch.allclose(model(x), loaded(x))


class TestTrainerAndClassifier:
    def test_train_returns_metrics(self):
        encoder = RagaLabelEncoder(RAGAS)
        train_ds = make_dataset("pcd", n=40)
        train_ds.label_encoder = encoder
        val_ds = make_dataset("pcd", n=16)
        model = RagaTDNN(num_ragas=len(RAGAS), label_encoder=encoder)
        trainer = RagaTrainer(model, epochs=2, batch_size=8, verbose=False)
        history = trainer.train(train_ds, val_ds, checkpoint_name="test_raga_tmp.pt")
        assert len(history["train_loss"]) >= 1
        assert "val_accuracy" in history
        assert "confusion_matrix" in history

    def test_evaluate_reports_per_raga(self):
        encoder = RagaLabelEncoder(RAGAS)
        model = RagaTDNN(num_ragas=len(RAGAS), label_encoder=encoder)
        trainer = RagaTrainer(model, epochs=1, batch_size=8, verbose=False)
        test_ds = make_dataset("pcd", n=20)
        metrics = trainer.evaluate(test_ds)
        assert 0.0 <= metrics["overall_accuracy"] <= 1.0
        assert isinstance(metrics["per_raga_accuracy"], dict)

    def test_classifier_end_to_end(self, tmp_path):
        encoder = RagaLabelEncoder(RAGAS)
        model = RagaTDNN(num_ragas=len(RAGAS), label_encoder=encoder)
        model_path = tmp_path / "model.pt"
        label_path = tmp_path / "labels.json"
        model.save(model_path)
        encoder.save(label_path)

        from carnatify.ml.raga_classifier import RagaClassifier

        clf = RagaClassifier(model_path, label_path, feature_mode="pcd")
        preds = clf.classify(make_features())
        assert all(isinstance(p, RagaPrediction) for p in preds)
        assert isinstance(clf.is_uncertain(preds), bool)
