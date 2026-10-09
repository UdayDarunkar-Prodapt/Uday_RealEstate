"""Builds locally generated semantic documents; retrieval always has TF-IDF/BM25-style local fallback."""
from pathlib import Path
import sys, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.app.config import DATA_PATH
from backend.app.retrieval import document
def main():
    if not DATA_PATH.exists(): raise SystemExit('Dataset missing. Run prepare_data first.')
    df=pd.read_csv(DATA_PATH); out=ROOT/'data'/'property_documents.jsonl'
    out.write_text('\n'.join(document(r) for _,r in df.iterrows()),encoding='utf-8'); print(f'Wrote {len(df)} property documents to {out}')
if __name__=='__main__': main()
