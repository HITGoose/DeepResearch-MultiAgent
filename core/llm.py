"""Unified LLM calling utility."""

import json
import re
from langchain_openai import ChatOpenAI
from config import (
    MAIN_MODEL, MAIN_MODEL_BASE_URL, MAIN_MODEL_API_KEY,
    LIGHT_MODEL, LIGHT_MODEL_BASE_URL, LIGHT_MODEL_API_KEY,
)


def get_main_llm(temperature: float = 0.3, max_tokens: int = 4096) -> ChatOpenAI:
    """Get the main LLM for complex reasoning tasks."""
    return ChatOpenAI(
        model=MAIN_MODEL,
        base_url=MAIN_MODEL_BASE_URL,
        api_key=MAIN_MODEL_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_light_llm(temperature: float = 0.1, max_tokens: int = 1024) -> ChatOpenAI:
    """Get the light LLM for simulation/summarization tasks."""
    return ChatOpenAI(
        model=LIGHT_MODEL,
        base_url=LIGHT_MODEL_BASE_URL,
        api_key=LIGHT_MODEL_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def call_llm(llm: ChatOpenAI, prompt: str) -> str:
    """Call LLM and return the text response."""
    response = llm.invoke(prompt)
    return response.content


def call_llm_json(llm: ChatOpenAI, prompt: str) -> dict | list:
    """Call LLM and parse the response as JSON."""
    response = call_llm(llm, prompt)
    # Try to extract JSON from the response (handle markdown code blocks)
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if json_match:
        response = json_match.group(1)
    # Clean up and parse
    response = response.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Last resort: try to find JSON object/array in the text
        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        print(f"[LLM] JSON 解析失败: {response[:200]}...")
        return {}
