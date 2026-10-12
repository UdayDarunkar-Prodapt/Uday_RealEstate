from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_PATH = Path(os.getenv("DATASET_PATH", ROOT / "data" / "AmesHousing.csv"))
MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT / "models" / "valuation_model.joblib"))
DB_PATH = ROOT / "database" / "app.db"
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", ROOT / "chroma_db"))
RRF_K = int(os.getenv("RRF_K", "60"))
MAX_QUERY_LENGTH = 1200
# OpenML Ames ID 43926 does not include GarageYrBlt, so it is not a model input.
FEATURES = ["OverallQual", "OverallCond", "GrLivArea", "TotalBsmtSF", "GarageCars", "GarageArea", "YearBuilt", "YearRemodAdd", "FullBath", "BedroomAbvGr", "TotRmsAbvGrd", "LotArea"]
# GarageYrBlt is included dynamically during training when the selected Ames
# source actually provides it; the OpenML 43926 variant used here does not.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY", "")
PRIMARY_LLM_MODEL = os.getenv("PRIMARY_LLM_MODEL") or "claude-sonnet-4-6"
FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
