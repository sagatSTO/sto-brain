from flask import Flask, request, jsonify
import time
import random
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode_decision": "C",  # A = conservateur, B = normal, C = agressif
    "market_status": "OFFLINE",
    "last_action": "ATTENTE",
    "reason": "Mode simulation",
    "start_time": time.time(),
    "journal": []
}

# ======================
# UTILITAIRES SIMULATION
# ======================
def generate_prices(n=60, start=87000):
    prices = [start]
    for _ in range(n-1):
        prices.append(round(prices[-1] * (1 + random.uniform(-0.002, 0.002)), 2))
    return prices

def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    if len(prices) <= period:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return jsonify({
        "statut": "STO STABLE – MODE OFFLINE",
        "mode_decision": sto_state["mode_decision"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

@app.route("/simulate")
def simulate():
    prices = generate_prices()
    rsi = calculate_rsi(prices)
    ema_short = calculate_ema(prices, 10)
    ema_long = calculate_ema(prices, 20)

    if rsi is None or ema_short is None or ema_long is None:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées"
        }), 500

    if sto_state["mode_decision"] == "A":
        signal = "ATTENTE"
    elif sto_state["mode_decision"] == "B":
        signal = "ACHAT" if rsi < 35 else "ATTENTE"
    else:  # C
        signal = "ACHAT" if rsi < 45 and ema_short > ema_long else "ATTENTE"

    decision = {
        "prix_actuel": prices[-1],
        "RSI": rsi,
        "EMA10": ema_short,
        "EMA20": ema_long,
        "action": signal,
        "timestamp": time.time()
    }

    sto_state["journal"].append(decision)
    sto_state["last_action"] = signal
    sto_state["reason"] = "Décision simulée"

    return jsonify({
        "statut_marche": "OK",
        "source": "SIMULATION",
        "decision": decision
    })

@app.route("/journal")
def journal():
    return jsonify(sto_state["journal"][-20:])

@app.route("/set_mode/<mode>")
def set_mode(mode):
    if mode in ["A", "B", "C"]:
        sto_state["mode_decision"] = mode
        return jsonify({"mode": mode, "status": "OK"})
    return jsonify({"error": "mode invalide"}), 400

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
