from flask import Flask, request, jsonify
import time
import math

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

sto_state = {
    "mode": "OFFLINE",
    "mode_decision": "C",  # A=conservateur B=semi C=agressif
    "capital_simule": 1000,
    "last_action": "ATTENTE",
    "reason": "STO initialisé",
    "start_time": time.time()
}

journal = []  # journal des décisions

# ======================
# INDICATEURS
# ======================
def ema(prices, period):
    if len(prices) < 2:
        return None
    k = 2 / (period + 1)
    ema_val = prices[0]
    for p in prices[1:]:
        ema_val = p * k + ema_val * (1 - k)
    return round(ema_val, 2)

def rsi(prices, period):
    if len(prices) < 2:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains[-period:]) / max(1, period)
    avg_loss = sum(losses[-period:]) / max(1, period)
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
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "mode_decision": sto_state["mode_decision"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

@app.route("/simulate")
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 5:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées (min 5)"
        }), 400

    period_rsi = min(14, len(prices) - 1)
    period_ema_short = min(5, len(prices))
    period_ema_long = min(10, len(prices))

    rsi_val = rsi(prices, period_rsi)
    ema_s = ema(prices, period_ema_short)
    ema_l = ema(prices, period_ema_long)

    tendance = "STABLE"
    action = "ATTENTE"

    if rsi_val is not None:
        if rsi_val > 65:
            tendance = "HAUSSE"
            action = "ACHAT"
        elif rsi_val < 35:
            tendance = "BAISSE"
            action = "VENTE"

    decision = {
        "prix_actuel": prices[-1],
        "RSI": rsi_val,
        "EMA_courte": ema_s,
        "EMA_longue": ema_l,
        "tendance": tendance,
        "action_STO": action,
        "mode_decision": sto_state["mode_decision"],
        "statut_marche": "OK"
    }

    journal.append({
        "timestamp": int(time.time()),
        "decision": decision
    })

    return jsonify(decision)

@app.route("/journal")
def get_journal():
    return jsonify({
        "total": len(journal),
        "entries": journal[-20:]
    })

@app.route("/backtest")
def backtest():
    gains = 0
    for entry in journal:
        if entry["decision"]["action_STO"] == "ACHAT":
            gains += 1
        elif entry["decision"]["action_STO"] == "VENTE":
            gains -= 1
    return jsonify({
        "capital_initial": sto_state["capital_simule"],
        "score_decisions": gains,
        "statut": "BACKTEST OK"
    })

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
