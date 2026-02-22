import os
from flask import Flask, render_template, request
import requests
import re
import certifi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Load API key securely from .env
API_KEY = os.getenv("OPENROUTER_API_KEY")
# print("API KEY:", API_KEY)
API_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:5000",   # Required by OpenRouter
    "X-Title": "GiftGenie"
}
MODEL = "meta-llama/llama-3-8b-instruct"

# print("Model being used:", MODEL)
def get_gift_suggestions(description, age, budget):
    prompt = (
        f"Suggest exactly 5 highly specific and creative gift ideas "
        f"for a {age}-year-old person. Budget under ${budget}. "
        f"Description: {description}. "
        f"For each idea, include:\n"
        f"1. Product Name (bold)\n"
        f"2. 1-2 sentence explanation\n"
        f"Return only a numbered list."
    )
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 400
        }

    response = requests.post(
        API_URL,
        json=payload,
        headers=HEADERS,
        verify=certifi.where()
    )

    # Debug (remove later if working)
    print("Status Code:", response.status_code)
    print("Response:", response.text)

    try:
        data = response.json()

        if "choices" in data:
            content = data["choices"][0]["message"]["content"]

            content = content.replace("~~", "")
            content = content.replace("—", "-")
            content = re.sub(r'<s>|</s>|<del>|</del>', '', content)

            suggestions_text = content.strip()

        elif "error" in data:
            suggestions_text = f"❌ API Error: {data['error'].get('message', 'Unknown error')}"

        else:
            suggestions_text = "❌ Unexpected API response."

        return suggestions_text

    except Exception as e:
        return f"❌ Failed to parse API response: {e}"


def mock_product_links(suggestions_text):
    items = re.findall(r"\d+\.\s*\*\*(.*?)\*\*:?\s*(.*)", suggestions_text)
    output = []

    for title, description in items:
        query = "+".join(title.split())
        link = f"https://www.amazon.com/s?k={query}"

        formatted = f"""
        <div class="gift-card">
            <h3>{title}</h3>
            <p>{description}</p>
            <a href="{link}" target="_blank">View on Amazon</a>
        </div>
        """
        output.append(formatted)

    return output

@app.route("/", methods=["GET", "POST"])
def index():
    suggestions = []
    if request.method == "POST":
        description = request.form.get("description")
        age = request.form.get("age")
        budget = request.form.get("budget")

        suggestions_text = get_gift_suggestions(description, age, budget)
        suggestions = mock_product_links(suggestions_text)

    return render_template("index.html", suggestions=suggestions)


@app.route("/form", methods=["GET", "POST"])
def form():
    suggestions = []
    if request.method == "POST":
        description = request.form.get("description")
        age = request.form.get("age")
        budget = request.form.get("budget")

        suggestions_text = get_gift_suggestions(description, age, budget)
        suggestions = mock_product_links(suggestions_text)

    return render_template("form.html", suggestions=suggestions)

if __name__ == "__main__":
    app.run(debug=True)