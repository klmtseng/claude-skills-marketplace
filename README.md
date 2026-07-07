# Claude Skills Marketplace — ai-mac-workflows

A curated collection of 8 workflow skills for Claude Code, built and battle-tested in a personal AI workstation setup. Skills are de-personalized for team sharing — placeholder conventions are documented below.

**Version**: 0.1.0

---

## Included Skills

| Skill | Description |
|---|---|
| `agent-memory` | Bounded memory + forgetting for long-running LLM agent loops (ring-buffer, compaction, recall) |
| `code-recon` | Cost-ladder codebase analysis: cheapest-first tool selection with mandatory cross-audit of graph tools |
| `core-gate` | AI-generated code quality enforcement: 3-gate headless pipeline (static purity + determinism + scenario) |
| `gh-vercel-publish` | Publish a local project to GitHub + Vercel via device-flow CLI, zero manual token pasting |
| `hostile-room` | 6-step communication playbook for adversarial/high-stakes settings (interviews, pitches, negotiations) |
| `stream-capture` | Live stream / webinar → timestamped transcript + deduplicated slides + synced notes |
| `tokenomics` | LLM cost engineering: pre-project estimation, budget gates, cost regression tests, weekly reconciliation |
| `validity-audit` | Pre-publication self-falsification: mechanical audit + mandatory independent reviewer, 3-tier threat model |

---

## Installation

### From a Git remote (GitLab or GitHub)

```bash
# Once the repo is hosted:
/plugin marketplace add https://gitlab.example.com/<your-org>/claude-skills-marketplace
# or
/plugin marketplace add https://github.com/<your-org>/claude-skills-marketplace
```

### Local testing (before pushing)

```bash
/plugin marketplace add /path/to/claude-skills-marketplace
```

To use an individual skill after installation:

```
/agent-memory
/validity-audit
/tokenomics
# etc.
```

---

## De-personalization Policy

Original skills were built with local paths, usernames, and project names baked in. This published copy replaces them with explicit placeholders:

| Placeholder | Meaning |
|---|---|
| `<your-username>` | Your GitHub / Vercel account handle |
| `<id>+<your-username>@users.noreply.github.com` | Your GitHub noreply commit email |
| `<your-project>` | Your specific project/repo name |
| `你的工具目錄/` | Directory where you store local CLI tools |
| `你的成本追蹤目錄` | Directory for your tokenomics scripts and data |
| `你的通知管道` | Your notification channel (bot, webhook, etc.) |

Search for these placeholders in any skill before using it in a new environment.

---

## Environment Notes

- `stream-capture` works best with public streams via yt-dlp or m3u8 URLs. Wayland-specific caveats are in the Appendix section of that skill's SKILL.md.
- `tokenomics` references companion scripts (`ref_class.py`, `budget_estimate.py`, etc.) that you maintain separately in your cost-tracking directory.
- `core-gate` scripts (`static_scan.py`, `determinism_gate.py`, `drift_gate.py`) are bundled under `skills/core-gate/scripts/` and work with any project that follows the gate config schema.
- `validity-audit` ships with an `audit_ledger.jsonl` of historical failure cases and golden test cases under `meta_eval/` — these are intended to accumulate over time.

---

## License

Skills are shared as-is for internal team use. No warranty.
