# #131 Plan: test-first stale-base proof

1. **RED**: Preserve a new synthetic test of `validate_provenance` with event base `BASE`, first parent `ADVANCED_BASE` and second parent exact `HEAD`: without a verified ancestry callback reject; with a trusted callback accept; wrong head, parents, or different github ref still reject. Also add mocked REST comparison tests asserting valid ahead/identical ancestry and denial on divergent/behind/missing/invalid responses.
2. **GREEN**: factor a small strict `verify_advanced_pr_base` GitHub REST helper, which checks immutable SHA ancestry twice against the verified live target branch; wire it to the pure validator only for true stale-base cases. Existing strict/equal, push/dispatch paths stay network-free.
3. Ensure all CI jobs that invoke the provenance check explicitly supply a read-only token (`GH_TOKEN: ${{ github.token }}`) and all path-filtered acceptance checks track provenance script changes.
4. Exact-head Python 3.10/3.12/3.13 plus real Workbooks/Agora and reviewed CUC/Context-Fabric/Appendix. Synthetic HEAD should still prove checked-out SHA equality and merge-ref integrity; test with a genuinely stale event locally through mocks.
5. Logically independent adversarial review attacks direction of ancestry, replaced refs, token omissions/API failures, head swaps, forged unrelated base, operational rate limits, stdout leak and effect on publish workflow; REVIEW COMMENT on exact head. Do not merge before published v0.3.0; never alter current release candidate or its tag.

## Review-derived token redirect gate

6. Preserve RED for a token-bearing ancestry request requiring a request-local no-redirect transport (global `urlopen` is prohibited) and a redirect handler that refuses forwarding credentials even if an API 3xx names another host. GREEN with a custom `HTTPRedirectHandler` in `build_opener` for each request; never install a process-global opener. Adapt the existing mocked REST ancestry checks to the new request-local seam; verify they still assert three exact trusted URLs and fail-closed ancestry behavior. Run the full exact-head gates again, and repeat independent review on that head.
