from time import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import time
db_file="instance/aniworld.db"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_html(start_url):
    found_urls = []

    response = requests.get(start_url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    soup = soup.prettify()
    with open("output1.html", "w") as file:
        file.write(str(soup))
    

get_html("https://s.to/serie/one-piece-2023/staffel-1/episode-1")