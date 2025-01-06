from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")

TRAVELPOUT_API_KEY = ""


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/calculate_flight_time")
async def calculate_flight_time(
        request: Request,
        from_city: str = Form(...),  # IATA код аэропорта вылета
        to_city: str = Form(...),  # IATA код аэропорта назначения
        departure_date: str = Form(...)  # дата вылета в формате YYYY-MM-DD
):
    flight_info = await get_flight_info(from_city, to_city, departure_date)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "from_city": from_city,
        "to_city": to_city,
        "flight_info": flight_info
    })


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
            return "Не удалось получить данные о времени полета."

        # Первый рейс
        flight_data = data['data'][0]
        flight_duration = flight_data.get('duration', None)
        price = flight_data.get('price', "Неизвестная цена")
        airline = flight_data.get('airline', "Неизвестная авиакомпания")
        departure_at = flight_data.get('departure_at', "Неизвестное время вылета")

        return {
            "duration": flight_duration,
            "price": price,
            "airline": airline,
            "departure_at": departure_at
        }