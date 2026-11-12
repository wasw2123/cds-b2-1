# 나만의 용돈 기입장 (`budget_app`)

Python 표준 라이브러리만을 사용하여 구현한 **파일 입출력 기반 콘솔 가계부 서비스**입니다.
단순한 내역 기록을 넘어 **제너레이터(`yield`) 기반 스트리밍 처리**, **데코레이터(`@handle_errors`)를 통한 공통 예외 처리 분리**, **`@dataclass`와 타입 힌트(`typing`) 기반의 데이터 계약**, 그리고 **임시 파일(`.tmp`)을 활용한 원자적(Atomic) 파일 교체**까지 안전한 소규모 서비스 구조로 설계되었습니다.

---

## 1. 개발 환경 및 실행 방법

### 1.1 환경 요구사항
- **Python**: 3.10 이상 (표준 라이브러리만 사용, 외부 서드파티 패키지 의존성 없음)

### 1.2 기본 실행 명령어
프로젝트 루트 디렉토리에서 아래 명령어로 실행합니다.

```bash
python -m budget_app <command> [options]

# 가상환경(.venv) 또는 uv 사용 시:
.venv/bin/python -m budget_app <command> [options]
```

### 1.3 도움말 확인 (`--help`)
모든 명령어와 하위 명령어는 `--help` 옵션을 지원합니다.
```bash
python -m budget_app --help
python -m budget_app search --help
python -m budget_app update --help
```

### 1.4 데이터 저장 경로 변경 옵션 (`--data-dir`)
기본 저장 경로는 `./data`이며, 실행 시 `--data-dir` 옵션으로 저장 폴더를 변경할 수 있습니다.
```bash
python -m budget_app --data-dir ./my_data list --limit 5
```

---

## 2. 모듈 구조 및 계층별 책임

```text
budget_app/
├── __init__.py       # 패키지 초기화
├── __main__.py       # 패키지 실행 진입점 (종료 코드 반환)
├── errors.py         # 사용자 정의 예외 클래스 (BudgetAppError: 오류 메시지 + 힌트)
├── validators.py     # 입력값 검증 함수 (날짜, 월, 거래 타입, 양수 금액, 카테고리, 태그)
├── models.py         # 불변 데이터 모델 (@dataclass(frozen=True): Transaction, Budget)
├── repositories.py   # JSONL 파일 I/O, yield 제너레이터 스트리밍 읽기, 원자적 파일 쓰기
├── services.py       # 비즈니스 로직 (CRUD, 조건 검색, 월별 요약, 예산 비교, CSV 입출력)
├── decorators.py     # 공통 관심사 데코레이터 분리 (@handle_errors: 예외 처리, @timer: 실행 시간 측정, @logger: 실행 로깅)
└── cli.py            # argparse 명령어 파싱, 대화형 입력, 콘솔 출력 포맷팅
```

---

## 3. 저장 파일 위치 및 형식

### 3.1 저장 위치 및 포맷
- **기본 폴더**: `./data/` (폴더가 없으면 실행 시 자동 생성)
- **저장 포맷**: **JSONL (`.jsonl`, UTF-8 인코딩)** — 한 줄에 하나의 JSON 객체를 저장하여 대용량 파일도 한 줄씩 스트리밍(`yield`) 처리 가능
- **분리된 3개 저장 파일**:
  1. `./data/transactions.jsonl`: 거래 내역 (`id`, `type`, `date`, `amount`, `category`, `memo`, `tags`)
  2. `./data/categories.jsonl`: 등록된 카테고리 목록 (`name`)
  3. `./data/budgets.jsonl`: 월별 예산 설정 데이터 (`month`, `amount`)

### 3.2 주요 저장 정책
- **초기 카테고리 정책 (안 A 채택)**: `categories.jsonl` 파일이 없거나 비어 있을 때 기본 카테고리 5종(`food`, `transport`, `rent`, `salary`, `etc`)을 자동으로 초기화합니다.
- **원자적 파일 교체 (Atomic Replace)**: 수정(`update`)이나 삭제(`delete`) 시 원본 파일을 직접 열지 않고 `.tmp` 임시 파일에 먼저 기록한 뒤 `Path.replace()`로 교체하여 예외 상황에서도 데이터 유실을 방지합니다.
- **CSV 임포트 롤백 정책 및 상세 오류 리포트**:
  - 임포트 전 기존 거래 내역의 스냅샷(`snapshot`)을 생성하여, 파일 손상(`csv.Error`, `UnicodeDecodeError`)이나 엄격 모드(`--rollback-on-error`)에서 오류 행이 발생하면 즉시 임포트 이전 상태로 **트랜잭션 전체 롤백(Rollback)**을 수행합니다.
  - 기본 모드(부분 임포트)에서는 정상 행만 반영하고, 건너뛴 행의 번호(`line_no`)와 구체적인 실패 사유를 `[스킵 이유]` 리포트로 출력합니다.

---

## 4. 주요 명령어 요약 (10대 기능)

| 기능 | 명령어 형식 |
| :--- | :--- |
| **1. 거래 추가 (`add`)** | `python -m budget_app add` (대화형 입력) |
| **2. 거래 목록 (`list`)** | `python -m budget_app list [--limit N]` |
| **3. 거래 검색 (`search`)** | `python -m budget_app search [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--category CAT] [--type TYPE] [--q KEYWORD] [--tag TAG]` |
| **4. 월별 요약 (`summary`)** | `python -m budget_app summary --month YYYY-MM [--top N]` |
| **5. 예산 설정 (`budget`)** | `python -m budget_app budget set --month YYYY-MM --amount AMOUNT` |
| **6. 카테고리 관리 (`category`)** | `python -m budget_app category {list,add,remove}` |
| **7. 거래 수정 (`update` — 옵션 방식 고정)** | `python -m budget_app update --id ID [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]` |
| **8. 거래 삭제 (`delete`)** | `python -m budget_app delete --id ID` |
| **9. CSV 내보내기 (`export`)** | `python -m budget_app export --out FILE.csv [--month YYYY-MM] [--from YYYY-MM-DD] [--to YYYY-MM-DD]` |
| **10. CSV 가져오기 (`import`)** | `python -m budget_app import --from FILE.csv [--rollback-on-error]` |

---

## 5. `import` / `export` CSV 스키마

- **인코딩**: `UTF-8`
- **첫 줄 헤더**: 필수 포함 (`date,type,category,amount,memo,tags`)

| 컬럼명 (`column`) | 필수 여부 (`required`) | 설명 | 예시 |
| :--- | :---: | :--- | :--- |
| `date` | Y | 거래 날짜 (`YYYY-MM-DD`) | `2024-01-15` |
| `type` | Y | 수입 / 지출 구분 (`income` / `expense`) | `expense` |
| `category` | Y | 등록된 카테고리 이름 | `food` |
| `amount` | Y | 양의 정수 금액 | `15000` |
| `memo` | N | 메모 문자열 (없으면 빈칸) | `점심` |
| `tags` | N | 쉼표(`,`)로 구분된 태그 문자열 | `"meal, friend"` |

---

## 6. 전체 명령어 실행 및 출력 결과 시연

### ① 도움말 확인 (`--help`)

**실행 명령어:**
```bash
python -m budget_app --help
```

**출력 결과:**
```text
usage: budget_app [-h] [--data-dir DATA_DIR]
                  {add,list,category,delete,update,search,summary,budget,export,import} ...

나만의 용돈 기입장

positional arguments:
  {add,list,category,delete,update,search,summary,budget,export,import}
    add                 거래 내역 추가
    list                거래 목록 조회
    category            카테고리 관리
    delete              거래내역 삭제
    update              거래내역 수정
    search              거래내역 검색
    summary             월별 요약
    budget              예산 관리
    export              csv 내보내기
    import              csv 가져오기

options:
  -h, --help            show this help message and exit
  --data-dir DATA_DIR   데이터 저장 폴더 경로
```

---

### ② 카테고리 관리 (`category list / add / remove`)

**실행 명령어 (목록 조회):**
```bash
python -m budget_app category list
```

**출력 결과:**
```text
- food
- transport
- rent
- salary
- etc
- cafe
- shopping
- culture
```

**실행 명령어 (카테고리 추가):**
```bash
python -m budget_app category add
```

**입력 및 출력 결과:**
```text
카테고리 이름: book
[저장 완료] category = book
```

**실행 명령어 (카테고리 삭제):**
```bash
python -m budget_app category remove
```

**입력 및 출력 결과:**
```text
삭제할 카테고리 이름: book
[카테고리 삭제 완료]
```

---

### ③ 거래 추가 (`add`)

**실행 명령어:**
```bash
python -m budget_app add
```

**입력 및 출력 결과:**
```text
날짜: 2026-11-06
타입(income, expense): expense
카테고리(food. transport. rent. salary. etc. cafe. shopping. culture): food
금액: 42000
메모(선택): 저녁 치킨 배달
태그(선택, 여러개 입력 시 ,(콤마)로 구분합니다.): meal, dinner, friend
[저장 완료] id=TX-000015
```

---

### ④ 거래 목록 조회 (`list --limit N`)

**실행 명령어:**
```bash
python -m budget_app list --limit 5
```

**출력 결과:**
```text
TX-000015 | 2026-11-06 | expense | food | 42000 | 저녁 치킨 배달 | meal, dinner, friend
TX-000014 | 2026-11-05 | expense | culture | 30000 | 주말 영화 관람 및 팝콘 | movie, friend
TX-000013 | 2026-11-05 | expense | shopping | 120000 | 무선 키보드 구매 | gear, study
TX-000012 | 2026-11-04 | expense | cafe | 5800 | 카페라떼 | coffee
TX-000011 | 2026-11-03 | expense | food | 16000 | 점심 돈까스 | meal, lunch
```

---

### ⑤ 거래 조건 검색 (`search`)

**1) 카테고리(`--category`) + 태그(`--tag`) 조합 검색 명령어:**
```bash
python -m budget_app search --category food --tag friend
```

**출력 결과:**
```text
TX-000015 | 2026-11-06 | expense | food | 42000 | 저녁 치킨 배달 | meal, dinner, friend
TX-000006 | 2026-10-25 | expense | food | 38000 | 저녁 삼겹살 모임 | meal, dinner, friend
```

**2) 기간(`--from`, `--to`) + 메모 키워드(`--q`) 검색 명령어:**
```bash
python -m budget_app search --from 2026-10-01 --to 2026-11-06 --q 점심
```

**출력 결과:**
```text
TX-000011 | 2026-11-03 | expense | food | 16000 | 점심 돈까스 | meal, lunch
TX-000003 | 2026-10-15 | expense | food | 14000 | 점심 김치찌개 | meal, lunch
```

**3) 거래 타입(`--type`) 검색 명령어:**
```bash
python -m budget_app search --type income
```

**출력 결과:**
```text
TX-000009 | 2026-11-02 | income | etc | 150000 | 중고 거래 판매 수익 | side, bonus
TX-000008 | 2026-11-01 | income | salary | 3200000 | 11월 정기 급여 | work, monthly
TX-000001 | 2026-10-10 | income | salary | 3200000 | 10월 정기 급여 | work, monthly
```

---

### ⑥ 예산 설정 (`budget set`) 및 월별 요약 (`summary`)

**1) 월별 예산 설정 명령어:**
```bash
python -m budget_app budget set --month 2026-10 --amount 1000000
python -m budget_app budget set --month 2026-11 --amount 600000
```

**출력 결과:**
```text
[예산 설정 완료] 2026년 10월 예산 1,000,000원
[예산 설정 완료] 2026년 11월 예산 600,000원
```

**2) 10월 요약 조회 (예산 이내인 달) 명령어:**
```bash
python -m budget_app summary --month 2026-10 --top 3
```

**출력 결과:**
```text
[거래 내역] 7건
[총 수입] 3,200,000원
[총 지출] 652,500원
[잔액] 2,547,500원
[상위 지출처 1] rent: 450,000원
[상위 지출처 2] shopping: 89,000원
[상위 지출처 3] transport: 55,000원
[예산] 1,000,000원
[예산 한도] 65.25%
[예산 초과 여부] 예산이 남았습니다.
```

**3) 11월 요약 조회 (예산 초과인 달) 명령어:**
```bash
python -m budget_app summary --month 2026-11 --top 3
```

**출력 결과:**
```text
[거래 내역] 8건
[총 수입] 3,350,000원
[총 지출] 663,800원
[잔액] 2,686,200원
[상위 지출처 1] rent: 450,000원
[상위 지출처 2] shopping: 120,000원
[상위 지출처 3] food: 58,000원
[예산] 600,000원
[예산 한도] 110.63%
[예산 초과 여부] 예산을 초과하였습니다.
```

**4) 거래 데이터가 없는 달 조회 명령어:**
```bash
python -m budget_app summary --month 2026-01
```

**출력 결과:**
```text
[데이터 없음]
```

---

### ⑦ 거래 수정 (`update`) 및 거래 삭제 (`delete`)

**1) 거래 수정 명령어 (옵션 방식):**
```bash
python -m budget_app update --id TX-000012 --amount 6300 --memo "바닐라 라떼"
```

**출력 결과:**
```text
[수정 완료] id=TX-000012
```

**2) 거래 삭제 명령어:**
```bash
python -m budget_app delete --id TX-000012
```

**출력 결과:**
```text
[삭제 완료]
```

---

### ⑧ CSV 내보내기 (`export`) 및 가져오기 (`import`)

**1) CSV 내보내기 명령어:**
```bash
python -m budget_app export --out ./data/november_export.csv --month 2026-11
```

**출력 결과:**
```text
[csv 내보내기 완료] ./data/november_export.csv (8 건)
```

**2) CSV 가져오기 명령어:**
```bash
python -m budget_app import --from ./data/sample_import.csv
```

**출력 결과:**
```text
[csv 가져오기 완료] imported=3, skipped=0
```

---

### ⑨ 실패 케이스 및 예외 처리 시연 (`@handle_errors`, 종료 코드 `1`)

모든 예외 상황에서 스택트레이스(Traceback)를 숨기고 `[오류]`와 `[힌트]`를 출력한 뒤 종료 코드 `1`을 반환합니다.

---

#### 9-1. 입력값 형식 검증 실패 (`validators.py`)

**1) 잘못된 날짜 형식 (`YYYY-MM-DD` 위반):**
```bash
python -m budget_app search --from 2026-13-40 --to 2026-12-31
```
**출력 결과:**
```text
[오류] 날짜 형식이 올바르지 않습니다. 2026-12-30 형식으로 입력해주세요.
[힌트] 2026-12-30 형식으로 작성해 주세요
```

**2) 잘못된 월 형식 (`YYYY-MM` 위반):**
```bash
python -m budget_app summary --month 2026-15
```
**출력 결과:**
```text
[오류] 날짜 형식이 올바르지 않습니다. 2026-03 형식으로 입력해주세요.
[힌트] 2026-03 형식으로 작성해 주세요
```

**3) 잘못된 거래 타입 입력 (`income`, `expense` 이외):**
```bash
python -m budget_app search --type saving
```
**출력 결과:**
```text
[오류] income, expense중 입력해주세요.
[힌트] income, expense
```

**4) 0 이하 또는 숫자가 아닌 금액 입력:**
```bash
python -m budget_app budget set --month 2026-11 --amount -5000
```
**출력 결과:**
```text
[오류] 0보다 큰 양의 정수만 입력해주세요
[힌트] 예) 15000
```

**5) 공백만 있는 카테고리 이름 입력:**
```bash
python -m budget_app category add
```
**입력 및 출력 결과:**
```text
카테고리 이름:    
[오류] 공백만 작성됐습니다. 카테고리 이름을 입력해주세요.
[힌트] food
```

---

#### 9-2. 카테고리 관리 실패 (`category`)

**1) 이미 존재하는 카테고리 중복 추가:**
```bash
python -m budget_app category add
```
**입력 및 출력 결과:**
```text
카테고리 이름: food
[오류] 중복되는 카테고리가 존재합니다.
[힌트] food, transport, rent, salary, etc, cafe, shopping, culture제외하고 입력해주세요.
```

**2) 존재하지 않는 카테고리 삭제 시도:**
```bash
python -m budget_app category remove
```
**입력 및 출력 결과:**
```text
삭제할 카테고리 이름: unknown
[오류] 카테고리가 존재하지 않습니다.
[힌트] food, transport, rent, salary, etc, cafe, shopping, culture내에서 입력해주세요.
```

**3) 거래 내역에서 사용 중인 카테고리 삭제 시도:**
```bash
python -m budget_app category remove
```
**입력 및 출력 결과:**
```text
삭제할 카테고리 이름: food
[오류] 거래내역에서 사용중인 카테고리입니다.
```

---

#### 9-3. 거래 추가 / 수정 / 삭제 실패 (`add`, `update`, `delete`)

**1) 미등록 카테고리로 거래 추가/수정 시도:**
```bash
python -m budget_app update --id TX-000001 --category travel
```
**출력 결과:**
```text
[오류] 카테고리가 등록돼 있지 않습니다.
[힌트] 현재 등록된 카테고리 목록입니다. [food. transport. rent. salary. etc. cafe. shopping. culture]
```

**2) 존재하지 않는 거래 ID 수정 시도:**
```bash
python -m budget_app update --id TX-999999 --amount 10000
```
**출력 결과:**
```text
[오류] 수정할 거래내역이 존재하지 않습니다. 거래내역 아이디를 확인해주세요.
```

**3) 변경할 옵션 없이 `update` 실행:**
```bash
python -m budget_app update --id TX-000001
```
**출력 결과:**
```text
[오류] 수정할 사항을 입력해주세요.
```

**4) 존재하지 않는 거래 ID 삭제 시도:**
```bash
python -m budget_app delete --id TX-999999
```
**출력 결과:**
```text
[오류] 일치하는 거래내역이 존재하지 않습니다.
```

---

#### 9-4. 조회 / 검색 / 요약 조건 실패 (`list`, `search`, `summary`)

**1) `list --limit`에 0 이하의 값 입력:**
```bash
python -m budget_app list --limit 0
```
**출력 결과:**
```text
[오류] 1이상의 양의 정수를 입력해 주세요
[힌트] 5
```

**2) `search`에서 시작일(`--from`)만 입력하고 종료일(`--to`) 누락:**
```bash
python -m budget_app search --from 2026-10-01
```
**출력 결과:**
```text
[오류] 시작일과 종료일 모두 입력해주세요.
```

**3) `search`에서 시작일이 종료일보다 늦은 경우:**
```bash
python -m budget_app search --from 2026-11-10 --to 2026-10-01
```
**출력 결과:**
```text
[오류] 시작일이 종료일보다 작아야합니다.
[힌트] 시작일: 2026-01-12, 종료일: 2026-02-12
```

**4) `summary --top`에 0 이하의 값 입력:**
```bash
python -m budget_app summary --month 2026-11 --top 0
```
**출력 결과:**
```text
[오류] 지출 순위는 양의 정수로 입력해주세요.
[힌트] 5
```

---

#### 9-5. CSV 내보내기 / 가져오기 및 파일 손상 실패 (`export`, `import`, `repositories`)

**1) 월(`--month`)이나 기간(`--from`, `--to`) 지정 없이 `export` 실행:**
```bash
python -m budget_app export --out ./data/out.csv
```
**출력 결과:**
```text
[오류] 특정 달이나 기간을 지정해주세요.
```

**2) `export`에서 시작일이 종료일보다 늦은 경우:**
```bash
python -m budget_app export --out ./data/out.csv --from 2026-11-10 --to 2026-10-01
```
**출력 결과:**
```text
[오류] 시작일이 종료일보다 작아야합니다.
[힌트] 시작일: 2026-01-12, 종료일: 2026-02-12
```

**3) 존재하지 않는 CSV 파일 `import` 시도:**
```bash
python -m budget_app import --from ./data/not_found.csv
```
**출력 결과:**
```text
[오류] 파일이 존재하지 않습니다.
```

**4) 오류 행(날짜 오류, 미등록 카테고리, 음수 금액, 잘못된 타입)이 섞인 CSV `import` 시 상세 실패 리포트(`[스킵 이유]`) 출력:**
- 테스트 파일: `./data/sample_import_errors.csv` (정상 1건 + 오류 4건)

```bash
python -m budget_app import --from ./data/sample_import_errors.csv
```
**출력 결과:**
```text
[csv 가져오기 완료] imported=1, skipped=4
[스킵 이유] 3행 오류: 날짜 형식이 올바르지 않습니다. 2026-12-30 형식으로 입력해주세요.
[스킵 이유] 4행 오류: 카테고리가 등록돼 있지 않습니다.
[스킵 이유] 5행 오류: 0보다 큰 양의 정수만 입력해주세요
[스킵 이유] 6행 오류: income, expense중 입력해주세요.
```

**5) 오류 행 발생 시 트랜잭션 전체 롤백(`--rollback-on-error`) 시연:**
```bash
python -m budget_app import --from ./data/sample_import_errors.csv --rollback-on-error
```
**출력 결과:**
```text
[오류] 오류 행(4건)이 발견되어 전체 롤백되었습니다.
[힌트] 3행 오류: 날짜 형식이 올바르지 않습니다. 2026-12-30 형식으로 입력해주세요. / 4행 오류: 카테고리가 등록돼 있지 않습니다. / 5행 오류: 0보다 큰 양의 정수만 입력해주세요 / 6행 오류: income, expense중 입력해주세요.
```

**6) 저장된 `.jsonl` 파일이 손상되었을 때 (`json.JSONDecodeError` 방어):**
```bash
python -m budget_app list
```
**출력 결과:**
```text
[오류] json을 로드를 실패하였습니다.
```

---

## 7. 대용량(100k건 수준) 병목 지점 식별 및 구체적 개선 계획

거래 데이터가 **100,000건(100k) 이상**으로 증가하는 대용량 환경에서 `@timer`(`time.perf_counter()`) 및 프로파일러(`cProfile`, `tracemalloc`)로 측정 시 예상되는 **주요 병목 지점(Profiling Points)**과 이를 해결하기 위한 **메모리(Memory) / 디스크 I/O / CPU 관점별 구체적 개선 방안**입니다.

---

### 7.1 100k 수준에서의 핵심 프로파일링 포인트 (병목 지점 식별)

| 순위 | 병목 지점 (모듈 및 메서드) | 원인 분석 | 시간 / 공간 복잡도 |
| :---: | :--- | :--- | :---: |
| **1** | `BudgetService.list_transactions()` (`services.py:77`) | `sorted(self.transaction_repo.iter_all(), ...)` 호출 시 제너레이터 스트림이 전체 리스트로 구체화(Materialization)되면서 100k 객체가 한꺼번에 메모리에 적재되고 전체 정렬 수행 | 시간 `O(N log N)` / 메모리 `O(N)` |
| **2** | `TransactionRepository.next_id()` (`repositories.py:107`) | 거래 1건 추가(`add`) 시마다 마지막 ID 번호를 계산하기 위해 100k 줄 전체를 처음부터 끝까지 읽고 `json.loads()`를 수행하는 풀 스캔(Full Scan) 발생 | 시간 `O(N)` (1건 추가당) |
| **3** | `BudgetService.import_csv()` (`services.py:252`) | 대량 CSV 가져오기 시 매 행마다 `category_repo.exists()`(파일 읽기) + `next_id()`(100k 스캔) + `append_jsonl()`(파일 `open`/`close` 반복)이 중첩 호출됨 | 시간 `O(N²)` / 과도한 디스크 I/O |
| **4** | `TransactionRepository.update()` / `delete()` (`repositories.py:113, 124`) | 수정·삭제 시 리스트 컴프리헨션(`[item.to_dict() for item in self.iter_all() ...]`)으로 100k 전체를 메모리에 적재한 뒤 `.tmp` 파일에 기록 | 시간 `O(N)` / 메모리 `O(N)` |

---

### 7.2 영역별(메모리 / 디스크 I/O / CPU) 구체적 개선 계획

#### ① 메모리(Memory) 최적화 계획: **역순 읽기(Reverse Reading) 및 완전 스트리밍화**
1. **파일 역순 읽기(Reverse Block Reading) 및 Top-K 힙(`heapq.nlargest`) 도입**:
   - **문제**: `list --limit 10`처럼 최신 10건만 필요할 때도 `sorted()`가 100k 건을 모두 메모리에 올립니다.
   - **개선**:
     - 거래가 시간순으로 쌓이는 경우에는 파일 포인터를 끝으로 이동(`os.seek(0, os.SEEK_END)`)하여 블록(예: `8KB`) 단위로 **역순 읽기(Reverse Reading)**를 수행하면 `limit` 건수만큼만 읽고 즉시 종료할 수 있어 메모리와 시간을 모두 **`O(K)` (`K = limit`)**로 줄일 수 있습니다.
     - 과거 날짜 입력으로 순서가 섞여 있는 경우에도 전체 `sorted()` 대신 파이썬 표준 라이브러리 **`heapq.nlargest(limit, self.transaction_repo.iter_all(), key=...)`**를 사용하면 메모리에 최대 `K`개의 요소만 유지하므로 메모리 사용량이 **`O(N)` → `O(K)`**로 대폭 감소합니다.
2. **`update` / `delete` 시 제너레이터 표현식(Generator Expression) 적용**:
   - **문제**: `repositories.py`의 `update()`와 `delete()`에서 대괄호 리스트 컴프리헨션(`[item.to_dict() ...]`)을 사용하여 100k 건을 메모리에 복사합니다.
   - **개선**: 대괄호 `[...]` 대신 소괄호 **제너레이터 표현식(`(item.to_dict() for item in self.iter_all() if item.id != tx_id)`)**으로 바꿔 `write_all_jsonl()`에 전달하면, `.tmp` 임시 파일로 복사하는 동안에도 메모리에 단 1건씩만 올라가는 **`O(1)` 메모리 스트리밍**이 유지됩니다.

#### ② 디스크 I/O 최적화 계획: **배치 쓰기(Batch Writing) 및 월별 파일 파티셔닝**
1. **배치 쓰기(Batch Write) 도입**:
   - **문제**: `import_csv()`에서 100k 건을 등록할 때 `append_jsonl()`이 10만 번 호출되어 파일 `open()` / `write()` / `close()` 시스템 콜이 10만 회 발생합니다.
   - **개선**: `TransactionRepository.add_batch(transactions: Iterable[Transaction])` 메서드를 추가하여 단일 `with path.open("a", encoding="utf-8") as f:` 블록 안에서 일정 크기(예: `5,000`건 단위 버퍼)로 묶어 **`f.writelines()` 배치 쓰기**를 수행하면 디스크 I/O 오버헤드를 수십 배 이상 단축할 수 있습니다.
2. **월별 파일 파티셔닝(Monthly File Partitioning)**:
   - **문제**: 단일 `transactions.jsonl` 파일에 100k 건이 누적되면 특정 달 요약(`summary --month 2026-11`) 시에도 모든 연도의 데이터를 읽어야 합니다.
   - **개선**: 저장 파일을 `data/transactions_2026-10.jsonl`, `data/transactions_2026-11.jsonl` 형태로 연-월 단위 분할(Partitioning)하면 월별 요약 및 기간 검색 시 해당 월 파일만 열면 되므로 디스크 읽기 I/O가 **`1/개월수`**로 줄어듭니다.

#### ③ CPU 및 탐색 최적화 계획: **인덱싱(Indexing) 및 메타데이터 캐싱**
1. **인덱싱(Indexing) 구조 도입 (`tx_id` 및 `month` 오프셋 인덱스)**:
   - **문제**: `get_by_id()`, `update()`, `delete()`, `search()` 실행 시 매번 100k 줄 전체에 대해 문자열 파싱(`json.loads()`)을 수행하여 CPU 연산 비용이 가장 크게 발생합니다.
   - **개선**:
     - `tx_id -> 파일 내 바이트 위치(byte offset)`를 매핑한 경량 인덱스 파일(`transactions.idx` 또는 표준 라이브러리 `sqlite3` 인덱스)을 유지합니다.
     - 특정 ID 조회 시 전체 파일을 파싱하지 않고 **`f.seek(byte_offset)`**으로 해당 줄만 읽어 `json.loads()`를 딱 1번만 수행하므로 탐색 및 CPU 파싱 비용이 **`O(N)` → `O(1)`**로 개선됩니다.
2. **ID 채번(`next_id`) 메타데이터 분리 및 역순 1줄 조회**:
   - **문제**: `next_id()`가 매번 100k 건을 전수 순회합니다.
   - **개선**: 마지막으로 발급된 번호(`last_seq`)를 `meta.json`에 기록해 두거나 파일의 맨 마지막 줄 1개만 역순으로 읽어 채번하면 `next_id()`의 CPU/IO 비용이 **`O(N)` → `O(1)`**로 즉시 제거됩니다.
3. **카테고리 목록 인메모리 해시 셋(`set`) 캐싱**:
   - **문제**: 거래 추가 및 `import_csv()` 반복 검증 시마다 `categories.jsonl` 파일을 반복해서 읽고 리스트 탐색(`O(M)`)을 수행합니다.
   - **개선**: `CategoryRepository`에서 카테고리 목록을 메모리 `set[str]`에 캐싱하고 카테고리 추가/삭제 시에만 갱신하도록 변경하면, 대량 검증 시 디스크 I/O가 사라지고 존재 여부 검사가 **`O(1)` 해시 조회**로 빨라집니다.
