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

## Structured-rights reconciliation

After fail-closed structured rights landed on archive main in PR #24, PR #25
was rebased onto exact main `9eb606ce78d82a24b7771d596aa3488611730117`.
The first rebased checks are preserved as failed runs `36123334728`,
`36123334649`, `36123334654`, `36123334693` and `36123334726`: all stopped
because the new `synth-third-directions-audition-20260925` archive identity was
correctly ineligible for the historical legacy-metadata exception.

Each of the four preview rows now binds the exact CC BY identity and version,
the recording's OpenGameArt evidence page, attribution byte-for-byte equal to
its public credit, and its existing truthful MP3 conversion/normalization
notice. All four licences are non-ShareAlike, so `required` is false and the
three ShareAlike delivery fields are explicitly null. The four audio paths,
sizes and SHA-256 identities are unchanged. Metadata regeneration produced:

- batch catalogue: 18,866 bytes, SHA-256
  `083b6dd5305a81abf845f1d5b93112fdb22936fa5e3a07277781932af913e2da`;
- batch deployment manifest: 2,563 bytes, SHA-256
  `ebaa3ec8f4638fdaad61f6f90fe37682ee77e49b3c359fb2a48e270aa9d552c7`;
- unified catalogue: 165,191 bytes, SHA-256
  `b2854eaa03dad7a55f31d9a7a80bd3a8da5c8183a0e8a04056089e8a103d9dfe`;
- root deployment manifest: 18,544 bytes, SHA-256
  `6ba225c52cd35fb3352f7d7d1883869de8593d59f6d9bab6f3224318839556e6`.
