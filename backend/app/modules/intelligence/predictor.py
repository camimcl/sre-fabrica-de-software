"""Integrity-checked local inference for approved model artifacts."""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import joblib

from app.modules.intelligence.contracts import (
    MetricFeatures,
    RiskPredictionResult,
)
from app.modules.intelligence.dataset import FEATURE_NAMES, feature_vector
from app.modules.intelligence.models import ModelVersion


class ArtifactValidationError(RuntimeError):
    pass


def model_directory() -> Path:
    return Path(os.getenv("LOADFORGE_MODEL_DIR", "models/artifacts")).resolve()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_artifact_path(relative_path: str) -> Path:
    root = model_directory()
    candidate = (root / relative_path).resolve()
    if candidate.parent != root:
        raise ArtifactValidationError("Model artifact path escapes the model directory")
    return candidate


class SklearnRiskPredictor:
    def __init__(self, model: ModelVersion) -> None:
        path = resolve_artifact_path(model.artifact_path)
        if not path.is_file():
            raise ArtifactValidationError("Model artifact was not found")
        if file_sha256(path) != model.artifact_sha256:
            raise ArtifactValidationError("Model artifact integrity check failed")
        artifact = joblib.load(path)
        if tuple(artifact.get("feature_names", ())) != FEATURE_NAMES:
            raise ArtifactValidationError("Model feature schema is incompatible")
        if artifact.get("version") != model.version:
            raise ArtifactValidationError("Model artifact version is incompatible")
        self._estimator = artifact["estimator"]
        self._version = model.version

    def predict_risk(self, features: MetricFeatures) -> RiskPredictionResult:
        started = time.perf_counter()
        probability = float(
            self._estimator.predict_proba([feature_vector(features)])[0][1]
        )
        latency_ms = max(0, round((time.perf_counter() - started) * 1000))
        return RiskPredictionResult(
            probability=probability,
            predicted_degradation=probability >= 0.5,
            model_version=self._version,
            inference_latency_ms=latency_ms,
        )
