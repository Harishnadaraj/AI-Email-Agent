import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")  # must be like: whatsapp:+1415...

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def send_whatsapp_message(to, message):
    """
    to -> should be like: +9178...
    we convert to whatsapp:+9178...
    """

    if not to:
        print("❌ ERROR: Missing 'to' number")
        return

    try:
        formatted_to = f"whatsapp:{to}"

        print("📤 Sending WhatsApp")
        print("   FROM:", FROM_NUMBER)
        print("   TO  :", formatted_to)
        print("   MSG :", message)

        client.messages.create(
            body=message,
            from_=FROM_NUMBER,
            to=formatted_to
        )

    except Exception as e:
        print("⚠️ WhatsApp failed:", str(e))
        print("📩 Message would be:\n", message)