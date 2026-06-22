import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for
)
import requests
import re
import sqlite3
import certifi
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "giftgenie_secret"

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

def init_db():
    conn = sqlite3.connect("giftgenie.db")

    cursor = conn.cursor()

    created_at = datetime.now().strftime("%d-%m-%Y %H:%M")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    age INTEGER,
    budget INTEGER,
    currency TEXT,
    occasion TEXT,
    relationship TEXT,
    category TEXT,
    recommendations TEXT,
    user_id INTEGER,
    created_at TEXT
)
""")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT
        )
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            gift_name TEXT
        )
        """)
    
    

    conn.commit()
    conn.close()

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("giftgenie.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users
            (username,email,password)
            VALUES(?,?,?)
            """,
            (username,email,password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("giftgenie.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=? AND password=?
            """,
            (email,password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/form")

    return render_template("login.html")

def get_gift_suggestions(description, age, budget,
                         currency, occasion,
                         relationship, category):
    prompt = f"""
        You are an expert gift consultant.

        Recipient Details:
        Relationship: {relationship}
        Age: {age}
        Occasion: {occasion}
        Budget: {budget} {currency}
        Preferred Category: {category}

        Description:
        {description}

        Suggest exactly 8 personalized gift ideas.

        For each gift use EXACTLY this format:

        1. **Product Name**
        Price: <estimated price>
        Category: <category>
        Reason: <why it is suitable>

        Repeat for all 8 gifts.
        Use ONLY one of these categories:
        Gaming
        Sports
        Books
        Technology
        Fashion
        Fitness
        Home Decor
        Accessories

        Do not use categories such as "Novelty", "Miscellaneous", or "Other".
        
        Keep recommendations within the budget.
        Make recommendations specific and practical.
        Return only a numbered list.
        """
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 800
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
    
def save_recommendation(
    description,
    age,
    budget,
    currency,
    occasion,
    relationship,
    category,
    recommendations
):

    conn = sqlite3.connect("giftgenie.db")

    cursor = conn.cursor()

    created_at = datetime.now().strftime("%d-%m-%Y %H:%M")


    cursor.execute("""
        INSERT INTO history
        (
            description,
            age,
            budget,
            currency,
            occasion,
            relationship,
            category,
            recommendations,
            user_id,
            created_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            description,
            age,
            budget,
            currency,
            occasion,
            relationship,
            category,
            recommendations,
            session["user_id"],
            created_at
        ))

    conn.commit()
    conn.close()

def mock_product_links(suggestions_text):

    pattern = r"\d+\.\s\*\*(.*?)\*\*\s*Price:\s*(.*?)\s*Category:\s*(.*?)\s*Reason:\s*(.*?)(?=\n\d+\.|\Z)"

    items = re.findall(pattern, suggestions_text, re.DOTALL)

    output = []

    for title, price, category, reason in items:

        query = "+".join(title.split())
        link = f"https://www.amazon.com/s?k={query}"

        formatted = f"""
        <div class="gift-card">

            <h3>
                <i class="fas fa-gift"></i>
                {title}
            </h3>

            <div class="gift-meta">

                <div class="gift-meta-item">
                    💰 {price}
                </div>

                <div class="gift-meta-item">
                    🏷️ {category}
                </div>

            </div>

            <p class="gift-desc">
                {reason}
            </p>

            <a class="gift-link"
               href="{link}"
               target="_blank">
               <i class="fas fa-cart-shopping"></i>
                View on Amazon
            </a>

        </div>
        """

        output.append(formatted)

    return output
@app.route("/", methods=["GET", "POST"])
def index():
    suggestions = []
    if request.method == "POST":
        description = request.form["description"]
        age = request.form["age"]
        budget = request.form["budget"]

        currency = request.form["currency"]
        occasion = request.form["occasion"]
        relationship = request.form["relationship"]
        category = request.form["category"]

        print("Description:", description)
        print("Age:", age)
        print("Budget:", budget)
        print("Currency:", currency)
        print("Occasion:", occasion)
        print("Relationship:", relationship)
        print("Category:", category)

        suggestions_text = get_gift_suggestions(
            description,
            age,
            budget,
            currency,
            occasion,
            relationship,
            category
        )
        save_recommendation(
            description,
            age,
            budget,
            currency,
            occasion,
            relationship,
            category,
            suggestions_text
        )
        print("\n\n===== AI RESPONSE =====")
        print(suggestions_text)
        print("=======================\n\n")
        suggestions = mock_product_links(suggestions_text)

    return render_template("index.html", suggestions=suggestions)


@app.route("/form", methods=["GET", "POST"])

def form():
    suggestions = []
    if "user_id" not in session:
        return redirect("/login")
    if request.method == "POST":
        description = request.form.get("description")
        age = request.form.get("age")
        budget = request.form.get("budget")

        currency = request.form.get("currency")
        occasion = request.form.get("occasion")
        relationship = request.form.get("relationship")
        category = request.form.get("category")

        suggestions_text = get_gift_suggestions(
            description,
            age,
            budget,
            currency,
            occasion,
            relationship,
            category
        )
        save_recommendation(
            description,
            age,
            budget,
            currency,
            occasion,
            relationship,
            category,
            suggestions_text
        )
        suggestions = mock_product_links(suggestions_text)

    return render_template("form.html", suggestions=suggestions)

@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")
    conn = sqlite3.connect("giftgenie.db")

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM history
    WHERE user_id=?
    ORDER BY id DESC
    """,
    (session["user_id"],))

    data = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=data
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# if __name__ == "__main__":
#     app.run(debug=True)
if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000
    )

    