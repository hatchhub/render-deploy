import os
import stripe
import requests
from fastapi import FastAPI, Request, Header, HTTPException
from dotenv import load_dotenv

# 環境変数の読み込み（.envがプロジェクト直下にある想定）
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

app = FastAPI()


@app.post("/stripe-webhook")
async def webhook_received(request: Request, stripe_signature: str = Header(None)):
    """
    StripeからのWebhookを受信し、checkout.session.completed イベント時に
    Supabaseのユーザー情報を更新する。
    """
    payload = await request.body()
    print("📩 Received payload:", payload.decode())

    # Stripe署名検証
    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=stripe_signature, secret=endpoint_secret
        )
        print("✅ Parsed event type:", event["type"])
    except Exception as e:
        print("❌ Webhook error:", str(e))
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    # Checkout完了時の処理
    if event["type"] == "checkout.session.completed":
        email = event["data"]["object"]["customer_details"]["email"]
        print("📧 Extracted email:", email)

        # Supabase管理者権限でユーザーを取得（emailフィルター）
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
        }
        url = f"{SUPABASE_URL}/auth/v1/admin/users?email={email}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print("⚠️ Failed to fetch user:", response.text)
            return {"status": "error"}

        users = response.json()["users"]
        user = users[0] if users else None

        if user:
            user_id = user["id"]
            print("🆔 Found user_id:", user_id)

            # user_metadata.subscription_active = True に更新
            update_url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
            update_response = requests.put(
                update_url,
                headers=headers,
                json={"user_metadata": {"subscription_active": True}}
            )
            print("🛠️ Update result:", update_response.json())
            return {"status": "subscription activated"}
        else:
            print("⚠️ No user found for email:", email)

    print("ℹ️ Webhook event ignored.")
    return {"status": "ignored"}
