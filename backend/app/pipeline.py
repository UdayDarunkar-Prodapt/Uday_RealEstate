import re
import pandas as pd
from pydantic import ValidationError
from .config import DATA_PATH
from .retrieval import HybridRetriever
from .ml.predictor import Predictor
from .database import comparable_feedback_scores
from .schemas import PropertyInput

class InvalidPropertyFeatures(ValueError): pass

ALIASES={'living area':'GrLivArea','square feet':'GrLivArea','sq ft':'GrLivArea','bedrooms':'BedroomAbvGr','bedroom':'BedroomAbvGr','beds':'BedroomAbvGr','full bathrooms':'FullBath','full bathroom':'FullBath','bathrooms':'FullBath','bathroom':'FullBath','full bath':'FullBath','baths':'FullBath','quality':'OverallQual','condition':'OverallCond','garage year built':'GarageYrBlt','year built':'YearBuilt','built':'YearBuilt','garage cars':'GarageCars','garage':'GarageCars','lot area':'LotArea'}
RATING_WORDS={'poor':2,'fair':4,'average':5,'typical':5,'good':7,'above average':6,'very good':8,'excellent':9,'exceptional':10}
NUMBER_WORDS={'one':1,'a':1,'an':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
NEIGHBORHOOD_ALIASES={'names':'North_Ames','northames':'North_Ames','collgcr':'College_Creek','collegecreek':'College_Creek','oldtown':'Old_Town','somerst':'Somerset','nridght':'Northridge_Heights','northridgeheights':'Northridge_Heights','swisu':'South_and_West_of_Iowa_State_University','brdale':'Briardale','brkside':'Brookside','clearcr':'Clear_Creek','idotrr':'Iowa_DOT_and_Rail_Road','meadowv':'Meadow_Village','noridge':'Northridge','npkvill':'Northpark_Villa','bluest':'Stone_Brook','mitchel':'Mitchell','crawfor':'Crawford','sawyerw':'Sawyer_West'}
def classify(query, supplied):
    result={k:v for k,v in supplied.items() if v is not None}; text=query.lower()
    for label,key in ALIASES.items():
        phrase=re.escape(label)
        unsigned_number=r'(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)'
        # Reject negative values in prose before parsing. Without this check,
        # the previous number pattern could skip the minus sign and read -2
        # bedrooms as a valid positive count of 2.
        negative_before=re.search(rf'(?<![a-z0-9])-\s*{unsigned_number}\s*[- ]?{phrase}(?![a-z])',text)
        negative_after=re.search(rf'(?<![a-z]){phrase}\s*[:=]?\s*-\s*{unsigned_number}(?![a-z0-9])',text)
        if negative_before or negative_after:
            raise InvalidPropertyFeatures(f"{label.capitalize()} cannot be negative.")
        if key in result: continue
        number=rf'(-?{unsigned_number})'
        match=re.search(rf'(?<![a-z0-9]){number}\s*[- ]?\s*{phrase}(?![a-z])',text)
        if not match: match=re.search(rf'(?<![a-z]){phrase}\s*[:=]?\s*{number}(?![a-z0-9])',text)
        if match:
            value=float(match.group(1).replace(',',''))
            result[key]=int(value) if key in {'YearBuilt','OverallQual','OverallCond'} and value.is_integer() else value
    # Common property prose puts "in" between "built" and the year.
    if 'YearBuilt' not in result:
        match=re.search(r'\b(?:built|constructed)\s+(?:in\s+)?(18\d{2}|19\d{2}|20\d{2})\b',text)
        if match: result['YearBuilt']=int(match.group(1))
    # Interpret standard ordinal descriptions when a numeric rating is absent.
    for word,value in sorted(RATING_WORDS.items(),key=lambda entry:-len(entry[0])):
        if re.search(rf'\b{re.escape(word)}\s+(?:overall\s+)?quality\s+and\s+(?:overall\s+)?condition\b',text):
            result.setdefault('OverallQual',value); result.setdefault('OverallCond',value); break
    for key,labels in [('OverallQual',r'(?:overall\s+)?quality'),('OverallCond',r'(?:overall\s+)?condition')]:
        if key in result: continue
        for word,value in sorted(RATING_WORDS.items(),key=lambda entry:-len(entry[0])):
            if re.search(rf'\b{re.escape(word)}\b(?:\s+[\w-]+){{0,2}}\s+{labels}\b',text) or re.search(rf'\b{labels}\b(?:\s+[\w-]+){{0,2}}\s+{re.escape(word)}\b',text):
                result[key]=value; break
    # Lot size and garage capacity are commonly expressed as "6,000 sq ft lot"
    # and "two-car garage" rather than feature labels followed by digits.
    if 'LotArea' not in result:
        match=re.search(r'\b(\d{1,3}(?:,\d{3})+|\d+)\s*(?:sq\.?\s*ft\.?|square\s+feet)\s+lot\b',text)
        if match: result['LotArea']=int(match.group(1).replace(',',''))
    if 'GarageCars' not in result:
        match=re.search(r'\b(one|two|three|four|\d+)\s*[- ]?car\s+garage\b',text)
        if match:
            raw=match.group(1); result['GarageCars']=NUMBER_WORDS.get(raw,int(raw) if raw.isdigit() else 1)
    match=re.search(r'\b(?:in|neighborhood)\s+([A-Za-z][A-Za-z0-9_-]*(?:\s+(?:Ames|Creek|Town|Heights|Villa|Village|Brook))?)',query,re.I)
    if match and 'neighborhood' not in result: result['neighborhood']=match.group(1)
    if result.get('neighborhood'):
        name=str(result['neighborhood']).strip(); key=name.casefold().replace('_','').replace(' ',''); result['neighborhood']=NEIGHBORHOOD_ALIASES.get(key,name)
    return result

class ValuationService:
    def __init__(self):
        self.data=None; self.retriever=None
        if DATA_PATH.exists():
            self.data=pd.read_csv(DATA_PATH); self.data.columns=self.data.columns.str.strip()
            if 'SalePrice' in self.data: self.retriever=HybridRetriever(self.data)
        self.predictor=Predictor(); self.graph=None
        try:
            from .graph.valuation_graph import build_valuation_graph
            self.graph=build_valuation_graph(self)
        except Exception: pass
    def status(self):
        return {'dataset_loaded':self.retriever is not None,'model_loaded':self.predictor.ready,'chroma_loaded':bool(self.retriever and self.retriever.chroma),'langgraph_enabled':self.graph is not None,'property_count':int(len(self.data)) if self.data is not None else 0,'dataset_path':str(DATA_PATH)}
    def classification_stage(self,item):
        features=classify(item.query,item.model_dump(exclude={'query'},exclude_none=True))
        property_fields={'neighborhood','OverallQual','OverallCond','GrLivArea','TotalBsmtSF','GarageCars','GarageArea','YearBuilt','YearRemodAdd','FullBath','BedroomAbvGr','TotRmsAbvGrd','LotArea','GarageYrBlt'}
        if not any(features.get(key) is not None for key in property_fields):
            raise InvalidPropertyFeatures('Please describe the property with at least one detail, such as bedrooms, bathrooms, area, year built, quality, or neighborhood.')
        try: return PropertyInput.model_validate({**item.model_dump(),**features}).model_dump(exclude={'query'},exclude_none=True)
        except ValidationError as exc: raise InvalidPropertyFeatures(str(exc)) from exc
    def retrieval_stage(self,features):
        self.retriever.set_feedback_scores(comparable_feedback_scores())
        return self.retriever.search(features)
    def valuation_stage(self,features,comparables,retrieval):
        prices=[float(c['SalePrice']) for c in comparables if pd.notna(c.get('SalePrice'))]
        try:
            prediction,x=self.predictor.predict(features)
            impacts=self.predictor.impacts(x)
            location=self._location_context(features)
            if location: impacts.append(location)
            return {'prediction':prediction,'impacts':impacts,'method':'model_with_comparables','fallback':False,'reason':None,'prices':prices}
        except Exception as exc:
            impacts=[]; location=self._location_context(features)
            if location: impacts.append(location)
            return {'prediction':float(pd.Series(prices).median()),'impacts':impacts,'method':'comparable_median_fallback','fallback':True,'reason':str(exc),'prices':prices}
    def _location_context(self,features):
        neighborhood=features.get('neighborhood')
        if not neighborhood or self.data is None or 'Neighborhood' not in self.data or 'SalePrice' not in self.data:return None
        prices=pd.to_numeric(self.data['SalePrice'],errors='coerce'); all_median=float(prices.median())
        local=prices[self.data['Neighborhood'].astype(str).str.casefold().eq(str(neighborhood).casefold())]
        local=local.dropna()
        if local.empty:return None
        delta=float(local.median()-all_median)
        return {'feature':'Neighborhood','impact':round(delta,2),'direction':'positive' if delta>=0 else 'negative','method':'historical_neighborhood_median','neighborhood':str(neighborhood),'local_median':round(float(local.median()),2),'dataset_median':round(all_median,2),'sample_count':int(len(local)),'interpretation':'Observed historical median difference; descriptive, not causal.'}
    def risk_stage(self,features,comparables,retrieval,valuation):
        prediction=valuation['prediction']; prices=valuation['prices']; dispersion=float(pd.Series(prices).std() if len(prices)>1 else prediction*.15); spread_ratio=dispersion/max(abs(prediction),1); similarity=sum(c['similarity_score'] for c in comparables)/max(len(comparables),1)/100
        expected_features=['OverallQual','OverallCond','GrLivArea','YearBuilt','BedroomAbvGr','FullBath','neighborhood']; completeness=sum(features.get(key) is not None for key in expected_features)/len(expected_features)
        confidence=max(.1,min(.95,.25+.3*similarity+.2*completeness+.15*max(0,1-spread_ratio)-.15*retrieval['fallback_used']-.1*valuation['fallback'])); width=max(dispersion,prediction*(.05+(1-confidence)*.2)); risk='LOW' if confidence>=.75 and spread_ratio<.2 else ('MEDIUM' if confidence>=.5 and spread_ratio<.4 else 'HIGH'); factors=[]
        if len(comparables)<5: factors.append(f'Only {len(comparables)} comparable properties were available.')
        if retrieval['fallback_used']: factors.append(retrieval['fallback_reason'])
        if completeness<.7: factors.append('The property description is incomplete; missing values were imputed using training medians.')
        if spread_ratio>=.25: factors.append(f'Comparable sale prices vary substantially ({spread_ratio:.0%} of the estimate).')
        if valuation['fallback']: factors.append('The trained prediction model was unavailable; a comparable-sale median was used.')
        if features.get('neighborhood') and not any(str(c.get('Neighborhood','')).casefold()==str(features['neighborhood']).casefold() for c in comparables): factors.append('No returned comparable is from the requested neighborhood.')
        return {'confidence':confidence,'width':width,'risk':risk,'factors':factors}

    @staticmethod
    def _money(value):
        number=float(value)
        return f"-${abs(number):,.0f}" if number<0 else f"${number:,.0f}"

    @staticmethod
    def _display_number(value):
        number=float(value)
        return f"{number:,.0f}" if number.is_integer() else f"{number:,.1f}"

    def _build_explanation(self,features,comparables,retrieval,valuation,risk,lower,upper):
        details=[]
        if features.get('BedroomAbvGr') is not None:
            count=float(features['BedroomAbvGr']); details.append(f"{self._display_number(count)} bedroom{'s' if count != 1 else ''}")
        if features.get('FullBath') is not None:
            count=float(features['FullBath']); details.append(f"{self._display_number(count)} full bathroom{'s' if count != 1 else ''}")
        if features.get('GrLivArea') is not None:
            details.append(f"{self._display_number(features['GrLivArea'])} sq ft of living area")
        if features.get('neighborhood'):
            details.append(f"in {str(features['neighborhood']).replace('_',' ')}")
        if features.get('YearBuilt') is not None:
            details.append(f"built in {self._display_number(features['YearBuilt'])}")
        ratings=[]
        if features.get('OverallQual') is not None:
            ratings.append(f"quality {self._display_number(features['OverallQual'])}/10")
        if features.get('OverallCond') is not None:
            ratings.append(f"condition {self._display_number(features['OverallCond'])}/10")
        if ratings:
            details.append(" and ".join(ratings))
        context=', '.join(details) if details else 'the supplied property details'

        prediction=float(valuation['prediction'])
        if valuation.get('fallback'):
            estimate_basis='A comparable-sale median was used because the trained model was unavailable'
        else:
            estimate_basis='The trained property model produced the estimate'
        paragraphs=[
            f"For a property described as {context}, the estimate is {self._money(prediction)}, with a range of {self._money(lower)} to {self._money(upper)}. {estimate_basis}.",
        ]

        prices=[float(item['SalePrice']) for item in comparables if item.get('SalePrice') is not None and pd.notna(item.get('SalePrice'))]
        if prices:
            paragraphs.append(
                f"The {len(prices)} returned historical comparables have sale prices from "
                f"{self._money(min(prices))} to {self._money(max(prices))}; their median is {self._money(pd.Series(prices).median())}."
            )
        else:
            paragraphs.append('No priced comparable properties were available to support this estimate.')

        impacts=[item for item in valuation.get('impacts',[]) if item.get('method') in {'shap_tree_explainer','feature_importance_fallback'}]
        positives=[item for item in impacts if float(item.get('impact',0))>0]
        negatives=[item for item in impacts if float(item.get('impact',0))<0]
        positives.sort(key=lambda item:float(item['impact']),reverse=True)
        negatives.sort(key=lambda item:float(item['impact']))
        if impacts:
            method=impacts[0].get('method')
            direction='SHAP attributed' if method=='shap_tree_explainer' else 'The feature-importance fallback highlighted'
            impact_text=[]
            if positives:
                item=positives[0]
                impact_text.append(f"{item['feature']} as the largest upward model impact ({self._money(item['impact'])})")
            if negatives:
                item=negatives[0]
                impact_text.append(f"{item['feature']} as the largest downward model impact ({self._money(item['impact'])})")
            if impact_text:
                paragraphs.append(f"{direction} " + ' and '.join(impact_text) + ". These are model explanations, not causal effects.")

        if features.get('neighborhood'):
            location=next((item for item in valuation.get('impacts',[]) if item.get('method')=='historical_neighborhood_median'),None)
            if location:
                paragraphs.append(
                    f"In the training data, {str(features['neighborhood']).replace('_',' ')} had a median sale price of "
                    f"{self._money(location['local_median'])} across {location['sample_count']} sales, compared with "
                    f"{self._money(location['dataset_median'])} across the full dataset. This is historical context, not a causal effect."
                )

        confidence=float(risk['confidence'])
        paragraphs.append(f"The risk level is {risk['risk']} and the confidence indicator is {confidence:.0%}; that indicator is a heuristic, not a probability that the estimate is correct.")
        reasons=list(risk.get('factors') or [])
        if retrieval.get('fallback_used') and retrieval.get('fallback_reason') and retrieval['fallback_reason'] not in reasons:
            reasons.insert(0,retrieval['fallback_reason'])
        if reasons:
            paragraphs.append('Safeguards: ' + ' '.join(reasons[:3]))
        else:
            paragraphs.append('The current checks did not flag missing core details, sparse comparable evidence, or a retrieval fallback.')
        paragraphs.append('This estimate is based on historical Ames sales; it is not a guarantee or a causal claim.')
        return ' '.join(paragraphs)

    def decision_stage(self,features,comparables,retrieval,valuation,risk):
        prediction=valuation['prediction']; width=risk['width']; lower=max(0,prediction-width); upper=prediction+width
        explanation=self._build_explanation(features,comparables,retrieval,valuation,risk,lower,upper)
        return {'status':'success','property_features':features,'predicted_value':round(prediction,2),'valuation_range':{'lower':round(lower,2),'upper':round(upper,2)},'confidence':round(risk['confidence'],3),'risk_level':risk['risk'],'risk_factors':risk['factors'],'valuation_method':valuation['method'],'fallback_used':valuation['fallback'] or retrieval['fallback_used'],'fallback_reason':valuation['reason'] or retrieval['fallback_reason'],'comparables':comparables,'feature_impacts':valuation['impacts'],'retrieval':retrieval,'evidence':[c['document'] for c in comparables],'explanation':explanation,'evaluation':{'groundedness':None,'relevance':None,'note':'LLM judge is applied by the API layer.'}}
    def valuate(self,item):
        features=self.classification_stage(item)
        if not self.retriever: return {'status':'setup_required','message':'Dataset unavailable. Place the real Ames CSV at data/AmesHousing.csv and run the preparation/training commands.','property_features':features,'fallback_used':False}
        if self.graph: return self.graph.invoke({'item':item})['result']
        comparables,retrieval=self.retrieval_stage(features); valuation=self.valuation_stage(features,comparables,retrieval); risk=self.risk_stage(features,comparables,retrieval,valuation)
        return self.decision_stage(features,comparables,retrieval,valuation,risk)
