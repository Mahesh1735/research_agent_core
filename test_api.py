import requests
import json
import os
from dotenv import load_dotenv

def test_search_api():
    # Load environment variables
    load_dotenv()
    
    # Get API URL from environment variable or use default
    base_url = os.getenv('AGENT_API_URL')
    
    # Test payload
    payload = {
        "thread_id": '2',
        "query": "I am looking for where I can getstarted by drag-and-drop but also enables me to edit code when required, its a chat interface website and with blogs, SEO is helpful, something free to use to get started, please call the tool find_products"
    }
    
    try:
        # Make the request
        response = requests.post(f"{base_url}/chat", json=payload)
        
        # Print status code
        print(f"Status Code: {response.status_code}")
        
        # Print response
        if response.status_code == 200:
            data = response.json()
            print("\nRequirements:")
            print(data.get('requirements'))
            print("\nCandidates:")
            print(data.get('candidates'))
            print("\nLast AI Message:")
            print(data.get('last_ai_message'))
        else:
            print("Error:", response.json())
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    test_search_api()