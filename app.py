from flask import Flask, jsonify, request
import time
import math

app = Flask(__name__)

# ======================
# CONFIG ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# CONFIG STO
# ======================
CAPITAL_SIMULE = 1000.0  # capital de test
RISQUE_PAR_TRADE = 0.01  # 1% par trade
MODE_DECISION = "C"      # A = passif, B = semi, C = pro

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OFFLINE",
    "mode_decision": MODE_DECISION,
    "statut": "STO STABLE – MODE OFFLINE",
    "capital": CAPITAL_SIMULE,
    "last_action": "ATTENTE",
    "reason": "Initialisation",
    "start_time": time.time(),
    "journal": []
}

# ======================
# OUTILS TECHNIQUES (OFFLINE)
# ======================
def calcul_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 2)

def calcul_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, pertes = 0, 0
    for i in range(1, period + 1):
        delta = prices[i] - prices[i - 1]
        if delta > 0:
            gains += delta
        else:
            pertes -= delta
    if pertes == 0:
        return 100
    rs = gains / pertes
    return round(100 - (100 / (1 + rs)), 2)

def position_sizing(capital, risque, stop_loss_pct):
    risque_montant = capital * risque
    taille = risque_montant / stop_loss_pct
    return round(taille, 2)

# ======================
# ROUTE PRINCIPALE
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": sto_state["statut"],
        "mode": sto_state["mode"],
        "mode_decision": sto_state["mode_decision"],
        "temps_en_ligne": int(time.time() - sto_state["start_time"])
    })

# ======================
# TEST OFFLINE DU CŒUR
# ======================
@app.route("/test/offline", methods=["GET"])
def test_offline():
    # données simulées
    prices = [100, 101, 102, 103, 102, 101, 104, 106, 107, 108, 109, 110]

    ema_9 = calcul_ema(prices, 9)
    ema_21 = calcul_ema(prices, 21)
    rsi_14 = calcul_rsi(prices)

    tendance = "INCONNUE"
    action = "ATTENTE"

    if ema_9 and ema_21 and rsi_14:
        if ema_9 > ema_21 and rsi_14 < 70:
            tendance = "HAUSSE"
            action = "ENTRER_LONG"
        elif ema_9 < ema_21 and rsi_14 > 30:
            tendance = "BAISSE"
            action = "ATTENTE"

    taille_position = position_sizing(
        sto_state["capital"],
        RISQUE_PAR_TRADE,
        0.02
    )

    decision = {
        "ema_9": ema_9,
        "ema_21": ema_21,
        "rsi": rsi_14,
        "tendance": tendance,
        "action_STO": action,
        "taille_position": taille_position
    }

    sto_state["last_action"] = action
    sto_state["reason"] = "Décision OFFLINE calculée"
    sto_state["journal"].append(decision)

    return jsonify({
        "capital_simule": sto_state["capital"],
        "mode_decision": sto_state["mode_decision"],
        "decision": decision,
        "statut": sto_state["statut"]
    })

# ======================
# JOURNAL
# ======================
@app.route("/journal", methods=["GET"])
def journal():
    return jsonify({
        "nombre_decisions": len(sto_state["journal"]),
        "journal": sto_state["journal"]
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
