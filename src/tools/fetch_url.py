import requests
import sys


def fetch_text(url: str) -> str:
    """
    指定されたURLからテキストを取得し、Jina Readerを使用してMarkdown形式で返す。
    """
    try:
        # Jina Reader APIを使用
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"User-Agent": "Mozilla/5.0 (ResearchBot/1.0)"}

        response = requests.get(jina_url, headers=headers, timeout=30)
        response.raise_for_status()

        return response.text

    except Exception as e:
        return f"Error fetching {url}: {str(e)}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_url.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    print(fetch_text(url))
