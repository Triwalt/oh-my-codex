from __future__ import annotations

import argparse
import concurrent.futures
import json
import shutil
import statistics
import subprocess
import textwrap
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CommandResult:
    command: list[str]
    cwd: str
    exit_code: int
    elapsed_sec: float
    stdout: str
    stderr: str


@dataclass
class StageResult:
    name: str
    elapsed_sec: float
    exit_code: int
    output_excerpt: str


@dataclass
class RunResult:
    strategy: str
    trial: int
    run_dir: str
    total_elapsed_sec: float
    success: bool
    retries: int
    changed_files: list[str]
    files_changed_count: int
    lines_added: int
    lines_deleted: int
    modified_tests: bool
    non_src_changes: list[str]
    stage_results: list[StageResult]
    local_verify_exit_code: int
    local_verify_excerpt: str


@dataclass
class AgentConfig:
    model: str
    timeout_sec: int
    binary: str


def run_cmd(command: list[str], cwd: Path, timeout_sec: int = 900) -> CommandResult:
    start = time.perf_counter()
    try:
        env = dict(**__import__("os").environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONUTF8"] = "1"
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        elapsed = time.perf_counter() - start
        return CommandResult(
            command=command,
            cwd=str(cwd),
            exit_code=proc.returncode,
            elapsed_sec=elapsed,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        err = exc.stderr if isinstance(exc.stderr, str) else ""
        if not err:
            err = f"Timed out after {timeout_sec}s"
        return CommandResult(
            command=command,
            cwd=str(cwd),
            exit_code=124,
            elapsed_sec=elapsed,
            stdout=out,
            stderr=err,
        )


def combined_output(result: CommandResult) -> str:
    both = []
    if result.stdout.strip():
        both.append(result.stdout.strip())
    if result.stderr.strip():
        both.append(result.stderr.strip())
    return "\n\n".join(both)


def excerpt(text: str, limit: int = 1400) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "\n...<truncated>"


def run_agent(prompt: str, cwd: Path, agent: AgentConfig) -> CommandResult:
    binary = agent.binary
    if binary == "codex":
        for candidate in ("codex.cmd", "codex.exe", "codex"):
            resolved = shutil.which(candidate)
            if resolved:
                binary = resolved
                break

    command = [
        binary,
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--color",
        "never",
        "--cd",
        str(cwd),
        "-m",
        agent.model,
        prompt,
    ]
    return run_cmd(command, cwd=cwd, timeout_sec=agent.timeout_sec)


def run_tests(cwd: Path) -> CommandResult:
    return run_cmd(["python", "-m", "unittest", "discover", "-s", "tests", "-v"], cwd, timeout_sec=120)


def setup_run_dir(template_dir: Path, runs_root: Path, strategy: str, trial: int) -> Path:
    run_dir = runs_root / f"{strategy}_trial_{trial:02d}"
    shutil.copytree(template_dir, run_dir)
    run_cmd(["git", "init"], run_dir)
    run_cmd(["git", "config", "user.email", "omx-eval@example.com"], run_dir)
    run_cmd(["git", "config", "user.name", "omx-eval"], run_dir)
    run_cmd(["git", "add", "."], run_dir)
    run_cmd(["git", "commit", "-m", "baseline"], run_dir)
    return run_dir


def gather_git_metrics(run_dir: Path) -> tuple[list[str], int, int]:
    changed_files_res = run_cmd(["git", "diff", "--name-only"], run_dir)
    files = [line.strip() for line in changed_files_res.stdout.splitlines() if line.strip()]

    numstat_res = run_cmd(["git", "diff", "--numstat"], run_dir)
    lines_added = 0
    lines_deleted = 0
    for line in numstat_res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add_s, del_s, _ = parts[:3]
        if add_s.isdigit():
            lines_added += int(add_s)
        if del_s.isdigit():
            lines_deleted += int(del_s)

    return files, lines_added, lines_deleted


def stage_from_result(name: str, result: CommandResult) -> StageResult:
    return StageResult(
        name=name,
        elapsed_sec=result.elapsed_sec,
        exit_code=result.exit_code,
        output_excerpt=excerpt(combined_output(result)),
    )


def run_serial_strategy(run_dir: Path, agent: AgentConfig) -> tuple[list[StageResult], int]:
    stages: list[StageResult] = []
    retries = 0

    prompt = textwrap.dedent(
        """
        STRATEGY: SERIAL

        This repository intentionally contains failing tests.
        Your full task is to make all tests pass.

        Rules:
        - Modify only files under src/.
        - Never edit tests/.
        - Verification command: python -m unittest discover -s tests -v
        - Keep iterating until verification passes.
        - Do not ask for additional clarification.
        - Do not invoke any external workflow or skill mode names.

        Final response must include:
        1) PASS or FAIL
        2) changed files
        3) final test summary
        """
    ).strip()

    first = run_agent(prompt, run_dir, agent)
    stages.append(stage_from_result("serial_main", first))

    verify = run_tests(run_dir)
    if verify.exit_code != 0:
        retries += 1
        retry_prompt = textwrap.dedent(
            f"""
            STRATEGY: SERIAL RETRY

            Previous attempt did not pass all tests.
            Fix remaining failures by editing src/ only.
            Do not edit tests/.
            Do not ask for more task details.

            Failure output:
            {excerpt(combined_output(verify), 2200)}

            Re-run verification until pass.
            """
        ).strip()
        retry = run_agent(retry_prompt, run_dir, agent)
        stages.append(stage_from_result("serial_retry", retry))

    return stages, retries


def run_pipeline_strategy(run_dir: Path, agent: AgentConfig) -> tuple[list[StageResult], int]:
    stages: list[StageResult] = []
    retries = 0

    diagnose_prompt = textwrap.dedent(
        """
        STAGED WORKFLOW PHASE: DIAGNOSE

        The repository intentionally has failing tests.
        Diagnose them first, then a separate phase will implement fixes.

        Analyze failing tests and produce root causes.

        Constraints:
        - Do not edit files.
        - Run: python -m unittest discover -s tests -v
        - Do not ask for additional task clarification.

        Return concise JSON with keys:
        - failing_tests
        - root_causes
        - minimal_fix_plan
        """
    ).strip()

    diagnose = run_agent(diagnose_prompt, run_dir, agent)
    stages.append(stage_from_result("pipeline_diagnose", diagnose))

    implement_prompt = textwrap.dedent(
        f"""
        STAGED WORKFLOW PHASE: IMPLEMENT

        Use prior diagnosis to implement only necessary fixes.

        Constraints:
        - Modify only src/ files.
        - Never edit tests/.
        - Verify by running python -m unittest discover -s tests -v until pass.
        - Do not ask for additional task clarification.

        Diagnosis context:
        {excerpt(combined_output(diagnose), 2600)}
        """
    ).strip()

    implement = run_agent(implement_prompt, run_dir, agent)
    stages.append(stage_from_result("pipeline_implement", implement))

    verify_prompt = textwrap.dedent(
        """
        STAGED WORKFLOW PHASE: VERIFY

        Run full verification command:
        python -m unittest discover -s tests -v

        If there are remaining failures, perform minimal src/ fixes and rerun.
        Never edit tests/.
        Do not ask for additional task clarification.

        Return PASS/FAIL and changed files.
        """
    ).strip()

    verify_stage = run_agent(verify_prompt, run_dir, agent)
    stages.append(stage_from_result("pipeline_verify", verify_stage))

    verify_local = run_tests(run_dir)
    if verify_local.exit_code != 0:
        retries += 1
        patch_prompt = textwrap.dedent(
            f"""
            STAGED WORKFLOW RETRY

            Tests still failing. Fix remaining issues in src/ only.
            Do not edit tests/.
            Do not ask for additional task clarification.

            Failure output:
            {excerpt(combined_output(verify_local), 2200)}
            """
        ).strip()
        retry = run_agent(patch_prompt, run_dir, agent)
        stages.append(stage_from_result("pipeline_retry", retry))

    return stages, retries


def run_ultrawork_strategy(run_dir: Path, agent: AgentConfig) -> tuple[list[StageResult], int]:
    stages: list[StageResult] = []
    retries = 0

    packet_root = run_dir.parent / f"{run_dir.name}_packets"
    p1_dir = packet_root / "p1"
    p2_dir = packet_root / "p2"
    if packet_root.exists():
        shutil.rmtree(packet_root)
    shutil.copytree(run_dir, p1_dir)
    shutil.copytree(run_dir, p2_dir)

    packet_p1 = textwrap.dedent(
        """
        PARALLEL PACKET P1

        The repository intentionally has failing tests.
        This packet should fix normalization-related failures.

        Objective: fix normalization-related failures.

        Ownership:
        - You may edit only src/normalization.py

        Constraints:
        - Do not edit tests/.
        - Run packet verification: python -m unittest tests/test_normalization.py -v
        - Keep iterating until packet verification passes.
        - Report changed lines.
        - Do not ask for additional task clarification.
        """
    ).strip()

    packet_p2 = textwrap.dedent(
        """
        PARALLEL PACKET P2

        The repository intentionally has failing tests.
        This packet should fix moving-average-related failures.

        Objective: fix moving-average-related failures.

        Ownership:
        - You may edit only src/math_quality.py

        Constraints:
        - Do not edit tests/.
        - Run packet verification: python -m unittest tests/test_math_quality.py -v
        - Keep iterating until packet verification passes.
        - Report changed lines.
        - Do not ask for additional task clarification.
        """
    ).strip()

    def run_packet(name: str, prompt: str, packet_dir: Path) -> StageResult:
        return stage_from_result(name, run_agent(prompt, packet_dir, agent))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(run_packet, "ultrawork_packet_p1", packet_p1, p1_dir),
            executor.submit(run_packet, "ultrawork_packet_p2", packet_p2, p2_dir),
        ]
        for fut in concurrent.futures.as_completed(futures):
            stages.append(fut.result())

    shutil.copy2(p1_dir / "src" / "normalization.py", run_dir / "src" / "normalization.py")
    shutil.copy2(p2_dir / "src" / "math_quality.py", run_dir / "src" / "math_quality.py")

    integrate_prompt = textwrap.dedent(
        """
        PARALLEL INTEGRATION + VERIFY

        The packet branches are already complete.
        Integrate and verify the repository now.

        Run full verification:
        python -m unittest discover -s tests -v

        If failures remain:
        - make minimal fixes in src/
        - rerun verification until pass
        - do not edit tests/
        - do not ask for additional task clarification

        Return PASS/FAIL and changed files.
        """
    ).strip()

    integrate = run_agent(integrate_prompt, run_dir, agent)
    stages.append(stage_from_result("ultrawork_integrate_verify", integrate))

    verify_local = run_tests(run_dir)
    if verify_local.exit_code != 0:
        retries += 1
        retry_prompt = textwrap.dedent(
            f"""
            PARALLEL RETRY

            Full tests still failing. Fix remaining issues in src/ only.
            Do not edit tests/.
            Do not ask for additional task clarification.

            Failure output:
            {excerpt(combined_output(verify_local), 2200)}
            """
        ).strip()
        retry = run_agent(retry_prompt, run_dir, agent)
        stages.append(stage_from_result("ultrawork_retry", retry))

    stages.sort(key=lambda s: s.name)
    return stages, retries


STRATEGY_HANDLERS = {
    "serial": run_serial_strategy,
    "pipeline": run_pipeline_strategy,
    "ultrawork": run_ultrawork_strategy,
}


def evaluate_strategy(
    template_dir: Path,
    runs_root: Path,
    strategy: str,
    trial: int,
    agent: AgentConfig,
) -> RunResult:
    run_dir = setup_run_dir(template_dir, runs_root, strategy, trial)

    start = time.perf_counter()
    stages, retries = STRATEGY_HANDLERS[strategy](run_dir, agent)
    total_elapsed = time.perf_counter() - start

    verify = run_tests(run_dir)
    changed_files, lines_added, lines_deleted = gather_git_metrics(run_dir)

    modified_tests = any(path.startswith("tests/") for path in changed_files)
    non_src_changes = [
        path for path in changed_files if not (path.startswith("src/") or path == "TASK.md")
    ]

    return RunResult(
        strategy=strategy,
        trial=trial,
        run_dir=str(run_dir),
        total_elapsed_sec=total_elapsed,
        success=verify.exit_code == 0,
        retries=retries,
        changed_files=changed_files,
        files_changed_count=len(changed_files),
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        modified_tests=modified_tests,
        non_src_changes=non_src_changes,
        stage_results=stages,
        local_verify_exit_code=verify.exit_code,
        local_verify_excerpt=excerpt(combined_output(verify), 2400),
    )


def summarize(results: list[RunResult]) -> dict[str, Any]:
    by_strategy: dict[str, list[RunResult]] = {}
    for result in results:
        by_strategy.setdefault(result.strategy, []).append(result)

    summary: dict[str, Any] = {"strategies": {}}
    for strategy, runs in by_strategy.items():
        times = [r.total_elapsed_sec for r in runs]
        success_flags = [r.success for r in runs]
        retries = [r.retries for r in runs]
        violation_flags = [r.modified_tests or len(r.non_src_changes) > 0 for r in runs]

        stats: dict[str, Any] = {
            "runs": len(runs),
            "success_rate": sum(1 for ok in success_flags if ok) / len(success_flags),
            "avg_time_sec": sum(times) / len(times),
            "p50_time_sec": statistics.median(times),
            "avg_retries": sum(retries) / len(retries),
            "context_accuracy": 1.0
            - (sum(1 for violated in violation_flags if violated) / len(violation_flags)),
            "avg_files_changed": sum(r.files_changed_count for r in runs) / len(runs),
            "avg_lines_added": sum(r.lines_added for r in runs) / len(runs),
            "avg_lines_deleted": sum(r.lines_deleted for r in runs) / len(runs),
        }

        if len(times) >= 2:
            stats["stability_stddev_sec"] = statistics.pstdev(times)
            sorted_times = sorted(times)
            idx = max(0, min(len(sorted_times) - 1, int(round(0.9 * (len(sorted_times) - 1)))))
            stats["p90_time_sec"] = sorted_times[idx]

        summary["strategies"][strategy] = stats

    return summary


def build_markdown_report(
    output_root: Path,
    generated_at: str,
    template_dir: Path,
    trials: int,
    model: str,
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Strategy Evaluation Report",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Template dir: `{template_dir}`",
        f"- Output root: `{output_root}`",
        f"- Trials per strategy: `{trials}`",
        f"- Model: `{model}`",
        "",
        "## Summary",
        "",
        "| Strategy | Runs | Success Rate | Avg Time (s) | Median Time (s) | Avg Retries | Context Accuracy | Avg Files Changed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for strategy, stats in summary["strategies"].items():
        lines.append(
            "| {strategy} | {runs} | {success_rate:.2f} | {avg_time_sec:.1f} | {p50_time_sec:.1f} | {avg_retries:.2f} | {context_accuracy:.2f} | {avg_files_changed:.1f} |".format(
                strategy=strategy,
                **stats,
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `Context Accuracy` penalizes modifications outside `src/` and unexpected test edits.",
            "- `Avg Time` measures end-to-end wall-clock runtime for the strategy handler plus local verification.",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local strategy benchmark for omx workflows")
    parser.add_argument("--template-dir", default=str(Path(__file__).resolve().parent / "template_project"))
    parser.add_argument("--strategies", nargs="+", default=["serial", "pipeline", "ultrawork"])
    parser.add_argument("--trials", type=int, default=2)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--timeout-sec", type=int, default=600)
    parser.add_argument("--binary", default="codex")
    args = parser.parse_args()

    template_dir = Path(args.template_dir).resolve()
    output_root = Path(__file__).resolve().parent / "eval_outputs" / datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_root = output_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    agent = AgentConfig(model=args.model, timeout_sec=args.timeout_sec, binary=args.binary)
    results: list[RunResult] = []
    for strategy in args.strategies:
        for trial in range(1, args.trials + 1):
            results.append(
                evaluate_strategy(
                    template_dir=template_dir,
                    runs_root=runs_root,
                    strategy=strategy,
                    trial=trial,
                    agent=agent,
                )
            )

    summary = summarize(results)
    report = {
        "generated_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "model": args.model,
        "output_root": str(output_root),
        "strategies": args.strategies,
        "trials": args.trials,
        "summary": summary,
        "results": [asdict(r) for r in results],
    }

    report_json = output_root / "report.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    report_md = output_root / "report.md"
    report_md.write_text(
        build_markdown_report(
            output_root=output_root,
            generated_at=report["generated_at"],
            template_dir=template_dir,
            trials=args.trials,
            model=args.model,
            summary=summary,
        ),
        encoding="utf-8",
    )

    print(f"[REPORT] {report_json}")
    print(f"[MARKDOWN] {report_md}")


if __name__ == "__main__":
    main()
