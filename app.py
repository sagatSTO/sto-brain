from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

# =========================
# CONFIGURATION STO
# =========================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "STO démarrage",
    "start_time": time.time()
}

# =========================
# PAGE RACINE
# =========================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# =========================
# DONNÉES MARCHÉ BTC
# =========================
@app.route("/market/status", methods=["GET"])
def market_status():
    price = None
    source = None

    # ---- Tentative 1 : Binance ----
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "price" in data:
                price = float(data["price"])
                source = "BINANCE"
    except Exception:
        pass

    # ---- Tentative 2 : CoinGecko (secours) ----
    if price is None:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true"
                },
                timeout=5
            )
            data = r.json()
            if "bitcoin" in data and "usd" in data["bitcoin"]:
                price = float(data["bitcoin"]["usd"])
                source = "COINGECKO"
        except Exception:
            pass

    # ---- Échec total ----
    if price is None:
        sto_state["market_status"] = "ERREUR"
        sto_state["last_action"] = "ATTENTE"
        sto_state["reason"] = "Aucune source marché disponible"

        return jsonify({
            "statut_marche": "ERREUR",
            "prix_actuel": 0,
            "action_STO": "ATTENTE",
            "raison": "Impossible de récupérer le prix BTC"
        }), 500

    # ---- Tendance simple ----
    tendance = "STABLE"
    if price > 0:
        tendance = "OK"

    sto_state["market_status"] = "OK"
    sto_state["last_action"] = "OBSERVATION"
    sto_state["reason"] = f"Prix BTC depuis {source}"

    return jsonify({
        "statut_marche": "OK",
        "prix_actuel": round(price, 2),
        "tendance": tendance,
        "source": source,
        "action_STO": "OBSERVATION",
        "raison": f"Connexion marché fonctionnelle ({source})"
    })

# =========================
# ACTION STO
# =========================
@app.route("/bot/action", methods=["GET"])
def bot_action():
    return jsonify({
        "action": sto_state["last_action"],
        "raison": sto_state["reason"],
        "mode": sto_state["mode"]
    })

# =========================
# AUTH ADMIN
# =========================
@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json or {}
    email = data.get("email")
    if email == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

# =========================
# LANCEMENT
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
