from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# ÉTAT STO (mémoire)
# ======================
sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "STO démarre",
    "start_time": time.time(),
    "last_price": None
}

# ======================
# PAGE PRINCIPALE
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "uptime_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# OUTILS MARCHÉ
# ======================
def get_price_binance():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    r = requests.get(url, timeout=5)
    if r.status_code == 200:
        return float(r.json()["price"])
    return None

def get_price_coingecko():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        return float(r.json()["bitcoin"]["usd"])
    return None

def get_price_24h_ago():
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": 1}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        prices = r.json().get("prices", [])
        if prices:
            return float(prices[0][1])
    return None

# ======================
# MARCHÉ : PRIX + TENDANCE (HYBRIDE PRO)
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        source = None
        price = None

        # 1️⃣ Binance
        price = get_price_binance()
        if price:
            source = "BINANCE"

        # 2️⃣ CoinGecko fallback
        if not price:
            price = get_price_coingecko()
            if price:
                source = "COINGECKO"

        # 3️⃣ Dernier prix mémorisé
        if not price and sto_state["last_price"]:
            price = sto_state["last_price"]
            source = "CACHE"

        if not price:
            raise Exception("Aucune source de prix disponible")

        sto_state["last_price"] = price

        # ---- TENDANCE ----
        price_24h_ago = get_price_24h_ago()
        tendance = "INCONNUE"

        if price_24h_ago:
            variation = (price - price_24h_ago) / price_24h_ago * 100

            if variation > 0.5:
                tendance = "HAUSSE"
                action = "SURVEILLANCE"
                raison = "Tendance haussière 24h"
            elif variation < -0.5:
                tendance = "BAISSE"
                action = "ATTENTE"
                raison = "Tendance baissière 24h"
            else:
                tendance = "STABLE"
                action = "ATTENTE"
                raison = "Marché stable"
        else:
            action = "OBSERVATION"
            raison = "Prix OK, tendance indisponible"

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": "OK",
            "source": source,
            "prix_actuel": round(price, 2),
            "tendance": tendance,
            "action_STO": action,
            "raison": raison
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": sto_state.get("last_price", 0),
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
