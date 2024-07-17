from apikey import apikey
from openai import OpenAI

client = OpenAI(
  api_key=apikey,
)


def userQuery():
    content = input("Enter what you ate for this meal:\n")

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a gym assistant for Akshat Tiwari that helps him track the amount of calories that they are intaking, and helps them stay consistent. You want to ensure that he eats around 2000 calories per day"},
        {"role": "user", "content": content}
    ]
    )



userQuery()
while(input("Exit (y/n): ") != "y"):
    userQuery()
