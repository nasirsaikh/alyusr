from whitenoise.storage import CompressedManifestStaticFilesStorage


class AlyusrStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Keep WhiteNoise compression and manifest-based cache busting while
    skipping JavaScript source-map URL rewriting.

    Some third-party packages (currently djangocms-text) ship minified
    JavaScript containing sourceMappingURL comments without shipping the
    referenced .map file. Django's ManifestStaticFilesStorage treats those
    comments as static-file dependencies during collectstatic and fails when
    the map is absent. Source maps are development/debug metadata and are not
    required for the application to run.
    """

    patterns = tuple(
        pattern
        for pattern in CompressedManifestStaticFilesStorage.patterns
        if pattern[0] != "*.js"
    )
