"""
Formats enriched signals into pretty Discord/Telegram messages.
"""
def format_alert(sig):
    s = sig.get("signal","HOLD")
    emo = "📈" if s=="BUY" else "📉" if s=="SELL" else "🤖"
    msg = f"{emo}  {sig.get('strategy','?')} suggests **{s}** {sig.get('symbol','')} @ conf. {sig.get('confidence',0)}%"
    return msg
