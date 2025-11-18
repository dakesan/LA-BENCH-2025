"""
DAG Validation Engine for BioPlanner × Snakemake
実験計画の論理的整合性を検証するエンジン
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json


@dataclass
class ValidationError:
    """検証エラーを表すクラス"""

    type: str
    operation_id: Optional[str] = None
    object_path: Optional[str] = None
    message: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "operation_id": self.operation_id,
            "object_path": self.object_path,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """検証結果を表すクラス"""

    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "execution_order": self.execution_order,
        }

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class DAGValidator:
    """実験計画のDAG検証エンジン"""

    def __init__(self):
        self.operations: List[Dict] = []
        self.initial_objects: Set[str] = set()
        self.final_objects: Set[str] = set()

        # グラフ構造
        self.graph: Dict[str, Set[str]] = defaultdict(
            set
        )  # オブジェクト → 依存するオブジェクト
        self.producers: Dict[str, str] = {}  # オブジェクト → 生成するオペレーションID
        self.consumers: Dict[str, List[str]] = defaultdict(
            list
        )  # オブジェクト → 消費するオペレーションID

    def load_from_phases(self, phase1_output: dict, phase2_output: dict) -> None:
        """フェーズ1とフェーズ2の出力からデータをロード"""
        # フェーズ1: オブジェクト同定結果
        identified = phase1_output.get("identified_objects", {})
        self.initial_objects = set(identified.get("initial", []))
        self.final_objects = set(identified.get("final", []))

        # フェーズ2: オペレーション定義結果
        self.operations = phase2_output.get("operations", [])

    def build_graph(self) -> None:
        """オペレーションからDAGを構築"""
        self.graph.clear()
        self.producers.clear()
        self.consumers.clear()

        for op in self.operations:
            op_id = op.get("operation_id", "unknown")
            inputs = op.get("input", [])
            outputs = op.get("output", [])

            # 各出力について、それを生成するオペレーションを記録
            for out_obj in outputs:
                if out_obj in self.producers:
                    # 既に別のオペレーションが同じオブジェクトを生成している（重複）
                    pass  # エラーは後で検出
                self.producers[out_obj] = op_id

            # 各入力について、それを消費するオペレーションを記録
            for in_obj in inputs:
                self.consumers[in_obj].append(op_id)

                # グラフのエッジを追加: 入力オブジェクト → 出力オブジェクト
                for out_obj in outputs:
                    self.graph[out_obj].add(in_obj)

    def detect_cycles(self) -> List[List[str]]:
        """循環参照を検出（DFSベース）"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # サイクル検出
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)

        for obj in self.graph.keys():
            if obj not in visited:
                dfs(obj, [])

        return cycles

    def topological_sort(self) -> Tuple[bool, List[str]]:
        """トポロジカルソート（Kahnのアルゴリズム）"""
        # 入次数を計算
        in_degree = defaultdict(int)
        all_nodes = set(self.graph.keys())
        for node in self.graph:
            for neighbor in self.graph[node]:
                in_degree[neighbor] += 1
                all_nodes.add(neighbor)

        # 入次数0のノードをキューに追加
        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        sorted_objects = []

        while queue:
            node = queue.popleft()
            sorted_objects.append(node)

            # このノードを出力するオペレーションを実行順序に追加
            # （ノード=オブジェクト、オペレーションの順序はオブジェクトの順序から導出）

            # 隣接ノードの入次数を減らす
            for neighbor in self.graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 全てのノードがソートされたか確認
        success = len(sorted_objects) == len(all_nodes)
        return success, sorted_objects

    def get_operation_execution_order(self) -> List[str]:
        """オペレーションの実行順序を取得"""
        # オペレーションの依存関係を構築
        op_graph = defaultdict(set)
        op_in_degree = defaultdict(int)

        # 全オペレーションを初期化
        for op in self.operations:
            op_id = op["operation_id"]
            op_in_degree[op_id] = 0

        # 依存関係を構築
        for op in self.operations:
            op_id = op["operation_id"]
            inputs = op.get("input", [])

            # このオペレーションの入力を生成するオペレーションに依存
            for in_obj in inputs:
                if in_obj in self.producers:
                    producer_op = self.producers[in_obj]
                    if producer_op != op_id:
                        if op_id not in op_graph[producer_op]:
                            op_graph[producer_op].add(op_id)
                            op_in_degree[op_id] += 1

        # トポロジカルソート
        queue = deque([op_id for op_id in op_in_degree if op_in_degree[op_id] == 0])
        execution_order = []

        while queue:
            op_id = queue.popleft()
            execution_order.append(op_id)

            for dependent_op in op_graph[op_id]:
                op_in_degree[dependent_op] -= 1
                if op_in_degree[dependent_op] == 0:
                    queue.append(dependent_op)

        return execution_order

    def validate(self) -> ValidationResult:
        """完全な検証を実行"""
        errors = []
        warnings = []

        # グラフを構築
        self.build_graph()

        # 1. 循環参照の検出
        cycles = self.detect_cycles()
        if cycles:
            for cycle in cycles:
                errors.append(
                    ValidationError(
                        type="CIRCULAR_DEPENDENCY",
                        message=f"循環参照が検出されました: {' -> '.join(cycle)}",
                        suggestion="オペレーションの依存関係を見直し、循環を解消してください。",
                    )
                )

        # 2. 入力の検証: 全ての入力が生成されているか
        for op in self.operations:
            op_id = op["operation_id"]
            for in_obj in op.get("input", []):
                # 初期オブジェクトでもなく、どのオペレーションでも生成されていない
                if in_obj not in self.initial_objects and in_obj not in self.producers:
                    errors.append(
                        ValidationError(
                            type="MISSING_INPUT",
                            operation_id=op_id,
                            object_path=in_obj,
                            message=f"オペレーション '{op_id}' の入力 '{in_obj}' は、どのオペレーションでも生成されていません。",
                            suggestion=f"'{in_obj}' を生成するオペレーションを追加するか、初期オブジェクトとして定義してください。",
                        )
                    )

        # 3. 出力の検証: 全ての出力が使用されているか（最終成果物を除く）
        for op in self.operations:
            op_id = op["operation_id"]
            for out_obj in op.get("output", []):
                # 最終成果物でもなく、どのオペレーションでも使用されていない
                if out_obj not in self.final_objects and out_obj not in self.consumers:
                    warnings.append(
                        ValidationError(
                            type="UNUSED_OUTPUT",
                            operation_id=op_id,
                            object_path=out_obj,
                            message=f"オペレーション '{op_id}' の出力 '{out_obj}' は、どのオペレーションでも使用されていません。",
                            suggestion=f"'{out_obj}' を使用するオペレーションを追加するか、最終成果物として定義してください。",
                        )
                    )

        # 4. 最終成果物の検証: 全ての最終成果物が生成されているか
        for final_obj in self.final_objects:
            if final_obj not in self.producers:
                errors.append(
                    ValidationError(
                        type="MISSING_FINAL_OUTPUT",
                        object_path=final_obj,
                        message=f"最終成果物 '{final_obj}' を生成するオペレーションがありません。",
                        suggestion=f"'{final_obj}' を出力として生成するオペレーションを追加してください。",
                    )
                )

        # 5. 重複出力の検証
        output_count = defaultdict(list)
        for op in self.operations:
            op_id = op["operation_id"]
            for out_obj in op.get("output", []):
                output_count[out_obj].append(op_id)

        for obj, producers in output_count.items():
            if len(producers) > 1:
                errors.append(
                    ValidationError(
                        type="DUPLICATE_OUTPUT",
                        object_path=obj,
                        message=f"オブジェクト '{obj}' が複数のオペレーションで生成されています: {', '.join(producers)}",
                        suggestion="各オブジェクトは1つのオペレーションのみで生成されるべきです。重複を解消してください。",
                    )
                )

        # 6. 実行順序の取得
        execution_order = self.get_operation_execution_order()
        if not errors and len(execution_order) != len(self.operations):
            errors.append(
                ValidationError(
                    type="TOPOLOGICAL_SORT_FAILED",
                    message="オペレーションの実行順序を決定できませんでした。循環参照または孤立したオペレーションが存在する可能性があります。",
                    suggestion="オペレーション間の依存関係を確認してください。",
                )
            )

        # 結果を返す
        valid = len(errors) == 0
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            execution_order=execution_order if valid else [],
        )


def main():
    """使用例"""
    # サンプルデータ
    phase1_output = {
        "identified_objects": {
            "initial": [
                "objects/initial/ExpA_stock.reagent",
                "objects/initial/buffer.reagent",
            ],
            "intermediate": [
                "objects/intermediate/diluted_ExpA.sample",
                "objects/intermediate/reaction_mix.sample",
            ],
            "final": ["objects/final/result.image"],
        }
    }

    phase2_output = {
        "operations": [
            {
                "operation_id": "dilute_enzyme",
                "input": [
                    "objects/initial/ExpA_stock.reagent",
                    "objects/initial/buffer.reagent",
                ],
                "output": ["objects/intermediate/diluted_ExpA.sample"],
            },
            {
                "operation_id": "prepare_reaction",
                "input": ["objects/intermediate/diluted_ExpA.sample"],
                "output": ["objects/intermediate/reaction_mix.sample"],
            },
            {
                "operation_id": "visualize",
                "input": ["objects/intermediate/reaction_mix.sample"],
                "output": ["objects/final/result.image"],
            },
        ]
    }

    # 検証実行
    validator = DAGValidator()
    validator.load_from_phases(phase1_output, phase2_output)
    result = validator.validate()

    print(result.to_json())


if __name__ == "__main__":
    main()
