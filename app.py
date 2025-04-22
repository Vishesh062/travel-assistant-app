import streamlit as st
import requests
import os
from dotenv import load_dotenv
from fpdf import FPDF
from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

# Function to create downloadable PDF in English
def generate_pdf(itinerary_text, filename="itinerary.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.set_font('DejaVu', '', 12)

    for line in itinerary_text.split('\n'):
        pdf.multi_cell(0, 10, line)

    pdf.output(filename)
    return filename

# Define IATA mappings for fallback
iata_codes = {
    "sydney": "SYD", "melbourne": "MEL", "brisbane": "BNE", "delhi": "DEL",
    "mumbai": "BOM", "bangalore": "BLR", "tokyo": "HND", "bali": "DPS",
    "new york": "JFK", "los angeles": "LAX", "singapore": "SIN",
    "dubai": "DXB", "london": "LHR"
}

def get_iata_code(city_name):
    return iata_codes.get(city_name.lower().strip(), city_name[:3].upper())

# Get real-time flight info
def get_basic_flight_info(origin_city, destination_city):
    url = "http://api.aviationstack.com/v1/flights"
    params = {
        'access_key': AVIATIONSTACK_API_KEY,
        'dep_iata': origin_city[:3].upper(),
        'arr_iata': destination_city[:3].upper(),
        'limit': 1
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            flight = data['data'][0]
            airline = flight['airline']['name']
            flight_number = flight['flight']['iata']
            dep_time = flight['departure']['scheduled']
            arr_time = flight['arrival']['scheduled']
            return f"{airline} Flight {flight_number} | Departs: {dep_time} | Arrives: {arr_time}"
        else:
            return "No flight data available."
    return "Failed to fetch flight info."

# Get current weather at destination
def get_weather(city):
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(weather_url)
    if response.status_code == 200:
        data = response.json()
        temp = data['main']['temp']
        condition = data['weather'][0]['description'].capitalize()
        return f"{temp}°C, {condition}"
    return "Weather info unavailable"

# Query OpenRouter API to generate plan
def get_travel_plan(prompt, model):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a smart and friendly AI travel planner that creates detailed, personalized itineraries."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    try:
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return None

# UI setup
st.set_page_config(page_title="AI Travel Assistant", layout="centered")
st.title("\U0001F5FA Personal Travel Assistant")
st.markdown("Plan your trip with the help of AI! Get custom travel itineraries based on your preferences.")

with st.form("trip_form"):
    name = st.text_input("👤 Your Name", placeholder="e.g. Vishesh")
    origin = st.text_input("🛫 Departure City", placeholder="e.g. Sydney")
    destination = st.text_input("📍 Travel Destination", placeholder="e.g. Bali")
    intention = st.selectbox("🎯 Trip Purpose", ["Honeymoon", "Family Vacation", "Solo Trip", "Business", "Other"])
    interests = st.text_area("❤️ Your Interests", placeholder="e.g. beaches, food, nightlife, hiking")
    days = st.text_input("📆 Trip Duration", placeholder="e.g. 7 days")
    budget = st.text_input("💸 Budget", placeholder="e.g. AU$2000")
    language = st.selectbox("🌐 Preferred Language", ["English", "Hindi", "Spanish", "French", "German"])
    llm_model = st.selectbox("🧠 Choose LLM Model", [
        "openai/gpt-3.5-turbo",
        "anthropic/claude-instant",
        "mistralai/mistral-7b-instruct"
    ])
    submitted = st.form_submit_button("🚀 Generate My Travel Plan")

if submitted:
    origin_code = get_iata_code(origin)
    destination_code = get_iata_code(destination)

    with st.spinner("Generating your personalized itinerary..."):
        flight_info = get_basic_flight_info(origin_code, destination_code)
        st.session_state.flight_info = flight_info
        st.info(f"✈️ Flight Info: {flight_info}")

        weather = get_weather(destination)
        st.info(f"🌤️ Weather in {destination}: {weather}")

        prompt = (
            f"Create a detailed travel itinerary for {name}, who is going on a {intention.lower()} from {origin} to {destination}. "
            f"The trip is for {days}, with a budget of {budget}. The itinerary should consider flight availability like: {flight_info}. "
            f"{name} is especially interested in {interests}. Provide day-wise suggestions that align with the purpose, preferences, and budget."
        )

        itinerary = get_travel_plan(prompt, llm_model)

        if not itinerary:
            fallback_model = "mistralai/mistral-7b-instruct"
            st.warning(f"⚠️ The selected model {llm_model} failed. Falling back to {fallback_model}.")
            itinerary = get_travel_plan(prompt, fallback_model)

        if itinerary:
            st.markdown("## 🗺️ Your Custom Itinerary")
            st.write(itinerary)

            if language != "English":
                translator = GoogleTranslator(source='auto', target=language.lower())
                translated = "\n".join([translator.translate(line) for line in itinerary.split('\n')])
                st.markdown("### 🌍 Translated Itinerary")
                st.write(translated)
            else:
                translated = itinerary

            filename = generate_pdf(itinerary)
            with open(filename, "rb") as f:
                st.download_button(
                    label="📄 Download PDF (English)",
                    data=f,
                    file_name="your_trip_plan.pdf",
                    mime="application/pdf"
                )

# Budget regeneration
st.markdown("---")
new_budget = st.text_input("🔁 Want to adjust the budget and regenerate?", placeholder="e.g. AU$3000")
if new_budget and st.button("🔁 Regenerate Itinerary with New Budget"):
    prompt = (
        f"Create a new itinerary for {name}, going on a {intention.lower()} from {origin} to {destination}. "
        f"This time, the budget is {new_budget}. Flight details: {st.session_state.flight_info}. "
        f"Keep it realistic and aligned to the trip purpose."
    )
    updated_plan = get_travel_plan(prompt, llm_model)
    if not updated_plan:
        fallback_model = "mistralai/mistral-7b-instruct"
        st.warning(f"⚠️ Retry with fallback model {fallback_model}.")
        updated_plan = get_travel_plan(prompt, fallback_model)

    if updated_plan:
        st.markdown("## 🔁 Regenerated Itinerary")
        if language != "English":
            translator = GoogleTranslator(source='auto', target=language.lower())
            translated = "\n".join([translator.translate(line) for line in updated_plan.split('\n')])
            st.markdown("### 🌍 Translated Itinerary")
            st.write(translated)
        else:
            st.write(updated_plan)

        updated_filename = generate_pdf(updated_plan, filename="new_plan.pdf")
        with open(updated_filename, "rb") as f:
            st.download_button(
                label="📄 Download Regenerated PDF (English)",
                data=f,
                file_name="new_plan.pdf",
                mime="application/pdf"
            )