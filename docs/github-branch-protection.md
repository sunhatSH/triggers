# GitHub branch protection (PR-only, all branches)

Goal: **only `@sunhatSH` may push directly** — everyone else contributes via fork + PR.

## One command (recommended)

Your GitHub token must allow **Administration** on this repo.

**Fine-grained PAT** (common with `gh auth login`):  
GitHub → Settings → Developer settings → Fine-grained tokens → edit token →  
Repository `sunhatSH/triggers` → **Administration: Read and write** → Save.

**Or classic token:**

```bash
gh auth login -h github.com -s repo
# or refresh:
gh auth refresh -h github.com -s repo
```

Then:

```bash
bash scripts/apply-branch-protection.sh
```

This configures **all branches** (`~ALL`):

| Rule | Value |
|---|---|
| Scope | All branches |
| Direct push | Only `@sunhatSH` (override with `PUSH_USERS=you`) |
| Merge | Pull request required |
| Reviews | 1 approval; Code Owners (`.github/CODEOWNERS`) |
| Force push / delete branch | Disabled |

Re-running the script upgrades the legacy `PR-only main and dev` ruleset in place.

## Collaborator access

Rulesets block direct push to **any** branch for users without bypass — including Write collaborators.

To keep the fork → PR workflow:

- **Settings → Collaborators**: give external contributors **Read** (or **Triage**), not **Write**
- They fork → open PR → you review and merge

Keep **Write** or **Maintain** only for trusted co-maintainers who should bypass rules (add them to `PUSH_USERS` in the script).

## Verify

```bash
gh api repos/sunhatSH/triggers/rulesets --jq '.[] | {name, include: .conditions.ref_name.include, bypass: [.bypass_actors[].actor_type]}'
```

Try pushing as another account to any branch — should be rejected.
