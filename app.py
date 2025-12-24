from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# ======================
# CONFIGURATION STO
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"
MODE_DECISION = "C"  # C = Hybride Pro

# ======================
# ÉTAT INTERNE STO
# ======================
sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "Initialisation STO",
    "last_price": None,
    "last_update": 0,
    "start_time": time.time()
}

CACHE_DURATION = 60  # secondes (anti-429)

# ======================
# PAGE PRINCIPALE
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "mode_decision": MODE_DECISION,
        "uptime_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# RÉCUPÉRATION PRIX (ROBUSTE)
# ======================
def fetch_price():
    # 1️⃣ BINANCE
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=5
        )
        data = r.json()
        return float(data["price"]), "BINANCE"
    except:
        pass

    # 2️⃣ COINGECKO SIMPLE
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=5
        )
        data = r.json()
        return float(data["bitcoin"]["usd"]), "COINGECKO"
    except:
        pass

    # 3️⃣ CACHE
    if sto_state["last_price"] is not None:
        return sto_state["last_price"], "CACHE"

    raise Exception("Aucune source marché disponible")

# ======================
# MARCHÉ + TENDANCE
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    try:
        now = time.time()

        # Cache anti-spam
        if now - sto_state["last_update"] < CACHE_DURATION:
            return jsonify({
                "statut_marche": "OK",
                "prix_actuel": sto_state["last_price"],
                "tendance": sto_state["market_status"],
                "action_STO": sto_state["last_action"],
                "raison": "Données en cache",
                "mode_decision": MODE_DECISION,
                "source": "CACHE"
            })

        price, source = fetch_price()

        # Calcul tendance locale
        if sto_state["last_price"] is None:
            tendance = "INCONNUE"
            action = "ATTENTE"
            raison = "Première observation"
        else:
            delta = (price - sto_state["last_price"]) / sto_state["last_price"] * 100

            if delta > 0.5:
                tendance = "HAUSSE"
                action = "SURVEILLANCE"
                raison = "Momentum haussier détecté"
            elif delta < -0.5:
                tendance = "BAISSE"
                action = "ATTENTE"
                raison = "Risque baissier"
            else:
                tendance = "STABLE"
                action = "ATTENTE"
                raison = "Marché neutre"

        # Mise à jour état
        sto_state.update({
            "market_status": tendance,
            "last_action": action,
            "reason": raison,
            "last_price": price,
            "last_update": now
        })

        return jsonify({
            "statut_marche": "OK",
            "prix_actuel": round(price, 2),
            "tendance": tendance,
            "action_STO": action,
            "raison": raison,
            "mode_decision": MODE_DECISION,
            "source": source
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": sto_state["last_price"] or 0,
            "action_STO": "ATTENTE",
            "mode_decision": MODE_DECISION,
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
        "mode_decision": MODE_DECISION
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
