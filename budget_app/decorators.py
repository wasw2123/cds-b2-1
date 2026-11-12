

from datetime import datetime
from functools import wraps
from pathlib import Path
import time
from typing import Any, Callable, TypeVar

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

T = TypeVar("T")

def timer(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(*args:Any, **kwargs:Any) -> T:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"\n소요 시간: {elapsed_ms:.2f}ms\n")

        return result
    return wrapper

path = Path("./data/app.log")
def logger(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(*args:Any, **kwargs:Any) -> T:
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            result = f"Fail({e})"
            raise
        finally:
            func_name = func.__qualname__
            now = datetime.now().isoformat(timespec="seconds")

            contant = f"[{now}] func: {func_name}, args: {args[1:], kwargs}, result: {result}\n"

            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(contant)

    return wrapper
