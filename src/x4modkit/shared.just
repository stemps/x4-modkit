# ---------------------------------------------------------------------------
# Shared tasks from x4-modkit. Keep this block identical to `x4mod justfile`;
# `x4mod doctor` (part of test-release) fails when it drifts.
# ---------------------------------------------------------------------------

x4mod := env('X4MOD', 'x4mod')

# Every translation matches the English source src/t/0001.xml: coverage, escapes and formatting.
translations:
    {{x4mod}} translations

# Release gate: the mod checks plus the release tooling tests.
check-release: check test-release

# Release tooling tests, including live checks of this repository's manifests, manual and configs.
test-release:
    {{x4mod}} doctor
    {{x4mod}} test

# Validate, record, push, package and publish a release from clean main.
release:
    {{x4mod}} release

# Package src/ from the working tree, including uncommitted files.
build-zip:
    {{x4mod}} build-zip

# Stage src/ as a Workshop folder (ws_ manifest, packed catalog) in dist/workshop/local.
build-workshop:
    {{x4mod}} build-workshop

# Minimal folder for the one-time WorkshopTool publish that creates the Workshop item.
workshop-placeholder:
    {{x4mod}} workshop-placeholder

# Publish or resume an existing tagged release on Nexus Mods.
publish-nexus tag *args:
    {{x4mod}} publish-nexus "{{tag}}" {{args}}

# Publish or resume a tagged release on the Steam Workshop (WorkshopTool; Steam must be running).
publish-steam tag *args:
    {{x4mod}} publish-steam "{{tag}}" {{args}}

# Announce a published release in the Discord channel named in discord.json.
publish-discord tag *args:
    {{x4mod}} publish-discord "{{tag}}" {{args}}

# Render and open the manual at a release tag, branch or commit without publishing anything.
nexus-description ref:
    {{x4mod}} description "{{ref}}"

# Render and open the manual as Steam BBCode at a release tag, branch or commit without publishing anything.
steam-description ref:
    {{x4mod}} description "{{ref}}" --target steam

# Junction src/ into the game's extensions folder for in-game testing.
link:
    {{x4mod}} link

# Remove the extensions junction; never deletes a regular folder or the dev files.
unlink:
    {{x4mod}} unlink

# Show whether the extensions folder holds a junction, a copied folder or nothing.
link-status:
    {{x4mod}} link-status

# Follow the game's debug log; press Ctrl+C to stop.
log:
    {{x4mod}} log
