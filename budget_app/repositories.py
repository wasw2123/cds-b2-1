

import json
from pathlib import Path
from typing import Any, Iterator

from budget_app.errors import BudgetAppError
from budget_app.models import Budget, Transaction


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip()
            if not cleaned:
                continue
            try:
                yield json.loads(cleaned)
            except json.JSONDecodeError:
                raise BudgetAppError(msg="json을 로드를 실패하였습니다.")

def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def write_all_jsonl(path: Path, items: Iterator[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_name(f"{path.name}.tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    tmp_path.replace(path)

DEFAULT_CATEGORIES = ("food", "transport", "rent", "salary", "etc")

class CategoryRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

        if not self.path.exists() or self.path.stat().st_size == 0:
            write_all_jsonl(self.path, [{"name": c} for c in DEFAULT_CATEGORIES])

    def list_all(self) -> list[str]:
        return [data["name"] for data in iter_jsonl(self.path)]
        
    def exists(self, name: str) -> bool:
        return name in self.list_all()
    
    def add(self, name: str) -> str:
        if self.exists(name):
            raise BudgetAppError(msg="중복되는 카테고리가 존재합니다.", hint=f"{', '.join(self.list_all())}제외하고 입력해주세요.")
        append_jsonl(self.path, {"name": name})

        return name

    def remove(self, name: str) -> None:
        categories = self.list_all()
        if name not in categories:
            raise BudgetAppError(msg="카테고리가 존재하지 않습니다.", hint=f"{', '.join(categories)}내에서 입력해주세요.")

        items = [{"name": c} for c in categories if c != name]
        write_all_jsonl(self.path, items)


class BudgetRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, month: str) -> Budget | None:
        for data in iter_jsonl(self.path):
            if data["month"] == month:
                return Budget.from_dict(data)
        return None

    def set_budget(self, budget: Budget) -> Budget:
        items = [data for data in iter_jsonl(self.path) if data["month"] != budget.month]
        items.append(budget.to_dict())

        write_all_jsonl(self.path, items)
        return budget

class TransactionRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def iter_all(self) -> Iterator[Transaction]:
        for data in iter_jsonl(self.path):
            yield Transaction.from_dict(data)

    def add(self, transaction: Transaction) -> Transaction:
        append_jsonl(self.path, transaction.to_dict())
        return transaction

    def get_by_id(self, tx_id: str) -> Transaction | None:
        for tx in self.iter_all():
            if tx.id == tx_id:
                return tx
        return None

    def next_id(self) -> str:
        max_num = 0
        for tx in self.iter_all():
            num = int(tx.id.split("-")[1])
            max_num = max(max_num, num)
        return f"TX-{max_num + 1:06d}"

    def update(self, updated_tx: Transaction) -> Transaction:
        old_tx = self.get_by_id(updated_tx.id)
        if not old_tx:
            raise BudgetAppError(msg="일치하는 거래내역이 존재하지 않습니다.")

        items = [item.to_dict() for item in self.iter_all() if item.id != old_tx.id]
        items.append(updated_tx.to_dict())

        write_all_jsonl(self.path, items)
        return updated_tx

    def delete(self, tx_id: str) -> None:
        tx = self.get_by_id(tx_id)
        if not tx:
            raise BudgetAppError(msg="일치하는 거래내역이 존재하지 않습니다.")

        items = [item.to_dict() for item in self.iter_all() if item.id != tx_id]
        write_all_jsonl(self.path, items)
        return None
        