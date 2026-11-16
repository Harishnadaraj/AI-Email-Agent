from fastapi import APIRouter, Request
from app.agent.brain import brain
from app.services.whatsapp import send_whatsapp_message

router = APIRouter()


# ---------------------------
# 🔥 NORMALIZE USER (SHARED LOGIC)
# ---------------------------
def normalize_user(user: str):
    if not user:
        return "default"
    return user.replace("whatsapp:", "").strip()


# ---------------------------
# 📩 WEBHOOK
# ---------------------------
@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.form()

    raw_user = data.get("From")   # "whatsapp:+9178..."
    msg = data.get("Body") or ""

    # 🔥 CRITICAL FIX
    user = normalize_user(raw_user)

    print("\n==============================")
    print(f"📩 Incoming from {user}")
    print(f"📨 Message: {msg}")

    # 🧠 CALL AGENT
    reply = brain(user, msg)

    print(f"🤖 Reply: {reply}")

    # ---------------------------
    # 📤 SEND WHATSAPP
    # ---------------------------
    try:
        send_whatsapp_message(user, reply)
    except Exception as e:
        print("⚠️ WhatsApp disabled:", str(e))
        print("📩 Message would be:\n", reply)

    return {"status": "ok"}