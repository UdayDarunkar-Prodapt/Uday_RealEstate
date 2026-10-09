import numpy as np
from backend.app.ml.predictor import Predictor
from backend.app.config import FEATURES

def test_feature_importance_fallback_is_explicit():
    predictor=Predictor.__new__(Predictor)
    predictor.bundle={'model':type('Model',(),{'feature_importances_':np.ones(len(FEATURES))/len(FEATURES)})(), 'medians':{f:0 for f in FEATURES}, 'price_per_weight':1}
    results=predictor._feature_importance_fallback(np.ones(len(FEATURES)))
    assert results and all(item['method']=='feature_importance_fallback' for item in results)
