from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# ======================
# CONFIGURATION STO
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INCONNU",
    "last_action": "ATTENTE",
    "reason": "STO démarre",
    "start_time": time.time()
}

# ======================
# PAGE D'ACCUEIL
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# STATUT DU MARCHÉ (BINANCE)
# ======================
import requests

@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        # 1️⃣ Prix actuel
        price_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        price_resp = requests.get(price_url, timeout=5)
        price_data = price_resp.json()
        last_price = float(price_data["price"])

        # 2️⃣ Variation 24h
        stats_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        stats_resp = requests.get(stats_url, timeout=5)
        stats_data = stats_resp.json()
        variation_24h = float(stats_data["priceChangePercent"])

        # 3️⃣ Détermination de la tendance
        if variation_24h > 1:
            tendance = "HAUSSIÈRE"
            action = "SURVEILLANCE_ACTIVE"
            raison = "Tendance haussière sur 24h"
        elif variation_24h < -1:
            tendance = "BAISSIÈRE"
            action = "ATTENTE"
            raison = "Tendance baissière sur 24h"
        else:
            tendance = "LATÉRALE"
            action = "OBSERVATION"
            raison = "Marché stable"

        # 4️⃣ Mise à jour état STO
        sto_state["market_status"] = tendance
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": tendance,
            "prix_actuel": last_price,
            "variation_24h_pourcent": variation_24h,
            "action_STO": action,
            "raison": raison
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": 0,
            "action_STO": "ATTENTE",
            "raison": str(e)
        }), 500

# ======================
# ACTION DU ROBOT
# ======================
@app.route("/bot/action", methods=["GET"])
def bot_action():
    return jsonify({
        "action": sto_state["last_action"],
        "raison": sto_state["reason"],
        "mode": sto_state["mode"]
    })

# ======================
# AUTHENTIFICATION (BASE)
# ======================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    email = data.get("email")

    if email == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})

    return jsonify({"acces": "utilisateur"})

# ======================
# LANCEMENT
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
