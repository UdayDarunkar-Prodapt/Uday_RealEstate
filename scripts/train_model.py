from pathlib import Path
import sys, json
import pandas as pd, numpy as np, joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.app.config import DATA_PATH, MODEL_PATH, FEATURES

def main():
    if not DATA_PATH.exists(): raise SystemExit('Dataset missing. Run: python scripts/prepare_data.py')
    df=pd.read_csv(DATA_PATH); df.columns=df.columns.str.strip(); model_features=FEATURES+(['GarageYrBlt'] if 'GarageYrBlt' in df.columns else []); X=df[model_features].apply(pd.to_numeric,errors='coerce'); med=X.median().fillna(0); X=X.fillna(med); y=pd.to_numeric(df.SalePrice,errors='coerce'); valid=y.notna(); X,y=X[valid],y[valid]
    a,b,c,d=train_test_split(X,y,test_size=.2,random_state=42)
    candidates={'random_forest':RandomForestRegressor(n_estimators=250,random_state=42,n_jobs=-1),'extra_trees':ExtraTreesRegressor(n_estimators=250,random_state=42,n_jobs=-1)}
    scored=[]
    for name,model in candidates.items():
        model.fit(a,c); p=model.predict(b); mse=float(mean_squared_error(d,p)); scored.append((mean_absolute_error(d,p),name,model,{'mae':float(mean_absolute_error(d,p)),'rmse':float(mse**.5),'mse':mse,'r2':float(r2_score(d,p))}))
    _,name,model,metrics=min(scored,key=lambda x:x[0]); model.fit(X,y); MODEL_PATH.parent.mkdir(exist_ok=True)
    bundle={'model':model,'model_name':name,'features':model_features,'medians':med.to_dict(),'metrics':metrics,'price_per_weight':float(y.std()/max(sum(model.feature_importances_),.01))}
    joblib.dump(bundle,MODEL_PATH)
    print(json.dumps({'selected_model':name,'metrics':metrics,'model_path':str(MODEL_PATH)},indent=2))
if __name__=='__main__': main()
