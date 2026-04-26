---
name: python
description: Execute Python code in a subprocess
category: builtin
tags: [code, execution, interpreter]
---

# python

Execute Python code and return output.

## Arguments

| Arg | Type | Description |
|-----|------|-------------|
| code | string | Python code to execute (required) |

## WHEN TO USE

- Quick computations or data transformations
- Testing code snippets
- Checking Python environment/packages
- Complex string/data processing

## Behavior

- Code runs in a separate subprocess using the current Python interpreter.
- Has access to all installed packages in the environment.
- stdout and stderr are captured and returned.
- Configurable timeout; killed on timeout.

## Output

Returns combined stdout/stderr. Exit code is included in the result metadata.

## LIMITATIONS

- Runs in isolated subprocess (no state persistence between calls)
- Timeout applies (default: 60 seconds)
- Only packages installed in environment are available

## TIPS

- Use `print()` to output results
- For file operations, prefer `read`/`write` tools
- Check package availability before using
