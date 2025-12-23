from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# EMAIL ADMIN STO
ADMIN_EMAIL = "saguiorelio32@gmail.com"

sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INCONNU",
    "last_action": "ATTENTE",
    "reason": "STO démarre",
    "start_time": time.time()
}

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

import requests

@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        r = requests.get(url, timeout=5)
        data = r.json()

        price_change = float(data["priceChangePercent"])
        last_price = float(data["lastPrice"])

        if price_change > 1:
            market_state = "FAVORABLE"
            action = "SURVEILLANCE_ACTIVE"
            reason = "Hausse détectée sur 24h"
        elif price_change < -1:
            market_state = "RISQUE"
            action = "ATTENTE"
            reason = "Baisse détectée sur 24h"
        else:
            market_state = "NEUTRE"
            action = "ATTENTE"
            reason = "Marché stable"

        sto_state["market_status"] = market_state
        sto_state["last_action"] = action
        sto_state["reason"] = reason

        return jsonify({
            "statut_marche": market_state,
            "variation_24h_pourcent": price_change,
            "prix_actuel": last_price,
            "action_STO": action,
            "raison": reason
        })

    except Exception as e:
        return jsonify({
            "erreur": "Impossible de récupérer les données marché",
            "details": str(e)
        }), 500

@app.route("/bot/action", methods=["GET"])
def bot_action():
    return jsonify({
        "action": sto_state["last_action"],
        "raison": sto_state["reason"],
        "mode": sto_state["mode"]
    })

@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    email = data.get("email")
    if email == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
