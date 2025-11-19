import requests
from bs4 import BeautifulSoup
import sys
import time

def fetch_text(url: str) -> str:
    """
    指定されたURLからテキストを取得し、簡易的に要約して返す。
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (ResearchBot/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 不要な要素を削除
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # 本文抽出（簡易版: pタグやhタグなどを中心に）
        lines = []
        
        # タイトル取得
        if soup.title:
            lines.append(f"# Title: {soup.title.string}")
        
        # 見出しと本文
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'article']):
            text = tag.get_text(strip=True)
            if len(text) > 20: # 短すぎるテキストを除外
                lines.append(text)
                
        # 文字数制限（トークン節約のため）
        full_text = "\n".join(lines)
        if len(full_text) > 5000:
            full_text = full_text[:5000] + "\n...(truncated)..."
            
        return full_text
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_url.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    print(fetch_text(url))
