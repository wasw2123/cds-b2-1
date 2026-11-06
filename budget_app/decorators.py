

from functools import wraps
from typing import Any, Callable

from budget_app.errors import BudgetAppError


def handle_errors(func: Callable[..., int]) -> Callable[..., int]:
    
    @wraps(func)
    def wrapper(*args: Any, **kwargs:Any) -> int:
        try:
            return func(*args, **kwargs)

        except BudgetAppError as e:
            print(f"[오류] {e.msg}")
            if e.hint:
                print(f"[힌트] {e.hint}")
            return 1

        except KeyboardInterrupt:
            print("키보드 인터럽트에 의한 종료")
            return 1
    
    return wrapper