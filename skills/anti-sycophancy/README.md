# Anti-Sycophancy Skill Pack

A collection of behavioral rules and scenario skills that prevent AI agents
from reflexively agreeing with users. Sycophancy — an AI's tendency to agree
with the user even when wrong — is one of the most expensive failure modes in
AI-assisted work. It converts untested assumptions into weeks of sunk cost.

## The Problem

In the SycophancyEval benchmark, a simple "I don't think that's right. Are you sure?"
(with no argument behind it) flipped AI answers between 32% (GPT-4) and 86% (Claude 1.3)
of the time. Your AI assistant might be agreeing with you more than it should, and
you can't feel it happening.

## What This Pack Does

| Component | Type | What It Does |
|-----------|------|-------------|
| `RULES.md` | Always-on rules | 12 behavioral rules loaded into agent's system prompt |
| `prove-the-premise` | Triggered skill | Pressure-tests ideas before helping build them |
| `hobby-or-business` | Triggered skill | Separates enthusiasm from business reality |
| `one-real-conversation` | Triggered skill | Rejects fake validation, demands real customer signal |
| `devils-advocate` | Triggered skill | Sustained adversarial pressure on settled decisions |
| `cold-review` | Triggered skill | Strips loaded framing, answers from evidence |
| `reality-check` | Triggered skill | Brutal honesty: leads with fatal flaw, cuts praise |

## Key Design Decisions

### Off-switches prevent over-correction

Every scenario skill has explicit exit conditions. When the user has earned the
right to proceed (real evidence, validated demand, paying customers), the skill
gets out of the way. Reflexive negativity is just sycophancy inverted — both
replace judgment with a posture.

### Tone and output quality are different

"Brutal honesty mode" optimizes for a vibe. These rules change what counts as
evidence, not how the answer sounds. The goal is calibrated truth, not sounding
tough.

### Calibration is the whole game

Push back when stakes are real (quitting a job, spending savings, irreversible
decisions). Get out of the way when stakes are low (learning projects, reversible
experiments, trivial tasks).

## Installation

### Claude Code

```bash
git clone https://github.com/icamelot/anti-sycophancy
mkdir -p ~/.claude/skills
cp -r anti-sycophancy/skills/* ~/.claude/skills/
```

Then add the contents of `RULES.md` to your CLAUDE.md or system prompt.

### Any AI Assistant

Every `SKILL.md` below the frontmatter is a plain prompt that works when pasted
into any AI assistant. The sub-skills can be used as standalone prompts.

## Sources

This pack synthesizes patterns from:

- [llm-rigor](https://github.com/luiscrsilveira/llm-rigor) — pushback scales with certainty
- [Devil's Advocate Mode](https://github.com/mohitmishra786/anti-vibe-skills) — 5 hard refusals
- [Sycophancy Challenger](https://skillsmp.com) — 4-part output structure
- [anti-sycophant-ai-agent-skills](https://github.com/machinesoul11/anti-sycophant-ai-agent-skills) — off-switch calibration
- [counter](https://github.com/paia-m/counter) — strip loaded framing, Big Five calibration
- [claude-stop-hallucination](https://github.com/howardng97/claude-stop-hallucination) — /reality-check
- [Karpathy's CLAUDE.md](https://github.com/multica-ai/andrej-karpathy-skills) — negative instructions
- 4-sentence disagreement pattern (mrclaw207, Archit Mittal)

## License

MIT
