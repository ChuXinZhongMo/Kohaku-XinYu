# Xinyu Real Life Input Adapter Policy v0.1

This document defines the future boundary for IM, image, voice transcript, group chat, private chat, and real-world context adapters.
It is a planning and validation layer only. It does not connect to any real account, device, chat platform, microphone, camera, or location service.

## Core Rule

Every real-life input must become a typed event first.
No adapter event may directly rewrite self, owner, relationship, emotion, dream, archive, or knowledge memory.

The required path is:

event -> adapter policy -> turn mode -> interpretation gate -> memory/source route -> normal writers or source pipeline

## Event Schema

Each event candidate should carry:

- `event_id`
- `source_channel`: `im`, `private_chat`, `group_chat`, `image`, `voice_transcript`, `system_context`
- `source_context`: `owner_private`, `group`, `public`, `unknown`
- `actor_id`: `owner`, `person:<id>`, `group:<id>`, or `unknown`
- `relationship_scope`: `owner`, `non_owner`, `group`, or `unknown`
- `content_type`: `text`, `image`, `voice_transcript`, `metadata`
- `content_summary`
- `observed_at`
- `contains_owner_private`: `yes` or `no`
- `contains_private_location`: `yes` or `no`
- `owner_intent`: `explicit`, `implicit`, or `none`
- `interpretation_status`: `raw`, `interpreted`, or `confirmed`
- `status`: `candidate`, `hold`, or `closed`

## Routing Rules

- IM/private owner text can become a relationship or emotion review candidate only after turn mode accepts it as a real user expression.
- Group chat is group context by default; it is not an owner relationship event just because the owner appears in it.
- Non-owner messages can update non-owner person candidates, but default priority remains below owner.
- Raw images are not facts. They need interpretation before memory or knowledge routing.
- Voice transcripts are text candidates with transcript uncertainty; facts need confirmation before durable write.
- Private address or precise location requires explicit owner intent and protected memory routing.
- Public or group content may create source/context candidates, but not owner-private memory.

## Real-World Anchors

Allowed anchors:

- observed timestamp
- channel type
- coarse context such as day phase or group/private setting
- owner explicitly provided address/location when protected and intentional

Blocked anchors:

- precise private location inferred from image metadata
- contact identifiers without explicit permission
- third-party private information
- unconfirmed claims from group chat treated as fact

## Memory Thresholds

- trivial event: no durable write
- ordinary social event: recent context only
- owner emotional event: emotion/relationship review candidate
- repeated non-owner event: non-owner profile candidate
- image or voice fact: hold until interpreted and confirmed
- private address/location: protected anchor candidate only with explicit owner intent

## Adapter Non-Goals

- No direct platform integration in this milestone.
- No automatic sending, posting, scraping, recording, or location reading.
- No bypass of resource-boundary posture.
- No bypass of social inquiry policy for external posting.
- No direct learner integration from raw adapter events.
