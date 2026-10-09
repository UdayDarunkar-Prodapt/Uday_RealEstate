"""Download/normalise the official OpenML Ames data into data/AmesHousing.csv."""
from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.app.config import DATA_PATH, FEATURES

# OpenML uses the original Ames names; the API uses the PDF/Kaggle-style names.
CANONICAL_COLUMNS = {
    'Sale_Price':'SalePrice', 'Overall_Qual':'OverallQual', 'Overall_Cond':'OverallCond',
    'Gr_Liv_Area':'GrLivArea', 'Total_Bsmt_SF':'TotalBsmtSF', 'Garage_Cars':'GarageCars',
    'Garage_Area':'GarageArea', 'Year_Built':'YearBuilt', 'Year_Remod_Add':'YearRemodAdd',
    'Full_Bath':'FullBath', 'Bedroom_AbvGr':'BedroomAbvGr', 'TotRms_AbvGrd':'TotRmsAbvGrd',
    'Lot_Area':'LotArea'
}
ORDINAL_QUALITY = {
    'Very_Poor': 1, 'Poor': 2, 'Fair': 3, 'Below_Average': 4,
    'Average': 5, 'Above_Average': 6, 'Good': 7, 'Very_Good': 8,
    'Excellent': 9, 'Very_Excellent': 10,
}

def main():
    DATA_PATH.parent.mkdir(exist_ok=True)
    if not DATA_PATH.exists():
        from sklearn.datasets import fetch_openml
        print('Downloading OpenML dataset 43926 (requires internet)...')
        bunch=fetch_openml(data_id=43926,as_frame=True,parser='auto')
        frame=bunch.frame
        frame.to_csv(DATA_PATH,index=False)
    frame=pd.read_csv(DATA_PATH); frame.columns=frame.columns.str.strip().str.replace(' ', '_')
    frame=frame.rename(columns=CANONICAL_COLUMNS)
    required=['SalePrice',*FEATURES,'Neighborhood']
    missing=[x for x in required if x not in frame]
    if missing: raise ValueError(f'Dataset is not Ames-compatible; missing: {missing}')
    # This OpenML source represents these ordered Ames ratings as text labels.
    # Convert them to their documented 1–10 ordinal scale for ML and similarity.
    for field in ('OverallQual', 'OverallCond'):
        if frame[field].dtype == 'object':
            unknown=set(frame[field].dropna().astype(str))-set(ORDINAL_QUALITY)
            if unknown: raise ValueError(f'Unknown {field} categories: {sorted(unknown)}')
            frame[field]=frame[field].map(ORDINAL_QUALITY)
    # Persist canonical headers so all later scripts and the API use one schema.
    frame.to_csv(DATA_PATH,index=False)
    print(f'Ready: {len(frame)} real property records at {DATA_PATH}')
if __name__=='__main__': main()
