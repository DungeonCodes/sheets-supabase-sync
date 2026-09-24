from __future__ import annotations

from .environment import Environment, validate_environment
from .errors import ErrorCode, SyncError


def validate_staging_access(environment: Environment, *, write_requested: bool, confirmed: bool) -> None:
    """Falha fechada para destinos que nao sejam o staging explicitamente permitido."""
    if environment.app_env == "production":
        raise SyncError(ErrorCode.CONFIGURATION, "Production nao e permitida neste entrypoint")
    try:
        validate_environment(environment)
    except ValueError as error:
        raise SyncError(ErrorCode.CONFIGURATION, "Destino nao corresponde ao staging permitido") from error
    if write_requested and not confirmed:
        raise SyncError(ErrorCode.CONFIGURATION, "Escrita em staging exige confirmacao explicita")
