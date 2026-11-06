from datetime import date

from budget_app.errors import BudgetAppError

def validate_date(value: str, date_type: str = "2026-12-30") -> str:
    cleaned_date = value.strip()

    try:
        if date.fromisoformat(cleaned_date).isoformat() != cleaned_date:
            raise ValueError
    except ValueError:
        raise BudgetAppError(msg=f"날짜 형식이 올바르지 않습니다. {date_type} 형식으로 입력해주세요.", hint=f"{date_type} 형식으로 작성해 주세요")

    return cleaned_date

def validate_month(value: str) -> str:
    cleaned_date = value.strip()
    date_type = "2026-03"

    validate_date(f"{cleaned_date}-01", date_type)

    return cleaned_date

def validate_type(value: str) -> str:
    normalize_data = value.strip().lower()
    options = ("income", "expense")

    if normalize_data not in options:
        raise BudgetAppError(msg=f"{', '.join(options)}중 입력해주세요.", hint=f"{', '.join(options)}")

    return normalize_data

def validate_amount(value: str | int) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        
        data = int(value)
        if data <= 0 :
            raise ValueError

    except ValueError:
        raise BudgetAppError(msg="0보다 큰 양의 정수만 입력해주세요", hint="예) 15000")

    return data

def validate_category_name(value: str) -> str:
    data = value.strip()

    if not data:
        raise BudgetAppError(msg="공백만 작성됐습니다. 카테고리 이름을 입력해주세요.", hint="food")

    return data

def parse_tags(value: str) -> list[str]:
    data = value.split(',')
    data_list = [d.strip() for d in data if d.strip()]

    return data_list
