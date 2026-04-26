# Runtime Boundaries

The AstrBot shell is intentionally thin.

## The Shell May

- receive AstrBot message events
- identify private vs group messages
- enforce a platform user whitelist
- forward text to a local XinYu bridge endpoint
- send the returned text reply back through AstrBot
- stop AstrBot's downstream LLM pipeline for accepted messages

## The Shell Must Not

- write XinYu memory files directly
- decide personality or relationship updates
- trigger autonomous web search
- convert images, voice, files, or group context into facts
- apply self-iteration proposals
- bypass XinYu source, privacy, adapter, memory, or growth gates

## Early Testing Defaults

- private text only
- whitelist required
- group handling disabled
- non-text messages ignored or held outside XinYu
- broad autonomous search remains disabled in the XinYu core

## Later Expansion

Add platform capabilities in this order:

1. private text with owner whitelist
2. private text with explicit small trusted list
3. group read-only/staged events
4. image or voice as staged events only
5. explicit memory admission policies for non-owner people

Do not add platform-side memory shortcuts. All durable decisions belong in the
XinYu core.
