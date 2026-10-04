# Pluggable evaluation and fallback strategies

JASIPA agents call a `StrategyChain` so provider failures and missing model responses do not force each agent to maintain a separate fallback implementation. The chain stops at the first strategy that returns `success: true`, records each attempt, and carries strategy name, fallback depth, elapsed time, and a stable error code into monitoring. Candidate routing remains deterministic and the final hiring decision remains with an HR reviewer.

## Strategies

| Strategy | Intended use | Behavior | Typical latency and cost |
| --- | --- | --- | --- |
| `llm` | Resume, assessment, and behavioral evaluation | Calls `LLMService`; provider, timeout, or invalid response becomes a failed attempt | Network/provider dependent; paid model usage |
| `regex` | Resume screening | Matches stated skills and extracts explicitly stated experience years | Usually milliseconds; no model cost |
| `heuristic` | Technical assessments | MCQ answer key, coding rubric point allocation, and short-answer keyword rubric | Usually milliseconds; no model cost |
| `star` | Behavioral answers | Detects evidence for Situation, Task, Action, Result and scores response structure | Usually milliseconds; no model cost |
| `template` | Panel summary | Writes a factual summary from already-calculated scores and evidence | Usually milliseconds; no model cost |
| `human_expert` | Last resort | Creates a pending HR expert task; it does not create a score or hiring decision | Queue latency; no model cost |

Success rates depend on provider configuration and input quality; JASIPA does not assume a universal rate. `/api/admin/strategy-effectiveness` reports observed attempts and fallback frequency for the last 30 days. It raises an alert when the invocation fallback rate exceeds `FALLBACK_ALERT_THRESHOLD`.

## Configuration

Set `FALLBACK_STRATEGY_CHAIN` to a JSON array such as `["llm","regex","heuristic","star","human_expert"]`. Agents use only compatible strategies from the list and append their supported defaults. `FALLBACK_TIMEOUT_SECONDS` sets the provider request timeout (default 30 seconds). `FALLBACK_ALERT_THRESHOLD` is a percentage (default 20). `ENABLE_HUMAN_EXPERT_FALLBACK` controls whether a task can be queued.

## Add a strategy

Subclass `EvaluationStrategy`, implement `evaluate(**kwargs) -> Dict[str, Any]`, and return a `success` boolean, a `data` object on success, and a stable `error` code on failure. Add it to an agent's strategy map and its default order, define the input contract, and add independent plus chain-order tests. Keep outputs evidence-based and do not let explanatory strategies change the deterministic routing result.

## Monitoring and limits

Attempts are stored in `strategy_metrics`, including agent, candidate when available, strategy, fallback level, outcome, error, latency, and time. Strategy rows may contain candidate identifiers and therefore require HR-only access. Per-attempt timeout enforcement currently relies on the LLM client's request timeout; deterministic strategies are synchronous and expected to remain bounded. Human-expert tasks are visible at `/api/admin/expert-tasks`.
