# Triage labels (beads)

Canonical Matt roles, stored as **bd labels** (string = name):

| Role | Label |
|---|---|
| needs triage | `needs-triage` |
| needs info | `needs-info` |
| ready for an agent | `ready-for-agent` |
| ready for a human | `ready-for-human` |
| will not fix | `wontfix` |
| bug | `bug` |
| enhancement | `enhancement` |

Every triaged bead carries exactly one state role and, when categorised, one of `bug` / `enhancement`.

The implement frontier is `bd ready` ∩ `ready-for-agent`.
