import sqlite3, time, os, numpy as np, pandas as pd, joblib
DB="learning_data.db"
MODEL_DIR="models"
os.makedirs(MODEL_DIR,exist_ok=True)

def fetch_data():
    if not os.path.exists(DB): return pd.DataFrame()
    con=sqlite3.connect(DB)
    df=pd.read_sql("SELECT * FROM trades",con)
    con.close()
    return df

def train_model():
    df=fetch_data()
    if df.empty: 
        print("⚠️ No data yet for training."); return
    X=df[['pnl','risk']].values
    y=(df['pnl']/ (df['risk']+1e-6)).values
    weights=np.polyfit(X[:,0],y,1)
    score=np.mean(y)
    model_file=f"{MODEL_DIR}/model_{time.strftime('%Y%m%d_%H%M%S')}.pkl"
    joblib.dump({'weights':weights,'score':score},model_file)
    print(f"🧠 Trained model saved: {model_file} | score={score:.4f}")
    best_model=find_best_model()
    joblib.dump(best_model,f"{MODEL_DIR}/active_model.pkl")
    print("✅ Best model reloaded for live use.")

def find_best_model():
    models=[f for f in os.listdir(MODEL_DIR) if f.endswith('.pkl')]
    if not models: return None
    best=None;best_score=-1e9
    for m in models:
        data=joblib.load(os.path.join(MODEL_DIR,m))
        s=data.get('score',0)
        if s>best_score:best=data;best_score=s
    return best

def loop():
    while True:
        print("🔁 Trainer Daemon tick — checking for new data...")
        train_model()
        time.sleep(3600*24)  # once a day

if __name__=="__main__":
    loop()
