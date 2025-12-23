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
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        r = requests.get(url, timeout=5)
        data = r.json()

        last_price = float(data.get("price", 0.0))

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = "OBSERVATION"
        sto_state["reason"] = "Connexion Binance fonctionnelle"

        return jsonify({
            "statut_marche": "OK",
            "prix_actuel": last_price,
            "action_STO": "OBSERVATION",
            "raison": "Connexion Binance fonctionnelle"
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": 0.0,
            "action_STO": "ATTENTE",
            "raison": str(e)
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
