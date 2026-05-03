from flask import Flask, render_template_string, jsonify
import requests
import time
from threading import Thread

app = Flask(__name__)

prijzen = []
waardes = []

start_saldo = 1000.0
saldo_usdt = 1000.0
btc_bezit = 0.0

positie_open = False
koopprijs = 0.0
hoogste_prijs = 0.0

fee = 0.001

status = "Starten..."
laatste_prijs = 0.0
laatste_rsi = 0.0
rsi_oversold_geweest = False

STOP_LOSS = -1.5
TAKE_PROFIT = 3.0
TRAILING_STOP = 1.0


def bereken_rsi(data, periode=14):
    if len(data) < periode + 1:
        return None

    gains = []
    losses = []

    laatste = data[-(periode + 1):]

    for i in range(1, len(laatste)):
        verschil = laatste[i] - laatste[i - 1]

        if verschil > 0:
            gains.append(verschil)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(verschil))

    avg_gain = sum(gains) / periode
    avg_loss = sum(losses) / periode

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ema(data, periode):
    if len(data) < periode:
        return None

    k = 2 / (periode + 1)
    ema_waarde = sum(data[:periode]) / periode

    for prijs in data[periode:]:
        ema_waarde = prijs * k + ema_waarde * (1 - k)

    return ema_waarde


def bot_loop():
    global saldo_usdt, btc_bezit, positie_open, koopprijs, hoogste_prijs
    global status, laatste_prijs, laatste_rsi, rsi_oversold_geweest

    while True:
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            prijs = float(response.json()["price"])

            prijzen.append(prijs)
            laatste_prijs = prijs

            if len(prijzen) > 300:
                prijzen.pop(0)

            rsi = bereken_rsi(prijzen)
            laatste_rsi = rsi if rsi else 0

            totale_waarde = saldo_usdt + (btc_bezit * prijs)
            waardes.append(totale_waarde)

            if len(waardes) > 150:
                waardes.pop(0)

            if len(prijzen) < 120 or rsi is None:
                status = "Data verzamelen..."
                time.sleep(10)
                continue

            ema20 = ema(prijzen, 20)
            ema50 = ema(prijzen, 50)
            ema100 = ema(prijzen, 100)

            trend_bullish = (
                ema20 is not None
                and ema50 is not None
                and ema100 is not None
                and ema20 > ema50
                and prijs > ema100
            )

            if rsi < 30:
                rsi_oversold_geweest = True

            if not positie_open:
                koop_signaal = (
                    trend_bullish
                    and rsi_oversold_geweest
                    and rsi > 35
                    and rsi < 60
                )

                if koop_signaal:
                    btc_bezit = (saldo_usdt * (1 - fee)) / prijs
                    saldo_usdt = 0
                    koopprijs = prijs
                    hoogste_prijs = prijs
                    positie_open = True
                    rsi_oversold_geweest = False
                    status = "PAPER KOOP - PRO v3"
                else:
                    reden = []
                    if not trend_bullish:
                        reden.append("Trend niet bullish")
                    if not rsi_oversold_geweest:
                        reden.append("RSI niet oversold geweest")
                    if rsi <= 35:
                        reden.append("RSI herstel nog zwak")
                    if rsi >= 60:
                        reden.append("RSI te hoog")

                    status = "Geen koop | " + ", ".join(reden)

            else:
                if prijs > hoogste_prijs:
                    hoogste_prijs = prijs

                verandering = ((prijs - koopprijs) / koopprijs) * 100
                trailing_daling = ((hoogste_prijs - prijs) / hoogste_prijs) * 100

                verkoop_reden = None

                if verandering <= STOP_LOSS:
                    verkoop_reden = "STOP-LOSS"
                elif verandering >= TAKE_PROFIT:
                    verkoop_reden = "TAKE-PROFIT"
                elif trailing_daling >= TRAILING_STOP and verandering > 0:
                    verkoop_reden = "TRAILING STOP"
                elif rsi > 75:
                    verkoop_reden = "RSI EXIT"

                if verkoop_reden:
                    saldo_usdt = btc_bezit * prijs * (1 - fee)
                    btc_bezit = 0
                    positie_open = False
                    status = "PAPER VERKOOP - " + verkoop_reden
                else:
                    status = "Positie open houden"

        except Exception as e:
            status = "FOUT: " + str(e)

        time.sleep(10)


@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>BTC PRO v3 Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial;
            background: #111;
            color: white;
            padding: 30px;
        }
        h1 {
            color: #00ff99;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }
        .box {
            background: #222;
            padding: 15px;
            border-radius: 10px;
        }
        .card {
            background: #1e1e1e;
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
        }
        b {
            color: white;
        }
    </style>
</head>
<body>
    <h1>BTC PRO v3 Dashboard</h1>

    <div class="grid">
        <div class="box">BTC prijs<br><b id="prijs">-</b></div>
        <div class="box">RSI<br><b id="rsi">-</b></div>
        <div class="box">Totale waarde<br><b id="waarde">-</b></div>
        <div class="box">Winst/verlies<br><b id="winst">-</b></div>
    </div>

    <div class="card">
        Status: <b id="status">-</b>
    </div>

    <div class="card">
        <canvas id="chart"></canvas>
    </div>

<script>
let chart;

async function updateData() {
    const res = await fetch('/data');
    const data = await res.json();

    document.getElementById('prijs').innerText = data.prijs + " USDT";
    document.getElementById('rsi').innerText = data.rsi;
    document.getElementById('waarde').innerText = data.waarde + " USDT";
    document.getElementById('winst').innerText = data.winst + " USDT";
    document.getElementById('status').innerText = data.status;

    if (!chart) {
        chart = new Chart(document.getElementById('chart'), {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Totale waarde USDT',
                    data: data.waardes,
                    borderWidth: 2
                }]
            }
        });
    } else {
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.waardes;
        chart.update();
    }
}

setInterval(updateData, 3000);
updateData();
</script>
</body>
</html>
""")


@app.route("/data")
def data():
    totale_waarde = saldo_usdt + (btc_bezit * laatste_prijs)

    return jsonify({
        "prijs": round(laatste_prijs, 2),
        "rsi": round(laatste_rsi, 2),
        "waarde": round(totale_waarde, 2),
        "winst": round(totale_waarde - start_saldo, 2),
        "status": status,
        "waardes": [round(x, 2) for x in waardes],
        "labels": list(range(len(waardes)))
    })


Thread(target=bot_loop, daemon=True).start()

app.run(host="0.0.0.0", port=5000, debug=False)