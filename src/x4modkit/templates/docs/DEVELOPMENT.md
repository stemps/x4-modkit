# Development of the Mod

See [Runtime architecture](../ARCHITECTURE.md) for module responsibilities.

## Dependencies

- [uv](https://docs.astral.sh/uv/) Python package manager
- [Just](https://github.com/casey/just) for running convenience tasks
- [x4-modkit](https://github.com/stemps/x4-modkit), the shared release,
  publishing, translation, `just link` and `just log` tooling. Install it once with
  `uv tool install git+https://github.com/stemps/x4-modkit` so `x4mod` is on PATH
- For Steam Workshop releases: Egosoft's "X Tools" (free, in the Steam library
  under Tools), which provides `WorkshopTool.exe` and `XRCatTool.exe`

## Local development setup

`just link` creates a junction from the game's `extensions/@MOD_ID@` to `src/`, so
the game loads your working copy directly; `just unlink` removes only the junction.
Paths come from environment variables or `~/.config/x4-modkit/paths.env`
(`x4mod config` shows what resolved). `just log` follows the game's `debug.txt`.

## Translations

English lives only in `src/t/0001.xml` (root `<language>`, no id); do not add a
`0001-l044.xml`. Each of the 15 other game locales has `src/t/0001-lNNN.xml` with
`<language id="NNN">` and exactly the English page/text ids. `just translations`
(part of `just check`) checks coverage, escapes (write `\(` and `\)`), em dashes
and formatting. Translation files need a full game restart.

## Releasing

`just release` runs from a clean `main` that tracks `origin/main`. Before the
first release, create the Nexus page and put its id into `nexus.json` as
`mod_id`. Keep `create_new_file: true` only for the first upload to an empty page,
then set it to false. Add `steam.json` (and `discord.json`) to publish there too;
see the x4-modkit README.
