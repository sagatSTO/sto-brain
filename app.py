from flask import Flask, jsonify
import time
from datetime import datetime

app = Flask(__name__)

# ======================
# CONFIG STO
# ======================
STO_NAME = "STO"
MODE_DECISION = "C"   # A = Offline / B = Semi / C = Hybride
CAPITAL_SIMULE = 1000.0

# ======================
# ÉTAT GLOBAL
# ======================
sto_state = {
    "statut": "STO STABLE – MODE OFFLINE",
    "mode_decision": MODE_DECISION,
    "capital": CAPITAL_SIMULE,
    "tendance": "INCONNUE",
    "action": "ATTENTE",
    "raison": "Initialisation",
    "start_time": time.time()
}

# ======================
# JOURNAL DES DÉCISIONS
# ======================
decision_log = []

def log_decision(action, raison):
    decision_log.append({
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": sto_state["mode_decision"],
        "action": action,
        "raison": raison,
        "capital": round(sto_state["capital"], 2)
    })

# ======================
# PAGE RACINE (SANTÉ STO)
# ======================
@app.route("/")
def home():
    return jsonify({
        "nom": STO_NAME,
        "statut": sto_state["statut"],
        "mode_decision": sto_state["mode_decision"],
        "uptime_secondes": int(time.time() - sto_state["start_time"])
    })

# =====================================================
# VISUEL 1 — DASHBOARD STO
# =====================================================
@app.route("/dashboard")
def dashboard():
    return jsonify({
        "STO": STO_NAME,
        "statut": sto_state["statut"],
        "mode_decision": sto_state["mode_decision"],
        "capital_simule": sto_state["capital"],
        "tendance": sto_state["tendance"],
        "action_actuelle": sto_state["action"],
        "raison": sto_state["raison"]
    })

# =====================================================
# VISUEL 2 — JOURNAL DES DÉCISIONS
# =====================================================
@app.route("/journal")
def journal():
    if not decision_log:
        return jsonify({
            "message": "Aucune décision enregistrée pour le moment",
            "statut": "OK"
        })
    return jsonify({
        "total_decisions": len(decision_log),
        "journal": decision_log
    })

# =====================================================
# SIMULATION INTERNE (OFFLINE)
# =====================================================
@app.route("/simulate/decision")
def simulate_decision():
    # Simulation simple et stable
    sto_state["tendance"] = "STABLE"
    sto_state["action"] = "OBSERVATION"
    sto_state["raison"] = "Simulation offline – marché neutre"

    log_decision(
        action=sto_state["action"],
        raison=sto_state["raison"]
    )

    return jsonify({
        "statut": "OK",
        "message": "Décision simulée avec succès",
        "action": sto_state["action"],
        "raison": sto_state["raison"]
    })

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
