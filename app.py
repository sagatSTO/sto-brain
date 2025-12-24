from flask import Flask, request, jsonify
import time
import requests
from collections import deque

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# MÉMOIRE STO (MODE C)
# ======================
PRICE_MEMORY = deque(maxlen=20)   # mémoire des 20 derniers prix
LAST_API_CALL = 0
API_COOLDOWN = 60  # secondes entre appels externes

sto_state = {
    "mode": "OBSERVATION",
    "decision_mode": "C",  # MODE HYBRIDE PRO
    "market_status": "INIT",
    "last_action": "ATTENTE",
    "reason": "Première observation",
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
        "mode_decision": sto_state["decision_mode"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

# ======================
# MARCHÉ : PRIX + TENDANCE (MODE C)
# ======================
@app.route("/market/status", methods=["GET"])
def market_status():
    global LAST_API_CALL

    now = time.time()
    prix = None
    source = "MEMOIRE"

    # ---------- APPEL API CONTRÔLÉ ----------
    if now - LAST_API_CALL > API_COOLDOWN:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd"},
                timeout=5
            )
            if r.status_code == 200:
                data = r.json()
                prix = float(data["bitcoin"]["usd"])
                LAST_API_CALL = now
                source = "COINGECKO"
                PRICE_MEMORY.append(prix)
        except:
            pass

    # ---------- FALLBACK MÉMOIRE ----------
    if prix is None:
        if len(PRICE_MEMORY) > 0:
            prix = PRICE_MEMORY[-1]
        else:
            return jsonify({
                "statut_marche": "ERREUR",
                "action_STO": "ATTENTE",
                "mode_decision": "C",
                "raison": "Aucune donnée marché disponible",
                "prix_actuel": 0
            }), 200

    # ---------- CALCUL TENDANCE LOCAL ----------
    tendance = "INCONNUE"
    if len(PRICE_MEMORY) >= 5:
        moyenne_passee = sum(list(PRICE_MEMORY)[:-1]) / (len(PRICE_MEMORY) - 1)
        if prix > moyenne_passee * 1.002:
            tendance = "HAUSSE"
            action = "SURVEILLANCE"
            raison = "Tendance haussière confirmée"
        elif prix < moyenne_passee * 0.998:
            tendance = "BAISSE"
            action = "ATTENTE"
            raison = "Pression baissière détectée"
        else:
            tendance = "STABLE"
            action = "ATTENTE"
            raison = "Marché stable"
    else:
        action = "ATTENTE"
        raison = "Données insuffisantes"

    sto_state["last_action"] = action
    sto_state["reason"] = raison
    sto_state["market_status"] = "OK"

    return jsonify({
        "statut_marche": "OK",
        "source": source,
        "prix_actuel": round(prix, 2),
        "tendance": tendance,
        "action_STO": action,
        "mode_decision": "C",
        "raison": raison
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
        "mode_decision": sto_state["decision_mode"]
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
