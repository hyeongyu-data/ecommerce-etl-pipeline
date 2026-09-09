# 통합 주문 스키마 설계

3개 이종 소스(PG 주문·오픈마켓 주문·GA4 이벤트)를 하나의 BigQuery 테이블 `orders_unified`로
모은다. 이 문서는 통합 스키마, 소스별 필드 매핑, 데이터 품질 규칙, 설계 판단 근거를 정리한다.

**컬럼 정의의 단일 출처는 `src/ecommerce_etl/schema.py`** 이며, `test_schema.py`가 이 문서의
표·아래 DDL 블록·코드가 모두 일치하는지 검증한다(어긋나면 CI 실패).

## 1. 통합 스키마 (`orders_unified`)

**Grain**: 주문 라인 1건 = 한 주문(거래) 안의 상품 1종. 멀티 상품 주문과 GA4 `purchase`
이벤트의 items 배열을 동일하게 다루기 위해 주문이 아니라 라인을 최소 단위로 잡는다.

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| `source` | STRING | N | 수집 소스: `pg` \| `openmarket` \| `ga4` |
| `source_order_id` | STRING | N | 원천 시스템의 주문/거래 식별자 |
| `order_id` | STRING | N | `{source}:{source_order_id}` — 소스 간 충돌 없는 주문 키 |
| `order_line_id` | STRING | N | `{order_id}#{line_no}` — 라인 단위 유니크 키(중복 적재 판별 기준) |
| `line_no` | INT64 | N | 주문 내 라인 순번(1부터) |
| `ordered_at` | TIMESTAMP | N | 주문/이벤트 발생 시각(UTC 저장) |
| `order_date` | DATE | N | `ordered_at`의 `Asia/Seoul` 날짜 — 파티션 키 |
| `customer_id` | STRING | Y | 원천 고객 식별자의 SHA-256 해시. GA4는 제공 불가로 NULL |
| `product_id` | STRING | N | 원천 상품 식별자 |
| `product_name` | STRING | Y | 상품명 |
| `quantity` | INT64 | N | 수량 (> 0) |
| `unit_price` | NUMERIC | Y | 단가 (>= 0) |
| `line_amount` | NUMERIC | N | 라인 금액 = `quantity * unit_price` (>= 0) |
| `currency` | STRING | N | 원천 통화. 이 프로젝트는 모든 소스를 `KRW`로 통일(4-3) |
| `channel` | STRING | Y | 판매 채널(자사몰·네이버·쿠팡 등). 없으면 NULL |
| `event_name` | STRING | Y | GA4 이벤트명(`purchase` 등). 주문 소스는 `order` 고정 |
| `source_file` | STRING | Y | 원본 파일명 또는 API 응답 배치 ID(추적용) |
| `ingested_at` | TIMESTAMP | N | 파이프라인 적재 시각 |

### DDL (초안)

데이터셋은 파라미터로 치환한다: `` `${GCP_PROJECT_ID}.${BQ_DATASET}.orders_unified` ``

```sql
CREATE TABLE IF NOT EXISTS `orders_unified`
(
  source          STRING    NOT NULL OPTIONS(description="수집 소스: pg | openmarket | ga4"),
  source_order_id STRING    NOT NULL OPTIONS(description="원천 시스템의 주문/거래 식별자"),
  order_id        STRING    NOT NULL OPTIONS(description="{source}:{source_order_id}"),
  order_line_id   STRING    NOT NULL OPTIONS(description="{order_id}#{line_no} — 라인 단위 유니크 키"),
  line_no         INT64     NOT NULL OPTIONS(description="주문 내 라인 순번(1부터)"),
  ordered_at      TIMESTAMP NOT NULL OPTIONS(description="주문/이벤트 시각(UTC)"),
  order_date      DATE      NOT NULL OPTIONS(description="ordered_at의 Asia/Seoul 날짜 — 파티션 키"),
  customer_id     STRING             OPTIONS(description="원천 고객 식별자 SHA-256 해시. GA4는 NULL"),
  product_id      STRING    NOT NULL,
  product_name    STRING,
  quantity        INT64     NOT NULL OPTIONS(description="수량 > 0"),
  unit_price      NUMERIC            OPTIONS(description="단가 >= 0"),
  line_amount     NUMERIC   NOT NULL OPTIONS(description="quantity * unit_price >= 0"),
  currency        STRING    NOT NULL OPTIONS(description="원천 통화. 이 프로젝트는 KRW로 통일"),
  channel         STRING             OPTIONS(description="판매 채널. 없으면 NULL"),
  event_name      STRING             OPTIONS(description="GA4 이벤트명. 주문 소스는 'order'"),
  source_file     STRING             OPTIONS(description="원본 파일명 또는 API 배치 ID(추적용)"),
  ingested_at     TIMESTAMP NOT NULL OPTIONS(description="파이프라인 적재 시각")
)
PARTITION BY order_date
CLUSTER BY source
OPTIONS(description="3개 이종 소스(PG/오픈마켓/GA4)를 라인 단위로 통합한 주문 테이블");
```

> 비용: 조회 시 `order_date` 범위 필터를 항상 건다(파티션 프루닝). 운영 전환 시
> `require_partition_filter=true` 부여를 고려한다.

## 2. 소스별 필드 매핑

### 2-1. PG 주문 — `pg` (Kaggle Olist `olist_orders` + `olist_order_items`)

| 통합 컬럼 | 원천 필드 | 비고 |
|---|---|---|
| `source_order_id` | `order_id` | |
| `line_no` | `order_item_id` | Olist는 주문항목마다 행이 나뉨 |
| `ordered_at` | `order_purchase_timestamp` | |
| `customer_id` | `customer_id` | SHA-256 해시 후 저장 |
| `product_id` | `product_id` | |
| `product_name` | `product_category_name` | 상품명이 없어 카테고리로 대체 |
| `quantity` | (상수 1) | Olist는 항목 행당 수량 개념이 없음 |
| `unit_price` | `price` | |
| `line_amount` | `price` | `quantity = 1` |
| `channel` | (NULL) | 단일 채널 |
| `event_name` | (상수 `order`) | |

### 2-2. 오픈마켓 주문 — `openmarket` (fakestoreapi `/carts` + `/products`, 또는 목업 생성)

| 통합 컬럼 | 원천 필드 | 비고 |
|---|---|---|
| `source_order_id` | `cart.id` | |
| `line_no` | `products[]` 인덱스 | 1부터 재부여 |
| `ordered_at` | `cart.date` | |
| `customer_id` | `cart.userId` | SHA-256 해시 |
| `product_id` | `products[].productId` | |
| `product_name` | `/products/{id}.title` | 상품 API 조인 |
| `quantity` | `products[].quantity` | |
| `unit_price` | `/products/{id}.price` | |
| `line_amount` | `quantity * unit_price` | 계산 |
| `channel` | (상수 `openmarket`) | 실데이터면 네이버/쿠팡 구분 |
| `event_name` | (상수 `order`) | |

### 2-3. GA4 이벤트 — `ga4` (GA4 Data API, `purchase` 이벤트)

| 통합 컬럼 | 원천 디멘션/메트릭 | 비고 |
|---|---|---|
| `source_order_id` | `transactionId` | |
| `line_no` | 행 내 item 순번 | Data API는 item 단위 행 |
| `ordered_at` | `date` + `hour` | 분 이하 시각은 소실(집계 API 한계) |
| `customer_id` | (NULL) | GA4 Data API는 개인 식별자 미제공 |
| `product_id` | `itemId` | |
| `product_name` | `itemName` | |
| `quantity` | `itemsPurchased` | |
| `unit_price` | `itemRevenue / itemsPurchased` | 역산 |
| `line_amount` | `itemRevenue` | |
| `channel` | `sessionDefaultChannelGroup` | |
| `event_name` | `eventName` | `purchase` |

## 3. 데이터 품질 규칙

적재 전(staging) 검증한다. 위반 행은 격리하고, 위반 비율이 임계치(예: 1%)를 넘으면 DAG를 실패시킨다.

| # | 규칙 | 목적 |
|---|---|---|
| Q1 | `order_line_id`, `source`, `ordered_at`, `product_id`, `quantity`, `line_amount` NOT NULL | 필수값 누락 |
| Q2 | `order_line_id` 유니크 | 중복 적재 방지 |
| Q3 | `quantity > 0`, `unit_price >= 0`, `line_amount >= 0` | 이상치 |
| Q4 | `abs(line_amount - quantity * unit_price) <= 1` | 소스 내부 금액 정합성 |
| Q5 | `order_date = DATE(ordered_at, 'Asia/Seoul')` | 파티션 키 파생 정확성 |
| Q6 | `source IN ('pg', 'openmarket', 'ga4')` | 허용된 소스만 |
| Q7 | `ordered_at <= ingested_at` | 미래 시각 주문 차단 |

## 4. 설계 판단 근거

### 4-1. 왜 BigQuery인가
소스별 스키마·볼륨이 제각각이고 분석 쿼리는 열 중심 집계(소스별 매출 추이 등)다. 컬럼형 DW가
적합하고, 관리형이라 이 규모에서 운영 부담이 없다. 날짜 파티션 + `source` 클러스터로 스캔 비용을
통제한다. 로컬 Postgres는 분석 스캔에 불리하고, DuckDB는 공유·대시보드 연동이 약하다.

### 4-2. 왜 주문이 아니라 라인 grain인가
멀티 상품 주문과 GA4 items 배열을 특수 처리 없이 같은 모양으로 담을 수 있다. 주문 단위 집계는
`order_id`로 GROUP BY 하면 되지만, 라인을 주문으로 뭉치면 상품별 분석이 불가능해진다. 되돌릴 수
없는 방향이라 더 잘게 잡는다.

### 4-3. 왜 통화를 KRW로 통일하는가
Olist(BRL)·fakestore(USD)를 그대로 합치면 매출 합계가 무의미해진다. 이 프로젝트의 목적은
"이종 소스 정합"이지 환율 처리가 아니므로, 수집 단계에서 모든 금액을 KRW로 생성·간주하고
`currency` 컬럼은 실데이터 확장 여지로 남긴다. 다통화 정규화는 명시적 범위 밖.

### 4-4. 왜 `customer_id`를 해시하는가
포트폴리오 저장소는 public이다. 원천 고객 식별자를 그대로 적재하면 안 되고, 조인·중복 판별에는
안정적 해시로 충분하다. GA4는 식별자 자체를 주지 않으므로 NULL을 허용한다.

### 4-5. 왜 `ordered_at`은 UTC, `order_date`는 KST인가
시각은 표준시로 저장해 소스 간 비교를 단순화하고, 파티션·리포트 기준일은 서비스 운영 기준인
`Asia/Seoul` 날짜로 파생한다. Q5가 이 파생을 강제한다.

## 5. 범위 밖 (이번 프로젝트에서 하지 않음)

- 다통화 환율 정규화
- 주문 취소·환불·부분취소 상태 추적(현재는 확정 주문/구매만)
- SCD(고객·상품 마스터 이력 관리)
- 실시간 스트리밍(모두 배치)
