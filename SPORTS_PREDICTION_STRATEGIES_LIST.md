# 🏆 Complete List of Prediction Strategies & Agents for Sports Betting

## Overview

The NeoLight sports betting system uses a **multi-layered, ensemble-based approach** with **world-class predictive factors** and **multiple machine learning models**.

---

## 📊 **PREDICTION MODELS (Ensemble System)**

### 1. **Random Forest** (`random_forest`)

- **Type**: Ensemble (tree-based)
- **Parameters**: 400 estimators, max_depth=10
- **Use Case**: General prediction, robust to overfitting
- **Weight**: Based on accuracy (0.6-0.995)

### 2. **Gradient Boosting** (`gradient_boosting`)

- **Type**: Boosting ensemble
- **Library**: scikit-learn
- **Use Case**: Sequential learning, captures complex patterns
- **Weight**: Based on accuracy

### 3. **Logistic Regression** (`logistic_regression`)

- **Type**: Linear classifier
- **Parameters**: max_iter=2000, solver="lbfgs"
- **Use Case**: Baseline model, interpretable
- **Weight**: Based on accuracy

### 4. **Multi-Layer Perceptron** (`mlp`)

- **Type**: Neural network
- **Architecture**: Hidden layers (64, 32), max_iter=1500
- **Use Case**: Non-linear relationships
- **Weight**: Based on accuracy

### 5. **XGBoost** (`xgboost`) - *Optional*

- **Type**: Gradient boosting
- **Library**: XGBoost
- **Parameters**:
  - n_estimators=500
  - max_depth=8
  - learning_rate=0.05
  - subsample=0.8
  - colsample_bytree=0.8
- **Use Case**: High-performance boosting
- **Weight**: Based on accuracy

### 6. **LightGBM** (`lightgbm`) - *Optional*

- **Type**: Gradient boosting (Microsoft)
- **Library**: LightGBM
- **Parameters**:
  - n_estimators=600
  - max_depth=8
  - learning_rate=0.05
- **Use Case**: Fast, memory-efficient boosting
- **Weight**: Based on accuracy

### 7. **Optuna-Optimized LightGBM** (`lightgbm_optuna_{regime}`)

- **Type**: Hyperparameter-optimized LightGBM
- **Library**: Optuna + LightGBM
- **Optimization**: TPE sampler, 20+ trials per regime
- **Use Case**: Regime-specific optimization (regular season, playoffs, etc.)
- **Weight**: Based on accuracy (0.6-0.995)

### 8. **Sequence GRU** (`sequence_gru`) - *Optional*

- **Type**: Recurrent Neural Network
- **Library**: TensorFlow/Keras
- **Architecture**:
  - Bidirectional GRU (32 units)
  - Dropout (0.2)
  - Dense layers (16 → 1)
- **Use Case**: Temporal patterns in team performance sequences
- **Weight**: Based on accuracy

### 9. **Transformer Sequence** (`sequence_transformer`) - *Optional*

- **Type**: Attention-based model
- **Library**: TensorFlow/Keras
- **Architecture**:
  - Multi-head attention (4 heads)
  - Feed-forward network (64 units)
  - Layer normalization
- **Use Case**: Long-term dependencies in team sequences
- **Weight**: Based on accuracy

### 10. **Multi-Task Dense** (`multitask_dense`) - *Optional*

- **Type**: Multi-task neural network
- **Library**: TensorFlow/Keras
- **Architecture**: Dense layers (64 → 32 → 1)
- **Use Case**: Cross-sport learning (NBA, NFL, Soccer)
- **Weight**: Based on accuracy

### 11. **Meta-Learner** (`meta_logistic`)

- **Type**: Stacked ensemble
- **Library**: scikit-learn (CalibratedClassifierCV)
- **Method**: Logistic regression on model probabilities
- **Calibration**: Isotonic calibration with cross-validation
- **Use Case**: Combines all base models, improves calibration
- **Weight**: High (0.65-0.995) - **FINAL PREDICTION**

---

## 🎯 **PREDICTIVE FACTORS (World-Class Features)**

### **Core Factors (Phase 1)**

#### 1. **Real Team Records**

- **Source**: ESPN API (NBA/NFL), API-Football (Soccer)
- **Metric**: Win-loss records, win percentage
- **Impact**: Base Elo rating calculation (1300-1700 range)
- **Implementation**: `fetch_team_record_espn()`, `fetch_team_record_from_scoreboard()`

#### 2. **Elo Rating System**

- **Source**: Historical game results
- **Base Rating**: 1500
- **K-Factor**: 32 (dynamic adjustment)
- **Home Advantage**: +100 Elo
- **Impact**: Primary team strength metric
- **Implementation**: `EloRatingSystem` class

#### 3. **Team Rest & Fatigue**

- **Source**: Game schedule analysis
- **Factors**:
  - Back-to-back games (0 days rest) = -150 Elo penalty
  - 1 day rest = -50 Elo penalty
  - 2+ days rest = 0 penalty
- **Impact**: Significant for NBA/NFL (fatigue matters)
- **Implementation**: `calculate_rest_days()` from `analytics/sports_advanced_features.py`

#### 4. **Injury Impact**

- **Source**: RapidAPI (primary), ESPN scraping (fallback)
- **Factors**:
  - Player status (Out, Doubtful, Questionable)
  - Star player impact (weighted)
  - Position depth (critical positions)
- **Impact**: -50 Elo per "out" player, -25 per "doubtful"
- **Implementation**: `InjuryTracker` class, `fetch_injury_data_espn()`

---

### **Advanced Factors (Phase 2)**

#### 5. **Momentum & Recent Form**

- **Source**: Recent game history (last 5-10 games)
- **Factors**:
  - Win/loss streaks (current streak length)
  - Last 5 games win percentage (weighted 2x)
  - Last 10 games win percentage
  - Point differential trend (improving vs declining)
- **Impact**: +25 Elo per 3-game win streak, -25 per 3-game loss streak
- **Implementation**: `fetch_team_momentum()` from `analytics/world_class_functions.py`

#### 6. **Head-to-Head Matchup History**

- **Source**: Historical matchups (ESPN, cached history)
- **Factors**:
  - Last 10 meetings win percentage
  - Home/away H2H splits
  - Recent dominance patterns
- **Impact**: +/-50 Elo adjustment based on matchup history
- **Implementation**: `calculate_head_to_head()` from `analytics/world_class_functions.py`

#### 7. **Schedule Strength**

- **Source**: Opponent Elo ratings (recent 5 games)
- **Factors**:
  - Average opponent Elo rating
  - Strength of schedule bias
  - Inflated/deflated stats adjustment
- **Impact**: Adjusts for quality of recent opponents
- **Implementation**: `calculate_schedule_strength()` from `analytics/world_class_functions.py`

#### 8. **Travel & Time Zone Impact**

- **Source**: Team city database, geographic calculations
- **Factors**:
  - Travel distance (miles between cities)
  - Time zone changes (1+ hour = -25 Elo)
  - East coast playing late on West coast = additional penalty
- **Impact**:
  - Travel > 1500 miles = -50 Elo
  - Time zone change = -25 Elo
- **Implementation**: `calculate_travel_impact()` from `analytics/world_class_functions.py`

#### 9. **Home Advantage**

- **Source**: Venue-specific historical performance
- **Impact**: +100 Elo base bonus for home team
- **Calculation**: Adjusted by team's historical home performance
- **Implementation**: `calculate_home_advantage_score()` from `analytics/sports_advanced_features.py`

---

### **Market Intelligence (Phase 3)**

#### 10. **Market Odds & Line Movement**

- **Source**: ESPN implied odds, odds comparison sites (free)
- **Factors**:
  - Opening line vs current line
  - Line movement direction
  - Sharp money signals (line moving against public)
- **Impact**: Adjusts confidence, identifies value bets
- **Implementation**: `fetch_market_odds()` from `analytics/world_class_functions.py`

#### 11. **Expected Value (EV) Calculation**

- **Formula**: `EV = (Model Probability - Market Implied Probability) × Stake`
- **Threshold**: 2% minimum edge (configurable via `SPORTS_EDGE_THRESHOLD`)
- **Use Case**: Identifies profitable bets

#### 12. **CLV (Closing Line Value)**

- **Definition**: Difference between opening and closing odds
- **Impact**: Measures prediction quality (sharp bettors beat closing line)
- **Calculation**: `calculate_clv(home_prob_open, home_prob_implied)`

---

## 🔄 **ENSEMBLE COMBINATION STRATEGY**

### **Weighted Average Ensemble**

- **Method**: Accuracy-weighted averaging of all model probabilities
- **Formula**: `ensemble_prob = Σ(model_prob × model_weight) / Σ(weights)`
- **Weights**: Based on test accuracy (clipped to 0.6-0.995 range)
- **Final Prediction**: Meta-learner if available, else weighted ensemble

### **Bayesian Aggregation**

- **Method**: Beta distribution fitting
- **Parameters**: Alpha, Beta from model weights and probabilities
- **Output**: Mean, variance, confidence intervals
- **Use Case**: Uncertainty quantification

---

## 📈 **FEATURE ENGINEERING**

### **Base Features (16 total)**

1. Home team win percentage
2. Away team win percentage
3. Home team average points
4. Away team average points
5. Home team average points allowed
6. Away team average points allowed
7. Home team rest days
8. Away team rest days
9. Market implied home probability
10. Market implied away probability
11. Opening home probability
12. Opening away probability
13. Line movement
14. Home Elo rating
15. Away Elo rating
16. Elo difference

### **Sequence Features (Temporal)**

- **Window Size**: 5-10 games (configurable)
- **Features per game**: Same as base features
- **Use Case**: RNN/Transformer models for temporal patterns

### **Regime Detection**

- **Types**: Regular season, playoffs, post-All-Star (NBA), etc.
- **Impact**: Regime-specific model training and prediction
- **Method**: Feature-based regime detection
- **Benefit**: Better performance in different contexts

---

## 🎯 **PREDICTION WORKFLOW**

### **1. Data Collection** (Free Sources)

- ESPN Public API (NBA, NFL, MLB) - **FREE**
- API-Football (Soccer) - **FREE** (unlimited tier)
- TheSportsDB (All sports) - **FREE** (public API)
- SofaScore (Soccer) - **FREE** (scraping)
- RapidAPI (Injuries) - **FREE** (with free tier)

### **2. Feature Building**

- `FeatureBuilder` class (`agents/sports_analytics_agent.py`)
- Builds historical datasets from game records
- Calculates rolling statistics (win%, points, etc.)
- Updates Elo ratings incrementally
- Extracts odds metadata

### **3. Model Training**

- `train_ensemble()` function
- Trains all available models
- Cross-validates on test set (20% split)
- Calibrates probabilities (isotonic calibration)
- Trains meta-learner on base model predictions

### **4. Prediction Generation**

- `ensemble_predict()` function
- Builds features for future games
- Runs all models
- Combines predictions (weighted average)
- Calculates edge, confidence, EV

### **5. World-Class Prediction** (`calculate_comprehensive_prediction`)

- Integrates ALL factors (not just ML models)
- Uses statistical adjustments (Elo-based)
- Applies all 12+ factors
- Generates comprehensive explanations

---

## 🏗️ **AGENT ARCHITECTURE**

### **Main Agent**: `agents/sports_analytics_agent.py`

- **Purpose**: Trains models, generates predictions
- **Output**: `state/sports_predictions_{sport}.json`
- **Frequency**: Runs periodically (configurable)

### **Realtime Agent**: `agents/sports_realtime_schedule.py`

- **Purpose**: Fetches today's games from free sources
- **Integration**: Feeds into `sports_analytics_agent.py`

### **Free Data Agent**: `analytics/free_sports_data.py`

- **Purpose**: Zero-cost data fetching and statistical predictions
- **Functions**:
  - `get_free_sports_schedule()` - Main entry point
  - `calculate_comprehensive_prediction()` - World-class predictions
  - `generate_world_class_explanation()` - Human-readable explanations

---

## 📊 **PREDICTION FACTORS SUMMARY**

### **Total Predictive Factors: 12+**

1. ✅ **Real Team Records** (wins, losses, win%)
2. ✅ **Elo Rating System** (team strength)
3. ✅ **Team Rest & Fatigue** (back-to-back, days off)
4. ✅ **Injury Impact** (players out, doubtful)
5. ✅ **Momentum & Recent Form** (streaks, recent win%)
6. ✅ **Head-to-Head History** (last 10 meetings)
7. ✅ **Schedule Strength** (opponent quality)
8. ✅ **Travel & Time Zone** (distance, timezone change)
9. ✅ **Home Advantage** (venue-specific)
10. ✅ **Market Odds** (implied probabilities)
11. ✅ **Line Movement** (sharp money signals)
12. ✅ **CLV (Closing Line Value)** (prediction quality)

---

## 🎯 **MODELS SUMMARY**

### **Total Models: 11**

1. ✅ **Random Forest** (400 trees)
2. ✅ **Gradient Boosting** (scikit-learn)
3. ✅ **Logistic Regression** (baseline)
4. ✅ **Multi-Layer Perceptron** (neural network)
5. ✅ **XGBoost** (optional, 500 estimators)
6. ✅ **LightGBM** (optional, 600 estimators)
7. ✅ **Optuna LightGBM** (regime-specific, optimized)
8. ✅ **Sequence GRU** (RNN, temporal patterns)
9. ✅ **Transformer** (attention, long-term dependencies)
10. ✅ **Multi-Task Dense** (cross-sport learning)
11. ✅ **Meta-Logistic** (ensemble combiner, **FINAL**)

---

## 🔧 **CONFIGURATION**

### **Environment Variables**

- `SPORTS_ENABLED`: "nfl,nba,mlb" (sports to process)
- `SPORTS_HISTORY_YEARS`: 7 (years of historical data)
- `SPORTS_CONFIDENCE_THRESHOLD`: 0.6 (minimum confidence)
- `SPORTS_EDGE_THRESHOLD`: 0.02 (minimum edge %)
- `SPORTS_USE_ELO`: "true" (enable Elo ratings)
- `SPORTS_USE_INJURIES`: "true" (enable injury tracking)
- `SPORTS_USE_REST_DAYS`: "true" (enable rest analysis)
- `SPORTS_USE_WEATHER`: "true" (placeholder for outdoor sports)

### **Model Configuration**

- `SPORTS_OPTUNA_TRIALS`: 20 (hyperparameter optimization trials)
- `SPORTS_OPTUNA_TIMEOUT`: 180 (seconds)
- `SPORTS_SEQUENCE_WINDOW`: 5 (temporal sequence length)
- `SPORTS_TRANSFORMER_HEADS`: 4 (attention heads)
- `SPORTS_MIN_REGIME_SAMPLES`: 120 (minimum samples per regime)

---

## 📈 **PERFORMANCE METRICS**

### **Current Accuracy** (from documentation)

- **NBA**: 64% accuracy, 745-758 edges
- **Soccer**: 72-74% accuracy, 1,991-2,061 edges
- **Combined**: 1,817 opportunities above 3% edge threshold

### **Evaluation Metrics**

- Accuracy (win/loss prediction)
- Log Loss (probability calibration)
- Brier Score (probability accuracy)
- Simulated ROI (backtesting)
- CLV (Closing Line Value)
- Bayesian Variance (uncertainty)

---

## 🌐 **DATA SOURCES (All FREE)**

1. **ESPN Public API** - No API key needed
2. **API-Football** - Free unlimited tier
3. **TheSportsDB** - Free public API
4. **SofaScore** - Free scraping (soccer)
5. **RapidAPI** - Free tier for injuries

**Cost**: $0/month - Completely free!

---

## 📝 **Files**

- **Main Agent**: `agents/sports_analytics_agent.py`
- **Free Data**: `analytics/free_sports_data.py`
- **World-Class Functions**: `analytics/world_class_functions.py`
- **Advanced Features**: `analytics/sports_advanced_features.py`
- **Realtime Schedule**: `agents/sports_realtime_schedule.py`

---

**Status**: ✅ **PRODUCTION READY** - All strategies active and integrated
