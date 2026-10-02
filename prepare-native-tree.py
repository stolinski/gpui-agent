#!/usr/bin/env python3
"""Prepare a pinned GPUI dependency with the shared local accessibility bridge API.
Independent of File-Bro. Never edits Cargo's registry or launches an application.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"Upstream patch anchor mismatch: {path.name}")
    path.write_text(text.replace(old, new))


def prepare(output, upstream):
    # Use only the exact cached archive pinned by Cargo.lock, never mutate registry sources.
    import json
    expected_package = json.loads((HERE / 'patches/upstream.json').read_text())
    archive = upstream.parents[2] / 'cache' / upstream.parent.name / (upstream.name + '.crate')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_package['checksum']:
        raise ValueError('Wrong GPUI registry package')
    output.mkdir(parents=True, exist_ok=False)
    vendor = output
    with tarfile.open(archive) as package:
        for member in package.getmembers():
            relative = Path(member.name).relative_to(upstream.name)
            if '..' in relative.parts or member.issym() or member.islnk():
                raise ValueError('Unsafe archive member')
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError('Nonregular archive member')
            target = vendor / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(package.extractfile(member).read())
    # This API is additive; local tree generation remains explicitly disabled until the
    # opted-in bridge enables it. Normal application/OS accessibility behavior is unchanged.
    window = vendor / 'src/window.rs'
    replace(window, 'pub(crate) mod a11y;',
            'pub(crate) mod a11y;\n#[cfg(not(target_family = "wasm"))]\nmod automation;')
    replace(window,
            '    pub(crate) fn handle_a11y_action(&mut self, request: accesskit::ActionRequest, cx: &mut App) {\n',
            '    pub(crate) fn handle_a11y_action(&mut self, request: accesskit::ActionRequest, cx: &mut App) {\n'
            '        self.handle_a11y_action_at(request, None, cx);\n    }\n\n'
            '    #[cfg(not(target_family = "wasm"))]\n'
            '    fn handle_a11y_action_at(&mut self, request: accesskit::ActionRequest, position: Option<Point<Pixels>>, cx: &mut App) {\n')
    replace(window,
            'if let Some(bounds) = self.a11y.node_bounds.get(&request.target_node).copied() {\n'
            '                    let center = bounds.center();',
            'if let Some(bounds) = self.a11y.node_bounds.get(&request.target_node).copied() {\n'
            '                    let center = position.unwrap_or_else(|| bounds.center());')
    replace(vendor / 'src/window.rs',
            'if should_send_a11y_update {',
            'if should_send_a11y_update && self.a11y.platform_is_active() {')
    shutil.copy2(HERE / 'patches/automation.rs', vendor / 'src/window/automation.rs')
    a11y = vendor / 'src/window/a11y.rs'
    replace(a11y, '\n    force_disabled: bool,\n',
            '\n    force_disabled: bool,\n    automation_enabled: bool,\n'
            '    pub(crate) automation_bounds: FxHashMap<NodeId, Bounds<Pixels>>,\n')
    replace(a11y, '            force_disabled,\n',
            '            force_disabled,\n            automation_enabled: false,\n'
            '            automation_bounds: FxHashMap::default(),\n')
    replace(a11y,
            'self.active_this_frame = self.is_enabled() && self.active_flag.load(Ordering::SeqCst);',
            'self.active_this_frame = self.is_enabled()\n'
            '            && (self.automation_enabled || self.active_flag.load(Ordering::SeqCst));')
    replace(a11y, '        self.node_bounds.clear();',
            '        self.node_bounds.clear();\n        self.automation_bounds.clear();')
    replace(a11y, '    pub(crate) fn debug_tree_json(&self) -> Option<String> {',
            '''    pub(crate) fn platform_is_active(&self) -> bool {
        !self.force_disabled && self.active_flag.load(Ordering::SeqCst)
    }

    pub(crate) fn enable_local_automation(&mut self) -> bool {
        if self.force_disabled { return false; }
        self.automation_enabled = true;
        true
    }

    pub(crate) fn local_automation_tree(&self) -> Option<&TreeUpdate> {
        self.automation_enabled.then(|| self.debug.tree_update()).flatten()
    }

    pub(crate) fn debug_tree_json(&self) -> Option<String> {''')
    replace(vendor / 'src/window/a11y/debug.rs', 'impl A11yDebug {',
            '''impl A11yDebug {
    pub(crate) fn tree_update(&self) -> Option<&TreeUpdate> {
        self.last_tree_update.as_ref()
    }
''')
    replace(vendor / 'src/element.rs',
            '                            window.a11y.node_bounds.insert(node_id, bounds);',
            '''                            window.a11y.node_bounds.insert(node_id, bounds);
                            let clipped = bounds.intersect(&window.content_mask().bounds);
                            window.a11y.automation_bounds.insert(node_id, clipped);''')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New, nonexistent patched dependency directory')
    parser.add_argument('--upstream', type=Path, required=True,
                        help='Unmodified cached gpui-pre source (the version in patches/upstream.json); never edited')
    args = parser.parse_args()
    print(prepare(args.output.resolve(), args.upstream.resolve()))
