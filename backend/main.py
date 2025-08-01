from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import time

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Weather Dashboard API",
    description="Beautiful Weather API with monitoring",
    version="1.0.0"
)

# CORS middleware for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
weather_requests = Counter('weather_requests_total', 'Total weather requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')

# Pydantic models
class WeatherResponse(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: int
    wind_speed: float
    icon: str
    country: str

class ErrorResponse(BaseModel):
    error: str
    message: str

@app.get("/")
async def root():
    return {"message": "Weather Dashboard API is running! 🌤️"}

@app.get("/weather/{city}", response_model=WeatherResponse)
async def get_weather(city: str):
    """Get current weather for a city"""
    start_time = time.time()
    weather_requests.inc()
    
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        base_url = os.getenv("OPENWEATHER_BASE_URL")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="API key not configured")
        
        url = f"{base_url}/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="City not found")
        
        data = response.json()
        
        weather_data = WeatherResponse(
            city=data["name"],
            temperature=data["main"]["temp"],
            description=data["weather"][0]["description"].title(),
            humidity=data["main"]["humidity"],
            wind_speed=data["wind"]["speed"],
            icon=data["weather"][0]["icon"],
            country=data["sys"]["country"]
        )
        
        # Record request duration
        request_duration.observe(time.time() - start_time)
        
        return weather_data
        
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Weather service unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "weather-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)