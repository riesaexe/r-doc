# Public evidence verification

The sanitized naturalistic export is reviewable without publishing raw CLI logs or machine-specific paths. It is not, by itself, proof that the private source bytes still match the recorded hashes.

Run the public-only verifier against the corrected v8 aggregate:

~~~bash
python benchmarks/naturalistic/verify_public_evidence.py \
  --public-evidence benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2/public-evidence.json \
  --summary benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2/summary-regraded-event-contract.json
~~~

This checks the public schema, redacted-path boundary, per-run identity, exported digest consistency, source-hash format, event ordering, and cross-summary identity. It reports source_artifacts as unavailable because the raw files are intentionally not required.

When the private capture directory is available, add source-root:

~~~bash
python benchmarks/naturalistic/verify_public_evidence.py \
  --public-evidence benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2/public-evidence.json \
  --summary benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2/summary-regraded-event-contract.json \
  --source-root benchmarks/naturalistic-runs-20260920-luna-v0.3.0-full-v8-command-glob-event-v2
~~~

This additionally loads each private artifact-hashes.json and replays every recorded LF-canonical SHA-256. A pass in public-only mode must therefore be described as structural and cross-summary verification, not raw artifact replay.

The formal root file benchmarks/naturalistic-runs/summary.json is now pending. The previous 44-record file is preserved as summary-unverified-v0.4.0.json because the v0.4.0 published tree contains no matching result artifacts for 36 records: 16 gpt-5.5 records and all 20 gpt-5.6-sol records. The sol records are not an approved measured batch. Do not restore that file as the formal summary without either publishing matching sanitized evidence or creating a new approved batch.

The expanded task specifications architecture-decision-sync-v1.json, cross-module-contract-migration-v1.json, and release-doc-drift-v1.json are included in the approved v0.4.0 Luna batch. Their original captures remain under `benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex/`; the deterministic grader regrade is recorded separately under `benchmarks/naturalistic-runs-20260920-luna-v0.4.0-full-v1-complex-regraded-v1/` and must not be mixed into the original evidence tree.
