# 프로젝트를 위해 꼭 알아야 할 파이썬 핵심 개념 가이드

이 문서는 직접 코드를 작성할 때 **"A를 구현하려면 어떤 개념과 표준 라이브러리가 필요한가?"**를 찾아볼 수 있는 개념 사전입니다. 정답 코드 대신 **원리와 미니 힌트**만 담았으니, 읽고 나만의 코드로 응용해 보세요!

---

## 1. 데이터 모델 정의하기: `@dataclass`와 타입 힌트 (`typing`)

### 언제 필요한가요?
거래 내역(`Transaction`), 예산(`Budget`) 같은 데이터를 그냥 딕셔너리(`{"id": "...", "amount": 1000}`)로만 다루면 오타(`"ammount"`)가 나도 실행 전까지 알기 어렵고, 어떤 필드가 있는지 파악하기 힘듭니다.

### 무엇을 쓰나요?
- 표준 라이브러리: `from dataclasses import dataclass, field, asdict`
- 타입 힌트: `from typing import Optional, Iterator, Callable, Any` (Python 3.10+에서는 `list[str]`, `str | None` 표기도 기본 지원됩니다!)

### 핵심 개념 & 힌트
`@dataclass`를 클래스 위에 붙이면 `__init__`, `__repr__`, `__eq__` 메서드를 파이썬이 자동으로 만들어 줍니다.

```python
from dataclasses import dataclass, field

@dataclass
class ItemExample:
    id: str
    amount: int
    memo: str = ""  # 기본값이 있는 필드는 뒤에 배치합니다.
    tags: list[str] = field(default_factory=list)  # 리스트 같은 가변(mutable) 기본값은 default_factory를 씁니다!
```

> **💡 직접 구현할 때 생각해볼 점**:
> - 왜 `tags: list[str] = []`라고 쓰면 안 되고 `field(default_factory=list)`를 써야 할까요? (파이썬에서 기본값 리스트를 여러 인스턴스가 공유해버리는 문제를 막기 위해서입니다.)
> - 객체를 파일에 저장하려면 `dict`로 바꾸는 메서드(예: `to_dict(self) -> dict[str, Any]`)와, 파일에서 읽은 `dict`를 다시 객체로 만드는 클래스 메서드(예: `@classmethod def from_dict(cls, data: dict[str, Any]) -> "Transaction"`)를 직접 만들어 두면 아주 편리합니다.

---

## 2. 예외 처리 설계: 스택트레이스 대신 친절한 에러와 힌트

### 언제 필요한가요?
사용자가 날짜를 `2024-13-40`으로 입력하거나 없는 거래 ID를 삭제하려고 할 때, 파이썬 기본 에러 화면(`Traceback (most recent call last): ...`)이 그대로 뜨면 안 됩니다.

### 무엇을 쓰나요?
- 파이썬 기본 `Exception` 클래스를 상속받은 **나만의 예외 클래스(`errors.py`)**

### 핵심 개념 & 힌트
일반 에러와 달리 **"오류 원인(`message`)"**과 **"해결 힌트(`hint`)"** 두 가지를 담을 수 있는 예외 상자를 만듭니다.

```python
class BudgetAppError(Exception):
    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
```

이렇게 만들어 두면 검증 함수나 서비스 계층 어디서든 문제가 생겼을 때:
```python
raise BudgetAppError(
    message="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).",
    hint="예: 2024-01-15"
)
```
처럼 던지기만(`raise`) 하고, 맨 바깥(CLI 또는 데코레이터)에서 한 번에 잡아서(`try ... except BudgetAppError as e:`) 예쁘게 출력할 수 있습니다.

---

## 3. 입력값 검증하기: 날짜(`datetime`)와 금액/타입

### 언제 필요한가요?
문자열 길이만 검사하면 `2024-02-30`이나 `2024-13-40` 같은 가짜 날짜를 걸러낼 수 없습니다.

### 무엇을 쓰나요?
- 표준 라이브러리: `from datetime import date`
- `date.fromisoformat("2024-01-15")`

### 핵심 개념 & 힌트
- `date.fromisoformat(value)`는 문자열이 정확히 `YYYY-MM-DD` 형식이고 **실제 달력에 존재하는 날짜**일 때만 성공하며, 아니면 `ValueError`를 발생시킵니다!
- 월(`YYYY-MM`) 검증은 어떻게 할까요?
  - 문자열을 `"-"`로 쪼개서 연도(4자리 숫자)와 월(`01`~`12`)을 확인하거나, 뒤에 `"-01"`을 붙여서 `date.fromisoformat(f"{month_str}-01")`로 달력 검증을 재활용하는 아이디어도 있습니다.
- 금액(`amount`) 검증:
  - 문자열로 들어온 입력을 `int(raw_value)`로 바꿀 때 숫자가 아니면 `ValueError`가 납니다. 변환 후 `> 0`인지(양수 정수인지)까지 확인하세요.

---

## 4. 파일 저장 포맷: `JSONL` vs `CSV`와 `pathlib`

### 언제 필요한가요?
프로그램을 껐다 켜도 데이터가 남아 있어야 하고, 한 줄씩 스트리밍으로 읽거나 추가하기 쉬워야 합니다.

### 무엇을 쓰나요?
- 경로 처리: `from pathlib import Path` (`os.path`보다 훨씬 직관적입니다)
- JSON 처리: `import json` (`json.dumps()`, `json.loads()`)

### 왜 내부 저장 포맷으로 `JSONL` (JSON Lines)이 유리할까요?
- 일반 `.json` 파일은 전체가 하나의 거대한 리스트(`[ {...}, {...} ]`)로 묶여 있어서, 데이터 1건을 추가하거나 읽으려 해도 **파일 전체를 처음부터 끝까지 다 읽고 다시 써야** 합니다.
- 반면 **JSONL(`.jsonl`)**은 **한 줄이 곧 독립된 JSON 객체 하나**입니다.
  ```jsonl
  {"id": "TX-000001", "date": "2024-01-14", "type": "income", "category": "salary", "amount": 3000000, "memo": "", "tags": []}
  {"id": "TX-000002", "date": "2024-01-15", "type": "expense", "category": "food", "amount": 15000, "memo": "점심", "tags": ["meal"]}
  ```
- 장점:
  1. 새 거래 추가(`add`) 시 파일 맨 끝에 한 줄만 덧붙이면(`mode="a"`) 끝납니다.
  2. 읽을 때 파일 전체를 메모리에 올리지 않고 **한 줄씩 읽어서 `json.loads(line)`**만 하면 됩니다.
  3. `tags` 같은 리스트 구조도 별도 변환 없이 깔끔하게 저장됩니다 (`ensure_ascii=False` 옵션을 주면 한글 메모도 깨지지 않고 그대로 보입니다).

---

## 5. 제너레이터(`yield`)와 스트리밍 처리

### 언제 필요한가요?
거래 내역이 100만 건일 때 `file.readlines()`로 모든 줄을 리스트에 다 담으면 메모리가 가득 차버립니다. `list`나 `search`, `summary`를 할 때 **메모리에 한 번에 한 건만 올리고 흘려보내는(Streaming)** 방식이 필수 요구사항입니다.

### 무엇을 쓰나요?
- 키워드: `yield`
- 반환 타입 힌트: `from typing import Iterator`

### 핵심 개념 & 힌트
함수 안에 `return` 대신 `yield`가 들어가면 그 함수는 리스트를 반환하는 대신, **달라고 할 때마다(`next()` 또는 `for`문) 하나씩 값을 만들어 내어주는 제너레이터(Generator)**가 됩니다.

```python
from pathlib import Path
from typing import Iterator
import json

def iter_records(file_path: Path) -> Iterator[dict]:
    if not file_path.exists():
        return  # 파일이 없으면 아무것도 yield하지 않고 종료

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:  # 파일 객체 f를 직접 순회하면 한 줄씩만 메모리로 읽습니다!
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)  # 한 줄을 변환해 내보내고, 다음 요청이 올 때까지 일시정지!
```

> **💡 직접 구현할 때 생각해볼 점**:
> - `search` 기능도 이 제너레이터를 받아서 조건(`--category`, `--from` 등)이 맞는 것만 다시 `yield`하면, 파일 읽기부터 검색 결과 출력까지 단 한 번도 전체 리스트를 메모리에 만들지 않고 파이프라인처럼 연결할 수 있습니다!
> - **최신순 정렬 고민**: `list`와 `search`는 최신순으로 출력해야 합니다. 스트리밍을 유지하면서 최신순으로 보여주려면 어떻게 설계할 수 있을까요? (예: 파일에 저장할 때부터 최신순 순서를 유지하도록 넣거나, 파일 역방향 읽기/정렬 전략을 세우는 방법 등이 있습니다. 함께 이야기하며 방식을 정해봐요!)

---

## 6. 안전한 파일 수정/삭제: 임시 파일과 원자적 교체 (Atomic Replace)

### 언제 필요한가요?
파일의 중간에 있는 특정 거래(`id=TX-000005`)를 수정(`update`)하거나 삭제(`delete`)할 때, 원본 파일을 곧바로 `"w"` 모드로 열어서 덮어쓰다가 중간에 에러가 나거나 전원이 꺼지면 **기존 가계부 데이터가 0바이트로 전부 날아갑니다!**

### 무엇을 쓰나요?
- 표준 라이브러리: `import tempfile`, `import os`
- 핵심 함수: `tempfile.NamedTemporaryFile(...)`, `os.replace(temp_path, original_path)`

### 핵심 개념 & 힌트
1. 원본 파일과 **같은 폴더(`dir=file_path.parent`)**에 임시 파일을 만듭니다.
2. 원본 파일을 제너레이터로 한 줄씩 읽으면서, 수정/삭제가 반영된 내용을 **임시 파일에** 다 씁니다.
3. 임시 파일 쓰기가 끝까지 무사히 성공했을 때만 `os.replace(임시파일경로, 원본파일경로)`를 호출해 이름표를 한 번에 바꿔치기합니다.
4. 만약 중간에 에러가 나면? 원본 파일은 손대지 않았으니 100% 안전합니다!

---

## 7. 데코레이터(`@decorator`)로 공통 관심사 분리하기

### 언제 필요한가요?
모든 CLI 명령 함수마다 똑같이 `try ... except BudgetAppError ...`를 쓰거나, 함수 실행 전후에 걸린 시간을 재고 로그를 남기는 코드를 매번 복붙하면 비즈니스 로직이 지저분해집니다.

### 무엇을 쓰나요?
- 표준 라이브러리: `from functools import wraps`, `import time`

### 핵심 개념 & 힌트
데코레이터는 **"함수를 받아서, 앞뒤로 부가 기능을 덧붙인 새 함수를 돌려주는 포장지 함수"**입니다.

```python
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

def handle_cli_errors(func: Callable[P, int]) -> Callable[P, int]:
    @wraps(func)  # 원래 함수의 이름(__name__)과 독스트링(__doc__)을 보존해 줍니다.
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return func(*args, **kwargs)
        except BudgetAppError as e:
            # 여기서 [오류] e.message 와 [힌트] e.hint 를 출력하고
            return 1  # 비정상 종료 코드 반환!
    return wrapper
```

이렇게 만들어 두고 실행 함수 위에 `@handle_cli_errors` 한 줄만 붙이면, 스택트레이스 방지와 종료 코드 처리가 깔끔하게 분리됩니다.

---

## 8. CLI 파싱(`argparse`)과 CSV 입출력(`csv`)

### 8.1 `argparse`로 하위 명령어(`subparsers`) 만들기
`python -m budget_app summary --month 2024-01 --top 3`나 `python -m budget_app budget set ...` 같은 구조는 `argparse`의 **서브파서(Subparsers)**로 만듭니다.

- 필요한 도구: `import argparse`
- 핵심 흐름:
  1. 최상위 파서 생성: `parser = argparse.ArgumentParser(prog="budget_app", description="...")`
  2. 공통 옵션 추가: `parser.add_argument("--data-dir", default="./data", ...)`
  3. 하위 명령 분기점 생성: `subparsers = parser.add_subparsers(dest="command", required=True)`
  4. 각 명령별 파서 등록:
     - `add_parser = subparsers.add_parser("add", help="거래 내역 추가")`
     - `list_parser = subparsers.add_parser("list", help="거래 목록 조회")`
     - `list_parser.add_argument("--limit", type=int, default=10, help="출력할 최대 건수")`
  5. `budget set`이나 `category add/list/remove`처럼 2단계 명령어는?
     - `budget_parser`에 한 번 더 `add_subparsers()`를 달아주거나 위치 인자를 활용할 수 있습니다!

### 8.2 `csv` 모듈로 태그(쉼표 포함) 안전하게 다루기
CSV는 쉼표(`,`)로 열을 구분하는데, `tags` 컬럼 안에도 `"meal,friend"`처럼 쉼표가 들어갑니다.
직접 `line.split(",")`이나 문자열 합치기로 CSV를 다루면 태그의 쉼표 때문에 열이 깨집니다!

- 필요한 도구: `import csv` (`csv.DictReader`, `csv.DictWriter`)
- 핵심 원리: 표준 `csv` 모듈을 쓰면 값 안에 쉼표(`,`)가 들어있을 때 자동으로 큰따옴표(`"meal,friend"`)로 감싸서 저장하고, 읽을 때도 하나의 컬럼으로 정확히 묶어서 읽어줍니다.
  - 파일을 열 때는 반드시 `open(path, "w", encoding="utf-8", newline="")`처럼 `newline=""` 옵션을 주어야 줄바꿈이 두 번 들어가는 현상을 막을 수 있습니다.
