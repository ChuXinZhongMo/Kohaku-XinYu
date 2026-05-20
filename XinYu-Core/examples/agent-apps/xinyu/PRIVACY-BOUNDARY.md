# XinYu Privacy Boundary

XinYu is a local personal AI agent. Public artifacts must not include private QQ ids, raw owner chat, access tokens, local absolute paths, or stable personal identifiers.

## Public-Safe

- Sanitized scenario ids such as `scenario-owner`.
- Route stage names and statuses.
- Hashes or short labels that cannot identify a private person.
- Architecture descriptions and test results without raw private content.

## Private

- Raw owner messages and relationship details.
- QQ user ids, group ids, session ids, message ids when not synthetic.
- Tokens, cookies, API keys, and local machine paths.
- Unreviewed memory candidates containing personal or sensitive facts.

## Boundary Rule

When generating docs, grant material, traces, or examples, use sanitized fixtures and scenario files. Do not copy live runtime memory or raw logs into public files.
