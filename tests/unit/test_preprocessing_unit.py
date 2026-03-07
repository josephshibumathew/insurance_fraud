from __future__ import annotations

import pandas as pd
import pytest

from ml_models.data.preprocessing import preprocess_and_split, separate_features_target


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature_num": [10, 20, 30, 40, 50, 60, 70, 80],
            "feature_cat": ["a", "b", "a", "b", "c", "a", "c", "b"],
            "fraud_label": [0, 1, 0, 1, 0, 1, 0, 1],
        }
    )


def test_separate_features_target_success(sample_df: pd.DataFrame):
    x, y = separate_features_target(sample_df)
    assert "fraud_label" not in x.columns
    assert len(x) == len(y) == len(sample_df)


def test_separate_features_target_missing_column(sample_df: pd.DataFrame):
    with pytest.raises(ValueError):
        separate_features_target(sample_df.drop(columns=["fraud_label"]))


def test_preprocess_and_split_shapes(sample_df: pd.DataFrame, tmp_path):
    result = preprocess_and_split(sample_df, save_outputs=False, data_root=tmp_path)
    assert len(result["X_train"]) > 0
    assert len(result["X_val"]) > 0
    assert len(result["X_test"]) > 0
    assert len(result["feature_names"]) == result["X_train"].shape[1]
