import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

from app.agent.memory import (
    get_history,
    save_message,
    get_context,
    set_context,
    set_pending_action,
    get_pending_action,
    clear_pending_action,
    save_log
)

from app.services.gmail import send_reply

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------------------
# 🔥 NORMALIZE USER (MUST MATCH MAIN)
# ---------------------------
def normalize_user(user):
    if not user:
        return "default"
    return user.replace("whatsapp:", "").strip()


# ---------------------------
# 📧 HELPER
# ---------------------------
def extract_email(raw):
    match = re.search(r'<(.+?)>', raw)
    return match.group(1) if match else raw


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
# 🧠 MAIN BRAIN
# ---------------------------
def brain(user, user_msg):

    user = normalize_user(user)

    print("\n==============================")
    print("📩 USER:", user_msg)
    print("🧠 USER:", user)

    save_message(user, "user", user_msg)
    save_log(user, "user_message", user_msg)

    pending = get_pending_action(user)
    mode = get_context(user, "mode")

    print("🧠 Pending:", pending)
    print("🧠 Mode:", mode)

    msg = user_msg.lower().strip()

    # ---------------------------
    # 🔥 HANDLE PENDING ACTION
    # ---------------------------
    if pending:

        # ✅ CONFIRM SEND
        if msg in ["yes", "send", "ok", "okay"]:
            print("📤 TRIGGER SEND EMAIL")

            try:
                result = send_reply(
                    pending["to"],
                    pending["subject"],
                    pending["body"]
                )
                print("📤 SEND RESULT:", result)

                save_log(user, "email_sent", pending)

                clear_pending_action(user)
                set_context(user, "mode", None)

                reply = "✅ Email sent."
            except Exception as e:
                print("❌ SEND FAILED:", str(e))
                reply = "❌ Failed to send email."

            save_message(user, "assistant", reply)
            return reply

        # ✏️ EDIT MODE
        if msg == "edit":
            set_context(user, "mode", "edit")

            reply = "✏️ Tell me the updated message."
            save_message(user, "assistant", reply)
            return reply

        # 🔥 APPLY EDIT
        if mode == "edit":
            new_body = user_msg.strip()

            set_pending_action(user, {
                **pending,
                "body": new_body
            })

            set_context(user, "mode", "draft")

            save_log(user, "email_draft_updated", new_body)

            reply = f"""📧 Updated Draft:

{new_body}

Send it? (yes/edit)"""

            save_message(user, "assistant", reply)
            return reply

        # ❌ INVALID INPUT
        reply = "Say 'yes' to send or 'edit' to modify."
        save_message(user, "assistant", reply)
        return reply

    # ---------------------------
    # 📩 LOAD LAST EMAIL
    # ---------------------------
    last_email_raw = get_context(user, "last_email")

    last_email = None
    if last_email_raw:
        try:
            last_email = json.loads(last_email_raw)
        except:
            print("⚠️ Context parse failed")

    print("📧 LAST EMAIL:", last_email)

    # ---------------------------
    # 🔥 FIX: HANDLE "YES" WITHOUT PENDING
    # ---------------------------
    if not pending and msg in ["yes", "send"]:
        reply = "⚠️ No draft available to send."
        save_message(user, "assistant", reply)
        return reply

    # ---------------------------
    # ❌ NO EMAIL CONTEXT
    # ---------------------------
    if not last_email and any(x in msg for x in ["reply", "respond"]):
        reply = "⚠️ No recent email found to reply."
        save_message(user, "assistant", reply)
        return reply

    history = get_history(user)

    # ---------------------------
    # 🧠 PROMPT
    # ---------------------------
    system_prompt = f"""
You are an AI email assistant.

Return ONLY JSON.

Intent:
- If user wants to reply → action = "reply_email"
- Otherwise → action = "chat"

Format:

{{
  "action": "reply_email" OR "chat",
  "body": "...",
  "message": "..."
}}

Rules:
- Keep replies short (1–2 lines)
- Do NOT include names unless provided
- Do NOT guess missing info
- message must NOT be empty

LAST EMAIL:
{last_email}
"""

    messages = [{"role": "system", "content": system_prompt}] + history

    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.3
    )

    output = res.choices[0].message.content.strip()
    print("🧠 RAW LLM:", output)

    data = safe_json_parse(output)

    if not data:
        reply = "⚠️ AI error. Try again."
        save_message(user, "assistant", reply)
        return reply

    save_log(user, "llm_output", data)

    action = data.get("action")

    # ---------------------------
    # 📤 EMAIL FLOW
    # ---------------------------
    if action == "reply_email" and last_email:

        body = (data.get("body") or "").strip()

        if not body:
            reply = "⚠️ Need message content."
            save_message(user, "assistant", reply)
            return reply

        to_email = extract_email(last_email["from"])

        pending_data = {
            "type": "reply_email",
            "to": to_email,
            "subject": last_email["subject"],
            "body": body
        }

        set_pending_action(user, pending_data)
        set_context(user, "mode", "draft")

        save_log(user, "email_draft_created", pending_data)

        reply = f"""📧 Draft:

{body}

Send it? (yes/edit)"""

        save_message(user, "assistant", reply)
        return reply

    # ---------------------------
    # 💬 CHAT FLOW
    # ---------------------------
    reply = data.get("message") or "Okay 👍"

    save_message(user, "assistant", reply)
    return reply