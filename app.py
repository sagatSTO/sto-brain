from flask import Flask, request, jsonify
import time
import math
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG STO
# ======================
STO_MODE = "OFFLINE"
DECISION_MODE = "SEMI_ACTIVE"  # CONSERVATEUR | SEMI_ACTIVE | AGRESSIF

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "start_time": time.time(),
    "last_signal": "NONE",
    "last_confirmation": "NONE"
}

# ======================
# JOURNAL TAPPER TRADING
# ======================
decision_journal = []

# ======================
# BACKUP MULTI-SÉRIES
# ======================
series_backup = []

# ======================
# INDICATEURS
# ======================
def ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema_val = prices[0]
    for p in prices[1:]:
        ema_val = p * k + ema_val * (1 - k)
    return round(ema_val, 2)

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# PAGE RACINE
# ======================
@app.route("/")
def home():
    return jsonify({
        "STO": "EN LIGNE",
        "mode": STO_MODE,
        "decision_mode": DECISION_MODE,
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

# ======================
# SIMULATION + LOGIQUE
# ======================
@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées"
        }), 400

    # Backup multisérie
    series_backup.append(prices)

    ema_short = ema(prices, 10)
    ema_long = ema(prices, 20)
    rsi_val = rsi(prices)

    # Signal
    signal = "HOLD"
    if ema_short and ema_long and rsi_val:
        if ema_short > ema_long and rsi_val > 55:
            signal = "BUY"
        elif ema_short < ema_long and rsi_val < 45:
            signal = "SELL"

    # Confirmation
    confirmation = "NO"
    if signal == "BUY" and rsi_val > 60:
        confirmation = "CONFIRMED"
    elif signal == "SELL" and rsi_val < 40:
        confirmation = "CONFIRMED"

    sto_state["last_signal"] = signal
    sto_state["last_confirmation"] = confirmation

    # Journalisation
    decision_journal.append({
        "timestamp": int(time.time()),
        "signal": signal,
        "confirmation": confirmation,
        "ema_short": ema_short,
        "ema_long": ema_long,
        "rsi": rsi_val
    })

    return jsonify({
        "mode": STO_MODE,
        "decision_mode": DECISION_MODE,
        "prix_actuel": prices[-1],
        "EMA_10": ema_short,
        "EMA_20": ema_long,
        "RSI": rsi_val,
        "signal": signal,
        "confirmation": confirmation
    })

# ======================
# JOURNAL
# ======================
@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(decision_journal)

# ======================
# BACKUP
# ======================
@app.route("/backup", methods=["GET"])
def backup():
    return jsonify({
        "nombre_series": len(series_backup),
        "series": series_backup[-3:]  # dernières séries
    })

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
