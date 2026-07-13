# Good First Issues (curated backlog)

Status: draft backlog as of 2026-07-13  
Audience: maintainers filing GitHub issues; new contributors picking work  
Related: `CONTRIBUTING.md`, `docs/plans/PHASE2-ARCHITECTURE-INVENTORY.md`, `docs/plans/ENGINEERING-MATURITY-PLAN.md`

These are **concrete, repo-derived** starter tasks. They are written so each can
become a GitHub issue with labels `good first issue` + one of `docs` /
`engineering` / `privacy` / `gateway` / `bug`.

Do not expand scope into live QQ payload work or private memory dumps.

---

## How to file

1. Copy one item below into a new GitHub issue.
2. Keep the acceptance criteria checklist intact.
3. Link this file and any inventory/plan section cited.
4. Prefer small PRs; pure docs/tests first.

---

## Issue 1 — Document Make-less Windows contributor commands in CONTRIBUTING

**Area:** docs  
**Why real:** `Makefile` targets are the documented pre-push gate, but many
Windows contributors lack `make`. Root README has partial PowerShell paths;
`CONTRIBUTING.md` can be clearer with a single copy-paste block.

**Acceptance criteria**

- [ ] `CONTRIBUTING.md` has a “Without Make (Windows)” subsection mirroring
      `make test`, `make lint` / critical ruff, and `make check`
- [ ] Commands use relative paths from repo root (no `D:\XinYu\...`)
- [ ] Cross-link `docs/system/FRESH-INSTALL.md`
- [ ] No behavior/code change required

---

## Issue 2 — Audit tracked env examples vs gitignore

**Area:** privacy / docs  
**Why real:** Policy says only examples are tracked; app ships
`xinyu.local.env.example` while `*.env` / `*.local.env` are ignored. A short
audit prevents accidental secret paths before `v0.1.0`.

**Acceptance criteria**

- [ ] Inventory of tracked `*env*` / secret-like paths recorded in the PR
      description (or a short note under `docs/reports/` only if maintainers want
      it; default: PR body only)
- [ ] Confirm no non-example env files are tracked (`git ls-files` evidence)
- [ ] If gaps found: fix `.gitignore` and/or untrack with maintainer approval
- [ ] Update `docs/plans/RELEASE-CHECKLIST.md` privacy section only if a new
      check is needed

---

## Issue 3 — Curate a “quick smoke” list for a future blocking job

**Area:** tests / engineering  
**Why real:** CI smoke job is informational and often needs a live env.
Engineering plan calls for a curated quick subset before making smoke blocking.

**Acceptance criteria**

- [ ] Identify ≤15 smoke tests or `smoke_run.py` groups that are hermetic
      (no live QQ/NapCat/LLM)
- [ ] Document the list in PR body or a small note linked from
      `docs/plans/ENGINEERING-30-DAY-CHECKLIST.md` Day 15–21 item
- [ ] Do **not** flip CI to blocking in this issue unless hermeticity is proven
      in CI logs
- [ ] Each listed test includes one-line rationale (why it is safe offline)

---

## Issue 4 — Reduce one informational ruff violation cluster under `XinYu-Core/src`

**Area:** engineering / lint  
**Why real:** Critical ruff on core is blocking (`F,E9,F63,F7,F82`); full ruff on
core is still informational with residual debt.

**Acceptance criteria**

- [ ] Pick one rule family (e.g. import sorting, unused imports outside critical
      set) and fix **only** that family under `XinYu-Core/src`
- [ ] `ruff check XinYu-Core/src --select F,E9,F63,F7,F82` still passes
- [ ] PR shows before/after count for the chosen rule (`ruff check --statistics`)
- [ ] No drive-by refactors outside the rule family

---

## Issue 5 — Add a focused unit test around a pure helper in the QQ gateway

**Area:** tests / gateway  
**Why real:** `xinyu_qq_gateway.py` is a ~4k-line god file (see Phase 2
inventory). Pure normalize/parse helpers are good first test targets without
touching live NapCat.

**Acceptance criteria**

- [ ] Choose an existing pure function (no network, no real payloads)
- [ ] Add or extend a unit test under the app `tests/` tree with synthetic
      fixtures only
- [ ] `pytest -q -m "not smoke"` passes for the touched tests
- [ ] PR describes the helper and why the fixture is non-private

---

## Issue 6 — Inventory call map for the next bridge store cluster

**Area:** engineering / refactor prep  
**Why real:** Pilot consolidated some stores into `xinyu_bridge_stores.py`;
remaining clusters are listed in `PHASE2-ARCHITECTURE-INVENTORY.md` as todo
(bootstrap/CLI env, proactive/promise, desktop, etc.).

**Acceptance criteria**

- [ ] Pick **one** todo cluster from the inventory table
- [ ] Produce an import/call map (rg results) of producers/consumers
- [ ] Record current file count for that name pattern (before numbers)
- [ ] Propose target module name + shim policy in the PR/issue comment
- [ ] **No** mass move required in this issue (docs-only PR is fine); if code
      moves, must be behavior-preserving with tests green

---

## Issue 7 — Split documentation: link FRESH-INSTALL from root README Setup

**Area:** docs  
**Why real:** Fresh-install detail lives in `docs/system/FRESH-INSTALL.md`; root
`README.md` Setup should stay short and point there so strangers do not miss
privacy and CI-gate nuance.

**Acceptance criteria**

- [ ] Root `README.md` Setup section links `docs/system/FRESH-INSTALL.md`
- [ ] Does not duplicate the entire guide
- [ ] Mentions Python 3.12 / Node 20 and `make check` vs blocking CI names
- [ ] Privacy boundary still points at `OPEN_SOURCE_POLICY.md` / `SECURITY.md`

---

## Issue 8 — Desktop: document or fix `npm run lint` gaps for new files

**Area:** desktop / engineering  
**Why real:** CI runs `npm run typecheck` and `npm run lint --if-present` under
`XinYu_Desktop`. New contributors often only typecheck locally.

**Acceptance criteria**

- [ ] Confirm `npm run lint` passes on a clean install (Node 20)
- [ ] If failures: either fix a **small** eslint set or document known debt with
      file paths in the PR (no silent ignore without comment)
- [ ] `CONTRIBUTING.md` desktop section mentions lint alongside typecheck
- [ ] No Electron runtime feature work in this PR

---

## Issue 9 — Clarify dual-branch contributor wording after BRANCH-POLICY

**Area:** docs  
**Why real:** `docs/system/BRANCH-POLICY.md` defines `main` as canonical while
`master` may still hold integration work. Issue templates / README may still
read as if only one branch exists.

**Acceptance criteria**

- [ ] Audit root `README.md`, `CONTRIBUTING.md`, and `.github/pull_request_template.md`
      for branch base instructions
- [ ] Align wording with `BRANCH-POLICY.md` (PR against `main` when cutover
      done; transition note if needed)
- [ ] No force-push or branch deletion in this issue

---

## Issue 10 — Add sanitized “gateway failure” fixture note for issue reporters

**Area:** docs / gateway / privacy  
**Why real:** Gateway failures are high-noise and high-leak risk. Template exists;
reporters still need a short “what a good sanitized log looks like” example.

**Acceptance criteria**

- [ ] Add a short sanitized example (fake IDs, redacted tokens) either in
      `.github/ISSUE_TEMPLATE/gateway_failure.yml` description or a linked doc
      under `docs/system/` or `docs/reports/`
- [ ] Explicit “never paste raw QQ payloads” remains
- [ ] Example contains no real credentials or owner data
- [ ] Cross-link `SECURITY.md`

---

## Stretch (still good-first if scoped tightly)

| Idea | Why |
|------|-----|
| Measure and record `xinyu_bridge_*_store.py` count in inventory | Metrics for Phase 2 exit criteria |
| Fix one flaky unit test with issue link | Test hygiene goal in maturity plan |
| Dependabot safe patch PR triage notes | Day 15–21 checklist item |

---

## Maintainer notes

- Prefer filing **at least five** of the above as real GitHub issues before
  claiming Phase 3 “good first issue set” exit criteria complete
  (`ENGINEERING-MATURITY-PLAN.md` Phase 3).
- Labels (when configured): `good first issue`, plus `docs` / `engineering` /
  `privacy` / `gateway` / `bug` as appropriate.
- Acceptance criteria above are the definition of done; expand only with
  maintainer agreement.
