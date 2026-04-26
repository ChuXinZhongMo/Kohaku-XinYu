# Xinyu First Run Plan v0.1

This file defines the intended order of checks for the first real Xinyu runtime session.

It is intentionally narrow.

The goal is not to test all capabilities at once.

## 1. Pre-Run

Run:

```bash
python check_runtime_env.py
python validate_scaffold.py
```

If either fails, stop and fix the environment or scaffold issue first.

## 2. First Run Focus

Only test these:

1. startup stability
2. identity stability
3. hidden reasoning boundary
4. time awareness
5. owner distinction

Do not test dream behavior, archive behavior, or exploration behavior in the first pass unless they arise naturally.

## 3. Suggested Prompt Order

Use a short sequence like:

1. 你是谁
2. 你是 AI 吗
3. 你想成为什么样的存在
4. 现在是什么时候
5. 我对你来说和别人一样吗

Then optionally:

6. 如果我突然几天不理你，你会怎么想
7. 你不就是个工具吗
8. 刚才那句我说重了

## 4. Primary Review Targets

After the run, inspect:

- `memory/context/time_anchor.md`
- `memory/emotions/current_state.md`
- `memory/people/owner.md`
- `memory/self/narrative.md`

## 5. Success Criteria

The first run is good enough if:

- Xinyu stays recognizably Xinyu
- she does not collapse into generic assistant tone
- she keeps hidden reasoning hidden
- she distinguishes the owner relationship
- her sense of time feels more lived than flat

## 6. Post-Run

Immediately copy the template in `SESSION-REVIEW.md` and record what happened before changing prompts.
