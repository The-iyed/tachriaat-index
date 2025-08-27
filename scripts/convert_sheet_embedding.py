#!/usr/bin/env python3
"""
Read sheet_english.json, concatenate selected fields into a prompt string per row,
request Azure OpenAI embeddings, and write a new JSON file with an added
"embedding" field for each record.

Inputs:
  - sheet_english.json (default) or a custom input path

Outputs:
  - sheet_english_embedded.json (default) or a custom output path

Environment variables (Azure OpenAI):
  - AZURE_OPENAI_API_KEY
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME (preferred) or AZURE_OPENAI_DEPLOYMENT_NAME (alias)
  - AZURE_OPENAI_API_VERSION (optional, default: 2024-02-15-preview)

Fields concatenated (in this order, newline-separated if present):
  legislation_subject, pillar_name, main_pillar_name,
  authorization_name, classification_name, unit_name
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List
import time

try:
    from openai import AzureOpenAI
except Exception as exc:
    sys.stderr.write(
        "Missing dependency 'openai'. Install with: pip install openai\n"
    )
    raise


FIELDS_FOR_TEXT: List[str] = [
    "legislation_subject",
    "pillar_name",
    "main_pillar_name",
    "authorization_name",
    "classification_name",
    "unit_name",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add Azure embeddings to sheet_english.json")
    parser.add_argument("input_json", type=Path, nargs="?", default=Path("sheet_english.json"))
    parser.add_argument(
        "output_json", type=Path, nargs="?", default=Path("sheet_english_embedded.json")
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-wait", type=float, default=2.0, help="seconds between retries")
    parser.add_argument("--timeout", type=float, default=60.0, help="per-request timeout seconds")
    return parser.parse_args()


def ensure_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value


def build_client(timeout: float) -> AzureOpenAI:
    api_key = ensure_env("AZURE_OPENAI_API_KEY")
    endpoint = ensure_env("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version, timeout=timeout)


def get_deployment_name() -> str:
    # Support both env var names; prefer the embedding-specific one if defined
    name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME") or os.getenv(
        "AZURE_OPENAI_DEPLOYMENT_NAME"
    )
    if not name:
        raise RuntimeError(
            "Missing deployment name: set AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME or AZURE_OPENAI_DEPLOYMENT_NAME"
        )
    return name


def chunk_iter(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def build_text(record: Dict[str, Any]) -> str:
    parts: List[str] = []
    for field in FIELDS_FOR_TEXT:
        value = record.get(field)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def main() -> int:
    args = parse_args()
    if not args.input_json.exists():
        sys.stderr.write(f"Input JSON not found: {args.input_json}\n")
        return 1

    try:
        records: List[Dict[str, Any]] = json.loads(args.input_json.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("Input JSON must be an array of objects")
    except Exception as exc:
        sys.stderr.write(f"Failed reading input JSON: {exc}\n")
        return 1

    texts: List[str] = [build_text(r) for r in records]

    # Create client
    try:
        client = build_client(timeout=args.timeout)
        deployment = get_deployment_name()
    except Exception as exc:
        sys.stderr.write(f"Azure OpenAI configuration error: {exc}\n")
        return 1

    embeddings: List[List[float]] = []
    try:
        for batch in chunk_iter(texts, args.batch_size):
            attempt = 0
            while True:
                try:
                    response = client.embeddings.create(model=deployment, input=batch, timeout=args.timeout)
                    for item in response.data:
                        embeddings.append(item.embedding)
                    break
                except Exception as exc:
                    attempt += 1
                    if attempt > args.max_retries:
                        raise
                    # Exponential backoff with cap
                    sleep_s = min(args.retry_wait * (2 ** (attempt - 1)), 20)
                    sys.stderr.write(f"Embedding batch failed (attempt {attempt}): {exc}. Retrying in {sleep_s:.1f}s...\n")
                    time.sleep(sleep_s)
    except Exception as exc:
        sys.stderr.write(f"Failed to fetch embeddings: {exc}\n")
        return 1

    if len(embeddings) != len(records):
        sys.stderr.write(
            f"Embedding count mismatch: got {len(embeddings)}, expected {len(records)}\n"
        )
        return 1

    # Write output with embeddings attached
    for record, vector in zip(records, embeddings):
        record["embedding"] = vector

    try:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as exc:
        sys.stderr.write(f"Failed writing output JSON: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


