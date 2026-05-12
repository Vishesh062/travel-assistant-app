# Travel Assistant

An LLM-powered travel itinerary generator. Give it a destination, dates, budget, and your interests; it builds a day-by-day plan with weather forecasts, flight suggestions, and a multilingual PDF export.

## What it does

- Generates a custom itinerary using GPT-3.5, Claude, or Mistral (selectable via OpenRouter)
- Pulls live weather data for the destination via OpenWeatherMap
- Suggests flights via AviationStack
- Translates the final itinerary into any language via Google Translator
- Exports a PDF version of the plan

## Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **LLMs**: OpenRouter (GPT-3.5 / Claude / Mistral)
- **APIs**: OpenWeatherMap, AviationStack, Google Translator (via deep-translator)
- **PDF**: FPDF
- **Config**: python-dotenv

## Running it locally

```bash
git clone https://github.com/Vishesh062/travel-assistant-app.git
cd travel-assistant-app
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root with your API keys:

```
OPENROUTER_API_KEY=your_key
OPENWEATHER_API_KEY=your_key
AVIATIONSTACK_API_KEY=your_key
```

Then:

```bash
streamlit run app.py
```

## Notes

Built originally as a coursework project at Macquarie University. The implementation uses three external APIs and an LLM provider abstraction layer, so each component can be swapped without changing the application logic. Most of the interesting code is in how prompts are constructed per-model and how the PDF export handles non-Latin scripts.
