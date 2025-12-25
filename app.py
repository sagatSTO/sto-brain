from flask import Flask, request, jsonify
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG STO
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"
INITIAL_CAPITAL = 1000
RISK_PER_TRADE = 0.02  # 2%

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "PAPER",
    "decision_mode": "C",
    "start_time": time.time(),
    "journal": []
}

# ======================
# INDICATEURS
# ======================
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(-min(diff, 0))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# BACKTEST MOTEUR
# ======================
def backtest_series(prices):
    capital = INITIAL_CAPITAL
    position = 0
    decisions = []

    for i in range(20, len(prices)):
        window = prices[:i]
        price = prices[i]
        rsi = calculate_rsi(window)
        ema_fast = calculate_ema(window, 10)
        ema_slow = calculate_ema(window, 20)

        action = "HOLD"

        if rsi and ema_fast and ema_slow:
            if rsi < 30 and ema_fast > ema_slow:
                risk_amount = capital * RISK_PER_TRADE
                position = risk_amount / price
                capital -= risk_amount
                action = "BUY"
            elif rsi > 70 and position > 0:
                capital += position * price
                position = 0
                action = "SELL"

        decisions.append({
            "price": price,
            "rsi": rsi,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "action": action
        })

    final_value = capital + position * prices[-1]

    return {
        "capital_final": round(final_value, 2),
        "profit_pct": round((final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2),
        "decisions": decisions
    }

# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return jsonify({
        "statut": "STO ONLINE",
        "mode": sto_state["mode"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

@app.route("/backtest", methods=["POST"])
def backtest():
    data = request.json or {}
    series_list = data.get("series")

    if not series_list or not isinstance(series_list, list):
        return jsonify({"error": "Aucune série fournie"}), 400

    results = []
    for idx, series in enumerate(series_list):
        if len(series) < 30:
            continue
        result = backtest_series(series)
        result["series_id"] = idx
        results.append(result)
        sto_state["journal"].append(result)

    return jsonify({
        "mode": "BACKTEST",
        "tests": results
    })

@app.route("/journal")
def journal():
    return jsonify(sto_state["journal"])

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
