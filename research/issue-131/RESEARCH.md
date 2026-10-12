# #131 Research: validate stale event base without trusting arbitrary merge parents

## Reproduced CI failure and code path

`scripts/check_ci_provenance.py::validate_provenance` currently insists that the two parents of GitHub's `refs/pull/<number>/merge` commit are *exactly* `(event.pull_request.base.sha, event.pull_request.head.sha)`. PR #130 demonstrated that GitHub may provide an event base SHA from before master advances, while the actual GitHub-generated synthetic merge first parent is the newer master. A synthetic HEAD update did not remedy this; merging master into the PR branch eventually did. The security-critical exact checkout `GITHUB_SHA`, exactly-two-parents and second-parent `head.sha` checks must remain.

## Verified real repository ancestry (GitHub REST, 2026-10-12)

`GET /repos/alexsosn/CTC-TF/compare/81cc9a6c4a233bbc06b5349515a5a466497d274d...ed6c7059803ff1adee057f5bd94d3ca661aac187` reports `status=ahead`, `ahead_by=13`, `behind_by=0`, merge-base SHA equal to the old event base. The current branch ref API `git/ref/heads/master` returns `ed6c705...`. Thus a stale event base is a true *ancestor*, not an arbitrary merge parent. Compare direction is consequential: reversing these endpoints reports `behind` and must be rejected.

## Safe implementation strategy

The existing strict-equality branch stays offline and unchanged for normal PR events and push/dispatch. Only when the first parent is different, validate:
1. event is a genuine `pull_request` with GitHub-provided `GITHUB_REF=refs/pull/<number>/merge`, matching PR number and valid base ref/repository;
2. exact checked-out SHA equals GITHUB_SHA, merge has exactly two distinct valid parents, and second parent equals event head SHA;
3. use GitHub's authenticated **read-only** REST compare API to prove the old event base is an ancestor of the checked-out synthetic merge's first parent;
4. verify that the synthetic first parent is itself an ancestor of the live **same target branch** (GET branch ref then compare), so a malicious off-branch descendant of the event base is never accepted;
5. fail closed for non-200, invalid JSON, missing token, mismatch, force-push/diverged history, malformed names and API errors. Never interpret a network error as approval; never echo a token.
6. return explicit integer/sha-only provenance evidence, differentiating a directly equal base from independently verified advanced base.

This uses standard-library urllib; no additional Python dependency or full Git history download. It incurs authenticated API requests only on the rare stale-base case. Each CI provenance step receives the GitHub read-only token via an explicit step-local environment binding; no token is printed. All PR workflows must trigger if the checker changes.

## Threat/limitations

The GitHub runtime event and refs are trusted; a pull request can change checked-in scripts, so branch protection/reviewer gates remain necessary. The API proves ancestry at verification time, not a cryptographic guarantee against future forced master updates; a missing/verifiably rewritten target branch correctly fails closed. No Burns data or related corpus features are affected.

## Independent review: token-bearing HTTP redirects (2026-10-12)

Source audit of Python's standard-library `urllib.request.HTTPRedirectHandler.redirect_request` finds that it copies all request headers except `content-length` and `content-type` to a redirected GET, **including Authorization**. The new `_github_json` currently calls the globally configured `urllib.request.urlopen` with a GitHub token. Even though the initial REST endpoint is fixed HTTPS `api.github.com`, an HTTP 3xx response can forward the token to a different redirect origin before code has a chance to inspect the final URL. This is not evidence of GitHub actually redirecting ancestry endpoints, but it violates the intended fail-closed token boundary.

Review-derived gate: preserve RED proof that the ancestry transport must not call redirect-following global `urlopen` and that the configured redirect handler refuses a 3xx to a different host; then GREEN by using a request-local no-redirect opener. Keep all existing pure ancestry and CI tests, no publisher write-token access, and no corpus changes.
