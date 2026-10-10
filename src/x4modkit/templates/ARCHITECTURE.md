# Runtime architecture

## Repository layout

`src/` is the mod: exactly the files the game loads and every release ships.
Everything else is development-only: `docs/`, `images/` and metadata.

## Translations

`src/t/0001.xml` is the English source for text page @PAGE@; the 15
`0001-lNNN.xml` files carry the same page/text ids for every other game locale.

## Release tooling

Release, publication, translation checks, `just link` and `just log` come from
x4-modkit; see its README and ARCHITECTURE.md.
