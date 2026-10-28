import os
import asyncio
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType
from aiogram.filters import CommandStart
from groq import Groq


# ==========================================
# КОНФИГУРАЦИЯ (Ключи полностью прописаны)
# ==========================================
TELEGRAM_BOT_TOKEN = "9211767291:AAE6yNL_C9S4sz5V5h-TsI62DFvDBXupi8I"
GROQ_API_KEY = "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"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# ==========================================
# ФЕЙКОВЫЙ СЕРВЕР ДЛЯ ОБХОДА ПОРТА RENDER
# ==========================================
def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Фейковый веб-сервер запущен на порту {port}")
    server.serve_forever()

# ==========================================
# ИНСТРУКЦИЯ ДЛЯ ИИ LLAMA (Системный промпт)
# ==========================================
SYSTEM_INSTRUCTION = """
Ты — строгий и опытный внутренний аудитор кирпичного завода "Енки" (Казахстан, Кокшетау). 
Твоя задача — анализировать цены закупок, которые предоставляет снабженец, и выявлять факты завышения стоимости материалов и оборудования.

Контекст завода:
- Завод производит высококачественный облицовочный кирпич (завод ENKI).
- Основное сырье: глина, песок, технологические добавки, упаковочные материалы (поддоны, термоусадочная пленка), запчасти для оборудования (пресс-формы, конвейерные ленты, редукторы), ГСМ, уголь/газ для обжиговых печей.

Инструкция:
Изучи переданный список товаров и их цен. Сравни указанные цены со своими знаниями о среднерыночных ценах в данном регионе (Казахстан/СНГ) для крупных производств.
Выдай красивый, чёткий текстовый отчет на русском языке. 
Напиши по каждой позиции, завышена ли цена, какая средняя цена на рынке в тенге (тг) и краткий комментарий, почему это так. В конце сделай общий аналитический вывод.
Используй эмодзи для наглядности (например, ⚠️ если цена завышена, ✅ если в норме).
"""

# ==========================================
# ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ ЧЕРЕЗ GROQ
# ==========================================
def analyze_prices_with_groq(input_text: str) -> str:
    """Отправляет данные в Groq API (Llama 3.1) и возвращает текстовый отчет."""
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION
                },
                {
                    "role": "user",
                    "content": f"Проанализируй следующие данные закупок завода ENKI:\n\n{input_text}"
                }
            ],
            model="llama-3.1-70b-versatile",
            temperature=0.2,
        )
        return chat_completion.choices.message.content
    except Exception as e:
        print(f"Ошибка Groq API: {e}")
        return None

# Хэндлер на команду /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🏭 **Добро пожаловать в систему аудита закупок кирпичного завода ENKI на движке Groq!**\n\n"
        "Отправьте мне текст со списком материалов и цен (например: *'HDMI кабель - 9000 тг за штуку'*), "
        "и я мгновенно проверю, не завысил ли снабженец стоимость."
    )

# Хэндлер на текстовые сообщения
@dp.message(F.content_type == ContentType.TEXT)
async def handle_text_audit(message: Message):
    status_msg = await message.answer("🔄 *Связываюсь со сверхбыстрыми серверами Groq, проверяю рынок... Пожалуйста, подождите.*", parse_mode="Markdown")
    
    report_text = analyze_prices_with_groq(message.text)
    
    if not report_text:
        await status_msg.edit_text("❌ Не удалось получить ответ от аналитического сервера. Попробуйте еще раз.")
        return

    await status_msg.delete()
    await message.answer(report_text)

# ==========================================
# ЗАПУСК БОТА
# ==========================================
async def main():
    server_thread = Thread(target=run_health_server, daemon=True)
    server_thread.start()
    
    print("Запуск Telegram бота через Groq...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
