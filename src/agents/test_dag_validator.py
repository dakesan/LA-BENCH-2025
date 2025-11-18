"""
DAG Validator のテストケース
様々なエラーケースを検証
"""

from dag_validator import DAGValidator
import json


def test_case_1_missing_input():
    """テストケース1: 入力が生成されていない"""
    print("=" * 60)
    print("テストケース1: 入力オブジェクトが生成されていない")
    print("=" * 60)

    phase1 = {
        "identified_objects": {
            "initial": ["objects/initial/reagent_A.reagent"],
            "intermediate": ["objects/intermediate/product_B.sample"],
            "final": ["objects/final/result.image"],
        }
    }

    phase2 = {
        "operations": [
            {
                "operation_id": "mix_reagents",
                "input": [
                    "objects/initial/reagent_A.reagent",
                    "objects/intermediate/reagent_B.reagent",  # これは生成されていない！
                ],
                "output": ["objects/intermediate/product_B.sample"],
            },
            {
                "operation_id": "visualize",
                "input": ["objects/intermediate/product_B.sample"],
                "output": ["objects/final/result.image"],
            },
        ]
    }

    validator = DAGValidator()
    validator.load_from_phases(phase1, phase2)
    result = validator.validate()
    print(result.to_json())
    print()


def test_case_2_unused_output():
    """テストケース2: 出力が使用されていない"""
    print("=" * 60)
    print("テストケース2: 中間生成物が使用されていない")
    print("=" * 60)

    phase1 = {
        "identified_objects": {
            "initial": ["objects/initial/reagent_A.reagent"],
            "intermediate": [
                "objects/intermediate/product_B.sample",
                "objects/intermediate/unused_product.sample",
            ],
            "final": ["objects/final/result.image"],
        }
    }

    phase2 = {
        "operations": [
            {
                "operation_id": "step1",
                "input": ["objects/initial/reagent_A.reagent"],
                "output": [
                    "objects/intermediate/product_B.sample",
                    "objects/intermediate/unused_product.sample",  # これは使われない
                ],
            },
            {
                "operation_id": "step2",
                "input": ["objects/intermediate/product_B.sample"],
                "output": ["objects/final/result.image"],
            },
        ]
    }

    validator = DAGValidator()
    validator.load_from_phases(phase1, phase2)
    result = validator.validate()
    print(result.to_json())
    print()


def test_case_3_circular_dependency():
    """テストケース3: 循環参照"""
    print("=" * 60)
    print("テストケース3: 循環参照が存在する")
    print("=" * 60)

    phase1 = {
        "identified_objects": {
            "initial": ["objects/initial/reagent_A.reagent"],
            "intermediate": [
                "objects/intermediate/product_B.sample",
                "objects/intermediate/product_C.sample",
            ],
            "final": ["objects/final/result.image"],
        }
    }

    phase2 = {
        "operations": [
            {
                "operation_id": "step1",
                "input": [
                    "objects/initial/reagent_A.reagent",
                    "objects/intermediate/product_C.sample",  # step2の出力に依存
                ],
                "output": ["objects/intermediate/product_B.sample"],
            },
            {
                "operation_id": "step2",
                "input": ["objects/intermediate/product_B.sample"],  # step1の出力に依存
                "output": ["objects/intermediate/product_C.sample"],
            },
            {
                "operation_id": "step3",
                "input": ["objects/intermediate/product_C.sample"],
                "output": ["objects/final/result.image"],
            },
        ]
    }

    validator = DAGValidator()
    validator.load_from_phases(phase1, phase2)
    result = validator.validate()
    print(result.to_json())
    print()


def test_case_4_missing_final_output():
    """テストケース4: 最終成果物が生成されていない"""
    print("=" * 60)
    print("テストケース4: 最終成果物が生成されていない")
    print("=" * 60)

    phase1 = {
        "identified_objects": {
            "initial": ["objects/initial/reagent_A.reagent"],
            "intermediate": ["objects/intermediate/product_B.sample"],
            "final": [
                "objects/final/result1.image",
                "objects/final/result2.image",  # これは生成されない
            ],
        }
    }

    phase2 = {
        "operations": [
            {
                "operation_id": "step1",
                "input": ["objects/initial/reagent_A.reagent"],
                "output": ["objects/intermediate/product_B.sample"],
            },
            {
                "operation_id": "step2",
                "input": ["objects/intermediate/product_B.sample"],
                "output": ["objects/final/result1.image"],
            },
        ]
    }

    validator = DAGValidator()
    validator.load_from_phases(phase1, phase2)
    result = validator.validate()
    print(result.to_json())
    print()


def test_case_5_duplicate_output():
    """テストケース5: 重複出力"""
    print("=" * 60)
    print("テストケース5: 同じオブジェクトが複数のオペレーションで生成される")
    print("=" * 60)

    phase1 = {
        "identified_objects": {
            "initial": ["objects/initial/reagent_A.reagent"],
            "intermediate": ["objects/intermediate/product_B.sample"],
            "final": ["objects/final/result.image"],
        }
    }

    phase2 = {
        "operations": [
            {
                "operation_id": "step1",
                "input": ["objects/initial/reagent_A.reagent"],
                "output": ["objects/intermediate/product_B.sample"],
            },
            {
                "operation_id": "step2",
                "input": ["objects/initial/reagent_A.reagent"],
                "output": ["objects/intermediate/product_B.sample"],  # 重複！
            },
            {
                "operation_id": "step3",
                "input": ["objects/intermediate/product_B.sample"],
                "output": ["objects/final/result.image"],
            },
        ]
    }

    validator = DAGValidator()
    validator.load_from_phases(phase1, phase2)
    result = validator.validate()
    print(result.to_json())
    print()


def test_case_6_complex_valid():
    """テストケース6: 複雑だが正しいDAG"""
    print("=" * 60)
    print("テストケース6: 複雑だが正しいDAG（EMSA実験の簡略版）")
    print("=" * 60)

    phase1 = {
        "identified_objects": {
            "initial": [
                "objects/initial/ExpA_stock.reagent",
                "objects/initial/tRNA_Ala.reagent",
                "objects/initial/buffer_components.reagent",
            ],
            "intermediate": [
                "objects/intermediate/ExpA_dilution_1.sample",
                "objects/intermediate/ExpA_dilution_2.sample",
                "objects/intermediate/reaction_buffer.buffer",
                "objects/intermediate/reaction_mix_1.sample",
                "objects/intermediate/reaction_mix_2.sample",
                "objects/intermediate/incubated_mix_1.sample",
                "objects/intermediate/incubated_mix_2.sample",
                "objects/intermediate/gel_after_electrophoresis.gel",
            ],
            "final": [
                "objects/final/sybr_stained_gel.image",
                "objects/final/cbb_stained_gel.image",
            ],
        }
    }

    phase2 = {
        "operations": [
            {
                "operation_id": "prepare_buffer",
                "input": ["objects/initial/buffer_components.reagent"],
                "output": ["objects/intermediate/reaction_buffer.buffer"],
            },
            {
                "operation_id": "dilute_enzyme",
                "input": [
                    "objects/initial/ExpA_stock.reagent",
                    "objects/intermediate/reaction_buffer.buffer",
                ],
                "output": [
                    "objects/intermediate/ExpA_dilution_1.sample",
                    "objects/intermediate/ExpA_dilution_2.sample",
                ],
            },
            {
                "operation_id": "prepare_reaction_1",
                "input": [
                    "objects/intermediate/ExpA_dilution_1.sample",
                    "objects/initial/tRNA_Ala.reagent",
                    "objects/intermediate/reaction_buffer.buffer",
                ],
                "output": ["objects/intermediate/reaction_mix_1.sample"],
            },
            {
                "operation_id": "prepare_reaction_2",
                "input": [
                    "objects/intermediate/ExpA_dilution_2.sample",
                    "objects/initial/tRNA_Ala.reagent",
                    "objects/intermediate/reaction_buffer.buffer",
                ],
                "output": ["objects/intermediate/reaction_mix_2.sample"],
            },
            {
                "operation_id": "incubate_reactions",
                "input": [
                    "objects/intermediate/reaction_mix_1.sample",
                    "objects/intermediate/reaction_mix_2.sample",
                ],
                "output": [
                    "objects/intermediate/incubated_mix_1.sample",
                    "objects/intermediate/incubated_mix_2.sample",
                ],
            },
            {
                "operation_id": "run_electrophoresis",
                "input": [
                    "objects/intermediate/incubated_mix_1.sample",
                    "objects/intermediate/incubated_mix_2.sample",
                ],
                "output": ["objects/intermediate/gel_after_electrophoresis.gel"],
            },
            {
                "operation_id": "stain_with_sybr",
                "input": ["objects/intermediate/gel_after_electrophoresis.gel"],
                "output": ["objects/final/sybr_stained_gel.image"],
            },
            {
                "operation_id": "stain_with_cbb",
                "input": ["objects/intermediate/gel_after_electrophoresis.gel"],
                "output": ["objects/final/cbb_stained_gel.image"],
            },
        ]
    }

    validator = DAGValidator()
    validator.load_from_phases(phase1, phase2)
    result = validator.validate()
    print(result.to_json())
    print()


if __name__ == "__main__":
    test_case_1_missing_input()
    test_case_2_unused_output()
    test_case_3_circular_dependency()
    test_case_4_missing_final_output()
    test_case_5_duplicate_output()
    test_case_6_complex_valid()
