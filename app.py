import streamlit as st
import requests
import os
from dotenv import load_dotenv
from fpdf import FPDF
from deep_translator import GoogleTranslator

# -----------------------------------------------------------------------------
# Config & secrets
# -----------------------------------------------------------------------------
load_dotenv()

def get_secret(name: str) -> str | None:
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        return os.getenv(name)

OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
OPENWEATHER_API_KEY = get_secret("OPENWEATHER_API_KEY")
AVIATIONSTACK_API_KEY = get_secret("AVIATIONSTACK_API_KEY")

# -----------------------------------------------------------------------------
# Page config + theme-aware styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Travel Assistant",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { max-width: 1100px; margin: 0 auto; }

    .hero { padding: 2rem 0 1.5rem 0; }
    .hero h1 {
        font-size: 2.75rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        line-height: 1.1;
        margin-bottom: 0.75rem;
    }
    .hero .subtitle {
        font-size: 1.15rem;
        opacity: 0.75;
        font-weight: 400;
        line-height: 1.5;
        margin-bottom: 1rem;
        max-width: 700px;
    }
    .hero .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background: rgba(34, 197, 94, 0.1);
        color: rgb(34, 197, 94);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    .section-label {
        font-size: 0.8rem;
        font-weight: 600;
        opacity: 0.6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .stButton button, .stFormSubmitButton button {
        font-weight: 600;
        border-radius: 8px;
    }

    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    .info-card {
        padding: 1rem 1.25rem;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        background: rgba(128, 128, 128, 0.05);
        height: 100%;
    }
    .info-card-label {
        font-size: 0.75rem;
        font-weight: 600;
        opacity: 0.6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }
    .info-card-value {
        font-size: 1.1rem;
        font-weight: 600;
        line-height: 1.3;
    }
    .info-card-sub {
        font-size: 0.85rem;
        opacity: 0.7;
        margin-top: 0.15rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Reference data
# -----------------------------------------------------------------------------
IATA_CODES = {
    "sydney": "SYD", "melbourne": "MEL", "brisbane": "BNE",
    "delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR",
    "tokyo": "HND", "bali": "DPS", "new york": "JFK",
    "los angeles": "LAX", "singapore": "SIN", "dubai": "DXB",
    "london": "LHR", "paris": "CDG", "bangkok": "BKK",
    "hong kong": "HKG", "seoul": "ICN", "auckland": "AKL",
}

# Destination → local currency
DESTINATION_CURRENCY = {
    "sydney": "AUD", "melbourne": "AUD", "brisbane": "AUD",
    "delhi": "INR", "mumbai": "INR", "bangalore": "INR",
    "tokyo": "JPY", "bali": "IDR",
    "new york": "USD", "los angeles": "USD",
    "singapore": "SGD", "dubai": "AED",
    "london": "GBP", "paris": "EUR",
    "bangkok": "THB", "hong kong": "HKD",
    "seoul": "KRW", "auckland": "NZD",
}

HOME_CURRENCIES = ["AUD", "USD", "EUR", "GBP", "INR", "JPY", "CNY", "SGD", "CAD", "NZD"]

def get_iata_code(city_name: str) -> str:
    return IATA_CODES.get(city_name.lower().strip(), city_name[:3].upper())

def get_destination_currency(city: str) -> str | None:
    return DESTINATION_CURRENCY.get(city.lower().strip())

# -----------------------------------------------------------------------------
# API helpers
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # cache rates for 1 hour
def get_exchange_rate(from_currency: str, to_currency: str) -> float | None:
    """Frankfurter API — free, no auth, ECB-sourced. Returns rate or None."""
    if from_currency == to_currency:
        return 1.0
    try:
        response = requests.get(
            "https://api.frankfurter.dev/v2/rates",
            params={"base": from_currency, "quotes": to_currency},
            timeout=8,
        )
        if response.status_code != 200:
            return None
        return response.json()["rates"][to_currency]
    except Exception:
        return None

def get_flight_info(origin_iata: str, destination_iata: str) -> str:
    if not AVIATIONSTACK_API_KEY:
        return "Not configured"
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
            return "Unavailable"
        data = response.json()
        if not data.get("data"):
            return "No live flights"
        flight = data["data"][0]
        airline = flight.get("airline", {}).get("name", "Unknown")
        number = flight.get("flight", {}).get("iata", "")
        return f"{airline} {number}".strip() or "No flight data"
    except Exception:
        return "Unavailable"

def get_weather(city: str) -> dict | None:
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
                            "You are a practical travel planner. Generate day-by-day itineraries "
                            "with specific venues, neighbourhoods, and approximate costs in the "
                            "destination's local currency. The user provides their home-currency "
                            "budget converted to local currency at today's live rate — use that "
                            "exact figure and trust it. Never make up exchange rates yourself. "
                            "Skip generic advice."
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
# Cost estimation
# -----------------------------------------------------------------------------
MODEL_PRICING = {
    "openai/gpt-4o-mini": (0.00015, 0.0006),
    "anthropic/claude-3-haiku": (0.00025, 0.00125),
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
# Example pre-fill
# -----------------------------------------------------------------------------
def load_example():
    st.session_state.name_input = "Vishesh"
    st.session_state.origin_input = "Sydney"
    st.session_state.destination_input = "Tokyo"
    st.session_state.days_input = "7 days"
    st.session_state.home_currency_input = "AUD"
    st.session_state.budget_amount_input = 3500
    st.session_state.interests_input = "ramen, jazz bars, vintage shopping in Shimokitazawa, day trip to Hakone"

# -----------------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>Plan a trip in 60 seconds.</h1>
    <p class="subtitle">
        An LLM-powered travel planner. Day-by-day itineraries with specific venues
        and real costs at today's exchange rate, live weather, flight info, and PDF
        export — in any language.
    </p>
    <span class="badge">● Live demo · No login required</span>
</div>
""", unsafe_allow_html=True)

col_a, _ = st.columns([1, 5])
with col_a:
    st.button("Try with example", on_click=load_example, use_container_width=True)

# -----------------------------------------------------------------------------
# Form
# -----------------------------------------------------------------------------
with st.form("trip_form"):
    st.markdown('<div class="section-label">WHO & WHERE</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("Name", key="name_input", placeholder="Vishesh")
    with col2:
        origin = st.text_input("From", key="origin_input", placeholder="Sydney")
    with col3:
        destination = st.text_input("To", key="destination_input", placeholder="Tokyo")

    st.markdown('<div class="section-label" style="margin-top: 1rem;">TRIP DETAILS</div>', unsafe_allow_html=True)
    col4, col5, col6, col7 = st.columns([2, 2, 1.5, 2])
    with col4:
        purpose = st.selectbox(
            "Purpose",
            ["Solo trip", "Family vacation", "Honeymoon", "Business", "Group trip", "Other"],
        )
    with col5:
        days = st.text_input("Duration", key="days_input", placeholder="7 days")
    with col6:
        home_currency = st.selectbox("Currency", HOME_CURRENCIES, key="home_currency_input")
    with col7:
        budget_amount = st.number_input(
            "Budget",
            min_value=100,
            value=2000,
            step=100,
            key="budget_amount_input",
        )

    interests = st.text_area(
        "Interests",
        key="interests_input",
        placeholder="e.g. ramen, jazz bars, vintage shopping",
        height=80,
    )

    st.markdown('<div class="section-label" style="margin-top: 0.5rem;">OUTPUT</div>', unsafe_allow_html=True)
    col8, col9 = st.columns(2)
    with col8:
        language = st.selectbox(
            "Language",
            ["English", "Hindi", "Spanish", "French", "German", "Japanese", "Mandarin"],
        )
    with col9:
        llm_model = st.selectbox(
            "Model",
            ["openai/gpt-4o-mini", "anthropic/claude-3-haiku"],
            help="Both cost ~$0.001 per generation. GPT-4o-mini is faster, Claude tends to write better prose.",
        )

    submitted = st.form_submit_button("Generate itinerary", type="primary", use_container_width=True)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def info_card(label: str, value: str, sub: str = ""):
    sub_html = f'<div class="info-card-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="info-card">
        <div class="info-card-label">{label}</div>
        <div class="info-card-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------------
if submitted:
    if not all([name, origin, destination, days, interests]):
        st.error("Please fill in all fields.")
        st.stop()

    origin_iata = get_iata_code(origin)
    destination_iata = get_iata_code(destination)
    dest_currency = get_destination_currency(destination)

    with st.spinner("Generating your itinerary..."):
        flight_info = get_flight_info(origin_iata, destination_iata)
        weather = get_weather(destination)

        # Currency conversion
        if dest_currency:
            rate = get_exchange_rate(home_currency, dest_currency)
            if rate:
                local_budget = budget_amount * rate
                budget_string = (
                    f"{home_currency} {budget_amount:,} "
                    f"(equivalent to approximately {dest_currency} {local_budget:,.0f} "
                    f"at today's rate of 1 {home_currency} = {rate:.2f} {dest_currency})"
                )
            else:
                local_budget = None
                budget_string = f"{home_currency} {budget_amount:,}"
        else:
            rate = None
            local_budget = None
            budget_string = f"{home_currency} {budget_amount:,}"

        prompt = (
            f"Plan a {days} trip for {name}, a {purpose.lower()} from {origin} to {destination}. "
            f"Budget: {budget_string}. "
            f"Interests: {interests}. "
            f"Provide a day-by-day breakdown with specific venues, neighbourhoods, and "
            f"approximate costs in {dest_currency or 'the local currency'}. "
            f"Keep it practical, not generic."
        )

        itinerary, usage = get_travel_plan(prompt, llm_model)

        if not itinerary:
            fallback = "anthropic/claude-3-haiku" if llm_model != "anthropic/claude-3-haiku" else "openai/gpt-4o-mini"
            st.warning(f"{llm_model} didn't respond. Trying {fallback}.")
            itinerary, usage = get_travel_plan(prompt, fallback)

        if not itinerary:
            st.error("Both models failed. Check your OpenRouter API key or credit balance.")
            st.stop()

        st.session_state["flight_info"] = flight_info
        st.session_state["last_model"] = llm_model
        st.session_state["last_inputs"] = {
            "name": name, "origin": origin, "destination": destination,
            "purpose": purpose, "interests": interests, "days": days,
            "home_currency": home_currency, "budget_amount": budget_amount,
            "language": language,
        }

    st.markdown('<div id="results"></div>', unsafe_allow_html=True)
    st.markdown('<script>document.getElementById("results").scrollIntoView({behavior: "smooth"});</script>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f"### Your trip to {destination.title()}")

    # Four metric cards if we have a rate, three otherwise
    if rate and dest_currency:
        m1, m2, m3, m4 = st.columns(4)
    else:
        m1, m2, m3 = st.columns(3)
        m4 = None

    with m1:
        if weather:
            info_card("Weather", f"{weather['temp']:.0f}°C", weather["description"])
        else:
            info_card("Weather", "Unavailable", "")
    with m2:
        info_card("Flight", flight_info, f"{origin_iata} → {destination_iata}")
    with m3:
        if usage:
            cost = estimate_cost(usage, llm_model)
            total_tokens = usage.get("total_tokens", 0)
            cost_label = f"${cost:.4f}" if cost > 0 else "Free"
            info_card("Generation cost", cost_label, f"{total_tokens:,} tokens")
        else:
            info_card("Generation cost", "—", "no data")
    if m4 is not None:
        with m4:
            info_card(
                "Exchange rate",
                f"1 {home_currency} = {rate:.2f} {dest_currency}",
                f"Budget: {local_budget:,.0f} {dest_currency}",
            )

    st.markdown("")
    with st.container(border=True):
        st.markdown(itinerary)

    LANGUAGE_CODES = {
        "Hindi": "hi", "Spanish": "es", "French": "fr",
        "German": "de", "Japanese": "ja", "Mandarin": "zh-CN",
    }

    if language != "English":
        with st.expander(f"View translated to {language}", expanded=True):
            try:
                target_code = LANGUAGE_CODES.get(language, language.lower())
                translator = GoogleTranslator(source="auto", target=target_code)
                # Translate in chunks of ~4000 chars (Google's limit is 5000)
                chunks = []
                current = ""
                for line in itinerary.split("\n"):
                    if len(current) + len(line) > 4000:
                        chunks.append(current)
                        current = line + "\n"
                    else:
                        current += line + "\n"
                if current:
                    chunks.append(current)

                translated_chunks = [translator.translate(chunk) for chunk in chunks if chunk.strip()]
                translated = "\n".join(c for c in translated_chunks if c)

                if translated.strip():
                    st.markdown(translated)
                else:
                    st.warning("Translation returned empty. The free Google Translate endpoint may be rate-limited. Try again in a minute.")
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

# -----------------------------------------------------------------------------
# Budget regeneration
# -----------------------------------------------------------------------------
if "last_inputs" in st.session_state:
    st.markdown("")
    with st.expander("Adjust budget and regenerate"):
        new_budget = st.number_input(
            "New budget",
            min_value=100,
            value=st.session_state["last_inputs"]["budget_amount"],
            step=100,
            key="new_budget_input",
        )
        if st.button("Regenerate", type="primary"):
            inputs = st.session_state["last_inputs"]
            with st.spinner("Regenerating..."):
                dest_currency_re = get_destination_currency(inputs["destination"])
                if dest_currency_re:
                    rate_re = get_exchange_rate(inputs["home_currency"], dest_currency_re)
                    if rate_re:
                        local_re = new_budget * rate_re
                        budget_string_re = (
                            f"{inputs['home_currency']} {new_budget:,} "
                            f"(approximately {dest_currency_re} {local_re:,.0f} at 1 "
                            f"{inputs['home_currency']} = {rate_re:.2f} {dest_currency_re})"
                        )
                    else:
                        budget_string_re = f"{inputs['home_currency']} {new_budget:,}"
                else:
                    budget_string_re = f"{inputs['home_currency']} {new_budget:,}"

                prompt = (
                    f"Plan a {inputs['days']} trip for {inputs['name']}, a {inputs['purpose'].lower()} "
                    f"from {inputs['origin']} to {inputs['destination']}. "
                    f"Budget: {budget_string_re}. "
                    f"Interests: {inputs['interests']}. "
                    f"Flight context: {st.session_state['flight_info']}. "
                    f"Day-by-day breakdown with specific venues and approximate costs."
                )
                new_plan, new_usage = get_travel_plan(prompt, st.session_state["last_model"])
                if new_plan:
                    with st.container(border=True):
                        st.markdown(new_plan)
                    if new_usage:
                        cost = estimate_cost(new_usage, st.session_state["last_model"])
                        cost_label = f"${cost:.4f}" if cost > 0 else "Free"
                        st.caption(f"Cost: {cost_label} · {new_usage.get('total_tokens', 0):,} tokens")

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<p style='text-align: center; opacity: 0.5; font-size: 0.85rem;'>"
    "Built by <a href='https://github.com/Vishesh062' style='color: inherit;'>Vishesh Singh</a> · "
    "<a href='https://github.com/Vishesh062/travel-assistant-app' style='color: inherit;'>Source code</a> · "
    "<a href='https://medium.com/@vishesh062' style='color: inherit;'>Writing</a>"
    "</p>",
    unsafe_allow_html=True,
)