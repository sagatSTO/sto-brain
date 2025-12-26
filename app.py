from flask import Flask, jsonify, request
import time
import uuid
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# ÉTAT GLOBAL STO
# ======================
sto_state = {
    "mode_decision": "C",          # A = conservateur, B = équilibré, C = semi-actif
    "mode_execution": "SEMI_ACTIF",
    "capital_simule": 10000,
    "risk_per_trade": 0.01,        # 1%
    "start_time": time.time()
}

# ======================
# JOURNAL DES DÉCISIONS
# ======================
decision_journal = []

# ======================
# INDICATEURS LOCAUX
# ======================
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = mean(gains[-period:])
    avg_loss = mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calculate_ema(prices, period=10):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)

# ======================
# LOGIQUE DE DÉCISION
# ======================
def decision_engine(prices):
    rsi = calculate_rsi(prices)
    ema_short = calculate_ema(prices, 10)
    ema_long = calculate_ema(prices, 20)

    if rsi is None or ema_short is None or ema_long is None:
        return "ATTENTE", "Pas assez de données"

    signal = "NEUTRE"
    if rsi > 60 and ema_short > ema_long:
        signal = "ACHAT"
    elif rsi < 40 and ema_short < ema_long:
        signal = "VENTE"

    # Confirmation (anti-bruit)
    if sto_state["mode_decision"] == "A" and signal != "ACHAT":
        signal = "ATTENTE"
    elif sto_state["mode_decision"] == "B" and signal == "VENTE":
        signal = "ATTENTE"

    return signal, f"RSI={rsi}, EMA10={ema_short}, EMA20={ema_long}"

# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return jsonify({
        "statut": "STO OPÉRATIONNEL",
        "mode_decision": sto_state["mode_decision"],
        "mode_execution": sto_state["mode_execution"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    signal, reason = decision_engine(prices)

    decision = {
        "id": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "signal": signal,
        "reason": reason,
        "mode": sto_state["mode_decision"]
    }

    decision_journal.append(decision)

    return jsonify({
        "statut": "OK",
        "signal": signal,
        "raison": reason,
        "journal_size": len(decision_journal)
    })

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(decision_journal[-50:])  # 50 dernières décisions

@app.route("/config/mode/<mode>", methods=["POST"])
def set_mode(mode):
    if mode not in ["A", "B", "C"]:
        return jsonify({"erreur": "mode invalide"}), 400
    sto_state["mode_decision"] = mode
    return jsonify({"mode_decision": mode})

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
