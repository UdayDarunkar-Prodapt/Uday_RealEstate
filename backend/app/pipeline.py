import re, math
import pandas as pd
from .config import DATA_PATH, FEATURES
from .retrieval import HybridRetriever
from .ml.predictor import Predictor

ALIASES={'gr_liv_area':'GrLivArea','living area':'GrLivArea','sq ft':'GrLivArea','bedrooms':'BedroomAbvGr','bedroom':'BedroomAbvGr','bathrooms':'FullBath','bathroom':'FullBath','quality':'OverallQual','year built':'YearBuilt','garage cars':'GarageCars','lot area':'LotArea'}
def classify(query, supplied):
    result={k:v for k,v in supplied.items() if v is not None}
    text=query.lower()
    for label,key in ALIASES.items():
        m=re.search(rf'(\d+(?:\.\d+)?)\s*(?:{re.escape(label)})',text)
        if m and key not in result: result[key]=float(m.group(1))
    m=re.search(r'\b(?:in|neighborhood)\s+([A-Za-z][A-Za-z0-9]+)',query)
    if m and 'neighborhood' not in result: result['neighborhood']=m.group(1)
    return result

class ValuationService:
    def __init__(self):
        self.data=None; self.retriever=None
        if DATA_PATH.exists():
            self.data=pd.read_csv(DATA_PATH); self.data.columns=self.data.columns.str.strip()
            if 'SalePrice' in self.data: self.retriever=HybridRetriever(self.data)
        self.predictor=Predictor()
    def status(self): return {'dataset_loaded':self.retriever is not None,'model_loaded':self.predictor.ready,'property_count':int(len(self.data)) if self.data is not None else 0,'dataset_path':str(DATA_PATH)}
    def valuate(self, item):
        features=classify(item.query,item.model_dump(exclude={'query'},exclude_none=True))
        if not self.retriever: return {'status':'setup_required','message':'Dataset unavailable. Place the real Ames CSV at data/AmesHousing.csv and run the preparation/training commands.','property_features':features,'fallback_used':False}
        comps,retrieval=self.retriever.search(features)
        prices=[float(c['SalePrice']) for c in comps if pd.notna(c.get('SalePrice'))]
        fallback=False; method='model_with_comparables'; reason=None
        try: prediction,x=self.predictor.predict(features); impacts=self.predictor.impacts(x)
        except Exception as e:
            prediction=float(pd.Series(prices).median()); impacts=[]; fallback=True; method='comparable_median_fallback'; reason=str(e)
        dispersion=float(pd.Series(prices).std() if len(prices)>1 else prediction*.15); similarity=sum(c['similarity_score'] for c in comps)/max(len(comps),1)/100
        completeness=min(len([v for v in features.values() if v is not None])/6,1); confidence=max(.1,min(.95,.35+.35*similarity+.2*completeness-.15*retrieval['fallback_used']))
        width=max(dispersion, prediction*(.06+(1-confidence)*.18)); risk='LOW' if confidence>=.75 else ('MEDIUM' if confidence>=.5 else 'HIGH')
        factors=[]
        if len(comps)<5: factors.append(f'Only {len(comps)} comparable properties were available.')
        if retrieval['fallback_used']: factors.append(retrieval['fallback_reason'])
        if completeness<.7: factors.append('The property description is incomplete; missing values were imputed using training medians.')
        explanation=f"Evidence-based estimate from {len(comps)} historical comparable properties. {'Retrieval filters were relaxed. ' if retrieval['fallback_used'] else ''}This is an estimate, not a causal claim or guarantee."
        return {'status':'success','property_features':features,'predicted_value':round(prediction,2),'valuation_range':{'lower':round(max(0,prediction-width),2),'upper':round(prediction+width,2)},'confidence':round(confidence,3),'risk_level':risk,'risk_factors':factors,'valuation_method':method,'fallback_used':fallback or retrieval['fallback_used'],'fallback_reason':reason or retrieval['fallback_reason'],'comparables':comps,'feature_impacts':impacts,'retrieval':retrieval,'evidence':[c['document'] for c in comps],'explanation':explanation,'evaluation':{'groundedness':None,'relevance':None,'note':'LLM judge is intentionally unavailable until an LLM is configured; it never changes numeric valuation.'}}
