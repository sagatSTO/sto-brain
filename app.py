from flask import Flask, jsonify, request
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG STO
# ======================
STO_MODE = "OFFLINE"
DECISION_MODE = "C"  # A = logique simple / C = logique avancée
CAPITAL_SIMULE = 1000

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OBSERVATION",
    "statut": "STO STABLE – MODE OFFLINE",
    "capital": CAPITAL_SIMULE,
    "last_action": "ATTENTE",
    "raison": "Initialisation",
    "start_time": time.time(),
    "journal": []
}

# ======================
# INDICATEURS
# ======================
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# VISUEL 1 – ÉTAT STO
# ======================
@app.route("/")
def visual_state():
    return f"""
    <html>
    <head><title>STO – État</title></head>
    <body style="font-family:Arial">
        <h1>🤖 STO – État général</h1>
        <p><b>Statut :</b> {sto_state['statut']}</p>
        <p><b>Mode décision :</b> {DECISION_MODE}</p>
        <p><b>Capital simulé :</b> {sto_state['capital']} $</p>
        <p><b>Dernière action :</b> {sto_state['last_action']}</p>
        <p><b>Raison :</b> {sto_state['raison']}</p>
        <p><b>Temps en ligne :</b> {int(time.time() - sto_state['start_time'])} sec</p>
        <a href="/visual/simulation">➡️ Voir simulation</a>
    </body>
    </html>
    """

# ======================
# VISUEL 2 – SIMULATION
# ======================
@app.route("/visual/simulation")
def visual_simulation():
    return """
    <html>
    <head><title>STO – Simulation</title></head>
    <body style="font-family:Arial">
        <h1>📊 Simulation STO (offline)</h1>
        <p>Utilise l’URL suivante pour tester :</p>
        <code>
        /simulate?prices=100,102,101,105,108,110,109,111,115,118,120
        </code>
        <br><br>
        <a href="/">⬅️ Retour état STO</a>
    </body>
    </html>
    """

# ======================
# SIMULATION INDICATEURS + DÉCISION
# ======================
@app.route("/simulate")
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées"
        })

    rsi = calculate_rsi(prices)
    ema_short = calculate_ema(prices, 9)
    ema_long = calculate_ema(prices, 21)

    action = "ATTENTE"
    raison = "Marché neutre"

    if DECISION_MODE == "C":
        if rsi and rsi < 35 and ema_short > ema_long:
            action = "ACHAT"
            raison = "RSI bas + EMA haussière"
        elif rsi and rsi > 65 and ema_short < ema_long:
            action = "VENTE"
            raison = "RSI haut + EMA baissière"

    sto_state["last_action"] = action
    sto_state["raison"] = raison
    sto_state["journal"].append({
        "time": int(time.time()),
        "action": action,
        "raison": raison
    })

    return jsonify({
        "statut_marche": "OK",
        "mode_decision": DECISION_MODE,
        "RSI": rsi,
        "EMA_courte": ema_short,
        "EMA_longue": ema_long,
        "action_STO": action,
        "raison": raison
    })

# ======================
# JOURNAL DES DÉCISIONS
# ======================
@app.route("/journal")
def journal():
    return jsonify(sto_state["journal"])

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
