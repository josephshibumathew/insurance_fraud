from __future__ import annotations

import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import auc, confusion_matrix, precision_recall_curve, roc_curve
from sklearn.model_selection import cross_val_score


def test_cross_validation_and_classification_metrics():
    x, y = make_classification(n_samples=250, n_features=12, n_informative=6, random_state=42)
    model = RandomForestClassifier(n_estimators=50, random_state=42)

    cv_scores = cross_val_score(model, x, y, cv=3, scoring="roc_auc")
    assert cv_scores.mean() > 0.5

    model.fit(x, y)
    preds = model.predict(x)
    probs = model.predict_proba(x)[:, 1]

    cm = confusion_matrix(y, preds)
    assert cm.shape == (2, 2)

    fpr, tpr, _ = roc_curve(y, probs)
    assert auc(fpr, tpr) > 0.5

    precision, recall, _ = precision_recall_curve(y, probs)
    assert len(precision) == len(recall)
