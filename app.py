from flask import Flask, request, jsonify
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIGURATION STO
# ======================
STO_NAME = "STO"
VERSION = "1.0-OFFLINE"
START_TIME = time.time()

# ======================
# ÉTAT GLOBAL
# ======================
sto_state = {
    "mode": "OFFLINE",
    "decision_mode": "C",  # C = logique hybride pro
    "last_action": "ATTENTE",
    "reason": "STO initialisé",
}

# ======================
# OUTILS INDICATEURS
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
        delta = prices[i] - prices[i-1]
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
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "STO": STO_NAME,
        "version": VERSION,
        "mode": sto_state["mode"],
        "decision_mode": sto_state["decision_mode"],
        "uptime_seconds": int(time.time() - START_TIME),
        "status": "STO STABLE – MODE OFFLINE"
    })

# ======================
# SIMULATION OFFLINE
# ======================
@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    try:
        prices = [float(x) for x in raw.split(",") if x.strip()]
        if len(prices) < 20:
            return jsonify({
                "statut_marche": "ERREUR",
                "raison": "Pas assez de données simulées (>=20 requises)"
            }), 400

        ema_short = calculate_ema(prices, 10)
        ema_long = calculate_ema(prices, 20)
        rsi = calculate_rsi(prices)

        # Décision hybride C
        if rsi and rsi < 35 and ema_short > ema_long:
            action = "ACHAT_SIMULÉ"
            tendance = "HAUSSE_POTENTIELLE"
        elif rsi and rsi > 65 and ema_short < ema_long:
            action = "VENTE_SIMULÉE"
            tendance = "FAIBLESSE_POTENTIELLE"
        else:
            action = "ATTENTE"
            tendance = "STABLE"

        sto_state["last_action"] = action
        sto_state["reason"] = "Décision basée sur RSI + EMA offline"

        return jsonify({
            "statut_marche": "OK",
            "mode": "OFFLINE",
            "prix_final": prices[-1],
            "RSI": rsi,
            "EMA_10": ema_short,
            "EMA_20": ema_long,
            "tendance": tendance,
            "action_STO": action,
            "raison": sto_state["reason"]
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": str(e)
        }), 500

# ======================
# JOURNAL DES DÉCISIONS (VISUEL 1)
# ======================
@app.route("/journal", methods=["GET"])
def journal():
    return jsonify({
        "dernier_mode": sto_state["decision_mode"],
        "derniere_action": sto_state["last_action"],
        "raison": sto_state["reason"],
        "timestamp": int(time.time())
    })

# ======================
# DASHBOARD SYNTHÈSE (VISUEL 2)
# ======================
@app.route("/dashboard", methods=["GET"])
def dashboard():
    return jsonify({
        "STO": STO_NAME,
        "version": VERSION,
        "mode": sto_state["mode"],
        "decision_mode": sto_state["decision_mode"],
        "action_actuelle": sto_state["last_action"],
        "etat": "PRÊT POUR MARCHÉ RÉEL"
    })

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
