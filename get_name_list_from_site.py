import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

def crawl_depth_1(start_url):
    found_urls = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    response = requests.get(start_url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        if href.startswith(("mailto:", "javascript:", "tel:", "#")):
            continue

        absolute_url = urljoin(start_url, href)

        parsed = urlparse(absolute_url)
        if parsed.scheme in ("http", "https"):
            found_urls.add(absolute_url)

    return found_urls


if __name__ == "__main__":
    start = "https://aniworld.to/animes/"  # echte URL einsetzen
    urls = crawl_depth_1(start)

    print("Gefundene URLs (Depth 1):")
    for u in sorted(urls):
        print(u)
        time.sleep(0.1)