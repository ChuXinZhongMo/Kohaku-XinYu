## Summary

<!-- What changed and why. One short paragraph. -->

## Type

- [ ] fix
- [ ] feat
- [ ] refactor
- [ ] test
- [ ] docs
- [ ] chore / engineering
- [ ] other

## Surface

- [ ] `XinYu-Core` runtime
- [ ] `xinyu` agent app
- [ ] QQ / gateway
- [ ] Desktop shell
- [ ] Operator scripts (`XinYu.ps1`, `scripts/`)
- [ ] CI / repo hygiene
- [ ] Docs only

## Validation

<!-- Run what you can. Prefer Makefile / documented commands. -->

- [ ] `make test` or app `pytest -q -m "not smoke"`
- [ ] `make lint` / ruff on touched paths (if available)
- [ ] Desktop `npm run typecheck` (if desktop touched)
- [ ] Relevant smoke (if integration path touched)
- [ ] N/A — docs-only or pure chore

Commands / notes:

```text
```

## Privacy boundary

- [ ] No secrets, `.env` bodies, tokens, or private keys
- [ ] No private QQ payloads or local memory dumps
- [ ] No owner-supplied material bodies
- [ ] No unclear-license third-party source snapshots

## Reviewer notes

<!-- Risk, rollout, follow-ups, linked issues. -->

Fixes #
