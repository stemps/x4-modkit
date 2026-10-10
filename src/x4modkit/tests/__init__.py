"""Release tooling tests.

A few tests check a real mod repository's own files (manifests, manual, publication
configs) against the tooling. They read MOD_ROOT: the mod under test when run through
`x4mod test` from a mod repository, otherwise the bundled sample mod.
"""
import os
from pathlib import Path

MOD_ROOT = Path(os.environ.get('X4MODKIT_MOD_ROOT') or Path(__file__).resolve().parent / 'sample_mod')
