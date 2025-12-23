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
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        r = requests.get(url, timeout=5)
        data = r.json()

        prix_actuel = float(data["price"])

        # Récupération du dernier prix connu
        prix_precedent = sto_state.get("last_price")

        # Détermination de la tendance
        if prix_precedent is None:
            tendance = "INCONNUE"
            action = "OBSERVATION"
            raison = "Première mesure du marché"
        elif prix_actuel > prix_precedent:
            tendance = "HAUSSE"
            action = "SURVEILLANCE"
            raison = "Le prix augmente"
        elif prix_actuel < prix_precedent:
            tendance = "BAISSE"
            action = "ATTENTE"
            raison = "Le prix baisse"
        else:
            tendance = "NEUTRE"
            action = "OBSERVATION"
            raison = "Prix stable"

        # Mise à jour de l'état STO
        sto_state["last_price"] = prix_actuel
        sto_state["market_status"] = tendance
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": tendance,
            "prix_actuel": prix_actuel,
            "action_STO": action,
            "raison": raison
        })

    except Exception as e:
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
