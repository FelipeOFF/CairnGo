"""cairn_gsd_render.py — o envelope medido do binário, em UMA fonte (D-01).

Módulo compartilhado pelos irmãos cairn-gsd-state.py, cairn-gsd-init.py e
cairn-gsd-check.py: a semântica de saída MEDIDA do gsd-tools real (io.cts
output(): sem --raw JSON.stringify(v, null, 2); com --raw e rawValue
definido String(rawValue); sem newline final) e o parse de argv na forma da
casa. O dispatcher cairn-gsd.py mantém a cópia original (é dele que a forma
foi copiada); este módulo existe para os irmãos não carregarem cópias que
possam divergir — a doença do milestone com outro chapéu.

A fase 35 usou a discrição do 35-CONTEXT ("uso de cairn_gsd_render.py se o
teto apertar") e trouxe para cá o substrato de leitura de documento e o de
resolução de fato; o arquivo fechou em 1536 linhas, acima do teto D-01, e o
nome passou a mentir sobre o conteúdo (CairnGo-zzgn). A partição
(CairnGo-2fyg, saída (a) decidida na fase 38) devolveu cada substrato ao seu
próprio módulo — cairn_gsd_parse.py (entrada de documento) e
cairn_gsd_fact.py (git, subprocess, auditoria). Aqui fica só o que 2+ irmãos
compartilham: entra símbolo novo quando um segundo irmão passa a precisar
dele, e não antes.

Não é CLI: sem wrapper .sh (nota registrada no SUMMARY do 34-05).
"""
import json
import sys

_UNDEFINED = object()


def js_number_text(n):
    if isinstance(n, int):
        return str(n)
    if float(n).is_integer():
        return str(int(n))
    return repr(float(n))


def js_string(value):
    """String(valor) do JS para --raw: bool minúsculo, null literal,
    objeto '[object Object]', array join por vírgula."""
    if isinstance(value, str):
        return value
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return js_number_text(value)
    if isinstance(value, list):
        return ",".join("" if item is None else js_string(item)
                        for item in value)
    if isinstance(value, dict):
        return "[object Object]"
    return str(value)


def stringify(value):
    return json.dumps(value, indent=2, ensure_ascii=False)


def emit(text):
    sys.stdout.write(text)


def output_like_binary(result, raw, raw_value=_UNDEFINED):
    if raw and raw_value is not _UNDEFINED:
        emit(js_string(raw_value))
    else:
        emit(stringify(result))


def parse_verb_args(rest, value_flags=(), bool_flags=("--raw",)):
    """Forma da casa: flags de valor nomeadas, bools, flag desconhecida
    ignorada best-effort; o resto é posicional."""
    pos, flags = [], {}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in value_flags:
            flags[tok] = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
        elif tok in bool_flags:
            flags[tok] = True
            i += 1
        elif tok.startswith("-"):
            i += 1
        else:
            pos.append(tok)
            i += 1
    return pos, flags
