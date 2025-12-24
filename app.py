from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# ======================
# CONFIGURATION ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# CONFIGURATION MODE
# A = PASSIF SÉCURISÉ
# ======================
MODE_DECISION = "A"  # A uniquement pour l’instant

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OBSERVATION",
    "mode_decision": MODE_DECISION,
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
        "mode_decision": sto_state["mode_decision"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# FONCTION PRIX BTC (ROBUSTE)
# ======================
def get_btc_price():
    # Source principale : CoinGecko
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            price = data.get("bitcoin", {}).get("usd")
            if isinstance(price, (int, float)):
                return price, "COINGECKO"
    except:
        pass

    # Fallback : Binance
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            price = float(data.get("price"))
            return price, "BINANCE"
    except:
        pass

    return None, None

# ======================
# MARCHÉ : PRIX + LOGIQUE MODE A
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    price, source = get_btc_price()

    if price is None:
        sto_state["market_status"] = "ERREUR"
        sto_state["last_action"] = "ATTENTE"
        sto_state["reason"] = "Aucune source marché disponible"

        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": 0,
            "action_STO": "ATTENTE",
            "mode_decision": MODE_DECISION,
            "raison": "Aucune source marché disponible"
        }), 500

    # ----- MODE A : PASSIF -----
    sto_state["market_status"] = "OK"
    sto_state["last_action"] = "OBSERVATION"
    sto_state["reason"] = "Mode A actif : observation uniquement"
    sto_state["last_price"] = price

    return jsonify({
        "statut_marche": "OK",
        "source": source,
        "prix_actuel": round(price, 2),
        "action_STO": "OBSERVATION",
        "mode_decision": MODE_DECISION,
        "tendance": "NON ANALYSÉE (MODE A)",
        "raison": sto_state["reason"]
    })

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
# AUTHENTIFICATION
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
