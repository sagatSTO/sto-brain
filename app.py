from flask import Flask, request, jsonify
import time
import uuid
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"
MODE_DECISION = "C"  # A / B / C
CAPITAL_SIMULE = 1000
SEUIL_JOURNALIER = 3  # max décisions / jour

# ======================
# STOCKAGE (TABLES)
# ======================

# TABLE 3 : Journal décisions
DECISION_JOURNAL = []

# TABLE 12 : Historique signaux
SIGNAL_TABLE = []

# ======================
# ÉTAT GLOBAL
# ======================
sto_state = {
    "mode": MODE_DECISION,
    "capital": CAPITAL_SIMULE,
    "daily_count": 0,
    "last_reset": time.strftime("%Y-%m-%d"),
    "start_time": time.time()
}

# ======================
# UTILS
# ======================
def reset_daily_counter():
    today = time.strftime("%Y-%m-%d")
    if sto_state["last_reset"] != today:
        sto_state["daily_count"] = 0
        sto_state["last_reset"] = today

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
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

def calculate_ema(prices, period=10):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = (p * k) + (ema * (1 - k))
    return round(ema, 2)

# ======================
# ROUTES
# ======================

@app.route("/")
def home():
    return jsonify({
        "statut": "STO STABLE – MODE OFFLINE",
        "mode": sto_state["mode"],
        "temps_en_ligne": int(time.time() - sto_state["start_time"])
    })

@app.route("/simulate", methods=["GET"])
def simulate():
    reset_daily_counter()

    if sto_state["daily_count"] >= SEUIL_JOURNALIER:
        return jsonify({
            "signal": "BLOQUÉ",
            "raison": "Seuil journalier atteint",
            "mode": sto_state["mode"]
        })

    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées"
        })

    rsi = calculate_rsi(prices)
    ema_fast = calculate_ema(prices, 10)
    ema_slow = calculate_ema(prices, 20)

    signal = "ATTENTE"
    raison = "Marché neutre"

    if rsi and ema_fast and ema_slow:
        if rsi > 60 and ema_fast > ema_slow:
            signal = "ACHAT"
            raison = "RSI + EMA haussiers"
        elif rsi < 40 and ema_fast < ema_slow:
            signal = "VENTE"
            raison = "RSI + EMA baissiers"

    sto_state["daily_count"] += 1

    record = {
        "id": str(uuid.uuid4()),
        "mode": sto_state["mode"],
        "signal": signal,
        "reason": raison,
        "timestamp": int(time.time())
    }

    DECISION_JOURNAL.append(record)
    SIGNAL_TABLE.append({
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "signal": signal,
        "timestamp": record["timestamp"]
    })

    return jsonify({
        "signal": signal,
        "raison": raison,
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "decisions_jour": sto_state["daily_count"]
    })

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(DECISION_JOURNAL[-20:])

@app.route("/signals", methods=["GET"])
def signals():
    return jsonify(SIGNAL_TABLE[-20:])

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
