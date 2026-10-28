import os
import asyncio
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType
from aiogram.filters import CommandStart
from google import genai
from google.genai import types

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
TELEGRAM_BOT_TOKEN = "9211767291:AAE6yNL_C9S4sz5V5h-TsI62DFvDBXupi8I"
GOOGLE_API_KEY = "AQ.Ab8RN6Jhk3LeUjqpI_xkXaLjKQlnEeq5ffxgmgG1o15UsOSOaw"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GOOGLE_API_KEY)

# ==========================================
# ФЕЙКОВЫЙ СЕРВЕР ДЛЯ ОБХОДА ПОРТА RENDER
# ==========================================
def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Фейковый веб-сервер запущен на порту {port}")
    server.serve_forever()

# ==========================================
# ИНСТРУКЦИЯ ДЛЯ GEMINI (Системный промпт)
# ==========================================
SYSTEM_INSTRUCTION = """
Ты — строгий и опытный внутренний аудитор кирпичного завода "Енки" (Казахстан, Кокшетау). 
Твоя задача — анализировать цены закупок, которые предоставляет снабженец, и выявлять факты завышения стоимости материалов и оборудования.

Контекст завода:
- Завод производит высококачественный облицовочный кирпич (завод ENKI).
- Основное сырье: глина, песок, технологические добавки, упаковочные материалы (поддоны, термоусадочная пленка), запчасти для оборудования (пресс-формы, конвейерные ленты, редукторы), ГСМ, уголь/газ для обжиговых печей.

Инструкция:
Изучи переданный список товаров и их цен. Сравни указанные цены со своими знаниями о среднерыночных ценах в данном регионе (Казахстан/СНГ) для крупных производств.
Выдай красивый текстовый отчет. Напиши по каждой позиции, завышена ли цена, какая средняя цена на рынке и краткий комментарий, почему это так. В конце сделай общий вывод.
Выдавай ответ на русском языке. Используй эмодзи для наглядности (например, ⚠️ если завышено, ✅ если в норме).
"""

# ==========================================
# ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ
# ==========================================
def analyze_prices_with_gemini(input_text: str) -> str:
    """Отправляет данные в Gemini напрямую и возвращает текстовый ответ."""
    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash', # Стабильная и доступная базовая модель
            contents=f"Проанализируй следующие данные закупок завода ENKI:\n\n{input_text}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
            ),
        )
        return response.text
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return None

# Хэндлер на команду /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🏭 **Добро пожаловать в систему аудита закупок кирпичного завода ENKI!**\n\n"
        "Отправьте мне текст со списком материалов и цен (например: *'HDMI кабель - 9000 тг за штуку'*), "
        "и я мгновенно проверю, не завысил ли снабженец стоимость."
    )

# Хэндлер на текстовые сообщения
@dp.message(F.content_type == ContentType.TEXT)
async def handle_text_audit(message: Message):
    status_msg = await message.answer("🔄 *Анализирую цены и проверяю рынок... Пожалуйста, подождите.*", parse_mode="Markdown")
    
    report_text = analyze_prices_with_gemini(message.text)
    
    if not report_text:
        await status_msg.edit_text("❌ Не удалось получить ответ от ИИ. Попробуйте отправить запрос еще раз.")
        return

    await status_msg.delete()
    # Отправляем напрямую готовый красивый текст от нейросети
    await message.answer(report_text)

# ==========================================
# ЗАПУСК БОТА
# ==========================================
async def main():
    server_thread = Thread(target=run_health_server, daemon=True)
    server_thread.start()
    
    print("Запуск polling Telegram бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

