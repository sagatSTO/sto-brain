from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# PARAMÈTRES STO
# ======================
MODE_DECISION = "C"  # C = HYBRIDE PRO (semi-actif)
MAX_RISK_PERCENT = 0.01  # 1 % du capital

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "SEMI-ACTIF",
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "Initialisation",
    "start_time": time.time()
}

# ======================
# OUTILS INDICATEURS
# ======================
def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

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
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# MARCHÉ : PRIX + RSI + EMA
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {"vs_currency": "usd", "days": 1}
        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            raise Exception("Marché indisponible")

        data = r.json()
        prices = [p[1] for p in data["prices"]]

        if len(prices) < 30:
            raise Exception("Données insuffisantes")

        last_price = round(prices[-1], 2)
        ema_9 = round(calculate_ema(prices[-50:], 9), 2)
        ema_21 = round(calculate_ema(prices[-50:], 21), 2)
        rsi = calculate_rsi(prices[-50:])

        # ======================
        # LOGIQUE SEMI-ACTIVE
        # ======================
        action = "ATTENTE"
        reason = "Conditions neutres"
        tendance = "STABLE"

        if ema_9 > ema_21 and rsi < 65:
            action = "SURVEILLANCE_ACHAT"
            tendance = "HAUSSIÈRE"
            reason = "EMA haussière + RSI sain"
        elif ema_9 < ema_21 and rsi > 35:
            action = "SURVEILLANCE_VENTE"
            tendance = "BAISSIÈRE"
            reason = "EMA baissière + RSI sain"

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = action
        sto_state["reason"] = reason

        return jsonify({
            "statut_marche": "OK",
            "source": "COINGECKO",
            "mode_decision": MODE_DECISION,
            "prix_actuel": last_price,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "rsi": rsi,
            "tendance": tendance,
            "action_STO": action,
            "risque_max_capital": f"{int(MAX_RISK_PERCENT*100)} %",
            "raison": reason
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "mode_decision": MODE_DECISION,
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
        "mode": sto_state["mode"]
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
