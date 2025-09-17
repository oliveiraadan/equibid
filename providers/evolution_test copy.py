import requests

url = "http://127.0.0.1:8080/group/participants/equibid"

querystring = {"groupJid":"120363261102259189@g.us"}

headers = {"apikey": "429683C4C977415CAAFCCE10F7D57E11"}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())


