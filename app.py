import os
from flask import Flask, render_template, request
import requests
import re
import certifi

app = Flask(__name__)
API_KEY="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" # ← Pulls from Render's config
API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}", 
    "Content-Type": "application/json"
}
MODEL = "mistralai/mistral-7b-instruct:free"
# MODEL = "openchat/openchat-7b:free"
# MODEL = "nousresearch/nous-hermes-2-mixtral-8x7b-dpo"

def get_gift_suggestions(description, age, budget):
    prompt = (
    f"Based on the following details, suggest 5 unique and specific gift ideas for a {age}-year-old. "
    f"Budget: ${budget}. Description: {description}. "
    f"Format your response as a numbered list where each item is a complete suggestion."
)
    payload = {
        # "model": "openchat/openchat-7b:free",  # or another supported free model
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }


    response = requests.post(API_URL, json=payload, headers=HEADERS, verify=certifi.where())


    try:
        data = response.json()


        if "choices" in data:
            # 1. ASSIGN the variable 'content' a value immediately
            
            content = data["choices"][0]["message"]["content"]
            content = content.replace("~~", "")
            content = content.replace("—", "-")
            content = re.sub(r'<s>|</s>|<del>|</del>', '', content)
            # 2. Clean the content (remove prefixes like [OUT])
            prefixes_to_remove = ["[OUT]", "[ASSISTANT]", "[ANSWER]"]
            for prefix in prefixes_to_remove:
                if content.strip().upper().startswith(prefix):
                    content = content.strip()[len(prefix):].strip()

            # 3. Clean the list numbering (removes the initial '1.' that may remain)
            content = re.sub(r'^\s*[\d\.\*-]+\s*', '', content, 1).strip()
            
            suggestions_text = content
            
        elif "error" in data:
            suggestions_text = f"❌ API Error: {data['error'].get('message', 'Unknown error')}"
        
        return suggestions_text
    except Exception as e:
        return f"❌ Failed to parse API response: {e}"


def mock_product_links(suggestions_text):
    lines = suggestions_text.split("\n")
    output = []
    for line in lines:
        if line.strip():
            keywords = line.strip().split(":")[0]
            query = "+".join(keywords.strip().split())
            link = f"https://www.amazon.com/s?k={query}"
            output.append(f"{line} — <a href='{link}' target='_blank'>View on Amazon</a>")
    return output

@app.route("/", methods=["GET", "POST"])
def index():
    suggestions = None
    links = None
    if request.method == "POST":
        description = request.form["description"]
        age = request.form["age"]
        budget = request.form["budget"]
        suggestions = get_gift_suggestions(description, age, budget)
        links = mock_product_links(suggestions)
    return render_template("index.html", suggestions=links if links else [])

@app.route("/form", methods=["GET", "POST"])
def form():
    suggestions = None
    if request.method == "POST":
        description = request.form["description"]
        age = request.form["age"] 
        budget = request.form["budget"]
        suggestions_text = get_gift_suggestions(description, age, budget)
        suggestions = mock_product_links(suggestions_text)
    return render_template("form.html", suggestions=suggestions)

if __name__ == "__main__":
    app.run(debug=True)
