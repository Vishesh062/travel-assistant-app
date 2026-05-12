# Travel Assistant

🔗 **[Live demo →](https://aitravelassistant.streamlit.app/)**

An LLM-powered travel planner. Give it a destination, dates, budget, and interests; it builds a day-by-day itinerary with specific venues and real costs at today's exchange rate, live weather, flight info, and PDF export — in any of seven languages.

## What it does

- Generates a custom day-by-day itinerary using GPT-4o-mini or Claude 3 Haiku via OpenRouter
- Pulls **live currency conversion** from Frankfurter (ECB-sourced, no API key) so costs reflect today's rates, not the LLM's training-cutoff data
- Fetches current weather at the destination via OpenWeatherMap
- Surfaces sample flight info via AviationStack
- Translates the itinerary into Hindi, Spanish, French, German, Japanese, or Mandarin
- Tracks per-generation cost (token count + $ estimate) so users see what their query costs
- Exports the full plan as a PDF

## Stack

- **Frontend**: Streamlit (theme-aware custom CSS, custom info-card components)
- **Backend**: Python
- **LLMs**: OpenRouter (GPT-4o-mini, Claude 3 Haiku)
- **APIs**: OpenWeatherMap, AviationStack, Frankfurter (FX), Google Translator (via deep-translator)
- **PDF**: FPDF with bundled DejaVu Sans for non-Latin script support
- **Deployment**: Streamlit Community Cloud
- **Config**: python-dotenv (local) + Streamlit Secrets (production)

## Notable design decisions

**Currency handling.** The LLM's training cutoff is roughly a year stale, so it makes up exchange rates that don't reflect today's value. I pull live rates from Frankfurter (free, ECB-sourced, no API key needed) on submission, convert the user's home-currency budget to the destination currency, and inject both figures into the LLM prompt. The model uses the local-currency figure for all costs, and the live rate is surfaced in a metric card so the user sees what conversion was applied. Rates are cached for 1 hour via `@st.cache_data` since ECB only updates daily.

**Configuration.** Uses a `get_secret()` helper that reads from Streamlit Cloud's secrets vault first and falls back to local `.env`. Same code path works in dev and production with zero changes.

**Cost transparency.** Most LLM apps hide their per-query cost. This one pulls token usage from OpenRouter's response, maps the model to per-token pricing, and shows the cost in the UI. Signals to the user (and to me, when debugging) which models are economical and which aren't.

**Model selection.** Originally supported free models on OpenRouter, but they routed through third-party providers with aggressive rate limits that broke the user experience. Switched to GPT-4o-mini and Claude 3 Haiku — both cost roughly $0.001 per generation. The deployed demo prioritises reliability over zero-cost.

**Translation.** Free Google Translate via `deep_translator` has a 5000-character limit per call and rate-limits aggressively when called repeatedly. The app chunks output into 4000-character pieces and translates each in one call rather than line-by-line.

## Running locally

```bash
git clone https://github.com/Vishesh062/travel-assistant-app.git
cd travel-assistant-app
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create a `.env` in the project root:

```
OPENROUTER_API_KEY=your_key
OPENWEATHER_API_KEY=your_key
AVIATIONSTACK_API_KEY=your_key
```

Then:

```bash
streamlit run app.py
```

The `.env` file is gitignored — never commit your API keys. For deployment, use the platform's secrets management instead.

## Notes

Originally built as a coursework project at Macquarie University. The codebase has since been substantially rewritten — original version used a five-API flat-file architecture with no abstraction; current version separates concerns, handles failures gracefully across four external APIs, and supports both local development and cloud deployment from the same codebase.
