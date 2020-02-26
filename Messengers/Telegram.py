import requests
import json

TOKEN = "1012422749:AAH256qjunfinG-XbWNDZZNzomxLpXb3nAQ"
URL = "https://api.telegram.org/bot" + TOKEN
CHANNEL_ID = 1029414853

def sendMessage(text: str):

    method = URL + "/sendMessage"

    try:

        r = requests.post(method, data={
            "chat_id": CHANNEL_ID,
            "text": text
            })    

        if r.status_code != 200:
            error = json.loads(r.content)
            print("Error code: " + str(error.get("error_code")) + "\nDescription: " + str(error.get("description")))

    except Exception as ex:
        print(ex)
    
