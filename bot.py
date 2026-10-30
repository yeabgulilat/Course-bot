"""
Course registration bot. Run with:  python bot.py
"""
import logging
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database as db

# ---------- logging (console + bot.log file) ----------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)
# httpx logs full URLs, which contain your bot token. Keep it quiet.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("coursebot")


# ====================== helpers ======================

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("About Our Course", callback_data="menu:about")],
        [InlineKeyboardButton("View Packages", callback_data="menu:packages")],
        [InlineKeyboardButton("Frequently Asked Questions", callback_data="menu:faq")],
        [InlineKeyboardButton("Contact Us", callback_data="menu:contact")],
    ])


def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back to Menu", callback_data="menu:home")]])


def package_buttons():
    rows = [
        [InlineKeyboardButton(
            f"Choose {p['name']} - {p['price']} {config.CURRENCY}", callback_data=f"pkg:{key}")]
        for key, p in config.PACKAGES.items()
    ]
    rows.append([InlineKeyboardButton("⬅ Back to Menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def packages_text():
    parts = ["🚀 UNIlift Ethiopia — Our Packages 🎓\n","Choose the package that matches your goals! 📚🔥\n\n"]
    for p in config.PACKAGES.values():
        parts.append(f"{p['name']} - {p['price']} {config.CURRENCY}\n{p['description']}\n")
    parts.append("🎯 Ready to level up?\n📩 Choose your package and contact us to register!\n🔥 UNIlift Ethiopia\nThe Gateway to Medicine & Aerospace Engineering. 🚀")
    return "\n".join(parts)


def package_name(key):
    return config.PACKAGES.get(key, {}).get("name", key)


def username_text(username):
    return f"@{username}" if username else "(no username)"


def status_message(reg):
    """Friendly explanation for a student who already has a registration in progress."""
    status = reg["status"]
    if status in ("pending_review", "approving"):
        return "Your payment proof is being reviewed. We will message you here as soon as it is checked."
    if status == "approved":
        return ("Your payment was approved ✅\nYour private invitation link:\n"
                f"{reg['invite_link']}\n\nIf it has expired, please contact us.")
    if status == "joined":
        return "You are already registered and have joined the course channel ✅"
    return "Please use the menu to continue."


async def safe_send(context, chat_id, text, **kwargs):
    """Send a message; return True on success, False (and log) on failure."""
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return True
    except Exception:
        logger.exception("Could not send message to %s", chat_id)
        return False


# ====================== student: commands ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(config.WELCOME_TEXT, reply_markup=main_menu())


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tells a user their own Telegram ID (handy for setting ADMIN_IDS)."""
    await update.message.reply_text(f"Your Telegram ID is: {update.effective_user.id}")


# ====================== student: buttons ======================

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # stops the loading spinner on the button
    action, _, value = query.data.partition(":")
    user = query.from_user
    msg = query.message

    # ----- menu buttons -----
    if action == "menu":
        if value == "about":
            await msg.reply_text(config.ABOUT_TEXT, reply_markup=back_menu())
        elif value == "packages":
            await msg.reply_text(packages_text(), reply_markup=package_buttons())
        elif value == "faq":
            await msg.reply_text(config.FAQ_TEXT, reply_markup=back_menu())
        elif value == "contact":
            await msg.reply_text(config.CONTACT_TEXT, reply_markup=back_menu())
        else:
            await msg.reply_text(config.WELCOME_TEXT, reply_markup=main_menu())
        return

    # ----- student chose a package -----
    if action == "pkg":
        package = config.PACKAGES.get(value)
        if package is None:
            await msg.reply_text("Sorry, that package is not available. Please view the packages again.",
                                 reply_markup=back_menu())
            return
        busy = db.get_latest_for_user(user.id, ["pending_review", "approving", "approved", "joined"])
        if busy:
            await msg.reply_text(status_message(busy))
            return
        reg_id = db.create_registration(user.id, user.username, value, package["price"])
        logger.info("Registration %s created: user=%s package=%s", reg_id, user.id, value)
        await msg.reply_text(
            f"📘You selected: {package['name']}\n"
            f"💰 Price: {package['price']} {config.CURRENCY}\n"
            f"🆔 Registration ID: {reg_id}\n\n"
            "Would you like to continue to payment?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Continue to Payment", callback_data=f"pay:{reg_id}")],
                [InlineKeyboardButton("Choose a different package", callback_data="menu:packages")],
            ]),
        )
        return

    # ----- the remaining buttons need a registration id that belongs to this student -----
    try:
        reg = db.get_registration(int(value))
    except ValueError:
        reg = None
    if reg is None or reg["user_id"] != user.id:
        await msg.reply_text("Sorry, I couldn't find that registration. Please start again with /start.")
        return

    if action == "pay":
        if reg["status"] not in ("selected", "awaiting_proof", "rejected"):
            await msg.reply_text(status_message(reg))
            return
        pay = config.PAYMENT
        await msg.reply_text(
            "Payment Instructions\n\n"
            f"Package: {package_name(reg['package'])}\n"
            f"Bank: {pay['bank_name']}\n"
            f"Account name: {pay['account_name']}\n"
            f"Account number: {pay['account_number']}\n"
            f"Amount to pay: {reg['amount']} {config.CURRENCY}\n\n"
            "After you have paid, press the button below.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("I've Paid", callback_data=f"paid:{reg['id']}")]]),
        )
        return

    if action == "paid":
        if reg["status"] == "selected":
            db.set_status_if(reg["id"], "selected", "awaiting_proof")
        elif reg["status"] not in ("awaiting_proof", "rejected"):
            await msg.reply_text(status_message(reg))
            return
        await msg.reply_text(
            "Thank you! Please send a clear screenshot (photo) of your payment now.\n"
            "We will check it against our bank records before approving.")
        return


# ====================== student: payment proof ======================

async def on_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user

    # Which registration is waiting for a screenshot?
    reg = db.get_latest_for_user(user.id, ["awaiting_proof", "rejected"])
    if reg is None:
        other = db.get_latest_for_user(user.id, ["pending_review", "approving", "approved", "joined"])
        if other:
            await msg.reply_text(status_message(other))
        else:
            await msg.reply_text("Please choose a package and press \"I've Paid\" first. Send /start to begin.")
        return

    if msg.photo:
        file_id, file_type = msg.photo[-1].file_id, "photo"  # last item = biggest size
    else:
        file_id, file_type = msg.document.file_id, "document"

    # Atomic: only one submission can move this registration to pending_review
    if not db.save_proof(reg["id"], file_id, file_type):
        await msg.reply_text("We already received your proof for this registration.")
        return

    caption = (
        "💳 New payment proof\n\n"
        f"Registration ID: {reg['id']}\n"
        f"Student Telegram ID: {user.id}\n"
        f"Username: {username_text(user.username)}\n"
        f"Package: {package_name(reg['package'])}\n"
        f"Expected amount: {reg['amount']} {config.CURRENCY}\n\n"
        "⚠ A screenshot is NOT proof of payment. Check your real bank transactions before approving."
    )
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve Payment", callback_data=f"approve:{reg['id']}"),
        InlineKeyboardButton("❌ Reject Payment", callback_data=f"reject:{reg['id']}"),
    ]])

    try:
        if file_type == "photo":
            await context.bot.send_photo(config.ADMIN_CHAT_ID, file_id, caption=caption, reply_markup=buttons)
        else:
            await context.bot.send_document(config.ADMIN_CHAT_ID, file_id, caption=caption, reply_markup=buttons)
    except Exception:
        # Admin could not be reached: let the student try again later.
        logger.exception("Could not forward proof for registration %s to admin chat", reg["id"])
        db.set_status_if(reg["id"], "pending_review", "awaiting_proof")
        await msg.reply_text("Sorry, something went wrong on our side. Please send your screenshot again in a few minutes.")
        return

    logger.info("Proof received for registration %s", reg["id"])
    await msg.reply_text("Thank you! ✅ We received your screenshot. We will verify your payment and message you here.")


# ====================== admin: approve / reject ======================

async def mark_admin_message(query, note):
    """Remove the buttons from the admin message and add a result line."""
    try:
        await query.edit_message_caption(caption=(query.message.caption or "") + f"\n\n{note}", reply_markup=None)
    except Exception:
        logger.exception("Could not edit admin message")


async def on_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = query.from_user

    # SECURITY: checked on EVERY click, not just once.
    if admin.id not in config.ADMIN_IDS:
        logger.warning("Unauthorized approve/reject attempt by user %s", admin.id)
        await query.answer("You are not authorized to do this.", show_alert=True)
        return

    action, _, value = query.data.partition(":")
    reg = db.get_registration(int(value))
    if reg is None:
        await query.answer("Registration not found.", show_alert=True)
        return
    reg_id = reg["id"]
    who = f"{admin.full_name} ({admin.id})"

    # ---------- REJECT ----------
    if action == "reject":
        if not db.set_status_if(reg_id, "pending_review", "rejected", decided_by=admin.id):
            current = db.get_registration(reg_id)["status"]
            await query.answer(f"Already processed (status: {current}).", show_alert=True)
            return
        await query.answer("Payment rejected.")
        logger.info("Registration %s rejected by %s", reg_id, admin.id)
        await mark_admin_message(query, f"❌ REJECTED by {who}")
        await safe_send(
            context, reg["user_id"],
            "Unfortunately we could not verify your payment. ❌\n\n"
            "Please check your transfer and send a new, clear screenshot of the payment in this chat. "
            "If you need help, use /start and press Contact Us.")
        return

    # ---------- APPROVE ----------
    # Step 1: lock the registration so nobody else can approve it at the same time.
    if not db.set_status_if(reg_id, "pending_review", "approving", decided_by=admin.id):
        current = db.get_registration(reg_id)["status"]
        await query.answer(f"Already processed (status: {current}).", show_alert=True)
        return

    # Step 2: create a personal invitation link (one person, expires).
    try:
        expires = datetime.now(timezone.utc) + timedelta(days=config.INVITE_LINK_DAYS)
        link_obj = await context.bot.create_chat_invite_link(
            chat_id=config.CHANNEL_ID,
            name=f"reg-{reg_id}",
            expire_date=expires,
            member_limit=1,
        )
        link = link_obj.invite_link
    except Exception:
        logger.exception("Could not create invite link for registration %s", reg_id)
        db.set_status_if(reg_id, "approving", "pending_review")  # unlock so you can retry
        await query.answer(
            "Could not create the invite link. Is the bot an admin of the channel with the "
            "'Invite users' permission? Check CHANNEL_ID. You can press Approve again.",
            show_alert=True)
        return

    # Step 3: save and tell everyone.
    db.set_status_if(reg_id, "approving", "approved", decided_by=admin.id, invite_link=link)
    await query.answer("Payment approved.")
    logger.info("Registration %s approved by %s", reg_id, admin.id)
    await mark_admin_message(query, f"✅ APPROVED by {who}")

    sent = await safe_send(
        context, reg["user_id"],
        "Your payment is approved! 🎉\n\n"
        f"Here is your private invitation link:\n{link}\n\n"
        f"It works for ONE person only and expires in {config.INVITE_LINK_DAYS} days. "
        "Please do not share it. Tap it now to join the course channel.")
    if not sent:
        await query.message.reply_text(
            f"⚠ Could not message the student (ID {reg['user_id']}). "
            f"Send this link to them manually:\n{link}")


# ====================== channel: detect joins ======================

async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    change = update.chat_member
    if change.chat.id != config.CHANNEL_ID:
        return  # some other chat, ignore

    old, new = change.old_chat_member.status, change.new_chat_member.status
    if not (new == ChatMemberStatus.MEMBER and old in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)):
        return  # not a new join

    joined_user = change.new_chat_member.user
    link_used = change.invite_link.invite_link if change.invite_link else None
    reg = db.get_latest_for_user(joined_user.id, ["approved"])

    if reg is None:
        # Someone joined who has no approved registration. Maybe a forwarded link?
        owner = db.find_by_invite_link(link_used) if link_used else None
        if owner:
            await safe_send(
                context, config.ADMIN_CHAT_ID,
                f"⚠ User {joined_user.id} ({username_text(joined_user.username)}) joined using the link "
                f"made for registration {owner['id']} (student {owner['user_id']}). The link may have been shared.")
        logger.info("User %s joined the channel without an approved registration", joined_user.id)
        return

    if db.set_status_if(reg["id"], "approved", "joined"):
        logger.info("Registration %s complete: user %s joined the channel", reg["id"], joined_user.id)
        await safe_send(context, reg["user_id"], "Welcome to the course channel! 🎉 Your registration is complete.")
        await safe_send(context, config.ADMIN_CHAT_ID,
                        f"✅ Registration {reg['id']} complete: student {joined_user.id} joined the channel.")


# ====================== fallbacks ======================

async def on_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Any other private message (random text, stickers, non-image files...)."""
    await update.message.reply_text(
        "Sorry, I didn't understand that. Please use the buttons from /start.\n"
        "If you are sending a payment screenshot, send it as a photo or image file.")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat and update.effective_chat.type == "private":
        await safe_send(context, update.effective_chat.id,
                        "Sorry, something went wrong. Please try again, or send /start.")


# ====================== start the bot ======================

def main():
    db.init_db()
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("myid", myid, filters=filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(menu|pkg|pay|paid):"))
    app.add_handler(CallbackQueryHandler(on_admin_decision, pattern=r"^(approve|reject):\d+$"))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.IMAGE), on_proof))
    app.add_handler(ChatMemberHandler(on_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, on_other))
    app.add_error_handler(on_error)

    if config.WEBHOOK_BASE_URL:
        # ---- Running on Render: Telegram sends updates to our web address ----
        if not config.WEBHOOK_SECRET:
            raise SystemExit("Missing WEBHOOK_SECRET. Add it to the Render environment variables.")
        logger.info("Starting in WEBHOOK mode on port %s", config.PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path="webhook",
            webhook_url=f"{config.WEBHOOK_BASE_URL}/webhook",
            secret_token=config.WEBHOOK_SECRET,  # Telegram sends this; others are rejected
            allowed_updates=Update.ALL_TYPES,    # needed for channel join detection
        )
    else:
        # ---- Running on your laptop: the bot asks Telegram for updates ----
        logger.info("Starting in POLLING mode (local)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()