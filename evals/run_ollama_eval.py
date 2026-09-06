"""Run semantic intent evaluations against an Ollama model."""

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genui_intent.config import Settings
from genui_intent.pipeline import IntentPipeline
from genui_intent.providers import create_provider


def load_cases(path, tags, case_ids):
    cases = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            case = json.loads(line)
            case["_line"] = line_number
            if tags and not tags.intersection(case.get("tags", [])):
                continue
            if case_ids and case["id"] not in case_ids:
                continue
            cases.append(case)
    return cases


def check_case(actual, expected):
    checks = []

    def check(label, got, want):
        passed = got == want
        checks.append({"name": label, "passed": passed, "expected": want, "actual": got})

    for field in ("domain", "intentType", "goalType"):
        if field in expected:
            check(field, actual.get(field), expected[field])
    if "taskCount" in expected:
        check("taskCount", len(actual.get("tasks", [])), expected["taskCount"])
    for index, wanted_task in enumerate(expected.get("tasks", [])):
        tasks = actual.get("tasks", [])
        if index >= len(tasks):
            checks.append({"name": f"tasks[{index}]", "passed": False, "expected": wanted_task, "actual": None})
            continue
        task = tasks[index]
        mappings = {
            "entityCategoryKey": task.get("entity", {}).get("entityCategoryKey"),
            "entityMention": task.get("entity", {}).get("entityMention"),
            "referenceType": task.get("entity", {}).get("referenceType"),
            "operationType": task.get("operation", {}).get("operationType"),
            "propertyKey": task.get("operation", {}).get("propertyKey"),
            "dependsOn": task.get("dependsOn"),
        }
        for field, want in wanted_task.items():
            if field == "parameters":
                actual_params = task.get("parameters", [])
                for wanted_param in want:
                    matches = [p for p in actual_params if p.get("parameterKey") == wanted_param["parameterKey"]]
                    if not matches:
                        checks.append({"name": f"tasks[{index}].param.{wanted_param['parameterKey']}", "passed": False, "expected": wanted_param, "actual": None})
                        continue
                    param = matches[0]
                    for key, value in wanted_param.items():
                        check(f"tasks[{index}].param.{wanted_param['parameterKey']}.{key}", param.get(key), value)
            elif field == "contextContains":
                contexts = task.get("contexts", [])
                passed = any(all(c.get(k) == v for k, v in want.items()) for c in contexts)
                checks.append({"name": f"tasks[{index}].contextContains", "passed": passed, "expected": want, "actual": contexts})
            else:
                check(f"tasks[{index}].{field}", mappings.get(field), want)
    resolution = expected.get("resolution", {})
    if "status" in resolution:
        check("resolution.status", actual.get("resolution", {}).get("status"), resolution["status"])
    if "statusAny" in resolution:
        got = actual.get("resolution", {}).get("status")
        checks.append({"name": "resolution.statusAny", "passed": got in resolution["statusAny"], "expected": resolution["statusAny"], "actual": got})
    for field in resolution.get("missingContains", []):
        got = actual.get("resolution", {}).get("missingFields", [])
        checks.append({"name": "resolution.missingContains." + field, "passed": field in got, "expected": field, "actual": got})
    passed_count = sum(item["passed"] for item in checks)
    return checks, passed_count, len(checks)


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def main():
    parser = argparse.ArgumentParser(description="Evaluate RawIntentSpec quality with Ollama")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("intent_cases.jsonl"))
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--rerun-failures", type=Path, help="Only cases that failed in a previous JSONL result")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("evals/results/latest.jsonl"))
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    selected_ids = set(args.case_id)
    if args.rerun_failures:
        with args.rerun_failures.open(encoding="utf-8") as previous:
            selected_ids.update(
                item["id"] for item in (json.loads(line) for line in previous if line.strip())
                if item["passed"] != item["total"]
            )
    cases = load_cases(args.dataset, set(args.tag), selected_ids)
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        raise SystemExit("No matching evaluation cases")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pipeline = IntentPipeline(create_provider(Settings("ollama", args.model, args.base_url.rstrip("/"), "", args.timeout)))
    results, durations, domain_stats = [], [], defaultdict(lambda: [0, 0])
    print(f"Running {len(cases)} cases with {args.model}", flush=True)
    with args.output.open("w", encoding="utf-8") as output:
        for position, case in enumerate(cases, 1):
            started = time.perf_counter()
            actual, error = None, None
            try:
                actual = pipeline.generate(case["prompt"])
                checks, passed, total = check_case(actual, case["expected"])
            except Exception as exc:
                error, checks, passed, total = str(exc), [], 0, 1
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            durations.append(elapsed_ms)
            domain = case["expected"].get("domain", "UNKNOWN")
            domain_stats[domain][0] += passed
            domain_stats[domain][1] += total
            result = {"id": case["id"], "prompt": case["prompt"], "tags": case.get("tags", []), "elapsedMs": elapsed_ms, "passed": passed, "total": total, "checks": checks, "actual": actual, "error": error}
            results.append(result)
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            mark = "PASS" if passed == total else "FAIL"
            print(f"[{position:03}/{len(cases):03}] {mark} {case['id']} {passed}/{total} {elapsed_ms:.0f}ms", flush=True)
    passed = sum(r["passed"] for r in results)
    total = sum(r["total"] for r in results)
    exact = sum(r["passed"] == r["total"] for r in results)
    errors = sum(bool(r["error"]) for r in results)
    print("\nSummary")
    print(f"case exact: {exact}/{len(results)} ({exact / len(results):.1%})")
    print(f"field score: {passed}/{total} ({passed / total:.1%})")
    print(f"pipeline errors: {errors}/{len(results)}")
    print(f"latency ms: p50={statistics.median(durations):.0f} p95={percentile(durations, .95):.0f}")
    for domain, (domain_passed, domain_total) in sorted(domain_stats.items()):
        print(f"{domain}: {domain_passed}/{domain_total} ({domain_passed / domain_total:.1%})")
    print("details: " + str(args.output))


if __name__ == "__main__":
    main()
