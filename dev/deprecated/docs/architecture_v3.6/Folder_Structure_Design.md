# CMIS 폴더 구조 (schemas / libraries / config)

**작성일**: 2025-12-13
**최종 업데이트**: 2025-12-14
**버전**: v3.6.0
**상태**: 적용 완료

---

## 1. 목적

CMIS 리포지토리의 YAML/지식/설정 파일들을 아래 3개 축으로 분리해 유지보수성과 재현성을 높입니다.

- **schemas/**: 타입 시스템(구조)
- **libraries/**: 도메인 지식(값/정의)
- **config/**: 런타임 설정(실행 방법)

---

## 2. 구분 기준(SSoT)

핵심 기준은 **역할 + 변경 빈도**입니다.

### 2.1 schemas/ (타입 시스템)

- **역할**: “무엇의 모양(shape)인가”
- **변경 빈도**: 거의 없음(대부분 breaking)
- **예시(현재)**:
  - `schemas/ledgers.yaml`
  - `schemas/ontology.yaml`
  - `schemas/reality_graph.yaml`
  - `schemas/pattern_graph.yaml`
  - `schemas/value_graph.yaml`
  - `schemas/decision_graph.yaml`

### 2.2 libraries/ (도메인 지식)

- **역할**: “구체적 값/정의(지식) 무엇인가”
- **변경 빈도**: 가끔(확장/추가)
- **예시(현재)**:
  - `libraries/patterns/` (Pattern YAML들)
  - `libraries/metrics_spec.yaml`
  - `libraries/domains/` (도메인 정의)
  - `libraries/domain_registry.yaml`
  - `libraries/prompt_library.yaml`

### 2.3 config/ (런타임 설정)

- **역할**: “어떻게 실행하는가”
- **변경 빈도**: 자주(튜닝/운영)
- **예시(현재)**:
  - `config/policies.yaml`
  - `config/workflows.yaml`
  - `config/archetypes/`
  - `config/sources/`
  - `config/search_strategy_spec.yaml`
  - `config/validation_guidelines.yaml`

---

## 3. 현재 구조(적용 결과)

리포지토리 루트 기준:

```text
cmis.yaml                 # Contracts + Registry
schemas/                  # 타입 시스템
libraries/                # 도메인 지식
config/                   # 런타임 설정
cmis_core/                # 엔진 구현
cmis_cli/                 # CLI
```

---

## 4. cmis.yaml 모듈 매핑

`cmis.yaml`은 “상위 계약/레지스트리”만 유지하고, 대형 스펙은 외부 파일로 분리합니다.

- **schemas**: `schemas/*.yaml`
- **libraries**: `libraries/*` 또는 `libraries/*/`
- **config**: `config/*.yaml` 및 하위 디렉토리

(참고) 레퍼런스 정합성은 `python3 -m cmis_cli config-validate --check-registry`로 검증합니다.

---

## 5. 운영 규칙

- **schemas 변경**: 스키마 변경은 파급이 크므로 PR 단위로 엄격하게 리뷰
- **libraries 확장**: pattern/metric/domain 추가는 호환성 유지(가능하면 backward)
- **config 튜닝**: 운영 중 수시 조정 가능하나, 정책/워크플로 변경은 재현성 관점에서 run_store에 기록

---

## 6. 문서 이력

(v3.6 문서 정리) 폴더 재구성 실행 플랜 문서는 `dev/deprecated/docs/architecture_v3.6/`로 이동했습니다.
