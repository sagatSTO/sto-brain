from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

ADMIN_EMAIL = "saguiorelio32@gmail.com"

sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INIT",
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

def get_price_binance():
    url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    data = r.json()
    return float(data["lastPrice"]), float(data["openPrice"])

def get_price_coingecko():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return float(data["bitcoin"]["usd"])

@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        # 1️⃣ SOURCE PRINCIPALE : BINANCE
        try:
            price, open_price = get_price_binance()
            source = "BINANCE"
            if price > open_price * 1.005:
                tendance = "HAUSSE"
                action = "SURVEILLANCE"
                raison = "Prix BTC au-dessus du prix 24h"
            elif price < open_price * 0.995:
                tendance = "BAISSE"
                action = "ATTENTE"
                raison = "Prix BTC en dessous du prix 24h"
            else:
                tendance = "STABLE"
                action = "ATTENTE"
                raison = "Marché stable"

        # 2️⃣ FALLBACK : COINGECKO
        except Exception:
            price = get_price_coingecko()
            source = "COINGECKO"
            tendance = "INCONNUE"
            action = "OBSERVATION"
            raison = "Prix récupéré via fallback CoinGecko"

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
            "action_STO": "ATTENTE",
            "raison": "Aucune source marché disponible"
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
    if data.get("email") == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
