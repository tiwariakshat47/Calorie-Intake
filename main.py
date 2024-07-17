import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI
from datetime import datetime
from apikey import apikey

cred = credentials.Certificate("calorie-tracker-2dac3-firebase-adminsdk-34cxu-ff72e0f85e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

client = OpenAI(api_key=apikey)

daily_intake = {}

def get_meal_count(date):
    # Query Firestore to get the number of meals recorded for the given date
    meals_ref = db.collection("daily_intake").where("date", "==", date)
    meals = meals_ref.stream()
    return sum(1 for _ in meals)

def userQuery():
    date = datetime.now().strftime("%Y-%m-%d")
    
    if date not in daily_intake:
        daily_intake[date] = []

    while True:
        content = input("Enter what you ate for this meal:\n")
        
        # First GPT-4 call to track meal details
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a gym assistant for Akshat Tiwari that helps him track the amount of calories that they are intaking, and helps them stay consistent. You want to ensure that he eats around 2000 calories per day. At the end of each response you have, indicate whether you are expecting a response from the user or not. If you are expecting a response add RESPONSE EXPECTED to the end of your response. You have to know the exact amount of food that is being eaten to generate a very accurate response and estimate to how many calories one eats. Ask as many follow up questions as necessary."},
                {"role": "user", "content": content}
            ]
        )

        response = completion.choices[0].message.content
        print(response)
        if("RESONSE EXPECTED" in response):
            new_content = input(response)
            completion2 = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a gym assistant for Akshat Tiwari that helps him track the amount of calories that they are intaking, and helps them stay consistent. You want to ensure that he eats around 2000 calories per day. At the end of each response you have, indicate whether you are expecting a response from the user or not. If you are expecting a response add RESPONSE EXPECTED to the end of your response."},
                {"role": "user", "content": new_content}
            ]
        )
        

        
        if("RESONSE EXPECTED" in response):
            response += completion2.choices[0].message.content
        
        # Second GPT-4 call to estimate calories
        calorie_estimation = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a calorie estimation assistant. Estimate the number of calories in the meal described below."},
                {"role": "user", "content": content}
            ]
        )
        
        calorie_response = calorie_estimation.choices[0].message.content
        print("Calorie Estimation:", calorie_response)
        
        # Parse calories from the response
        calories = parse_calories(calorie_response)
        
        # Log the meal
        meal_entry = {
            "meal": content,
            "date": date,
            "time": datetime.now().strftime("%H:%M:%S"),
            "calories": calories
        }
        daily_intake[date].append(meal_entry)
        
        # Store meal entry in Firestore
        db.collection("daily_intake").add(meal_entry)
        
        if "RESPONSE EXPECTED" not in response:
            break

def parse_calories(calorie_response):
    # Extract the calorie value from the response
    # Assuming the response is something like "The estimated number of calories is 500."
    import re
    match = re.search(r'(\d+)', calorie_response)
    if match:
        return int(match.group(1))
    return 0

def display_intake():
    print("Daily Intake Summary:")
    for date, meals in daily_intake.items():
        print(f"{date}:")
        for meal in meals:
            print(f" - {meal['time']} - {meal['meal']} ({meal['calories']} calories)")

def main():
    while True:
        userQuery()
        exit_query = input("Exit (y/n): ")
        if exit_query.lower() == "y":
            break
    
    display_intake()

if __name__ == "__main__":
    main()
