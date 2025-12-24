from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "STO démarre",
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
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# MARCHÉ : PRIX + TENDANCE
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        # --- PRIX ACTUEL ---
        price_url = "https://api.coingecko.com/api/v3/simple/price"
        price_params = {
            "ids": "bitcoin",
            "vs_currencies": "usd"
        }
        price_resp = requests.get(price_url, params=price_params, timeout=10)

        if price_resp.status_code != 200:
            raise Exception("CoinGecko prix indisponible")

        price_data = price_resp.json()
        btc_price = price_data.get("bitcoin", {}).get("usd")

        if btc_price is None:
            raise Exception("Prix BTC absent")

        # --- HISTORIQUE 24H ---
        history_url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        history_params = {
            "vs_currency": "usd",
            "days": 1
        }
        history_resp = requests.get(history_url, params=history_params, timeout=10)

        if history_resp.status_code != 200:
            raise Exception("Historique indisponible")

        history_data = history_resp.json()
        prices = history_data.get("prices", [])

        if len(prices) < 2:
            raise Exception("Données historiques insuffisantes")

        price_24h_ago = prices[0][1]

        # --- CALCUL TENDANCE ---
        if btc_price > price_24h_ago * 1.005:
            tendance = "HAUSSE"
            action = "SURVEILLANCE"
            raison = "Prix en hausse sur 24h"
        elif btc_price < price_24h_ago * 0.995:
            tendance = "BAISSE"
            action = "ATTENTE"
            raison = "Prix en baisse sur 24h"
        else:
            tendance = "STABLE"
            action = "ATTENTE"
            raison = "Marché stable"

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": "OK",
            "source": "COINGECKO",
            "prix_actuel": round(btc_price, 2),
            "prix_24h_ago": round(price_24h_ago, 2),
            "tendance": tendance,
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
