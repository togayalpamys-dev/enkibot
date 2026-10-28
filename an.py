import os
import asyncio
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType
from aiogram.filters import CommandStart
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

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
    # Render автоматически передает номер порта в переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Фейковый веб-сервер запущен на порту {port}")
    server.serve_forever()

# ==========================================
# СТРУКТУРА ДАННЫХ И ПРОМПТ
# ==========================================
class ItemAnalysis(BaseModel):
    item_name: str = Field(description="Название позиции")
    purchase_price: float = Field(description="Заявленная цена")
    market_average_price: float = Field(description="Среднерыночная цена")
    is_overpriced: bool = Field(description="Завышена ли")
    deviation_percent: float = Field(description="Процент завышения")
    comment: str = Field(description="Комментарий")

class AuditReport(BaseModel):
    items: list[ItemAnalysis]
    summary: str = Field(description="Общий вывод")

SYSTEM_INSTRUCTION = """
Ты — строгий внутренний аудитор кирпичного завода "Енки" (Казахстан, Кокшетау). 
Твоя задача — анализировать цены закупок и выявлять факты завышения стоимости.
Выдай результат строго в формате JSON по схеме AuditReport.
"""

def analyze_prices_with_gemini(input_text: str) -> AuditReport:
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Проанализируй цены:\n\n{input_text}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=AuditReport,
                temperature=0.2,
            ),
        )
        return AuditReport.model_validate_json(response.text)
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return None

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("🏭 Система аудита завода ENKI успешно запущена в облаке Render! Отправьте список материалов и цен.")

@dp.message(F.content_type == ContentType.TEXT)
async def handle_text_audit(message: Message):
    status_msg = await message.answer("🔄 Анализирую рынок, сверяю базы данных региона...")
    report: AuditReport = analyze_prices_with_gemini(message.text)
    
    if not report:
        await status_msg.edit_text("❌ Ошибка обработки данных искусственным интеллектом.")
        return

    res = "📊 **РЕЗУЛЬТАТЫ ПРОВЕРКИ ЗАКУПКИ:**\n\n"
    for item in report.items:
        emoji = "⚠️" if item.is_overpriced else "✅"
        res += (f"{emoji} **{item.item_name}**\n"
                f" ├ Заявлено снабженцем: {item.purchase_price} тг\n"
                f" ├ Среднерыночная цена: {item.market_average_price} тг\n"
                f" ├ Отклонение: {item.deviation_percent}%\n"
                f" └ Анализ аудитора: {item.comment}\n\n")
    
    res += f"📝 **Итоговое заключение:** {report.summary}"
    await status_msg.delete()
    await message.answer(res)

async def main():
    # Запускаем веб-сервер в отдельном потоке, чтобы он не мешал боту слушать чат
    server_thread = Thread(target=run_health_server, daemon=True)
    server_thread.start()
    
    # Запуск самого бота
    print("Запуск polling Telegram бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
