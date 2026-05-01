import time
import requests

symbol = "BTCUSDT"

saldo_usdt = 1000
btc_bezit = 0
positie_open = False
koopprijs = 0
hoogste_prijs = 0
fee = 0.001

prijzen = []
rsi_oversold_geweest = False

def bereken_rsi(prijzen, periode=14):
    if len(prijzen) < periode + 1:
        return None

    winsten = []
    verliezen = []
    laatste = prijzen[-(periode + 1):]

    for i in range(1, len(laatste)):
        verschil = laatste[i] - laatste[i - 1]
        if verschil > 0:
            winsten.append(verschil)
            verliezen.append(0)
        else:
            winsten.append(0)
            verliezen.append(abs(verschil))

    gem_winst = sum(winsten) / periode
    gem_verlies = sum(verliezen) / periode

    if gem_verlies == 0:
        return 100

    rs = gem_winst / gem_verlies
    return 100 - (100 / (1 + rs))

while True:
    response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
    data = response.json()

    prijs = float(data["price"])
    prijzen.append(prijs)

    print("BTC prijs:", prijs)

    rsi = bereken_rsi(prijzen)

    if len(prijzen) >= 100 and rsi is not None:
        ma20 = sum(prijzen[-20:]) / 20
        ma50 = sum(prijzen[-50:]) / 50
        ma100 = sum(prijzen[-100:]) / 100
        ma100_vorig = sum(prijzen[-120:-20]) / 100

        trend_stijgt = ma100 > ma100_vorig
        prijs_boven_trend = prijs > ma100

        hoogste_20 = max(prijzen[-20:])
        laagste_20 = min(prijzen[-20:])
        range_pct = (hoogste_20 - laagste_20) / prijs * 100
        genoeg_volatiliteit = range_pct > 1.5

        print("RSI:", round(rsi, 2))
        print("MA20:", round(ma20, 2))
        print("MA50:", round(ma50, 2))
        print("MA100:", round(ma100, 2))

        if rsi < 30:
            rsi_oversold_geweest = True

        if not positie_open:
            if (
                rsi_oversold_geweest
                and rsi > 30
                and ma20 > ma50
                and trend_stijgt
                and prijs_boven_trend
                and genoeg_volatiliteit
            ):
                btc_bezit = (saldo_usdt * (1 - fee)) / prijs
                koopprijs = prijs
                hoogste_prijs = prijs
                saldo_usdt = 0
                positie_open = True
                rsi_oversold_geweest = False
                print("PAPER KOOP op:", koopprijs)
            else:
                print("Geen koop")

        else:
            if prijs > hoogste_prijs:
                hoogste_prijs = prijs

            verandering = (prijs - koopprijs) / koopprijs * 100
            trailing_daling = (hoogste_prijs - prijs) / hoogste_prijs * 100

            verkoop_reden = None

            if verandering <= -2:
                verkoop_reden = "STOP-LOSS"
            elif verandering >= 6:
                verkoop_reden = "TAKE-PROFIT"
            elif trailing_daling >= 1.5:
                verkoop_reden = "TRAILING"
            elif rsi > 75:
                verkoop_reden = "RSI EXIT"

            if verkoop_reden:
                saldo_usdt = btc_bezit * prijs * (1 - fee)
                winst_verlies = saldo_usdt - 1000
                btc_bezit = 0
                positie_open = False
                print("PAPER VERKOOP:", verkoop_reden, "op:", prijs)
                print("Winst/verlies:", round(winst_verlies, 2), "USDT")
            else:
                print("Positie open houden")

        totale_waarde = saldo_usdt + (btc_bezit * prijs)
        print("Totale waarde:", round(totale_waarde, 2), "USDT")

    else:
        print("Data verzamelen:", len(prijzen), "/ 100")

    print("-------------------")
    time.sleep(10)