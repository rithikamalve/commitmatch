import os
from dotenv import load_dotenv

load_dotenv()

# ── AWS ────────────────────────────────────────────────────────────────────
AWS_REGION           = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID    = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# ── DynamoDB ───────────────────────────────────────────────────────────────
# Leave blank to use real DynamoDB; set to http://localhost:8000 for DynamoDB Local
DYNAMODB_ENDPOINT    = os.getenv("DYNAMODB_ENDPOINT", "")

# ── Bedrock ────────────────────────────────────────────────────────────────
BEDROCK_MODEL_ID     = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")

# ── API Gateway WebSocket ──────────────────────────────────────────────────
WEBSOCKET_ENDPOINT   = os.getenv("WEBSOCKET_ENDPOINT", "")
WEBSOCKET_API_ID     = os.getenv("WEBSOCKET_API_ID", "")

# ── S3 ─────────────────────────────────────────────────────────────────────
S3_BUCKET            = os.getenv("S3_BUCKET", "commitmatch-frontend")

# ── Twilio ─────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# ── App ────────────────────────────────────────────────────────────────────
CSV_PATH             = os.getenv("CSV_PATH", "data/Dataset.csv")
DEMO_MODE            = os.getenv("DEMO_MODE", "true").lower() == "true"
DEMO_WHATSAPP        = os.getenv("DEMO_WHATSAPP", "false").lower() == "true"
DEMO_PHONE_1         = os.getenv("DEMO_PHONE_1", "")
PORT                 = int(os.getenv("PORT", "8000"))
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3000")
