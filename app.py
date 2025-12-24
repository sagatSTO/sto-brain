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
    "mode_decision": "C",  # HYBRIDE PRO
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "Initialisation STO",
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
        "mode_decision": sto_state["mode_decision"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

# ======================
# OUTILS MARCHÉ
# ======================
def get_btc_price():
    """Source unique fiable : CoinGecko simple price"""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return float(data["bitcoin"]["usd"])

def get_btc_24h_price():
    """Prix BTC il y a 24h pour tendance"""
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": 1}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    prices = r.json().get("prices", [])
    return float(prices[0][1]) if prices else None

# ======================
# STATUT MARCHÉ
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        price_now = get_btc_price()
        price_24h = get_btc_24h_price()

        if price_24h is None:
            raise Exception("Historique insuffisant")

        delta = (price_now - price_24h) / price_24h * 100

        # === LOGIQUE HYBRIDE PRO ===
        if delta > 1.2:
            tendance = "HAUSSE"
            action = "SURVEILLANCE_ACTIVE"
            raison = "Avantage haussier détecté"
        elif delta < -1.2:
            tendance = "BAISSE"
            action = "ATTENTE"
            raison = "Risque baissier détecté"
        else:
            tendance = "STABLE"
            action = "ATTENTE"
            raison = "Marché sans avantage clair"

        sto_state["market_status"] = "OK"
        sto_state["last_action"] = action
        sto_state["reason"] = raison

        return jsonify({
            "statut_marche": "OK",
            "source": "COINGECKO",
            "mode_decision": "C",
            "prix_actuel": round(price_now, 2),
            "prix_24h_ago": round(price_24h, 2),
            "variation_24h_pct": round(delta, 2),
            "tendance": tendance,
            "action_STO": action,
            "raison": raison
        })

    except Exception as e:
        # SÉCURITÉ ABSOLUE → retour mode A
        sto_state["market_status"] = "ERREUR"
        sto_state["last_action"] = "ATTENTE"
        sto_state["reason"] = "Marché indisponible → sécurité"

        return jsonify({
            "statut_marche": "ERREUR",
            "mode_decision": "A",
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
        "mode": sto_state["mode"],
        "mode_decision": sto_state["mode_decision"]
    })

# ======================
# AUTH
# ======================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    if data.get("email") == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
