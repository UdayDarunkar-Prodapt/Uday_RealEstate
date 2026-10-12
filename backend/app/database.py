import json, sqlite3
from datetime import datetime, timezone
from .config import DB_PATH

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def initialize():
    try:
        with _connect() as c:
            c.executescript("""CREATE TABLE IF NOT EXISTS query_history(id INTEGER PRIMARY KEY, query TEXT, timestamp TEXT);
            CREATE TABLE IF NOT EXISTS valuation_history(id INTEGER PRIMARY KEY, query_id INTEGER, predicted_value REAL, lower_bound REAL, upper_bound REAL, confidence REAL, risk_level TEXT, valuation_method TEXT, fallback_used INTEGER, payload TEXT, timestamp TEXT);
            CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY, query_id INTEGER, rating INTEGER, comment TEXT, timestamp TEXT);
            CREATE TABLE IF NOT EXISTS evaluation_results(id INTEGER PRIMARY KEY, query_id INTEGER, payload TEXT, timestamp TEXT);
            CREATE TABLE IF NOT EXISTS fallback_events(id INTEGER PRIMARY KEY, component TEXT, fallback_type TEXT, reason TEXT, timestamp TEXT);""")
        return True
    except sqlite3.Error:
        return False

def save_valuation(query, result):
    try:
        now = datetime.now(timezone.utc).isoformat()
        with _connect() as c:
            cur=c.execute("INSERT INTO query_history(query,timestamp) VALUES(?,?)", (query,now)); qid=cur.lastrowid
            c.execute("INSERT INTO valuation_history(query_id,predicted_value,lower_bound,upper_bound,confidence,risk_level,valuation_method,fallback_used,payload,timestamp) VALUES(?,?,?,?,?,?,?,?,?,?)", (qid,result.get('predicted_value'),result.get('valuation_range',{}).get('lower'),result.get('valuation_range',{}).get('upper'),result.get('confidence'),result.get('risk_level'),result.get('valuation_method'),int(result.get('fallback_used',False)),json.dumps(result),now))
            return qid
    except sqlite3.Error: return None

def save_feedback(item):
    try:
        with _connect() as c: c.execute("INSERT INTO feedback(query_id,rating,comment,timestamp) VALUES(?,?,?,?)", (item.query_id,item.rating,item.comment,datetime.now(timezone.utc).isoformat()))
        return True
    except sqlite3.Error: return False

def comparable_feedback_scores(min_votes=3):
    """Return a small ranking prior from repeatedly rated valuation evidence."""
    try:
        with _connect() as c:
            rows=c.execute("SELECT v.payload,f.rating FROM feedback f JOIN valuation_history v ON v.query_id=f.query_id WHERE f.query_id IS NOT NULL").fetchall()
        totals={}
        for payload,rating in rows:
            try: properties=json.loads(payload).get('comparables',[])
            except (TypeError,json.JSONDecodeError): continue
            for prop in properties:
                pid=prop.get('property_id')
                if pid is None: continue
                count,total=totals.get(int(pid),(0,0)); totals[int(pid)]=(count+1,total+int(rating))
        # Keep feedback deliberately small; it can break close ranking ties, but
        # cannot outweigh actual similarity or change a predicted price.
        return {pid:(0.002*max(-1,min(1,total/count))) for pid,(count,total) in totals.items() if count>=min_votes}
    except sqlite3.Error: return {}

def save_evaluation(query_id, evaluation):
    try:
        with _connect() as c: c.execute("INSERT INTO evaluation_results(query_id,payload,timestamp) VALUES(?,?,?)", (query_id,json.dumps(evaluation),datetime.now(timezone.utc).isoformat()))
        return True
    except sqlite3.Error: return False
