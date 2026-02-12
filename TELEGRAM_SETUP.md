# Telegram Bot Integration Guide

Dieses Handbuch erklärt, wie Sie einen Telegram-Bot erstellen und in den Zenatus Backtester integrieren, um Alerts (z.B. bei Fehlern oder Backtest-Abschluss) direkt aufs Handy zu erhalten.

## Schritt 1: Bot erstellen
1. Öffnen Sie Telegram und suchen Sie nach **@BotFather**.
2. Starten Sie den Chat (`/start`).
3. Senden Sie den Befehl `/newbot`.
4. Folgen Sie den Anweisungen:
   - Geben Sie dem Bot einen Namen (z.B. "Zenatus Alert Bot").
   - Geben Sie dem Bot einen Usernamen (muss auf `bot` enden, z.B. `zenatus_alert_bot`).
5. **BotFather gibt Ihnen einen API Token.**
   - Beispiel: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
   - **Kopieren Sie diesen Token.**

## Schritt 2: Chat ID herausfinden
Damit der Bot weiß, an WEN er senden soll, brauchen Sie Ihre Chat ID.
1. Starten Sie einen Chat mit Ihrem neuen Bot (`/start`).
2. Senden Sie eine beliebige Nachricht an den Bot (z.B. "Hello").
3. Öffnen Sie folgende URL im Browser (ersetzen Sie `<TOKEN>` mit Ihrem Token aus Schritt 1):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Sie sehen eine JSON-Antwort. Suchen Sie nach `"chat": {"id": 123456789, ...}`.
   - Die Nummer `123456789` ist Ihre **Chat ID**.

## Schritt 3: Integration in Zenatus
Fügen Sie die Daten in Ihre `config/config.yaml` ein:

```yaml
alerts:
  enabled: true
  telegram_bot_token: "123456789:ABCdef..."
  telegram_chat_id: "987654321"
```

## Testen
Starten Sie den Container neu. Wenn alles korrekt ist, sendet der `alert_agent.py` Nachrichten an diesen Chat.
