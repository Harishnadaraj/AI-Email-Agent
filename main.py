from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()

from app.routes import whatsapp, dashboard, api

from app.agent.memory import (
    init_db,
    save_message,
    set_context,
    save_log
)

from app.services.gmail import get_unread_emails, mark_as_read
from app.services.whatsapp import send_whatsapp_message
from app.agent.brain import client

app = FastAPI()

app.include_router(whatsapp.router)
app.include_router(dashboard.router)
app.include_router(api.router)


# ---------------------------
# 🔥 NORMALIZE USER
# ---------------------------
def normalize_user(user):
    if not user:
        return "default"
    return user.replace("whatsapp:", "").strip()


# 🔥 FIXED: USE MY_PHONE (MATCHES WEBHOOK FORMAT)
USER_ID = normalize_user(os.getenv("MY_PHONE"))

print("🧠 SYSTEM USER:", USER_ID)


# ---------------------------
# 🧠 SAFE JSON PARSER
# ---------------------------
def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return None
    return None


# ---------------------------
# 📩 EMAIL LISTENER
# ---------------------------
def check_emails():
    print("\n🔄 Checking emails...")

    try:
        emails = get_unread_emails()

        if not emails:
            print("📭 No new emails")
            return

        for email in emails:
            subject = email.get("subject") or "(no subject)"
            body = email.get("body") or ""

            print("📩 New email:", subject)

            # 🔥 LOG
            save_log(USER_ID, "email_received", email)

            # ---------------------------
            # 🧠 LLM ANALYSIS
            # ---------------------------
            prompt = f"""
You are an AI email assistant.

Your job is to decide importance FOR THE USER.

IMPORTANT means:
- Requires reply or action
- Personal communication
- Meetings, classes, deadlines
- Anything directed to the user

NOT IMPORTANT means:
- Promotions, ads, newsletters
- Automated messages with no action needed

---

Return ONLY JSON:

{{
  "score": number (0-100),
  "summary": "1 line summary",
  "notify": "short WhatsApp style message"
}}

---

SCORING RULES:
- 80–100 → urgent/action required
- 50–79 → important
- 20–49 → maybe useful
- 0–19 → ignore/spam

---

EMAIL:
Subject: {subject}
Body: {body[:400]}
"""

            try:
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )

                output = res.choices[0].message.content.strip()
                print("🧠 LLM:", output)

                data = safe_json_parse(output)

                if not data:
                    raise Exception("JSON parse failed")

            except Exception as e:
                print("⚠️ LLM failed:", str(e))

                data = {
                    "score": 50,
                    "summary": subject,
                    "notify": f"New email: {subject}"
                }

            # 🔥 LOG decision
            save_log(USER_ID, "email_decision", data)

            # ---------------------------
            # 🎯 IMPORTANCE LOGIC
            # ---------------------------
            score = data.get("score", 50)
            is_important = score >= 20

            print(f"📊 Score: {score} | Important: {is_important}")

            if not is_important:
                print("🚫 Ignored")
                mark_as_read(email["id"])
                continue

            print("🧠 STORE USER:", USER_ID)

            # ---------------------------
            # 🧠 STORE CONTEXT (FIXED)
            # ---------------------------
            set_context(USER_ID, "last_email", json.dumps(email))

            # 🔥 DEBUG (THIS WILL CONFIRM FIX)
            print("✅ STORED last_email for:", USER_ID)

            # ---------------------------
            # 💬 SAVE MEMORY
            # ---------------------------
            save_message(
                USER_ID,
                "assistant",
                f"📩 {data.get('summary')}"
            )

            notify_msg = data.get("notify") or subject

            # ---------------------------
            # 📤 SEND WHATSAPP
            # ---------------------------
            try:
                send_whatsapp_message(
                    USER_ID,
                    f"{notify_msg}\n\nWhat do you want to do?"
                )
            except Exception as e:
                print("⚠️ WhatsApp disabled:", str(e))
                print("📩 Message would be:\n", notify_msg)

            # ---------------------------
            # ✅ MARK READ
            # ---------------------------
            mark_as_read(email["id"])

    except Exception as e:
        print("❌ Email check error:", str(e))


# ---------------------------
# 🔁 SCHEDULER
# ---------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(
    check_emails,
    "interval",
    seconds=20,
    max_instances=1,
    coalesce=True
)


# ---------------------------
# 🚀 STARTUP
# ---------------------------
@app.on_event("startup")
def startup():
    init_db()
    scheduler.start()
    print("🚀 Agent running...")


# ---------------------------
# 🛑 SHUTDOWN
# ---------------------------
@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()