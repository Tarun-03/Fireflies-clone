from dataclasses import dataclass, field


@dataclass
class DomainError(Exception):
    status: int
    code: str
    message: str
    field_errors: list[dict[str, str]] = field(default_factory=list)
