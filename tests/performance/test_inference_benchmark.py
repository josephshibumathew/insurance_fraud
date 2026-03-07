from __future__ import annotations

import time

import numpy as np


class _MockTabularModel:
    def predict(self, x):
        time.sleep(0.01)
        return np.zeros(len(x), dtype=int)


class _MockImageModel:
    def infer(self, _image):
        time.sleep(0.15)
        return {"detections": 3}


def test_tabular_inference_under_target():
    model = _MockTabularModel()
    x = np.random.rand(128, 20)

    start = time.perf_counter()
    model.predict(x)
    elapsed = (time.perf_counter() - start) * 1000

    assert elapsed < 200


def test_image_inference_under_target():
    model = _MockImageModel()

    start = time.perf_counter()
    model.infer("fake-image")
    elapsed = time.perf_counter() - start

    assert elapsed < 3.0
