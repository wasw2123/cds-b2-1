
import argparse

from budget_app.decorators import handle_errors, timer
from budget_app.models import Transaction
from budget_app.services import BudgetService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="budget_app", description="나만의 용돈 기입장")
    parser.add_argument("--data-dir", default="./data", help="데이터 저장 폴더 경로")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("add", help="거래 내역 추가")

    list_parser = subparsers.add_parser("list", help="거래 목록 조회")
    list_parser.add_argument("--limit", type=int, default=10, help="출력할 최대 건수")

    cat_parser = subparsers.add_parser("category", help="카테고리 관리")
    cat_sub = cat_parser.add_subparsers(dest="category_cmd", required=True)
    cat_sub.add_parser("add", help="카테고리 추가")
    cat_sub.add_parser("list", help="카테고리 목록 조회")
    cat_sub.add_parser("remove", help="카테고리 삭제")

    del_parser = subparsers.add_parser("delete", help="거래내역 삭제")
    del_parser.add_argument("--id", required=True)

    update_parser = subparsers.add_parser("update", help="거래내역 수정")
    update_parser.add_argument("--id", required=True)
    update_parser.add_argument("--date")
    update_parser.add_argument("--type")
    update_parser.add_argument("--category")
    update_parser.add_argument("--amount")
    update_parser.add_argument("--memo")
    update_parser.add_argument("--tags")

    search_parser = subparsers.add_parser("search", help="거래내역 검색")
    search_parser.add_argument("--from", dest="date_from")
    search_parser.add_argument("--to", dest="date_to")
    search_parser.add_argument("--category")
    search_parser.add_argument("--type")
    search_parser.add_argument("--q")
    search_parser.add_argument("--tag")

    summary_parser = subparsers.add_parser("summary", help="월별 요약")
    summary_parser.add_argument("--month", required=True)
    summary_parser.add_argument("--top", type=int, default=3)

    budget_parser = subparsers.add_parser("budget", help="예산 관리")
    budget_sub = budget_parser.add_subparsers(dest="budget_cmd", required=True)
    budget_set = budget_sub.add_parser("set", help="예산 설정")
    budget_set.add_argument("--month", required=True)
    budget_set.add_argument("--amount", required=True)

    export_parser = subparsers.add_parser("export", help="csv 내보내기")
    export_parser.add_argument("--out", required=True)
    export_parser.add_argument("--month")
    export_parser.add_argument("--from", dest="date_from")
    export_parser.add_argument("--to", dest="date_to")

    import_parser = subparsers.add_parser("import", help="csv 가져오기")
    import_parser.add_argument("--from", required=True, dest="from_file")
    import_parser.add_argument("--rollback-on-error", action="store_true", help="오류 발생 시 전체 롤백")

    return parser

def format_transaction(tx: Transaction) -> str:
    return f"{tx.id} | {tx.date} | {tx.type} | {tx.category} | {tx.amount} | {tx.memo} | {', '.join(tx.tags) if tx.tags else ''}"

@timer
@handle_errors
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = BudgetService(data_dir = args.data_dir)

    if args.command == "category":
        if args.category_cmd == "list":
            for c in service.list_categories(): print(f"- {c}")

        if args.category_cmd == "add":
            raw_name = input("카테고리 이름: ")
            cat_name = service.add_category(raw_name)
            print(f"[저장 완료] category = {cat_name}")

        if args.category_cmd == "remove":
            raw_name = input("삭제할 카테고리 이름: ")
            service.remove_category(raw_name)
            print(f"[카테고리 삭제 완료]")

    if args.command == "add":
        tx = service.add_transaction(
            raw_date=input("날짜: "),
            raw_type=input("타입(income, expense): "),
            raw_category=input(f"카테고리({'. '.join(service.list_categories())}): "),
            raw_amount=input("금액: "),
            raw_memo=input("메모(선택): "),
            raw_tags=input("태그(선택, 여러개 입력 시 ,(콤마)로 구분합니다.): " )
        )
        print(f"[저장 완료] id={tx.id}")

    if args.command == "list":
        for tx in service.list_transactions(limit=args.limit):
            print(format_transaction(tx))

    if args.command == "delete":
        service.delete_transaction(args.id)
        print("[삭제 완료]")

    if args.command == "update":
        tx = service.update_transaction(
            tx_id=args.id,
            raw_date=args.date,
            raw_type=args.type,
            raw_category=args.category,
            raw_amount=args.amount,
            raw_memo=args.memo,
            raw_tags=args.tags,
        )

        print(f"[수정 완료] id={tx.id}")

    if args.command == "search":
        for tx in service.search_transactions(
            date_from=args.date_from,
            date_to=args.date_to,
            category=args.category,
            tx_type=args.type,
            query=args.q,
            tag=args.tag,
        ):
            print(format_transaction(tx))

    if args.command == "summary":
        res = service.get_monthly_summary(raw_month=args.month, top_n=args.top)
        if res["count"] == 0:
            print("[데이터 없음]")
        else:
            print(f"[거래 내역] {res['count']}건")
            print(f"[총 수입] {res['total_income']:,}원")
            print(f"[총 지출] {res['total_expense']:,}원")
            print(f"[잔액] {res['balance']:,}원")
            for idx, top_e in enumerate(res["top_expenses"], start=1):
                print(f"[상위 지출처 {idx}] {top_e[0]}: {top_e[1]:,}원")
            if res["budget_amount"]:
                print(f"[예산] {res['budget_amount']:,}원")
                print(f"[예산 한도] {res['usage_rate']:,.2f}%")
                print(f"[예산 초과 여부] {'예산을 초과하였습니다.' if res['is_exceeded'] else '예산이 남았습니다.'}")
            else:
                print("예산 설정 없음")
                print("예산 설정 방법")
                print("예) python -m budget_app budget set --month yyyy-mm --amount 50000")

    if args.command == "budget":

        if args.budget_cmd == "set":
            budget = service.set_budget(raw_month=args.month, raw_amount=args.amount)
            date = budget.month.split("-")
            print(f"[예산 설정 완료] {date[0]}년 {date[1]}월 예산 {budget.amount:,}원")

    if args.command == "export":
        count = service.export_csv(
            out_file=args.out,
            month=args.month,
            date_from=args.date_from,
            date_to=args.date_to,
        )

        print(f"[csv 내보내기 완료] {args.out} ({count} 건)")

    if args.command == "import":
        imported, skipped, errors = service.import_csv(
            from_file=args.from_file,
            rollback_on_error=args.rollback_on_error,
        )

        print(f"[csv 가져오기 완료] imported={imported}, skipped={skipped}")
        if errors:
            for err in errors: print(f"[스킵 이유] {err}")


    return 0