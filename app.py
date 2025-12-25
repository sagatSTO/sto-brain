from flask import Flask, request, jsonify, render_template_string
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG STO
# ======================
ADMIN_EMAIL = "saguiorelio32@gmail.com"
START_TIME = time.time()

# ======================
# ÉTAT STO
# ======================
sto_state = {
    "mode": "OFFLINE",
    "decision_mode": "C",   # A / B / C
    "last_action": "ATTENTE",
    "reason": "STO STABLE – MODE OFFLINE",
}

# ======================
# JOURNAL DES DÉCISIONS
# ======================
decision_log = []

def log_decision(data):
    decision_log.append({
        "time": int(time.time()),
        **data
    })
    if len(decision_log) > 100:
        decision_log.pop(0)

# ======================
# INDICATEURS
# ======================
def ema(prices, period):
    k = 2 / (period + 1)
    e = prices[0]
    for p in prices[1:]:
        e = p * k + e * (1 - k)
    return round(e, 2)

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
        "decision": sto_state["decision_mode"],
        "uptime_sec": int(time.time() - START_TIME)
    })

# ======================
# SIMULATION OFFLINE
# ======================
@app.route("/simulate")
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(p) for p in raw.split(",") if p.strip()]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées (min 20)"
        }), 400

    rsi_val = rsi(prices)
    ema_fast = ema(prices[-20:], 10)
    ema_slow = ema(prices[-20:], 20)

    signal = "STABLE"
    action = "ATTENTE"

    if rsi_val > 60 and ema_fast > ema_slow:
        signal = "HAUSSE"
        action = "SURVEILLANCE"
    elif rsi_val < 40 and ema_fast < ema_slow:
        signal = "BAISSE"
        action = "ATTENTE"

    sto_state["last_action"] = action
    sto_state["reason"] = f"RSI {rsi_val} / EMA"

    log_decision({
        "prix": prices[-1],
        "RSI": rsi_val,
        "EMA10": ema_fast,
        "EMA20": ema_slow,
        "signal": signal,
        "action": action
    })

    return jsonify({
        "statut_marche": "OK",
        "prix_actuel": prices[-1],
        "RSI": rsi_val,
        "EMA10": ema_fast,
        "EMA20": ema_slow,
        "signal": signal,
        "action_STO": action
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
    prices = [d["prix"] for d in decision_log if "prix" in d]
    rsi_vals = [d["RSI"] for d in decision_log if "RSI" in d]

    html = """
    <html>
    <head>
        <title>STO Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body style="font-family:Arial;background:#111;color:#eee">
        <h1>STO Dashboard</h1>
        <p>Mode: {{mode}} | Décision: {{decision}}</p>

        <canvas id="priceChart"></canvas>
        <canvas id="rsiChart"></canvas>

        <script>
        const prices = {{prices}};
        const rsi = {{rsi}};

        new Chart(document.getElementById('priceChart'), {
            type: 'line',
            data: { labels: prices.map((_,i)=>i),
                datasets:[{label:'Prix',data:prices,borderColor:'lime'}]}
        });

        new Chart(document.getElementById('rsiChart'), {
            type: 'line',
            data: { labels: rsi.map((_,i)=>i),
                datasets:[{label:'RSI',data:rsi,borderColor:'orange'}]}
        });
        </script>
    </body>
    </html>
    """
    return render_template_string(
        html,
        prices=prices,
        rsi=rsi_vals,
        mode=sto_state["mode"],
        decision=sto_state["decision_mode"]
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
