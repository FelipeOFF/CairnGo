#!/usr/bin/env bats
load 'helpers'

@test "hooks adapt runtime context, preserve Stop hygiene and dispatch jobs in the payload project" {
  python3 - "$CAIRN_REPO_ROOT" "$BATS_TEST_TMPDIR" <<'PYTEST'
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

repo, tmp = (Path(arg).resolve() for arg in sys.argv[1:])
hooks = repo / 'cairn/hooks'
project = tmp / 'project with spaces'
other = tmp / 'other worktree'
for directory in (project, other):
    (directory / '.beads').mkdir(parents=True)
bin_dir = tmp / 'bin'
bin_dir.mkdir()
log = tmp / 'calls.jsonl'
stub = bin_dir / 'bd'
stub.write_text(f'#!{sys.executable}\n' + r"""
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['HOOK_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps({'args': args, 'cwd': os.getcwd()}) + '\n')
if args[:1] == ['lease']:
    assert args == ['lease', 'release', '--mine', '--project-dir', os.environ['HOOK_TEST_PROJECT'], '--json']
    print(os.environ['HOOK_TEST_LEASES'])
elif args[:1] in (['sync'], ['map']):
    pass
else:
    assert 'list' in args, 'Stop must never mutate issues'
    if args[:1] == ['-C']:
        assert args[1] == os.environ['HOOK_TEST_PROJECT']
    else:
        assert os.getcwd() == os.environ['HOOK_TEST_PROJECT']
    print(os.environ['HOOK_TEST_ISSUES'])
""")
stub.chmod(0o755)
for name in ('lease', 'sync', 'map'):
    (bin_dir / name).write_text(f'#!/usr/bin/env bash\nexec {shlex.quote(str(stub))} {name} "$@"\n')
(bin_dir / 'gh').write_text('#!/usr/bin/env bash\nexit 1\n')
(bin_dir / 'gh').chmod(0o755)
env = {k: v for k, v in os.environ.items()
       if not k.startswith(('CAIRN_', 'CLAUDE', 'CODEX_', 'GROK_', 'PLUGIN_'))}
env.update(PATH=f'{bin_dir}{os.pathsep}{env["PATH"]}', BEADS_ACTOR='hook test actor',
           CAIRN_LEASE=str(bin_dir / 'lease'), CAIRN_GBSYNC=str(bin_dir / 'sync'),
           CAIRN_MAP=str(bin_dir / 'map'), CAIRN_GH=str(bin_dir / 'gh'),
           HOOK_TEST_PROJECT=str(project), HOOK_TEST_LOG=str(log),
           HOOK_TEST_ISSUES='[]', HOOK_TEST_LEASES='{"phases":[]}')

def invoke(script, payload, extra=None):
    result = subprocess.run(['bash', str(hooks / script)], cwd=other,
                            input=json.dumps(payload), env={**env, **(extra or {})},
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result
    assert result.stderr == '', result
    return result.stdout

def calls():
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

def context(payload, extra=None):
    result = subprocess.run([sys.executable, str(repo / 'cairn/scripts/cairn-hook-context.py')],
                            input=json.dumps(payload), cwd=other, env={**env, **(extra or {})},
                            text=True, capture_output=True, check=True)
    return dict(token.split('=', 1) for token in shlex.split(result.stdout))

# The entire Stop matrix runs from a different worktree, with a conflicting
# Claude compatibility variable. Quotes/newlines must survive JSON encoding.
issue_id = 'task-"quoted"\\path\nline'
phase = 'phase-"quoted"\\path\nline'
for agent, payload, signals in (
    ('codex', {'turn_id': 'test-turn'}, {'PLUGIN_ROOT': '/installed/cairn'}),
    ('claude', {}, {'CLAUDECODE': '1'}),
    ('grok', {'hookEventName': 'stop'}, {'GROK_HOOK_EVENT': 'stop'}),
    ('unknown', {}, {}),
):
    for issues_on, leases_on in ((False, False), (True, False), (False, True), (True, True)):
        log.unlink(missing_ok=True)
        issues = [{'id': 'lease-hidden', 'labels': ['lease']}]
        if issues_on:
            issues.append({'id': issue_id, 'labels': []})
        output = invoke('session-stop.sh', {'cwd': str(project), 'hook_event_name': 'Stop', **payload}, {
            **signals, 'CLAUDE_PROJECT_DIR': str(other),
            'HOOK_TEST_ISSUES': json.dumps(issues),
            'HOOK_TEST_LEASES': json.dumps({'phases': [phase] if leases_on else []}),
        })
        if not (issues_on or leases_on):
            assert output == '', (agent, output)
        else:
            parsed = json.loads(output)  # rejects extra JSON documents / loose text
            assert set(parsed) == {'systemMessage'}, (agent, parsed)
            message = parsed['systemMessage']
            assert (issue_id in message) == issues_on, (agent, message)
            assert (phase in message) == leases_on, (agent, message)
            assert 'lease-hidden' not in message
        seen = calls()
        assert len(seen) == 2, (agent, seen)
        assert seen[0]['args'] == ['-C', str(project), 'list', '--status', 'in_progress',
                                    '--assignee', 'hook test actor', '--limit', '0', '--json'], seen
        assert seen[1]['args'] == ['lease', 'release', '--mine', '--project-dir', str(project), '--json'], seen

for issues, leases in (('invalid', 'invalid'), ('null', '[]'), ('[null,3]', '{}')):
    assert invoke('session-stop.sh', {'cwd': str(project)}, {
        'HOOK_TEST_ISSUES': issues, 'HOOK_TEST_LEASES': leases}) == ''

# A tool may execute in src/: all hooks must find the current worktree root.
subdir = project / 'src/deep'
subdir.mkdir(parents=True)
log.unlink(missing_ok=True)
output = invoke('session-stop.sh', {'cwd': str(subdir), 'turn_id': 'test'}, {
    'CLAUDE_PROJECT_DIR': str(other), 'HOOK_TEST_ISSUES': '[{"id":"task-subdir"}]'})
assert 'task-subdir' in output, output
assert calls()[0]['args'][1] == str(project), calls()
assert calls()[1]['args'][4] == str(project), calls()
invoke('session-start.sh', {'cwd': str(subdir)}, {'PLUGIN_ROOT': '/installed/cairn'})
assert (project / '.cairn/plugin-root').exists()
assert not (subdir / '.cairn').exists()
(project / '.cairn/sync.json').write_text('{"backends":[{"enabled":true}]}')
log.unlink(missing_ok=True)
invoke('post-bd-write.sh', {'cwd': str(subdir), 'turn_id': 'test', 'tool_name': 'Bash',
                          'tool_input': {'command': 'bd update task-subdir --claim'}})
deadline = time.monotonic() + 3
while not calls() and time.monotonic() < deadline:
    time.sleep(0.02)
assert calls() == [{'args': ['sync', 'update', 'task-subdir', '--dir', str(project)],
                   'cwd': str(project)}], calls()

# A nearer .git file (linked worktree) or directory is a hard boundary even
# without .beads: never walk into an enclosing project's tracker or sync.
for marker_type in ('file', 'directory'):
    nested = project / ('nested-' + marker_type)
    nested_subdir = nested / 'src'
    nested_subdir.mkdir(parents=True)
    if marker_type == 'file':
        (nested / '.git').write_text('gitdir: /fixture/linked-worktree')
    else:
        (nested / '.git').mkdir()
    (project / '.cairn/stop').touch()
    log.unlink(missing_ok=True)
    assert context({'cwd': str(nested_subdir)})['PROJECT_DIR'] == str(nested)
    assert invoke('session-stop.sh', {'cwd': str(nested_subdir)}, {
        'CLAUDE_PROJECT_DIR': str(project)}) == ''
    assert invoke('post-bd-write.sh', {'cwd': str(nested_subdir), 'tool_name': 'Bash',
                  'tool_input': {'command': 'bd update task-parent --claim'}}) == ''
    invoke('session-start.sh', {'cwd': str(nested_subdir)}, {'PLUGIN_ROOT': '/installed/cairn'})
    assert calls() == [], calls()
    assert (nested / '.cairn/plugin-root').exists()
    assert not (nested_subdir / '.cairn').exists()
    assert (project / '.cairn/stop').exists()

# Payload signatures outrank inherited env; generic CLAUDE_PLUGIN_ROOT is no
# proof of Claude. Shell quoting must make payload values data, never code.
for payload, signals, expected in (
    ({'hookEventName': 'stop', 'turn_id': 't'}, {'PLUGIN_ROOT': '/codex'}, 'grok'),
    ({'turn_id': 't'}, {'GROK_HOOK_EVENT': 'stop', 'CLAUDECODE': '1'}, 'codex'),
    ({}, {'GROK_HOOK_EVENT': 'stop', 'PLUGIN_ROOT': '/codex', 'CLAUDECODE': '1'}, 'grok'),
    ({}, {'PLUGIN_ROOT': '/codex', 'CLAUDECODE': '1'}, 'codex'),
    ({}, {'CLAUDECODE': '1'}, 'claude'),
    ({}, {'CLAUDE_PLUGIN_ROOT': '/shared'}, 'unknown'),
):
    found = context({'cwd': str(project), **payload}, signals)
    assert found['CAIRN_HOOK_AGENT'] == expected, found
    assert found['PROJECT_DIR'] == str(project), found
for payload in (None, [], 'bad', {'cwd': []}, {'toolInput': ['bad']}):
    found = context(payload)
    assert found['PROJECT_DIR'] == str(other), found
unsafe = str(tmp / "quote'$(touch injected)`touch injected`\nspace")
assert context({'cwd': unsafe})['PROJECT_DIR'] == unsafe
assert invoke('session-stop.sh', {'cwd': unsafe}) == ''
assert not (other / 'injected').exists()

# Actor fallback stays BEADS_ACTOR > git user.name > USER.
subprocess.run(['git', 'init', '-q', str(project)], check=True)
subprocess.run(['git', '-C', str(project), 'config', 'user.name', 'fixture git actor'], check=True)
for actor_env, expected_actor in (({'BEADS_ACTOR': '', 'USER': 'fallback user'}, 'fixture git actor'),
                                  ({'BEADS_ACTOR': 'explicit actor'}, 'explicit actor')):
    log.unlink(missing_ok=True)
    invoke('session-stop.sh', {'cwd': str(project)}, actor_env)
    argv = calls()[0]['args']
    assert argv[argv.index('--assignee') + 1] == expected_actor, argv
subprocess.run(['git', '-C', str(project), 'config', '--unset', 'user.name'], check=True)
log.unlink(missing_ok=True)
invoke('session-stop.sh', {'cwd': str(project)}, {'BEADS_ACTOR': '', 'USER': 'fallback user'})
argv = calls()[0]['args']
assert argv[argv.index('--assignee') + 1] == 'fallback user', argv

# Actual SessionStart uses the resolved project and native data directory.
# A harmless bd stub prevents installation; AGENTS/GROK docs suppress basics.
for agent, payload, signals, instruction in (
    ('codex', {}, {'PLUGIN_ROOT': '/installed/cairn'}, 'AGENTS.md'),
    ('claude', {}, {'CLAUDECODE': '1'}, 'CLAUDE.md'),
    ('grok', {'hookEventName': 'session_start'}, {'GROK_HOOK_EVENT': 'session_start'}, 'GROK.md'),
):
    (project / instruction).write_text('<!-- BEGIN BEADS INTEGRATION -->\n')
    (project / '.cairn').mkdir(exist_ok=True)
    (project / '.cairn/stop').touch()
    output = invoke('session-start.sh', {'cwd': str(project), **payload}, signals)
    structured = json.loads(output)
    if agent == 'grok':
        # Grok's Observe gate extracts systemMessage, not additionalContext.
        assert set(structured) == {'systemMessage'}, structured
        assert 'bd basics' in structured['systemMessage'], (agent, output)
    else:
        specific = structured['hookSpecificOutput']
        assert specific['hookEventName'] == 'SessionStart', structured
        assert 'bd basics' in specific['additionalContext'], (agent, output)
    assert not (project / '.cairn/stop').exists()
    assert Path((project / '.cairn/plugin-root').read_text().strip()) == hooks.parent
    assert not (other / '.cairn').exists()
    (project / instruction).unlink()
for signals, expected_dir in (
    ({'GROK_HOOK_EVENT': 'stop', 'GROK_WORKSPACE_ROOT': str(project), 'CLAUDE_PROJECT_DIR': str(other)}, project),
    ({'CLAUDECODE': '1', 'CLAUDE_PROJECT_DIR': str(project)}, project),
    ({'PLUGIN_ROOT': '/installed/cairn', 'CLAUDE_PROJECT_DIR': str(project)}, other),
):
    assert context({}, signals)['PROJECT_DIR'] == str(expected_dir)
assert context({}, {'PLUGIN_ROOT': '/plugin', 'PLUGIN_DATA': '/codex/data',
                    'CLAUDE_PLUGIN_DATA': '/wrong'})['DATA_DIR'] == '/codex/data'
assert context({}, {'GROK_HOOK_EVENT': 'stop', 'GROK_PLUGIN_DATA': '/grok/data',
                    'CLAUDE_PLUGIN_DATA': '/wrong'})['DATA_DIR'] == '/grok/data'

# No real gbsync/gh/bd mutation: background jobs log their project and argv.
(project / '.cairn/sync.json').write_text('{"backends":[{"enabled":true}]}')
(project / '.cairn/id-map.json').write_text('{"mapped-1":{}}')
for payload in (
    {'turn_id': 'test', 'tool_name': 'Bash', 'tool_input': {'command': 'bd update task-1 --claim'}},
    {'tool_name': 'Bash', 'tool_input': {'command': 'bd update task-1 --claim'}},
    {'hookEventName': 'post_tool_use', 'toolName': 'run_terminal_command',
     'toolInput': {'command': 'bd update task-1 --claim'},
     'tool_name': 'IgnoredAlias', 'tool_input': {'command': 'bd close wrong-1'}},
):
    log.unlink(missing_ok=True)
    output = invoke('post-bd-write.sh', {'cwd': str(project), **payload}, {'CLAUDE_PROJECT_DIR': str(other)})
    assert json.loads(output)['systemMessage'].endswith('mirror push queued'), output
    deadline = time.monotonic() + 3
    while not calls() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert calls() == [{'args': ['sync', 'update', 'task-1', '--dir', str(project)], 'cwd': str(project)}], calls()
log.unlink(missing_ok=True)
invoke('post-bd-write.sh', {'cwd': str(project), 'turn_id': 'test', 'tool_name': 'Bash',
       'tool_input': {'command': 'bd create --title new'}}, {
    'CLAUDE_PROJECT_DIR': str(other), 'HOOK_TEST_ISSUES': '[{"id":"mapped-1"},{"id":"new-1"}]'})
deadline = time.monotonic() + 3
while len(calls()) < 2 and time.monotonic() < deadline:
    time.sleep(0.02)
assert calls()[-1] == {'args': ['sync', 'create', 'new-1', '--dir', str(project)], 'cwd': str(project)}, calls()
for payload in ([], {'tool_name': 'Read', 'tool_input': {'command': 'bd update task-1'}},
                {'hookEventName': 'post_tool_use', 'toolName': 'run_terminal_command', 'toolInput': []},
                {'tool_name': 'Bash', 'tool_input': {'command': 5}}):
    assert invoke('post-bd-write.sh', payload) == ''

# The shared manifest must reach native Grok shell events as well as Bash.
manifest = json.loads((hooks / 'hooks.json').read_text())
import re
matcher = manifest['hooks']['PostToolUse'][0]['matcher']
for tool in ('Bash', 'run_terminal_command'):
    assert re.fullmatch(matcher, tool), matcher
PYTEST
}
