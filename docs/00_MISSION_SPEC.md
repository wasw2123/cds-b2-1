# 나만의 용돈 기입장 (`budget_app`) — 과제 명세서

- **분야**: AI/SW 기초
- **구분**: Python과 Git 심화
- **학습시간**: 60시간 (필수)

---

## 1. 미션 소개

> **'작은 서비스'란 기능이 많은 게 아니라 예외 상황에서도 데이터가 안전한 것을 말합니다.**

이번 미션은 Python으로 파일 입출력 기반의 콘솔 가계부(`budget_app`)를 구현하는 과제입니다.
수입과 지출 내역을 단순히 저장하는 수준을 넘어 **수정/삭제, 검색, 월별 요약, 카테고리 관리, 예산 초과 경고**까지 포함한 "작은 서비스" 형태로 완성합니다.

### 핵심 설계 포인트
- **영구 저장**: 프로그램 종료 후에도 유지되도록 파일(JSONL 또는 CSV)에 3개 이상 분리 저장 (`transactions`, `categories`, `budgets`)
- **제너레이터 스트리밍**: 저장 파일을 한 번에 메모리에 모두 읽지 않고 `yield` 제너레이터로 한 줄씩 스트리밍 처리
- **데코레이터 분리**: 공통 관심사(예외 처리, 실행 로그, 실행 시간 측정 등)를 데코레이터로 분리
- **타입 힌트와 데이터 계약**: `@dataclass`와 타입 힌트(`typing`)를 적용해 함수와 데이터 구조의 계약을 명확히 정의
- **모듈 분리**: 모델 / 저장소 / 서비스 / CLI 등 책임별로 모듈을 나누어 유지보수 가능한 구조 설계

---

## 2. 학습 목표 (스스로 설명할 수 있어야 하는 5가지)

과제를 마친 후 아래 질문에 내 코드 예시를 들어 답할 수 있어야 합니다.

1. **파일 기반 영구 저장과 CRUD**: 파일(JSONL/CSV)로 데이터를 영구 저장하고, 추가/조회/수정/삭제/검색/요약/입출력을 어떻게 구현했는가? (특히 수정/삭제 시 파일 안전성을 어떻게 지켰는가?)
2. **계층 구조와 책임 분리**: 모델(Model), 저장소(Repository), 서비스(Service), CLI 각 계층은 어떤 책임을 가지며 왜 분리했는가?
3. **제너레이터 스트리밍(`yield`)**: 대용량 파일도 `read()`나 `readlines()` 없이 스트리밍 처리하는 이유와 동작 원리는 무엇인가?
4. **데코레이터(`@decorator`)**: 공통 관심사(로그/예외 처리/시간 측정)를 데코레이터로 분리한 구조와 장점은 무엇인가?
5. **타입 힌트(`typing`)**: 타입 힌트를 통해 입출력 계약을 명확히 했을 때 얻는 이점은 무엇인가?

---

## 3. 10대 필수 기능 요약

| 번호 | 명령어 | 입력 / 옵션 | 출력 및 핵심 동작 | 완료 여부 |
| :--- | :--- | :--- | :--- | :---: |
| 1 | **`add`** | 대화형 입력 (`날짜`, `타입`, `카테고리`, `금액`, `메모`, `태그`) | 등록된 카테고리 검증, 저장 성공 메시지 + 생성된 거래 `id` 출력 | [x] |
| 2 | **`list`** | `--limit N` (기본값 제공) | 최신순 거래 리스트 출력 (**제너레이터 스트리밍 처리 필수**) | [x] |
| 3 | **`search`** | `--from`, `--to`, `--category`, `--type`, `--q`, `--tag` | 조건에 맞는 거래 리스트 최신순 출력 (**스트리밍 유지**) | [x] |
| 4 | **`summary`** | `--month YYYY-MM`, `--top N` | 총수입/총지출/잔액 + 카테고리별 지출 TOP N + 데이터 없는 달 안내 | [x] |
| 5 | **`budget`** | `budget set --month YYYY-MM --amount 금액` (및 조회) | 월 예산 영구 저장 + `summary` 실행 시 예산 사용률(%) 및 초과 경고 출력 | [x] |
| 6 | **`category`** | `category add`, `category list`, `category remove` | 카테고리 목록/추가/삭제 (사용 중인 카테고리 삭제 시 차단 또는 대체 요구) | [x] |
| 7 | **`update`** | `--id <id>` 기반 (옵션 방식 또는 대화형 중 택1하여 문서 고정) | 수정 성공/실패 메시지 출력 (존재하지 않는 `id` 안내 포함, 안전한 재작성) | [x] |
| 8 | **`delete`** | `delete --id <id>` | 삭제 성공/실패 메시지 출력 (존재하지 않는 `id` 안내 포함, 안전한 재작성) | [x] |
| 9 | **`import`** | `import --from <csv>` | CSV 파일에서 거래 일괄 등록 (행 검증 및 처리/스킵 건수 출력) | [x] |
| 10 | **`export`** | `export --out <csv>` + (`--month` 또는 `--from`/`--to` 필수) | 조건에 맞는 거래를 CSV로 내보내기 + 처리 건수 출력 | [x] |

---

## 4. 상세 기능 요구사항

### 4.1 실행 및 입력 방식
- **실행 명령**: `python -m budget_app <command> [options]`
- **도움말**: 모든 명령은 `--help` 옵션으로 사용 방법이 출력되어야 함
- **기본 입력 방식**: 대화형(`input()`)을 기본으로 하되, `search`, `list`, `summary`, `export`, `import`, `delete`는 옵션 인자 방식 허용(권장)
- **`update` 방식 고정**: 아래 두 방식 중 하나를 선택하여 `README.md`에 명확히 고정
  - **(안 A) 옵션 기반**: `update --id <id> [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]`
  - **(안 B) 대화형 기반**: 수정할 필드만 선택/재입력 받는 흐름
- **옵션 표기 통일**: 리눅스 표준인 `--`로 통일 (`--help`, `--limit`, `--from`, `--to`, `--month`, `--data-dir` 등)

### 4.2 데이터 모델 및 클래스
- `Transaction` 데이터 모델은 `@dataclass` 또는 그에 준하는 구조로 정의하며 최소 다음 필드를 포함:
  - `id`: 유일한 식별자 (예: `TX-000012` 또는 UUID 기반)
  - `type`: `income` 또는 `expense`
  - `date`: `YYYY-MM-DD`
  - `amount`: 양수 정수 (`int`)
  - `category`: 등록된 카테고리 문자열
  - `memo`: 문자열 (선택)
  - `tags`: 태그 목록 또는 문자열 (선택)
- 최소 2개 이상의 클래스를 정의하여 사용 (예: `Transaction`, `TransactionRepository`, `BudgetStore`, `CategoryStore`, `BudgetService` 등)

### 4.3 입력 검증 (Validation)
- 날짜 형식 오류(`YYYY-MM-DD`가 아니거나 `2024-13-40` 같은 불가능한 날짜)
- 음수 또는 0원 금액, 정수가 아닌 금액
- 허용되지 않은 `type` (`income`, `expense` 외의 값)
- 존재하지 않는 `category`
- 위 오류 발생 시 **재입력을 요구하거나 원인 + 해결 힌트 오류 메시지를 출력**해야 함

### 4.4 저장 정책 및 초기 실행
- **포맷**: `JSONL` 또는 `CSV` 중 1개 선택
- **파일 분리 (3개 이상 필수)**:
  - `transactions.<fmt>`
  - `categories.<fmt>`
  - `budgets.<fmt>`
- **기본 저장 폴더**: `./data` 권장 (`--data-dir` 옵션으로 변경 가능해야 함)
- **초기 실행 처리**:
  - 저장 폴더나 파일이 없으면 자동 생성하거나 초기화 안내 메시지 출력
  - 카테고리 파일이 비어 있을 때 아래 중 택1:
    - **(안 A)** 기본 카테고리 자동 생성 (예: `food`, `transport`, `rent`, `salary` 등)
    - **(안 B)** `category add`를 먼저 하도록 안내하고 거래 추가(`add`)를 막음

### 4.5 CSV 가져오기 / 내보내기 (`import` / `export`) 스키마
- 공통 규칙: **UTF-8 인코딩, 첫 줄 헤더 포함**
- 컬럼 순서 및 정의:

| column | required | 설명 |
| :--- | :---: | :--- |
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` / `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 양수 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표(`,`)로 구분된 문자열 |

### 4.6 데코레이터, 예외 처리, 모듈화, 문서화
- **데코레이터**: 예외 처리 / 로그 / 실행 시간 측정 등 공통 관심사 데코레이터를 1개 이상 직접 구현하고 실제 함수/메서드에 적용
- **예외 처리 및 종료 코드**:
  - 스택트레이스(Traceback) 출력 금지 -> `[오류] 원인` + `[힌트] 해결 방법` 출력
  - 정상 종료는 `0`, 오류 종료는 `0이 아닌 값`으로 종료
- **모듈화**: 한 파일에 몰아넣지 않고 최소 3개 이상 모듈로 분리 (CLI / 서비스 / 저장소 / 모델 등)
- **`README.md` 필수 포함 내용**:
  1. 프로그램 실행 방법
  2. 저장 파일 위치 및 형식
  3. 주요 명령어 사용 예시
  4. `import` / `export` CSV 스키마 설명

---

## 5. 보너스 과제 (필수 기능 완성 후 도전)

1. **백업 기능 (`backup`)**: 타임스탬프가 포함된 백업 파일 생성 (복구 가능성 확보)
2. **반복 내역 기능**: 월급/월세처럼 반복되는 내역 규칙을 등록하고 특정 월에 자동 생성
3. **출력 포맷 테이블 정렬**: 외부 라이브러리 없이 문자열 폭 정렬로 콘솔 가독성 개선
4. **저장 원자성 강화**: `update`/`delete` 시 임시 파일에 먼저 쓰고 `os.replace`(`rename`)로 원자적 교체

---

## 6. 입출력 참고 예시

### `add` (거래 추가)
```text
$ python -m budget_app add
날짜(YYYY-MM-DD): 2024-01-15
타입(income/expense): expense
카테고리: food
금액(양수): 15000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): meal
[저장 완료] id=TX-000012
```

### `list` (거래 목록)
```text
$ python -m budget_app list --limit 3
TX-000012 | 2024-01-15 | expense | food | 15000 | 점심
TX-000011 | 2024-01-14 | income  | salary | 3000000 |
TX-000010 | 2024-01-12 | expense | transport | 20000 |
```

### `category` (카테고리 관리)
```text
$ python -m budget_app category add
카테고리명: food
[저장 완료] category=food

$ python -m budget_app category list
- food
- transport
```

### `budget` + `summary` (예산 설정 및 월별 요약)
```text
$ python -m budget_app budget set --month 2024-01 --amount 500000
[저장 완료] 2024-01 예산 500000원

$ python -m budget_app summary --month 2024-01 --top 3
총 수입: 3000000원
총 지출: 215000원
잔액: 2785000원
예산: 500000원 (사용률 43.0%)

지출 TOP 3
1) rent 150000원
2) food 45000원
3) transport 20000원
```

### `export` / `import` (CSV 내보내기/가져오기)
```text
$ python -m budget_app export --out export.csv --month 2024-01
[완료] export.csv (12 records)

$ python -m budget_app import --from import.csv
[완료] imported=5, skipped=0
```

### 오류 출력 예시
```text
$ python -m budget_app add
날짜(YYYY-MM-DD): 2024-13-40
[오류] 날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).
[힌트] 예: 2024-01-15
```
