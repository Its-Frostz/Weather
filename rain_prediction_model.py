"""
Simplified October 2024 Rain Prediction Model
==============================================

Focused on testing model performance on October 2024 data specifically.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
    import xgboost as xgb
    print("✅ All ML libraries loaded successfully")
except ImportError as e:
    print(f"❌ Error importing libraries: {e}")
    print("Please install required packages with: pip install pandas numpy scikit-learn xgboost matplotlib seaborn")
    exit(1)

def load_and_process_data(data_file_path):
    """Load and process the weather data."""
    print("🔄 Loading weather data...")
    
    try:
        # Load Excel file - skip header rows and use row 5 as column names
        df = pd.read_excel(data_file_path, skiprows=4)
        
        # The actual column names are in the first row - use them as headers
        new_header = df.iloc[0]  # Get first row for headers
        df = df[1:]  # Take data without header row
        df.columns = new_header  # Set the header row as column names
        df = df.reset_index(drop=True)  # Reset index
        
        # Handle duplicate column names by making them unique
        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f'{dup}_{i}' for i in range(sum(cols == dup))]
        df.columns = cols
        
        print(f"✅ Successfully loaded Excel file with {len(df)} rows")
        
        print(f"📅 Available columns: {list(df.columns)[:10]}")
        
        # Convert datetime
        datetime_col = 'Date & Time'
        if datetime_col in df.columns:
            # Convert datetime if it's not already
            if not pd.api.types.is_datetime64_any_dtype(df[datetime_col]):
                df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')
            df = df.sort_values(datetime_col).reset_index(drop=True)
            print(f"📅 Date range: {df[datetime_col].min()} to {df[datetime_col].max()}")
        
        # Select key weather features - use the actual column names from CSV
        weather_cols = ['Date & Time', 'Temp - °C', 'Hum - %', 'Dew Point - °C', 
                       'Barometer - mb', 'Avg Wind Speed - km/h', 'Rain - mm']
        
        # Keep only existing columns
        available_cols = [col for col in weather_cols if col in df.columns]
        
        # Debug: print available columns
        print(f"🔍 Available weather columns: {[col for col in df.columns if any(x in col for x in ['Temp', 'Hum', 'Dew', 'Barometer', 'Wind', 'Rain', 'Date'])][:8]}")
        print(f"🎯 Selected columns: {available_cols}")
        
        if len(available_cols) < 2:
            print("❌ Not enough weather columns found")
            return None
            
        df = df[available_cols].copy()
        
        print(f"🎯 Using {len(available_cols)} weather features")
        
        # Handle missing values and data types - Excel should have better data types
        for col in df.columns:
            if col != 'Date & Time':
                try:
                    # Convert to numeric if not already
                    if df[col].dtype == 'object':
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        print(f"✅ Converted {col} to numeric")
                    else:
                        print(f"✅ Column {col} already numeric ({df[col].dtype})")
                except Exception as e:
                    print(f"⚠️ Warning: Could not convert column {col} to numeric: {e}")
        
        # Fill missing values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            df[numeric_cols] = df[numeric_cols].fillna(method='ffill').fillna(method='bfill')
        
        # Remove rows with remaining NaN values
        initial_rows = len(df)
        df = df.dropna()
        print(f"🧹 Removed {initial_rows - len(df)} rows with missing data")
        print(f"🧹 Final clean data: {len(df)} rows")
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_features(df):
    """Create prediction features."""
    print("⚙️ Creating features...")
    
    # Create lag features (past 4 intervals = 1 hour)
    # Use the actual column names that exist in the data
    all_cols = df.columns.tolist()
    
    # Find temperature, humidity, dew point, and pressure columns
    temp_col = next((col for col in all_cols if 'Temp' in col and '°C' in col or '�C' in col), None)
    humidity_col = next((col for col in all_cols if 'Hum' in col and '%' in col), None)
    dew_col = next((col for col in all_cols if 'Dew Point' in col), None)
    pressure_col = next((col for col in all_cols if 'Barometer' in col), None)
    rain_col = next((col for col in all_cols if 'Rain' in col and 'mm' in col), None)
    
    weather_features = [col for col in [temp_col, humidity_col, dew_col, pressure_col] if col is not None]
    
    print(f"🌡️ Found weather features: {weather_features}")
    
    # Create lag features
    for feature in weather_features:
        for lag in [1, 2, 3, 4]:
            df[f'{feature}_lag_{lag}'] = df[feature].shift(lag)
    
    # Create rolling averages
    for feature in weather_features:
        df[f'{feature}_avg_4h'] = df[feature].rolling(4).mean()
        df[f'{feature}_std_4h'] = df[feature].rolling(4).std()
    
    # Pressure trends (important for rain)
    if pressure_col:
        df['Pressure_Trend_1h'] = df[pressure_col].diff()
        df['Pressure_Trend_4h'] = df[pressure_col] - df[pressure_col].shift(4)
    
    # Time features
    df['Hour'] = df['Date & Time'].dt.hour
    df['Day_of_Year'] = df['Date & Time'].dt.dayofyear
    df['Month'] = df['Date & Time'].dt.month
    
    # Target: rain in NEXT interval
    if rain_col:
        df['Next_Rain'] = df[rain_col].shift(-1)
        df['Will_Rain_Next'] = (df['Next_Rain'] > 0).astype(int)
    else:
        df['Will_Rain_Next'] = 0
    
    # Identify October 2024 data
    df['Is_Oct_2024'] = ((df['Date & Time'].dt.month == 10) & (df['Date & Time'].dt.year == 2024))
    
    print(f"📈 Created features, October 2024 data: {df['Is_Oct_2024'].sum()} rows")
    
    return df

def split_oct_2024(df):
    """Split data with October 2024 as test set."""
    print("🔀 Splitting data - October 2024 as test set...")
    
    # Remove NaN rows created by lag features
    df_clean = df.dropna()
    print(f"📊 Clean data for modeling: {len(df_clean)} rows")
    
    # Split train/test
    train_data = df_clean[~df_clean['Is_Oct_2024']].copy()
    test_data = df_clean[df_clean['Is_Oct_2024']].copy()
    
    print(f"🏋️ Training data: {len(train_data)} rows")
    print(f"🧪 Test data (Oct 2024): {len(test_data)} rows")
    
    if len(test_data) == 0:
        raise ValueError("❌ No October 2024 data found!")
    
    # Select feature columns - exclude metadata and target columns
    exclude_cols = ['Date & Time', 'Next_Rain', 'Will_Rain_Next', 'Is_Oct_2024']
    
    # Also exclude the original rain column (find it dynamically)
    rain_cols = [col for col in df_clean.columns if 'Rain' in col and 'mm' in col and 'Next' not in col]
    exclude_cols.extend(rain_cols)
    
    feature_cols = [col for col in df_clean.columns if col not in exclude_cols]
    
    print(f"🎯 Using {len(feature_cols)} features for prediction")
    
    X_train = train_data[feature_cols]
    y_train = train_data['Will_Rain_Next']
    X_test = test_data[feature_cols]
    y_test = test_data['Will_Rain_Next']
    
    # Show target distributions
    train_rain_pct = y_train.mean() * 100
    test_rain_pct = y_test.mean() * 100
    
    print(f"🌧️ Training set: {train_rain_pct:.1f}% rain events")
    print(f"🌧️ October 2024 test: {test_rain_pct:.1f}% rain events")
    
    return X_train, X_test, y_train, y_test, feature_cols, test_data

def train_and_evaluate(X_train, X_test, y_train, y_test, feature_cols, test_data):
    """Train model and evaluate on October 2024."""
    print("🚀 Training XGBoost model...")
    
    # Train model
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric='logloss',
        verbosity=0
    )
    
    model.fit(X_train, y_train)
    
    # Training accuracy
    train_pred = model.predict(X_train)
    train_accuracy = accuracy_score(y_train, train_pred)
    
    # Test predictions
    test_pred = model.predict(X_test)
    test_proba = model.predict_proba(X_test)[:, 1]
    
    # Test metrics
    test_accuracy = accuracy_score(y_test, test_pred)
    precision = precision_score(y_test, test_pred, zero_division=0)
    recall = recall_score(y_test, test_pred, zero_division=0)
    f1 = f1_score(y_test, test_pred, zero_division=0)
    
    # Confusion matrix
    cm = confusion_matrix(y_test, test_pred)
    
    print("\\n" + "="*60)
    print("🎯 MODEL PERFORMANCE RESULTS")
    print("="*60)
    print(f"📊 TRAINING ACCURACY: {train_accuracy:.4f} ({train_accuracy*100:.2f}%)")
    print(f"📊 TEST ACCURACY (October 2024): {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")
    print(f"📊 PRECISION: {precision:.4f}")
    print(f"📊 RECALL: {recall:.4f}")
    print(f"📊 F1-SCORE: {f1:.4f}")
    
    print(f"\\n🗂️ CONFUSION MATRIX (October 2024):")
    print(f"                 Predicted")
    print(f"               No Rain  Rain")
    print(f"Actual No Rain   {cm[0,0]:4d}   {cm[0,1]:4d}")
    print(f"       Rain      {cm[1,0]:4d}   {cm[1,1]:4d}")
    
    # Analyze October 2024 patterns
    analyze_october_patterns(test_data, test_pred, test_proba, y_test)
    
    # Feature importance
    show_feature_importance(model, feature_cols)
    
    return {
        'train_accuracy': train_accuracy,
        'test_accuracy': test_accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'model': model
    }

def analyze_october_patterns(test_data, predictions, probabilities, y_true):
    """Analyze October 2024 specific patterns."""
    print("\\n🔍 OCTOBER 2024 DETAILED ANALYSIS:")
    print("-" * 50)
    
    # Create analysis dataframe
    analysis_df = test_data.copy()
    analysis_df['Predicted'] = predictions
    analysis_df['Probability'] = probabilities
    analysis_df['Correct'] = (y_true == predictions)
    
    # Daily summary
    analysis_df['Date'] = analysis_df['Date & Time'].dt.date
    daily_summary = analysis_df.groupby('Date').agg({
        'Will_Rain_Next': 'sum',
        'Predicted': 'sum', 
        'Probability': 'mean',
        'Correct': 'mean'
    }).round(3)
    
    # Find interesting days
    rain_days = daily_summary[daily_summary['Will_Rain_Next'] > 0]
    high_prob_days = daily_summary[daily_summary['Probability'] > 0.5]
    
    print(f"📅 Total days in October 2024: {len(daily_summary)}")
    print(f"🌧️ Days with actual rain: {len(rain_days)}")
    print(f"⚠️ Days with high rain probability (>50%): {len(high_prob_days)}")
    
    if len(rain_days) > 0:
        print(f"\\n🌧️ RAIN EVENT DAYS:")
        print(rain_days.to_string())
        
    # High probability events
    high_prob_events = analysis_df[analysis_df['Probability'] > 0.7]
    if len(high_prob_events) > 0:
        print(f"\\n⚠️ HIGH-RISK PREDICTIONS (>70% probability): {len(high_prob_events)} intervals")
        correct_high_risk = high_prob_events['Correct'].sum()
        print(f"   Correctly predicted: {correct_high_risk}/{len(high_prob_events)} ({correct_high_risk/len(high_prob_events)*100:.1f}%)")
        
        # Show some examples
        if len(high_prob_events) > 0:
            print("\\n   Sample high-risk predictions:")
            sample = high_prob_events[['Date & Time', 'Probability', 'Will_Rain_Next', 'Predicted']].head()
            print(sample.to_string(index=False))

def show_feature_importance(model, feature_cols):
    """Display top feature importances."""
    print("\\n🎯 TOP 10 MOST IMPORTANT FEATURES:")
    print("-" * 40)
    
    importance_df = pd.DataFrame({
        'Feature': feature_cols,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False)
    
    for i, (_, row) in enumerate(importance_df.head(10).iterrows()):
        print(f"{i+1:2d}. {row['Feature']:<25} {row['Importance']:.4f}")

def main():
    """Main execution."""
    print("🌧️ OCTOBER 2024 RAIN PREDICTION ANALYSIS")
    print("="*50)
    
    data_file = "data.xlsx"
    
    # Load and process data
    df = load_and_process_data(data_file)
    if df is None:
        return
    
    # Create features
    df = create_features(df)
    
    # Split data
    X_train, X_test, y_train, y_test, feature_cols, test_data = split_oct_2024(df)
    
    # Train and evaluate
    results = train_and_evaluate(X_train, X_test, y_train, y_test, feature_cols, test_data)
    
    print("\\n" + "="*60)
    print("✅ ANALYSIS COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("Key Insights:")
    print(f"• Model trained on {len(X_train)} non-October data points")
    print(f"• Tested on {len(X_test)} October 2024 data points") 
    print(f"• Training accuracy: {results['train_accuracy']*100:.2f}%")
    print(f"• October 2024 test accuracy: {results['test_accuracy']*100:.2f}%")
    print("\\nThis analysis shows how well the model predicts rain events")
    print("specifically during October 2024, based on training from other periods.")

if __name__ == "__main__":
    main()
