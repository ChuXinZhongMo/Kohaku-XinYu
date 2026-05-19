# Services

Runtime service helpers live here. They can support the turn path, but should
not own bridge routing, transport adapters, or stable persona policy.

- `daily_digest.py` builds and maintains the watched-source daily digest. The app-root `xinyu_daily_digest.py` is only a compatibility wrapper.
- `chat_service.py` validates chat requests and owns lightweight turn clock setup. The app-root `xinyu_chat_service.py` is only a compatibility wrapper.
