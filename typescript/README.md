# Free-form GPUI goals for pi

One `gpui_task` invocation owns observe → Jev decisions → native input → completion → cleanup. Native observations stay out of the main coding assistant's context; only a compact result returns. This MIT package lives in [stolinski/gpui-agent](https://github.com/stolinski/gpui-agent). It is not published to npm.

## Setup

First follow the [root README](../README.md) to build the patched GPUI Counter, create `.env`, and copy `examples/gpui-agent.json` to `.gpui-agent.json`. The bridge requires **gpui-pre 0.3.7**, its pinned patch, and one app startup hook; an arbitrary unmodified GPUI binary cannot be driven.

From the repository root:

```sh
pnpm --dir typescript install --frozen-lockfile --ignore-scripts
pi -e ./typescript/src/extension.ts
```

Review/trust the checkout before using launch configuration. This loads the extension for one session without changing global settings. For ongoing use, run `pi install -l /absolute/path/to/gpui-agent/typescript` in the consuming project and restart pi or `/reload`. Install the **subdirectory**, not the repository root. The consuming project needs its own `.gpui-agent.json`.

Node ≥22.18, pnpm 11.1.3; tested against pi 0.85.1. The package exports TypeScript source; installed consumers under `node_modules` need a TS-aware loader (pi supplies one). Other pi versions and runtimes may require compatibility work.

## Call the tool

```ts
gpui_task({ app: "counter", goal: "Increment twice", check: "count-two" })
gpui_task({ app: "counter", goal: "Increment three times" })
gpui_task({}) // Discover apps; no launch, key read, or billing.
```

App IDs/descriptions enter tool metadata at startup. No configured task catalog or custom success callback is required. Exact typing inputs come from each invocation:

- Double-quoted, curly-double-quoted, or backtick phrases in the goal become available typing choices.
- `textValues: ["exact text", ""]` supplies explicit inputs, including clearing a field. It overrides quote extraction, even when empty.
- Unquoted prose is not automatically transformed into text. Jev selects supplied strings; it does not generate arbitrary text or code.

## Launch configuration

Create operator-reviewed `.gpui-agent.json` in the project where pi runs:

```json
{
  "version": 2,
  "fixtureOnly": true,
  "envFile": ".env",
  "apps": {
    "counter": {
      "description": "Fresh Counter fixture; Increment button and count label",
      "application": ["./target/release/examples/counter", "--agent", "{session}"],
      "maxRequests": 20,
      "maxSeconds": 120
    }
  }
}
```

Relative executable paths resolve from this project root. Use an absolute binary path when the build lives elsewhere. Only launch settings belong here; goal, check, and text are supplied per call. Literal argv, exactly one complete `{session}` argument, no shell evaluation or caller-supplied executable/environment/limit overrides. At most 32 app profiles; each call opens a fresh owned fixture and closes it afterward. No implicit build or existing-window fallback.

**`fixtureOnly` and project trust are declarations, not OS containment or authority over personal data.** Review the configured executable/launcher; a generic bridge is not a per-control safety allowlist. Do not use this with ordinary production startup or content-mutating apps without enforced disposable-fixture isolation.

Version-1 configs and optional `gpui_task({ task: "old-preset" })` / `runTask(project, "old-preset")` remain compatible. Do not combine presets with free-form arguments. The separate Python CLI/Swamp adapter still uses task files with required checks.

## Completion versus verification

| Outcome | `completed` | `passed` | Meaning |
| --- | --- | --- | --- |
| `completed_unverified` | true | false | Jev reported completion against a freshly rechecked semantic surface; no independent assertion requested |
| `passed` | true | true | The explicitly requested native assertion passed |
| `verification_failed` | false | false | Jev said done but the requested assertion did not pass |
| blocked, limit, cancellation, timeout, shutdown failure | false | false | Incomplete/failed run; inspect retained evidence |

`check: "count-two"` requests Counter's application-owned assertion. Your app defines its own named checks through `serve_with_checks(...)`; without assertions, use `serve(...)`. A passing check is an authoritative early stop and certifies **that named assertion**, not arbitrary prose beyond it. Unknown/failing checks cannot be bypassed by model DONE. No-check runs send no native Verify requests.

Every result has `visual_verification: "unavailable"`. Native semantics are not proof of presented pixels, visual quality, VoiceOver behavior, or permission to mutate content.

## Credentials, privacy, and limits

- Reads `TYPESAFE_API_KEY` from pi's environment, or the explicit ignored `envFile` (environment wins). Only that key is parsed; no shell evaluation or unrelated secret loading. File reads are bounded regular-file/no-symlink reads.
- Get a key from the [TypeSafe dashboard](https://console.typesafe.ai/keys). Live calls send goal/UI state/history to TypeSafe and incur usage. Pi-managed `/login typesafe` is **not implemented**. There is no allowance command/ledger.
- Native children receive only HOME/PATH/TMPDIR/LANG/LC_ALL/USER/LOGNAME, never runner credentials. SDK logging is off; fixed TypeSafe origin, no redirects or automatic retries; configured HTTP(S) proxies refuse rather than silently bypass.
- App profiles cap runs at 120 requests/120 seconds; the runner allows 80 observation cycles. Goal ≤4,096 characters; up to 32 text values, each ≤1,024 UTF-8 bytes without control characters. Invalid inputs refuse before credentials/launch/billing.
- One Choice covers at most 125 complete actions plus wait/done/blocked. Oversized tables refuse before billing; reduce supplied text or visible action space. Confidence 0.2 is an experimental threshold, not calibrated assurance.
- History retains target labels/roles and execution outcomes across navigation. Stale actions and stale completion judgments require a new observation/decision. Uncertain acknowledgements are never replayed. Three unchanged post-input surfaces stop for no progress.
- Cancellation, deadlines, and shutdown close only owned children/process groups. POSIX/macOS tested; Windows tree cleanup unverified. No cross-goal warm sessions.

Each run retains a private `gpui-task-*` directory: `report.json`, bounded `trace.jsonl`, `native.stderr.log`, and `final-observation.json` when available. Traces contain UI state; review/redact before sharing. They are not automatically cleaned or Git-backed up. Tool output stays compact (<4 KB); discovery stays bounded (<16 KB). Reports count failed/cancelled transport attempts and measured tokens, not invented dollar prices or `$0` pi usage.

## Library usage

```ts
import { loadProject, runTask } from "./src/task.ts";

// Establish project trust before loading executable configuration.
const project = await loadProject(process.cwd());
const report = await runTask(project, {
  app: "counter",
  goal: "Increment twice",
  check: "count-two"
});
if (!report.passed) throw new Error(`Check did not pass: ${report.status}`);
```

`runTask` also accepts `{ signal, progress }` options. No AgentBuilder, replacement main model, Python orchestrator, service, or listening port is required for this TypeScript loop.

## Verification

Run from the repository root:

```sh
pnpm --dir typescript check
pnpm --dir typescript test
```

These tests use fixtures, fake stdio peers, and mocked HTTP; never a native app, real key, model request, personal catalog, or OS permission prompt.

An **explicit** native test after building Counter and copying the example config:

```sh
node typescript/verify-native.ts --fixtures-only \
  '{"app":"counter","goal":"Increment twice","check":"count-two"}' \
  examples/counter-script.json --expect-text 'Count: 2'
```

Replacing the script path with `--live` explicitly uses the real key/SDK/Jev. `--expect-text` is an independent post-run harness assertion on native semantics; it does not influence Jev or upgrade the tool's unverified status. This harness executes the registered tool handler and actual owned process, not the main assistant's tool-selection behavior. Check the report's `passed` field for native-check success; the harness exit code alone also accepts unverified completion.
