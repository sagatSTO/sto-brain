from flask import Flask, request, jsonify
import time
import uuid
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG GLOBALE STO
# ======================
STO_MODE = "C"  # A / B / C
MIN_DATA_POINTS = 20
DAILY_SIGNAL_THRESHOLD = 1  # nb min de signaux valides par jour

# ======================
# ÉTAT GLOBAL
# ======================
sto_state = {
    "mode": STO_MODE,
    "daily_signals": 0,
    "last_reset": int(time.time()),
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
    for p in prices[1:]:
        ema = (p * k) + (ema * (1 - k))
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# PAGE PRINCIPALE
# ======================
@app.route("/")
def home():
    return jsonify({
        "statut": "STO STABLE – MODE OFFLINE",
        "mode": sto_state["mode"],
        "journal_entries": len(sto_state["journal"])
    })

# ======================
# SIMULATION / DÉCISION
# ======================
@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    try:
        prices = [float(x) for x in raw.split(",") if x.strip()]
        uid = str(uuid.uuid4())
        timestamp = int(time.time())

        # Reset journalier (24h)
        if timestamp - sto_state["last_reset"] > 86400:
            sto_state["daily_signals"] = 0
            sto_state["last_reset"] = timestamp

        # Vérification données
        if len(prices) < MIN_DATA_POINTS:
            reason = f"Pas assez de données ({len(prices)}/{MIN_DATA_POINTS})"
            decision = {
                "id": uid,
                "mode": STO_MODE,
                "signal": "ATTENTE",
                "reason": reason,
                "timestamp": timestamp
            }
            sto_state["journal"].append(decision)
            return jsonify(decision)

        # Indicateurs
        rsi = calculate_rsi(prices)
        ema_fast = calculate_ema(prices, 10)
        ema_slow = calculate_ema(prices, 20)

        # Logique décisionnelle
        signal = "ATTENTE"
        reason = "Conditions non remplies"

        if rsi and ema_fast and ema_slow:
            if rsi > 55 and ema_fast > ema_slow:
                if sto_state["daily_signals"] < DAILY_SIGNAL_THRESHOLD:
                    signal = "ACHAT"
                    reason = "RSI + EMA validés (seuil journalier OK)"
                    sto_state["daily_signals"] += 1
                else:
                    reason = "Seuil journalier atteint"
            else:
                reason = "RSI / EMA non alignés"

        decision = {
            "id": uid,
            "mode": STO_MODE,
            "signal": signal,
            "rsi": rsi,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "daily_signals": sto_state["daily_signals"],
            "reason": reason,
            "timestamp": timestamp
        }

        sto_state["journal"].append(decision)
        return jsonify(decision)

    except Exception as e:
        return jsonify({
            "signal": "ERREUR",
            "reason": str(e)
        }), 500

# ======================
# JOURNAL
# ======================
@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(sto_state["journal"][-20:])

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
