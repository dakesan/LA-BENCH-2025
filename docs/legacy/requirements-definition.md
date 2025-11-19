# 実験手順を考えるエージェント

## Intro

実験課題と使用可能な実験手技のリストが与えられた時、目的の状態を得るために行う実験手順のリストを生成するAIエージェントを開発する。

## システム要件

- claude codeを使用する。
- 複数の独自スキルを作成する。
- claude -pコマンドを使用し、非対話的かつ自動的に結果を生成する。

## ファイル要件

### Input

以下のようなフォーマットをインプットとする。

```json
{
  "id": "private_test_2",
  "input": {
    "instruction": "EMSA [出典1]により、RNA 修飾酵素 ExpA（10-80 pmol の段階希釈 4 系列、および酵素コントロール）と tRNA 2 種（Ala tRNA または Leu tRNA 各 20 pmol、および ExpA 80 pmol 系列に対する基質コントロール）との結合を評価する。反応条件は 37 °C で 1 時間、反応スケールは 10 µL とし、反応液の終濃度組成は 50 mM HEPES–KOH pH 7.5、5 mM Mg(OAc)₂、100 mM KCl、1 mM spermine、1 mM DTT、12% (v/v) グリセロールとする。6% 非変性ポリアクリルアミドゲル（ランニングバッファー：50 mM HEPES–KOH pH 7.5、5 mM Mg(OAc)₂、1 mM DTT）で 4 °C で電気泳動し、まず SYBR Safe で tRNA を検出し、続いて CBB 染色で酵素を染色する。",
    "mandatory_objects": [
      "ExpA（20 µM ストック、酵素希釈バッファー中）",
      "tRNA（10 µM ストック）",
      "1 M HEPES–KOH (pH 7.5) ストック（4 °C 保存）",
      "4 M KCl ストック（室温保存）",
      "1 M Mg(OAc)₂ ストック（室温保存）",
      "100 mM spermine ストック（–20 °C 保存）",
      "1 M DTT ストック（–20 °C、遮光保存）",
      "酵素希釈バッファー［50 mM HEPES–KOH pH 7.5、200 mM KCl、10 mM Mg(OAc)₂、1 mM DTT、30% (v/v) グリセロール］",
      "6% 非変性ポリアクリルアミドゲル（アクリルアミド:ビス = 29:1、プロトコル外で作成済）",
      "電気泳動装置",
      "ゲル撮影装置（青色光源蛍光および白色光源対応）",
      "冷蔵チャンバー（4 °C、庫内用電源コンセント付）",
      "SYBR Safe DNA Gel Stain (10,000× stock) [出典2]",
      "CBB Stain One [出典3]"
    ],
    "source_protocol_steps": [
      {
        "id": 1,
        "text": "酵素と基質を反応溶液中で 37 °C で 1 時間インキュベートする（標準反応スケール：10 µL）。反応後のサンプルは氷上操作。"
      },
      {
        "id": 2,
        "text": "速やかに反応物を冷蔵チャンバー内で、6% 非変性ゲルを用いて電気泳動（150Vで1時間）する。このとき、結合に影響する恐れのある色素は入れない。見えにくいため注意する。"
      },
      {
        "id": 3,
        "text": "SYBR Safe で RNA を染色し、青色光源で蛍光画像を撮像する。"
      },
      {
        "id": 4,
        "text": "CBB でタンパク質を染色し、白色光源で撮像する。"
      },
      {
        "id": 5,
        "text": "両画像から酵素濃度依存的な RNA のバンドシフトを解析する。"
      }
    ],
    "expected_final_states": [
      "実験指示にある反応溶液（総計 11 系列：酵素なし・基質なしのコントロール 3 系列 + 酵素段階希釈 4 系列 × tRNA 2 種の計 8 系列）が正しく調製され、全量が使用されている。調製時の終濃度組成は 50 mM HEPES–KOH pH 7.5、5 mM Mg(OAc)₂、100 mM KCl、1 mM spermine、1 mM DTT、12% グリセロール、ExpA 0-80 pmol、tRNA 0 または 20 pmolになっている。",
      "反応溶液 11 系列の 6% 非変性ゲル電気泳動後、SYBR Safe のみで染色されたRNA 可視化画像が保存されている。",
      "同じ 11 系列のゲルをさらに CBB で染色し、タンパク質可視化画像が保存されている。"
    ],
    "references": [
      {
        "id": 1,
        "text": "Sakai, Y. et al. Dual pathways of tRNA hydroxylation ensure efficient translation. *Nat. Commun.* 10, 1, 2858 (2019). https://www.nature.com/articles/s41467-019-10750-8"
      },
      {
        "id": 2,
        "text": "Thermo Fisher Scientific. SYBR™ Safe DNA Gel Stain User Guide (MAN0002338). https://documents.thermofisher.com/TFS-Assets/LSG/manuals/sybr_safe_dna_gel_stain_man.pdf"
      },
      {
        "id": 3,
        "text": "Nacalai Tesque. CBB Stain One (Ready To Use) Product No.04543, https://www.nacalai.co.jp/products/181/"
      }
    ]
  }
}
```

## Output

```json
{
    "id": "sample_1",
    "output": {
        "procedure_steps": [
            {
                "id": 1,
                "text": "本手順は高レベルの概要です。具体的な配合量・温度・時間などの操作条件はメーカーの取扱説明書（KOD Plus neo、制限酵素、精製キット等）に厳密に従ってください。"
            },
            {
                "id": 2,
                "text": "yexP（約3 kbp）の配列を確認し、Forward/Reverse primerに付加したEcoRI/XhoIサイト、余剰塩基、読み枠、C末His-tagの有無（終止コドンの有無）など設計要件が満たされていることをin silicoで確認します。合わせてyexP内部にEcoRI/XhoIサイトが存在しないことを確認します。"
            },
            {
                "id": 3,
                "text": "大腸菌K-12ゲノムDNAの濃度・純度（A260/280など）を微量分光計で確認し、PCRに適した品質であることを評価します。必要に応じてメーカー推奨範囲に合うよう濃度調整の方針を決めます。"
            },
            {
                "id": 4,
                "text": "KOD Plus neoおよび添付Buffer類を用い、取扱説明書に準拠してPCR反応液を調製します。テンプレート、プライマー、dNTP等の比率はマニュアルのガイドラインに従います。"
            },
            {
                "id": 5,
                "text": "サーマルサイクラーを用い、3 kbp標的に適したKOD Plus neoの推奨サイクル条件でPCRを実行します。必要であれば段階的なアニーリング温度の最適化などはマニュアル記載の一般指針に従います。"
            },
            {
                "id": 6,
                "text": "PCR後、反応液の一部をローディングダイと混和し、DNAラダーとともにアガロースゲル電気泳動で増幅の有無とサイズ（約3 kbp）を確認します。ゲル撮影装置の青色光源下で安全に観察します。"
            },
            {
                "id": 7,
                "text": "バンドが単一であればPCRクリーンアップ、複数バンドが見える場合は目的バンドを切り出してゲル抽出を行い、いずれもDNA精製カラムキットの手順に厳密に従って精製します。溶出はキット推奨条件で実施します。"
            },
            {
                "id": 8,
                "text": "pET-21bベクターの品質と濃度を確認し、線形化に用いる量の方針を決めます。必要に応じて反応前に希釈や前処理の方針を検討します。"
            },
            {
                "id": 9,
                "text": "挿入断片（yexP PCR産物）およびpET-21bをEcoRIとXhoIで二重消化します。Takaraのダブルダイジェスト推奨情報に従い、対応Bufferと反応条件を設定します。"
            },
            {
                "id": 10,
                "text": "消化反応の一部をゲルで確認し、サイズが期待どおりであることを評価します。問題がなければ各消化反応をDNA精製カラムキットで精製し、キット推奨条件で溶出します。"
            },
            {
                "id": 11,
                "text": "精製した挿入断片と線形化ベクターを微量分光計で定量し、A260/280などの指標で品質を確認します。必要に応じて保存濃度に合わせて調整します。"
            },
            {
                "id": 12,
                "text": "ラベルを明確に記載し、消化済みで精製・定量済みの挿入断片（yexP）と線形化ベクター（pET-21b由来）を凍結保存します。作業記録にはプライマー情報、使用したマニュアル版、定量結果、ゲル画像の参照先を残します。"
            }
        ]
    }
}
```

## 想定される動作手順

- Claude Codeに対してクエリ入力
- Reference情報についてurlリンク先をフェッチして読み込みやすい状態にしておく
- 使えるsource protocol 



## 検証TODO

- WebFetchの自動化手法
    - CCで許可を与えてheadlessに実行
    - 別のwebfetch toolを使用
- GPT5.1でreasoning effortを条件振って実施
-
