# Evaluation strategies and fallbacks

Agents run a `StrategyChain`: the first strategy that succeeds produces the result, and every attempt (strategy, fallback depth, latency, error code) is stored in `strategy_metrics` and summarised on the Settings page. When no LLM provider is configured the LLM strategy is skipped entirely instead of being recorded as a failure.

| Agent | Strategies | Notes |
| --- | --- | --- |
| Resume-Screener | `llm` → `regex` | `regex` scores matched required/preferred skills, stated experience and education/projects with the rubric's anchored resume weights. |
| Skill-Assessor | objective + (`llm` → `heuristic` → `human_expert`) | MCQs use the answer key and coding questions run in the sandbox; these can never be overridden. Only open-ended answers use the chain. Categories are combined with the rubric's MCQ/coding/written weights. |
| Culture-Fit | `llm` → `star` → `human_expert` | STAR structure scoring weighted by the rubric's competency points. |
| Panel Coordinator | `llm` → `template` for the summary only | Scores and routing are computed in code; the summary writer cannot change them. |
| QuestionGenerationAgent | `llm` → `template` | LLM questions are schema-validated and coding challenges are kept only if their reference solution passes their own tests. |

`human_expert` creates a task in the expert review queue (Settings page) and produces no score. Candidate answers are wrapped as untrusted input and filtered for prompt-injection phrases before reaching an LLM.

Configuration: `FALLBACK_STRATEGY_CHAIN`, `FALLBACK_TIMEOUT_SECONDS`, `FALLBACK_ALERT_THRESHOLD` (percent), `ENABLE_HUMAN_EXPERT_FALLBACK`.
