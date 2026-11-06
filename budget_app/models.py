
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Transaction:
    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)


    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        return cls(
            id = data["id"],
            date = data["date"],
            type = data["type"],
            category = data["category"],
            amount = data["amount"],
            memo = data.get("memo", ""),
            tags = data.get("tags", []),
        )

@dataclass(frozen=True)
class Budget:
    month: str
    amount: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data:dict[str, Any]) -> "Budget":
        return cls(
            month = data["month"],
            amount = data["amount"]
        )
    