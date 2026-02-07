import logging
import threading
import time
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
TOKEN = "8501784414:AAH__8X0wawfff0tSIXvV4lhMixt91_aa1k" # သင့် Token ထည့်ပါ
THREAD_COUNT = 1          # PC ဆိုရင် 2 သို့မဟုတ် 3 ပြောင်းလို့ရ (ဖုန်းဆို 1 ပဲထားပါ)

# --- GLOBAL VARIABLES ---
user_tasks = {}

class TikTokTask:
    def __init__(self, chat_id, link, service_type, bot):
        self.chat_id = chat_id
        self.link = link
        self.service_type = service_type
        self.bot = bot
        self.total_sent = 0
        self.is_running = True

    def log(self, message):
        print(f"[{self.service_type}] {message}")

    async def send_update(self, message):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as e:
            self.log(f"Telegram sending error: {e}")

    def run_browser(self):
        chrome_options = Options()
        # chrome_options.add_argument("--headless") # မြန်ချင်ရင်/Server ပေါ်ဆို ဒါဖွင့်ပါ
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        
        # Page Load Strategy (မြန်အောင်လုပ်ခြင်း)
        chrome_options.page_load_strategy = 'eager' 

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            wait = WebDriverWait(driver, 20)

            driver.get("https://zefoy.com/")
            
            # Telegram သို့ အသိပေးခြင်း
            asyncio.run(self.send_update(f"🚀 {self.service_type} Automation စတင်ပါပြီ!\nကျေးဇူးပြု၍ Captcha ဖြေပေးပါ။"))

            # Captcha အတွက် အချိန်ပေးခြင်း
            time.sleep(20) 

            while self.is_running:
                try:
                    # Input Box ရှာခြင်း
                    search_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="search"]')))
                    search_input.clear()
                    search_input.send_keys(self.link)
                    
                    # Search Button
                    driver.find_element(By.XPATH, '//button[@type="submit"]').click()
                    time.sleep(3)
                    
                    # Service Button နှိပ်ခြင်း (Views/Likes)
                    # မှတ်ချက်: Zefoy ခလုတ်စာသားတွေက ပြောင်းလဲနိုင်ပါတယ်
                    button_text = "Views" if self.service_type == "views" else "Hearts"
                    service_btn = wait.until(EC.element_to_be_clickable((By.XPATH, f'//button[contains(text(), "{button_text}")]')))
                    service_btn.click()
                    
                    self.total_sent += 1000 # ခန့်မှန်းခြေ တစ်ခါပို့ရင် ၁၀၀၀
                    
                    # Success Message sending to Telegram
                    msg = f"✅ {self.service_type} ပို့ဆောင်ပြီးပါပြီ!\n📊 စုစုပေါင်း: {self.total_sent} (ခန့်မှန်း)"
                    asyncio.run(self.send_update(msg))
                    self.log(f"Success! Total: {self.total_sent}")

                    # Waiting for cooldown
                    # Timer ကို Element ကနေ ဖတ်နိုင်ရင် ပိုတိကျပါတယ်၊ လောလောဆယ် ၂ မိနစ်ထားထားပါတယ်
                    time.sleep(150)
                    
                    # Refresh for next round
                    driver.refresh()
                    
                except Exception as e:
                    self.log(f"Retrying... Error: {str(e)[:50]}")
                    driver.refresh()
                    time.sleep(10)
                    
        except Exception as e:
            self.log(f"Browser Crash: {e}")
        finally:
            driver.quit()

# --- TELEGRAM BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👁 Views (Fast)", callback_data='views'),
         InlineKeyboardButton("❤️ Likes", callback_data='likes')],
        [InlineKeyboardButton("🛑 Stop All", callback_data='stop')]
    ]
    await update.message.reply_text(
        '⚡️ **Turbo TikTok Bot** ⚡️\nဝန်ဆောင်မှု ရွေးချယ်ပါ:', 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    chat_id = update.effective_chat.id

    if choice == 'stop':
        if chat_id in user_tasks:
            user_tasks[chat_id].is_running = False
            del user_tasks[chat_id]
            await query.edit_message_text("🛑 Automation ကို ရပ်လိုက်ပါပြီ။")
        else:
            await query.edit_message_text("Running tasks မရှိပါ။")
        return

    context.user_data['service'] = choice
    await query.edit_message_text(f"🔥 {choice.upper()} mode active.\nLink ပို့ပေးပါ:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'service' not in context.user_data:
        await update.message.reply_text("Please select a service first using /start")
        return

    chat_id = update.effective_chat.id
    link = update.message.text
    service = context.user_data['service']

    # Task အသစ် ဖန်တီးခြင်း
    task = TikTokTask(chat_id, link, service, context.bot)
    user_tasks[chat_id] = task

    await update.message.reply_text(f"🚀 **Starting {THREAD_COUNT} Thread(s)...**\n\nTarget: {link}\nService: {service}")

    # Multi-threading Loop (မြန်စေချင်ရင် THREAD_COUNT ပြောင်းပါ)
    for _ in range(THREAD_COUNT):
        t = threading.Thread(target=task.run_browser)
        t.start()
        time.sleep(5) # Browser တွေ တပြိုင်တည်းမပွင့်အောင် ခဏခြား

# --- MAIN ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Turbo Bot is Running...")
    app.run_polling()
