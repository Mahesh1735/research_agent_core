from typing import List
from urllib.parse import urlparse
import functools
import time
import requests
import os

## util functions

def retry(max_tries=3, delay=1, backoff=2, retry_enabled=True, default_value=None):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not retry_enabled:
                # If retry is disabled, just run the function once and return the result
                return func(*args, **kwargs)

            tries = 0
            curr_delay = delay
            while tries < max_tries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    tries += 1
                    # Print the function name, args, and kwargs for each retry attempt
                    print(f"Attempt {tries} for function '{func.__name__}' with args: {args} and kwargs: {kwargs} failed with error: {e}")
                    if tries < max_tries:
                        print(f"Retrying in {curr_delay} seconds...")
                        time.sleep(curr_delay)
                        curr_delay *= backoff

            # If all retries fail, return the default_value
            print(f"Function '{func.__name__}' failed after {max_tries} attempts. Returning default value: {default_value}")
            return default_value
        return wrapper
    return decorator_retry


def deduplicate_candidates(products):
    # Dictionary to hold deduplicated products
    deduplicated = {}

    for product in products:
        domain = urlparse(product['product_URL']).netloc

        # If the domain already exists, concatenate the overviews
        if domain in deduplicated:
            deduplicated[domain]['overview'] += " " + product['overview']
        else:
            # If domain not seen before, add the product to the deduplicated dictionary
            deduplicated[domain] = {
                'title': product['title'],
                'product_URL': product['product_URL'],
                'overview': product['overview']
            }

    # Return the deduplicated products as a list of dictionaries
    return list(deduplicated.values())

@retry(max_tries=3, delay=1, backoff=2, retry_enabled=True, default_value=[])
def get_page_ranks(urls):
    # Extract domains from the provided URLs
    domains = [urlparse(url).netloc for url in urls]
    # Prepare the API request
    api_key = os.environ.get('OPEN_PAGERANK_API_KEY')  # Ensure the API key is set in the environment
    url = 'https://openpagerank.com/api/v1.0/getPageRank'
    headers = {'API-OPR': api_key}
    params = {'domains[]': domains}

    # Make the API call
    response = requests.get(url, headers=headers, params=params, timeout=10)
    
    # Parse the JSON response
    if response.status_code == 200:
        data = response.json()
        page_ranks = [(item['page_rank_decimal'] + 1)/11 for item in data['response']]
        return page_ranks
    else:
        raise Exception(f"Error fetching page ranks: {response.status_code}")