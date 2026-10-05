# Filesystem Rename Model Lab

A Python learning tool for supplied ordinary-rename namespace endpoints. Move a binding, replace another file's binding, or recognize a same-file alias no-op while existing abstract references keep their original identity. It performs no real rename or target filesystem inspection.

Demo: A→F, B→G and R→G; rename A to B gives B→F while R→G remains. G becomes reference_only. If A and B both name F, renaming A to B keeps BOTH names. Objects and name bindings are separate.

Run from this directory with installed Python; no package installation or dependency download:

```powershell
Get-Content -Raw examples/replace-reference.json | python -m rename_lab
python -m rename_lab --help
python tools/verify.py
```

Reusable API: `from rename_lab import evaluate`; pass the native dict described in PLAN/CONTRACT. It returns a fresh full report and preserves caller data. CLI reads one UTF8 JSON document from stdin and writes compact sorted-key JSON with LF. No paths/filenames or commands supplied as input. Python stdlib only; verifier additionally uses the already installed Bandit module, which is not an application dependency.

| Status | Meaning | Exit |
|---|---|---|
| modeled | Complete conditional endpoint trace | 0 |
| unsupported | Known extension or unknown/excluded context; no snapshots | 0 |
| invalid_input | Malformed/common admission failure; no snapshots | 2 |
| invalid_trace | Missing model source; entire prefix suppressed | 2 |
| IO delivery failure | Fixed checked stderr diagnostic when available | 3 |

Unsupported exit0 means recognized input classification, never permission/safety approval. See SECURITY.md for the exact threat boundary. The profile assumes regular files, one mounted namespace, complete resolved synthetic bindings/references and successful operations. Exchange, noreplace, whiteout, cross-mount and unknown assumptions remain unsupported. No live paths, permissions, descriptors, symlinks, races, failed-syscall prediction, actual reclamation or crash durability. Model precondition rejection does not prove a real failed rename had no effect.

Architecture: complete native admission → known unsupported classification → private binding-map replay → fresh sorted snapshots → bounded serializer and checked CLI. Strict UTF8/duplicate-key/nonfinite/integer/depth controls precede native admission. At most4files/8names/8references/24events; ASCII IDs1–24chars; stdin32768bytes; report262144bytes. Exact schema/report/diagnostic precedence in PLAN.md and frozen CONTRACT.md.

For a fresh clone, install the version-pinned development tools with `python -m pip install -r requirements-dev.txt` before the full verifier. The application itself needs no external dependencies. Development artifact hashes remain unverified because official PyPI metadata requests failed at transport. Each verification run saves fresh receipts beneath research/runs; local historical raw logs, worker drafts, vault/coordination records and upstream source excerpts are excluded from Git. Frozen oracle receipts/source metadata remain included. PLAN and detailed source snapshots are retained locally; CONTRACT and RESEARCH document the public behavior and source comparison. Byte-preserving Git attributes keep the original frozen hashes valid across operating systems. CI tests Linux/Windows, runs Bandit, and runs CodeQL weekly/on pushes/PRs/manual dispatch with immutable action pins.

Verified locally on Windows CPython3.13.7:14 tests normal and optimized,32 independent full reports,693 finite controls,54 real child CLI observations and38 fault seams per suite. Six fixed in-memory assertion mutants detected with zero errors and production source unchanged. Bandit1.9.4:0findings/0errors over application/tools; three narrow trusted-harness rule annotations, none in app; tests manually reviewed. VERIFICATION.md and raw research receipts provide details and the Windows CRLF correction. Other runtimes/live Linux/hosted CI/independent audit remain unverified.

Research recommends build over adopting pyfakefs/LTP; source bodies, licenses, maintenance evidence and retrieval gaps are in RESEARCH.md/source-index. Original implementation/test/oracle/tool code is MIT; upstream research excerpts retain their respective Apache2/GPL2-or-later licenses and are excluded from the original-code license grant. Owned checked CLI/admission/report patterns derive from Jake's accepted Filesystem Link Lifecycle/Sticky/ACL labs; no sibling imports or prior source changes. AI assistance: Codex drafted/reviewed/tested original work; one public local Ollama2B idea draft was rejected as inaccurate/truncated. No accepted remote draft, paid call or upstream execution. ECC review is the implementing agent's self-review.

Optional exercise: add another name for G before replacement and predict its final binding and retention. Compare the result with frozen victim_alias and replace_ref cases; a name disappearing does not imply the object changed identity.
