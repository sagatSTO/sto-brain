from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# ======================
# CONFIGURATION ADMIN
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# ÉTAT GLOBAL STO
# ======================
sto_state = {
    "mode": "DECISIONNEL_A",        # Mode A : logique pure
    "cycle": 0,                     # Compteur de cycles
    "last_action": "ATTENTE",
    "risk_level": "FAIBLE",
    "confidence": 0.5,              # 0 → 1
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
        "cycle": sto_state["cycle"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

# ======================
# CŒUR DÉCISIONNEL (A)
# ======================
@app.route("/decision/core", methods=["GET"])
def decision_core():
    """
    Cœur décisionnel autonome
    Aucun appel externe
    Simulation de raisonnement trader
    """

    sto_state["cycle"] += 1

    # --- SIMULATION CONTEXTE ---
    if sto_state["cycle"] % 5 == 0:
        contexte = "VOLATIL"
    elif sto_state["cycle"] % 3 == 0:
        contexte = "FAVORABLE"
    else:
        contexte = "NEUTRE"

    # --- LOGIQUE DE RISQUE ---
    if sto_state["confidence"] < 0.4:
        risk = "FAIBLE"
        action = "ATTENTE"
        raison = "Confiance insuffisante"
    elif contexte == "FAVORABLE":
        risk = "MODÉRÉ"
        action = "OBSERVATION_ACTIVE"
        raison = "Conditions simulées favorables"
    elif contexte == "VOLATIL":
        risk = "ÉLEVÉ"
        action = "ATTENTE"
        raison = "Volatilité simulée"
    else:
        risk = "FAIBLE"
        action = "ATTENTE"
        raison = "Aucune opportunité claire"

    # --- AJUSTEMENT CONFIANCE ---
    if action == "OBSERVATION_ACTIVE":
        sto_state["confidence"] = min(1.0, sto_state["confidence"] + 0.05)
    else:
        sto_state["confidence"] = max(0.1, sto_state["confidence"] - 0.02)

    sto_state["last_action"] = action
    sto_state["risk_level"] = risk
    sto_state["reason"] = raison

    return jsonify({
        "mode_decision": "A",
        "cycle": sto_state["cycle"],
        "contexte_simule": contexte,
        "action_STO": action,
        "niveau_risque": risk,
        "confiance": round(sto_state["confidence"], 2),
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
        "mode": sto_state["mode"]
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
