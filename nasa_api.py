import requests
    
def get_nasa():
    base_url = f"https://api.nasa.gov/planetary/apod?api_key=wVnaajaqfHQIaOhSyc5SQWFecweOwKAe54OUSuZT"
    response = requests.get(base_url)
    nasa_data = response.json()
    return nasa_data

def parse_nasa_data(nasa_data):
    explanation = nasa_data.get("explanation")
    url = nasa_data.get("url")
    return explanation, url