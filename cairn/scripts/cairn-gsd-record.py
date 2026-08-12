#!/usr/bin/env python3
"""cairn-gsd-record.py — grava os goldens do diferencial a partir do binário
REAL da tag pinada (D-02, TRIV-04).

Executa o gsd-tools.cjs do clone em cache, cenário a cenário, a partir do
MESMO manifesto tests/fixtures/gsd-goldens/scenarios.json que o bats
diferencial consome — e escreve cada golden com provenance `recorded`. Um
golden gravado carrega os bytes do binário real; o diferencial passa então a
comparar por igualdade literal (bytes/json conforme o `compare` do cenário).

Gates, na ordem, cada um com exit próprio e mensagem nomeada:
    (1) o cache existe e o HEAD bate com o commit esperado — senão exit 6
        (EXIT_BAD_CORPUS; a doutrina de ensure_corpus do cairn-inventory.py,
        forma copiada, módulo nunca importado: corpus não verificado não
        grava golden nenhum). Este script NUNCA clona: popular o cache é
        papel do cairn-inventory.sh.
    (2) `node` no PATH — senão exit 5 (EXIT_NO_HELPER).
    (3) probe do binário: uma invocação barata do gsd-tools.cjs; se falhar
        por runtime não buildado (módulos ./lib ausentes), tenta o build do
        clone (`npm install` + `npm run build:lib`) e re-proba; build falhou
        → exit 5 nomeando o passo.

Execução por cenário: o fixture declarativo do manifesto é montado num
diretório DESCARTÁVEL (identidade git determinística via env GIT_CONFIG_*) e
o binário roda com cwd NO FIXTURE — jamais no repositório de trabalho
(config-set mutaria estado de verdade). O envelope capturado (stdout, exit,
stderr quando o cenário registrar) vira o golden, com `mask` aplicada
(o valor no jq_path é validado contra o regex e substituído pelo marcador).

NUNCA golden parcial: cada golden é escrito em arquivo temp irmão e publicado
por rename atômico; falha no meio de um cenário aborta o processo sem tocar
os goldens já commitados dos cenários restantes. NENHUM timestamp entra no
golden — o teste de reprodução byte a byte exige determinismo.

Usage: cairn-gsd-record.py [--cache-dir <dir>] [--source <url|path>]
                           [--expect-commit <sha>] [--only <scenario-id>]
                           [--scenarios <file>] [--goldens-dir <dir>]
Exit:  0 ok. 2 uso. 5 dependência ausente (node, ou o build do runtime
       falhou). 6 corpus/manifesto inválido (HEAD divergente, cenário
       inexistente, mask que não casa).

--scenarios e --goldens-dir são seams de teste (mesmo espírito dos seams do
cairn-inventory): apontam manifesto e destino alternativos para a suíte
exercitar gates, mask e escrita atômica sem tocar os goldens versionados.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_HELPER = 5
EXIT_BAD_CORPUS = 6

TAG_PREFIX = "[cairn-gsd-record]"

SOURCE_URL = "https://github.com/open-gsd/gsd-core"
TAG = "v1.10.0"
TAG_COMMIT = "68a04ccf8ef74803bdb651e12c3b85b218bbccdf"
CACHE_RELPATH = ".cairn/cache/gsd-core-" + TAG

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_RELPATH = "tests/fixtures/gsd-goldens"

BUILD_NEEDED_MARKERS = (
    "runtime library is not built",
    "Cannot find module",
)

USAGE = ("usage: cairn-gsd-record.py [--cache-dir <dir>] [--source "
         "<url|path>] [--expect-commit <sha>] [--only <scenario-id>] "
         "[--scenarios <file>] [--goldens-dir <dir>]")


def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)


def say(msg):
    print(f"{TAG_PREFIX} {msg}")


def build_parser():
    p = argparse.ArgumentParser(prog="cairn-gsd-record.py", add_help=True,
                                description=USAGE)
    p.add_argument("--cache-dir")
    p.add_argument("--source")
    p.add_argument("--expect-commit")
    p.add_argument("--only")
    p.add_argument("--scenarios")
    p.add_argument("--goldens-dir")
    return p


def run_git(argv):
    """(returncode, stdout, stderr) para um comando git, ou (None, "", err)
    quando o próprio git não existe."""
    try:
        proc = subprocess.run(["git"] + argv, capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "", str(e)
    return proc.returncode, proc.stdout, proc.stderr


def verify_corpus(cache_dir, expected_commit):
    """Gate (1): o cache existe e o HEAD é o commit esperado — a doutrina de
    ensure_corpus do cairn-inventory.py (forma copiada). Este script nunca
    clona; sem cache válido é exit 6 nomeado."""
    if not (cache_dir / ".git").exists():
        die(f"cache do clone ausente em {cache_dir} — rode "
            "cairn-inventory.sh uma vez com rede para populá-lo",
            EXIT_BAD_CORPUS)
    code, out, err = run_git(["-C", str(cache_dir), "rev-parse", "HEAD"])
    if code is None:
        die(f"could not run git rev-parse on the cache: {err}",
            EXIT_NO_HELPER)
    if code != 0:
        die(f"cache at {cache_dir} is not a readable git clone: "
            f"{(err or '').strip()[:200]}", EXIT_BAD_CORPUS)
    head = out.strip()
    if head != expected_commit:
        die(f"cache HEAD {head} does not match the expected tag commit "
            f"{expected_commit} — refusing to record from an unverified "
            f"corpus (delete the cache or refresh it via cairn-inventory.sh)",
            EXIT_BAD_CORPUS)
    return head


def require_node():
    """Gate (2): node no PATH."""
    if shutil.which("node") is None:
        die("node não está no PATH — instale node para gravar goldens do "
            "binário real", EXIT_NO_HELPER)


def find_entrypoint(cache_dir):
    """O gsd-tools.cjs do cache, procurado sob gsd-core/bin (a localização
    da tag) e por rglob como fallback — nunca dentro de .git/node_modules."""
    direct = cache_dir / "gsd-core" / "bin" / "gsd-tools.cjs"
    if direct.is_file():
        return direct
    for hit in sorted(cache_dir.rglob("gsd-tools.cjs")):
        if ".git" not in hit.parts and "node_modules" not in hit.parts:
            return hit
    die(f"gsd-tools.cjs não encontrado sob {cache_dir}", EXIT_BAD_CORPUS)


def probe_ok(entry):
    """O binário responde sem pedir build? Critério: os marcadores de
    runtime-não-buildado ausentes da saída combinada de uma invocação
    barata (o exit code do probe não importa — uso inválido também prova
    que o runtime carregou)."""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                ["node", str(entry), "query", "config-get", "probe.key",
                 "--default", "probe", "--raw"],
                capture_output=True, text=True, cwd=tmp, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return False
    combined = (proc.stdout or "") + (proc.stderr or "")
    return not any(marker in combined for marker in BUILD_NEEDED_MARKERS)


def ensure_runtime_build(cache_dir, entry):
    """Gate (3): probe → build (npm install + npm run build:lib) → re-probe.
    Cada falha morre nomeando o passo, exit 5."""
    if probe_ok(entry):
        return
    say("runtime do clone não buildado — tentando npm install + build:lib")
    for step in (["npm", "install", "--no-audit", "--no-fund"],
                 ["npm", "run", "build:lib"]):
        try:
            proc = subprocess.run(step, capture_output=True, text=True,
                                  cwd=str(cache_dir), timeout=600)
        except (OSError, subprocess.SubprocessError) as e:
            die(f"build do runtime falhou no passo `{' '.join(step)}`: {e}",
                EXIT_NO_HELPER)
        if proc.returncode != 0:
            die(f"build do runtime falhou no passo `{' '.join(step)}` "
                f"(exit {proc.returncode}): "
                f"{(proc.stderr or '').strip()[:300]}", EXIT_NO_HELPER)
    if not probe_ok(entry):
        die("build do runtime terminou mas o probe do gsd-tools.cjs segue "
            "falhando — corpus inutilizável para gravação", EXIT_NO_HELPER)


def load_manifest(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        die(f"manifesto ilegível: {path}: {e}", EXIT_USAGE)
    except json.JSONDecodeError as e:
        die(f"manifesto não é JSON válido: {path}: {e}", EXIT_BAD_CORPUS)
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        die(f"manifesto sem cenários: {path}", EXIT_BAD_CORPUS)
    return data


def build_fixture(spec, fixture_dir):
    """Monta o fixture declarativo do cenário: git init com identidade via
    env GIT_CONFIG_* (seam da fase 02), commit base opcional (git_commit,
    espelho do builder do bats — fase 35, bug latente da 34), .planning/
    config.json e files."""
    fixture = spec.get("fixture") or {}
    if fixture.get("git"):
        env = dict(os.environ)
        env.update({
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "user.name",
            "GIT_CONFIG_VALUE_0": "Cairn Tests",
            "GIT_CONFIG_KEY_1": "user.email",
            "GIT_CONFIG_VALUE_1": "cairn-tests@example.com",
        })
        proc = subprocess.run(["git", "init", "-q", str(fixture_dir)],
                              capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            die(f"git init do fixture falhou: {proc.stderr.strip()[:200]}",
                EXIT_NO_HELPER)
        if fixture.get("git_commit"):
            proc = subprocess.run(
                ["git", "-C", str(fixture_dir), "commit", "-q",
                 "--allow-empty", "-m", "fixture base"],
                capture_output=True, text=True, env=env)
            if proc.returncode != 0:
                die("git commit base do fixture falhou: "
                    f"{proc.stderr.strip()[:200]}", EXIT_NO_HELPER)
    planning = fixture.get("planning_config")
    if planning is not None:
        planning_dir = fixture_dir / ".planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        (planning_dir / "config.json").write_text(
            json.dumps(planning, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    for rel, content in (fixture.get("files") or {}).items():
        target = fixture_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def apply_mask(scenario_id, mask, stdout_text):
    """Valida cada valor no jq_path contra o regex e o substitui pelo
    marcador. Mask que não casa é manifesto/corpus inconsistente: aborta
    (exit 6) sem gravar nada — nunca golden com valor vivo não mascarado."""
    if not mask:
        return stdout_text
    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError:
        die(f"cenário {scenario_id}: mask declarada mas o stdout não é JSON",
            EXIT_BAD_CORPUS)
    for jq_path, regex in mask.items():
        parts = [p for p in jq_path.lstrip(".").split(".") if p]
        cur = payload
        for part in parts[:-1]:
            if not isinstance(cur, dict) or part not in cur:
                die(f"cenário {scenario_id}: mask path {jq_path} não existe "
                    "no stdout gravado", EXIT_BAD_CORPUS)
            cur = cur[part]
        leaf = parts[-1] if parts else None
        if leaf is None or not isinstance(cur, dict) or leaf not in cur:
            die(f"cenário {scenario_id}: mask path {jq_path} não existe no "
                "stdout gravado", EXIT_BAD_CORPUS)
        value = cur[leaf]
        if not isinstance(value, str) or not re.search(regex, value):
            die(f"cenário {scenario_id}: valor em {jq_path} não casa o "
                f"regex da mask ({regex})", EXIT_BAD_CORPUS)
        cur[leaf] = "<masked>"
    return json.dumps(payload, indent=2, ensure_ascii=False)


def write_golden_atomic(path, golden):
    """Escrita em temp irmão + rename atômico (precedente staging da fase
    02): interrupção nunca deixa golden parcial no diretório."""
    data = json.dumps(golden, indent=2, ensure_ascii=False,
                      sort_keys=True) + "\n"
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        die(f"não consegui publicar o golden {path}: {e}", EXIT_NO_HELPER)


def record_scenario(spec, entry, goldens_dir, source_info):
    scenario_id = spec.get("id")
    argv = spec.get("argv")
    if not scenario_id or not isinstance(argv, list) or not argv:
        die(f"cenário sem id/argv utilizável no manifesto: {spec!r}",
            EXIT_BAD_CORPUS)
    if spec.get("divergent_from_real"):
        # Divergência DECLARADA da casa (divergences.json): o envelope do
        # cairn difere do binário real por decisão consciente (fato no bd,
        # shapes próprios) — gravar do real produziria um golden que a casa
        # nunca satisfaz. Pular com mensagem, nunca abortar (fase 35).
        say(f"pulado (divergência declarada da casa): {scenario_id}")
        return
    with tempfile.TemporaryDirectory(prefix="gsd-record.") as tmp:
        fixture_dir = Path(tmp) / "fixture"
        fixture_dir.mkdir()
        build_fixture(spec, fixture_dir)
        env = dict(os.environ)
        env.pop("CAIRN_GSD_CONFIG_MANIFEST", None)
        try:
            proc = subprocess.run(
                ["node", str(entry)] + list(argv),
                capture_output=True, text=True, cwd=str(fixture_dir),
                env=env, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            die(f"cenário {scenario_id}: execução do binário falhou: {e}",
                EXIT_NO_HELPER)
    stdout_text = apply_mask(scenario_id, spec.get("mask"), proc.stdout)
    golden = {
        "expect": {
            "exit_code": proc.returncode,
            "stderr": proc.stderr if spec.get("expect_stderr") else None,
            "stdout": stdout_text,
        },
        "provenance": "recorded",
        "scenario": scenario_id,
        "schema_version": 1,
        "source": source_info,
    }
    write_golden_atomic(goldens_dir / f"{scenario_id}.golden.json", golden)
    say(f"gravado: {scenario_id} (exit {proc.returncode})")


def main():
    args = build_parser().parse_args()
    cache_dir = (Path(args.cache_dir).resolve() if args.cache_dir
                 else REPO_ROOT / CACHE_RELPATH)
    expected = args.expect_commit or TAG_COMMIT
    source = args.source or SOURCE_URL
    scenarios_path = (Path(args.scenarios).resolve() if args.scenarios
                      else REPO_ROOT / GOLDENS_RELPATH / "scenarios.json")
    goldens_dir = (Path(args.goldens_dir).resolve() if args.goldens_dir
                   else REPO_ROOT / GOLDENS_RELPATH)

    head = verify_corpus(cache_dir, expected)
    require_node()
    entry = find_entrypoint(cache_dir)
    ensure_runtime_build(cache_dir, entry)

    manifest = load_manifest(scenarios_path)
    msource = manifest.get("source") or {}
    source_info = {
        "commit": head,
        "repo": msource.get("repo") or str(source),
        "tag": msource.get("tag") or TAG,
    }
    scenarios = manifest["scenarios"]
    if args.only:
        scenarios = [s for s in scenarios if s.get("id") == args.only]
        if not scenarios:
            die(f"cenário '{args.only}' não existe no manifesto "
                f"{scenarios_path}", EXIT_BAD_CORPUS)
    if not goldens_dir.is_dir():
        die(f"diretório de goldens inexistente: {goldens_dir}", EXIT_USAGE)
    for spec in scenarios:
        record_scenario(spec, entry, goldens_dir, source_info)
    say(f"{len(scenarios)} golden(s) gravado(s) em {goldens_dir}")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
