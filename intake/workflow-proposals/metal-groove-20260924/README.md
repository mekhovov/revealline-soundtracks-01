# Uninstalled manual-only intake proposal

These files preserve the earlier tested workflow proposal. They are deliberately
outside `.github/workflows/` and do not execute. The adjacent
`source-verification.json` describes that earlier proposal, not the active
source-only revision.

GitHub rejected tree creation for each workflow path with HTTP 404 under the
CLI credential. Its observed OAuth scopes were `admin:public_key, gist, read:org,
repo`; `workflow` was absent. The installed GitHub connector separately returned
HTTP 403, `Resource not accessible by integration`. No branch or PR was created
by those failed attempts, and no acquisition ran.

The approved continuation uses the existing configurable intake interface:
switch the active core manifest to the new four rows, preserve prior manifests,
and independently review the source branch before opening a PR. The existing
PR workflows will then acquire the new batch and separately reacquire Shchedryk.
No GitHub workflow permissions are changed.

Preserved remote blobs from the original attempt:

| Proposed workflow | Blob |
| --- | --- |
| core-intake.yml | `d176cf9e0a15849f29e6b34a613bae601dc86eb1` |
| ukrainian-intake.yml | `e5f0a4da1143e377b9796f4d9a1726b216c359ad` |
| metal-groove-intake.yml | `e4da1ea002ce0cff09aff8726222f684350bd7a0` |
