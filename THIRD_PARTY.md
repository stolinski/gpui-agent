# Third-party attribution

The toolkit's original code is [MIT-licensed](LICENSE). That license does not relicense its dependencies.

- **GPUI / gpui-pre 0.3.7** — [Zed Industries](https://github.com/zed-industries/zed), Apache-2.0 as declared by the matched crate. `prepare-native-tree.py` verifies the cached crate's SHA-256 and copies it into a local ignored vendor directory before adding the automation API. The copied dependency retains its original license/notices. This repository distributes only our additive patch code and preparation script, not the GPUI source archive or a compiled binary.
- **Jev Ultrafast** — [Browser Use × TypeSafe](https://github.com/browser-use/jev-ultrafast), MIT. Architectural inspiration for indexed action choices and a small decision model inside a code-owned loop. No upstream browser implementation is vendored here.
- **TypeSafe SDK, pi, and other Cargo/JavaScript dependencies** — fetched by their respective package managers; consult each package's license before redistributing a bundled application. The TypeSafe API is an external service with its own terms and usage charges.

Any future binary/package distribution must include the notices required by all dependencies it actually bundles. Publishing this source repository is not approval of a downstream app's licenses or distribution terms.
