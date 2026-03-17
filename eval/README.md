# OMX Eval Tools

This directory contains optional local tooling for:

- runtime hygiene audits and sanitization
- small matrix benchmarks comparing native Codex vs current omx vs optimized omx

These scripts do not ship as part of the MCP server runtime. They are for local verification and iteration.

## Runtime Maintenance

Audit local omx runtime files:

```bash
python eval/omx_runtime_maintenance.py audit
```

Archive stale state and rebuild a clean local notepad/state layout:

```bash
python eval/omx_runtime_maintenance.py sanitize
```

## Skill Matrix Benchmark

Run the small prompt-workflow matrix:

```bash
python eval/run_skill_matrix_eval.py --trials 1
```

Outputs are written under `eval/eval_outputs/`.
