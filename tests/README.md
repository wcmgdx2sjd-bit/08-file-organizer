# Tests

All nine milestones have 29 automated tests covering the reusable organizer module, thin CLI boundary, preview-only behavior, recursive discovery and apply behavior, category-folder skipping, JSON move receipts, SHA-256 fingerprint verification, preview-first undo, explicit approval, friendly invalid-path errors, atomic collision safety, and the real command-line entry point.

Run the tests from the project root:

```bash
python3 -m unittest discover -s tests -v
```
