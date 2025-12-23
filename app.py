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
        # 1️⃣ PRIX ACTUEL (endpoint SIMPLE et fiable)
        price_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        price_resp = requests.get(price_url, timeout=5)
        price_data = price_resp.json()
        last_price = float(price_data["price"])

        # 2️⃣ TENDANCE (bougies 1h – 20 dernières)
        kline_url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "limit": 20
        }
        kline_resp = requests.get(kline_url, params=params, timeout=5)
        klines = kline_resp.json()

        # Extraction des prix de clôture
        closes = [float(k[4]) for k in klines]

        # Calcul tendance simple
        moyenne_debut = sum(closes[:10]) / 10
        moyenne_fin = sum(closes[-10:]) / 10

        if moyenne_fin > moyenne_debut:
            tendance = "HAUSSIÈRE"
            action = "OBSERVATION"
            raison = "Tendance haussière détectée"
        elif moyenne_fin < moyenne_debut:
            tendance = "BAISSIÈRE"
            action = "ATTENTE"
            raison = "Tendance baissière détectée"
        else:
            tendance = "LATÉRALE"
            action = "ATTENTE"
            raison = "Marché sans direction claire"

        # Mise à jour état STO
        sto_state["market_status"] = tendance
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": tendance,
            "prix_actuel": round(last_price, 2),
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
