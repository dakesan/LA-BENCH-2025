ご提示いただいた「BioPlanner × Snakemake」の思想を取り入れた3フェーズ思考プロセスは非常に強力です。これを`claude code`で実行可能な具体的なアーキテクチャ（ディレクトリ構成、ツール、プロンプト）に落とし込みます。

`claude code` はツール（スクリプト）の実行とファイル操作が得意なため、各フェーズを単なる思考だけでなく、実際に中間ファイル（JSON）を出力させることで、検証性と精度を高める設計にします。

---

# 実験手順生成エージェント アーキテクチャ

## 1. ディレクトリ構成

```text
.
├── input/
│   └── task.json          # ユーザーからの入力 (ご提示のInputフォーマット)
├── output/
│   └── result.json        # 最終出力
├── workspace/             # 中間生成物を格納する場所
│   ├── 1_objects.json
│   ├── 2_operations.json
│   └── references/        # Webから取得した情報のキャッシュ
├── tools/
│   ├── fetch_url.py       # 指定URLのテキストを取得するスクリプト
│   └── common.py          # ユーティリティ
└── prompts/
    └── master_instruction.md # エージェントへの指示書
```

---

## 2. 独自スキル（Tools）の実装

`claude code` が Webブラウジングを行うためのPythonスクリプトを用意します。これをエージェントが必要に応じて呼び出します。

**tools/fetch_url.py**
（`pip install requests beautifulsoup4` が必要）

```python
import sys
import json
import requests
from bs4 import BeautifulSoup

def fetch_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (ResearchBot/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 本文抽出（簡易版: pタグやhタグなどを中心に）
        lines = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'article']):
            text = tag.get_text(strip=True)
            if len(text) > 20: # 短すぎるテキストを除外
                lines.append(text)
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_url.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    print(fetch_text(url))
```

---

## 3. プロンプト設計 (master_instruction.md)

`claude code` に渡す指示書です。ご提示の3フェーズ思考プロセスを具体的なアクションとして記述します。

```markdown
# 実験手順生成エージェント 指示書

あなたは熟練したバイオ実験の自動化エンジニアです。
`input/task.json` を読み込み、論理的かつ実行可能な実験手順書 `output/result.json` を生成してください。

## 実行プロセス

以下の手順を順番に実行してください。各ステップで中間ファイルを作成し、思考過程を保存すること。

### Step 1: 外部情報の収集 (Web Fetching)
1. `input/task.json` の `references` リストにあるURLを確認する。
2. `tools/fetch_url.py` を使用して、各URLからテキスト情報を取得する。
3. 取得した情報を要約し、`workspace/references/` フォルダにテキストファイルとして保存する。
   - 特に「プロトコル条件」「試薬の組成」「保存条件」に注目すること。

### Step 2: オブジェクト同定 (Phase 1: Object Identifier)
実験に登場する全ての「物理的実体」をファイルパス形式で定義する。
- 入力: `input/task.json` および `workspace/references/` 内の情報
- 思考プロセス:
    - `input/task.json` の `mandatory_objects` を `objects/initial/` にマッピング。
    - プロトコル手順から推測される中間生成物を `objects/intermediate/` にマッピング（例: 希釈系列、反応混合液）。
    - 最終成果物を `objects/final/` にマッピング。
- 出力: `workspace/1_objects.json` に保存。

### Step 3: オペレーション定義 (Phase 2: Operation Definer)
オブジェクト間の変換ルール（関数）を定義する。
- 入力: `workspace/1_objects.json`
- 思考プロセス:
    - 各操作を `input` (オブジェクト) と `output` (オブジェクト) を持つ関数として定義。
    - 操作IDと操作内容の記述を含める。
    - Snakemakeのルールのように依存関係が明確になるようにする。
- 出力: `workspace/2_operations.json` に保存。

### Step 4: 手順書生成 (Phase 3: Procedure Writer)
オペレーションリストを、人間が実行可能な自然言語の手順書に変換する。
- 入力: `workspace/2_operations.json`
- 要件:
    - 依存関係を解決し、時系列順に並べる。
    - 具体的数値（温度、時間、量）を含める。
    - `input/task.json` の `expected_final_states` を満たすことを確認する。
    - 出力フォーマットは下記の「Output Schema」に厳密に従うこと。
- 出力: `output/result.json` に保存。

## Output Schema

```json
{
  "id": "<inputのid>",
  "output": {
    "procedure_steps": [
      {
        "id": 1,
        "text": "操作指示文..."
      }
    ]
  }
}
```

## 制約事項
- 推測が必要な箇所は、一般的な分子生物学の知識（EMSA, PCR等）で補完し、その旨をメモに残すこと。
- ファイル操作やコマンド実行は、失敗した場合に原因を分析して再試行すること。
```

---

## 4. 実行コマンド

`claude code` を非対話モード（`-p`）で起動し、プロンプトファイルを読み込ませて実行します。

```bash
# 準備: ツールの依存関係インストール
pip install requests beautifulsoup4

# 実行
cat prompts/master_instruction.md | claude -p "この指示書に従って input/task.json から実験手順を生成してください。"
```

---

## 5. 検証・改善のポイント (TODOへの回答)

ご提示いただいた「検証TODO」に対する具体的な実装方針です。

### A. WebFetchの自動化手法
上記のアーキテクチャでは、**`tools/fetch_url.py` を `claude code` に叩かせる** 方式を採用しました。
- **利点**: `claude code` 自体がheadlessブラウザを持っていなくても、Python経由で軽量にテキスト取得できます。
- **工夫**: 取得したHTMLをそのまま渡すとトークン数が膨大になるため、スクリプト側（Python）またはClaude側で「要約して保存」させるステップを入れています。

### B. Reasoning Effort (推論の深さ) の調整
Claude 3.5 Sonnet / Opus (または将来のGPT-5系) を使う場合、以下のようにプロンプトで思考の粒度を指定します。

- **Low Effort**: 「入力から直接手順を書いてください」
- **High Effort (今回採用)**: 「オブジェクト定義 → 操作定義 → 手順生成 という中間ステップを必ず経由し、各段階でJSONファイルを出力して自己レビューしてください」

この**Chain of Thought with Artifacts (中間生成物付き思考連鎖)** パターンにより、複雑な実験プロトコルでも整合性の取れた手順を生成させることが可能になります。

### C. エラーハンドリング
プロトコル生成において「試薬が足りない」「手順が繋がらない」といった論理エラーが発生した場合、Step 3 (Operation Definer) の段階でグラフが繋がらないため検知可能です。
プロンプトに「全ての `objects/final/` に到達するパスが存在するか確認せよ」という指示を追加すると、さらに堅牢になります。