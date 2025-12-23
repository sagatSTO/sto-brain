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
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": "BTCUSDT"}

        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()

        # Sécurisation maximale
        price_str = data.get("price")
        if price_str is None:
            raise ValueError("Prix BTC indisponible")

        last_price = float(price_str)

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = "OBSERVATION"
        sto_state["reason"] = "Prix BTC récupéré avec succès"

        return jsonify({
            "statut_marche": "OK",
            "prix_actuel": last_price,
            "action_STO": sto_state["last_action"],
            "raison": sto_state["reason"]
        })

    except Exception as e:
        sto_state["market_status"] = "ERREUR"
        sto_state["last_action"] = "ATTENTE"
        sto_state["reason"] = "Erreur récupération Binance"

        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": 0.0,
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
