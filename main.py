from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
from starlette.staticfiles import StaticFiles

from config import TRAVELPOUT_API_KEY # Укажите ваш API ключ TravelPayouts
from datetime import datetime, timezone, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/calculate_flight_time")
async def calculate_flight_time(
        request: Request,
        from_city: str = Form(...),  # Название города вылета
        to_city: str = Form(...),  # Название города назначения
        departure_date: str = Form(...)  # Дата вылета
):
    # Формируем строку для поиска IATA-кодов
    query = f"{from_city.strip()}%20{to_city.strip()}"

    # Получаем IATA коды
    iata_codes = await get_iata_codes(query)

    if not iata_codes or len(iata_codes) != 2:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "error": "Не удалось найти IATA-коды для указанных городов."
        })

    origin_iata, destination_iata = iata_codes

    # Получаем информацию о рейсе
    flight_info = await get_flight_info(origin_iata, destination_iata, departure_date)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "flight_info": flight_info
    })


async def get_iata_codes(query: str):
    async with httpx.AsyncClient() as client:
        # Кодируем строку запроса
        encoded_query = query.replace(" ", "%20")
        response = await client.get(f"https://www.travelpayouts.com/widgets_suggest_params?q={encoded_query}")

        print(
            f"Запрос к API IATA: https://www.travelpayouts.com/widgets_suggest_params?q={encoded_query}")  # Для отладки

        if response.status_code == 200:
            data = response.json()
            origin_iata = data.get('origin', {}).get('iata')
            destination_iata = data.get('destination', {}).get('iata')
            return origin_iata, destination_iata  # Возвращаем IATA-коды

    return None


async def get_flight_info(from_city: str, to_city: str, departure_date: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.travelpayouts.com/aviasales/v3/prices_for_dates",
            params={
                "origin": from_city,  # IATA код аэропорта вылета
                "destination": to_city,  # IATA код аэропорта назначения
                "departure_at": departure_date,  # Дата вылета
                "one_way": "true",  # Один рейс
                "token": TRAVELPOUT_API_KEY
            }
        )

        data = response.json()

        if response.status_code != 200 or not data.get('data'):
            return None

        # Берем первый рейс
        flight_data = data['data'][0]
        flight_duration = flight_data.get('duration', None)
        price = flight_data.get('price', "Неизвестная цена")
        airline = flight_data.get('airline', "Неизвестная авиакомпания")
        departure_at_str = flight_data.get('departure_at', "Неизвестное время вылета")

        # Преобразуем строку в объект datetime
        departure_at = datetime.fromisoformat(departure_at_str.replace("Z", "+00:00"))

        # Форматируем дату и время
        formatted_departure_at = "* " + departure_at.strftime("%d/%m/%Y") + " " + departure_at.strftime("%H:%M") + " ч. по МСК *"

        return {
            "duration": flight_duration,
            "price": price,
            "airline": airline,
            "departure_at": formatted_departure_at  # Используем отформатированное время
        }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7777)