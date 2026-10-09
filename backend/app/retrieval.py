import re
import numpy as np
import pandas as pd
from .config import RRF_K

def document(row):
    return (f"Property in {row.get('Neighborhood','unknown')} neighborhood; {row.get('BedroomAbvGr','?')} bedrooms, "
            f"{row.get('FullBath','?')} full bathrooms, {row.get('GrLivArea','?')} sq ft living area, built {row.get('YearBuilt','?')}, "
            f"quality {row.get('OverallQual','?')}, condition {row.get('OverallCond','?')}, {row.get('GarageCars','?')}-car garage.")
def tokens(s): return re.findall(r"[a-z0-9]+", str(s).lower())

class HybridRetriever:
    def __init__(self, frame: pd.DataFrame):
        self.frame=frame.reset_index(drop=True); self.docs=[document(r) for _,r in self.frame.iterrows()]
        self.vocab={t:i for i,t in enumerate(sorted(set(t for d in self.docs for t in tokens(d))))}
        self.matrix=np.zeros((len(self.docs),len(self.vocab)))
        for i,d in enumerate(self.docs):
            for t in tokens(d): self.matrix[i,self.vocab[t]]+=1
        self.matrix/=np.maximum(np.linalg.norm(self.matrix,axis=1,keepdims=True),1)
    def search(self, features, limit=5):
        f=self.frame; exact=np.ones(len(f),dtype=bool)
        if features.get('neighborhood'): exact &= f.Neighborhood.astype(str).str.lower().eq(str(features['neighborhood']).lower()).to_numpy()
        if features.get('YearBuilt'): exact &= (abs(pd.to_numeric(f.YearBuilt,errors='coerce').fillna(0)-float(features['YearBuilt']))<=15).to_numpy()
        candidates=np.where(exact)[0]; mode='hybrid_rrf'; fallback=False; reason=None
        if len(candidates)<limit:
            candidates=np.arange(len(f)); mode='hybrid_rrf_relaxed'; fallback=True; reason='Insufficient exact metadata matches; age/location constraints were relaxed.'
        q=' '.join([str(x) for x in features.values() if x is not None]); qv=np.zeros(len(self.vocab))
        for t in tokens(q):
            if t in self.vocab: qv[self.vocab[t]]+=1
        qv/=max(np.linalg.norm(qv),1); semantic=self.matrix@qv
        # Local BM25-style lexical ranking; always combined with semantic via RRF.
        query=set(tokens(q)); lexical=np.array([len(query.intersection(tokens(d))) for d in self.docs],dtype=float)
        ranks1=np.argsort(np.argsort(-semantic)); ranks2=np.argsort(np.argsort(-lexical)); rrf=1/(RRF_K+ranks1+1)+1/(RRF_K+ranks2+1)
        scored=[]
        for i in candidates:
            source=f.iloc[i].to_dict(); sim=self._similarity(source,features,semantic[i])
            row=self._public_property(source)
            row.update({'property_id':int(i),'similarity_score':round(sim*100,1),'semantic_score':round(float(semantic[i]),3),'document':self.docs[i]}); scored.append(row)
        scored.sort(key=lambda x:(x['similarity_score'],rrf[x['property_id']]),reverse=True)
        return scored[:limit], {'exact_match_count':int(exact.sum()),'relaxed_match_count':max(0,limit-int(exact.sum())) if fallback else 0,'retrieval_mode':mode,'fallback_used':fallback,'fallback_reason':reason}

    @staticmethod
    def _public_property(row):
        """Return JSON-safe, relevant comparable metadata instead of raw CSV internals."""
        keys=['SalePrice','Neighborhood','BedroomAbvGr','FullBath','GrLivArea','LotArea','YearBuilt','YearRemodAdd','OverallQual','OverallCond','GarageCars','GarageArea','TotalBsmtSF','TotRmsAbvGrd']
        result={}
        for key in keys:
            value=row.get(key)
            if pd.isna(value): result[key]=None
            elif isinstance(value, np.generic): result[key]=value.item()
            else: result[key]=value
        return result
    def _similarity(self,row,q,semantic):
        parts=[max(semantic,0)]
        for k,scale in [('GrLivArea',1000),('LotArea',10000),('YearBuilt',50),('OverallQual',5),('OverallCond',5),('BedroomAbvGr',4),('FullBath',3),('GarageCars',3)]:
            if q.get(k) is not None and pd.notna(row.get(k)):
                parts.append(max(0,1-abs(float(row[k])-float(q[k]))/scale))
        if q.get('neighborhood'): parts.append(1.0 if str(row.get('Neighborhood','')).lower()==str(q['neighborhood']).lower() else 0.35)
        return float(np.mean(parts))
