import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI
from datetime import datetime
from apikey import apikey
import re

cred = credentials.Certificate("calorie-tracker-2dac3-firebase-adminsdk-34cxu-ff72e0f85e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

client = OpenAI(api_key=apikey)

daily_intake = {}

def get_meal_count(date):
    meals_ref = db.collection("daily_intake").where("date", "==", date)
    meals = meals_ref.stream()
    return sum(1 for _ in meals)

def userQuery():
    date = datetime.now().strftime("%Y-%m-%d")
    
    if date not in daily_intake:
        daily_intake[date] = []
    count = 0
    while True:
        content = input("Enter what you ate for this meal:\n")
        full_content = content
        
        
        while True:
            completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a gym assistant for Akshat Tiwari that helps him track the amount of calories that they are intaking, and helps them stay consistent. You want to ensure that he eats around 2000 calories per day. At the end of each response you have, indicate whether you are expecting a response from the user or not. If you are expecting a response add RESPONSE EXPECTED to the end of your response. If you know how many calories there are in the meal already, don't add RESPONSE EXPECTED to the end of your response."},
                    {"role": "user", "content": content}
                ]
            )

            response = completion.choices[0].message.content
            
            print(response)
            count += 1
            
            if "RESPONSE EXPECTED" not in response or count > 3:
                break
            
            response += "\n"
            new_content = input(response)
            content = new_content
            full_content += " " + new_content + "\n"

        calorie_estimation = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a calorie estimation assistant. Estimate the number of calories in the meal described below."},
                {"role": "user", "content": full_content}
            ]
        )
        
        calorie_response = calorie_estimation.choices[0].message.content
        print("Calorie Estimation:", calorie_response)
        
        calories = parse_calories(calorie_response)
        
        meal_count = len(daily_intake[date]) + 1
        meal_entry = {
            "meal": full_content,
            "date": date,
            "time": datetime.now().strftime("%H:%M:%S"),
            "calories": calories
        }
        daily_intake[date].append(meal_entry)
        
        meal_id = f"{date.replace('-', '')}_meal_{meal_count}"
        db.collection("daily_intake").document(meal_id).set(meal_entry)
        
        if input("Do you want to enter another meal? (y/n): ").lower() != 'y':
            break

def parse_calories(calorie_response):
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
