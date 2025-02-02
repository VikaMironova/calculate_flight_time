import respx
from httpx import Response
from fastapi.testclient import TestClient
from main import app
from config import TRAVELPOUT_API_KEY

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "<html" in response.text.lower()

@respx.mock
def test_calculate_flight_time_success():
    query = "Moscow%20St%20Petersburg"
    iata_url = f"https://www.travelpayouts.com/widgets_suggest_params?q={query}"
    respx.get(iata_url).mock(return_value=Response(
        200,
        json={
            "origin": {"iata": "MOW"},
            "destination": {"iata": "LED"}
        }
    ))

    flight_url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    departure_date = "2023-10-15"
    flight_data = {
        "data": [{
            "duration": 300,
            "price": 100,
            "airline": "TestAir",
            "departure_at": "2023-10-15T10:00:00Z"
        }]
    }
    respx.get(flight_url).mock(return_value=Response(200, json=flight_data))

    response = client.post("/calculate_flight_time", data={
        "from_city": "Moscow",
        "to_city": "St Petersburg",
        "departure_date": departure_date
    })

    assert response.status_code == 200
    response_text = response.text
    assert "TestAir" in response_text
    assert "100" in response_text
    assert "ч. по МСК" in response_text

@respx.mock
def test_calculate_flight_time_iata_error():
    query = "InvalidCity%20AnotherCity"
    iata_url = f"https://www.travelpayouts.com/widgets_suggest_params?q={query}"
    respx.get(iata_url).mock(return_value=Response(200, json={}))

    response = client.post("/calculate_flight_time", data={
        "from_city": "InvalidCity",
        "to_city": "AnotherCity",
        "departure_date": "2023-10-15"
    })
    assert response.status_code == 200
    assert "Не удалось найти IATA-коды" in response.text