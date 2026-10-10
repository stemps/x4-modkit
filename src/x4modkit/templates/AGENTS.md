# AGENTS.md

## Tooling

Release, publishing, translation checks, `just link` and `just log` come from
x4-modkit (`x4mod` on PATH). Never copy its files into this repository; the
"Shared tasks" block at the end of the `justfile` must stay identical to
`x4mod justfile`.

## How to work with this repository

- Don't commit changes. Leave them unstashed for review. Only create worktrees
  if explicitly asked to.
- Maintain a repo-local KNOWLEDGEBASE.md with condensed details relevant for
  future development of this mod. Keep only durable, non-obvious findings.
  Capture:
  - findings about the game engine
  - vanilla game mechanisms this mod interacts with
  - core mechanics of this mod
  - experiments performed and their relevant findings
- Maintain a repo-root ARCHITECTURE.md with info about code organisation and
  module responsibilities.
- Once the mod is released, new additions need to be backwards compatible with
  existing older saves.
- README.md and all files in `docs/` are end-user focused (players and mod
  developers) and maintained by the repo owner. Leave them alone.
- Keep code modules to a focused single responsibility. Recommend refactorings if
  you spot code that violates this.
- Make sure to keep all language translation files in sync with the English
  version (`src/t/0001.xml`), in which the mod is developed. Auto-translate all
  new and changed keys into all languages.
- After each turn with code changes, inform the user whether a full restart is
  required, or if a `/reloadui` command suffices.
- Don't use em-dashes. The game can't render them. Use normal hyphens instead.

## Validation

- Use `just` to run checks (execute without options to get a list of possible
  tasks). Run validations for areas affected by your changes after each turn.
