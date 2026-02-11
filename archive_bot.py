import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telethon import TelegramClient, events
import os

# ----------------------------------------------------------------------
# تنظیمات اولیه و بارگذاری متغیرهای محیطی
# ----------------------------------------------------------------------

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغیرهای محیطی
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_NAME = 'archive_session' # نام فایل سشن تلثون

# دیکشنری برای ذخیره پیام‌های انتخاب شده
# {telegram_user_id: {'source_channel_id': [message_ids]}}
selected_messages = {}

# ----------------------------------------------------------------------
# تنظیمات Telethon (برای دسترسی به کانال‌ها و پیام‌ها)
# ----------------------------------------------------------------------
try:
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    client.start(bot_token=BOT_TOKEN)
    logger.info("Telethon Client started successfully.")
except Exception as e:
    logger.error(f"Error starting Telethon Client: {e}")
    client = None

# ----------------------------------------------------------------------
# توابع هندلر تلگرام (Telegram Bot Handler Functions)
# ----------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هنگامی که دستور /start ارسال می شود، پیامی خوش آمدگویی ارسال می کند."""
    user_id = update.effective_user.id
    
    # اطمینان از وجود کلید برای کاربر فعلی
    if user_id not in selected_messages:
        selected_messages[user_id] = {}

    keyboard = [
        [InlineKeyboardButton("راهنما", callback_data='help')],
        [InlineKeyboardButton("نحوه استفاده", callback_data='usage')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'سلام {update.effective_user.first_name}!\n'
        'من ربات آرشیوکننده شما هستم. برای شروع، آیدی کانالی که می‌خواهید از آن کپی کنید را برایم بفرستید.',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هنگامی که دستور /help ارسال می شود، راهنما را نمایش می دهد."""
    help_text = (
        "🤖 **راهنمای ربات آرشیوکننده:**\n\n"
        "هدف این ربات، آرشیو کردن پیام‌ها از یک کانال منبع به یک کانال مقصد شماست.\n\n"
        "**مراحل کار:**\n"
        "1. **ارسال آیدی منبع:** ابتدا آیدی کانال یا گروهی که می‌خواهید پیام‌ها را از آن کپی کنید، ارسال کنید (مثال: `-1001234567890`). **توجه:** ربات باید عضو آن کانال باشد یا کانال عمومی باشد.\n"
        "2. **انتخاب پیام:** پس از دریافت تأییدیه کانال، هر پیامی که می‌خواهید آرشیو شود را **به این ربات فوروارد کنید**.\n"
        "3. **تأیید مقصد:** پس از انتخاب چند پیام، دستور `/archive` را ارسال کنید تا مقصد نهایی را مشخص کنید.\n"
        "4. **اجرای آرشیو:** ربات پیام‌ها را به کانال مقصد شما منتقل می‌کند."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندل کردن پیام‌های دریافتی (انتخاب کانال منبع یا پیام‌ها برای آرشیو)."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id not in selected_messages:
        selected_messages[user_id] = {}

    # حالت 1: کاربر در حال وارد کردن آیدی کانال منبع است
    if 'source_channel_id' not in selected_messages[user_id]:
        
        # بررسی می‌کنیم که ورودی عددی (آیدی کانال) باشد
        if message.text and message.text.startswith(('-100', '-1', '@')):
            source_id_raw = message.text
            
            # تلاش برای دریافت اطلاعات کانال منبع با استفاده از Telethon
            try:
                # برای کانال‌های خصوصی، باید ادمین باشید یا ربات عضو باشد
                entity = await client.get_entity(source_id_raw)
                
                # آیدی کانال را به فرمت عددی ذخیره می‌کنیم (مثبت برای کانال مقصد نیست)
                # Telethon خودش آیدی را به فرمت مناسب مدیریت می‌کند، اما ما رشته را ذخیره می‌کنیم
                selected_messages[user_id]['source_channel_id'] = source_id_raw
                
                await message.reply_text(
                    f"✅ کانال منبع با آیدی/نام `{source_id_raw}` تأیید شد.\n"
                    "حالا لطفاً **پیام‌هایی که می‌خواهید آرشیو کنید را به این ربات فوروارد کنید**."
                )
            except Exception as e:
                logger.error(f"Error getting entity for {source_id_raw}: {e}")
                await message.reply_text(
                    "❌ نتوانستم کانال را پیدا کنم. لطفاً آیدی را با دقت (مثلا `-1001234567890` یا آیدی عمومی) وارد کنید."
                )
        else:
            await message.reply_text(
                "❌ لطفاً ابتدا آیدی کانال منبع را وارد کنید (مثال: `-1001234567890`) یا دستور `/help` را بزنید."
            )
            
    # حالت 2: کاربر پیام‌هایی را برای آرشیو فوروارد می‌کند
    elif message.forward_from_chat and 'source_channel_id' in selected_messages[user_id]:
        
        source_id = selected_messages[user_id]['source_channel_id']
        
        # اگر این پیام از کانال منبع مورد نظر ماست
        try:
            # دریافت اطلاعات کانال منبع برای مقایسه نهایی (اختیاری)
            source_entity = await client.get_entity(source_id)
            
            # اگر کانال فوروارد شده با کانال منبع مطابقت دارد
            # در اینجا نیاز به مقایسه دقیق تری هست که ممکن است پیچیده باشد.
            # ساده‌ترین راه این است که هر پیام فوروارد شده را ذخیره کنیم
            
            if user_id not in selected_messages[user_id]:
                selected_messages[user_id]['messages_to_forward'] = []
                
            # ذخیره اطلاعات پیام فوروارد شده
            message_data = {
                'message_id': message.forward_from_message_id,
                'chat_id': message.forward_from_chat.id, # این شناسه چت منبع است
                'message_object': message # برای دسترسی کامل به محتوا در صورت لزوم
            }
            selected_messages[user_id]['messages_to_forward'].append(message_data)
            
            count = len(selected_messages[user_id]['messages_to_forward'])
            await message.reply_text(
                f"✅ پیام شماره {count} از منبع ذخیره شد.\n"
                "برای اتمام انتخاب، دستور `/archive` را ارسال کنید."
            )
            
        except Exception as e:
            logger.warning(f"Could not verify source chat for forwarded message: {e}")
            # اگر نتوانستیم تأیید کنیم، پیام را باز هم ذخیره می‌کنیم و به کاربر اطلاع می‌دهیم
            if user_id not in selected_messages[user_id]:
                selected_messages[user_id]['messages_to_forward'] = []
            
            message_data = {
                'message_id': message.forward_from_message_id,
                'chat_id': message.forward_from_chat.id,
                'message_object': message
            }
            selected_messages[user_id]['messages_to_forward'].append(message_data)
            
            count = len(selected_messages[user_id]['messages_to_forward'])
            await message.reply_text(
                f"⚠️ پیام شماره {count} ذخیره شد (تأیید منبع کمی مشکل داشت).\n"
                "برای اتمام انتخاب، دستور `/archive` را ارسال کنید."
            )
            
    # حالت 3: کاربر دستور آرشیو را ارسال کرده است
    elif message.text and message.text.strip().lower() == '/archive':
        await archive_command(update, context)
        
    else:
        await message.reply_text(
            "لطفاً یا آیدی کانال منبع را ارسال کنید، یا پیام‌ها را فوروارد کنید، یا از دستور `/archive` استفاده کنید."
        )


async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند آرشیو کردن پیام‌های انتخاب شده به کانال مقصد."""
    user_id = update.effective_user.id
    
    if user_id not in selected_messages or not selected_messages[user_id].get('messages_to_forward'):
        await update.message.reply_text(
            "❌ لیستی برای آرشیو پیدا نشد. لطفاً ابتدا پیام‌ها را انتخاب کنید و سپس `/archive` را بزنید."
        )
        return
        
    # مرحله اول: دریافت کانال مقصد از کاربر
    if 'destination_channel_id' not in selected_messages[user_id]:
        
        keyboard = [
            [InlineKeyboardButton("لغو عملیات", callback_data='cancel_archive')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "لطفاً **آیدی کانال مقصد** (جایی که می‌خواهید پیام‌ها کپی شوند) را ارسال کنید. "
            "این آیدی باید مانند کانال منبع باشد (مثال: `-100987654321`).",
            reply_markup=reply_markup
        )
        # وضعیت را به انتظار برای آیدی مقصد تغییر می‌دهیم
        selected_messages[user_id]['awaiting_destination'] = True
        return

    # مرحله دوم: اجرای آرشیو (اگر آیدی مقصد قبلاً تنظیم شده باشد)
    
    messages_to_forward = selected_messages[user_id]['messages_to_forward']
    source_id = selected_messages[user_id]['source_channel_id']
    destination_id = selected_messages[user_id]['destination_channel_id']
    
    await update.message.reply_text(f"⏳ در حال آرشیو کردن {len(messages_to_forward)} پیام به کانال مقصد...")

    success_count = 0
    failure_count = 0
    
    try:
        # دریافت شناسه منبع نهایی (Entity)
        source_entity = await client.get_entity(source_id)
        
        # دریافت شناسه مقصد نهایی (Entity)
        destination_entity = await client.get_entity(destination_id)
        
        for msg_data in messages_to_forward:
            try:
                # استفاده از متد 'Forward Messages' تلثون برای کپی کردن پیام
                # اگر پیام اصلی دارای فایل است، با این روش فایل اصلی فوروارد می‌شود.
                await client.forward_messages(
                    peer=destination_entity,
                    from_peer=source_entity,
                    ids=msg_data['message_id']
                )
                success_count += 1
                logger.info(f"Successfully forwarded message {msg_data['message_id']} for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to forward message {msg_data['message_id']}: {e}")
                failure_count += 1
                
    except Exception as e:
        logger.critical(f"Critical error during entity resolution or main loop: {e}")
        await update.message.reply_text(
            f"❌ یک خطای سیستمی جدی رخ داد: {e}.\nعملیات آرشیو متوقف شد."
        )
        return

    # پاکسازی پس از اتمام عملیات
    selected_messages[user_id] = {'source_channel_id': source_id, 'destination_channel_id': destination_id} # برای اینکه منبع و مقصد حفظ شود
    
    await update.message.reply_text(
        f"✅ **عملیات آرشیو به پایان رسید!**\n"
        f"✅ تعداد پیام‌های موفق: {success_count}\n"
        f"❌ تعداد پیام‌های ناموفق: {failure_count}\n\n"
        f"شما می‌توانید دوباره پیام‌های جدیدی را انتخاب کنید."
    )


async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندل کردن پاسخ‌های کلیک شده روی دکمه‌های اینلاین."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in selected_messages:
        await query.edit_message_text("خطای سشن. لطفاً دوباره /start را بزنید.")
        return
        
    current_state = selected_messages[user_id]

    if data == 'help':
        help_text = (
            "🤖 **راهنمای ربات آرشیوکننده:**\n\n"
            "1. ابتدا آیدی کانال منبع را بفرستید.\n"
            "2. پیام‌های مورد نظر را به این ربات فوروارد کنید.\n"
            "3. دستور `/archive` را بفرستید.\n"
            "4. آیدی کانال مقصد را بفرستید."
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
        
    elif data == 'usage':
        usage_text = (
            "💡 **نحوه استفاده دقیق:**\n\n"
            "**مثال ۱: تنظیم منبع**\n"
            "شما: `-100123456789`\n"
            "ربات: کانال تأیید شد. پیام‌ها را فوروارد کنید.\n\n"
            "**مثال ۲: انتخاب پیام**\n"
            "شما: [فوروارد کردن پیام X از کانال منبع]\n"
            "ربات: پیام شماره ۱ ذخیره شد."
        )
        await query.edit_message_text(usage_text)

    elif data == 'cancel_archive':
        if 'awaiting_destination' in current_state:
            del current_state['awaiting_destination']
            
        if 'messages_to_forward' in current_state:
             del current_state['messages_to_forward']
             
        await query.edit_message_text("عملیات آرشیو لغو شد. برای شروع مجدد دستور /start را بزنید.")

    # برای حالتی که کاربر مستقیم آیدی مقصد را فرستاده باشد و قبلا در handle_message هندل نشده باشد:
    elif data.startswith(('-100', '-1')):
        destination_id = data
        current_state['destination_channel_id'] = destination_id
        del current_state['awaiting_destination']
        
        # فراخوانی archive_command برای ادامه فرآیند
        update.callback_query.message.text = '/archive' # شبیه سازی ارسال دستور /archive
        await archive_command(update, context)


async def main() -> None:
    """اجرای ربات."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in environment variables.")
        print("خطا: BOT_TOKEN در متغیرهای محیطی تعریف نشده است.")
        return

    # تنظیم Application
    application = Application.builder().token(BOT_TOKEN).build()

    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("archive", archive_command))
    
    # هندلر اصلی برای پیام‌های متنی و فوروارد شده
    application.add_handler(MessageHandler(filters.TEXT | filters.FORWARD, handle_message))
    
    # هندلر برای کلیک‌های اینلاین
    application.add_handler(CallbackQueryHandler(callback_query))

    # اجرای ربات
    logger.info("Bot is starting polling...")
    # این خط باعث اجرای نامحدود ربات می‌شود
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # اطمینان از اینکه Telethon هم شروع به کار می‌کند
    try:
        # چون client.start() در ابتدا فراخوانی شده، اینجا فقط منتظر می‌مانیم
        # برای اجرای در محیط‌های مختلف ممکن است نیاز به تغییر باشد
        # اما در محیط‌های مانند Render یا سرور، run_polling کافی است.
        pass
    except Exception as e:
        logger.error(f"Error during main execution setup: {e}")
        
    main()
