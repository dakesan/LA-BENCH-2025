#!/usr/bin/env python3
"""
LA-Bench 2025: 実験手順生成タスク
Baseline Implementation with Responses API (Standalone Python Script)
GitHub: https://github.com/lasa-or-jp/la-bench.git

Usage:
    export OPENAI_API_KEY="your-api-key"
    python baseline_responses_api.py
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

# Data processing
import pandas as pd
from pydantic import BaseModel, Field

# OpenAI API
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAIライブラリが利用できません")
    print("pip install openai でインストールしてください")
    exit(1)

# Progress bar
from tqdm.auto import tqdm

# Logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Model settings (Responses API)
MODEL_NAME = "gpt-5.1"
REASONING_EFFORT = "medium"  # low, medium, high

# Judge model settings
JUDGE_MODEL = "gpt-4.1-mini"
JUDGE_TEMPERATURE = 0.2

# Input/Output paths
JSONL_PATH = 'data/example/example.jsonl'
OUTPUT_DIR = Path('./outputs/runs')


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class Step:
    id: int
    text: str


@dataclass
class ReferenceEntry:
    id: int
    text: str


@dataclass
class ExampleInput:
    instruction: str
    mandatory_objects: Set[str] = field(default_factory=set)
    source_protocol_steps: List[Step] = field(default_factory=list)
    expected_final_states: Set[str] = field(default_factory=set)
    references: List[ReferenceEntry] = field(default_factory=list)


@dataclass
class ExampleOutput:
    procedure_steps: List[Step] = field(default_factory=list)


@dataclass
class Measurement:
    specific_criteria: Dict[str, int] = field(default_factory=dict)


@dataclass
class ExampleSample:
    id: str
    input: ExampleInput
    output: ExampleOutput
    measurement: Optional[Measurement] = None


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class StepModel(BaseModel):
    id: int = Field(ge=1, description="ステップ番号")
    text: str = Field(description="実験手順の詳細な説明")


class GeneratedOutput(BaseModel):
    procedure_steps: List[StepModel] = Field(
        description="実験手順のリスト",
        min_items=1,
        max_items=50
    )


class JudgeOutput(BaseModel):
    general_score: float = Field(ge=0, le=5)
    specific_score: float = Field(ge=0, le=5)
    final_score: float = Field(ge=0, le=10)
    general_reason: str
    specific_matches: List[str] = []
    notes: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def _to_set(x):
    return set(x) if isinstance(x, (list, set, tuple)) else set()


def _to_list(x):
    return list(x) if isinstance(x, (list, set, tuple)) else (x if isinstance(x, list) else [])


def _to_steps(x) -> List[Step]:
    steps: List[Step] = []
    arr = _to_list(x)
    if not arr:
        return steps
    if isinstance(arr[0], dict):
        for it in arr:
            try:
                sid = int(it.get("id", len(steps) + 1))
            except Exception:
                sid = len(steps) + 1
            steps.append(Step(id=sid, text=str(it.get("text", "")).strip()))
    else:
        for idx, s in enumerate(arr, start=1):
            steps.append(Step(id=idx, text=str(s).strip()))
    return steps


def _to_references(x) -> List[ReferenceEntry]:
    refs: List[ReferenceEntry] = []
    arr = _to_list(x)
    if not arr:
        return refs
    if isinstance(arr[0], dict):
        for it in arr:
            try:
                rid = int(it.get("id", len(refs) + 1))
            except Exception:
                rid = len(refs) + 1
            refs.append(ReferenceEntry(id=rid, text=str(it.get("text", "")).strip()))
    else:
        for idx, ref in enumerate(arr, start=1):
            refs.append(ReferenceEntry(id=idx, text=str(ref).strip()))
    return refs


def parse_sample(obj: Dict[str, Any]) -> ExampleSample:
    sid = obj.get("id") or obj.get("sample_id") or "unknown"
    i = obj.get("input", {})
    o = obj.get("output", {})
    m = obj.get("measurement", {})

    # Measurement.specific_criteria を dict に正規化（list形式も許容）
    sc_raw = m.get("specific_criteria", {})
    sc: Dict[str, int] = {}
    if isinstance(sc_raw, dict):
        for k, v in sc_raw.items():
            try:
                sc[str(k)] = int(v)
            except Exception:
                pass
    elif isinstance(sc_raw, list):
        for it in sc_raw:
            try:
                k = it.get("item")
                v = int(it.get("score", 0))
                if k:
                    sc[str(k)] = v
            except Exception:
                pass

    sample = ExampleSample(
        id=str(sid),
        input=ExampleInput(
            instruction=str(i.get("instruction", "")).strip(),
            mandatory_objects=_to_set(i.get("mandatory_objects", [])),
            source_protocol_steps=_to_steps(i.get("source_protocol_steps", [])),
            expected_final_states=_to_set(i.get("expected_final_states", [])),
            references=_to_references(i.get("references", [])),
        ),
        output=ExampleOutput(
            procedure_steps=_to_steps(o.get("procedure_steps", []))
        ),
        measurement=Measurement(specific_criteria=sc) if sc else None
    )
    return sample


def load_example_jsonl(path: str):
    samples = []
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSONL not found: {p}")
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            print(f"⚠️ JSONL parse error: {e}")
            continue
        samples.append(parse_sample(obj))
    return samples


# ============================================================================
# Generation Functions (Responses API)
# ============================================================================

def build_input_text(sample: ExampleSample) -> str:
    """
    Responses API用に単一の入力テキストを構築
    """
    lines = []
    lines.append("あなたは生命科学実験の専門家です。以下の Input を読み、")
    lines.append("日本語で実行可能な実験手順（procedure_steps）を返してください。")
    lines.append("制約: ステップ数は最大50、各ステップは10文以下、idは1から昇順。")
    lines.append("")
    lines.append(f"【実験指示】\n{sample.input.instruction}")

    if sample.input.mandatory_objects:
        lines.append("\n【使用する物品】")
        for it in sorted(sample.input.mandatory_objects):
            lines.append(f"- {it}")

    if sample.input.source_protocol_steps:
        lines.append("\n【元プロトコルの手順（参考）】")
        for st in sample.input.source_protocol_steps:
            lines.append(f"- {st.id}. {st.text}")

    if sample.input.expected_final_states:
        lines.append("\n【期待される最終状態】")
        for fs in sorted(sample.input.expected_final_states):
            lines.append(f"- {fs}")

    if sample.input.references:
        lines.append("\n【参考文献】")
        for ref in sample.input.references:
            lines.append(f"- [{ref.id}] {ref.text}")

    return "\n".join(lines)


def generate_outputs(samples: list[ExampleSample], api_key: str) -> list[dict]:
    client = OpenAI(api_key=api_key)
    results: list[dict] = []

    for sm in tqdm(samples, desc="Generating procedures (Responses API)"):
        input_text = build_input_text(sm)
        try:
            # Responses APIを使用してreasoning effortを制御
            response = client.responses.create(
                model=MODEL_NAME,
                input=input_text,
                reasoning={"effort": REASONING_EFFORT},
                response_format=GeneratedOutput,
            )

            # 構造化された出力をパース
            parsed: GeneratedOutput = response.parsed_output
            steps = [
                Step(id=s.id, text=s.text)
                for s in sorted(parsed.procedure_steps, key=lambda x: x.id)
            ][:50]

        except Exception as e:
            print(f"❌ 生成失敗: {sm.id}: {e}")
            steps = []

        results.append({
            "id": sm.id,
            "procedure_steps": [{"id": s.id, "text": s.text} for s in steps],
        })

    print(f"✅ 生成完了: {len(results)} samples (reasoning={REASONING_EFFORT})")
    return results


# ============================================================================
# Evaluation Functions
# ============================================================================

def build_judge_messages(sample: ExampleSample, steps: List[Step]) -> list[dict]:
    system = (
        "あなたは生命科学実験の専門家であり、公平な採点者です。"
        "以下の基準に従って、与えられた Input と生成手順（Output）を評価し、"
        "general_score(0-5) と specific_score(0-5) と final_score(0-10) を出力してください。"
        "\n\n[共通採点基準 5点満点]\n"
        "加点(+1ずつ): 1) 実験指示のパラメータ反映, 2) 使用する物品の反映, 3) 元手順の論理反映, 4) 期待される最終状態の達成, 5) 適切な補完。\n"
        "減点: 不自然な日本語/ハルシネーション, 計算ミス, 手順矛盾。\n"
        "上限: 入力手順の丸写し等の過度の安全性が見られる場合、general_score は最大2点に制限。\n\n"
        "[個別採点基準 5点満点]\n"
        "与えられた specific_criteria の各 item が手順に含まれる/満たすなら、その score を加点（合計5点で上限）。"
    )

    parts = []
    parts.append(f"【実験指示】\n{sample.input.instruction}")
    if sample.input.mandatory_objects:
        parts.append("\n【使用する物品】")
        for it in sorted(sample.input.mandatory_objects):
            parts.append(f"- {it}")
    if sample.input.source_protocol_steps:
        parts.append("\n【元プロトコルの手順（参考）】")
        for st in sample.input.source_protocol_steps:
            parts.append(f"- {st.id}. {st.text}")
    if sample.input.expected_final_states:
        parts.append("\n【期待される最終状態】")
        for fs in sorted(sample.input.expected_final_states):
            parts.append(f"- {fs}")
    if sample.input.references:
        parts.append("\n【参考文献】")
        for ref in sample.input.references:
            parts.append(f"- [{ref.id}] {ref.text}")

    parts.append("\n【生成手順（Output）】")
    for s in steps:
        parts.append(f"- {s.id}. {s.text}")

    parts.append("\n【specific_criteria】")
    if sample.measurement and sample.measurement.specific_criteria:
        for item, sc in sample.measurement.specific_criteria.items():
            parts.append(f"- ({int(sc)}点) {item}")
    else:
        parts.append("- なし")

    user = "\n".join(parts)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def judge_with_llm(samples: List[ExampleSample], generated: list[dict], api_key: str) -> pd.DataFrame:
    client = OpenAI(api_key=api_key)
    proc_map = {g['id']: [Step(id=it['id'], text=it['text']) for it in g['procedure_steps']] for g in generated}
    rows = []
    quota_exhausted = False

    def _is_insufficient_quota(err: Exception) -> bool:
        s = str(err)
        return 'insufficient_quota' in s or 'You exceeded your current quota' in s

    for sm in tqdm(samples, desc="Evaluating procedures"):
        if quota_exhausted:
            print(f"⏭️ スキップ採点: {sm.id}（クォータ不足）")
            rows.append({
                'id': sm.id,
                'general_score': 0.0,
                'specific_score': 0.0,
                'total_score': 0.0,
                'notes': 'skipped_due_to_quota',
            })
            continue
        steps = proc_map.get(sm.id, [])
        msgs = build_judge_messages(sm, steps)
        try:
            completion = client.chat.completions.parse(
                model=JUDGE_MODEL,
                messages=msgs,
                temperature=JUDGE_TEMPERATURE,
                response_format=JudgeOutput,
            )
            parsed: JudgeOutput = completion.choices[0].message.parsed
            rows.append({
                'id': sm.id,
                'general_score': parsed.general_score,
                'specific_score': parsed.specific_score,
                'total_score': parsed.final_score,
                'notes': parsed.notes or '',
            })
        except Exception as e:
            print(f"❌ 評価失敗: {sm.id}: {e}")
            if _is_insufficient_quota(e):
                print("⚠️ APIクォータ不足のため、以降の採点を中断します。プラン/課金設定をご確認ください。")
                quota_exhausted = True
            rows.append({
                'id': sm.id,
                'general_score': 0.0,
                'specific_score': 0.0,
                'total_score': 0.0,
                'notes': 'evaluation_failed',
            })
    return pd.DataFrame(rows)


# ============================================================================
# Main Function
# ============================================================================

def main():
    print("=" * 60)
    print("LA-Bench 2025 Baseline Implementation (Responses API)")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY環境変数が設定されていません")
        print("設定方法: export OPENAI_API_KEY='your-api-key'")
        exit(1)

    print(f"✅ OpenAI API Key: {'*' * 20}{api_key[-4:]}")
    print(f"📊 Model: {MODEL_NAME}")
    print(f"🧠 Reasoning Effort: {REASONING_EFFORT}")
    print()

    # Load samples
    try:
        samples = load_example_jsonl(JSONL_PATH)
        print(f'✅ Loaded {len(samples)} samples from {JSONL_PATH}')
    except Exception as e:
        print(f'❌ Load error: {e}')
        exit(1)

    # Generate outputs
    print("\n" + "=" * 60)
    print("Step 1: 実験手順の生成 (Responses API)")
    print("=" * 60)
    generated_results = generate_outputs(samples, api_key)
    if generated_results:
        print(f"例: {generated_results[0]['id']} → {len(generated_results[0]['procedure_steps'])} steps")

    # Save generated results to JSONL
    ts = time.strftime('%Y%m%d_%H%M%S')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUTPUT_DIR / f'generated_responses_{ts}.jsonl'
    with jsonl_path.open('w', encoding='utf-8') as f:
        for rec in generated_results:
            obj = {"id": rec["id"], "output": {"procedure_steps": rec["procedure_steps"]}}
            line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            f.write(line + "\n")
    print(f"📄 Saved JSONL: {jsonl_path}")

    # Evaluate with LLM-as-a-judge
    print("\n" + "=" * 60)
    print("Step 2: LLM-as-a-judge 評価")
    print("=" * 60)
    df = judge_with_llm(samples, generated_results, api_key)
    print(f"✅ LLM-as-a-judge: Scored {len(df)} samples (0-10)")
    print("\n評価結果:")
    print(df[['id', 'general_score', 'specific_score', 'total_score']])

    # Save evaluation results to CSV
    csv_path = OUTPUT_DIR / f'eval_responses_{ts}.csv'
    df.to_csv(csv_path, index=False, encoding="utf_8_sig")
    print(f'\n📄 Saved CSV: {csv_path}')

    print("\n" + "=" * 60)
    print("✅ 処理完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
