"""Reports retrieval latency on the loaded real dataset; no fabricated precision labels."""
from pathlib import Path
import sys, time, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.app.config import DATA_PATH
from backend.app.retrieval import HybridRetriever
def main():
    df=pd.read_csv(DATA_PATH); r=HybridRetriever(df); q={'neighborhood':str(df.iloc[0].Neighborhood),'GrLivArea':float(df.iloc[0].GrLivArea)}; t=time.perf_counter(); found,meta=r.search(q); print({'latency_ms':round((time.perf_counter()-t)*1000,2),'returned':len(found),'metadata':meta})
if __name__=='__main__': main()
