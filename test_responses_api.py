#!/usr/bin/env python3
"""
Test script for Responses API implementation
"""
import os
from openai import OpenAI
from pydantic import BaseModel, Field


class StepModel(BaseModel):
    id: int = Field(ge=1, description="Step number")
    text: str = Field(description="Step description")


class GeneratedOutput(BaseModel):
    procedure_steps: list[StepModel] = Field(
        description="List of procedure steps",
        min_items=1,
        max_items=5
    )


def test_responses_api():
    """
    Test the Responses API with GPT-5.1 and reasoning effort
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        return

    client = OpenAI(api_key=api_key)

    print("=" * 60)
    print("Testing Responses API with GPT-5.1")
    print("=" * 60)

    test_input = """
あなたは生命科学実験の専門家です。
以下の実験指示に従って、実行可能な手順を3-5ステップで返してください。

【実験指示】
PCR反応液を調製し、サーマルサイクラーで増幅を行う。

【使用する物品】
- PCRチューブ
- DNAポリメラーゼ
- プライマー
- dNTPs
- サーマルサイクラー
"""

    # Test 1: reasoning effort = "none"
    print("\nTest 1: reasoning effort = 'none'")
    try:
        response = client.responses.create(
            model="gpt-5.1",
            input=test_input,
            reasoning={"effort": "none"},
            response_format=GeneratedOutput,
            max_output_tokens=1024,
        )
        parsed = response.parsed_output
        print(f"✅ Success: Generated {len(parsed.procedure_steps)} steps")
        for step in parsed.procedure_steps:
            print(f"  {step.id}. {step.text[:50]}...")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test 2: reasoning effort = "medium"
    print("\nTest 2: reasoning effort = 'medium'")
    try:
        response = client.responses.create(
            model="gpt-5.1",
            input=test_input,
            reasoning={"effort": "medium"},
            response_format=GeneratedOutput,
            max_output_tokens=2048,
        )
        parsed = response.parsed_output
        print(f"✅ Success: Generated {len(parsed.procedure_steps)} steps")
        for step in parsed.procedure_steps:
            print(f"  {step.id}. {step.text[:50]}...")
    except Exception as e:
        print(f"❌ Failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Test completed")
    print("=" * 60)


if __name__ == "__main__":
    test_responses_api()
