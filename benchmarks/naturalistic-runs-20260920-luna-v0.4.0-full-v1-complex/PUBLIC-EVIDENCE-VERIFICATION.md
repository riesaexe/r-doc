# v0.4.0 Luna full batch evidence

This batch uses the explicitly confirmed model 'gpt-5.6-luna', paired conditions 'with-r-doc' and 'baseline-no-r-doc', ten matched repetitions, and seven tasks:

- api-response-field-rename
- cli-option-rename
- event-payload-rename-v2
- sql-column-rename
- architecture-decision-sync-v1
- cross-module-contract-migration-v1
- release-doc-drift-v1

The batch manifest declares 140 jobs. One baseline API job initially reached the 900-second timeout; it was retried with the same task, condition, profile, model, and run ID. The final batch contains 140 runs and 70 complete A/B pairs.

The final independent regrade reports 93 task-outcome passes and 47 failures. The failures are concentrated in cross-module-contract-migration-v1 (20) and release-doc-drift-v1 (19), with 8 in architecture-decision-sync-v1; the four smaller task families and 12 architecture runs pass. Command-level forbidden-read evidence is 0/140. The with-r-doc condition has visible/load/use activation evidence in 70/70 runs; baseline activation is not applicable.

The aggregate status: pass means all records passed the measurement gate. It is not a claim that every task outcome passed. Because both conditions share skill-discovery-safe-read-preflight-v2-command-glob, effect_attribution.status remains descriptive-only; safe-read outcomes are not attributed to r-doc.

## Verification commands

Public-only verification:

~~~bash
python benchmarks/naturalistic/verify_public_evidence.py \
  --public-evidence benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex/public-evidence.json \
  --summary benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex/summary.json
~~~

Expected result: status: pass, run_count: 140, source_artifacts: unavailable.

Local source-artifact replay:

~~~bash
python benchmarks/naturalistic/verify_public_evidence.py \
  --public-evidence benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex/public-evidence.json \
  --summary benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex/summary.json \
  --source-root benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex
~~~

Expected result: status: pass, run_count: 140, source_artifacts: verified.

The public export contains sanitized per-run manifests, critical events, results, and source artifact hashes. Raw CLI event streams remain local. replay-status.json records the local regrade and the command-segment read-attribution fix that excludes PowerShell -PathType and Write-Output path labels from file-read inference.
