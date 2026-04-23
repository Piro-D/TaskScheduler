"""
ADHD Academic Task Duration Estimator - High Accuracy Version
Features: IQR Outlier Removal, Dataset Cleaning, and Optimized Random Forest.
"""

import pandas as pd
import numpy as np
import joblib
import os
import warnings
from pathlib import Path

# Machine Learning Imports
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings('ignore')

# 1. PATH CONFIGURATION
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "Datasets" / "preprocessed_jira_data.csv"

# 2. TRAINING & EVALUATION FUNCTION
def train_evaluate_and_save():
    if not DATA_PATH.exists():
        print(f"❌ Error: Dataset not found at {DATA_PATH}")
        return

    # Cleanup old models
    for f in ['duration_model.pkl', 'encoder_task_type.pkl', 'encoder_complexity.pkl']:
        if os.path.exists(f): os.remove(f)

    df = pd.read_csv(DATA_PATH)
    
    # --- STEP A: INITIAL CLEANING ---
    df = df[(df['expert_estimated_effort'] > 0) & (df['actual_effort'] > 0)].copy()

    # --- STEP B: IQR OUTLIER REMOVAL ---
    # We focus on 'actual_effort' because that's our target "Truth"
    Q1 = df['actual_effort'].quantile(0.25)
    Q3 = df['actual_effort'].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    # Apply filter
    df_clean = df[(df['actual_effort'] >= lower_bound) & (df['actual_effort'] <= upper_bound)].copy()
    
    removed_count = len(df) - len(df_clean)
    print(f"🧹 Outlier Removal: Deleted {removed_count} noisy rows.")
    print(f"📊 Final Dataset Size: {len(df_clean)} rows.")

    # --- STEP C: ENCODING ---
    df_clean['task_type'] = df_clean['task_type'].fillna('general').astype(str)
    df_clean['complexity_class'] = df_clean['complexity_class'].fillna('M').astype(str)

    le_task = LabelEncoder()
    le_comp = LabelEncoder()

    df_clean['task_type_enc'] = le_task.fit_transform(df_clean['task_type'])
    df_clean['complexity_class_enc'] = le_comp.fit_transform(df_clean['complexity_class'])

    X = df_clean[['expert_estimated_effort', 'complexity_class_enc', 'task_type_enc']]
    y = df_clean['actual_effort']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- STEP D: OPTIMIZED MODEL ---
    # Increased estimators and adjusted min_samples to prevent overfitting
    model = RandomForestRegressor(
        n_estimators=300, 
        max_depth=12, 
        min_samples_leaf=4, 
        random_state=42,
        n_jobs=-1 # Uses all CPU cores for faster training
    )
    model.fit(X_train, y_train)

    # --- STEP E: EVALUATION ---
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    
    print("=" * 40)
    print("📊 OPTIMIZED MODEL RESULTS")
    print("=" * 40)
    print(f"MAE      : {mae:.2f} seconds")
    print(f"RMSE     : {rmse:.2f} seconds")
    print(f"R² Score : {r2:.4f}  <-- Check for improvement!")
    print("=" * 40)

    # Save Artifacts
    joblib.dump(model, 'duration_model.pkl')
    joblib.dump(le_task, 'encoder_task_type.pkl')
    joblib.dump(le_comp, 'encoder_complexity.pkl')
    print("💾 Model and Encoders saved successfully.\n")

# 3. GLOBAL OBJECT LOADING
def load_model_objects():
    try:
        m = joblib.load('duration_model.pkl')
        t = joblib.load('encoder_task_type.pkl')
        c = joblib.load('encoder_complexity.pkl')
        return m, t, c
    except:
        return None, None, None

# 4. ROBUST INFERENCE
def predict_duration_adhd(expert_est_sec, complexity_str, task_type_str, buffer=1.2):
    model, le_task, le_comp = load_model_objects()
    if model is None: return "Error: Model files not found."

    t_str, c_str = str(task_type_str), str(complexity_str)
    if t_str not in le_task.classes_: t_str = le_task.classes_[0]
    if c_str not in le_comp.classes_: c_str = le_comp.classes_[0]

    t_enc = le_task.transform([t_str])[0]
    c_enc = le_comp.transform([c_str])[0]

    X_input = pd.DataFrame(
        [[expert_est_sec, c_enc, t_enc]],
        columns=['expert_estimated_effort', 'complexity_class_enc', 'task_type_enc']
    )
    
    pred_sec = model.predict(X_input)[0]
    return round((pred_sec / 60) * buffer, 1)

if __name__ == "__main__":
    train_evaluate_and_save()
    
    # Test
    print("🚀 SAMPLE PREDICTION...")
    result = predict_duration_adhd(3600, "M", "coding")
    print(f"👉 Suggested ADHD Duration: {result} minutes")