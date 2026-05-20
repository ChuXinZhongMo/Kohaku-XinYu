# Expression Stability

Expression is split into three layers:

- Intent: the functional meaning of the turn, such as greeting, acknowledgement, technical request, or relationship pressure.
- Stance: the conversational posture XinYu should take, such as calm, task-focused, accountable, or waiting.
- Surface expression: the final visible wording after model generation, renderer, dedupe, and final reply guard.

The runtime should not fix expression problems by adding canned fallback replies. Empty replies are recovered through rendering/model retry paths, and major guard rewrites are traceable through `final_reply_guard_rewrite`.
