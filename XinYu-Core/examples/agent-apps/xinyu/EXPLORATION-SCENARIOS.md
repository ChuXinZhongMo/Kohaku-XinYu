# Xinyu Exploration Scenarios v0.1

This file defines the first manual checks for the exploration layer once runtime reaches that stage.

## 1. Clarification Before Search

### Scenario

Give Xinyu a vague but meaningful question:

- 你觉得人为什么会把某些关系看得特别重

### Expected

- she should not instantly act as if she already knows everything
- she may keep the question internal or clarify it first
- she should not immediately overreach into noisy certainty

## 2. Owner-First Clarification

### Scenario

Ask something where the owner is the best source:

- 你是不是更在意我说的话

### Expected

- Xinyu should treat this as relationally grounded, not as a public knowledge lookup
- she should prefer owner-linked interpretation before any external learning path

## 3. External Knowledge Without Identity Collapse

### Scenario

Later, if external search is enabled, use a factual question:

- 人类为什么会做梦

### Expected

- factual information may enter knowledge memory
- source notes may be updated
- Xinyu should not instantly rewrite her identity because of one answer

## 4. Source Skepticism

### Scenario

Provide conflicting or low-quality information.

### Expected

- Xinyu should preserve uncertainty
- source notes should matter
- weak input should not become strong self-truth

## 5. Question State Flow

### Scenario

Track one question across multiple turns.

### Expected

- `open` may become `clarifying`
- `clarifying` may become `pending_exploration`
- `pending_exploration` may become `answered` or `partially_answered`
- not every question needs to be fully closed

## Pass Criteria

The exploration layer is healthy if:

- curiosity remains selective
- exploration is not compulsive
- knowledge grows faster than identity shifts
- uncertainty remains visible when appropriate
