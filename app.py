from flask import Flask, jsonify
import time

app = Flask(__name__)

# ======================
# CONFIG GLOBALE
# ======================
STO_VERSION = "1.0-OFFLINE"
CAPITAL_SIMULE = 1000.0  # capital fictif
RISQUE_PAR_TRADE = 0.02  # 2%

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode_decision": "C",  # A=passif, B=semi, C=agressif
    "statut": "STO STABLE – MODE OFFLINE",
    "capital": CAPITAL_SIMULE,
    "last_action": "ATTENTE",
    "reason": "Initialisation",
    "start_time": time.time()
}

# ======================
# INDICATEURS OFFLINE (SIMULÉS)
# ======================
def calcul_rsi(prices):
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains) / max(len(gains), 1)
    avg_loss = sum(losses) / max(len(losses), 1)
    if avg_loss == 0:
        return 70
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calcul_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)

# ======================
# LOGIQUE DÉCISIONNELLE C (PRO)
# ======================
def decision_engine():
    prices = [87000, 87200, 87150, 87300, 87500, 87400]
    rsi = calcul_rsi(prices)
    ema_fast = calcul_ema(prices, 5)
    ema_slow = calcul_ema(prices, 10)

    position_size = sto_state["capital"] * RISQUE_PAR_TRADE

    if rsi < 30 and ema_fast > ema_slow:
        action = "ACHAT"
        reason = "RSI survendu + EMA haussière"
    elif rsi > 70 and ema_fast < ema_slow:
        action = "VENTE"
        reason = "RSI suracheté + EMA baissière"
    else:
        action = "ATTENTE"
        reason = "Aucune condition optimale"

    return {
        "action_STO": action,
        "raison": reason,
        "RSI": rsi,
        "EMA_fast": ema_fast,
        "EMA_slow": ema_slow,
        "position_size": round(position_size, 2)
    }

# ======================
# ROUTES API
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": sto_state["statut"],
        "version": STO_VERSION,
        "mode_decision": sto_state["mode_decision"],
        "capital_simule": sto_state["capital"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

@app.route("/decision", methods=["GET"])
def decision():
    result = decision_engine()
    sto_state["last_action"] = result["action_STO"]
    sto_state["reason"] = result["raison"]

    return jsonify({
        "statut": "OK",
        "mode_decision": sto_state["mode_decision"],
        **result
    })

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify({
        "last_action": sto_state["last_action"],
        "reason": sto_state["reason"],
        "capital": sto_state["capital"],
        "mode_decision": sto_state["mode_decision"]
    })

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
