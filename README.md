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
├── decorators.py     # 공통 관심사 데코레이터 (@handle_errors: 예외 출력 및 종료 코드 제어)
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
| **10. CSV 가져오기 (`import`)** | `python -m budget_app import --from FILE.csv` |

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

**4) 오류 행(날짜 오류, 미등록 카테고리, 음수 금액, 잘못된 타입)이 섞인 CSV `import` 시 `skipped` 처리:**
- 테스트 파일: `./data/sample_import_errors.csv` (정상 1건 + 오류 4건)

```bash
python -m budget_app import --from ./data/sample_import_errors.csv
```
**출력 결과:**
```text
[csv 가져오기 완료] imported=1, skipped=4
```

**5) 저장된 `.jsonl` 파일이 손상되었을 때 (`json.JSONDecodeError` 방어):**
```bash
python -m budget_app list
```
**출력 결과:**
```text
[오류] json을 로드를 실패하였습니다.
```
