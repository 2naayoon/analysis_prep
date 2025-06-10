import asyncio
from weather_server import get_weather_alerts, get_weather_forecast, mcp

async def test_tools():
    alerts = await get_weather_alerts("CA")
    print("캘리포니아 날씨 경보:", alerts)

    forecast = await get_weather_forecast(37.7749, -122.4194)
    print("샌프란시스코 날씨 예보:", forecast)

if __name__ == "__main__":
    asyncio.run(test_tools())
