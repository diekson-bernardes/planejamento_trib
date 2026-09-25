"""Erros de domínio do worker. `code` é gravado em source_files.error_code."""


class WorkerError(Exception):
    code = "ERROR"
    retryable = False


class NoTextLayer(WorkerError):
    code = "NO_TEXT"


class NotPdf(WorkerError):
    code = "NOT_PDF"


class HashMismatch(WorkerError):
    code = "HASH_MISMATCH"


class Unclassified(WorkerError):
    code = "UNCLASSIFIED"


class LayoutNotRecognized(WorkerError):
    code = "LAYOUT"


class CnpjMismatch(WorkerError):
    code = "CNPJ_MISMATCH"


class HasAdjustments(WorkerError):
    code = "HAS_ADJUSTMENTS"


class FileNotFound(WorkerError):
    code = "FILE_NOT_FOUND"


class TransientError(WorkerError):
    """Falha de infraestrutura (banco/Storage/timeout): o job pode ser repetido."""

    code = "TRANSIENT"
    retryable = True
