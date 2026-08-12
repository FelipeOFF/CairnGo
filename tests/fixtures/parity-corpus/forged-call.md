# Corpus fixture do controle negativo (PAR-02)

Este arquivo existe para provar que o scanner MORDE. Ele carrega, de propósito,
uma chamada a um verbo que nenhum spelling do contrato roteia — se a varredura
do corpus real ficasse verde por vacuidade (regex que não casa nada, tabela de
rotas vazia lida como "tudo resolve"), este arquivo continuaria verde junto, e
o gate inteiro seria decoração.

Um passo de workflow, como qualquer outro:

```bash
FORJADO=$(gsd_run query forged.dead-route --pick nada)
```

E duas armadilhas que o scanner tem que IGNORAR, porque as duas resolvem ou não
são chamada:

- prosa citando `gsd_run query`, que é menção e não passo;
- `$(gsd_run query verification status "${PHASE_DIR}" --pick status)` na forma
  com espaço, que é spelling registrado de `verification.status`.

```bash
VERIFY_STATUS=$(gsd_run query verification status "${PHASE_DIR}" --pick status)
```
