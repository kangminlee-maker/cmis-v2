# Project Patterns — CMIS v2

## File & Directory Naming

<!-- auto:naming -->
- Directories: `snake_case/` (예: `cmis_v2/`, `engine_data/`)
- Files: `snake_case.py` (예: `state_machine.py`, `ontology_migration.py`)
- YAML configs: `snake_case.yaml` (예: `policies.yaml`, `ontology.yaml`)
<!-- /auto:naming -->

## Language Protocol
- All files on `main`: English.
- Config keys, enum values, file paths: always English.
- User-facing string values: follow locale setting (Korean default).
- Comments in code: English.
- Ontology descriptions, pattern descriptions: Korean.

## Terminology Boundaries

| Term | 의미 | 주의: 이것이 아님 |
|------|------|-----------------|
| Estimation | 추정 **과정** (불확실, 구간 기반) | Value (확정 결과) |
| Value | 확정된 메트릭 **결과** (evidence-backed) | Estimation (추정 과정) |
| Interval | P10/P90 구간 (주관적 범위) | 수학적 interval arithmetic의 "보장된 포함" 구간 |
| bounds | METRIC_REGISTRY의 물리적 hard constraint (0≤churn≤1) | Interval (추정 범위) |
| source_reliability | 데이터 소스의 객관적 품질 (Evidence Engine 생산) | estimate_confidence (삭제 예정) |
| Evidence | 수집된 외부 데이터 (KOSIS, DART, web) | Estimate (추정 결과) |
| Estimate | 추정 엔진이 생산한 구간 결과 | Evidence (수집 데이터) |
| Fermi tree | 미지 숫자를 하위 요소로 분해한 트리 구조 | 단일 점추정 |
| Distribution | Interval 위의 선택적 확률 분포 (Beta, Lognormal 등). P10/P90에서 fitting | Interval (P10/P90 구간 자체) |

## Abbreviation Registry

| 약어 | 정식 명칭 | 설명 |
|------|----------|------|
| RLM | Recursive Language Model | LLM 실행 엔진 |
| KBD | Knowledge-Based Design | 온톨로지 기반 설계 방법론 |
| TAM | Total Addressable Market | 총 시장 규모 |
| SAM | Serviceable Available Market | 유효 시장 규모 |
| SOM | Serviceable Obtainable Market | 수익 가능 시장 규모 |
| ARPU | Average Revenue Per User | 사용자당 평균 매출 |
| LTV | Lifetime Value | 고객 생애 가치 |
| CAC | Customer Acquisition Cost | 고객 획득 비용 |
| HHI | Herfindahl-Hirschman Index | 시장 집중도 지수 |

No other abbreviations without adding to this registry.

## Branch Rule

<!-- auto:branch -->
`main` = always deployable. All work on feature branches.
<!-- /auto:branch -->
