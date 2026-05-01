
import requests

symbol = "BTCUSDT"

start_saldo = 1000
fee = 0.001

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

def backtest():
    saldo_usdt = start_saldo
    coin_bezit = 0
    positie_open = False
    koopprijs = 0
    hoogste_prijs = 0
    trades = 0
    wins = 0
    losses = 0
    rsi_oversold_geweest = False
    peak = start_saldo
    max_drawdown = 0

    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "1h",
        "limit": 500
    }

    response = requests.get(url, params=params)
    candles = response.json()

    prijzen = []

    for candle in candles:
        sluitprijs = float(candle[4])
        prijzen.append(sluitprijs)

        rsi = bereken_rsi(prijzen)

        if len(prijzen) >= 100 and rsi is not None:
            ma20 = sum(prijzen[-20:]) / 20
            ma50 = sum(prijzen[-50:]) / 50
            ma100 = sum(prijzen[-100:]) / 100
            ma100_vorig = sum(prijzen[-120:-20]) / 100

            lange_trend_stijgt = ma100 > ma100_vorig
            prijs_boven_trend = sluitprijs > ma100

            hoogste_20 = max(prijzen[-20:])
            laagste_20 = min(prijzen[-20:])
            range_pct = (hoogste_20 - laagste_20) / sluitprijs * 100

            genoeg_volatiliteit = range_pct > 1.5

            if rsi < 30:
                rsi_oversold_geweest = True

            if not positie_open:
                if (
                    rsi_oversold_geweest
                    and rsi > 30
                    and ma20 > ma50
                    and lange_trend_stijgt
                    and prijs_boven_trend
                    and genoeg_volatiliteit
                ):
                    coin_bezit = (saldo_usdt * (1 - fee)) / sluitprijs
                    koopprijs = sluitprijs
                    hoogste_prijs = sluitprijs
                    saldo_usdt = 0
                    positie_open = True
                    rsi_oversold_geweest = False
                    trades += 1
                    print("KOOP:", sluitprijs)

            else:
                if sluitprijs > hoogste_prijs:
                    hoogste_prijs = sluitprijs

                verandering = (sluitprijs - koopprijs) / koopprijs * 100
                trailing_daling = (hoogste_prijs - sluitprijs) / hoogste_prijs * 100

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
                    verkoop_waarde = coin_bezit * sluitprijs * (1 - fee)
                    winst_trade = verkoop_waarde - (coin_bezit * koopprijs)

                    saldo_usdt = verkoop_waarde
                    coin_bezit = 0
                    positie_open = False
                    trades += 1

                    if winst_trade > 0:
                        wins += 1
                    else:
                        losses += 1

                    print("VERKOOP:", verkoop_reden, sluitprijs, "P/L:", round(winst_trade, 2))

        huidige_waarde = saldo_usdt + (coin_bezit * sluitprijs)

        if huidige_waarde > peak:
            peak = huidige_waarde

        drawdown = (peak - huidige_waarde) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    laatste_prijs = prijzen[-1]
    eindwaarde = saldo_usdt + (coin_bezit * laatste_prijs)
    winst_verlies = eindwaarde - start_saldo
    winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    print("\nRESULTATEN BTC")
    print("-------------------")
    print("Eindwaarde:", round(eindwaarde, 2), "USDT")
    print("Winst/verlies:", round(winst_verlies, 2), "USDT")
    print("Aantal trades:", trades)
    print("Winrate:", round(winrate, 2), "%")
    print("Max drawdown:", round(max_drawdown, 2), "%")

backtest()