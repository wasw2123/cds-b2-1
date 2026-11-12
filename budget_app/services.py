



import csv
from pathlib import Path
from typing import Any, Iterator

from budget_app.decorators import logger
from budget_app.errors import BudgetAppError
from budget_app.models import Budget, Transaction
from budget_app.repositories import BudgetRepository, CategoryRepository, TransactionRepository
from budget_app.validators import parse_tags, validate_amount, validate_category_name, validate_date, validate_month, validate_type


class BudgetService:
    def __init__(self, data_dir: Path | str = "./data") -> None:
        base_dir = Path(data_dir)
        self.category_repo = CategoryRepository(base_dir / "categories.jsonl")
        self.budget_repo = BudgetRepository(base_dir / "budgets.jsonl")
        self.transaction_repo = TransactionRepository(base_dir / "transactions.jsonl")

    @logger
    def list_categories(self) -> list[str]:
        return self.category_repo.list_all()

    @logger
    def add_category(self, raw_name: str) -> str:
        name = validate_category_name(raw_name)
        return self.category_repo.add(name)

    @logger
    def remove_category(self, raw_name: str) -> None:
        name = validate_category_name(raw_name)
        for tx in self.transaction_repo.iter_all():
            if tx.category == name:
                raise BudgetAppError(msg="거래내역에서 사용중인 카테고리입니다.")
        self.category_repo.remove(name)

    @logger
    def add_transaction(
        self,
        raw_date: str,
        raw_type: str,
        raw_category: str,
        raw_amount: str | int,
        raw_memo: str = "",
        raw_tags: str = "",
    ) -> Transaction:
        tx_category = validate_category_name(raw_category)
        if not self.category_repo.exists(tx_category):
            raise BudgetAppError(msg="카테고리가 등록돼 있지 않습니다.", hint=f"현재 등록된 카테고리 목록입니다. [{'. '.join(self.category_repo.list_all())}]")
        tx_date = validate_date(raw_date)
        tx_type = validate_type(raw_type)
        tx_amount = validate_amount(raw_amount)
        tx_memo = raw_memo.strip()
        tx_tags = parse_tags(raw_tags)
        tx_id = self.transaction_repo.next_id()

        return self.transaction_repo.add(
            Transaction(
                id = tx_id,
                type=tx_type,
                date=tx_date,
                amount=tx_amount,
                category=tx_category,
                memo=tx_memo,
                tags=tx_tags,
            )
        )

    @logger
    def list_transactions(self, limit: int | None = None) -> Iterator[Transaction]:
        if limit is not None and limit <= 0:
            raise BudgetAppError(msg="1이상의 양의 정수를 입력해 주세요", hint="5")
        
        sorted_txs = sorted(self.transaction_repo.iter_all(), key=lambda tx: (tx.date, tx.id), reverse=True)

        for tx in sorted_txs[:limit]:
            yield tx

    @logger
    def delete_transaction(self, tx_id: str) -> None:
        id = tx_id.strip()
        if not id:
            raise BudgetAppError(msg="아이디를 정확하게 입력해주세요.", hint="예: TX-000001")
        
        self.transaction_repo.delete(id)

    @logger
    def update_transaction(
        self,
        tx_id: str,
        raw_date: str | None = None,
        raw_type: str | None = None,
        raw_category: str | None = None,
        raw_amount: str | int | None = None,
        raw_memo: str | None = None,
        raw_tags: str | None = None,
    ) -> Transaction:
        tx = self.transaction_repo.get_by_id(tx_id.strip())
        if not tx:
            raise BudgetAppError(msg="수정할 거래내역이 존재하지 않습니다. 거래내역 아이디를 확인해주세요.")
        
        if all(v is None for v in (raw_date, raw_type, raw_category, raw_amount, raw_memo, raw_tags)):
            raise BudgetAppError(msg="수정할 사항을 입력해주세요.")

        updated_tx = Transaction(
            id = tx.id,
            type = tx.type if raw_type is None else validate_type(raw_type),
            date = tx.date if raw_date is None else validate_date(raw_date),
            amount = tx.amount if raw_amount is None else validate_amount(raw_amount),
            category = tx.category if raw_category is None else validate_category_name(raw_category),
            memo = tx.memo if raw_memo is None else raw_memo.strip(),
            tags = tx.tags if raw_tags is None else parse_tags(raw_tags),
        )

        if not self.category_repo.exists(updated_tx.category):
            raise BudgetAppError(msg="카테고리가 등록돼 있지 않습니다.", hint=f"현재 등록된 카테고리 목록입니다. [{'. '.join(self.category_repo.list_all())}]")

        return self.transaction_repo.update(updated_tx)

    @logger
    def search_transactions(
            self,
            date_from: str | None = None,
            date_to: str | None = None,
            category: str | None = None,
            tx_type: str | None = None,
            query: str | None = None,
            tag: str | None = None,
    ) -> Iterator[Transaction]:
        valied_from = validate_date(date_from) if date_from else None
        valied_to = validate_date(date_to) if date_to else None
        if (valied_from is not None and valied_to is None) or (valied_from is None and valied_to is not None):
            raise BudgetAppError(msg="시작일과 종료일 모두 입력해주세요.")

        if valied_from is not None and valied_to is not None and valied_from > valied_to:
            raise BudgetAppError(msg="시작일이 종료일보다 작아야합니다.", hint="시작일: 2026-01-12, 종료일: 2026-02-12")
        
        valied_category = validate_category_name(category) if category else None
        valied_type = validate_type(tx_type) if tx_type else None
        cleaned_query = query.strip() if query else None
        cleaned_tag = tag.strip() if tag else None

        for tx in self.list_transactions():
            if valied_from is not None and valied_from > tx.date:
                continue

            if valied_to is not None and valied_to < tx.date:
                continue

            if valied_category is not None and tx.category != valied_category:
                continue

            if valied_type is not None and tx.type != valied_type:
                continue

            if cleaned_query is not None and cleaned_query not in tx.memo:
                continue

            if cleaned_tag is not None and cleaned_tag not in tx.tags:
                continue

            yield tx


    @logger
    def set_budget(self, raw_month: str, raw_amount: str | int) -> Budget:
        return self.budget_repo.set_budget(Budget(
            month=validate_month(raw_month),
            amount=validate_amount(raw_amount),
        ))

    @logger
    def get_monthly_summary(self, raw_month: str, top_n: int = 3) -> dict[str, Any]:
        month = validate_month(raw_month)
        if top_n <= 0:
            raise BudgetAppError(msg="지출 순위는 양의 정수로 입력해주세요.", hint="5")


        count = 0
        total_income = 0
        total_expense = 0
        category_expenses = dict()
        for tx in self.transaction_repo.iter_all():
            if not tx.date.startswith(month):
                continue

            if tx.type == "income":
                total_income += tx.amount

            if tx.type == "expense":
                total_expense += tx.amount
                category_expenses[tx.category] = category_expenses.get(tx.category, 0) + tx.amount
            count += 1
        balance = total_income - total_expense

        top_expenses = sorted(category_expenses.items(), key=lambda item: item[1], reverse=True)[:top_n]

        budget = self.budget_repo.get(month)

        if budget is not None:
            usage_rate = total_expense / budget.amount * 100
            is_exceeded = total_expense > budget.amount
        else:
            usage_rate = None
            is_exceeded = False

        return {
            "count": count,
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": balance,
            "top_expenses": top_expenses,
            "budget_amount": budget.amount if budget is not None else None,
            "usage_rate": usage_rate,
            "is_exceeded": is_exceeded,
        }

    @logger
    def export_csv(
        self,
        out_file: Path | str,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        if month is None and date_from is None and date_to is None:
            raise BudgetAppError(msg="특정 달이나 기간을 지정해주세요.")

        valied_month = validate_month(month) if month is not None else None
        valied_from = validate_date(date_from) if date_from is not None else None
        valied_to = validate_date(date_to) if date_to is not None else None

        if valied_from is not None and valied_to is not None and valied_from > valied_to:
            raise BudgetAppError(msg="시작일이 종료일보다 작아야합니다.", hint="시작일: 2026-01-12, 종료일: 2026-02-12")

        out_path = Path(out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "type", "category", "amount", "memo", "tags"])
            writer.writeheader()
            for tx in self.transaction_repo.iter_all():
                if valied_month is not None and not tx.date.startswith(valied_month):
                    continue
                if valied_from is not None and valied_from > tx.date:
                    continue
                if valied_to is not None and valied_to < tx.date:
                    continue

                writer.writerow({
                    "date": tx.date,
                    "type": tx.type,
                    "category": tx.category,
                    "amount": tx.amount,
                    "memo": tx.memo,
                    "tags": ", ".join(tx.tags),
                })
                count += 1
        return count

    @logger
    def import_csv(self, from_file: Path | str) -> tuple[int, int]:
        path = Path(from_file)
        if not path.exists():
            raise BudgetAppError(msg="파일이 존재하지 않습니다.")

        imported = 0
        skipped = 0
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.add_transaction(
                        raw_date=row["date"],
                        raw_type=row["type"],
                        raw_category=row["category"],
                        raw_amount=row["amount"],
                        raw_memo=row.get("memo") or "",
                        raw_tags=row.get("tags") or "",
                    )
                    imported += 1
                except (BudgetAppError, KeyError, TypeError):
                    skipped += 1
        return imported, skipped

