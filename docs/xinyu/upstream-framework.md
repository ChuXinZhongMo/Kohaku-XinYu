# Upstream Framework Snapshot

XinYu currently carries a source snapshot of KohakuTerrarium in this repository.

That is intentional for now. XinYu's local runtime, bridge scripts, tests, and
development workflow still depend on the local framework source. Removing it too
early would make the project look cleaner but would risk breaking the working
system.

## Current Boundary

XinYu-owned material:

```text
examples/agent-apps/xinyu/
docs/xinyu/
integrations/
Plan.md
ROADMAP.md
README.md
```

Vendored framework material:

```text
src/kohakuterrarium/
src/kohakuterrarium-frontend/
tests/
docs/en/
docs/zh-CN/
docs/zh-TW/
examples/agent-apps/          except xinyu
examples/terrariums/
```

## Why Keep It

- XinYu can run against the local source without relying on a published package.
- Local smoke checks can exercise the same framework code that XinYu uses.
- Development remains reproducible on the current machine.

## Later Cleanup

Before removing or moving the framework snapshot, XinYu needs:

1. A clean package dependency path.
2. A verified install process from a fresh clone.
3. Replacement docs for all XinYu-specific startup and recovery commands.
4. Smoke tests that pass without relying on removed upstream files.

Until then, the snapshot should be treated as a vendored implementation
dependency, not as the public identity of this repository.
