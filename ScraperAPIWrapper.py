import requests
import json

class ScraperAPIWrapper:
    def __init__(self, service_url):
        self.service_url = service_url

    def scrape_multiple(self, urls):
        payload = {
            "urls": urls,
            "with_tavily": False
        }
        response = requests.post(self.service_url, json=payload)
        if response.status_code == 200:
            response = response.json()
            return response['results']
        else:
            print("Error:", response.status_code, response.text)
            return []