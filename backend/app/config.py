from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_PATH = Path(os.getenv("DATASET_PATH", ROOT / "data" / "AmesHousing.csv"))
MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT / "models" / "valuation_model.joblib"))
DB_PATH = ROOT / "database" / "app.db"
RRF_K = int(os.getenv("RRF_K", "60"))
MAX_QUERY_LENGTH = 1200
# OpenML Ames ID 43926 does not include GarageYrBlt, so it is not a model input.
FEATURES = ["OverallQual", "OverallCond", "GrLivArea", "TotalBsmtSF", "GarageCars", "GarageArea", "YearBuilt", "YearRemodAdd", "FullBath", "BedroomAbvGr", "TotRmsAbvGrd", "LotArea"]
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PRIMARY_LLM_MODEL = os.getenv("PRIMARY_LLM_MODEL", "")
FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
