from __future__ import annotations

import argparse
import json
import shutil
import statistics
import textwrap
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from run_strategy_eval import (
    AgentConfig,
    combined_output,
    excerpt,
    gather_git_metrics,
    run_agent,
    run_cmd,
    run_tests,
)


@dataclass
class MatrixRunResult:
    task: str
    strategy: str
    trial: int
    run_dir: str
    total_elapsed_sec: float
    success: bool
    retries: int
    prompt_chars: int
    prompt_lines: int
    changed_files: list[str]
    files_changed_count: int
    lines_added: int
    lines_deleted: int
    modified_tests: bool
    non_src_changes: list[str]
    local_verify_exit_code: int
    local_verify_excerpt: str


def find_latest_snapshot(root: Path) -> Path:
    candidates = sorted(root.glob("*_pre_p0_p3"))
    if not candidates:
        raise FileNotFoundError(f"No snapshot found under {root}")
    return candidates[-1]


def setup_run_dir(task_dir: Path, runs_root: Path, task: str, strategy: str, trial: int) -> Path:
    run_dir = runs_root / f"{task}__{strategy}_trial_{trial:02d}"
    shutil.copytree(task_dir, run_dir)
    run_cmd(["git", "init"], run_dir)
    run_cmd(["git", "config", "user.email", "omx-eval@example.com"], run_dir)
    run_cmd(["git", "config", "user.name", "omx-eval"], run_dir)
    run_cmd(["git", "add", "."], run_dir)
    run_cmd(["git", "commit", "-m", "baseline"], run_dir)
    return run_dir


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_prompt_bundle(strategy: str, snapshot_root: Path, skills_root: Path) -> str:
    if strategy == "native":
        return textwrap.dedent(
            """
            You are fixing a small Python repository with failing unit tests.

            Rules:
            - Modify only files under src/.
            - Never edit tests/.
            - Run: python -m unittest discover -s tests -v
            - Keep iterating until tests pass.
            - Do not ask for additional clarification.

            Final response must include:
            1) PASS or FAIL
            2) changed files
            3) final test summary
            """
        ).strip()

    if strategy == "omx_current":
        current_serial = load_text(snapshot_root / "skills" / "omx-serial" / "SKILL.md")
        return textwrap.dedent(
            f"""
            Use the following current omx skill instructions as your workflow guide.

            {current_serial}

            Repository-specific rules:
            - Modify only files under src/.
            - Never edit tests/.
            - Run: python -m unittest discover -s tests -v
            - Keep iterating until tests pass.
            - Do not ask for additional clarification.

            Final response must include:
            1) PASS or FAIL
            2) changed files
            3) final test summary
            """
        ).strip()

    runtime_contract = load_text(
        skills_root / "omx-help" / "references" / "omx-runtime-contract.md"
    )
    optimized_serial = load_text(skills_root / "omx-serial" / "SKILL.md")
    return textwrap.dedent(
        f"""
        Use the following optimized omx workflow instructions as your guide.

        {runtime_contract}

        {optimized_serial}

        Repository-specific rules:
        - Modify only files under src/.
        - Never edit tests/.
        - Run: python -m unittest discover -s tests -v
        - Keep iterating until tests pass.
        - Do not ask for additional clarification.

        Final response must include:
        1) PASS or FAIL
        2) changed files
        3) final test summary
        """
    ).strip()


def evaluate_run(
    task_dir: Path,
    task: str,
    strategy: str,
    trial: int,
    runs_root: Path,
    snapshot_root: Path,
    skills_root: Path,
    agent: AgentConfig,
) -> MatrixRunResult:
    run_dir = setup_run_dir(task_dir, runs_root, task, strategy, trial)
    base_prompt = build_prompt_bundle(strategy, snapshot_root, skills_root)
    prompt = f"{base_prompt}\n\nTask brief:\n{load_text(task_dir / 'TASK.md')}"

    start = time.perf_counter()
    retries = 0
    run_agent(prompt, run_dir, agent)
    verify = run_tests(run_dir)
    if verify.exit_code != 0:
        retries = 1
        retry_prompt = textwrap.dedent(
            f"""
            The previous attempt did not pass all tests.

            Continue with the same workflow and fix the remaining failures.
            Modify only src/.
            Never edit tests/.

            Failure output:
            {excerpt(combined_output(verify), 2200)}
            """
        ).strip()
        run_agent(f"{prompt}\n\n{retry_prompt}", run_dir, agent)
        verify = run_tests(run_dir)

    total_elapsed = time.perf_counter() - start
    changed_files, lines_added, lines_deleted = gather_git_metrics(run_dir)
    modified_tests = any(path.startswith("tests/") for path in changed_files)
    non_src_changes = [
        path for path in changed_files if not (path.startswith("src/") or path == "TASK.md")
    ]

    return MatrixRunResult(
        task=task,
        strategy=strategy,
        trial=trial,
        run_dir=str(run_dir),
        total_elapsed_sec=total_elapsed,
        success=verify.exit_code == 0,
        retries=retries,
        prompt_chars=len(prompt),
        prompt_lines=len(prompt.splitlines()),
        changed_files=changed_files,
        files_changed_count=len(changed_files),
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        modified_tests=modified_tests,
        non_src_changes=non_src_changes,
        local_verify_exit_code=verify.exit_code,
        local_verify_excerpt=excerpt(combined_output(verify), 2400),
    )


def summarize(results: list[MatrixRunResult]) -> dict[str, Any]:
    by_strategy: dict[str, list[MatrixRunResult]] = {}
    by_task: dict[str, list[MatrixRunResult]] = {}
    for result in results:
        by_strategy.setdefault(result.strategy, []).append(result)
        by_task.setdefault(result.task, []).append(result)

    summary: dict[str, Any] = {"strategies": {}, "tasks": {}}
    for strategy, runs in by_strategy.items():
        times = [r.total_elapsed_sec for r in runs]
        prompt_chars = [r.prompt_chars for r in runs]
        retries = [r.retries for r in runs]
        violations = [r.modified_tests or bool(r.non_src_changes) for r in runs]
        summary["strategies"][strategy] = {
            "runs": len(runs),
            "success_rate": sum(1 for r in runs if r.success) / len(runs),
            "avg_time_sec": sum(times) / len(times),
            "avg_prompt_chars": sum(prompt_chars) / len(prompt_chars),
            "avg_retries": sum(retries) / len(retries),
            "context_accuracy": 1.0 - (sum(1 for v in violations if v) / len(violations)),
        }
        if len(times) >= 2:
            summary["strategies"][strategy]["stability_stddev_sec"] = statistics.pstdev(times)

    for task, runs in by_task.items():
        summary["tasks"][task] = {
            "runs": len(runs),
            "success_rate": sum(1 for r in runs if r.success) / len(runs),
            "avg_time_sec": sum(r.total_elapsed_sec for r in runs) / len(runs),
        }
    return summary


def build_markdown_report(
    output_root: Path,
    generated_at: str,
    model: str,
    snapshot_root: Path,
    tasks: list[str],
    trials: int,
    summary: dict[str, Any],
) -> str:
    lines = [
        "# OMX Skill Matrix Benchmark",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Model: `{model}`",
        f"- Current-skill snapshot: `{snapshot_root}`",
        f"- Trials per strategy-task pair: `{trials}`",
        "",
        "## Tasks",
        "",
    ]
    for task in tasks:
        lines.append(f"- `{task}`")

    lines.extend(
        [
            "",
            "## Strategy Summary",
            "",
            "| Strategy | Runs | Success Rate | Avg Time (s) | Avg Prompt Chars | Avg Retries | Context Accuracy |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for strategy, stats in summary["strategies"].items():
        lines.append(
            "| {strategy} | {runs} | {success:.2f} | {time:.1f} | {prompt:.0f} | {retries:.2f} | {ctx:.2f} |".format(
                strategy=strategy,
                runs=stats["runs"],
                success=stats["success_rate"],
                time=stats["avg_time_sec"],
                prompt=stats["avg_prompt_chars"],
                retries=stats["avg_retries"],
                ctx=stats["context_accuracy"],
            )
        )

    lines.extend(
        [
            "",
            "## Task Summary",
            "",
            "| Task | Runs | Success Rate | Avg Time (s) |",
            "|---|---:|---:|---:|",
        ]
    )
    for task, stats in summary["tasks"].items():
        lines.append(
            "| {task} | {runs} | {success:.2f} | {time:.1f} |".format(
                task=task,
                runs=stats["runs"],
                success=stats["success_rate"],
                time=stats["avg_time_sec"],
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `omx_current` is replayed from the archived pre-change serial skill snapshot.",
            "- `omx_optimized` uses the live serial skill plus the new runtime contract.",
            "- This matrix measures prompt-workflow effects under the current local runtime, not live omx MCP delegation.",
            "",
            f"- Output root: `{output_root}`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small matrix benchmark for current vs optimized omx skills")
    parser.add_argument("--tasks-root", default=str(Path(__file__).resolve().parent / "tasks"))
    parser.add_argument("--strategies", nargs="+", default=["native", "omx_current", "omx_optimized"])
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--timeout-sec", type=int, default=600)
    parser.add_argument("--binary", default="codex")
    parser.add_argument("--snapshot-root", default="")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    tasks_root = Path(args.tasks_root).resolve()
    task_dirs = sorted([path for path in tasks_root.iterdir() if path.is_dir()])
    if not task_dirs:
        raise FileNotFoundError(f"No task directories found under {tasks_root}")

    snapshot_root = (
        Path(args.snapshot_root).resolve()
        if args.snapshot_root
        else find_latest_snapshot(script_dir / "snapshots")
    )
    skills_root = Path(__file__).resolve().parent.parent / "skills"

    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = script_dir / "eval_outputs" / f"{generated_at}_skill_matrix"
    runs_root = output_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    agent = AgentConfig(model=args.model, timeout_sec=args.timeout_sec, binary=args.binary)
    results: list[MatrixRunResult] = []

    for task_dir in task_dirs:
        task = task_dir.name
        for strategy in args.strategies:
            for trial in range(1, args.trials + 1):
                results.append(
                    evaluate_run(
                        task_dir=task_dir,
                        task=task,
                        strategy=strategy,
                        trial=trial,
                        runs_root=runs_root,
                        snapshot_root=snapshot_root,
                        skills_root=skills_root,
                        agent=agent,
                    )
                )

    summary = summarize(results)
    report = {
        "generated_at": generated_at,
        "model": args.model,
        "output_root": str(output_root),
        "snapshot_root": str(snapshot_root),
        "strategies": args.strategies,
        "tasks": [path.name for path in task_dirs],
        "trials": args.trials,
        "summary": summary,
        "results": [asdict(result) for result in results],
    }

    (output_root / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_root / "report.md").write_text(
        build_markdown_report(
            output_root=output_root,
            generated_at=generated_at,
            model=args.model,
            snapshot_root=snapshot_root,
            tasks=[path.name for path in task_dirs],
            trials=args.trials,
            summary=summary,
        ),
        encoding="utf-8",
    )
    print(f"[REPORT] {output_root / 'report.json'}")
    print(f"[MARKDOWN] {output_root / 'report.md'}")


if __name__ == "__main__":
    main()
