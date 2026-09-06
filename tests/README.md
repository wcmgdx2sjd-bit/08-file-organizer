# Tests

All seven milestones have 15 automated tests covering the reusable organizer module, thin CLI boundary, preview-only behavior, explicit approval, friendly invalid-path errors, atomic collision safety, and the real command-line entry point.

Run the tests from the project root:

```bash
python3 -m unittest discover -s tests -v
```
