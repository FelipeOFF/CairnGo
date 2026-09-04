#!/usr/bin/env bats
load 'helpers'

@test "Codex marketplace packages discoverable skills and runnable resources outside the checkout" {
  python3 - "$CAIRN_REPO_ROOT" "$BATS_TEST_TMPDIR" <<'PY'
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

repo, tmp = (Path(arg).resolve() for arg in sys.argv[1:])
ignored = subprocess.run(
    ['git', 'check-ignore', '--no-index', '-q', '.agents/plugins/marketplace.json'],
    cwd=repo,
)
assert ignored.returncode == 1, 'Codex marketplace must be versionable'
marketplace = json.loads((repo / '.agents/plugins/marketplace.json').read_text())
entry, = marketplace['plugins']
assert marketplace['name'] == 'cairngo'
assert entry['source']['source'] == 'local'
assert entry['policy']['installation'] == 'AVAILABLE'
source = (repo / entry['source']['path']).resolve()
package = tmp / 'installed plugin' / entry['name']
shutil.copytree(source, package)

manifest = json.loads((package / '.codex-plugin/plugin.json').read_text())
claude = json.loads((package / '.claude-plugin/plugin.json').read_text())
assert manifest['name'] == entry['name'] == claude['name']
assert manifest['version'].split('+')[0] == claude['version']
skills = sorted((package / manifest['skills']).glob('*/SKILL.md'))
commands = {p.stem.removeprefix('cairn-'): p
            for p in (package / 'commands').glob('cairn-*.md')}
assert {p.parent.name for p in skills} == {'cairn', 'cairn-sync', *commands}, \
    'Every Cairn command must have a native Codex skill'
for skill in skills:
    name = re.search(r'^name: ([a-z0-9-]+)$', skill.read_text(), re.MULTILINE)
    assert name and name[1] == skill.parent.name, skill
    if skill.parent.name in commands:
        targets = {(skill.parent / target).resolve()
                   for target in re.findall(r'\]\(([^)]+)\)', skill.read_text())}
        assert commands[skill.parent.name].resolve() in targets, skill
        assert package / 'references/codex.md' in targets, skill
for document in [*skills, package / 'references/codex.md']:
    for target in re.findall(r'\]\(([^)]+)\)', document.read_text()):
        resource = (document.parent / target).resolve()
        assert resource.is_relative_to(package), (document, target)
        assert resource.is_file(), (document, target)

env = dict(os.environ, CAIRN_PLUGIN_ROOT='', GROK_PLUGIN_ROOT='', CLAUDE_PLUGIN_ROOT='')
for skill in skills:
    root = skill.resolve().parents[2]
    assert (root / 'templates/issue-tracker-beads.md').is_file()
    result = subprocess.run(
        ['bash', str(root / 'scripts/cairn-root.sh')], cwd=tmp,
        env=env, text=True, capture_output=True, check=True,
    )
    assert Path(result.stdout.strip()).resolve() == package.resolve(), result
PY
}
