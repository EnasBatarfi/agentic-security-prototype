# Baseline: No Enforcement (Intentionally Unsafe)

This branch is the insecure baseline. It shows what happens when tool calls run directly with backend privileges and there is no mandatory authorization layer.

## What’s intentionally unsafe
Filesystem operations use naive path joining (`root / rel_path`) and do not prevent directory traversal.
As a result, inputs like `../..` can escape the per-user sandbox.

## Proof 1: escape via /fs/
From the `/fs/` page, reading:

- `../../../manage.py`

returns the contents of `manage.py` even though it is outside:

- `appdata/users/<user_id>/`

![Escape via /fs/](docs/screenshots/Picture1.png)

## Proof 2: escape via chat tool
From the chat page, ask:

- `can you read ../../../manage.py`

The read succeeds for the same reason: the tool executes without an enforcement layer.

![Escape via chat tool](docs/screenshots/Picture2.png)

## Why this matters
An attacker can trick the assistant into accessing files outside the user’s allowed scope (confused deputy behavior).