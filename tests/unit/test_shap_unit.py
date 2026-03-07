from __future__ import annotations

import numpy as np

from ml_models.explainability.shap_explainer import ShapExplainerEngine


class _DummyTreeExplainer:
    def __init__(self, model):
        self.model = model
        self.expected_value = 0.1

    def shap_values(self, x):
        return np.ones((len(x), x.shape[1])) * 0.05


class _DummyShapModule:
    TreeExplainer = _DummyTreeExplainer


class _DummyModel:
    def predict_proba(self, x):
        pos = np.full((len(x), 1), 0.7)
        return np.hstack([1 - pos, pos])


def test_local_and_global_explanations(monkeypatch):
    monkeypatch.setattr("ml_models.explainability.shap_explainer._load_shap_module", lambda: _DummyShapModule())

    feature_names = ["f1", "f2", "f3"]
    x = np.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
    model = _DummyModel()

    engine = ShapExplainerEngine(
        model=model,
        model_type="random_forest",
        feature_names=feature_names,
        background_data=x,
        predict_proba_fn=lambda arr: model.predict_proba(arr)[:, 1],
    )

    local = engine.explain_local(x[0])
    assert local.prediction == 0.7
    assert len(local.mapped_feature_contributions) == 3

    global_exp = engine.explain_global(x)
    assert list(global_exp.feature_importance.columns) == ["feature", "mean_abs_shap"]
