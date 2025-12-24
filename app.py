from flask import Flask, request, jsonify
import time
import requests
from collections import deque

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# MÉMOIRE STO (MODE C)
# ======================
PRICE_MEMORY = deque(maxlen=20)   # mémoire des 20 derniers prix
LAST_API_CALL = 0
API_COOLDOWN = 60  # secondes entre appels externes

sto_state = {
    "mode": "OBSERVATION",
    "decision_mode": "C",  # MODE HYBRIDE PRO
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "Première observation",
    "start_time": time.time()
}

# ======================
# PAGE PRINCIPALE
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "mode_decision": sto_state["decision_mode"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

# ======================
# MARCHÉ : PRIX + TENDANCE (MODE C)
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        import math

        # ======================
        # RÉCUPÉRATION HISTORIQUE
        # ======================
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            "vs_currency": "usd",
            "days": 1
        }
        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            raise Exception(f"Erreur marché: {r.status_code}")

        data = r.json()
        prices = [p[1] for p in data.get("prices", [])]

        if len(prices) < 30:
            raise Exception("Données insuffisantes pour indicateurs")

        current_price = prices[-1]

        # ======================
        # CALCUL EMA
        # ======================
        def ema(prices, period):
            k = 2 / (period + 1)
            ema_val = prices[0]
            for price in prices[1:]:
                ema_val = price * k + ema_val * (1 - k)
            return ema_val

        ema12 = ema(prices[-26:], 12)
        ema26 = ema(prices[-26:], 26)

        # ======================
        # CALCUL RSI
        # ======================
        def rsi(prices, period=14):
            gains = []
            losses = []

            for i in range(1, period + 1):
                diff = prices[-i] - prices[-i - 1]
                if diff >= 0:
                    gains.append(diff)
                else:
                    losses.append(abs(diff))

            avg_gain = sum(gains) / period if gains else 0
            avg_loss = sum(losses) / period if losses else 1

            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))

        rsi_val = rsi(prices)

        # ======================
        # INTERPRÉTATION STO (MODE C)
        # ======================
        if rsi_val > 70 and ema12 < ema26:
            tendance = "SURACHETÉ"
            action = "ATTENTE"
            raison = "RSI élevé, possible correction"
        elif rsi_val < 30 and ema12 > ema26:
            tendance = "SURVENDU"
            action = "OBSERVATION"
            raison = "RSI bas, possible opportunité"
        elif ema12 > ema26:
            tendance = "HAUSSE"
            action = "OBSERVATION"
            raison = "Tendance haussière confirmée"
        elif ema12 < ema26:
            tendance = "BAISSE"
            action = "ATTENTE"
            raison = "Tendance baissière"
        else:
            tendance = "NEUTRE"
            action = "ATTENTE"
            raison = "Marché indécis"

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": "OK",
            "source": "COINGECKO",
            "mode_decision": "C",
            "prix_actuel": round(current_price, 2),
            "ema12": round(ema12, 2),
            "ema26": round(ema26, 2),
            "rsi": round(rsi_val, 2),
            "tendance": tendance,
            "action_STO": action,
            "raison": raison
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "mode_decision": "C",
            "prix_actuel": 0,
            "action_STO": "ATTENTE",
            "raison": str(e)
        }), 500

# ======================
# ACTION STO
# ======================
@app.route("/bot/action", methods=["GET"])
def bot_action():
    return jsonify({
        "action": sto_state["last_action"],
        "raison": sto_state["reason"],
        "mode": sto_state["mode"],
        "mode_decision": sto_state["decision_mode"]
    })

# ======================
# AUTH
# ======================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    email = data.get("email")
    if email == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
