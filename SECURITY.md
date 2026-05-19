# Security Policy

Do not report private tokens, QQ payloads, local memory contents, owner-supplied
material bodies, or credentials in public issues.

## Supported Surface

Security review currently covers the public source tree, tests, operator tools,
and desktop shell.

Private local runtime state is intentionally excluded from publication.

## Reporting

Open a private security advisory or contact the repository owner directly for:

- credential exposure
- unsafe filesystem access
- unintended publication of private runtime state
- unauthorized network or QQ gateway behavior
- dependency supply-chain issues

Reports should include paths, versions, reproduction steps, and sanitized logs
only.
