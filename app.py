from flask import Flask, jsonify, request
import time
import random

app = Flask(__name__)

# ======================
# CONFIG STO
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# ÉTAT GLOBAL STO
# ======================
sto_state = {
    "mode_decision": "C",            # A = conservateur, B = normal, C = agressif
    "profil_risque": "AGRESSIF",     # CONSERVATEUR / NORMAL / AGRESSIF
    "capital_simule": 1000.0,
    "risque_par_trade": 0.02,        # 2 %
    "position_size": 0.0,
    "rsi": None,
    "ema": None,
    "tendance": "INCONNUE",
    "action": "ATTENTE",
    "raison": "Initialisation STO",
    "journal": [],
    "start_time": time.time()
}

# ======================
# OUTILS OFFLINE
# ======================
def simulate_rsi():
    return round(random.uniform(20, 80), 2)

def simulate_ema():
    return round(random.uniform(85000, 90000), 2)

def calcul_position_size():
    return round(
        sto_state["capital_simule"] * sto_state["risque_par_trade"], 2
    )

def log_decision():
    sto_state["journal"].append({
        "timestamp": int(time.time()),
        "mode": sto_state["mode_decision"],
        "rsi": sto_state["rsi"],
        "ema": sto_state["ema"],
        "action": sto_state["action"],
        "raison": sto_state["raison"]
    })

# ======================
# LOGIQUE DÉCISIONNELLE
# ======================
def decision_engine():
    sto_state["rsi"] = simulate_rsi()
    sto_state["ema"] = simulate_ema()
    sto_state["position_size"] = calcul_position_size()

    rsi = sto_state["rsi"]

    if sto_state["mode_decision"] == "A":  # Conservateur
        if rsi < 30:
            sto_state["action"] = "SURVEILLANCE"
            sto_state["raison"] = "RSI bas – prudence"
        else:
            sto_state["action"] = "ATTENTE"
            sto_state["raison"] = "Aucune condition sûre"

    elif sto_state["mode_decision"] == "B":  # Normal
        if rsi < 35:
            sto_state["action"] = "ENTREE_POTENTIELLE"
            sto_state["raison"] = "RSI favorable"
        else:
            sto_state["action"] = "ATTENTE"
            sto_state["raison"] = "Signal insuffisant"

    elif sto_state["mode_decision"] == "C":  # Agressif
        if rsi < 40:
            sto_state["action"] = "ENTREE_SIMULEE"
            sto_state["raison"] = "RSI opportunité agressive"
        else:
            sto_state["action"] = "ATTENTE"
            sto_state["raison"] = "Marché neutre"

    log_decision()

# ======================
# ROUTES API
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO STABLE – MODE OFFLINE",
        "uptime_sec": int(time.time() - sto_state["start_time"]),
        "mode_decision": sto_state["mode_decision"],
        "profil_risque": sto_state["profil_risque"]
    })

@app.route("/test/decision", methods=["GET"])
def test_decision():
    decision_engine()
    return jsonify({
        "action_STO": sto_state["action"],
        "mode_decision": sto_state["mode_decision"],
        "rsi": sto_state["rsi"],
        "ema": sto_state["ema"],
        "position_size": sto_state["position_size"],
        "capital_simule": sto_state["capital_simule"],
        "raison": sto_state["raison"],
        "statut": "TEST OK"
    })

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(sto_state["journal"][-10:])

@app.route("/config/mode", methods=["POST"])
def set_mode():
    data = request.json or {}
    mode = data.get("mode")
    if mode in ["A", "B", "C"]:
        sto_state["mode_decision"] = mode
        return jsonify({"ok": True, "mode_decision": mode})
    return jsonify({"ok": False}), 400

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
