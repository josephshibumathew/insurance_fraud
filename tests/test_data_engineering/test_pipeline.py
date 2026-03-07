from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ml_models.data.augmentation import preprocess_yolo_dataset
from ml_models.data.data_loader import load_image_manifest, load_raw_data
from ml_models.data.data_validation import generate_data_quality_report
from ml_models.data.dataset import ClaimsTabularDataset, create_dataloader
from ml_models.data.imbalance import random_undersample_train
from ml_models.data.preprocessing import preprocess_and_split


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    rows = []
    for index in range(120):
        rows.append(
            {
                "policy_type": "Sedan" if index % 2 == 0 else "SUV",
                "claim_amount": float(1000 + index * 10),
                "accident_location": "urban" if index % 3 == 0 else "rural",
                "vehicle_age": float((index % 15) + 1),
                "driver_age": float((index % 40) + 20),
                "previous_claims": float(index % 4),
                "fraud_label": 1 if index < 12 else 0,
            }
        )
    return pd.DataFrame(rows)


def test_load_raw_data_success_and_schema(tmp_path: Path, sample_dataframe: pd.DataFrame) -> None:
    csv_path = tmp_path / "claims.csv"
    sample_dataframe.to_csv(csv_path, index=False)

    loaded = load_raw_data(csv_path)
    assert not loaded.empty
    assert {"policy_type", "claim_amount", "fraud_label"}.issubset(set(loaded.columns))


def test_load_raw_data_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_raw_data("/tmp/does_not_exist_claims.csv")


def test_load_raw_data_missing_columns_raises(tmp_path: Path) -> None:
    invalid_df = pd.DataFrame(
        {
            "policy_type": ["SUV"],
            "claim_amount": [1000.0],
            "fraud_label": [0],
        }
    )
    csv_path = tmp_path / "invalid_claims.csv"
    invalid_df.to_csv(csv_path, index=False)

    with pytest.raises(ValueError):
        load_raw_data(csv_path)


def test_load_raw_data_auto_claims_fraudfound_mapping(tmp_path: Path) -> None:
    auto_claims_df = pd.DataFrame(
        {
            "PolicyType": ["Sport - Liability", "Sedan - Collision"],
            "AccidentArea": ["Urban", "Rural"],
            "Age": [34, 42],
            "FraudFound": ["No", "Yes"],
        }
    )
    csv_path = tmp_path / "auto_claims.csv"
    auto_claims_df.to_csv(csv_path, index=False)

    loaded = load_raw_data(csv_path)
    assert "fraud_label" in loaded.columns
    assert loaded["fraud_label"].tolist() == [0, 1]


def test_load_image_manifest_training_validation_layout(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    train_0 = tmp_path / "images" / "training" / "claim_000"
    train_1 = tmp_path / "images" / "training" / "claim_001"
    val_0 = tmp_path / "images" / "validation" / "claim_000"
    val_1 = tmp_path / "images" / "validation" / "claim_001"
    for path in (train_0, train_1, val_0, val_1):
        path.mkdir(parents=True, exist_ok=True)

    Image.new("RGB", (32, 32), color=(100, 20, 20)).save(train_0 / "0001.jpg")
    Image.new("RGB", (32, 32), color=(20, 100, 20)).save(train_1 / "0002.jpg")
    Image.new("RGB", (32, 32), color=(20, 20, 100)).save(val_0 / "0003.jpg")
    Image.new("RGB", (32, 32), color=(100, 100, 20)).save(val_1 / "0004.jpg")

    manifest = load_image_manifest(tmp_path / "images")
    assert len(manifest) == 4
    assert set(manifest["split"].unique().tolist()) == {"training", "validation"}
    assert set(manifest["fraud_label"].unique().tolist()) == {0, 1}


def test_preprocess_and_split_outputs_and_artifacts(tmp_path: Path, sample_dataframe: pd.DataFrame) -> None:
    data_root = tmp_path / "data"
    artifacts_root = tmp_path / "preprocessors"

    output = preprocess_and_split(
        dataframe=sample_dataframe,
        data_root=data_root,
        artifacts_dir=artifacts_root,
        save_outputs=True,
    )

    assert len(output["X_train"]) + len(output["X_val"]) + len(output["X_test"]) == len(sample_dataframe)
    assert (data_root / "train" / "train_processed.csv").exists()
    assert (data_root / "val" / "val_processed.csv").exists()
    assert (data_root / "test" / "test_processed.csv").exists()
    assert (artifacts_root / "preprocessor.joblib").exists()
    assert (artifacts_root / "preprocessing_metadata.json").exists()


def test_random_undersample_train_balances_classes(sample_dataframe: pd.DataFrame) -> None:
    preprocessed = preprocess_and_split(sample_dataframe, save_outputs=False)

    x_bal, y_bal, stats = random_undersample_train(
        x_train=preprocessed["X_train"],
        y_train=preprocessed["y_train"],
    )

    value_counts = y_bal.value_counts().to_dict()
    assert value_counts[0] == value_counts[1]
    assert len(x_bal) == len(y_bal)
    assert stats.after_counts[0] == stats.after_counts[1]


def test_data_validation_report_generation(tmp_path: Path, sample_dataframe: pd.DataFrame) -> None:
    df = sample_dataframe.copy()
    df.loc[0, "claim_amount"] = None
    df.loc[1, "policy_type"] = None

    expected_schema = {
        "policy_type": "categorical",
        "claim_amount": "numeric",
        "accident_location": "categorical",
        "vehicle_age": "numeric",
        "driver_age": "numeric",
        "previous_claims": "numeric",
        "fraud_label": "binary",
    }

    report_path = tmp_path / "quality_report.json"
    report = generate_data_quality_report(
        dataframe=df,
        expected_schema=expected_schema,
        report_path=report_path,
    )

    assert report_path.exists()
    assert report["row_count"] == len(df)
    assert report["missing_values_before"]["claim_amount"] == 1

    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert "outliers" in loaded


def test_claims_tabular_dataset_and_dataloader(sample_dataframe: pd.DataFrame) -> None:
    torch = pytest.importorskip("torch")
    preprocessed = preprocess_and_split(sample_dataframe, save_outputs=False)
    dataset = ClaimsTabularDataset(preprocessed["X_train"], preprocessed["y_train"])
    loader = create_dataloader(dataset, batch_size=16, shuffle=True)

    batch_x, batch_y = next(iter(loader))  # type: ignore[arg-type]
    assert isinstance(batch_x, torch.Tensor)
    assert isinstance(batch_y, torch.Tensor)
    assert batch_x.shape[0] <= 16


def test_yolo_preprocess_pipeline(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    images_dir = tmp_path / "images"
    labels_dir = tmp_path / "labels"
    output_dir = tmp_path / "yolo_format"

    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    image_path = images_dir / "sample_1.jpg"
    label_path = labels_dir / "sample_1.txt"

    Image.new("RGB", (300, 200), color=(128, 64, 64)).save(image_path)
    label_path.write_text("0 0.500000 0.500000 0.300000 0.300000\n", encoding="utf-8")

    summary = preprocess_yolo_dataset(
        images_dir=images_dir,
        labels_dir=labels_dir,
        output_dir=output_dir,
        train_ratio=0.8,
        random_state=42,
    )

    assert summary["train_images"] + summary["val_images"] == 1
    produced_images = list((output_dir / "images").rglob("*.jpg"))
    produced_labels = list((output_dir / "labels").rglob("*.txt"))
    assert produced_images
    assert produced_labels
