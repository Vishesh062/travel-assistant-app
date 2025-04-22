import os
import requests
from dotenv import load_dotenv

# Load the API key
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_travel_plan(prompt, model="mistralai/mistral-7b-instruct"):
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
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code}\n{response.text}"

# Start of the interactive session
if __name__ == "__main__":
    print("\n🧳 Welcome to your Personal Travel Assistant!\n")

    name = input("👤 What's your name? ")
    origin = input("🛫 Where are you departing from? (Your current city or nearest airport) ")
    intention = input("🎯 What's the purpose of your trip? (e.g., honeymoon, family vacation, solo trip, business) ")
    destination = input("📍 Where do you want to travel to? ")
    interests = input("❤️ What are you interested in? (e.g., hiking, food, beaches, art, nightlife) ")
    days = input("📆 How many days is your trip? ")
    budget = input("💸 What's your total budget in your local currency? (e.g., $1000, ₹50,000) ")

    # Dynamic prompt construction
    prompt = (
        f"Create a detailed travel itinerary for {name}, who is going on a {intention} from {origin} to {destination}. "
        f"The trip is for {days}, with a budget of {budget}. The itinerary should consider flight costs from {origin}. "
        f"{name} is especially interested in {interests}. Provide day-wise suggestions that align with the purpose, preferences, and budget."
    )

    print("\n🧠 Generating your personalized itinerary...\n")
    itinerary = get_travel_plan(prompt)

    print("\n--- Your Custom Travel Itinerary ---\n")
    print(itinerary)