import httpx
from datetime import datetime
from config import GEMINI_API_KEY, GEMINI_MODEL
import google.generativeai as genai

# ── Gemini client setup ────────────────────────────────────────────────────────

genai.configure(api_key=GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel(GEMINI_MODEL)

_INVALID_CITY = {
    "no", "none", "unknown", "here", "current", "location", "city",
    "no city", "no city name", "current location", "my location",
    "your location", "not mentioned",
}


def _gemini_chat(system_prompt: str, user_message: str,
                 temperature: float = 0.0, max_tokens: int = 150) -> str:
    """Send a prompt to Gemini and return the text response."""
    generation_config = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    full_prompt = f"{system_prompt}\n\nUser: {user_message}"
    response = _gemini_model.generate_content(
        full_prompt,
        generation_config=generation_config,
    )
    return response.text.strip()


def _extract_city(question: str) -> str:
    city = _gemini_chat(
        system_prompt=(
            "Extract the city name from the question. "
            "Reply with ONLY the city name — one or two words max. "
            "If no city is mentioned, reply with just: Bangalore"
        ),
        user_message=question,
        temperature=0,
        max_tokens=10,
    )
    city = city.split("\n")[0].split(".")[0].strip()
    if not city or len(city) > 40 or city.lower() in _INVALID_CITY:
        return "Bangalore"
    return city


def _get_weather(city: str) -> str:
    resp = httpx.get(f"https://wttr.in/{city}?format=j1", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    c = data["current_condition"][0]
    desc = c["weatherDesc"][0]["value"]
    temp = c["temp_C"]
    feels = c["FeelsLikeC"]
    humidity = c["humidity"]
    return f"In {city}, it's {desc} with {temp}°C, feels like {feels}°C, humidity {humidity}%."


def _web_search(query: str) -> str:
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
    if not results:
        return _gemini_answer(query)   # fall back to Gemini if no results
    context = "\n".join(
        f"{r.get('title', '')}: {r.get('body', '')}" for r in results
    )
    return _gemini_chat(
        system_prompt=(
            "Answer in 1-2 short sentences based on search results. "
            "Be conversational — the answer will be spoken aloud."
        ),
        user_message=f"Question: {query}\n\nSearch results:\n{context}",
        temperature=0.3,
        max_tokens=120,
    )


def _gemini_answer(question: str) -> str:
    """Use Gemini's own knowledge — no web needed."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    return _gemini_chat(
        system_prompt=(
            f"You are a helpful voice assistant named Dev. "
            f"Today's date is {today}. "
            "Answer in 1-2 short conversational sentences. "
            "The response will be spoken aloud so keep it brief and natural. "
            "Never say you don't know the date."
        ),
        user_message=question,
        temperature=0.4,
        max_tokens=150,
    )


def answer(question: str) -> str:
    q = question.lower()
    try:
        # Real-time weather → wttr.in
        if any(w in q for w in ["weather", "temperature", "rain", "humidity", "forecast"]):
            city = _extract_city(question)
            try:
                return _get_weather(city)
            except Exception as e:
                print(f"  [weather error] {e}")
                return f"Sorry, I couldn't fetch the weather for {city} right now."

        # Real-time news/scores → web search
        if any(w in q for w in ["news", "latest news", "score", "match result", "stock price"]):
            return _web_search(question)

        # Everything else → Gemini directly
        return _gemini_answer(question)

    except Exception as e:
        print(f"  [search error] {e}")
        try:
            return _gemini_answer(question)
        except Exception:
            return "Sorry, I couldn't get that information right now."
