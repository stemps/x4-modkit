# x4-modkit architecture

`x4mod` (`cli.py`) is the only entry point. It finds the mod root as the nearest
folder with `src/content.xml` (`release_archive.find_root`, or `--root`) and passes
it to every module; no module locates itself relative to the mod. Mod-specific
values come only from `src/content.xml` (its `id` names the package folder, its
`name` the ZIP prefix), `nexus.json`, `steam.json` and `discord.json`.
Machine-local paths come from `settings.py`: environment variable, then
`~/.config/x4-modkit/paths.env` (or `$X4MODKIT_CONFIG`).

`shared.just` is the justfile block every mod carries verbatim (`x4mod justfile`
prints it). `doctor.py` fails `just test-release` when a mod's block differs or it
still holds a copy of a kit-owned file. Recovery messages name `just` recipes, so
the block and those messages change together.

`translations.py` (`x4mod translations`) is the translation gate; its module
docstring states the convention. It reads `translations.json` for format
exemptions and reports every problem in one run. Mod-specific text contracts
(for example which entries must escape `%`) stay in the mod's own tests.

## Release flow

`just release` requires clean `main` tracking and matching `origin/main`. It
suggests the next minor version (with an editable override), opens commit subjects
in Git's configured editor, checks Nexus and Steam, updates `VERSION`,
`CHANGELOG.md` and the manifest version/date, runs `just check-release`, commits
only that metadata, creates an annotated tag and atomically pushes both. It then
publishes to Nexus and afterwards to the Steam Workshop. Before the first tag the
suggestion comes from the manifest version; later releases use the latest tag.

- `release.py`: preflight, version/notes, metadata, validation and Git
  orchestration; preserves concurrent edits and rolls back pre-commit failures.
  Edited notes are saved to `.git/release-notes/v<version>.json` right after the
  editor closes; a later attempt at the same version reopens them (plus subjects of
  commits made since) and the file is deleted once the release tag exists.
- `release_archive.py`: deterministic ZIPs of `src/` under the manifest
  id, local working-tree builds and reconstruction from verified remote tags.
  Every file in `src/` ships and nothing outside it does. The game's junction
  points at `src/`, so in-game tests see the same files as the ZIP.
  `src/MIT-LICENSE` is a copy of the root licence (kept for GitHub); a test keeps
  them identical. Tags from before the `src/` layout cannot be repackaged.
- `nexus_publish.py`: Nexus upload/version/changelog publication with
  resumable receipts in ignored `dist/nexus/`; `X4_NEXUS_KEY` supplies
  credentials. A `file_id` in `nexus.json` pins the main file; with `null`,
  exactly one main file must exist. `create_new_file: true` is only for an empty
  page and is not safe to leave on once a file exists.
- `workshop_build.py`: stages `dist/workshop/<tag|local>/<id>/` from the
  same files as the ZIP. Its `content.xml` gets `id="ws_<published_file_id>"`
  and `sync="false"`; each dependency mapped in `steam.json` gets its Workshop id,
  added beside an optional dependency and replacing a required one. Root `.mkv`
  files stay loose; everything else is packed into `ext_01.cat/.dat` with
  XRCatTool and verified against the sources. `just workshop-placeholder` builds
  the folder for the one-time item creation.
- `steam_publish.py`: uploads that folder with `WorkshopTool update
  -batchmode` (Steam client must be online) and keeps resumable receipts in
  `dist/steam/`. Uncertain outcomes are resolved with `--confirm-uploaded` or
  `--retry-upload`; `--minor` is for an unchanged version. Releases skip Steam
  while `steam.json` is absent or has no `published_file_id`.
  The change note is the release notes as Steam BBCode: WorkshopTool reads a
  value starting with `-` (a Markdown list) as the next switch and uploads nothing.
- `discord_publish.py`: posts the release announcement (title, Nexus/Steam
  links, tag notes) through the webhook of the channel in `discord.json`. The URL
  is a secret read from the env var that file names, never written anywhere. Release
  preflight checks the webhook points at that channel and the text fits 2000
  characters; the post runs last, only after Nexus (and Steam, if recorded) are done.
  Receipts in `dist/discord/`; uncertain outcomes are resolved with
  `--confirm-posted` or `--retry-post`. Releases skip Discord without `discord.json`.
- `manual_bbcode.py`: converts the released `docs/MANUAL.md` to Nexus or
  Steam BBCode (`dist/<nexus|steam>/<tag>/description-<nexus|steam>.bbcode.txt`) and opens
  Notepad for copy/paste. Unsupported Markdown fails before releasing, and so does
  Steam output over 8000 characters (Steam preflight). Continued numbered lists
  use explicit numbers because neither site has a list-start attribute.
- `gamelink.py` (`just link` / `unlink` / `link-status`): manages the
  `extensions/<repo folder>` junction to `src/` (a symlink off Windows). The
  extensions dir comes from `X4_EXTENSIONS`, then `X4_GAME/extensions`, each from
  the environment or the kit config (`settings.py`). It refuses to replace or
  delete a regular folder, and unlink removes only the junction itself.
  `--source`/`--name` link another folder of the repo, such as a sample.
- `gamelog.py` (`just log`): follows `debug.txt` from `X4_DEBUGLOG`, then
  `X4_PROFILE/debug.txt`, then the newest profile's log.
- `tests/`: isolated release repositories/local remotes and fake HTTP responses
  around a neutral `example_mod` fixture, plus live checks of a real mod's files
  (`MOD_ROOT`: the mod under `x4mod test`, else `tests/sample_mod/`). Each module
  runs in its own process. `test_kit.py` covers settings, root discovery, links
  and drift detection.

`just build-zip` packages dirty and untracked `src/` files without changing Git
or versions. `just publish-nexus vX.Y.Z` and `just publish-steam vX.Y.Z` resume
one platform; `just nexus-description <ref>` regenerates only the manual handoff
(`just steam-description <ref>` for Steam)
for a release tag or any branch/commit. The kit pins
`markdown-it-py==4.0.0`. Retain `dist/` receipts to resume uncertain uploads safely.
