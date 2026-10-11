# #128 — Plan (research → RED → GREEN → CI → independent review)

1. Preserve test-first RED in `tests/test_reviewed_release_publisher.py` before publisher code. Fake GitHub REST client asserts verified merge SHA, same-tree second parent, six green exact-PR-head workflows, green master push Tests, immutable package+manifest versions, local-only Burns data, typed confirmation, preexisting correct/wrong tag handling, missing/failed checks, and no mutation under preflight.
2. Implement smallest explicit `scripts/publish_reviewed_release.py` with:
   - `GH_TOKEN` and `gh api` subprocess transport isolated behind injectable client;
   - conservative `--publish` opt-in (default validation/preflight only);
   - current-default-master exact-SHA and confirm-text requirements;
   - safe Git ref creation, then GitHub Release creation using reviewed notes from target commit; no attachments; after-write verification.
3. Add `.github/workflows/publish-reviewed-v0.3.0.yml` with `workflow_dispatch` only, exact text inputs, pinned `actions/checkout`, no third-party publishing action, job-level `contents: write` and `GH_TOKEN: ${{ github.token }}`. Update pinned-checkout inventory in existing CI test and add source-safe workflow safety assertions.
4. Update `docs/releases/v0.3.0.md` minimally with the manual publication gate and explicit no-corpus-assets rule. It remains technically accurate before and after Release.
5. Run exact-head Python 3.10/3.12/3.13, reviewed CUC index, Context-Fabric, licensed real Workbooks/Agora Bubblewrap, CUC Burns feature-only, Appendix. Confirm true workflow results.
6. Perform **logically independent adversarial review** anchored to frozen HEAD: challenge wrong commit, race after preflight, tag squatting, truncated CI evidence, GitHub API error/404 handling, malformed metadata, workflow injection/permissions, source licensing and assets, and idempotency. Review via `COMMENT`.
7. Merge only after complete exact-head CI/review, then independently review new master release-candidate **merge commit** and its push Tests; because publisher workflow changes master, the previous `81cc9a6...` is replaced as candidate, not published as an arbitrary historical commit. User must explicitly dispatch the manual publisher with the new reviewed full SHA. Do not claim publication until tag and Release are both verified.
