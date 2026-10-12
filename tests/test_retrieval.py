import numpy as np
import pandas as pd

from backend.app import retrieval
from backend.app.rag import chroma_store


def small_frame():
    return pd.DataFrame([
        {'Neighborhood':'North_Ames','BedroomAbvGr':3,'FullBath':2,'GrLivArea':1800,'YearBuilt':2000,'OverallQual':7,'OverallCond':6,'GarageCars':2,'SalePrice':210000},
        {'Neighborhood':'North_Ames','BedroomAbvGr':2,'FullBath':1,'GrLivArea':1100,'YearBuilt':1990,'OverallQual':5,'OverallCond':5,'GarageCars':1,'SalePrice':150000},
        {'Neighborhood':'Somerset','BedroomAbvGr':4,'FullBath':3,'GrLivArea':2400,'YearBuilt':2010,'OverallQual':8,'OverallCond':7,'GarageCars':3,'SalePrice':310000},
    ])


def query_features():
    return {'query':'cedar amber'}


def retrieval_frame():
    frame=small_frame()
    frame['LexicalDocument']=['cedar amber','amber','violet']
    return frame


def patch_document(monkeypatch):
    def make_document(row):
        return row.get('query',row.get('LexicalDocument',''))
    monkeypatch.setattr(retrieval,'document',make_document)


def test_minilm_embedding_vectors_are_normalized(monkeypatch):
    class FakeEncoder:
        def encode(self, texts, **kwargs):
            assert kwargs['normalize_embeddings'] is True
            assert kwargs['convert_to_numpy'] is True
            return np.array([[3.0, 4.0], [0.0, 2.0]], dtype=np.float32)

    monkeypatch.setattr(chroma_store, 'get_embedding_model', lambda: FakeEncoder())
    vectors=chroma_store.embed_many(['first', 'second'])
    assert np.allclose(np.linalg.norm(vectors,axis=1),1.0)


def test_reciprocal_rank_fusion_uses_both_rankings():
    scores=retrieval.reciprocal_rank_fusion([[10,20,30],[20,10,40]],k=0)
    assert scores[10] == 1 + 1/2
    assert scores[20] == 1/2 + 1
    assert scores[30] == 1/3
    assert max(scores,key=scores.get) == 10


def test_bm25_retrieval_ranks_matching_property(monkeypatch):
    patch_document(monkeypatch)
    monkeypatch.setattr(retrieval.ChromaPropertyStore,'available',classmethod(lambda cls,*args:None))
    monkeypatch.setattr(retrieval,'embed_many',lambda docs:np.zeros((len(docs),4),dtype=np.float32))
    monkeypatch.setattr(retrieval,'embed',lambda text:[0,0,0,0])
    retriever=retrieval.HybridRetriever(retrieval_frame())
    results,meta=retriever.search(query_features(),limit=3)
    assert results[0]['property_id']==0
    assert results[0]['bm25_score']>results[1]['bm25_score']
    assert meta['lexical_method']=='BM25Okapi'


def test_chroma_semantic_ranking_is_fused_with_bm25(monkeypatch):
    patch_document(monkeypatch)
    class FakeChroma:
        def query(self,*args,**kwargs): return [(1,0.0),(0,0.2),(2,0.4)]
    monkeypatch.setattr(retrieval.ChromaPropertyStore,'available',classmethod(lambda cls,*args:FakeChroma()))
    retriever=retrieval.HybridRetriever(retrieval_frame())
    results,meta=retriever.search(query_features(),limit=3)
    assert meta['retrieval_mode']=='chroma_bm25_rrf'
    assert meta['semantic_store']=='ChromaDB'
    assert results[0]['semantic_score']==1.0
    assert results[0]['bm25_score']>0
    assert {x['property_id'] for x in results[:2]}=={0,1}


def test_missing_semantic_model_falls_back_to_bm25(monkeypatch):
    patch_document(monkeypatch)
    monkeypatch.setattr(retrieval.ChromaPropertyStore,'available',classmethod(lambda cls,*args:None))
    def unavailable(_): raise ImportError('model unavailable')
    monkeypatch.setattr(retrieval,'embed_many',unavailable)
    retriever=retrieval.HybridRetriever(retrieval_frame())
    results,meta=retriever.search(query_features(),limit=3)
    assert results[0]['property_id']==0
    assert meta['retrieval_mode']=='bm25_only_fallback'
    assert meta['fallback_used'] is True
    assert meta['semantic_available'] is False
