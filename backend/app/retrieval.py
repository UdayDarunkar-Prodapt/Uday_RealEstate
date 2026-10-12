import re
import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from .config import RRF_K
from .rag.chroma_store import ChromaPropertyStore, embed, embed_many

def document(row):
    garage_year=row.get('GarageYrBlt','?')
    return (f"Property in {row.get('Neighborhood','unknown')} neighborhood; {row.get('BedroomAbvGr','?')} bedrooms, "
            f"{row.get('FullBath','?')} full bathrooms, {row.get('GrLivArea','?')} sq ft living area, built {row.get('YearBuilt','?')}, "
            f"quality {row.get('OverallQual','?')}, condition {row.get('OverallCond','?')}, {row.get('GarageCars','?')}-car garage, garage built {garage_year}.")
def tokens(s): return re.findall(r"[a-z0-9]+", str(s).lower())

def reciprocal_rank_fusion(rankings, k=RRF_K):
    """Fuse ranked property ID lists with standard reciprocal-rank fusion."""
    scores={}
    for ranking in rankings:
        for rank,property_id in enumerate(ranking, start=1):
            scores[property_id]=scores.get(property_id,0.0)+1.0/(k+rank)
    return scores

class HybridRetriever:
    def __init__(self, frame: pd.DataFrame):
        self.frame=frame.reset_index(drop=True); self.docs=[document(r) for _,r in self.frame.iterrows()]
        self.tokenized_docs=[tokens(doc) for doc in self.docs]
        self.bm25=BM25Okapi(self.tokenized_docs)
        self.chroma=ChromaPropertyStore.available(self.frame,self.docs)
        self.feedback_scores={}
        self.local_embeddings=None
        self.semantic_available=bool(self.chroma)
        if not self.chroma: self._load_local_embeddings()
    def set_feedback_scores(self,scores): self.feedback_scores=dict(scores or {})
    def _load_local_embeddings(self):
        try:
            self.local_embeddings=embed_many(self.docs)
            self.semantic_available=True
        except Exception:
            self.local_embeddings=None
            self.semantic_available=False
    def search(self, features, limit=5):
        f=self.frame; filters={}; mask=np.ones(len(f),dtype=bool); applied=[]
        specs=[('neighborhood','Neighborhood','eq'),('YearBuilt','YearBuilt','age'),('BedroomAbvGr','BedroomAbvGr','count'),('FullBath','FullBath','count'),('TotRmsAbvGrd','TotRmsAbvGrd','count'),('GrLivArea','GrLivArea','area'),('LotArea','LotArea','area')]
        for feature,column,kind in specs:
            value=features.get(feature) if feature!='neighborhood' else features.get('neighborhood')
            if value is None or value=='': continue
            series=f[column].astype(str).str.lower() if kind=='eq' else pd.to_numeric(f[column],errors='coerce')
            if kind=='eq': cond={'$eq':str(value)}; keep=series.eq(str(value).lower()).to_numpy()
            elif kind=='age': cond={'$gte':float(value)-15,'$lte':float(value)+15}; keep=series.between(float(value)-15,float(value)+15).to_numpy()
            elif kind=='count': cond={'$gte':max(0,float(value)-1),'$lte':float(value)+1}; keep=series.between(max(0,float(value)-1),float(value)+1).to_numpy()
            else:
                tolerance=max(250.0,float(value)*.35); cond={'$gte':max(0,float(value)-tolerance),'$lte':float(value)+tolerance}; keep=series.between(max(0,float(value)-tolerance),float(value)+tolerance).to_numpy()
            applied.append((feature,column,cond,keep))
        strict_count=int(np.logical_and.reduce([x[3] for x in applied]).sum()) if applied else len(f)
        # Relax constraints from least specific to most specific until enough real
        # comparables remain; the selected filter set is shared with Chroma.
        candidates=np.arange(len(f)); active=list(applied)
        relax_order=['LotArea','TotRmsAbvGrd','FullBath','BedroomAbvGr','GrLivArea','YearBuilt','neighborhood']
        for removable in [None,*relax_order]:
            active=[x for x in applied if x[0] not in relax_order[:relax_order.index(removable)+1]] if removable else list(applied)
            mask=np.ones(len(f),dtype=bool)
            for _,_,_,keep in active: mask &= keep
            candidates=np.where(mask)[0]
            if len(candidates)>=limit: break
        filters={column:condition for _,column,condition,_ in active}
        fallback=len(active)<len(applied); mode='hybrid_rrf_relaxed' if fallback else 'hybrid_rrf'; reason='Some property filters were relaxed because too few close comparables matched.' if fallback else None
        q=document(features); query_tokens=tokens(q)
        semantic_scores=np.zeros(len(f),dtype=np.float32); semantic_order=None; semantic_fallback=False
        # ChromaDB is primary semantic retrieval. Without it, use the same local
        # MiniLM vectors against the cached document vectors.
        if self.chroma:
            try:
                hits=self.chroma.query(q,limit=min(len(candidates),250),filters=filters)
                for rank,(property_id,distance) in enumerate(hits):
                    semantic_scores[property_id]=max(0.0,1.0-distance)
                hit_ids=[pid for pid,_ in hits if pid in set(candidates)]
                remaining=[int(pid) for pid in candidates if int(pid) not in set(hit_ids)]
                semantic_order=hit_ids+remaining
            except Exception:
                self.chroma=None
        if not self.chroma:
            semantic_fallback=True
            if self.local_embeddings is None: self._load_local_embeddings()
            if self.semantic_available:
                try:
                    query_vector=embed(q)
                    semantic_scores=self.local_embeddings@np.asarray(query_vector,dtype=np.float32)
                    semantic_order=sorted((int(pid) for pid in candidates),key=lambda pid:(-semantic_scores[pid],pid))
                except Exception:
                    self.semantic_available=False
        if semantic_order is None: semantic_order=[int(pid) for pid in candidates]
        lexical_scores=np.asarray(self.bm25.get_scores(query_tokens),dtype=np.float32)
        lexical_order=sorted((int(pid) for pid in candidates),key=lambda pid:(-lexical_scores[pid],pid))
        rankings=([semantic_order] if self.semantic_available else [])+[lexical_order]
        fused=reciprocal_rank_fusion(rankings)
        scored=[]
        for i in candidates:
            source=f.iloc[i].to_dict(); sim=self._similarity(source,features,float(semantic_scores[i]))
            row=self._public_property(source)
            row.update({'property_id':int(i),'similarity_score':round(sim*100,1),'semantic_score':round(float(semantic_scores[i]),3),'bm25_score':round(float(lexical_scores[i]),3),'document':self.docs[i]}); scored.append(row)
        scored.sort(key=lambda x:(fused[x['property_id']]+self.feedback_scores.get(x['property_id'],0),x['similarity_score']),reverse=True)
        mode='chroma_bm25_rrf' if self.chroma else ('local_minilm_bm25_rrf' if self.semantic_available else 'bm25_only_fallback')
        if fallback: mode+='_relaxed'
        reasons=[]
        if fallback: reasons.append(reason)
        if semantic_fallback: reasons.append('ChromaDB unavailable; semantic retrieval used local MiniLM vectors.' if self.semantic_available else 'ChromaDB/MiniLM unavailable; ranking used BM25 only.')
        effective_fallback=fallback or semantic_fallback or not self.semantic_available
        return scored[:limit], {'exact_match_count':strict_count,'relaxed_match_count':max(0,min(limit,len(candidates))-strict_count) if fallback else 0,'retrieval_mode':mode,'fallback_used':effective_fallback,'fallback_reason':' '.join(reasons) or None,'filters_applied':[x[0] for x in active],'feedback_used':bool(self.feedback_scores),'semantic_available':self.semantic_available,'lexical_method':'BM25Okapi','semantic_store':'ChromaDB' if self.chroma else ('local_minilm' if self.semantic_available else None)}

    @staticmethod
    def _public_property(row):
        """Return JSON-safe, relevant comparable metadata instead of raw CSV internals."""
        keys=['SalePrice','Neighborhood','BedroomAbvGr','FullBath','GrLivArea','LotArea','YearBuilt','YearRemodAdd','GarageYrBlt','OverallQual','OverallCond','GarageCars','GarageArea','TotalBsmtSF','TotRmsAbvGrd']
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
