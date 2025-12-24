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
    "last_price": None,
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
# FONCTIONS MARCHÉ
# ======================
def get_price_binance():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    r = requests.get(url, timeout=5)
    data = r.json()
    return float(data["price"])

def get_price_coingecko():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    return float(data["bitcoin"]["usd"])

def get_price_24h_ago():
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1d",
        "limit": 2
    }
    r = requests.get(url, params=params, timeout=5)
    data = r.json()
    return float(data[0][4])  # close price J-1

# ======================
# MARCHÉ : PRIX + TENDANCE
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        source = "BINANCE"
        try:
            price_now = get_price_binance()
        except:
            source = "COINGECKO"
            price_now = get_price_coingecko()

        price_24h_ago = get_price_24h_ago()

        sto_state["last_price"] = price_now

        # --- TENDANCE ---
        if price_now > price_24h_ago * 1.005:
            tendance = "HAUSSE"
            action = "SURVEILLANCE"
            raison = "Tendance haussière confirmée"
        elif price_now < price_24h_ago * 0.995:
            tendance = "BAISSE"
            action = "ATTENTE"
            raison = "Tendance baissière"
        else:
            tendance = "STABLE"
            action = "ATTENTE"
            raison = "Marché stable"

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": "OK",
            "source": source,
            "prix_actuel": round(price_now, 2),
            "prix_24h_ago": round(price_24h_ago, 2),
            "tendance": tendance,
            "action_STO": action,
            "raison": raison
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": sto_state["last_price"] or 0,
            "action_STO": "ATTENTE",
            "raison": f"Erreur marché: {str(e)}"
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
