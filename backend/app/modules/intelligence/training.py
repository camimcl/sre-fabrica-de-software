"""Chronological local training and candidate model versioning."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.types import ModelStatus
from app.modules.intelligence.dataset import (
    FEATURE_NAMES,
    MIN_TRAINING_SAMPLES,
    PREDICTION_HORIZON_WINDOWS,
    build_training_samples,
    dataset_sha256,
    feature_vector,
)
from app.modules.intelligence.models import ModelVersion
from app.modules.intelligence.predictor import file_sha256, model_directory


class TrainingDataError(ValueError):
    pass


def _score(estimator, x_test, y_test) -> dict[str, float]:
    predicted = estimator.predict(x_test)
    return {
        "precision": float(precision_score(y_test, predicted, zero_division=0)),
        "recall": float(recall_score(y_test, predicted, zero_division=0)),
        "f1": float(f1_score(y_test, predicted, zero_division=0)),
        "accuracy": float(accuracy_score(y_test, predicted)),
        "false_positives": int(confusion_matrix(y_test, predicted, labels=[0, 1])[0, 1]),
    }


def chronological_partitions(samples):
    first, second = int(len(samples) * 0.6), int(len(samples) * 0.8)
    validation_start, test_start = samples[first].observed_at, samples[second].observed_at
    # Purge labels whose future horizon reaches the next partition.
    train = [s for s in samples[:first] if s.label_ends_at < validation_start]
    validation = [s for s in samples[first:second] if s.label_ends_at < test_start]
    test = samples[second:]
    for partition in (train, validation, test):
        if len({s.degraded_within_horizon for s in partition}) < 2:
            raise TrainingDataError("Chronological train, validation and test partitions must contain both classes after horizon purging")
    return train, validation, test


def train_candidate(db: Session) -> ModelVersion:
    samples = build_training_samples(db)
    if len(samples) < MIN_TRAINING_SAMPLES:
        raise TrainingDataError(
            f"At least {MIN_TRAINING_SAMPLES} chronological samples are required"
        )
    labels = [int(sample.degraded_within_horizon) for sample in samples]
    if len(set(labels)) < 2:
        raise TrainingDataError("Training data must contain both degradation classes")

    train, validation, test = chronological_partitions(samples)
    x_train = [feature_vector(s.features) for s in train]
    y_train = [int(s.degraded_within_horizon) for s in train]
    x_validation = [feature_vector(s.features) for s in validation]
    y_validation = [int(s.degraded_within_horizon) for s in validation]
    x_test = [feature_vector(s.features) for s in test]
    y_test = [int(s.degraded_within_horizon) for s in test]

    candidates = {
        "logistic-regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)
        ),
        "random-forest": RandomForestClassifier(
            n_estimators=120, max_depth=8, random_state=42, n_jobs=1
        ),
    }
    evaluated: list[tuple[str, object, dict[str, float]]] = []
    for name, estimator in candidates.items():
        estimator.fit(x_train, y_train)
        evaluated.append((name, estimator, _score(estimator, x_validation, y_validation)))
    algorithm, estimator, _ = max(
        evaluated,
        key=lambda item: (
            item[2]["f1"], item[2]["recall"], item[2]["precision"], item[0]
        ),
    )
    metrics = _score(estimator, x_test, y_test)

    dataset_hash = dataset_sha256(samples)
    version = datetime.now(timezone.utc).strftime("lf-%Y%m%d%H%M%S%f")
    directory = model_directory()
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{version}.joblib"
    path = directory / filename
    joblib.dump(
        {
            "version": version,
            "feature_names": FEATURE_NAMES,
            "estimator": estimator,
        },
        path,
    )

    notes = json.dumps(
        {
            "split": "chronological-60-20-20-purged",
            "prediction_horizon": {
                "kind": "future_windows",
                "window_count": PREDICTION_HORIZON_WINDOWS,
                "nominal_seconds": 10,
                "observed_min_seconds": min((s.label_ends_at - s.observed_at).total_seconds() for s in samples),
                "observed_max_seconds": max((s.label_ends_at - s.observed_at).total_seconds() for s in samples),
            },
            "train_samples": len(train),
            "validation_samples": len(validation),
            "test_samples": len(test),
            "purged_samples": len(samples) - len(train) - len(validation) - len(test),
            "test_metrics": metrics,
            "evaluated": {name: score for name, _, score in evaluated},
        },
        sort_keys=True,
    )
    model = ModelVersion(
        version=version,
        algorithm=algorithm,
        artifact_path=filename,
        status=ModelStatus.CANDIDATE,
        precision_score=Decimal(str(round(metrics["precision"], 5))),
        recall_score=Decimal(str(round(metrics["recall"], 5))),
        f1_score=Decimal(str(round(metrics["f1"], 5))),
        accuracy_score=Decimal(str(round(metrics["accuracy"], 5))),
        training_sample_count=len(samples),
        training_dataset_hash=dataset_hash,
        artifact_sha256=file_sha256(path),
        notes=notes,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def approve_candidate(db: Session, model: ModelVersion) -> ModelVersion:
    from app.modules.intelligence.predictor import SklearnRiskPredictor

    SklearnRiskPredictor(model)  # validate before changing approval state
    for approved in db.scalars(
        select(ModelVersion).where(ModelVersion.status == ModelStatus.APPROVED)
    ):
        approved.status = ModelStatus.RETIRED
    db.flush()
    model.status = ModelStatus.APPROVED
    db.commit()
    db.refresh(model)
    return model
