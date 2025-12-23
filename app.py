from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# =========================
# CONFIG ADMIN STO
# =========================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INCONNU",
    "last_action": "ATTENTE",
    "reason": "STO démarre",
    "start_time": time.time()
}

# =========================
# PAGE RACINE
# =========================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# =========================
# PRIX + TENDANCE (COINGECKO)
# =========================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        # Prix actuel
        price_url = (
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin&vs_currencies=usd"
        )
        price_resp = requests.get(price_url, timeout=10).json()
        current_price = float(price_resp["bitcoin"]["usd"])

        # Prix il y a 1 heure
        history_url = (
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            "?vs_currency=usd&days=1&interval=hourly"
        )
        history_resp = requests.get(history_url, timeout=10).json()
        prices = history_resp["prices"]

        price_1h_ago = float(prices[-2][1])

        # Calcul tendance
        if current_price > price_1h_ago:
            trend = "HAUSSIÈRE"
            action = "SURVEILLANCE"
            reason = "Prix supérieur à il y a 1 heure"
        elif current_price < price_1h_ago:
            trend = "BAISSIÈRE"
            action = "ATTENTE"
            reason = "Prix inférieur à il y a 1 heure"
        else:
            trend = "NEUTRE"
            action = "ATTENTE"
            reason = "Prix stable"

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = action
        sto_state["reason"] = reason

        return jsonify({
            "statut_marche": "OK",
            "source": "COINGECKO",
            "prix_actuel": round(current_price, 2),
            "prix_1h_ago": round(price_1h_ago, 2),
            "tendance": trend,
            "action_STO": action,
            "raison": reason
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "action_STO": "ATTENTE",
            "prix_actuel": 0,
            "raison": str(e)
        }), 500

# =========================
# ACTION STO
# =========================
@app.route("/bot/action", methods=["GET"])
def bot_action():
    return jsonify({
        "action": sto_state["last_action"],
        "raison": sto_state["reason"],
        "mode": sto_state["mode"]
    })

# =========================
# AUTH ADMIN
# =========================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    email = data.get("email")
    if email == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

# =========================
# LANCEMENT
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
