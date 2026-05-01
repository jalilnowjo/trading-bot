import time
import requests

prijzen = []

saldo_usdt = 1000
btc_bezit = 0
positie_open = False
koopprijs = 0

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

    if len(prijzen) > 5:
        korte_ma = sum(prijzen[-3:]) / 3
        lange_ma = sum(prijzen[-5:]) / 5

        print("Korte MA:", korte_ma)
        print("Lange MA:", lange_ma)

        if rsi is not None:
            print("RSI:", round(rsi, 2))

            # KOOP
            if rsi < 30 and korte_ma > lange_ma and not positie_open:
                btc_bezit = saldo_usdt / prijs
                koopprijs = prijs
                saldo_usdt = 0
                positie_open = True
                print("GEKOCHT op:", koopprijs)

            # VERKOOP
            elif rsi > 70 and korte_ma < lange_ma and positie_open:
                saldo_usdt = btc_bezit * prijs
                winst_verlies = saldo_usdt - 1000
                btc_bezit = 0
                positie_open = False
                print("VERKOCHT op:", prijs)
                print("Winst/verlies:", round(winst_verlies, 2), "USDT")

            # STOP-LOSS / TAKE-PROFIT
            if positie_open:
                verandering = (prijs - koopprijs) / koopprijs * 100

                if verandering <= -1:
                    saldo_usdt = btc_bezit * prijs
                    btc_bezit = 0
                    positie_open = False
                    print("STOP-LOSS geactiveerd")

                elif verandering >= 1.5:
                    saldo_usdt = btc_bezit * prijs
                    btc_bezit = 0
                    positie_open = False
                    print("TAKE-PROFIT geactiveerd")

            print("Totale waarde:", round(saldo_usdt + btc_bezit * prijs, 2), "USDT")

    print("-------------------")
    time.sleep(5)