from pathlib import Path
import joblib, numpy as np
from ..config import MODEL_PATH, FEATURES

class Predictor:
    def __init__(self):
        self.bundle=None
        self._shap_explainer=None
        self._shap_attempted=False
        if MODEL_PATH.exists(): self.bundle=joblib.load(MODEL_PATH)
    @property
    def ready(self): return self.bundle is not None
    def predict(self, features):
        if not self.ready: raise RuntimeError('No trained model. Run python scripts/train_model.py after placing the Ames CSV in data/.')
        medians=self.bundle['medians']; x=np.array([[features.get(k,medians[k]) if features.get(k) is not None else medians[k] for k in FEATURES]],dtype=float)
        return float(self.bundle['model'].predict(x)[0]), x[0]
    def impacts(self, x):
        """Return genuine local SHAP values, falling back only when SHAP cannot run."""
        try:
            return self._shap_impacts(x)
        except Exception:
            return self._feature_importance_fallback(x)

    def _shap_impacts(self, x):
        # Import lazily: a missing optional dependency must not block valuation.
        import shap
        if self._shap_explainer is None:
            self._shap_explainer = shap.TreeExplainer(self.bundle['model'])
        values = self._shap_explainer.shap_values(np.asarray(x, dtype=float).reshape(1, -1))
        # TreeExplainer returns a 2-D array for regression models; handle variants safely.
        values = np.asarray(values)
        if values.ndim == 3:
            values = values[0, :, 0]
        elif values.ndim == 2:
            values = values[0]
        if len(values) != len(FEATURES):
            raise ValueError('Unexpected SHAP value shape.')
        impacts=[]
        for feature, value in zip(FEATURES, values):
            impact=float(value)
            impacts.append({'feature':feature,'impact':round(impact,2),
                            'direction':'positive' if impact >= 0 else 'negative',
                            'method':'shap_tree_explainer'})
        return sorted(impacts,key=lambda item:abs(item['impact']),reverse=True)[:6]

    def _feature_importance_fallback(self, x):
        model=self.bundle['model']; importances=getattr(model,'feature_importances_',np.ones(len(FEATURES))/len(FEATURES)); med=self.bundle['medians']
        impacts=[]
        for k,v,w in zip(FEATURES,x,importances):
            # Deterministic model-relative proxy if SHAP optional package is absent.
            effect=float((v-med[k])*w*self.bundle.get('price_per_weight',1))
            impacts.append({'feature':k,'impact':round(effect,2),'direction':'positive' if effect>=0 else 'negative','method':'feature_importance_fallback'})
        return sorted(impacts,key=lambda a:abs(a['impact']),reverse=True)[:6]
