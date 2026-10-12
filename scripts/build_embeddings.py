"""Rebuild the persistent ChromaDB index with local all-MiniLM-L6-v2 vectors."""
from pathlib import Path
import sys, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.app.config import DATA_PATH
from backend.app.retrieval import document
from backend.app.rag.chroma_store import ChromaPropertyStore
def main():
    if not DATA_PATH.exists(): raise SystemExit('Dataset missing. Run prepare_data first.')
    df=pd.read_csv(DATA_PATH); documents=[document(r) for _,r in df.iterrows()]
    out=ROOT/'data'/'property_documents.jsonl'; out.write_text('\n'.join(documents),encoding='utf-8')
    count=ChromaPropertyStore().rebuild(df,documents)
    print(f'Wrote {len(documents)} normalized all-MiniLM-L6-v2 embeddings to ChromaDB ({count} records).')
if __name__=='__main__': main()
