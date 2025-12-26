from flask import Flask, jsonify, request
import time
import uuid
from statistics import mean

app = Flask(__name__)

# =========================
# CONFIGURATION GLOBALE
# =========================
MODE_DECISION = "C"  # C = Hybride Pro
SEUIL_MIN_DONNEES = 20  # seuil journal minimum
CAPITAL_SIMULE = 1000

# =========================
# ÉTAT GLOBAL STO
# =========================
sto_state = {
    "mode": MODE_DECISION,
    "capital": CAPITAL_SIMULE,
    "positions": [],
    "journal": [],
    "price_buffer": [],
    "last_signal": "ATTENTE",
}

# =========================
# OUTILS INDICATEURS
# =========================
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = mean(gains[-period:])
    avg_loss = mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)

# =========================
# SIMULATION / INJECTION
# =========================
@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    try:
        prices = [float(p) for p in raw.split(",") if p.strip()]
        sto_state["price_buffer"] = prices

        if len(prices) < SEUIL_MIN_DONNEES:
            message = f"Pas assez de données ({len(prices)}/{SEUIL_MIN_DONNEES}) – seuil journal non atteint"
            sto_state["last_signal"] = "ATTENTE"
            return jsonify({
                "signal": "ATTENTE",
                "mode": MODE_DECISION,
                "raison": message,
                "statut": "STO STABLE – MODE OFFLINE"
            })

        # =========================
        # ANALYSE
        # =========================
        rsi = calculate_rsi(prices)
        ema_fast = calculate_ema(prices, 9)
        ema_slow = calculate_ema(prices, 21)

        signal = "ATTENTE"
        raison = "Conditions non réunies"

        if rsi and ema_fast and ema_slow:
            if rsi < 30 and ema_fast > ema_slow:
                signal = "ACHAT"
                raison = "RSI bas + EMA haussière confirmée"
            elif rsi > 70:
                signal = "VENTE"
                raison = "RSI élevé – prise de profit"

        decision = {
            "id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "mode": MODE_DECISION,
            "signal": signal,
            "reason": raison,
            "rsi": rsi,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow
        }

        sto_state["journal"].append(decision)
        sto_state["last_signal"] = signal

        return jsonify(decision)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# =========================
# JOURNAL DES DÉCISIONS
# =========================
@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(sto_state["journal"][-50:])

# =========================
# ÉTAT STO
# =========================
@app.route("/", methods=["GET"])
def status():
    return jsonify({
        "mode": MODE_DECISION,
        "capital": sto_state["capital"],
        "last_signal": sto_state["last_signal"],
        "points_donnees": len(sto_state["price_buffer"]),
        "seuil_requis": SEUIL_MIN_DONNEES
    })

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
