import os
import pickle
import numpy as np
import yfinance as yf
from typing import Dict, List, Any, Optional
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import MinMaxScaler
import pandas as pd

# Reproducibility
tf.random.set_seed(42)
np.random.seed(42)

# Enable GPU acceleration if available
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"GPU acceleration enabled: {len(gpus)} GPU(s) detected.")
else:
    print("No GPU detected by TensorFlow. (Note: On Windows, TF > 2.10 requires WSL2 for GPU support)")

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def build_lstm_model(input_shape):
    model = Sequential([
        Input(shape=input_shape),
        LSTM(units=50, return_sequences=True),
        LSTM(units=50, return_sequences=False),
        Dense(units=25),
        Dense(units=1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def run_prediction(tickers: List[str], predict_days: int = 30, epochs: int = 20, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Prediction Agent
    Improved LSTM forecasting...
    """
    from firebase.firestore_service import update_analysis_status
    results = {}

    for i, ticker in enumerate(tickers):
        try:
            if user_id:
                update_analysis_status(user_id, f"Predicting {ticker} ({i+1}/{len(tickers)})...")
            
            print(f"Starting prediction for {ticker}...")
            # Fetch last 3 years of daily data for training
            data = yf.download(ticker, period="3y", progress=False)
            if data.empty or len(data) < 60 + predict_days:
                print(f"Insufficient data for {ticker}, using fallback.")
                results[ticker] = {"expected_return": 0.05, "backtest_mse": None}
                continue

            # Fix: Handle yfinance MultiIndex or DataFrame columns
            if isinstance(data['Close'], pd.DataFrame):
                close_series = data['Close'].iloc[:, 0].dropna()
            else:
                close_series = data['Close'].dropna()
            
            close_data = close_series.values.reshape(-1, 1)

            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(close_data)

            # Prepare sequences
            seq_len = 60
            X = []
            y = []
            for i in range(seq_len, len(scaled_data)):
                X.append(scaled_data[i - seq_len:i, 0])
                y.append(scaled_data[i, 0])

            X = np.array(X)
            y = np.array(y)
            X = X.reshape((X.shape[0], X.shape[1], 1))

            # Train/test split (time-series aware)
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]

            model_path = os.path.join(MODELS_DIR, f"{ticker}.keras")
            scaler_path = os.path.join(MODELS_DIR, f"{ticker}_scaler.pkl")

            # Load existing model if available
            model = None
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                # Check model freshness (disable loading if older than 24 hours to force daily update)
                import time
                file_age = time.time() - os.path.getmtime(model_path)
                if file_age < 86400: # 24 hours
                    try:
                        model = load_model(model_path)
                        with open(scaler_path, 'rb') as f:
                            saved_scaler = pickle.load(f)
                        scaler = saved_scaler
                        print(f"Loaded fresh model for {ticker}")
                    except Exception:
                        model = None
                else:
                    print(f"Model for {ticker} is stale (>24h). Retraining...")

            if model is None:
                print(f"Training LSTM model for {ticker} with {len(X_train)} samples...")
                model = build_lstm_model((seq_len, 1))
                callbacks = [
                    EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True),
                    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2)
                ]
                history = model.fit(
                    X_train, y_train,
                    epochs=epochs,
                    batch_size=32,
                    validation_data=(X_test, y_test),
                    callbacks=callbacks,
                    verbose=1
                )
                # Save model and scaler
                try:
                    model.save(model_path)
                    with open(scaler_path, 'wb') as f:
                        pickle.dump(scaler, f)
                except Exception as e:
                    print(f"Warning: failed to save model/scaler for {ticker}: {e}")

            # Basic backtest evaluation on test set
            try:
                y_pred_test = model.predict(X_test, verbose=0).flatten()
                # Inverse transform for real scale
                y_test_prices = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
                y_pred_prices = scaler.inverse_transform(y_pred_test.reshape(-1, 1)).flatten()
                backtest_mse = float(((y_test_prices - y_pred_prices) ** 2).mean())
            except Exception as e:
                print(f"Backtest failed for {ticker}: {e}")
                backtest_mse = None

            # Predict future prices iteratively using the latest sequence (from scaled_data)
            last_seq = scaled_data[-seq_len:].reshape(seq_len, 1)
            predicted_scaled = []
            for _ in range(predict_days):
                pred = model.predict(np.array([last_seq]), verbose=0)
                predicted_scaled.append(pred[0][0])
                last_seq = np.vstack([last_seq[1:], pred.reshape(1, 1)])

            predicted_prices = scaler.inverse_transform(np.array(predicted_scaled).reshape(-1, 1)).flatten()
            final_pred_price = predicted_prices[-1]
            current_price = close_series.iloc[-1]

            # Calculate total return over the prediction period (CAGR-based annualization)
            # We predict 30 days ahead, so we annualize based on that horizon
            total_return_pct = (final_pred_price - current_price) / current_price
            
            # Annualize: ((1 + R)^(252/T)) - 1
            # Using 21 trading days approx for 30 calendar days
            expected_return = ((1 + total_return_pct) ** (252 / 21)) - 1
            
            # Sanity Cap: 100% Annualized
            expected_return = max(0.01, min(1.0, expected_return))

            print(f"Prediction completed for {ticker}. Expected return: {expected_return:.4f}")
            results[ticker] = {
                "expected_return": round(float(expected_return), 4),
                "backtest_mse": backtest_mse,
                "model_path": model_path if os.path.exists(model_path) else None
            }
        except Exception as e:
            print(f"Prediction Error for {ticker}: {e}")
            results[ticker] = {"expected_return": 0.05, "backtest_mse": None}

    return results
