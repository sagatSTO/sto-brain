from flask import Flask, request, jsonify, render_template_string
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "SEMI_ACTIF",
    "mode_decision": "C",
    "last_action": "OBSERVATION",
    "reason": "Initialisation STO",
    "start_time": time.time()
}

# ======================
# JOURNAL DES DÉCISIONS
# ======================
decision_log = []

def log_decision(data):
    data["timestamp"] = int(time.time())
    decision_log.append(data)
    if len(decision_log) > 100:
        decision_log.pop(0)

# ======================
# INDICATEURS
# ======================
def ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    value = prices[0]
    for p in prices[1:]:
        value = p * k + value * (1 - k)
    return round(value, 2)

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# HOME
# ======================
@app.route("/")
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "mode_decision": sto_state["mode_decision"],
        "uptime_sec": int(time.time() - sto_state["start_time"])
    })

# ======================
# SIMULATION OFFLINE
# ======================
@app.route("/simulate")
def simulate():
    raw = request.args.get("prices", "")
    try:
        prices = [float(x) for x in raw.split(",") if x.strip()]
        if len(prices) < 20:
            return jsonify({
                "statut_marche": "ERREUR",
                "raison": "Pas assez de données simulées (min 20)"
            })

        r = rsi(prices)
        e_fast = ema(prices, 10)
        e_slow = ema(prices, 20)

        if r is None or e_fast is None or e_slow is None:
            raise Exception("Calcul indicateurs impossible")

        if r > 60 and e_fast > e_slow:
            signal = "ACHAT"
        elif r < 40 and e_fast < e_slow:
            signal = "VENTE"
        else:
            signal = "ATTENTE"

        log_decision({
            "prix": prices[-1],
            "RSI": r,
            "EMA_10": e_fast,
            "EMA_20": e_slow,
            "signal": signal
        })

        return jsonify({
            "statut_marche": "OK",
            "prix_actuel": prices[-1],
            "RSI": r,
            "EMA_10": e_fast,
            "EMA_20": e_slow,
            "action_STO": signal,
            "mode_decision": sto_state["mode_decision"]
        })

    except Exception as e:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": str(e)
        })

# ======================
# JOURNAL API
# ======================
@app.route("/journal")
def journal():
    return jsonify(decision_log)

# ======================
# DASHBOARD VISUEL
# ======================
@app.route("/dashboard")
def dashboard():
    html = """
    <html>
    <head>
        <title>STO Dashboard</title>
        <style>
            body { background:#0f172a; color:white; font-family:Arial }
            h1 { color:#38bdf8 }
            table { border-collapse: collapse; width:100% }
            th, td { border:1px solid #334155; padding:6px; text-align:center }
            th { background:#1e293b }
        </style>
    </head>
    <body>
        <h1>📊 STO – Dashboard Décisionnel</h1>
        <table>
            <tr>
                <th>Temps</th>
                <th>Prix</th>
                <th>RSI</th>
                <th>EMA 10</th>
                <th>EMA 20</th>
                <th>Action</th>
            </tr>
            {% for d in logs %}
            <tr>
                <td>{{ d.timestamp }}</td>
                <td>{{ d.prix }}</td>
                <td>{{ d.RSI }}</td>
                <td>{{ d.EMA_10 }}</td>
                <td>{{ d.EMA_20 }}</td>
                <td>{{ d.signal }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html, logs=decision_log)

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
