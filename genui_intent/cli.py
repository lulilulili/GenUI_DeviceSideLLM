import argparse
import json
import sys

from .config import Settings
from .pipeline import IntentPipeline
from .providers import create_provider


def main():
    defaults = Settings.from_env()
    parser = argparse.ArgumentParser(description="用户提示词 → RawIntentSpec v1.0")
    parser.add_argument("prompt", help="用户提示词")
    parser.add_argument("--provider", choices=["ollama", "openai_compatible", "mock"], default=defaults.provider)
    parser.add_argument("--model", default=defaults.model)
    parser.add_argument("--base-url", default=defaults.base_url)
    parser.add_argument("--api-key", default=defaults.api_key)
    parser.add_argument("--timeout", type=float, default=defaults.timeout)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    settings = Settings(args.provider, args.model, args.base_url.rstrip("/"), args.api_key, args.timeout)
    try:
        result = IntentPipeline(create_provider(settings)).generate(args.prompt)
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")))
    except Exception as exc:
        print("error: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

