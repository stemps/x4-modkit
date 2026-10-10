# x4-modkit

Shared release, publication and game-link tasks for X4: Foundations mod repositories,
so each mod stops carrying (and drifting) its own copy.

One CLI, `x4mod`, run from anywhere inside a mod repository. The kit finds the mod root
as the nearest folder with `src/content.xml`; `--root` overrides it.

## Install

Requires [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/).

```bash
uv tool install --editable C:/path/to/x4-modkit     # local checkout; edits apply immediately
uv tool install git+https://github.com/stemps/x4-modkit@v0.1.0   # or a pinned release
```

`x4mod` is then on PATH. A mod justfile can point elsewhere with `X4MOD`, for example
`X4MOD="uv run --project C:/path/to/x4-modkit x4mod"`.

## Machine-local paths

Read from the environment variable first, then `~/.config/x4-modkit/paths.env`
(or `$X4MODKIT_CONFIG`), in `KEY=value` lines. An empty value counts as unset.

| Key | Used for |
|-----|----------|
| `X4_GAME` | game folder; `extensions/` below it is the default link target |
| `X4_EXTENSIONS` | link target, overrides `X4_GAME/extensions` |
| `X4_PROFILE`, `X4_DEBUGLOG` | `x4mod log`; falls back to the newest `Documents/Egosoft/X4/*/debug.txt` |
| `XRCATTOOL` | packing the Workshop catalog |
| `X4_WORKSHOPTOOL` | Steam Workshop uploads |
| `X4_NEXUS_KEY` | Nexus API key (environment only, never in a file you commit) |

`x4mod config` shows what resolved and where from.

## A mod repository

Expected layout: `src/` is the shipped mod (`content.xml`, `ui.xml`), with
`VERSION`, `CHANGELOG.md`, `docs/MANUAL.md` and optional `nexus.json`, `steam.json`,
`discord.json` at the root. Every mod-specific name comes from `src/content.xml`.

Paste the output of `x4mod justfile` at the end of the mod's justfile. It defines
`check-release`, which depends on the mod's own `check` recipe, plus `release`,
`build-zip`, `publish-*`, `link`, `log` and friends as one-line calls into the kit.

`just test-release` runs `x4mod doctor` and `x4mod test`:

- **doctor** fails on drift: a leftover copy of a kit file (`scripts/release.py`,
  `tests/release/`, ...) or a shared justfile block that differs from the kit's.
- **test** runs the kit's suite with its live checks pointed at this mod: the shipped
  `ui.xml` modules are packaged, both license copies match, the manual renders for Nexus
  and Steam, and `nexus.json`/`steam.json`/`discord.json` are valid.

## Translations

One convention for every mod, checked by `just translations` (`x4mod translations`):

- English lives in `src/t/0001.xml`, root `<language>` without an id. Shipping a
  `0001-l044.xml` as well is an error: two English copies drift.
- All 15 other game locales ship `0001-lNNN.xml` with `<language id="NNN">` and
  exactly the English page/text ids, none empty or duplicated.
- No unescaped `(` `)` (X4 strips them as translator comments; write `\(` `\)`) and
  no em dashes (the game cannot render them).
- Formatting survives translation: Lua specifiers in the same order, the same set of
  numbered MD arguments, the same `{page,t}` references and literal `\n` count.

The formatting rule is the only one with exceptions. List them in
`translations.json` at the repository root, each with a reason:

```json
{"format_exemptions": {"90210/3175": "Turkish writes %50; the text is never formatted."}}
```

An exemption no translation needs any more is itself an error.

## Developing the kit

```bash
uv run x4mod test --sample     # the full suite against the bundled sample mod
```
