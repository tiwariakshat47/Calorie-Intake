import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI
from datetime import datetime
from apikey import apikey
import re
import uuid
from flask import Flask, request, render_template, redirect, url_for, flash, session

# Initialize Firebase Admin SDK
cred = credentials.Certificate("calorie-tracker-2dac3-firebase-adminsdk-34cxu-ff72e0f85e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize OpenAI API client
client = OpenAI(api_key=apikey)

# Flask app initialization
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Target calories per day
TARGET_CALORIES = 1800

def parse_calories(calorie_response):
    match = re.search(r'(\d+)', calorie_response)
    if match:
        return int(match.group(1))
    return 0

def get_current_calories():
    total_calories = 0
    docs = db.collection("daily_intake").stream()
    for doc in docs:
        meal = doc.to_dict()
        total_calories += meal['calories']
    return total_calories

@app.route('/')
def home():
    current_calories = get_current_calories()
    remaining_calories = TARGET_CALORIES - current_calories
    ai_response = session.pop('ai_response', None)
    return render_template('index.html', ai_response=ai_response, current_calories=current_calories, remaining_calories=remaining_calories)

@app.route('/add_meal', methods=['POST'])
def add_meal():
    content = request.form['content']
    date = datetime.now().strftime("%Y-%m-%d")
    
    full_content = content
    while True:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a gym assistant for Akshat Tiwari that helps him track the amount of calories that they are intaking, and helps them stay consistent. You want to ensure that he eats around 1800 calories per day. If you are expecting a response add RESPONSE EXPECTED to the end of your response. If you know how many calories there are in the meal already, don't add RESPONSE EXPECTED to the end of your response."},
                {"role": "user", "content": full_content}
            ]
        )
        
        response = completion.choices[0].message.content
        
        if "RESPONSE EXPECTED" not in response:
            break
        
        session['ai_response'] = response
        session['interaction_content'] = full_content
        return redirect(url_for('home'))

    calorie_estimation = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a calorie estimation assistant. Estimate the number of calories in the meal described below."},
            {"role": "user", "content": full_content}
        ]
    )

    calorie_response = calorie_estimation.choices[0].message.content
    calories = parse_calories(calorie_response)

    meal_entry = {
        "meal": full_content,
        "date": date,
        "time": datetime.now().strftime("%H:%M:%S"),
        "calories": calories
    }

    # Generate a unique meal_id using uuid
    meal_id = f"{date.replace('-', '')}_{uuid.uuid4()}"
    db.collection("daily_intake").document(meal_id).set(meal_entry)

    return redirect(url_for('view_intake'))

@app.route('/continue_interaction', methods=['POST'])
def continue_interaction():
    content = request.form['content']
    interaction_content = session.pop('interaction_content', "") + " " + content
    session['interaction_content'] = interaction_content
    return redirect(url_for('add_meal'))

@app.route('/remove_meal/<meal_id>', methods=['POST'])
def remove_meal(meal_id):
    meal_ref = db.collection("daily_intake").document(meal_id)
    meal = meal_ref.get().to_dict()
    if meal:
        meal_ref.delete()
    return redirect(url_for('view_intake'))

@app.route('/view_intake')
def view_intake():
    daily_intake = {}
    docs = db.collection("daily_intake").stream()

    for doc in docs:
        meal = doc.to_dict()
        date = meal['date']
        meal_id = doc.id
        meal['id'] = meal_id
        if date not in daily_intake:
            daily_intake[date] = []
        daily_intake[date].append(meal)

    current_calories = get_current_calories()
    remaining_calories = TARGET_CALORIES - current_calories
    return render_template('intake.html', daily_intake=daily_intake, current_calories=current_calories, remaining_calories=remaining_calories)

if __name__ == "__main__":
    app.run(debug=True)
