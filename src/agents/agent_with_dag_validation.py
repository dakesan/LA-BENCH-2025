"""
BioPlanner × Snakemake エージェントとDAG検証エンジンの統合実装
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
from dag_validator import DAGValidator, ValidationResult
from openai import OpenAI
import sys

# Add src to path to import tools
sys.path.append(str(Path(__file__).parent.parent))
from tools.fetch_url import fetch_text
from agents.prompts import PHASE1_OBJ_ID_PROMPT, PHASE2_OP_DEF_PROMPT, PHASE3_PROC_GEN_PROMPT, FEEDBACK_PROMPT

class ExperimentPlanningAgent:
    """実験計画エージェント（DAG検証機能付き）"""

    def __init__(self, api_key: str, model_name: str = "gpt-4o", max_retries: int = 3, workspace_dir: str = "workspace"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.max_retries = max_retries
        self.validator = DAGValidator()
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Sub-directories
        (self.workspace_dir / "references").mkdir(exist_ok=True)

    def _call_llm(self, system_prompt: str, user_prompt: str, response_format=None) -> Any:
        """LLMを呼び出す共通メソッド"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.2,
            }
            
            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            
            if response_format:
                # response_formatを指定した場合はパース済みオブジェクトが返るわけではない（OpenAI Python SDKのバージョンによるが、
                # ここではjson_object指定を想定して手動パースするか、pydanticモデルを使うか。
                # 簡易的に json_object モードを使って json.loads する）
                return json.loads(content)
            return content

        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise

    def fetch_references(self, references: List[Dict]) -> str:
        """参考文献のURLからテキストを取得"""
        print("🌐 参考文献を取得中...")
        fetched_summary = []
        for ref in references:
            url = next((w for w in ref.get("text", "").split() if w.startswith("http")), None)
            if url:
                print(f"  Fetching: {url}")
                text = fetch_text(url)
                
                # Save to workspace
                ref_id = ref.get("id", "unknown")
                save_path = self.workspace_dir / "references" / f"ref_{ref_id}.txt"
                save_path.write_text(text, encoding="utf-8")
                
                fetched_summary.append(f"Reference [{ref_id}]: {text[:500]}...")
        
        return "\n\n".join(fetched_summary)

    def phase1_identify_objects(self, input_data: dict, references_text: str) -> dict:
        """
        フェーズ1: オブジェクト同定
        """
        print("=" * 60)
        print("フェーズ1: オブジェクト同定エージェント実行中...")
        print("=" * 60)

        instruction = input_data["input"]["instruction"]
        mandatory_objects = input_data["input"]["mandatory_objects"]
        
        # プロンプト構築
        prompt = PHASE1_OBJ_ID_PROMPT.format(
            instruction=instruction,
            mandatory_objects=json.dumps(mandatory_objects, ensure_ascii=False)
        )
        if references_text:
            prompt += f"\n\n## 参考文献情報\n{references_text}"

        # LLM呼び出し (JSONモード)
        result = self._call_llm(
            system_prompt="You are a laboratory automation expert. Output JSON.",
            user_prompt=prompt,
            response_format={"type": "json_object"}
        )
        
        # ワークスペースに保存
        (self.workspace_dir / "1_objects.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        print("✅ フェーズ1完了")
        return result

    def phase2_define_operations(
        self, input_data: dict, phase1_result: dict, feedback: Optional[str] = None
    ) -> dict:
        """
        フェーズ2: オペレーション定義
        """
        print("=" * 60)
        print("フェーズ2: オペレーション定義エージェント実行中...")
        if feedback:
            print("⚠️ フィードバックあり再試行")
        print("=" * 60)

        instruction = input_data["input"]["instruction"]
        source_protocol = input_data["input"].get("source_protocol_steps", [])
        identified_objects = phase1_result["identified_objects"]

        prompt = PHASE2_OP_DEF_PROMPT.format(
            instruction=instruction,
            identified_objects=json.dumps(identified_objects, ensure_ascii=False),
            source_protocol=json.dumps(source_protocol, ensure_ascii=False)
        )
        
        if feedback:
            prompt += "\n\n" + FEEDBACK_PROMPT.format(feedback=feedback)

        # LLM呼び出し
        result = self._call_llm(
            system_prompt="You are a laboratory automation expert. Output JSON.",
            user_prompt=prompt,
            response_format={"type": "json_object"}
        )

        # ワークスペースに保存
        (self.workspace_dir / "2_operations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        print("✅ フェーズ2完了")
        return result

    def validate_with_retry(
        self, input_data: dict, phase1_result: dict
    ) -> tuple[dict, ValidationResult]:
        """
        フェーズ2の出力をDAG検証し、エラーがあれば修正を試みる
        """
        phase2_result = None
        validation_result = None

        for attempt in range(self.max_retries):
            print(f"\n{'=' * 60}")
            print(f"検証試行 {attempt + 1}/{self.max_retries}")
            print(f"{'=' * 60}")

            # フィードバックを生成（2回目以降）
            feedback = None
            if attempt > 0 and validation_result:
                feedback = self._generate_feedback(validation_result)

            # フェーズ2を実行
            phase2_result = self.phase2_define_operations(
                input_data, phase1_result, feedback
            )

            # DAG検証
            self.validator.load_from_phases(phase1_result, phase2_result)
            validation_result = self.validator.validate()

            print("\n" + "=" * 60)
            print("DAG検証結果:")
            print("=" * 60)
            print(validation_result.to_json())

            if validation_result.valid:
                print("\n✅ 検証成功！")
                break
            else:
                print(f"\n❌ 検証失敗（{len(validation_result.errors)}個のエラー）")
                if attempt < self.max_retries - 1:
                    print("→ エラーをフィードバックして再試行します...")

        return phase2_result, validation_result

    def _generate_feedback(self, validation_result: ValidationResult) -> str:
        """検証結果から、LLMに渡すフィードバックメッセージを生成"""
        feedback_lines = [
            "前回生成したオペレーションには以下のエラーがありました。修正してください:\n"
        ]

        for i, error in enumerate(validation_result.errors, 1):
            feedback_lines.append(f"{i}. {error.message}")
            feedback_lines.append(f"   提案: {error.suggestion}\n")

        return "\n".join(feedback_lines)

    def phase3_generate_procedure(
        self,
        input_data: dict,
        phase1_result: dict,
        phase2_result: dict,
        validation_result: ValidationResult,
        references_text: str
    ) -> dict:
        """
        フェーズ3: 手順書生成
        """
        print("\n" + "=" * 60)
        print("フェーズ3: 手順書生成エージェント実行中...")
        print("=" * 60)

        instruction = input_data["input"]["instruction"]
        operations = phase2_result["operations"]
        
        # 実行順序でソート
        execution_order = validation_result.execution_order
        ordered_ops = []
        for op_id in execution_order:
            op = next((o for o in operations if o["operation_id"] == op_id), None)
            if op:
                ordered_ops.append(op)

        prompt = PHASE3_PROC_GEN_PROMPT.format(
            instruction=instruction,
            operations=json.dumps(ordered_ops, ensure_ascii=False),
            references=references_text
        )

        # LLM呼び出し
        result = self._call_llm(
            system_prompt="You are a laboratory automation expert. Output JSON.",
            user_prompt=prompt,
            response_format={"type": "json_object"}
        )

        print("✅ フェーズ3完了")
        return result

    def run(self, input_data: dict) -> dict:
        """エージェント全体を実行"""
        print("\n" + "🚀" * 30)
        print(f"実験計画エージェント開始: {input_data.get('id', 'unknown')}")
        print("🚀" * 30 + "\n")
        
        # 参考文献取得
        references = input_data["input"].get("references", [])
        references_text = self.fetch_references(references)

        # フェーズ1: オブジェクト同定
        phase1_result = self.phase1_identify_objects(input_data, references_text)

        # フェーズ2: オペレーション定義（DAG検証付き）
        phase2_result, validation_result = self.validate_with_retry(
            input_data, phase1_result
        )

        if not validation_result.valid:
            print("\n❌ 最大試行回数に達しましたが、検証に失敗しました。")
            return {
                "success": False,
                "error": "DAG validation failed after maximum retries",
                "validation_result": validation_result.to_dict(),
            }

        # フェーズ3: 手順書生成
        phase3_result = self.phase3_generate_procedure(
            input_data, phase1_result, phase2_result, validation_result, references_text
        )

        print("\n" + "🎉" * 30)
        print("実験計画エージェント完了")
        print("🎉" * 30 + "\n")

        return {"success": True, "output": phase3_result}


def main():
    """使用例"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEYが設定されていません")
        return

    # 入力データ（LA-Benchの形式）
    # 実際にはファイルから読み込む
    input_data = {
        "id": "demo_experiment",
        "input": {
            "instruction": "EMSA により、RNA 修飾酵素 ExpA と tRNA との結合を評価する。",
            "mandatory_objects": [
                "ExpA（20 µM ストック）",
                "tRNA（10 µM ストック）",
                "バッファー類",
            ],
            "source_protocol_steps": [
                {
                    "id": 1,
                    "text": "酵素と基質を反応溶液中で 37 °C で 1 時間インキュベートする。",
                },
                {"id": 2, "text": "6% 非変性ゲルで電気泳動する。"},
                {"id": 3, "text": "SYBR Safe で RNA を染色する。"},
                {"id": 4, "text": "CBB でタンパク質を染色する。"},
            ],
            "expected_final_states": ["SYBR Safe 染色画像", "CBB 染色画像"],
            "references": []
        },
    }

    # エージェント実行
    agent = ExperimentPlanningAgent(api_key=api_key)
    result = agent.run(input_data)

    print("\n" + "=" * 60)
    print("最終結果:")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
