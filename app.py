from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# CONFIG MODE STO
# ======================
MODE_DECISION = "A"  # A = Observation Active (SAFE)

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OBSERVATION",
    "mode_decision": MODE_DECISION,
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "STO démarre",
    "start_time": time.time()
}
# ======================
# CACHE PRIX (MODE A)
# ======================
last_known_price = {
    "btc_usd": None,
    "timestamp": None
}
# ======================
# PAGE PRINCIPALE
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "mode_decision": sto_state["mode_decision"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# MARCHÉ : PRIX + TENDANCE (MODE A)
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin",
            "vs_currencies": "usd"
        }

        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            raise Exception("CoinGecko indisponible")

        data = r.json()
        btc_price = data.get("bitcoin", {}).get("usd")

        if btc_price is None:
            raise Exception("Prix BTC absent")

        # MODE A : observation uniquement
        sto_state["market_status"] = "OK"
        sto_state["last_action"] = "OBSERVATION"
        sto_state["reason"] = "Mode A actif : observation sans trading"

        return jsonify({
            "statut_marche": "OK",
            "source": "COINGECKO",
            "mode_decision": "A",
            "prix_actuel": round(btc_price, 2),
            "tendance": "STABLE",
            "action_STO": "OBSERVATION",
            "raison": sto_state["reason"]
        })

    except Exception as e:
    # MODE A : PAS D'ERREUR BLOQUANTE
    return jsonify({
        "statut_marche": "OK",
        "mode_decision": "A",
        "source": "CACHE",
        "prix_actuel": last_known_price["btc_usd"],
        "tendance": "INCONNUE",
        "action_STO": "OBSERVATION",
        "raison": "Marché indisponible, mode sécurité actif"
    }), 500

# ======================
# ACTION STO
# ======================
@app.route("/bot/action", methods=["GET"])
def bot_action():
    return jsonify({
        "mode_decision": sto_state["mode_decision"],
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
