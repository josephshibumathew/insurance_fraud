from __future__ import annotations

import numpy as np

from ml_models.ensemble.weighted_ensemble import WeightedEnsembleFraudModel


class _MockModel:
    def __init__(self, prob: float) -> None:
        self._prob = prob

    def predict_proba(self, x):
        rows = len(x)
        pos = np.full((rows, 1), self._prob)
        return np.hstack([1 - pos, pos])


class _Wrap:
    def __init__(self, prob: float) -> None:
        self.model = _MockModel(prob)

    def predict_proba(self, x):
        return self.model.predict_proba(x)


def test_weighted_ensemble_predict_proba_shape():
    ensemble = WeightedEnsembleFraudModel(_Wrap(0.3), _Wrap(0.6), _Wrap(0.9), weights=(0.2, 0.3, 0.5))
    x = np.array([[1, 2], [3, 4], [5, 6]])
    probs = ensemble.predict_proba(x)
    assert probs.shape == (3, 2)
    assert np.all((probs >= 0) & (probs <= 1))


def test_weighted_ensemble_predict_thresholding():
    ensemble = WeightedEnsembleFraudModel(_Wrap(0.2), _Wrap(0.2), _Wrap(0.2), weights=(1 / 3, 1 / 3, 1 / 3))
    x = np.array([[1, 2], [3, 4]])
    preds = ensemble.predict(x, threshold=0.5)
    assert preds.tolist() == [0, 0]
