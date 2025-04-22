# Personal Travel Assistant (COMP8420 Assignment 2)

This is a fully interactive AI-powered travel planning app built using large language models (LLMs) like GPT-3.5, Claude, and Mistral via OpenRouter API. It collects user preferences and generates a custom travel itinerary, including real-time weather, flight suggestions, and multi-language output.

---

## Features

- LLM-powered itinerary generator (supports multiple models)
-  User-defined trip details: origin, destination, interests, budget
- Flight info via AviationStack API
- Live weather via OpenWeatherMap API
- Multi-language output via Google Translator
- PDF export of itinerary (always in English)
- Regenerate plan based on new budget

---

##  Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **APIs Used**:
  - OpenRouter (for LLMs)
  - OpenWeatherMap (weather data)
  - AviationStack (flight info)
  - Google Translator (via deep-translator)
- **PDF Export**: FPDF
- **Environment Config**: dotenv

---

## How to Run

```bash
git clone https://github.com/YOUR_USERNAME/travel-assistant-app.git
cd travel-assistant-app
pip install -r requirements.txt