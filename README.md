# gpui-agent

**Let Jev drive a native GPUI app, without putting your coding model in the per-click loop.**

Give it a goal. The runner observes GPUI's accessibility tree, asks [TypeSafe's Jev](https://docs.typesafe.ai/) to choose a typed action, and dispatches real native input. It keeps going within fixed limits, then returns a compact report.

```ts
// In pi, after the setup below:
gpui_task({
  app: "counter",
  goal: "Click Increment until the count is exactly two.",
  check: "count-two"
})
```

No screenshots sent to the model. No browser, CDP, global mouse/keyboard driver, or second text-generation model. Your main coding model delegates the entire workflow once.

> **Experimental developer toolkit, macOS-first.** This works with apps you own and explicitly instrument—not arbitrary installed GPUI apps. It currently requires **gpui-pre 0.3.7, the included additive framework patch, and one startup hook**. Use disposable fixtures, not personal data. GitHub source is available under MIT; there are no npm, PyPI, or crates.io releases.

## How it works

```text
Your goal → runner → GPUI accessibility snapshot → Jev Choice
               ↑                                     ↓
        check / next observation ← validated native input
```

The app supplies the UI and optional independent assertions. Jev selects only from observed, supported actions. The runner handles freshness checks, limits, cancellation, reporting, and shutting down its own test process.

**Completion is not proof.** Without a named assertion, Jev saying “done” produces `completed_unverified`, not a test pass. Only `passed: true` means the requested application-owned check passed. Neither result certifies pixels, visual design, or accessibility quality.

## What you need

| Requirement | Used for |
| --- | --- |
| macOS with a graphical desktop and Apple command-line developer tools | Building/running the native Counter demo; Linux/Windows native runtime is unverified |
| [Rust/rustup](https://rustup.rs/) | The checkout pins Rust **1.98.1**; first use may download it |
| Python **3.10+** | Preparing the GPUI patch; optionally the dependency-free standalone runner |
| [TypeSafe API key](https://console.typesafe.ai/keys) | Live Jev decisions only; **not** offline tests or scripted smoke checks |
| Node **22.18+** and pnpm **11.1.3** | The TypeScript runner/pi integration only |
| [pi](https://pi.dev/) | Optional coding-agent integration; tested against **0.85.1**, not a promise of compatibility with every release |

If Apple developer tools are absent, install them with `xcode-select --install`. The Counter uses runtime Metal shaders; a separate Metal toolchain download is not required. Dependency fetching needs network access and the first GPUI build can take several minutes.

## Quickstart: build Counter

Run these commands in a new checkout. They do not read a catalog or launch an app:

```sh
git clone https://github.com/stolinski/gpui-agent.git
cd gpui-agent

# Populate Cargo's registry with the pinned GPUI source/archive.
cargo fetch

# Copy and patch the SHA-256-verified archive into a NEW directory.
# Cargo's registry files are never modified.
python3 prepare-native-tree.py vendor/gpui-pre --upstream \
  "$(find "${CARGO_HOME:-$HOME/.cargo}/registry/src" -mindepth 2 -maxdepth 2 \
      -type d -name gpui-pre-0.3.7)"

cargo --config 'patch.crates-io.gpui-pre.path="vendor/gpui-pre"' \
  build --features demo --example counter --release
```

If `find` returns multiple paths, choose the one for your crates.io registry and pass that single path to `--upstream`. The preparation command deliberately refuses to overwrite an existing `vendor/gpui-pre`; do not repeat it for ordinary rebuilds. Reuse the same `cargo --config …` build command. A plain `cargo build --features demo` uses unpatched GPUI and will fail.

The executable is `target/release/examples/counter` (unless you override Cargo's target directory). It is a test-only app: each runner invocation opens a new Counter, starts at zero, and closes that owned process afterward.

### First run: no key, no model calls

```sh
python3 run.py \
  --task examples/counter.json \
  --script examples/counter-script.json \
  -- ./target/release/examples/counter --agent '{session}'
```

This explicitly opens the native Counter and clicks Increment twice using a script. Look for `"passed": true` in the JSON report. It proves the native input/check path, **not** Jev performance. GUI smoke checks are separate from the automatic test suite.

### Live run: let Jev choose

Create a local `.env` from the template and set your TypeSafe key:

```sh
cp .env.example .env
# Edit .env locally: TYPESAFE_API_KEY=your-key
```

Then explicitly allow this generated UI state to be sent to TypeSafe:

```sh
python3 run.py \
  --task examples/counter.json \
  --env-file .env --allow-cloud \
  --max-requests 10 --max-seconds 60 \
  --decision-mode actions --keepalive \
  -- ./target/release/examples/counter --agent '{session}'
```

**Live runs incur API usage.** An exported `TYPESAFE_API_KEY` takes precedence over the file. The key is read by the external runner, never passed to the native child. `.env` is Git-ignored; never commit keys or private run traces. Configure credentials locally rather than placing them in goals.

The Python CLI requires a JSON task with `goal`, `check`, and optional `text_values`; see [examples/counter.json](examples/counter.json). It exits `0` only when the check passes, `1` for an unsuccessful run, and `2` for setup/transport errors. `--help` lists limits and options. The pi runner below supports free-form goals and optional checks instead.

## Use from pi

After building Counter, install the TypeScript dependencies and copy the launch-profile example:

```sh
pnpm --dir typescript install --frozen-lockfile --ignore-scripts
cp examples/gpui-agent.json .gpui-agent.json

# Try it in this checkout without changing global pi settings:
pi -e ./typescript/src/extension.ts
```

Review and trust this project in pi before invoking the tool. The example configuration points to Counter and the local `.env`; it contains **launch settings, not a catalog of allowed goals**.

Ask pi to use `gpui_task` to increment Counter twice and check `count-two`. The tool call is:

```ts
gpui_task({ app: "counter", goal: "Increment twice", check: "count-two" })
```

Or give a goal without a custom test assertion:

```ts
gpui_task({ app: "counter", goal: "Increment three times" })
// A reported completion is completed_unverified, passed: false.
```

`gpui_task({})` lists configured apps without launching anything or reading credentials. Each invocation owns the whole observe/decide/input loop. There is no per-click conversation with the coding assistant.

For ongoing use in another project, install the **local TypeScript subdirectory** as a project package:

```sh
cd /path/to/your/project
pi install -l /absolute/path/to/gpui-agent/typescript
```

Create `.gpui-agent.json` in that project's root with its own reviewed fixture launch command; relative executable paths resolve there, not in the toolkit checkout. Restart pi or use `/reload`. Keep the toolkit checkout in place. The repository root is a Rust/Python toolkit, **not a root-level pi package**; cloning and using `typescript/` is the supported installation path.

Full configuration, text entry, statuses, library usage, and limits: **[TypeScript/pi guide](typescript/README.md)**. Pi-managed `/login typesafe` is not implemented; use the environment or explicit `envFile`.

## Add your own GPUI app

1. Use the matched `gpui-pre = "=0.3.7"` stack. Prepare its patched dependency as above, and put the patch in **your workspace root**:

   ```toml
   [patch.crates-io]
   gpui-pre = { path = "/absolute/path/to/gpui-agent/vendor/gpui-pre" }
   ```

2. Add the toolkit to your app's `Cargo.toml`:

   ```toml
   [dependencies]
   gpui-agent = { path = "/absolute/path/to/gpui-agent", features = ["native-tree"] }
   ```

3. In an explicit test-only startup mode, create a fresh owned window and call `gpui_agent::ui::serve(view, token, window, cx)` once. Use `serve_with_checks(...)` if you want independent assertions. [Counter's complete source](examples/counter.rs) shows token validation, startup, and the `count-two` check.
4. Use normal accessible controls. Custom widgets need ordinary roles and labels, for example `.role(Role::Button).aria_label("Increment")`. There is no per-control automation registry or custom `Host` implementation.
5. Add a trusted app profile to `.gpui-agent.json`, with exactly one complete `"{session}"` argv entry, then supply goals at call time.

GPUI Click/SetValue handlers perform clicks/text replacement. Window-local GPUI events perform double-clicks and scrolling. The bridge reads the real AccessKit tree, excludes hidden/password/disabled targets, and rechecks the observed surface immediately before input. UI semantics must truthfully describe your controls; clipping does not prove full occlusion or correct pixels.

Keep the bridge out of ordinary production startup. Closing a session closes the dedicated process. **Never attach it to an existing interactive window.** A fixture flag or session token is not an OS sandbox; apps with file/network capabilities need their own enforced isolation and explicit authority.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/` | Rust JSON protocol, freshness/replay guards, native tree/input bridge |
| `patches/`, `prepare-native-tree.py` | Pinned, additive GPUI patch and verified preparation |
| `typescript/` | Official TypeSafe SDK loop, pi extension, tests and library API |
| `python/`, `run.py` | Standalone CLI; Python standard library only |
| `examples/` | Counter app, task, script, and pi launch configuration; File-Bro task examples require that separate app |
| `integrations/` | Optional typed Swamp factory; not a registered/published Swamp extension |
| [PROTOCOL.md](PROTOCOL.md) | Versioned newline-delimited JSON interface |

## Test and contribute

These deterministic tests do **not** launch a native app, read personal files, open OS permission prompts, or make model requests:

```sh
cargo test --lib
cargo clippy --lib -- -D warnings
python3 -m unittest discover -s tests -v
pnpm --dir typescript check
pnpm --dir typescript test

# Bridge tests need the prepared patch, but do not launch a window:
cargo --config 'patch.crates-io.gpui-pre.path="vendor/gpui-pre"' \
  test --features native-tree --lib
```

Run `pnpm --dir typescript install --frozen-lockfile --ignore-scripts` first if needed. Optional Swamp factory tests use `deno test --no-config integrations/swamp_test.ts`; actual Swamp installation/runtime is not verified. Native GUI checks must be explicitly requested, on disposable fixtures, separately from CI. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Limits and safety

- **Not a universal desktop agent.** Only the opted-in GPUI process and supported actions are available. No arbitrary keyboard shortcuts, clipboard, file uploads, OS permissions, or existing-window attachment.
- **Not a visual judge.** No screenshot inference; stale presentation remains a known gap. Semantic assertions do not replace visual inspection, VoiceOver, or IME testing.
- **Not a security boundary.** The native app's capabilities determine what a mistaken click can do. Use synthetic data and enforced isolation for anything that can mutate content.
- **Cloud privacy:** live runs send the goal, observed UI labels/values/facts, and bounded action history to TypeSafe. Local artifacts retain UI observations. Do not expose private content or secrets in test fixtures; review traces before sharing.
- **Bounded, not infallible.** Stale input requires a new observation/decision; uncertain acknowledgements are never blindly replayed. Model errors, low confidence, no progress, timeouts, or request limits stop the run. No automatic larger-model fallback or unlimited retry loop.
- **Exact text comes from the caller.** The pi runner accepts `textValues` or quoted literals in the goal; Python uses `text_values`. Jev selects supplied strings, it does not generate arbitrary text.
- **Reports are retained locally.** Inspect the returned artifact directory for `report.json`, bounded `trace.jsonl`, stderr, and (TypeScript) final observation. Retention is not a Git backup. Token counts are measured; no dollar-cost or general accuracy claim is implied.

This grew out of generated-fixture testing in File-Bro. Small native flows have been exercised with live Jev, but that development evidence is not a cross-platform reliability benchmark. This standalone repository deliberately excludes File-Bro app code, private configuration, raw traces, screenshots, and runtime data.

## License and credits

[MIT](LICENSE) for this toolkit. Architecture inspired by Browser Use × TypeSafe's [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast); no browser code is vendored. GPUI and other dependencies retain their own licenses; the downloaded GPUI dependency is not included in this repository. See [THIRD_PARTY.md](THIRD_PARTY.md).
