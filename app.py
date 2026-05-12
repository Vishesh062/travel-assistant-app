import streamlit as st
import requests
import os
from dotenv import load_dotenv
from fpdf import FPDF
from deep_translator import GoogleTranslator

# -----------------------------------------------------------------------------
# Config & secrets (works with both local .env and Streamlit Cloud secrets)
# -----------------------------------------------------------------------------
load_dotenv()

def get_secret(name: str) -> str | None:
    """Read from Streamlit Cloud secrets first, fall back to .env / env vars."""
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        return os.getenv(name)

OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
OPENWEATHER_API_KEY = get_secret("OPENWEATHER_API_KEY")
AVIATIONSTACK_API_KEY = get_secret("AVIATIONSTACK_API_KEY")

# -----------------------------------------------------------------------------
# Page config + light styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Travel Assistant",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    h1 { font-weight: 700; letter-spacing: -0.02em; }
    .stButton button { width: 100%; font-weight: 600; }
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# IATA codes + API helpers
# -----------------------------------------------------------------------------
IATA_CODES = {
    "sydney": "SYD", "melbourne": "MEL", "brisbane": "BNE",
    "delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR",
    "tokyo": "HND", "bali": "DPS", "new york": "JFK",
    "los angeles": "LAX", "singapore": "SIN", "dubai": "DXB",
    "london": "LHR", "paris": "CDG", "bangkok": "BKK",
    "hong kong": "HKG", "seoul": "ICN", "auckland": "AKL",
}

def get_iata_code(city_name: str) -> str:
    return IATA_CODES.get(city_name.lower().strip(), city_name[:3].upper())

def get_flight_info(origin_iata: str, destination_iata: str) -> str:
    """Fetch a sample flight. AviationStack free tier uses HTTP, not HTTPS."""
    if not AVIATIONSTACK_API_KEY:
        return "No API key configured"
    try:
        response = requests.get(
            "http://api.aviationstack.com/v1/flights",
            params={
                "access_key": AVIATIONSTACK_API_KEY,
                "dep_iata": origin_iata,
                "arr_iata": destination_iata,
                "limit": 1,
            },
            timeout=10,
        )
        if response.status_code != 200:
            return "Service unavailable"
        data = response.json()
        if not data.get("data"):
            return f"No active flights ({origin_iata}→{destination_iata})"
        flight = data["data"][0]
        return f"{flight['airline']['name']} {flight['flight']['iata']}"
    except Exception:
        return "Service unavailable"

def get_weather(city: str) -> dict | None:
    """Returns dict with temp + description, or None if failed."""
    if not OPENWEATHER_API_KEY:
        return None
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return {
            "temp": data["main"]["temp"],
            "description": data["weather"][0]["description"].capitalize(),
        }
    except Exception:
        return None

def get_travel_plan(prompt: str, model: str) -> tuple[str | None, dict]:
    """Generate itinerary. Returns (text, usage_stats) tuple."""
    if not OPENROUTER_API_KEY:
        return None, {}
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a practical travel planner. Generate day-by-day "
                            "itineraries with specific venues, neighbourhoods, and "
                            "approximate costs. Skip generic advice."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        result = response.json()
        text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        return text, usage
    except Exception:
        return None, {}

# -----------------------------------------------------------------------------
# Cost estimation (rough; based on OpenRouter pricing snapshots)
# -----------------------------------------------------------------------------
MODEL_PRICING = {
    # USD per 1K tokens: (prompt_rate, completion_rate)
    "openai/gpt-4o-mini": (0.00015, 0.0006),
    "anthropic/claude-3-haiku": (0.00025, 0.00125),
    "meta-llama/llama-3.3-70b-instruct:free": (0.0, 0.0),
    "qwen/qwen3-next-80b-a3b-instruct:free": (0.0, 0.0),
    "openai/gpt-oss-20b:free": (0.0, 0.0),
}

def estimate_cost(usage: dict, model: str) -> float:
    if not usage or model not in MODEL_PRICING:
        return 0.0
    prompt_rate, completion_rate = MODEL_PRICING[model]
    return (
        usage.get("prompt_tokens", 0) * prompt_rate
        + usage.get("completion_tokens", 0) * completion_rate
    ) / 1000

# -----------------------------------------------------------------------------
# PDF generation
# -----------------------------------------------------------------------------
def generate_pdf(itinerary_text: str, filename: str = "itinerary.pdf") -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    try:
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVu", "", 11)
    except Exception:
        pdf.set_font("Helvetica", "", 11)
    for line in itinerary_text.split("\n"):
        try:
            pdf.multi_cell(0, 7, line)
        except UnicodeEncodeError:
            pdf.multi_cell(0, 7, line.encode("latin-1", "ignore").decode("latin-1"))
    pdf.output(filename)
    return filename

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
st.title("AI Travel Assistant")
st.markdown(
    "Plan a custom trip in under a minute. Pick a model, fill in your destination "
    "and budget, get a day-by-day itinerary with weather, flights, and a PDF export."
)

st.divider()

with st.form("trip_form"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Who & where")
        name = st.text_input("Your name", placeholder="Vishesh")
        origin = st.text_input("Departure city", placeholder="Sydney")
        destination = st.text_input("Destination", placeholder="Tokyo")

    with col2:
        st.markdown("##### Trip details")
        purpose = st.selectbox(
            "Purpose",
            ["Solo trip", "Family vacation", "Honeymoon", "Business", "Group trip", "Other"],
        )
        days = st.text_input("Duration", placeholder="7 days")
        budget = st.text_input("Budget", placeholder="AU$2000")

    interests = st.text_area(
        "Interests",
        placeholder="e.g. street food, hiking, jazz bars, vintage bookshops",
        height=80,
    )

    col3, col4 = st.columns(2)
    with col3:
        language = st.selectbox(
            "Output language",
            ["English", "Hindi", "Spanish", "French", "German", "Japanese", "Mandarin"],
        )
    with col4:
        llm_model = st.selectbox(
            "LLM",
            [
                "meta-llama/llama-3.3-70b-instruct:free",
                "qwen/qwen3-next-80b-a3b-instruct:free",
                "openai/gpt-oss-20b:free",
                "openai/gpt-4o-mini",
                "anthropic/claude-3-haiku",
            ],
            help="Free models (`:free`) are slower and less polished but cost $0. Paid models are faster and produce better output for ~$0.001 per generation.",
        )

    submitted = st.form_submit_button("Generate itinerary", use_container_width=True)

# --- Results ---
if submitted:
    if not all([name, origin, destination, days, budget, interests]):
        st.error("Please fill in all fields.")
        st.stop()

    origin_iata = get_iata_code(origin)
    destination_iata = get_iata_code(destination)

    with st.spinner("Generating your itinerary..."):
        flight_info = get_flight_info(origin_iata, destination_iata)
        weather = get_weather(destination)

        prompt = (
            f"Plan a {days} trip for {name}, a {purpose.lower()} from {origin} to {destination}. "
            f"Budget: {budget}. Interests: {interests}. "
            f"Provide a day-by-day breakdown with specific venues, neighbourhoods, and approximate costs. "
            f"Keep it practical, not generic."
        )

        itinerary, usage = get_travel_plan(prompt, llm_model)

        if not itinerary:
            st.warning(f"{llm_model} didn't respond. Trying Llama 3.3 as fallback.")
            itinerary, usage = get_travel_plan(prompt, "meta-llama/llama-3.3-70b-instruct:free")

        if not itinerary:
            st.error("All models failed. Check your OpenRouter API key.")
            st.stop()

        # Persist for budget regeneration
        st.session_state["flight_info"] = flight_info
        st.session_state["last_model"] = llm_model
        st.session_state["last_inputs"] = {
            "name": name, "origin": origin, "destination": destination,
            "purpose": purpose, "interests": interests, "days": days,
            "budget": budget, "language": language,
        }

    st.divider()
    result_col, info_col = st.columns([3, 1])

    with info_col:
        st.markdown("##### Trip details")
        if weather:
            st.metric("Weather", f"{weather['temp']:.0f}°C", weather["description"])
        else:
            st.metric("Weather", "—", "unavailable")
        st.metric("Flights", flight_info)
        if usage:
            cost = estimate_cost(usage, llm_model)
            total_tokens = usage.get("total_tokens", 0)
            cost_label = "Free" if cost == 0 else f"${cost:.4f}"
            st.metric("Cost", cost_label, f"{total_tokens} tokens")

    with result_col:
        st.markdown("##### Your itinerary")
        st.markdown(itinerary)

        if language != "English":
            with st.expander(f"Translated to {language}"):
                try:
                    translator = GoogleTranslator(source="auto", target=language.lower())
                    translated = "\n".join(
                        translator.translate(line) for line in itinerary.split("\n") if line.strip()
                    )
                    st.markdown(translated)
                except Exception as e:
                    st.error(f"Translation failed: {e}")

        filename = generate_pdf(itinerary)
        with open(filename, "rb") as f:
            st.download_button(
                label="Download as PDF",
                data=f,
                file_name=f"trip_to_{destination.lower().replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# --- Budget regeneration ---
if "last_inputs" in st.session_state:
    st.divider()
    with st.expander("Adjust budget and regenerate"):
        new_budget = st.text_input("New budget", placeholder="AU$3000")
        if st.button("Regenerate") and new_budget:
            inputs = st.session_state["last_inputs"]
            with st.spinner("Regenerating..."):
                prompt = (
                    f"Plan a {inputs['days']} trip for {inputs['name']}, a {inputs['purpose'].lower()} "
                    f"from {inputs['origin']} to {inputs['destination']}. "
                    f"Budget: {new_budget}. Interests: {inputs['interests']}. "
                    f"Flight context: {st.session_state['flight_info']}. "
                    f"Day-by-day breakdown with specific venues and approximate costs."
                )
                new_plan, new_usage = get_travel_plan(prompt, st.session_state["last_model"])
                if new_plan:
                    st.markdown(new_plan)
                    if new_usage:
                        cost = estimate_cost(new_usage, st.session_state["last_model"])
                        cost_label = "Free" if cost == 0 else f"${cost:.4f}"
                        st.caption(f"Cost: {cost_label} · {new_usage.get('total_tokens', 0)} tokens")

st.divider()
st.caption(
    "Built by [Vishesh Singh](https://github.com/Vishesh062). "
    "[Source code](https://github.com/Vishesh062/travel-assistant-app)."
)