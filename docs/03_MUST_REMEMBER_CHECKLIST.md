# 프로젝트 총정리: 반드시 기억해야 할 핵심 원리 & 실수 방지 노트

이 문서는 `budget_app` 프로젝트를 직접 구현하며 다룬 **5대 설계 질문에 대한 내 코드 기준 답변**, **구현 중 마주쳤던 파이썬 함정(Gotchas)과 해결 원리**, 그리고 **추가 개선 포인트**를 한눈에 복습할 수 있도록 정리한 핵심 요약본입니다.

---

## 1. 과제 평가 5대 핵심 질문 & 내 코드 기준 답변

과제 제출 후 코드 리뷰나 발표에서 **"왜 이렇게 설계했나요?"**라는 질문을 받았을 때 아래 내용으로 답하면 완벽합니다.

### Q1. 파일 기반 영구 저장을 어떻게 설계했고, 수정/삭제 시 데이터 안전성은 어떻게 지켰나요?
- **저장 포맷 분리**: 한 줄에 하나의 JSON 객체를 저장하는 **JSONL(`.jsonl`)** 포맷을 선택하고, 책임에 따라 `transactions.jsonl`, `categories.jsonl`, `budgets.jsonl` 3개 파일로 분리했습니다.
- **원자적 파일 교체 (Atomic Replace)**: `repositories.py`의 `write_all_jsonl()`에서 원본 파일을 직접 `"w"` 모드로 열지 않습니다. 원본을 바로 열면 쓰기 도중 예외 발생 시 파일이 0바이트로 날아가기 때문에, 같은 디렉토리에 **`.tmp` 임시 파일(`transactions.jsonl.tmp`)**을 먼저 만들어 끝까지 기록한 뒤 `tmp_path.replace(path)`로 **원자적(Atomic) 교체**를 수행했습니다.

### Q2. 왜 모델 / 저장소 / 서비스 / CLI 4계층으로 분리했나요?
- **단일 책임 원칙(SRP)과 의존성 단방향 유지 (`cli -> services -> repositories -> models/validators/errors`)**:
  - `models.py` / `validators.py`: 데이터 구조 계약과 입력값 검증 규칙만 담당합니다.
  - `repositories.py`: 오직 `.jsonl` 파일 읽기/쓰기만 담당하며 `input()`이나 `print()`를 절대 호출하지 않습니다.
  - `services.py`: 카테고리 사용 여부 확인, 검색 조건 필터링, 월별 요약 및 예산 초과율 계산 등 비즈니스 규칙을 담당합니다.
  - `cli.py`: `argparse` 명령 파싱과 콘솔 입출력 포맷팅만 담당합니다.
- **효과**: 나중에 콘솔(`cli.py`)이 아니라 웹이나 GUI로 화면을 바꾸거나, 저장 포맷을 `.jsonl`에서 SQLite DB로 바꾸더라도 다른 계층의 코드를 건드리지 않고 교체할 수 있습니다.

### Q3. 제너레이터(`yield`) 스트리밍은 어디에 적용했고 왜 필요한가요?
- **적용 위치**:
  1. `repositories.py`의 `iter_jsonl(path)`: 파일을 `for line in f:`로 한 줄씩 읽어 `yield json.loads(cleaned)`로 내보냅니다.
  2. `TransactionRepository.iter_all()`: `iter_jsonl`을 받아 `Transaction` 객체를 한 건씩 `yield`합니다.
  3. `services.py`의 `list_transactions()` 및 `search_transactions()`: 조건에 맞는 거래만 `yield tx`로 흘려보냅니다.
- **필요한 이유**: `f.read()`나 `f.readlines()`로 파일 전체를 리스트에 올리면 데이터가 수십만~수백만 건일 때 메모리 부족(`MemoryError`)이 발생합니다. `yield`를 쓰면 **한 시점에 메모리에 거래 객체 1건만 올라가는 스트리밍 파이프라인**이 만들어집니다.

### Q4. 데코레이터(`@handle_errors`)는 어떤 역할을 하며 왜 분리했나요?
- **역할**: `cli.py`의 진입 함수인 `main()`을 감싸서 실행 중 발생하는 `BudgetAppError`와 `KeyboardInterrupt`를 한곳에서 잡아냅니다.
- **장점 (공통 관심사 분리)**:
  - 각 명령어(`add`, `list`, `update`, `delete` 등)마다 `try ... except` 블록을 중복 작성할 필요가 없습니다.
  - 사용자에게 파이썬 스택트레이스(Traceback)를 노출하지 않고 `[오류]`와 `[힌트]` 형식으로 일관되게 출력한 뒤, 비정상 종료 코드 `1`(정상 종료 시 `0`)을 반환하도록 강제합니다.
  - `@functools.wraps(func)`를 사용해 원본 함수의 메타데이터(`__name__`, `__doc__`)를 보존했습니다.

### Q5. `@dataclass(frozen=True)`와 타입 힌트(`typing`)를 써서 얻은 이점은 무엇인가요?
- **명확한 입출력 계약**: 함수 시그니처만 봐도 `str | None`을 받는지, `Iterator[Transaction]`을 반환하는지 명확히 알 수 있어 IDE 자동완성과 정적 타입 검사가 가능해집니다.
- **불변성(`frozen=True`) 보장**: `Transaction`과 `Budget` 인스턴스를 생성한 뒤 중간에 실수로 금액이나 날짜 속성을 덮어쓰는 버그(`tx.amount = -100`)를 원천 차단합니다.

---

## 2. 코딩하며 직접 겪은 파이썬 핵심 디테일 & 실수 방지 노트 (Gotchas)

직접 코드를 짜면서 마주쳤던 중요한 문법 포인트들입니다. 다시 코드를 작성할 때 꼭 기억하세요!

### ① `bool`은 `int`의 자식 클래스다 (`validators.py`)
- 파이썬에서 `isinstance(True, int)`는 `True`이고, `int(True)`는 `1`입니다.
- 따라서 금액 검증 함수 `validate_amount(value)`에서 `int(value)`를 호출하기 전에 **`if isinstance(value, bool): raise ValueError`**로 불리언 값을 먼저 걸러내야 합니다.

### ② Python 3.11+ `date.fromisoformat()`의 함정 (`validators.py`)
- Python 3.11부터 `date.fromisoformat("20261230")`처럼 하이픈(`-`)이 없는 8자리 문자열도 통과됩니다.
- 정확히 `YYYY-MM-DD` 형식만 허용하려면 변환 후 다시 문자열로 바꾼 값과 비교해야 합니다:
  ```python
  if date.fromisoformat(cleaned_date).isoformat() != cleaned_date:
      raise ValueError
  ```

### ③ `@dataclass`에서 리스트 기본값은 반드시 `field(default_factory=list)` (`models.py`)
- `tags: list[str] = []`라고 쓰면 모든 `Transaction` 인스턴스가 똑같은 리스트 객체 하나를 공유하는 대형 버그가 발생합니다(파이썬 데이터클래스는 이를 `ValueError`로 막습니다).
- 인스턴스가 생성될 때마다 새 빈 리스트를 만들도록 `field(default_factory=list)`를 사용해야 합니다.

### ④ 논리 연산자 `and`가 `or`보다 우선순위가 높다 (`services.py`)
- 조건문에서 `A and B or C and D`처럼 쓰거나 괄호를 잘못 묶으면 의도와 전혀 다르게 평가됩니다.
- 시작일(`--from`)과 종료일(`--to`) 중 하나만 입력된 경우를 잡을 때는 아래처럼 괄호로 명확히 묶어야 합니다:
  ```python
  if (valied_from is not None and valied_to is None) or (valied_from is None and valied_to is not None):
      raise BudgetAppError(msg="시작일과 종료일 모두 입력해주세요.")
  ```

### ⑤ 메서드 이름(`to_dict`) vs 메서드 호출(`to_dict()`) (`repositories.py`)
- `items.append(budget.to_dict)`처럼 괄호 `()`를 빼먹으면 딕셔너리 데이터가 아니라 **함수 객체 자체**가 리스트에 들어가서 `json.dumps()`를 할 때 `TypeError: Object of type method is not JSON serializable` 에러가 발생합니다.
- 반드시 `budget.to_dict()`처럼 괄호를 붙여 호출 결과를 넣어야 합니다.

### ⑥ `argparse`에서 `--from` 옵션과 `dest` 설정 (`cli.py`)
- 리눅스 표준 옵션으로 `--from`을 쓰면 `args.from`으로 접근해야 하는데, 파이썬에서 `from`은 문법 예약어(`from ... import ...`)라서 `args.from`이라고 쓰면 `SyntaxError`가 발생합니다.
- 따라서 `add_argument("--from", dest="date_from")`처럼 **`dest`로 저장될 변수 이름을 지정**해 `args.date_from`으로 안전하게 꺼내 써야 합니다.

### ⑦ 왜 `budget` 명령어는 `budget set` 2단계 서브파서로 만들었나? (`cli.py`)
- `category` 명령어가 `category list / add / remove`로 나뉘는 것처럼, `budget`이라는 도메인 아래에 향후 `budget show`, `budget delete` 같은 하위 명령이 확장될 수 있도록 **일관된 계층형 CLI 구조(`command="budget"`, `budget_cmd="set"`)**로 설계한 것입니다.

### ⑧ `raise SystemExit(main())` vs `sys.exit(main())` (`__main__.py`)
- 둘 다 최종적으로 `SystemExit` 예외를 발생시켜 프로세스를 종료하고 운영체제에 종료 코드(`0` 또는 `1`)를 전달하는 동작은 **100% 동일**합니다.
- 하지만 `raise SystemExit(main())`은:
  1. `import sys`를 할 필요가 없는 파이썬 내장 예외입니다.
  2. 코드 흐름상 "여기서 예외를 던져 프로그램을 끝낸다"는 의도가 정적 타입 검사기(mypy 등)와 사람에게 더 명확히 드러납니다.

### ⑨ CSV 파일 입출력 시 `newline=""`과 태그 쉼표 처리 (`services.py`)
- `open(..., newline="")`을 지정하지 않으면 Windows 등에서 줄바꿈(`\r\n`)이 두 번 들어가 빈 줄이 생깁니다.
- `tags`에 `"meal, lunch"`처럼 쉼표가 포함되어 있어도 표준 `csv.DictWriter`와 `csv.DictReader`를 사용하면 자동으로 큰따옴표(`"meal, lunch"`)로 감싸고 해독해 주어 컬럼이 밀리지 않습니다.

---

## 3. 대용량(100k건 수준) 프로파일링 포인트(병목 지점) 및 개선 계획

10만 건(100k) 이상의 데이터를 처리할 때 현재 구조에서 발생하는 **4대 병목 지점**과 **메모리 / 디스크 I/O / CPU별 구체적 개선 방안**입니다.

### 3.1 100k 수준 프로파일링 병목 지점
1. **`list_transactions()`의 `sorted()` (`services.py:77`)**: `sorted(self.transaction_repo.iter_all(), ...)`가 제너레이터 스트림을 깨고 100k 전체를 메모리 리스트로 적재(`O(N)` 메모리, `O(N log N)` CPU)
2. **`next_id()`의 전체 스캔 (`repositories.py:107`)**: 1건 추가(`add`) 시마다 마지막 ID를 찾기 위해 100k 줄 전체를 읽고 `json.loads()` 수행(`O(N)`)
3. **`import_csv()`의 건별 반복 I/O (`services.py:252`)**: 행마다 `category_repo.exists()` + `next_id()` + `append_jsonl()`이 반복 호출되어 `O(N²)` 시간 및 10만 회 파일 `open/close` 발생
4. **`update()` / `delete()`의 리스트 컴프리헨션 (`repositories.py:113, 124`)**: `[item.to_dict() for item in self.iter_all() ...]`가 100k 전체를 메모리에 적재한 뒤 `.tmp` 파일에 기록

### 3.2 메모리 / 디스크 I/O / CPU별 구체적 개선 방안
- **메모리(Memory) 개선 — 역순 읽기(Reverse Reading) & `heapq.nlargest`**:
  - `list --limit N` 실행 시 파일 끝(`os.seek(0, os.SEEK_END)`)에서부터 블록 단위로 **역순 읽기**를 수행하거나, **`heapq.nlargest(limit, iter_all())`**를 사용하여 메모리 사용량을 `O(N)`에서 **`O(K)` (`K = limit`)**로 절감
  - `update`/`delete` 시 리스트 컴프리헨션(`[...]`) 대신 **제너레이터 표현식(`(...)`)**을 `write_all_jsonl()`에 전달하여 `O(1)` 스트리밍 유지
- **디스크 I/O 개선 — 배치 쓰기(Batch Writing) & 월별 파티셔닝**:
  - `import_csv()`에서 건별 `append_jsonl()` 대신 버퍼(예: `5,000`건 단위)를 모아 단일 파일 핸들에서 **`f.writelines()` 배치 쓰기**를 수행하여 파일 I/O 시스템 콜을 10만 회 → 수십 회로 축소
  - 단일 `transactions.jsonl` 대신 `transactions_YYYY-MM.jsonl`로 **월별 파일 분할(Partitioning)** 적용
- **CPU 및 탐색 개선 — 인덱싱(Indexing) & 캐싱**:
  - `tx_id -> byte_offset`을 매핑한 **오프셋 인덱스(`transactions.idx`)**를 구축하고 `f.seek(offset)`으로 즉시 점프하여 100k 전체 `json.loads()` 파싱 비용을 **`O(N)` → `O(1)`**로 제거
  - 마지막 발급 ID를 `meta.json` 또는 파일 마지막 1줄 역순 읽기로 조회해 `next_id()`를 **`O(1)`**화하고, 카테고리는 인메모리 `set[str]`에 캐싱하여 검증 속도를 **`O(1)`**로 최적화
