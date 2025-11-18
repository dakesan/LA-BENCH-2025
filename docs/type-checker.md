## BioPlanner × Snakemake: エージェント的実装による実験手順生成アーキテクチャ

「BioPlanner × Snakemake」のアイデアは、LLMの柔軟な解釈能力とワークフローエンジンの厳密性を組み合わせる、非常に先進的かつ有望なアプローチです。ベースライン実装が単一のプロンプトで全手順を生成するのに対し、本アーキテクチャはタスクを複数のフェーズに分解し、それぞれを専門の思考プロセス（プロンプト）で解決する「エージェント的」な実装を目指します。

以下に、その具体的な実装手順とプロンプティング戦略を提案します。

---

### 全体アーキテクチャ：3フェーズの思考プロセス`    

エージェントは、人間が実験計画を立てるプロセスを模倣し、以下の3つのフェーズを順に実行します。

1.  **フェーズ1: オブジェクト同定エージェント (Object Identifier)**
    *   **目的**: 実験全体で登場する全ての「モノ」を洗い出し、ファイルパスのように一意な名前を付ける。
    *   **思考プロセス**: 指示書を読み、試薬、サンプル、中間生成物、最終成果物をリストアップする。

2.  **フェーズ2: オペレーション定義エージェント (Operation Definer)**
    *   **目的**: フェーズ1で同定したオブジェクト間の変換操作（オペレーション）を定義する。
    *   **思考プロセス**: 「何と何を混ぜて何を作るか」「何を測定して何を得るか」という単位で、BioPlannerの疑似関数のように入出力を定義する。

3.  **フェーズ3: 手順書生成エージェント (Procedure Writer)**
    *   **目的**: フェーズ2で定義したオペレーションの依存関係を解決し、人間が実行可能な自然言語の手順書に変換する。
    *   **思考プロセス**: Snakemakeが実行順序を決めるように、オペレーションのグラフを頭の中で描き、それを時系列のステップバイステップの指示に書き起こす。

この段階的なプロセスにより、複雑な依存関係を持つ実験計画においても、論理的で再現性の高い手順を生成することが可能になります。

---

### フェーズ1: オブジェクト同定エージェント

このフェーズの鍵は、ウェットな実験における物理的な実体を、コンピュータが扱える「ファイル」の概念に抽象化することです。

#### プロンプト戦略

```
あなたは、実験室の全てをデジタルツインとして管理する超几帳面なラボマネージャーです。あなたの仕事は、与えられた実験プロトコルを読み解き、そこで使用、生成、変化する全ての「オブジェクト」をファイルパスの形式でリストアップすることです。

# 指示
- `mandatory_objects` は `objects/initial/` ディレクトリに配置します。
- 実験の途中で生まれる中間生成物は `objects/intermediate/` に配置します。
- `expected_final_states` から最終成果物を推測し、`objects/final/` に配置します。
- オブジェクト名は、内容が明確にわかるように具体的に命名してください（例: `ExpA_stock_20uM.reagent`）。
- 特に、EMSAの反応液のように複数系列あるものは、`reaction_mix_A1.sample` のようにインデックスを付けて区別してください。

# 入力JSON
{ここにユーザー提供の入力JSONを挿入}

# 出力形式 (JSON)
{
  "identified_objects": {
    "initial": [
      "objects/initial/ExpA_stock_20uM.reagent",
      "objects/initial/tRNA_Ala_10uM.reagent",
      ...
    ],
    "intermediate": [
      "objects/intermediate/ExpA_dilution_series_1.sample",
      "objects/intermediate/ExpA_dilution_series_2.sample",
      ...
      "objects/intermediate/reaction_mix_A1.sample",
      "objects/intermediate/reaction_mix_A2.sample",
      ...
    ],
    "final": [
      "objects/final/sybr_safe_stained_gel.image",
      "objects/final/cbb_stained_gel.image"
    ]
  }
}
```

#### このフェーズの価値

- **依存関係の可視化**: 全ての「モノ」がリスト化されることで、後のフェーズで操作の繋がりを追いやすくなります。
- **曖昧性の排除**: 「反応液」のような曖昧な言葉が、「11系列の具体的なサンプル」として明確に定義されます。

---

### フェーズ2: オペレーション定義エージェント

次に、オブジェクト間の関係性を「ルール」として定義します。これはSnakemakeの`rule`やBioPlannerの疑似関数に相当します。

#### プロンプト戦略

```
あなたは、実験操作をワークフローの「ルール」に変換する専門家です。フェーズ1で同定されたオブジェクトリストを使い、それらを繋ぐ全ての操作を定義してください。

# 指示
- 各操作は、Snakemakeのルールのように`input`と`output`を明確に持つJSONオブジェクトとして定義します。
- `operation_id`には、`prepare_reaction_mix`や`run_electrophoresis`のような操作名を入れてください。
- `text_description`には、その操作の自然言語による説明を簡潔に記述します。
- `input`と`output`には、フェーズ1で定義したオブジェクトのパスを正確に記述してください。

# 入力: フェーズ1の出力
{ここにフェーズ1で生成されたJSONを挿入}

# 出力形式 (JSON)
{
  "operations": [
    {
      "operation_id": "prepare_enzyme_dilutions",
      "text_description": "ExpAストックを酵素希釈バッファーで段階希釈する",
      "input": [
        "objects/initial/ExpA_stock_20uM.reagent",
        "objects/initial/enzyme_dilution_buffer.reagent"
      ],
      "output": [
        "objects/intermediate/ExpA_dilution_series_1.sample",
        "objects/intermediate/ExpA_dilution_series_2.sample",
        "objects/intermediate/ExpA_dilution_series_3.sample",
        "objects/intermediate/ExpA_dilution_series_4.sample"
      ]
    },
    {
      "operation_id": "prepare_reaction_mixes",
      "text_description": "11系列の反応液を調製する",
      "input": [
        "objects/intermediate/ExpA_dilution_series_1.sample",
        ...,
        "objects/initial/tRNA_Ala_10uM.reagent",
        "objects/initial/tRNA_Leu_10uM.reagent",
        "objects/initial/HEPES_KOH_stock.reagent",
        ...
      ],
      "output": [
        "objects/intermediate/reaction_mix_A1.sample",
        ...
      ]
    },
    {
      "operation_id": "incubate_reactions",
      "text_description": "反応液を37℃で1時間インキュベートする",
      "input": [
        "objects/intermediate/reaction_mix_A1.sample",
        ...
      ],
      "output": [
        "objects/intermediate/incubated_mix_A1.sample",
        ...
      ]
    },
    ...
  ]
}
```

#### このフェーズの価値

- **プロセスの構造化**: 曖昧な実験の流れが、入出力を伴う明確な操作の集合として再定義されます。
- **並列化・依存関係の明確化**: どの操作がどの操作に依存しているか、あるいはどの操作が並列で実行可能かが、この構造から自動的に判断できます。

---

### フェーズ3: 手順書生成エージェント

最後に、定義されたオペレーションのリストを、人間が実行できる論理的な順序の指示書に変換します。

#### プロンプト戦略

```
あなたは、熟練の実験指導者です。与えられたオペレーションのリスト（依存関係グラフ）を解析し、初心者が間違いなく実行できる、ステップバイステップの美しい手順書を作成してください。

# 指示
- オペレーションの`input`が他のオペレーションの`output`になっている場合、その`output`を生成する操作を先に行う必要があります。
- 依存関係を解決し、論理的に正しい実行順序を構築してください。
- 各オペレーションの`text_description`を元に、より丁寧で具体的な指示文を生成します。
- 最終的な出力は、LA-Benchの指定する`procedure_steps`のJSON形式にしてください。

# 入力: フェーズ2の出力
{ここにフェーズ2で生成されたJSONを挿入}

# 出力形式 (JSON)
{
  "procedure_steps": [
    {
      "id": 1,
      "text": "まず、実験に使用する酵素ExpAの段階希釈系列を調製します。酵素希釈バッファーを用いて、ストック溶液から4点の希釈液を作成します。"
    },
    {
      "id": 2,
      "text": "次に、EMSAに必要な11系列の反応液を調製します。先ほど作成した酵素希釈系列、各種tRNA、およびバッファー類を、指示された終濃度になるように混合してください。"
    },
    {
      "id": 3,
      "text": "調製した11系列の反応液を、37℃のインキュベーターで正確に1時間インキュベートします。"
    },
    ...
  ]
}
```

#### このフェーズの価値

- **論理的な順序付け**: Snakemakeのように依存関係を解決し、実行可能な手順を生成します。
- **人間可読な形式への翻訳**: 構造化されたオペレーションを、自然で分かりやすい指示文に変換します。
- **タスク要求への準拠**: 最終的に、コンペティションで要求される出力形式に準拠したアウトプットを生成します。

---

### まとめ

この3フェーズ・アーキテクチャは、単一のLLMコールに頼るのではなく、タスクを論理的なサブタスクに分割し、それぞれに特化した思考（プロンプト）を適用することで、より複雑で信頼性の高い計画を生成することを目指します。これはまさに「エージェント」的なアプローチであり、ベースライン実装からの大きな飛躍となるでしょう。
