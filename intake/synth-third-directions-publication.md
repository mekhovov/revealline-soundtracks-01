# Third synth-direction publication binding

This guarded publication consumes only the exact hosted artifact prepared by
source PR #20. It does not reacquire or re-encode audio. It preserves the four
native sources, rights snapshots, technical receipts, pending review flags and
exact MP3 derivatives under the immutable intake archive, then creates one
four-recording listening-only batch.

- Source run: `36082136561`
- Artifact: `10843185196`
- Artifact bytes: `62,234,070`
- Artifact SHA-256: `fdcf01c091d53b7349d873569cb4fe4ba1e365432f52fd51f98938feb6d96ecc`
- Source head: `400367c644cafeae6e8ce94011cbb790561455f6`
- Hosted PR runner revision: `e774748eace8567fbeda3d8c8e31245a29dfbb9b`
- Permanent tree proof: `d674bd24db64dd20925148945158b265e8526f07`
- Source tree: `97bebf63ab89a3718ec172614ad5d3561e18d1d0`

The runner revision remains pinned to the artifact receipt. GitHub no longer
serves that temporary pull-request merge object after merge, so the remote gate
uses the permanent merge commit with the same base/source parents and identical
tree as proof of the checked-out source. The artifact digest, run identity,
source head, source-file hashes and embedded runner binding remain exact.

Publication adds listening previews only. Listening approval, game catalogue
admission, default selection and Recording-mode admission remain false. The
source statement that Neon Pulse has Content ID disabled remains a source claim;
it does not enable Recording mode. All other Content ID status remains unknown.

## Hosted assembly evidence

Failed run `36102828802` is preserved. It assembled and verified the exact
artifact, then stopped before commit or push because the source test still
required all four candidates to be absent after assembly. The corrected test
accepts only two complete states: all four exact source identities absent, or
all four exact identities and titles present. Partial publication and identity
mismatch remain failures.

Corrected run `36103067295` passed at source head
`cdaede794bc4c1084f6208f99d9e99d6f6034b48` and generated review commit
`6181c6fad391d7359525e40ce55094ec25923482`. It verified 132 unique
recordings across 13 collections, 761,327,907 public audio bytes and
762,215,203 total public bytes. The new immutable batch is 25,138,336 bytes;
its deployment manifest is 2,563 bytes with SHA-256
`63848e4351c83b507824345d124b498f98bc8ae982fc5eaebe60f0c1a84c85cd`.
The small assembly evidence artifact `10850495971` is 2,928 bytes with SHA-256
`a1fce8993ee5bc8fedfbf8c8ea0a7af837676d379a16b554de364b790f1d1dc0`.

Post-assembly pull-request run `36103455462` is also preserved. Its source and
archive checks passed, then its acquisition job correctly rejected the four
now-public exact identities as duplicates. The intake workflow now follows the
existing second-slate lifecycle: pull requests verify source and history only;
an explicit dispatch is required to reacquire the fixed audition artifact.
