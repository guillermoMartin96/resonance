# Engineering playbook

## Branches and commits
Create `feature/m0-research` first. Commit at logical checkpoints with clear messages. Push only when configured and authorized. Never merge to main without explicit approval; favor PR and independent review.

## Decision protocol
For ambiguous high-impact choices, create a numbered request with options, recommendation, evidence and reversible/irreversible consequences. Continue non-blocked work only. Track assumptions explicitly.

## Quality protocol
Write small, reviewable changes. Tests before marking tasks complete. Validate inputs and file paths, use safe subprocess invocation, timeouts, bounded resources, and no arbitrary model-supplied shell commands. Prefer deterministic fixtures and reproducible dependencies.

## Proof protocol
Record OS/environment, dependency versions, exact commands, fixture licensing, expected/observed results, model versions, timing, failures and limitations in `docs/proof/Mx-proof.md`.

## Review protocol
After each milestone, ask an independent coding agent to review correctness, security, license compliance, architecture and tests. Log issues with severity, fix critical/high findings and rerun gates. Preserve commit references.

## Costs
Prefer local and free tools. Ask before paid APIs, GPU rental, or other spending. Track model artifacts and disk footprint.
