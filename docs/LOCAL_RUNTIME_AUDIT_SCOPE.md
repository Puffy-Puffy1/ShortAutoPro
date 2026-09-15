# Local Runtime Audit Scope

The Consolidation 2.0 repository architecture audit is intentionally scoped to files tracked by the current Git revision.

Ignored local runtime material such as `backups/`, `temp/`, generated media, cached scripts and per-Short reports must not be treated as repository architecture. The source of truth is `git ls-files`.

This keeps the audit fail-closed for tracked dead code while avoiding false failures caused by historical or temporary files that exist only on a Termux device.

Professional per-Short runtime reports under `roteiros/` are ignored by pattern and remain local to the production that created them.
