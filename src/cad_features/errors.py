class CadFeaturesError(Exception):
    """Base class for expected user-facing errors."""


class UnsupportedFormatError(CadFeaturesError):
    pass


class InputFileError(CadFeaturesError):
    pass


class OutputFileError(CadFeaturesError):
    pass


class CadReadError(CadFeaturesError):
    pass


class CadAnalysisError(CadFeaturesError):
    pass
