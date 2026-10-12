"""Persistent ChromaDB index using locally generated MiniLM embeddings."""
from functools import lru_cache
from hashlib import sha256

import numpy as np
import pandas as pd
from ..config import CHROMA_PATH

COLLECTION_NAME = "ames_properties"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_SCHEMA_VERSION = "4"


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the local sentence-transformer once per process."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_many(texts):
    """Encode texts as unit-normalized MiniLM vectors on the local machine."""
    if not texts:
        return np.empty((0, 384), dtype=np.float32)
    vectors = np.asarray(get_embedding_model().encode(
        list(texts),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ), dtype=np.float32)
    norms=np.linalg.norm(vectors,axis=1,keepdims=True)
    return vectors/np.maximum(norms,1e-12)


def embed(text):
    """Return one normalized embedding for a Chroma query."""
    return embed_many([text])[0].tolist()


class ChromaPropertyStore:
    def __init__(self):
        import chromadb
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.client.get_or_create_collection(
            COLLECTION_NAME,
            embedding_function=None,
            metadata={"hnsw:space": "cosine"},
        )

    @classmethod
    def available(cls, frame=None, documents=None):
        try:
            instance = cls()
            if frame is not None and documents is not None:
                fingerprint = cls.fingerprint(frame, documents)
                if (instance.collection.count() != len(frame)
                        or instance.collection.metadata.get("source_fingerprint") != fingerprint):
                    instance.rebuild(frame, documents, fingerprint)
            return instance if instance.collection.count() else None
        except Exception:
            return None

    @staticmethod
    def fingerprint(frame, documents):
        digest = sha256()
        digest.update(INDEX_SCHEMA_VERSION.encode("ascii"))
        digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
        for doc in documents:
            digest.update(str(doc).encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    def rebuild(self, frame, documents, fingerprint=None):
        """Encode before replacing the old collection so failures preserve it."""
        fingerprint = fingerprint or self.fingerprint(frame, documents)
        vectors = embed_many(documents)
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            COLLECTION_NAME,
            embedding_function=None,
            metadata={"hnsw:space": "cosine", "source_fingerprint": fingerprint},
        )
        for start in range(0, len(frame), 250):
            end = min(start + 250, len(frame))
            batch = frame.iloc[start:end]
            self.collection.upsert(
                ids=[str(i) for i in range(start, end)],
                documents=list(documents[start:end]),
                embeddings=vectors[start:end].tolist(),
                metadatas=[self._metadata(i, row) for i, (_, row) in enumerate(batch.iterrows(), start)],
            )
        return self.collection.count()

    @staticmethod
    def _metadata(index, row):
        def number(name):
            value = pd.to_numeric(row.get(name), errors="coerce")
            return float(value) if pd.notna(value) else -1.0
        return {
            "property_id": str(index),
            "Neighborhood": str(row.get("Neighborhood") or "unknown").casefold(),
            "YearBuilt": number("YearBuilt"),
            "GrLivArea": number("GrLivArea"),
            "LotArea": number("LotArea"),
            "BedroomAbvGr": number("BedroomAbvGr"),
            "FullBath": number("FullBath"),
            "TotRmsAbvGrd": number("TotRmsAbvGrd"),
            "OverallQual": number("OverallQual"),
        }

    def query(self, query_text, limit=100, filters=None):
        clauses = []
        for field, condition in (filters or {}).items():
            if field == "Neighborhood":
                condition = {"$eq": str(condition["$eq"]).casefold()}
            clauses.extend({field: {operator: value}} for operator, value in condition.items())
        where = clauses[0] if len(clauses) == 1 else ({"$and": clauses} if clauses else None)
        result = self.collection.query(
            query_embeddings=[embed(query_text)],
            n_results=min(max(1, limit), self.collection.count()),
            where=where,
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [(int(identifier), float(distance)) for identifier, distance in zip(ids, distances)]
