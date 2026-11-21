# TDD and ATDD evidence guide

The automated tests in `portal/tests.py` cover authentication, profile ownership, chatbot normal/unknown/emergency behavior, AJAX persistence, doctor search, booking, cancellation, past slots, and account isolation.

To demonstrate Red–Green–Refactor honestly during development:

1. Create a focused test for one acceptance behavior and run it. Save the failing test output with the commit/branch and timestamp as Red evidence.
2. Implement only enough behavior to pass; run that test and save Green output.
3. Refactor names/structure without changing behavior; rerun the focused test and full regression suite; save Refactor output.
4. Keep the commits or CI run URLs and screenshots of actual output. This repository does not claim a historical Red/Green sequence; capture evidence during the team's own changes.

ATDD Given–When–Then scenarios for all eight stories are in `product-backlog.md`. Translate each scenario into a test before implementation where practical.
