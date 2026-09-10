import urllib.request
import urllib.parse
import re

def resolve_youtube(search_url_or_query):
    if "results?search_query=" in search_url_or_query:
        search_url = search_url_or_query
    else:
        encoded = urllib.parse.quote_plus(search_url_or_query)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"

    try:
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
            if not matches:
                matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
            if matches:
                return f"https://www.youtube.com/watch?v={matches[0]}"
    except Exception as e:
        print("Scrape error:", e)
    return search_url

if __name__ == "__main__":
    test_url = "https://www.youtube.com/results?search_query=best+hit+song+2024"
    print("Resolved to:", resolve_youtube(test_url))
