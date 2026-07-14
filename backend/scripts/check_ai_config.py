"""Check service-B/DeepSeek configuration without printing the API key."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (BACKEND_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.core.intelligence_settings import SERVICE_B_ENV_FILE, settings  # noqa: E402
from llm.providers.deepseek import DeepSeekClient, DeepSeekConfig, DeepSeekError  # noqa: E402


def _client() -> DeepSeekClient | None:
    if not settings.deepseek_api_key:
        return None
    return DeepSeekClient(
        DeepSeekConfig(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            timeout_seconds=settings.deepseek_timeout_seconds,
            max_tokens=min(settings.deepseek_max_tokens, 30),
            temperature=0,
        )
    )


async def _probe(client: DeepSeekClient) -> None:
    answer = await client.chat(
        [
            {"role": "system", "content": "只做连通性检查。"},
            {"role": "user", "content": "只回复 OK"},
        ]
    )
    print(f"DeepSeek probe: OK ({answer[:40]!r})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Send one minimal billable request to verify the key and model.",
    )
    args = parser.parse_args()

    print(f"intelligence env file: {SERVICE_B_ENV_FILE}")
    print(f"env file exists: {SERVICE_B_ENV_FILE.is_file()}")
    print(f"DEEPSEEK_API_KEY configured: {bool(settings.deepseek_api_key)}")
    if settings.deepseek_api_key:
        print(f"API key length: {len(settings.deepseek_api_key)} (value hidden)")
    print(f"DeepSeek base URL: {settings.deepseek_base_url}")
    print(f"DeepSeek model: {settings.deepseek_model}")
    print(f"DeepSeek timeout: {settings.deepseek_timeout_seconds}s")

    client = _client()
    if client is None:
        print("[FAILED] DeepSeek client is disabled because no valid API key was loaded.")
        return 1
    print("[OK] DeepSeek client can be constructed.")

    if args.probe:
        try:
            asyncio.run(_probe(client))
        except DeepSeekError as exc:
            print(f"[FAILED] {exc}")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
