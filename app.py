from flask import Flask, jsonify
import time
import statistics

app = Flask(__name__)

# ======================
# CONFIG STO
# ======================
STO_MODE = "C"  # A = conservateur | B = normal | C = hybride pro
RISK_PROFILE = {
    "A": 0.01,   # 1% du capital
    "B": 0.02,   # 2%
    "C": 0.03    # 3%
}

CAPITAL = 1000  # capital simulé
DECISION_LOG = []

# ======================
# OUTILS INDICATEURS
# ======================
def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50  # neutre

    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = prices[-i] - prices[-i - 1]
        if delta >= 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))

    avg_gain = statistics.mean(gains) if gains else 0
    avg_loss = statistics.mean(losses) if losses else 1

    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# DONNÉES SIMULÉES
# ======================
def simulated_prices():
    # Simulation réaliste de marché
    base = 87000
    return [base + i * 15 for i in range(30)]

# ======================
# LOGIQUE DÉCISIONNELLE
# ======================
def sto_decision():
    prices = simulated_prices()

    ema_short = calculate_ema(prices[-10:], 10)
    ema_long = calculate_ema(prices[-20:], 20)
    rsi = calculate_rsi(prices)

    if ema_short > ema_long and rsi < 70:
        action = "PREPARATION_ENTREE"
        reason = "Tendance haussière + RSI sain"
    elif rsi > 70:
        action = "ATTENTE"
        reason = "Marché suracheté"
    elif rsi < 30:
        action = "OBSERVATION"
        reason = "Zone survendue"
    else:
        action = "ATTENTE"
        reason = "Aucune opportunité claire"

    risk = RISK_PROFILE[STO_MODE]
    position_size = round(CAPITAL * risk, 2)

    log = {
        "time": int(time.time()),
        "mode": STO_MODE,
        "ema_short": round(ema_short, 2),
        "ema_long": round(ema_long, 2),
        "rsi": rsi,
        "action": action,
        "position_size": position_size,
        "reason": reason
    }

    DECISION_LOG.append(log)
    return log

# ======================
# ROUTES
# ======================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO STABLE – MODE OFFLINE",
        "mode_decision": STO_MODE,
        "capital_simule": CAPITAL
    })

@app.route("/decision", methods=["GET"])
def decision():
    return jsonify(sto_decision())

@app.route("/journal", methods=["GET"])
def journal():
    return jsonify(DECISION_LOG[-10:])  # dernières décisions

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
