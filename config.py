"""
All settings you may want to edit live in this file.
Secrets (token, IDs) are read from the .env file, never written here.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file in the project folder


def _required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing {name}. Add it to your .env file.")
    return value


# ---------- SECRETS / IDS (from .env) ----------
BOT_TOKEN = _required("BOT_TOKEN")
try:
    ADMIN_IDS = {int(x) for x in _required("ADMIN_IDS").replace(" ", "").split(",") if x}
    ADMIN_CHAT_ID = int(_required("ADMIN_CHAT_ID"))
    CHANNEL_ID = int(_required("CHANNEL_ID"))
except ValueError:
    raise SystemExit("ADMIN_IDS, ADMIN_CHAT_ID and CHANNEL_ID must be numbers.")

# ---------- GENERAL SETTINGS ----------
# DB_PATH = "bot.db"
# Neon (PostgreSQL) connection string, from .env
DATABASE_URL = _required("DATABASE_URL")

# Webhook settings. On Render these are set automatically (RENDER_EXTERNAL_URL, PORT).
# On your laptop RENDER_EXTERNAL_URL is empty, so the bot uses polling instead.
WEBHOOK_BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
PORT = int(os.getenv("PORT", "10000"))

CURRENCY = "ETB"
INVITE_LINK_DAYS = 3  # how long each invitation link stays valid

# ---------- PACKAGES (edit freely) ----------
# The key (BASIC, STANDARD, PREMIUM) is stored in the database, so don't rename keys
# after you have real students. You can change name, price and description any time.
PACKAGES = {
    "BASIC": {
        "name": "🥉 BASIC PACKAGE",
        "price": 250,
        "description": "\n✅ Descriptions of all 6 Freshman Courses",
    },
    "STANDARD": {
        "name": "🥈 STANDARD PACKAGE",
        "price": 300,
        "description": (
            "\n✅ Descriptions of all 6 Freshman Courses\n"
            "✅ COC Exam📝 Preparation"
        ),
    },
    "PREMIUM": {
        "name": "🥇 PREMIUM PACKAGE ",
        "price": 400,
        "description": (
            "\n✅Descriptions of all 6 Freshman Courses\n"
            "✅ COC Exam📝 Preparation\n"
            "✅ Aerospace Engineering✈️ Student Interview Preparation\n"
            "✅ In-Person👥 Sessions every 2 weeks"

        ),
    },
}

# ---------- PAYMENT DETAILS (placeholders: replace with your real details) ----------
PAYMENT = {
    "bank_name": "COMMERICIAL BANK OF ETHIOPIA",
    "account_name": "Kidus Simon Fuge",
    "account_number": "1000302238603",
}

# ---------- TEXTS (edit freely, plain text only) ----------
WELCOME_TEXT = (
    "Welcome! 👋\n\n"
    "We help university freshmen succeed with simple, recorded courses.\n"
    "Choose an option below to get started."
)

ABOUT_TEXT = (

" 🚀 Welcome to UNIlift Ethiopia! 🎓📚\n\n"
"📚 በ UNIlift Ethiopia የምታገኙት፦\n\n"
"📌 Brief Course Explanations — በኮርሶቻችሁ ውስጥ ያሉ እያንዳንዱ Topics በአጭሩና በቀላሉ ይብራራሉ።\n\n"
"🧮 Weekly Math & Physics Q&A — በየሳምንቱ የሂሳብ (Math) እና የፊዚክስ (Physics) ጥያቄና መልስ ዝግጅት ይኖራል። የማይገባችሁን ጠይቁ፣ አብረን እንማር!💡\n"
"📝 Previous Midterm & Final Exams — የባለፉት ዓመታት Midterm እና Final Exam ጥያቄዎች በTutor Program ውስጥ ይገኛሉ፣ ለፈተና ዝግጅታችሁም ይረዷችኋል።\n"
"🤝 Strong Study Community — ከሌሎች ተማሪዎች ጋር ተማማሩ፣ ሃሳብ ተለዋወጡ፣ አብራችሁ እደጉ!\n"
"✈️ Our Vision: የዩኒቨርሲቲ ተማሪዎችን በመሠረታዊ ትምህርቶች ማጠናከርና ወደ ኤሮስፔስ ምህንድስና ህልማቸው ማቅረብ።\n"
"🔥 UNIlift Ethiopia\n\n"
"Learn Smart. Rise Higher. 🚀||"
"አብረን እንማር፣ አብረን እናድግ፣ አብረን ከፍ እንበል! 💪🎓")

FAQ_TEXT = (
    "Frequently Asked Questions\n\n"
    "Q: How do I get access?\n"
    "A: Choose a package, pay, send us your payment screenshot, and we will send your private channel link after we verify the payment.\n\n"
    "Q: How long does approval take?\n"
    "A: We check payments manually, so it can take some time. Please be patient.\n\n"
    "Q: Can I share my invitation link?\n"
    "A: No. Your link is made for you only and works for one person.\n\n"
    "Q: My payment was rejected. What now?\n"
    "A: Just send a new, clear screenshot in this chat.\n\n"
    "[Edit these questions in config.py]"
)

CONTACT_TEXT = (
    "Contact Us\n\n"
    "Telegram: @unilift_ethiopia\n"
    "Phone: +251-717278178\n\n"
)