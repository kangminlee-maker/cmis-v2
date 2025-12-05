# UMIS v9 아키텍처 갭 분석 리포트

**작성일**: 2025-12-05  
**목적**: v7.x 실전 경험 기반 v9 상위 설계 보완점 도출  
**대상**: UMIS v9 아키텍트 및 개발팀

---

## Executive Summary

### 현재 상태 평가

**v9 상위 설계 강점**:
- ✅ 철학적 완성도 매우 높음 (Reality/Pattern/Value/Decision 그래프 분리)
- ✅ Ontology 설계 우수 (Trait 기반, Ontology lock-in 회피)
- ✅ 4-Plane 아키텍처 명확함 (Interaction/Role/Substrate/Cognition)
- ✅ Evidence-first 철학 일관성 유지

**핵심 문제**:
- ⚠️ **실행 레벨 상세 부족**: 개념적 설계는 훌륭하나, 실제 프로젝트 수행을 위한 운영 상세가 미비
- ⚠️ **v7 실전 노하우 미반영**: v7에서 검증된 프로세스/협업 체계/검증 메커니즘이 v9에 이식되지 않음
- ⚠️ **Agent 협업 프로토콜 부재**: Role Plane에 역할은 정의되어 있으나 협업 방법 불명확

### 권고사항 요약

**Phase 2-3 구현 전 필수 보완** (Priority 1):
1. Agent 협업 프로토콜 정의
2. 14-Phase 프로세스 구조화
3. 검증 게이트 메커니즘 수립

**Phase 3-4 전 권장** (Priority 2):
4. 전략 프레임워크 라이브러리 이식
5. 가치사슬 분석 템플릿 작성
6. 데이터 품질 관리 체계 구축

**Phase 4-5 전 유용** (Priority 3):
7. 산업별 벤치마크 데이터 확보
8. BM 분류 프레임워크 상세화
9. ID 생성/관리 규칙 정교화
10. Output 포맷 표준화

---

## 1. v7.x 실전 경험 분석

### 1.1 v7 Market Reality Report 프로젝트 구조

**프로젝트**: 한국 성인 어학교육 시장 구조 분석  
**기간**: 14 Phases (약 5일)  
**결과**: 9개 산출물, 품질 등급 A

#### Phase 구조 (v7 실제 사용)

```
Phase 1: 시장 정의 및 경계 설정 (Needs 기반)
  ├─ 산출물: Needs 분류 (A-D 카테고리, 12개 세부)
  ├─ 검증: MECE 여부
  └─ 소요: 1.5시간

Phase 2: 도메인 MECE 분류
  ├─ 산출물: 15개 언어 도메인
  ├─ 검증: Mutually Exclusive, Collectively Exhaustive
  └─ 소요: 1시간

Phase 3: BM 분류 프레임워크
  ├─ 산출물: 3-Axis Framework, 23개 BM 매트릭스
  ├─ 검증: MECE 프레임워크
  └─ 소요: 1.5시간

Phase 4: BM 전수조사
  ├─ 산출물: 23개 BM 상세 정의
  ├─ 검증: Collectively Exhaustive 달성
  └─ 소요: 1.5시간

Phase 5-1: 주요 플레이어 식별
  ├─ 담당: Observer + Validator
  ├─ 산출물: 50개+ 플레이어 목록, Rachel 데이터 요청서
  └─ 소요: 1.5시간

Phase 5-2: 플레이어 목록 검증
  └─ 누락 플레이어 Cross-check

Phase 6: 가치사슬 구조 맵핑
  ├─ 산출물: BM별 돈의 흐름 추적 (누가→누구→얼마)
  ├─ 협업: Estimator (마진율 추정)
  └─ 소요: 2시간

Phase 7-1: Rachel 데이터 수집
  ├─ 산출물: SRC-ID 5개 확보
  └─ 신뢰도: 70-95%

Phase 7-2: Bill 시장규모 계산
  ├─ 방법: Bottom-up (Top 플레이어 합산)
  └─ 산출물: ASM-ID 부여

Phase 7-3: Fermi 시장규모 추정
  ├─ 방법: 4-Method Convergence
  ├─ 산출물: EST-ID 50개+
  └─ 신뢰도: 75%

Phase 8-11: 경쟁구조 분석
  ├─ 경쟁강도 (CR3, HHI)
  ├─ 교섭력 구조
  ├─ 거래 구조
  └─ 시장집중도

Phase 12: MECE 검증
  └─ 모든 분류 재검증

Phase 13: 3명 검증 게이트
  ├─ Bill (정량 타당성): ✅ 통과
  ├─ Rachel (데이터 신뢰성): ✅ 통과 (70-75%)
  └─ Stewart (논리 건전성): ✅ 통과 (품질 A)

Phase 14: Market Reality Report 작성
  └─ 9개 파일 통합
```

#### 핵심 성공 요인

1. **명확한 Phase 구조**: 14단계로 분해, 각 단계별 명확한 산출물
2. **Agent 협업 체계**: 요청서/응답 포맷 표준화 (Rachel Data Request)
3. **완전한 추적성**: SRC-/EST-/ASM- ID로 모든 주장 근거 추적
4. **검증 게이트**: 3명 검증자, 각자 명확한 체크리스트
5. **MECE 원칙 준수**: 모든 분류에 대해 검증 수행

### 1.2 v7 Agent 협업 사례

#### Rachel 데이터 요청서 (02_Rachel_Data_Request.md)

```markdown
# Validator(Rachel) 데이터 수집 요청서

**요청자**: Observer (Albert)
**요청일**: 2025-12-04
**우선순위**: HIGH

## 1. 데이터 수집 우선순위

### 1순위: 확정 데이터 (신뢰도 ≥80%)

1. **상장사 공시자료 (DART)**
   - YBM넷, 능률교육, 메가스터디
   - 수집 항목: 매출액, 영업이익, 지점 수, 수강생 수

2. **통계청/정부 공식 통계**
   - 사교육비 조사
   - 성인 대상 어학 사교육비

### 2순위: 신뢰할 수 있는 추정 데이터
   ...

## 2. BM별 구체적 데이터 수집 항목
   ...

## 5. 데이터 품질 기준

| 신뢰도 | 출처 유형 | 예시 |
|-------|---------|------|
| 90-100 | 공식 공시/정부 통계 | DART, 통계청 |
| 80-89 | 업계 보고서 | IBK, KB 리포트 |
| 70-79 | 주요 언론 보도 | 매출 발표 |
```

**시사점**:
- Agent 간 명확한 요청/응답 포맷
- 우선순위 명시
- 품질 기준 사전 합의

#### 3명 검증 게이트 (07_Final_Validation.md)

```markdown
## 13.1 Bill (Quantifier) 검증: 정량 타당성

**시장 규모 검증**
- 4-Method Convergence 적용
- ±30% 범위 검증
- **결과**: ✅ 정량적으로 타당함

## 13.2 Rachel (Validator) 검증: 데이터 신뢰성

**확정 데이터 활용도**
- 확보된 SRC-ID: 5개
- **결과**: ✅ 데이터 신뢰도 적정 (70-75%)

## 13.3 Stewart (Guardian) 검증: 논리 건전성

**분석 프로세스 검증**
- MECE 원칙 준수
- 목표 정렬
- **결과**: ✅ 논리적으로 건전함 (품질 A)
```

**시사점**:
- 검증자별 명확한 책임
- 체크 항목 구체화
- Pass/Fail 기준 명확

---

## 2. v9 상위 설계 갭 분석

### 갭 분석 방법론

v7 실전 산출물과 v9 `umis_v9.yaml`을 다음 기준으로 비교:

1. **프로세스 실행 가능성**: 실제 프로젝트를 돌릴 수 있는가?
2. **협업 명확성**: Agent들이 어떻게 협업하는가?
3. **품질 보증**: 검증 메커니즘이 작동하는가?
4. **재사용성**: 프레임워크/벤치마크를 활용할 수 있는가?

### 갭 요약 매트릭스

| 영역 | v7 수준 | v9 수준 | 갭 크기 | 우선순위 |
|------|---------|---------|---------|----------|
| 프로세스 Phase 정의 | ●●●●● | ●●○○○ | 큰 | P1 |
| Agent 협업 프로토콜 | ●●●●○ | ●○○○○ | 매우 큰 | P1 |
| 검증 게이트 메커니즘 | ●●●●○ | ●●○○○ | 큰 | P1 |
| 전략 프레임워크 | ●●●●● | ○○○○○ | 매우 큰 | P2 |
| 가치사슬 템플릿 | ●●●●○ | ●○○○○ | 큰 | P2 |
| 데이터 품질 관리 | ●●●●● | ●●○○○ | 큰 | P2 |
| 산업 벤치마크 | ●●●●● | ○○○○○ | 매우 큰 | P3 |
| BM 분류 프레임워크 | ●●●●○ | ●●○○○ | 중간 | P3 |
| ID 관리 규칙 | ●●●●○ | ●●○○○ | 중간 | P3 |
| Output 포맷 | ●●●●○ | ●●○○○ | 중간 | P3 |

---

## 3. 상세 갭 분석 및 보완 방안

### 갭 #1: 프로세스 Phase 정의 부재 ⭐⭐⭐

#### 현재 v9 상태

```yaml
# umis_v9.yaml (1332-1396줄)
canonical_workflows:
  - id: "structure_analysis"
    role_id: "structure_analyst"
    description: "특정 시장/도메인의 구조/메커니즘 및 핵심 economics 이해"
    steps:
      - call: "world_engine.snapshot"
        with: { ... }
      - call: "pattern_engine.match_patterns"
        with: { ... }
      - call: "value_engine.evaluate_metrics"
        with: { ... }
```

**문제점**:
- Step이 너무 high-level (3개 step으로 전체 프로젝트 표현)
- 각 step의 입력/출력이 불명확
- 중간 검증 포인트가 없음
- Phase 간 의존성 관리 불가

#### v7 실제 구조

```
14 Phases × 각 Phase별:
  - 명확한 산출물
  - 검증 기준
  - 소요 시간
  - 협업 대상
  - 품질 평가
```

#### 보완 방안

**새 파일 생성**: `umis_v9_process_phases.yaml`

```yaml
---
umis_v9_process_phases:
  meta:
    description: "canonical_workflows의 상세 Phase 분해"
    linked_to: "umis_v9.yaml#canonical_workflows"

  workflows:
    structure_analysis:
      workflow_id: "structure_analysis"
      role_id: "structure_analyst"
      total_phases: 14
      estimated_duration: "3-5 days"

      phases:

        - phase_id: "PH01_market_definition"
          sequence: 1
          name: "시장 정의 및 경계 설정"
          owner: "structure_analyst"
          duration: "1-2 hours"

          inputs:
            - type: "user_query"
              content: "시장/도메인 범위 질문"

          activities:
            - "Needs 전수 분류 (A-D 카테고리)"
            - "시장 경계 정의 (포함/제외)"
            - "거래 주체별 분류 (B2C/B2B/B2G)"

          outputs:
            - type: "artifact"
              id: "ART-needs_classification"
              format: "structured_yaml"
              content:
                - "Needs 분류 체계"
                - "시장 포함/제외 범위"

          validation:
            type: "self_check"
            criteria:
              - "Needs가 MECE인가?"
              - "거래 관찰 가능한가?"
              - "시장 경계가 명확한가?"

          success_criteria:
            - "모든 Needs가 A-D 중 하나에 할당"
            - "포함/제외 범위 명시"

        - phase_id: "PH02_domain_classification"
          sequence: 2
          name: "도메인 MECE 분류"
          owner: "structure_analyst"
          duration: "1 hour"

          depends_on:
            - "PH01_market_definition"

          inputs:
            - type: "artifact"
              id: "ART-needs_classification"

          activities:
            - "도메인 축 정의 (언어, 제품 카테고리 등)"
            - "도메인별 MECE 분류"
            - "도메인별 추정 점유율"

          outputs:
            - type: "artifact"
              id: "ART-domain_classification"
              format: "structured_yaml"

          validation:
            type: "mece_check"
            criteria:
              - "Mutually Exclusive"
              - "Collectively Exhaustive (100%)"

        - phase_id: "PH03_bm_framework"
          sequence: 3
          name: "비즈니스 모델 분류 프레임워크"
          owner: "structure_analyst"
          duration: "1.5 hours"

          inputs:
            - type: "framework_library"
              id: "bm_classification_framework"

          activities:
            - "BM 분류 축 정의 (Delivery/Interaction/Transaction)"
            - "BM 매트릭스 작성"
            - "BM 그룹핑"

          outputs:
            - type: "artifact"
              id: "ART-bm_framework"

          validation:
            type: "framework_check"
            criteria:
              - "MECE 프레임워크인가?"
              - "관찰 가능한 거래 구조인가?"

        - phase_id: "PH04_bm_enumeration"
          sequence: 4
          name: "BM 전수조사"
          owner: "structure_analyst"

          activities:
            - "모든 BM 상세 정의"
            - "Edge Cases 검토"
            - "BM별 특성 Summary"

          outputs:
            - type: "artifact"
              id: "ART-bm_complete_list"

          validation:
            type: "exhaustiveness_check"
            criteria:
              - "누락 BM 없는가?"
              - "Edge Cases 처리했는가?"

        - phase_id: "PH05_player_identification"
          sequence: 5
          name: "주요 플레이어 식별 및 데이터 수집"
          owner: "structure_analyst"
          collaborators:
            - role: "validator"
              responsibility: "데이터 수집"

          activities:
            - "BM별 Top 플레이어 목록 작성"
            - "Validator에게 데이터 요청"

          outputs:
            - type: "artifact"
              id: "ART-player_list"
            - type: "request"
              id: "REQ-validator_data_collection"
              target_role: "validator"
              template: "data_collection_request"

          validation:
            type: "completeness_check"

        - phase_id: "PH06_value_chain_mapping"
          sequence: 6
          name: "가치사슬 구조 맵핑"
          owner: "structure_analyst"

          inputs:
            - type: "artifact"
              id: "ART-player_list"
            - type: "framework"
              id: "value_chain_template"

          activities:
            - "BM별 돈의 흐름 추적 (누가→누구→얼마)"
            - "가치사슬 단계 식별"
            - "마진율 관찰/추정"

          outputs:
            - type: "artifact"
              id: "ART-value_chain_map"
            - type: "estimation_requests"
              ids: ["EST-margin_rates"]

          validation:
            type: "flow_check"
            criteria:
              - "모든 돈의 흐름이 추적되는가?"
              - "합계가 100%인가?"

        - phase_id: "PH07_market_sizing"
          sequence: 7
          name: "시장규모 추정 (Multi-method)"
          owner: "quantifier"
          collaborators:
            - role: "validator"
              responsibility: "확정 데이터 제공"
            - role: "estimator"
              responsibility: "추정 수행"

          activities:
            - "Method 1: Top-down"
            - "Method 2: Bottom-up (Top 플레이어 합산)"
            - "Method 3: Fermi 분해"
            - "Method 4: 유사 시장 비교"
            - "4-Method Convergence"

          outputs:
            - type: "artifact"
              id: "ART-market_size_estimate"
            - type: "assumptions"
              ids: ["ASM-total_market", "ASM-bm_shares"]

          validation:
            type: "convergence_check"
            criteria:
              - "4가지 방법이 합리적 범위 내 수렴"
              - "±30% 이내"

        - phase_id: "PH08_competition_analysis"
          sequence: 8
          name: "경쟁구조 분석"
          owner: "structure_analyst"

          activities:
            - "경쟁강도 (CR3, HHI)"
            - "교섭력 구조"
            - "거래 구조"
            - "시장집중도"

          outputs:
            - type: "artifact"
              id: "ART-competition_analysis"

        - phase_id: "PH12_mece_validation"
          sequence: 12
          name: "MECE 검증"
          owner: "structure_analyst"

          activities:
            - "모든 분류 MECE 재검증"
            - "합산 검증 (BM별 = 도메인별 = 전체)"

          validation:
            type: "comprehensive_mece"
            all_artifacts:
              - "ART-needs_classification"
              - "ART-domain_classification"
              - "ART-bm_complete_list"

        - phase_id: "PH13_validation_gate"
          sequence: 13
          name: "3명 검증 게이트"
          validators:
            - role: "quantifier"
              checklist: ["calculation_logic", "convergence"]
            - role: "validator"
              checklist: ["data_reliability", "traceability"]
            - role: "guardian"
              checklist: ["goal_alignment", "umis_principles", "quality"]

          pass_criteria:
            - "모든 검증자 통과"

          fail_action:
            - "해당 Phase 재수행"

        - phase_id: "PH14_report_generation"
          sequence: 14
          name: "Market Reality Report 작성"
          owner: "structure_analyst"

          inputs:
            - all_artifacts: true

          activities:
            - "Executive Summary 작성"
            - "섹션별 통합"
            - "추적성 완성 (SRC-/EST-/ASM- ID)"

          outputs:
            - type: "final_report"
              id: "RPT-market_reality"
              format: "markdown"
              template: "market_reality_report_template"

  # 다른 workflows도 유사하게 정의
  opportunity_discovery:
    workflow_id: "opportunity_discovery"
    # ...
```

**umis_v9.yaml 수정**:

```yaml
canonical_workflows:
  - id: "structure_analysis"
    role_id: "structure_analyst"
    description: "..."
    process_phases_ref: "umis_v9_process_phases.yaml#structure_analysis"
    # ← 상세 Phase는 별도 파일 참조
```

---

### 갭 #2: Agent 협업 프로토콜 부재 ⭐⭐⭐

#### 현재 v9 상태

```yaml
# umis_v9.yaml (215-264줄)
role_plane:
  roles:
    - id: "structure_analyst"
      primary_engines: ["world_engine", "pattern_engine", "value_engine"]
      # ← 다른 Role과 어떻게 협업하는지 없음
```

**문제점**:
- Role 간 요청/응답 방법 불명확
- 데이터 전달 포맷 없음
- 협업 타이밍/트리거 불명확

#### 보완 방안

**새 파일 생성**: `umis_v9_agent_protocols.yaml`

```yaml
---
umis_v9_agent_protocols:
  meta:
    description: "Role Plane Agent 간 협업 프로토콜"
    linked_to: "umis_v9.yaml#role_plane"

  collaboration_patterns:

    # ========================================
    # Pattern 1: 데이터 수집 요청
    # ========================================

    data_collection_request:
      pattern_id: "data_collection_request"
      from_role: "structure_analyst"
      to_role: "validator"

      trigger:
        - "Phase 5-1: 플레이어 식별 완료"

      request_template:
        format: "markdown"
        required_sections:
          - section: "요청 개요"
            fields:
              - "요청자"
              - "요청일"
              - "프로젝트"
              - "우선순위"

          - section: "데이터 수집 우선순위"
            subsections:
              - "1순위: 확정 데이터 (신뢰도 ≥80%)"
              - "2순위: 신뢰할 수 있는 추정 데이터"
              - "3순위: 보조 데이터"

          - section: "수집 대상 항목"
            format: "table"
            columns: ["항목", "출처", "신뢰도 목표", "비고"]

          - section: "데이터 품질 기준"
            reliability_matrix:
              - ["90-100", "공식 공시/정부 통계", "DART, 통계청"]
              - ["80-89", "업계 보고서", "증권사 리포트"]
              - ["70-79", "주요 언론 보도", "매출 발표, IR"]

          - section: "산출물 형식"
            required_files:
              - "source_registry.yaml"
              - "data_summary.md"

          - section: "일정"
            fields:
              - "중간 보고"
              - "최종 보고"

      response_template:
        format: "markdown + yaml"
        required_sections:
          - section: "확보 데이터 Summary"
            format: "table"
            columns: ["SRC-ID", "출처", "데이터 내용", "신뢰도"]

          - section: "데이터 갭"
            list_of:
              - "항목"
              - "데이터 갭"
              - "추정 방법 제안"

          - section: "Source Registry"
            file: "source_registry.yaml"
            schema:
              SRC_ID:
                source_type: "string"
                organization: "string"
                document_name: "string"
                publication_date: "date"
                url: "string"
                reliability_score: "int (0-100)"
                data_points: "list[string]"
                notes: "string"

      example:
        request: |
          # Validator(Rachel) 데이터 수집 요청서

          **요청자**: Observer (Albert)
          **요청일**: 2025-12-05
          **프로젝트**: 한국 성인 어학교육 시장 분석
          **우선순위**: HIGH

          ## 1. 데이터 수집 우선순위

          ### 1순위: 확정 데이터 (신뢰도 ≥80%)
          ...

    # ========================================
    # Pattern 2: 추정 요청
    # ========================================

    estimation_request:
      pattern_id: "estimation_request"
      from_role: ["structure_analyst", "quantifier"]
      to_role: "estimator"

      request_template:
        format: "structured_yaml"
        schema:
          estimation_id: "EST-YYYYMMDD-NNN"
          question: "string (명확한 추정 대상)"
          context:
            known_data: "dict (확정 데이터)"
            domain_id: "string"
            region: "string"
          estimation_method:
            suggested: ["fermi", "bottom_up", "top_down", "analog"]
          quality_requirement:
            min_literal_ratio: "float"
            max_spread_ratio: "float"

      response_template:
        estimation_result:
          estimation_id: "string"
          point_estimate: "number"
          distribution:
            type: "enum[normal, uniform, triangular]"
            parameters: "dict"
          confidence: "float (0-1)"
          method_used: "string"
          assumptions: "list[ASM-ID]"
          lineage:
            from_evidence_ids: "list[SRC-ID]"
            from_value_ids: "list[VAL-ID]"
            reasoning: "string (markdown)"

      example:
        request_yaml: |
          estimation_id: "EST-20251205-001"
          question: "파고다어학원 2023년 매출액은?"
          context:
            known_data:
              YBM_revenue_2023: "817억원"
              Pagoda_revenue_2012: "53억원"
              market_growth_rate: "5-10% CAGR"
            domain_id: "Adult_Language_Education_KR"
            region: "KR"
          estimation_method:
            suggested: ["analog", "growth_projection"]
          quality_requirement:
            min_literal_ratio: 0.3
            max_spread_ratio: 0.5

    # ========================================
    # Pattern 3: 계산 요청
    # ========================================

    calculation_request:
      pattern_id: "calculation_request"
      from_role: "structure_analyst"
      to_role: "quantifier"

      request_template:
        calculation_type: "enum[bottom_up, top_down, margin, convergence]"
        input_data: "dict"
        formula: "string (optional)"
        assumptions: "list[ASM-ID]"

      response_template:
        calculation_id: "ASM-YYYYMMDD-NNN"
        result: "number"
        breakdown: "dict"
        validation:
          sanity_check: "bool"
          convergence_check: "bool (if applicable)"
        lineage: "dict"

    # ========================================
    # Pattern 4: 검증 요청
    # ========================================

    validation_gate_request:
      pattern_id: "validation_gate"
      from_role: "structure_analyst"
      to_roles: ["quantifier", "validator", "guardian"]

      trigger:
        - "Phase 13: 최종 검증"

      request_template:
        gate_id: "GATE-YYYYMMDD-NN"
        artifacts_to_validate: "list[ART-ID]"
        validation_deadline: "datetime"

      validator_checklists:

        quantifier:
          - checklist_item: "계산 논리 타당성"
            criteria:
              - "공식이 맞는가?"
              - "4-Method 수렴하는가?"
              - "±30% 범위 내인가?"

          - checklist_item: "Bottom-up 합산 검증"
            criteria:
              - "BM별 합 = 전체?"
              - "도메인별 합 = 전체?"

        validator:
          - checklist_item: "데이터 신뢰성"
            criteria:
              - "SRC-ID 모두 부여?"
              - "신뢰도 평가 적절?"
              - "출처 추적 가능?"

          - checklist_item: "추정 방법론"
            criteria:
              - "EST-ID 명시?"
              - "추정 방법 합리적?"

        guardian:
          - checklist_item: "목표 정렬"
            criteria:
              - "초기 목표 달성?"
              - "UMIS 원칙 준수?"

          - checklist_item: "논리 건전성"
            criteria:
              - "MECE 준수?"
              - "완전한 추적성?"

      response_template:
        validator_role: "string"
        gate_id: "string"
        validation_result: "enum[pass, fail]"
        checked_items: "list[checklist_item_id]"
        issues_found: "list[issue]"
        recommendation: "string"

  # ========================================
  # 협업 워크플로 예시
  # ========================================

  collaboration_workflow_example:
    scenario: "Phase 5-7: 데이터 수집 → 시장규모 추정"

    sequence:
      - step: 1
        action: "structure_analyst → validator: data_collection_request"
        artifact: "REQ-data-001"

      - step: 2
        action: "validator: 데이터 수집 수행"
        duration: "2-3 days"
        output: "source_registry.yaml (SRC-001~005)"

      - step: 3
        action: "validator → structure_analyst: data_collection_response"
        artifact: "RSP-data-001"

      - step: 4
        action: "structure_analyst → quantifier: calculation_request"
        content: "Bottom-up 시장 규모 계산"

      - step: 5
        action: "quantifier → estimator: estimation_request (데이터 갭)"
        content: "비상장사 매출 추정"

      - step: 6
        action: "estimator: 추정 수행"
        output: "EST-001~050"

      - step: 7
        action: "quantifier: 4-Method Convergence"
        output: "ASM-total_market"

      - step: 8
        action: "structure_analyst → [quantifier, validator, guardian]: validation_gate"
        gate_id: "GATE-final"

      - step: 9
        action: "모든 검증자: 체크리스트 수행"
        output: "validation_results"

      - step: 10
        condition: "all pass"
        action: "structure_analyst: report_generation"
```

**umis_v9.yaml 수정**:

```yaml
role_plane:
  roles:
    - id: "structure_analyst"
      # ...
      collaboration_protocols_ref: "umis_v9_agent_protocols.yaml"
      can_request:
        - pattern: "data_collection_request"
          to_role: "validator"
        - pattern: "calculation_request"
          to_role: "quantifier"
        - pattern: "validation_gate_request"
          to_roles: ["quantifier", "validator", "guardian"]
```

---

### 갭 #3: 검증 게이트 메커니즘 부재 ⭐⭐⭐

#### 현재 v9 상태

```yaml
# umis_v9.yaml (1251-1271줄)
policy_engine:
  policies:
    modes:
      - id: "reporting_strict"
        quality_profile_ref: "reporting_strict"
      # ← 품질 프로파일은 있지만 검증 게이트가 없음
```

**문제점**:
- 언제, 누가, 무엇을 검증하는지 불명확
- 검증 실패 시 대응 방안 없음
- 품질 보증 메커니즘 부재

#### 보완 방안

**새 파일 생성**: `umis_v9_validation_gates.yaml`

```yaml
---
umis_v9_validation_gates:
  meta:
    description: "품질 보증을 위한 검증 게이트 정의"
    linked_to: "umis_v9.yaml#policy_engine"

  gate_types:

    # ========================================
    # Gate Type 1: MECE 검증
    # ========================================

    mece_validation:
      gate_type: "mece_validation"
      trigger: "분류 작업 완료 시 (Needs, Domain, BM 등)"
      validator: "structure_analyst (self-check) or guardian"

      checks:
        mutually_exclusive:
          description: "모든 항목이 상호 배타적인가?"
          method: "교집합 확인"
          criteria:
            - "각 항목이 하나의 카테고리에만 속함"
            - "중복 없음"

        collectively_exhaustive:
          description: "모든 경우를 빠짐없이 포함하는가?"
          method: "합집합 확인"
          criteria:
            - "합계 100%"
            - "'기타' 카테고리로 나머지 커버"

      pass_criteria:
        - "ME check: pass"
        - "CE check: pass"

      fail_action:
        - "분류 재수행"
        - "누락 항목 추가"

      example:
        artifact: "ART-domain_classification"
        validation:
          me_check:
            - "영어 ∩ 중국어 = ∅"
            - "영어 ∩ 일본어 = ∅"
            - result: "pass"
          ce_check:
            - "영어(75%) + 중국어(12.5%) + 일본어(7.5%) + ... + 기타(2%) = 100%"
            - result: "pass"

    # ========================================
    # Gate Type 2: 4-Method Convergence
    # ========================================

    four_method_convergence:
      gate_type: "quantitative_validation"
      trigger: "시장 규모 추정 완료"
      validator: "quantifier"

      methods:
        - id: "method_1"
          name: "Top-down"
          weight: 0.2

        - id: "method_2"
          name: "Bottom-up"
          weight: 0.4

        - id: "method_3"
          name: "Fermi"
          weight: 0.3

        - id: "method_4"
          name: "Analog/Benchmark"
          weight: 0.1

      convergence_check:
        formula: "가중 평균 계산"
        acceptable_range: "±30%"
        criteria:
          - "모든 방법이 ±50% 범위 내"
          - "가중 평균 ±30% 범위 확정"

      pass_criteria:
        - "Convergence within ±30%"

      fail_action:
        - "outlier method 재검토"
        - "가정 재확인"
        - "재계산"

      example:
        methods_results:
          - method: "Top-down"
            estimate: "1,500억"
            weight: 0.2
          - method: "Bottom-up"
            estimate: "10,000억"
            weight: 0.4
          - method: "Fermi"
            estimate: "13,000억"
            weight: 0.3
          - method: "Analog"
            estimate: "18,000억"
            weight: 0.1
        weighted_average: "10,000억"
        range: "7,000억 ~ 13,000억 (±30%)"
        validation: "pass"

    # ========================================
    # Gate Type 3: 데이터 신뢰성 검증
    # ========================================

    data_reliability_validation:
      gate_type: "data_quality"
      trigger: "Phase 7-1 완료 (데이터 수집)"
      validator: "validator"

      checks:
        source_coverage:
          description: "모든 데이터에 SRC-ID 부여?"
          criteria:
            - "SRC-ID 없는 데이터 0%"

        reliability_distribution:
          description: "신뢰도 분포가 적절한가?"
          target:
            - "≥80% 신뢰도: ≥50% (이상적)"
            - "≥70% 신뢰도: ≥70% (최소)"
          acceptable: "평균 신뢰도 ≥70%"

        traceability:
          description: "모든 출처 추적 가능한가?"
          criteria:
            - "URL/문서명 명시"
            - "접근 가능"

      pass_criteria:
        - "모든 데이터 SRC-ID 보유"
        - "평균 신뢰도 ≥70%"
        - "추적 가능"

      fail_action:
        - "신뢰도 낮은 데이터 재수집"
        - "SRC-ID 미부여 데이터 Registry 추가"

    # ========================================
    # Gate Type 4: 합산 검증
    # ========================================

    summation_validation:
      gate_type: "arithmetic_check"
      trigger: "Phase 12 MECE 검증"
      validator: "quantifier"

      checks:
        bm_summation:
          description: "BM별 합 = 전체?"
          formula: "Σ(BM 시장 규모) = 전체 시장 규모"
          tolerance: "±5%"

        domain_summation:
          description: "도메인별 합 = 전체?"
          formula: "Σ(도메인 시장 규모) = 전체 시장 규모"
          tolerance: "±5%"

        cross_check:
          description: "BM별 합 = 도메인별 합?"

      pass_criteria:
        - "모든 합산이 tolerance 내"

      fail_action:
        - "불일치 원인 파악"
        - "재계산"

    # ========================================
    # Gate Type 5: 최종 3자 검증
    # ========================================

    three_validator_gate:
      gate_type: "comprehensive_validation"
      trigger: "Phase 13"
      validators:
        - "quantifier"
        - "validator"
        - "guardian"

      validation_matrix:

        quantifier_checklist:
          role: "quantifier"
          responsibility: "정량 타당성"
          items:
            - id: "calc_logic"
              item: "계산 논리 타당성"
              check: "공식이 맞는가? 4-Method 수렴?"
              pass_criteria: "논리 오류 없음"

            - id: "convergence"
              item: "수렴 검증"
              check: "±30% 범위?"
              pass_criteria: "범위 내"

            - id: "summation"
              item: "합산 검증"
              check: "BM별 = 도메인별 = 전체?"
              pass_criteria: "±5% 일치"

        validator_checklist:
          role: "validator"
          responsibility: "데이터 신뢰성"
          items:
            - id: "source_quality"
              item: "출처 품질"
              check: "SRC-ID 모두 부여? 평균 신뢰도 ≥70%?"
              pass_criteria: "기준 충족"

            - id: "traceability"
              item: "추적성"
              check: "모든 주장에 근거?"
              pass_criteria: "100% 추적 가능"

            - id: "estimation_method"
              item: "추정 방법론"
              check: "EST-ID 명시? 방법 합리적?"
              pass_criteria: "방법론 적절"

        guardian_checklist:
          role: "guardian"
          responsibility: "논리 건전성"
          items:
            - id: "goal_alignment"
              item: "목표 정렬"
              check: "초기 목표 달성? 이탈 없음?"
              pass_criteria: "100% 정렬"

            - id: "umis_principles"
              item: "UMIS 원칙 준수"
              check: "MECE? Evidence-first? 완전한 추적성?"
              pass_criteria: "모든 원칙 준수"

            - id: "logic_soundness"
              item: "논리 건전성"
              check: "프로세스 순서 적절? 논리 비약 없음?"
              pass_criteria: "논리 건전"

            - id: "quality_grade"
              item: "품질 등급"
              check: "A/B/C 평가"
              pass_criteria: "≥B 등급"

      pass_criteria:
        require: "all_pass"
        condition: "모든 검증자가 모든 항목 통과"

      fail_action:
        if: "any_fail"
        then:
          - "실패 항목 식별"
          - "해당 Phase 재수행"
          - "재검증"

      output_format:
        validation_report:
          sections:
            - "검증자별 결과"
            - "통과/실패 항목"
            - "발견된 이슈"
            - "권고사항"
            - "최종 판정"

  # ========================================
  # 검증 게이트 적용 매트릭스
  # ========================================

  gate_application_matrix:
    by_phase:
      - phase_id: "PH02_domain_classification"
        gates: ["mece_validation"]

      - phase_id: "PH04_bm_enumeration"
        gates: ["mece_validation"]

      - phase_id: "PH07_market_sizing"
        gates: ["four_method_convergence"]

      - phase_id: "PH12_mece_validation"
        gates: ["mece_validation", "summation_validation"]

      - phase_id: "PH13_validation_gate"
        gates: ["three_validator_gate"]

  # ========================================
  # 품질 프로파일 연동
  # ========================================

  quality_profile_integration:
    description: "umis_v9.yaml의 quality_profiles과 검증 게이트 연동"

    reporting_strict:
      applicable_gates:
        - "data_reliability_validation"
        - "three_validator_gate"
      minimum_standards:
        - "평균 신뢰도 ≥80%"
        - "allow_prior: false"

    decision_balanced:
      applicable_gates:
        - "four_method_convergence"
        - "summation_validation"
      minimum_standards:
        - "평균 신뢰도 ≥70%"
        - "수렴 범위 ±30%"

    exploration_friendly:
      applicable_gates:
        - "mece_validation"
      minimum_standards:
        - "평균 신뢰도 ≥60%"
        - "논리 건전성 유지"
```

**umis_v9.yaml 수정**:

```yaml
policy_engine:
  policies:
    modes:
      - id: "reporting_strict"
        quality_profile_ref: "reporting_strict"
        validation_gates_ref: "umis_v9_validation_gates.yaml#reporting_strict"
```

---

### 갭 #4: 전략 프레임워크 라이브러리 부재 ⭐⭐⭐

#### 현재 v9 상태

- Pattern Graph에 패턴 정의는 있으나 실제 전략 분석 프레임워크 없음
- Strategy Engine이 어떤 이론/방법론을 사용할지 불명확

#### 보완 방안

**파일 이식**: `reference/Observer_v7.x/umis_strategic_frameworks.yaml` → `frameworks/umis_v9_strategic_frameworks.yaml`

**추가 작업**: v9 Pattern Graph와 연결

```yaml
# frameworks/umis_v9_strategic_frameworks.yaml

strategic_frameworks:

  # v7 내용 그대로 이식 + v9 연결 추가

  porters_five_forces:
    _id: "porters_five_forces"
    _source: "Michael Porter (1979)"

    # v7 내용...

    # v9 추가: Pattern Graph 연동
    pattern_graph_mapping:
      competition_intensity:
        maps_to: "pattern_graph.node.pattern.traits"
        trait_keys:
          - "competition_intensity"
          - "market_growth_rate"
          - "differentiation_level"

      entry_barriers:
        maps_to: "pattern_graph.node.pattern.traits"
        trait_keys:
          - "capital_requirement"
          - "regulatory_barrier"
          - "brand_importance"

    # v9 추가: Strategy Engine 사용법
    strategy_engine_usage:
      when_to_use: "새 시장 진입 전 매력도 평가"
      workflow_integration:
        phase: "opportunity_discovery"
        step: "market_attractiveness_assessment"
      
      api_call:
        engine: "strategy_engine"
        function: "evaluate_market_attractiveness"
        inputs:
          - "reality_graph_slice"
          - "framework_id: porters_five_forces"
        outputs:
          - "attractiveness_score"
          - "force_ratings"

  blue_ocean_strategy:
    # v7 내용...

    pattern_graph_mapping:
      value_innovation:
        creates_new_pattern:
          pattern_id: "PAT-blue_ocean_model"
          traits:
            - eliminate: [...]
            - reduce: [...]
            - raise: [...]
            - create: [...]

  # ... 30개 프레임워크 모두 이식
```

---

### 갭 #5: 가치사슬 분석 템플릿 부재 ⭐⭐

#### 보완 방안

**새 파일 생성**: `frameworks/umis_v9_value_chain_templates.yaml`

```yaml
---
umis_v9_value_chain_templates:
  meta:
    description: "BM별 가치사슬 분석 템플릿 및 방법론"

  analysis_framework:

    template_structure:
      stages:
        description: "가치사슬 단계 정의"
        common_stages:
          - "sourcing"
          - "production/operation"
          - "distribution"
          - "marketing_sales"
          - "service"

      for_each_stage:
        analyze:
          - field: "activities"
            description: "이 단계에서 수행되는 활동"

          - field: "cost_share"
            description: "전체 비용 중 비중 (%)"
            estimation_needed: true

          - field: "margin"
            description: "이 단계의 마진율 (%)"
            estimation_needed: true

          - field: "actors"
            description: "이 단계의 주요 행위자"
            links_to: "reality_graph.actor"

          - field: "inefficiencies"
            description: "비효율 지점 식별"

          - field: "disruption_opportunities"
            description: "혁신/개선 기회"

    money_flow_tracking:
      description: "돈의 흐름 추적 (누가→누구→얼마)"

      template:
        flow_id: "MFL-XXXXXX"
        from_actor: "actor_id"
        to_actor: "actor_id"
        amount:
          quantity_id: "QTY-XXXXXX"
          kind: "money"
          amount: "number"
          currency: "string"
          per: "string"
        recurrence: "enum"
        margin_estimation:
          gross_margin: "float"
          net_margin: "float"
          basis: "SRC-ID or EST-ID"

    benchmarking:
      use: "value_chain_benchmarks.yaml"
      match_by:
        - "industry"
        - "business_model"
        - "revenue_model"

  # BM별 템플릿 예시

  bm_templates:

    saas_b2b:
      template_id: "saas_b2b_value_chain"
      
      stages:
        product_development:
          typical_cost_share: "30%"
          activities:
            - "R&D"
            - "Engineering"
          
        cloud_infrastructure:
          typical_cost_share: "15%"
          
        sales_marketing:
          typical_cost_share: "45%"
          note: "B2B SaaS는 S&M 비중 높음"
          
        customer_success:
          typical_cost_share: "5%"

      typical_margins:
        gross_margin: "75-85%"
        operating_margin: "5-15%"

      unit_economics_template:
        metrics:
          - "ACV (Annual Contract Value)"
          - "CAC (Customer Acquisition Cost)"
          - "LTV (Lifetime Value)"
          - "LTV/CAC ratio"
          - "Payback Period"

      reference_benchmark: "VCH_IT_001"

    ecommerce_1p:
      template_id: "ecommerce_inventory_model"
      
      stages:
        sourcing:
          typical_cost_share: "60-70%"
          
        warehousing:
          typical_cost_share: "5-7%"
          
        last_mile_delivery:
          typical_cost_share: "8-12%"
          
        marketing:
          typical_cost_share: "3-5%"

      typical_margins:
        gross_margin: "15-20%"
        contribution_margin: "10-12%"

      reference_benchmark: "VCH_RET_001"

  # Phase 6 실행 가이드

  phase_6_execution_guide:
    
    step_1_identify_stages:
      action: "BM에 맞는 template 선택"
      if_no_template: "common_stages 사용"

    step_2_map_actors:
      action: "각 stage의 actor를 Reality Graph에서 식별"
      create:
        - "actor nodes (if not exist)"
        - "money_flow edges"

    step_3_estimate_costs:
      for_each_stage:
        - "benchmark 참조"
        - "확정 데이터 우선 (SRC-ID)"
        - "없으면 Estimator 요청 (EST-ID)"

    step_4_calculate_margins:
      formula: "Margin = (Revenue - Cost) / Revenue"
      track: "gross_margin, operating_margin, net_margin"

    step_5_identify_inefficiencies:
      questions:
        - "어느 단계가 비용 비중이 높은가?"
        - "업계 벤치마크 대비 어떤가?"
        - "비효율 지점은?"

    step_6_find_opportunities:
      questions:
        - "어느 단계를 제거/축소할 수 있는가?"
        - "수직 통합 기회는?"
        - "자동화 기회는?"
```

---

## 4. 구현 로드맵

### Phase별 파일 추가 계획

#### Sprint 2 (현재) → Sprint 3 전환 전

**Priority 1 파일 생성**:

```bash
# 1. Process Phases
touch umis_v9_process_phases.yaml
# 내용: 14 Phase 상세 정의

# 2. Agent Protocols
touch umis_v9_agent_protocols.yaml
# 내용: 협업 패턴, 요청/응답 템플릿

# 3. Validation Gates
touch umis_v9_validation_gates.yaml
# 내용: 검증 게이트 메커니즘
```

#### Sprint 3 (EvidenceEngine + WorldEngine) 중

**Priority 2 파일 생성**:

```bash
mkdir -p frameworks benchmarks schemas

# 4. Strategic Frameworks
cp reference/Observer_v7.x/umis_strategic_frameworks.yaml \
   frameworks/umis_v9_strategic_frameworks.yaml
# 수정: Pattern Graph 연동 추가

# 5. Value Chain Templates
touch frameworks/umis_v9_value_chain_templates.yaml

# 6. Data Quality Framework
touch schemas/umis_v9_data_quality.yaml
```

#### Sprint 4 (ValueEngine) 전

**Priority 3 파일 생성**:

```bash
# 7. Industry Benchmarks
cp reference/Observer_v7.x/value_chain_benchmarks.yaml \
   benchmarks/umis_v9_industry_benchmarks.yaml
# 확장: v9 Pattern에 맞게 재구조화

# 8. BM Classification
touch frameworks/umis_v9_bm_classification.yaml

# 9. ID Management
touch schemas/umis_v9_id_management.yaml

# 10. Output Formats
touch schemas/umis_v9_output_formats.yaml
```

### 최종 파일 구조

```
umis_v9_dev/
├── umis_v9.yaml                          # ✅ Core schema
├── umis_v9_philosophy_concept.md         # ✅ Philosophy
├── umis_v9_roadmap.md                    # ✅ Roadmap
│
├── umis_v9_process_phases.yaml           # ⭐ NEW (P1)
├── umis_v9_agent_protocols.yaml          # ⭐ NEW (P1)
├── umis_v9_validation_gates.yaml         # ⭐ NEW (P1)
│
├── frameworks/
│   ├── umis_v9_strategic_frameworks.yaml # ⭐ NEW (P2, from v7)
│   ├── umis_v9_value_chain_templates.yaml# ⭐ NEW (P2)
│   └── umis_v9_bm_classification.yaml    # ⭐ NEW (P3)
│
├── benchmarks/
│   └── umis_v9_industry_benchmarks.yaml  # ⭐ NEW (P3, from v7)
│
├── schemas/
│   ├── umis_v9_data_quality.yaml         # ⭐ NEW (P2)
│   ├── umis_v9_id_management.yaml        # ⭐ NEW (P3)
│   └── umis_v9_output_formats.yaml       # ⭐ NEW (P3)
│
├── umis_v9_core/
│   ├── graph.py
│   └── world_engine_poc.py
│
├── seeds/
├── domain_registry.yaml
└── validation_guidelines.yaml
```

---

## 5. 실행 체크리스트

### Phase 2 완료 전 (현재)

- [ ] `umis_v9_process_phases.yaml` 작성 완료
  - [ ] structure_analysis 14 Phase 정의
  - [ ] opportunity_discovery Phase 정의
  - [ ] 각 Phase별 입력/출력/검증 기준 명시

- [ ] `umis_v9_agent_protocols.yaml` 작성 완료
  - [ ] data_collection_request 템플릿
  - [ ] estimation_request 템플릿
  - [ ] calculation_request 템플릿
  - [ ] validation_gate_request 템플릿

- [ ] `umis_v9_validation_gates.yaml` 작성 완료
  - [ ] MECE validation gate
  - [ ] 4-Method convergence gate
  - [ ] Data reliability gate
  - [ ] 3-validator gate

- [ ] `umis_v9.yaml` 수정
  - [ ] canonical_workflows에 process_phases_ref 추가
  - [ ] role_plane에 collaboration_protocols_ref 추가
  - [ ] policy_engine에 validation_gates_ref 추가

### Phase 3 구현 중

- [ ] `umis_v9_strategic_frameworks.yaml` 이식/확장
  - [ ] v7 30개 프레임워크 복사
  - [ ] Pattern Graph 연동 추가
  - [ ] Strategy Engine 사용법 명시

- [ ] `umis_v9_value_chain_templates.yaml` 작성
  - [ ] 분석 프레임워크 정의
  - [ ] BM별 템플릿 (최소 5개)
  - [ ] Phase 6 실행 가이드

- [ ] `umis_v9_data_quality.yaml` 작성
  - [ ] 신뢰도 등급 체계
  - [ ] Source Registry 스키마
  - [ ] Estimation 방법론

### Phase 4 구현 전

- [ ] `umis_v9_industry_benchmarks.yaml` 이식/확장
  - [ ] v7 50개 벤치마크 복사
  - [ ] Pattern 연동 추가

- [ ] 나머지 schemas 작성
  - [ ] BM classification framework
  - [ ] ID management rules
  - [ ] Output formats

---

### 갭 #6: 데이터 품질 관리 체계 미흡 ⭐⭐

#### 현재 v9 상태

```yaml
# umis_v9.yaml (461-471줄)
stores:
  evidence_store:
    schema:
      fields:
        evidence_id: { type: "string", required: true }
        source_tier: { type: "enum", values: ["official","curated_internal",...] }
        # ← source_tier 정의는 있으나 신뢰도 점수 계산 방법 없음
```

#### v7 실제 사용

```yaml
# Rachel이 사용한 신뢰도 등급
| 신뢰도 | 출처 유형 | 예시 |
|-------|---------|------|
| 90-100 | 공식 공시/정부 통계 | DART, 통계청, 공정위 |
| 80-89 | 업계 보고서 (증권사) | IBK, KB 리포트 |
| 70-79 | 주요 언론 보도 | 매출 발표, IR 자료 |
| 60-69 | 협회/단체 자료 | 학원연합회 통계 |
| 50-59 | 설문조사/연구 | 학술 논문, 시장조사 |
| <50 | 추정/소문 | 사용 제한 |
```

#### 보완 방안

**새 파일 생성**: `schemas/umis_v9_data_quality.yaml`

```yaml
---
umis_v9_data_quality:
  meta:
    description: "Evidence/Data 품질 관리 프레임워크"

  # ========================================
  # 신뢰도 등급 체계
  # ========================================

  reliability_scoring:

    scale:
      range: "0-100"
      description: "숫자가 높을수록 신뢰도 높음"

    tier_mapping:
      source_tier_to_score:
        official:
          base_score: 95
          range: "90-100"
          examples:
            - "DART 전자공시"
            - "통계청 공식 통계"
            - "정부 부처 공개 자료"

        curated_internal:
          base_score: 85
          range: "80-90"
          examples:
            - "내부 검증된 데이터"
            - "자체 수집 1차 데이터"

        commercial:
          base_score: 75
          range: "70-85"
          examples:
            - "증권사 리포트"
            - "시장조사기관 보고서"
            - "컨설팅사 보고서"

        structured_estimation:
          base_score: 65
          range: "60-75"
          examples:
            - "Fermi 추정"
            - "구조적 모델 기반"

        llm_baseline:
          base_score: 50
          range: "40-60"
          examples:
            - "LLM Prior (검증 없음)"
            - "일반적 상식"

        other:
          base_score: 30
          range: "0-50"

    adjustment_factors:
      freshness:
        - condition: "data_age < 1 year"
          adjustment: "+5"
        - condition: "1 year ≤ data_age < 3 years"
          adjustment: "0"
        - condition: "data_age ≥ 3 years"
          adjustment: "-10"

      verification:
        - condition: "cross_verified (2+ sources)"
          adjustment: "+10"
        - condition: "single_source"
          adjustment: "0"

      specificity:
        - condition: "exact_match (metric/context 정확)"
          adjustment: "+5"
        - condition: "requires_interpretation"
          adjustment: "-5"

    final_score_calculation:
      formula: "base_score + Σ(adjustments)"
      clamp: "[0, 100]"

  # ========================================
  # Source Registry 스키마
  # ========================================

  source_registry_schema:

    file_format: "yaml"
    filename_pattern: "source_registry_{domain_id}_{YYYYMMDD}.yaml"

    entry_schema:
      SRC_ID:
        format: "SRC_YYYYMMDD_NNN"
        fields:
          source_type:
            type: "string"
            examples: ["공시자료", "기업 발표", "정부 통계", "리서치 보고서"]

          organization:
            type: "string"
            description: "발행 기관/회사"

          document_name:
            type: "string"

          publication_date:
            type: "date"
            format: "YYYY-MM-DD"

          url:
            type: "string"
            required: false

          reliability_score:
            type: "int"
            range: "0-100"
            calculation_ref: "reliability_scoring"

          data_points:
            type: "list[string]"
            description: "이 소스에서 추출한 구체적 데이터"

          notes:
            type: "string"
            required: false

          retrieved_at:
            type: "datetime"

          tags:
            type: "list[string]"
            examples: ["market_size", "player_revenue", "cost_structure"]

    example:
      SRC_20251205_001:
        source_type: "공시자료"
        organization: "YBM넷"
        document_name: "2023년 사업보고서"
        publication_date: "2024-03-31"
        url: "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240331..."
        reliability_score: 95
        data_points:
          - "2023 매출액: 81,728,516,256원"
          - "사업부문: 어학교육, 출판, 기타"
        notes: "사업부문별 매출 세부 공개 안 됨, 전체 매출만 확정"
        retrieved_at: "2025-12-05T10:30:00"
        tags: ["player_revenue", "Adult_Language_Education_KR"]

  # ========================================
  # Estimation Registry 스키마
  # ========================================

  estimation_registry_schema:

    entry_schema:
      EST_ID:
        format: "EST_YYYYMMDD_NNN"
        fields:
          estimation_type:
            type: "enum"
            values: ["fermi", "bottom_up", "top_down", "analog", "fusion"]

          question:
            type: "string"
            description: "명확한 추정 대상"

          method:
            type: "string"
            description: "사용한 추정 방법 상세"

          inputs:
            known_data: "dict[SRC-ID or VAL-ID]"
            assumptions: "list[ASM-ID]"

          calculation:
            formula: "string"
            steps: "list[string]"

          result:
            point_estimate: "number"
            range: "dict{low, high}"
            confidence: "float (0-1)"

          reliability_score:
            type: "int"
            range: "40-75"
            note: "추정은 확정 데이터보다 신뢰도 낮음"

          lineage:
            from_evidence_ids: "list[SRC-ID]"
            from_estimation_ids: "list[EST-ID]"
            engine_id: "string"

    example:
      EST_20251205_102:
        estimation_type: "analog"
        question: "파고다어학원 2023년 매출액은?"
        method: "유사 기업 비교 + 성장률 적용"
        inputs:
          known_data:
            SRC_20251205_001: "YBM 2023 매출 817억"
            SRC_20251205_010: "파고다 2012 매출 53억 (과거)"
          assumptions:
            ASM_20251205_050: "어학 시장 CAGR 5-10%"
        calculation:
          formula: "과거 매출 × (1 + CAGR)^years × 상대적 규모 조정"
          steps:
            - "2012→2023: 11년"
            - "53억 × (1.075)^11 = 115억 (성장률만)"
            - "YBM/파고다 규모 비율 고려 (파고다가 YBM의 60% 수준)"
            - "최종: 300억 추정"
        result:
          point_estimate: 300억
          range:
            low: 250억
            high: 350억
          confidence: 0.65
        reliability_score: 65
        lineage:
          from_evidence_ids: ["SRC_20251205_001", "SRC_20251205_010"]
          engine_id: "estimator_fermi"

  # ========================================
  # Assumption Registry 스키마
  # ========================================

  assumption_registry_schema:

    entry_schema:
      ASM_ID:
        format: "ASM_YYYYMMDD_NNN"
        fields:
          assumption_statement:
            type: "string"
            description: "명확한 가정 진술"

          basis:
            type: "enum"
            values: ["calculation", "convergence", "industry_benchmark", "expert_judgment"]

          supporting_evidence:
            type: "list[SRC-ID or EST-ID]"

          confidence:
            type: "float"
            range: "0-1"

          usage:
            type: "list[VAL-ID or EST-ID]"
            description: "이 가정을 사용한 값/추정 목록"

    example:
      ASM_20251205_100:
        assumption_statement: "한국 성인 어학교육 시장 전체 규모 1조원 (±30%)"
        basis: "convergence"
        supporting_evidence:
          - "EST_20251205_100"  # Top-down
          - "EST_20251205_200"  # Bottom-up
          - "EST_20251205_300"  # Fermi
          - "EST_20251205_400"  # Analog
        confidence: 0.75
        usage:
          - "ASM_20251205_110"  # BM별 시장 규모
          - "ASM_20251205_500"  # 도메인별 비율

  # ========================================
  # 품질 프로파일 적용
  # ========================================

  quality_profile_application:

    reporting_strict:
      minimum_requirements:
        average_reliability: 80
        allow_estimation: false
        require_multi_source: true

      validation:
        - "모든 핵심 데이터 SRC-ID 보유"
        - "평균 신뢰도 ≥80%"
        - "추정 비율 <20%"

    decision_balanced:
      minimum_requirements:
        average_reliability: 70
        allow_estimation: true
        estimation_reliability_min: 60

      validation:
        - "평균 신뢰도 ≥70%"
        - "추정 방법론 명시"
        - "4-Method Convergence (if applicable)"

    exploration_friendly:
      minimum_requirements:
        average_reliability: 60
        allow_estimation: true
        allow_llm_prior: true

      validation:
        - "평균 신뢰도 ≥60%"
        - "논리적 건전성 유지"
        - "Lineage 추적 가능"
```

---

### 갭 #7: 산업별 벤치마크 데이터 부재 ⭐⭐

#### 현재 v9 상태

- Pattern Graph 정의는 있으나 실제 벤치마크 없음
- 패턴별 비용 구조/마진율 데이터 없음

#### v7 자산

`value_chain_benchmarks.yaml`: 50개 산업별 가치사슬 벤치마크
- 제조업 10개, 유통 12개, 서비스 10개, IT 10개, 플랫폼 8개
- 각 벤치마크: 비용 구조, 마진율, 경쟁 구조, 최적화 전략

#### 보완 방안

**새 파일 생성**: `benchmarks/umis_v9_pattern_benchmarks.yaml`

```yaml
---
umis_v9_pattern_benchmarks:
  meta:
    description: "Pattern별 비용 구조/마진율/경쟁 구조 벤치마크"
    source: "value_chain_benchmarks.yaml + 신규 추가"
    linked_to: "umis_v9.yaml#pattern_graph"

  # ========================================
  # Pattern 벤치마크
  # ========================================

  patterns:

    saas_like_model:
      pattern_id: "PAT-SaaS_like_model"
      
      linked_benchmarks:
        - "VCH_IT_001"  # Salesforce (B2B SaaS)
        - "VCH_IT_004"  # SMB SaaS
        - "VCH_IT_005"  # Enterprise SaaS

      typical_cost_structure:
        cogs:
          range: "15-25%"
          median: "20%"
          components:
            - "Cloud infrastructure: 10-15%"
            - "Support: 3-5%"
            - "Other: 2-5%"

        r_and_d:
          range: "15-30%"
          median: "25%"
          note: "제품 개발, 엔지니어링"

        sales_marketing:
          range: "30-50%"
          median: "40%"
          breakdown:
            sales_team: "20-30%"
            marketing: "10-20%"
          note: "B2B는 S&M 비중 매우 높음"

        g_and_a:
          range: "10-15%"
          median: "12%"

      typical_margins:
        gross_margin:
          range: "75-85%"
          median: "80%"
        operating_margin:
          range: "5-15%"
          median: "10%"
        note: "소프트웨어 특성상 gross margin 높음"

      unit_economics_benchmarks:
        acv:
          b2b_smb: "$5,000-20,000"
          b2b_mid: "$20,000-100,000"
          b2b_enterprise: "$100,000-1,000,000"

        cac:
          b2b_smb: "$1,000-5,000"
          b2b_mid: "$5,000-20,000"
          b2b_enterprise: "$20,000-100,000"

        ltv_cac_ratio:
          healthy: ">3"
          typical: "3-10"

        payback_period:
          healthy: "<12 months"
          typical: "4-18 months"

      competitive_structure:
        typical_cr3: "40-60%"
        typical_hhi: "800-1,500"
        entry_barriers: "medium-high"
        key_moats:
          - "Switching cost"
          - "Data network effects"
          - "Brand"

      trait_constraints:
        required:
          revenue_model: ["subscription", "usage_based"]
          payment_recurs: true
          marginal_cost_profile: "low"
        typical:
          delivery_channel: "online"
          inventory_risk: "low"

    marketplace_model:
      pattern_id: "PAT-Marketplace_model"

      linked_benchmarks:
        - "VCH_PLT_001"  # 배달의민족
        - "VCH_PLT_002"  # Amazon Marketplace
        - "VCH_RET_002"  # Naver Shopping

      typical_cost_structure:
        platform_operations:
          range: "30-40%"
          components:
            - "Technology: 20-25%"
            - "Customer support: 5-10%"
            - "Payment processing: 2-3%"

        marketing:
          range: "20-30%"
          note: "양쪽 획득 (supply + demand)"

        sales:
          range: "10-15%"
          note: "판매자 온보딩"

      typical_margins:
        gross_margin:
          range: "80-90%"
          median: "85%"
        operating_margin:
          range: "15-30%"
          median: "20%"

      revenue_model:
        take_rate:
          range: "10-30%"
          by_category:
            high_touch: "20-30%"
            low_touch: "10-15%"
            payment_only: "2-5%"

      unit_economics_benchmarks:
        gmv_per_active_user:
          range: "$100-1,000/year"

        take_rate:
          typical: "15%"

        ltv:
          calculation: "GMV × take_rate × retention_years"

      competitive_structure:
        typical_cr3: "50-70%"
        winner_takes_most: true
        network_effects: "strong"

    offline_subscription_like:
      pattern_id: "PAT-Offline_subscription_like"

      description: "오프라인 정기 서비스 (건물관리, 헬스, 학원 등)"

      typical_cost_structure:
        labor:
          range: "40-60%"
          median: "50%"
          note: "사람 중심 서비스"

        facilities:
          range: "20-35%"
          median: "25%"
          components:
            - "임대료: 15-25%"
            - "시설/장비: 5-10%"

        materials_supplies:
          range: "5-15%"
          median: "10%"

        marketing:
          range: "5-10%"
          median: "7%"

      typical_margins:
        gross_margin:
          range: "30-50%"
          median: "40%"
        operating_margin:
          range: "10-20%"
          median: "15%"

      unit_economics_benchmarks:
        arpu:
          range: "월 10-50만원"
          by_service:
            fitness: "월 5-15만원"
            education: "월 20-60만원"
            building_maintenance: "월 100-500만원"

        churn_rate:
          monthly: "3-8%"
          annual: "30-60%"

        ltv:
          calculation: "ARPU × margin × (1/churn)"
          typical: "150-300만원"

      trait_constraints:
        required:
          revenue_model: "subscription"
          payment_recurs: true
          requires_physical_presence: true
        typical:
          delivery_channel: ["offline", "hybrid"]
          marginal_cost_profile: ["medium", "high"]

    ecommerce_inventory_model:
      pattern_id: "PAT-Ecommerce_1P"

      linked_benchmarks:
        - "VCH_RET_001"  # Coupang

      typical_cost_structure:
        cogs:
          range: "60-75%"
          median: "68%"

        fulfillment:
          range: "10-20%"
          median: "15%"
          breakdown:
            warehousing: "5-7%"
            last_mile: "8-12%"

        marketing:
          range: "3-5%"

      typical_margins:
        gross_margin: "15-25%"
        contribution_margin: "10-15%"

      unit_economics_benchmarks:
        aov: "평균 3만원"
        delivery_cost: "3,000-4,000원"
        contribution_per_order: "3,000-4,000원"

  # ========================================
  # Usage: Pattern Engine 연동
  # ========================================

  pattern_engine_integration:

    match_patterns_with_benchmarks:
      description: "R-Graph의 Actor/Business를 패턴에 매칭할 때 벤치마크 참조"

      process:
        - step: 1
          action: "Actor traits 추출"
          example:
            actor_id: "ACT-OnlinePlatform_Top1"
            traits:
              revenue_model: "subscription"
              delivery_channel: "online"
              marginal_cost_profile: "low"

        - step: 2
          action: "Pattern 후보 찾기 (trait 유사도)"
          candidates:
            - pattern_id: "PAT-SaaS_like_model"
              match_score: 0.85
            - pattern_id: "PAT-Marketplace_model"
              match_score: 0.30

        - step: 3
          action: "Best match pattern의 benchmark 적용"
          selected: "PAT-SaaS_like_model"
          apply_benchmarks:
            - "typical_cost_structure"
            - "typical_margins"
            - "unit_economics_benchmarks"

        - step: 4
          action: "Metric Resolver에 Prior 제공"
          example:
            metric_request: "MET-Gross_margin"
            context: { actor_id: "ACT-OnlinePlatform_Top1" }
            prior_from_benchmark:
              distribution: "normal(mean=80%, std=5%)"
              source: "PAT-SaaS_like_model benchmark"
```

**Pattern Graph 수정**:

```yaml
# umis_v9.yaml 수정
pattern_graph:
  node_types:
    pattern:
      fields:
        pattern_id: { ... }
        benchmark_ref:
          type: "benchmark_id"
          description: "이 패턴의 산업 벤치마크 참조"
          file: "benchmarks/umis_v9_pattern_benchmarks.yaml"
```

---

### 갭 #8: BM 분류 프레임워크 상세 부족 ⭐⭐

#### v7 실제 사용

**3-Axis Framework**:
- Axis 1: Delivery Channel (오프라인/온라인/하이브리드/물리적제품)
- Axis 2: Interaction Type (실시간/비실시간/독학/혼합)
- Axis 3: Transaction Structure (B2C직접/B2C플랫폼/B2B/B2G)

→ 23개 BM 완전 분류

#### 보완 방안

**새 파일 생성**: `frameworks/umis_v9_bm_classification.yaml`

```yaml
---
umis_v9_bm_classification:
  meta:
    description: "비즈니스 모델 분류 프레임워크"

  classification_framework:

    axes:
      - axis_id: "delivery_channel"
        name: "가치 전달 방식"
        values:
          - "offline"
          - "online"
          - "hybrid"
          - "physical_product"
        maps_to: "ontology.traits.core_traits.delivery_channel"

      - axis_id: "interaction_type"
        name: "상호작용 방식"
        values:
          - "live"
          - "recorded"
          - "self_study"
          - "mixed"

      - axis_id: "transaction_structure"
        name: "거래 구조"
        values:
          - "b2c_direct"
          - "b2c_platform"
          - "b2b"
          - "b2g"

    bm_matrix:
      description: "3-Axis 조합으로 모든 BM 정의"

      example_bm_definitions:
        - bm_id: "BM-SaaS_standard"
          name: "표준 B2B SaaS"
          axes:
            delivery_channel: "online"
            interaction_type: "mixed"
            transaction_structure: "b2b"
          pattern_ref: "PAT-SaaS_like_model"

        - bm_id: "BM-Offline_academy"
          name: "오프라인 학원"
          axes:
            delivery_channel: "offline"
            interaction_type: "live"
            transaction_structure: "b2c_direct"
          pattern_ref: "PAT-Offline_subscription_like"

    mece_validation_rules:
      mutually_exclusive:
        - "각 BM은 3-Axis 조합으로 unique하게 정의"
        - "같은 조합 = 같은 BM"

      collectively_exhaustive:
        - "모든 가능한 조합 검토"
        - "관찰 불가능한 조합 제외 (근거 명시)"
        - "Edge Cases 검토 완료"
```

---

### 갭 #9: ID 생성/관리 규칙 상세 부족 ⭐⭐

#### 현재 v9 상태

```yaml
# umis_v9.yaml (1277-1297줄)
ids_and_lineage:
  id_prefixes:
    evidence: "EVD-"
    # ... 나열만 있음
    # ← 실제 생성 알고리즘 없음
```

#### 보완 방안

**새 파일 생성**: `schemas/umis_v9_id_management.yaml`

```yaml
---
umis_v9_id_management:
  meta:
    description: "ID 생성, 관리, Registry 규칙"

  # ========================================
  # ID 생성 규칙
  # ========================================

  id_generation_rules:

    format_patterns:

      evidence:
        prefix: "EVD-"
        pattern: "EVD-YYYYMMDD-NNN"
        example: "EVD-20251205-001"
        counter_scope: "per_day"
        zero_padding: 3

      source:
        prefix: "SRC_"
        pattern: "SRC_YYYYMMDD_NNN"
        example: "SRC_20251205_001"
        note: "v7 호환 (언더스코어 사용)"

      estimation:
        prefix: "EST-"
        pattern: "EST-YYYYMMDD-NNN"
        example: "EST-20251205-001"

      assumption:
        prefix: "ASM-"
        pattern: "ASM-YYYYMMDD-NNN"
        example: "ASM-20251205-100"

      value:
        prefix: "VAL-"
        pattern: "VAL-{metric_id}-{context_hash}-{timestamp}"
        example: "VAL-MET_TAM-ctx_a3f9-20251205T103045"
        note: "ValueRecord는 재계산 가능하도록 결정적 ID"

      artifact:
        prefix: "ART-"
        pattern: "ART-{workflow_id}-{phase_id}-{YYYYMMDD}"
        example: "ART-structure_analysis-PH06-20251205"

    id_allocation_service:
      description: "ID 자동 생성 및 충돌 방지"

      implementation_pseudo_code: |
        class IDAllocator:
          def __init__(self):
            self.counters = {}  # {prefix}_{date} -> counter
          
          def allocate(self, prefix: str) -> str:
            today = datetime.now().strftime("%Y%m%d")
            key = f"{prefix}_{today}"
            
            if key not in self.counters:
              self.counters[key] = 0
            
            self.counters[key] += 1
            counter = self.counters[key]
            
            return f"{prefix}{today}-{counter:03d}"

  # ========================================
  # Registry 파일 규칙
  # ========================================

  registry_file_rules:

    source_registry:
      filename: "source_registry_{domain_id}.yaml"
      location: "stores/evidence/"
      schema: "schemas/umis_v9_data_quality.yaml#source_registry_schema"
      
      lifecycle:
        creation: "Validator가 데이터 수집 시 생성"
        update: "추가 데이터 수집 시 append"
        archival: "프로젝트 완료 시 Evidence Store에 영구 저장"

    estimation_registry:
      filename: "estimation_registry_{domain_id}.yaml"
      location: "stores/value/"
      schema: "schemas/umis_v9_data_quality.yaml#estimation_registry_schema"

    assumption_registry:
      filename: "assumption_registry_{domain_id}.yaml"
      location: "stores/value/"
      schema: "schemas/umis_v9_data_quality.yaml#assumption_registry_schema"

  # ========================================
  # Lineage 추적 규칙
  # ========================================

  lineage_tracking:

    lineage_schema:
      description: "umis_v9.yaml#lineage_schema 구현 상세"

      fields:
        from_evidence_ids:
          type: "list[SRC-ID or EVD-ID]"
          description: "이 값이 기반한 Evidence"

        from_value_ids:
          type: "list[VAL-ID]"
          description: "이 값이 기반한 다른 값 (Derived 계산)"

        from_estimation_ids:
          type: "list[EST-ID]"
          description: "이 값이 사용한 추정"

        from_assumption_ids:
          type: "list[ASM-ID]"
          description: "이 값이 전제한 가정"

        from_pattern_ids:
          type: "list[PAT-ID]"
          description: "이 값이 참조한 패턴 (Prior)"

        from_program_id:
          type: "string"
          description: "Value Program ID (추론 trace)"

        engine_ids:
          type: "list[string]"
          description: "거쳐간 엔진"

        policy_id:
          type: "string"

        created_by_role:
          type: "role_id"

        created_at:
          type: "datetime"

    lineage_graph:
      description: "Lineage를 그래프로 시각화 가능"

      example:
        val_id: "VAL-MET_TAM-ctx_kr_adult_lang-20251205"
        lineage_trace: |
          VAL-MET_TAM
            ├─ from_value_ids:
            │   ├─ VAL-MET_N_customers (Bottom-up)
            │   │   ├─ from_evidence_ids:
            │   │   │   └─ SRC_20251205_020 (통계청 인구)
            │   │   └─ from_estimation_ids:
            │   │       └─ EST_20251205_050 (참여율 추정)
            │   └─ VAL-MET_ARPU
            │       ├─ from_evidence_ids:
            │       │   └─ SRC_20251205_030 (학원 수강료)
            │       └─ from_pattern_ids:
            │           └─ PAT-Offline_subscription (ARPU 범위)
            └─ from_assumption_ids:
                └─ ASM_20251205_100 (시장 1조원)

    explainability:
      description: "사용자에게 '왜 이 값인가?' 설명"

      explanation_template: |
        **이 값이 나온 이유:**

        1. 확정 데이터 (SRC-ID):
           - [SRC 목록]

        2. 파생 계산 (VAL-ID):
           - [계산 경로]

        3. 추정 (EST-ID):
           - [추정 방법]

        4. 가정 (ASM-ID):
           - [주요 가정]

        5. 참조 패턴 (PAT-ID):
           - [벤치마크]
```

---

### 갭 #10: Output 포맷 표준화 부족 ⭐⭐

#### v7 실제 Output

9개 파일 구조:
1. Guardian Work Log
2. Market Structure Analysis Progress
3. Rachel Data Request
4. Rachel Data Collection Results
5. Value Chain Mapping
6. Market Size Estimation
7. Competition Analysis
8. Final Validation
9. Market Reality Report Final

각 파일: 명확한 섹션 구조, 일관된 포맷

#### 보완 방안

**새 파일 생성**: `schemas/umis_v9_output_formats.yaml`

```yaml
---
umis_v9_output_formats:
  meta:
    description: "Role별 산출물 표준 포맷"

  # ========================================
  # Market Reality Report
  # ========================================

  market_reality_report:
    artifact_type: "final_report"
    role: "structure_analyst"
    workflow: "structure_analysis"
    format: "markdown"

    template_structure:

      front_matter:
        - "제목"
        - "작성자 (Agent names)"
        - "작성일"
        - "버전"
        - "검증 상태"

      executive_summary:
        max_length: "1-2 pages"
        required_sections:
          - "시장 정의"
          - "핵심 수치 (전체/BM별/도메인별)"
          - "Top-N 플레이어"
          - "주요 발견"
          - "전략적 시사점"

      section_1_market_definition:
        subsections:
          - "1.1 시장 경계"
          - "1.2 Needs 분류"
          - "1.3 시장 정의 Summary"

      section_2_market_sizing:
        subsections:
          - "2.1 전체 시장 규모"
            must_include:
              - "4-Method 결과 테이블"
              - "가중 평균"
              - "신뢰 구간"
              - "ASM-ID 참조"
          - "2.2 BM별 시장 규모"
          - "2.3 도메인별 시장 규모"

      section_3_player_analysis:
        subsections:
          - "3.1 BM별 주요 플레이어"
          - "3.2 Top 10 플레이어 상세"
            for_each_player:
              - "매출 (SRC-ID or EST-ID)"
              - "강점/약점"
              - "시장 점유율"

      section_4_value_chain:
        subsections:
          - "4.1 BM별 가치사슬 구조"
            visualize: "flow diagram"
          - "4.2 비용 구조"
          - "4.3 마진 분석"

      section_5_competition:
        subsections:
          - "5.1 경쟁강도 (CR3, HHI)"
          - "5.2 교섭력 구조"
          - "5.3 진입장벽"

      section_6_data_traceability:
        subsections:
          - "6.1 Source Registry Summary"
          - "6.2 Estimation Registry Summary"
          - "6.3 Assumption Registry Summary"

      section_7_validation:
        subsections:
          - "7.1 MECE 검증 결과"
          - "7.2 3자 검증 게이트 결과"

      section_8_limitations:
        - "분석 한계"
        - "개선 방안"

      section_9_conclusion:
        - "핵심 발견"
        - "전략적 시사점"

      appendix:
        - "A. 전체 BM 목록"
        - "B. 전체 도메인 목록"
        - "C. Top 50 플레이어 목록"
        - "D. 데이터 출처 전체 목록"

    example_skeleton: |
      # Market Reality Report: {시장명}

      **작성자**: {Agent names}
      **작성일**: {date}
      **검증**: {validators} ✅

      ## Executive Summary

      ### 시장 정의
      ...

      ### 핵심 수치
      | 항목 | 수치 | 신뢰도 |
      |------|------|--------|
      | 전체 시장 | ... | ... |

      ## 1. 시장 정의 및 범위
      ...

  # ========================================
  # Opportunity Card
  # ========================================

  opportunity_card:
    artifact_type: "opportunity"
    role: "opportunity_designer"
    workflow: "opportunity_discovery"
    format: "yaml + markdown"

    template_structure:

      metadata:
        - "opportunity_id"
        - "domain_id"
        - "pattern_ids"
        - "created_at"
        - "created_by_role"

      summary:
        - "one_line_pitch"
        - "target_segment"
        - "value_proposition"

      structural_basis:
        - "related_patterns"
        - "gap_analysis"
        - "why_now"

      rough_sizing:
        metrics:
          - "TAM"
          - "SAM"
          - "SOM"
        confidence: "exploration_friendly"

      key_assumptions:
        - "list[ASM-ID]"

      risks_levers:
        risks:
          - "주요 리스크 3-5개"
        levers:
          - "성공 레버 3-5개"

      next_steps:
        - "추가 검증 필요 항목"
        - "Prototype/MVP 제안"

    example: |
      # OPP-20251205-001: 피아노 레슨 구독 서비스

      **Pattern**: SaaS-like + Offline hybrid
      **Target**: 서울 거주 직장인 피아노 학습자
      **Value Prop**: 구독형 정기 레슨 + 진도 관리 앱

      ## Structural Basis
      - Gap: 오프라인 학원은 선불 패키지, 유연성 낮음
      - Pattern: 구독형 모델이 적용 가능한 구조
      - Why now: COVID 이후 온라인 수용도 증가

      ## Rough Sizing
      - TAM: 7,500억 (성인 어학 전체)
      - SAM: 300억 (피아노 레슨 추정)
      - SOM: 30억 (10% 획득 목표)
      - Confidence: 60% (exploration mode)

      ## Risks & Levers
      **Risks**:
      - 선생님 확보 어려움
      - 오프라인 필수 (레슨 특성)

      **Levers**:
      - 선생님 네트워크 구축
      - 진도/출석 관리 자동화
```

---

## 6. 구현 우선순위 상세

### Priority 1: Sprint 3 시작 전 필수 (1주 이내)

#### 작업 1: `umis_v9_process_phases.yaml` 작성

**예상 소요**: 2-3일  
**담당**: 아키텍트 + v7 경험자

**작업 내용**:
1. v7 14 Phase 구조 분석
2. Phase별 입력/출력/검증 정의
3. 4개 canonical_workflows에 각각 Phase 매핑
4. umis_v9.yaml에 참조 추가

**산출물**:
- `umis_v9_process_phases.yaml` (예상 500-800줄)
- umis_v9.yaml 수정 (canonical_workflows 섹션)

**검증**:
- [ ] structure_analysis 14 Phase 완전 정의
- [ ] 각 Phase별 산출물 artifact ID 부여
- [ ] Phase 간 의존성 명시
- [ ] 검증 게이트 위치 표시

---

#### 작업 2: `umis_v9_agent_protocols.yaml` 작성

**예상 소요**: 2일  
**담당**: 아키텍트

**작업 내용**:
1. v7 Agent 협업 사례 분석 (Rachel 요청서 등)
2. 협업 패턴 4-5개 정의
3. 요청/응답 템플릿 작성
4. umis_v9.yaml Role Plane에 참조 추가

**산출물**:
- `umis_v9_agent_protocols.yaml` (예상 400-600줄)
- umis_v9.yaml 수정 (role_plane 섹션)

**검증**:
- [ ] data_collection_request 템플릿 완성
- [ ] estimation_request 템플릿 완성
- [ ] validation_gate_request 템플릿 완성
- [ ] 협업 워크플로 예시 작성

---

#### 작업 3: `umis_v9_validation_gates.yaml` 작성

**예상 소요**: 2일  
**담당**: 아키텍트 + 품질 담당자

**작업 내용**:
1. v7 검증 게이트 분석 (Phase 13)
2. Gate 타입 5개 정의
3. 각 검증자별 체크리스트 작성
4. umis_v9.yaml Policy Engine에 참조 추가

**산출물**:
- `umis_v9_validation_gates.yaml` (예상 300-500줄)
- umis_v9.yaml 수정 (policy_engine 섹션)

**검증**:
- [ ] MECE validation 정의
- [ ] 4-Method convergence 정의
- [ ] 3-validator gate 정의
- [ ] Pass/Fail 기준 명확

---

### Priority 2: Sprint 3 중 병행 (2주 이내)

#### 작업 4: Strategic Frameworks 이식

**예상 소요**: 1-2일

```bash
# Step 1: 파일 복사
cp reference/Observer_v7.x/umis_strategic_frameworks.yaml \
   frameworks/umis_v9_strategic_frameworks.yaml

# Step 2: Pattern Graph 연동 추가
# 각 프레임워크에 pattern_graph_mapping 섹션 추가

# Step 3: Strategy Engine 사용법 추가
# 각 프레임워크에 strategy_engine_usage 추가
```

---

#### 작업 5: Value Chain Templates 작성

**예상 소요**: 2-3일

**작업 내용**:
1. 가치사슬 분석 프레임워크 정의
2. BM별 템플릿 5-10개 작성
3. Phase 6 실행 가이드 작성
4. v7 벤치마크와 연동

---

#### 작업 6: Data Quality Framework 작성

**예상 소요**: 1-2일

**작업 내용**:
1. 신뢰도 등급 체계 정의 (v7 기반)
2. Source/Estimation/Assumption Registry 스키마
3. 품질 프로파일 적용 규칙

---

### Priority 3: Sprint 4 전 (3-4주 이내)

- 작업 7-10: 나머지 파일 작성
- 각 1-2일 소요

---

## 7. v7→v9 마이그레이션 가이드

### 개념 매핑

| v7 개념 | v9 개념 | 변경 사항 |
|---------|---------|-----------|
| Observer (Albert) | Structure Analyst | 역할명 변경, 책임 유사 |
| Validator (Rachel) | (없음, 내장) | Reality Monitor + Evidence Engine |
| Quantifier (Bill) | Numerical Modeler | 역할명 변경 |
| Estimator (Fermi) | (없음, 내장) | Metric Resolver Prior 단계 |
| Explorer (Steve) | Opportunity Designer | 역할명 변경 |
| Guardian (Stewart) | (없음, 내장) | Policy Engine + Validation Gates |
| 4-Layer RAG | Substrate Plane | Stores로 재구조화 |
| Estimator 4-Stage | Metric Resolver | Direct→Derived→Prior→Fusion |
| Knowledge Graph | Pattern Graph | 확장 및 재정의 |
| Memory | Memory Store | 유사 |

### 프로세스 매핑

| v7 Phase | v9 Phase | 매핑 |
|----------|----------|------|
| Phase 1-4 (구조 분석) | umis_v9_process_phases.yaml#PH01-04 | 1:1 매핑 |
| Phase 5 (플레이어) | PH05 + EvidenceEngine 호출 | 자동화 추가 |
| Phase 6 (가치사슬) | PH06 + value_chain_template | 템플릿화 |
| Phase 7 (시장규모) | PH07 + Metric Resolver | 통합 |
| Phase 8-11 (경쟁) | PH08-11 + Pattern Engine | 패턴 연동 |
| Phase 12-13 (검증) | Validation Gates | 시스템화 |
| Phase 14 (리포트) | Output Format | 템플릿화 |

### 데이터 매핑

| v7 ID | v9 ID | 변경 사항 |
|-------|-------|-----------|
| SRC_YYYYMMDD_NNN | SRC_YYYYMMDD_NNN | 동일 (호환) |
| EST_YYYYMMDD_NNN | EST-YYYYMMDD-NNN | 하이픈 추가 |
| ASM_YYYYMMDD_NNN | ASM-YYYYMMDD-NNN | 하이픈 추가 |
| (없음) | EVD-YYYYMMDD-NNN | 신규 (Evidence 공식 ID) |
| (없음) | VAL-{...} | 신규 (ValueRecord) |

---

## 6. 핵심 권고사항

### DO (반드시 할 것)

1. **Priority 1 파일을 Sprint 3 전에 완성**
   - Process Phases, Agent Protocols, Validation Gates
   - 이것 없이는 실제 프로젝트 수행 불가

2. **v7 자산 적극 활용**
   - Strategic Frameworks 30개 이식
   - Industry Benchmarks 50개 이식
   - 검증된 프로세스 재사용

3. **명확한 책임 분리**
   - Agent별 체크리스트
   - 검증 게이트 pass/fail 기준
   - 협업 프로토콜 템플릿화

4. **완전한 추적성 유지**
   - 모든 데이터: SRC-ID
   - 모든 추정: EST-ID
   - 모든 가정: ASM-ID

### DON'T (하지 말 것)

1. **Phase 정의 없이 구현 시작 금지**
   - 개념적 설계만으로는 프로젝트 못 돌림
   - 실행 상세 없으면 Agent 협업 불가

2. **검증 게이트 없이 진행 금지**
   - 품질 보증 메커니즘 필수
   - v7처럼 3자 검증 체계 구축

3. **v7 자산 무시 금지**
   - 검증된 프레임워크/벤치마크 활용
   - 바퀴 재발명하지 말 것

4. **협업 프로토콜 없이 멀티 Agent 구현 금지**
   - 요청/응답 포맷 사전 정의 필수
   - 책임/권한 명확화 필요

---

## 7. 결론

### 현재 v9 평가

**강점**:
- 철학적/개념적 완성도: A+
- 아키텍처 설계: A+
- 확장성/유연성: A+

**약점**:
- 실행 가능성: C
- 운영 상세: D
- v7 자산 활용: F

### 최종 권고

**v9는 훌륭한 설계입니다. 하지만 실행하려면 v7의 실전 노하우가 필요합니다.**

Priority 1 파일 3개를 먼저 완성하세요:
1. Process Phases (14단계 구조)
2. Agent Protocols (협업 방법)
3. Validation Gates (품질 보증)

그 다음 v7의 Strategic Frameworks와 Benchmarks를 이식하세요.

**이것만 하면 v9는 실제로 작동하는 시스템이 됩니다.**

---

---

## 8. 구현 예시 및 코드 스니펫

### 예시 1: Phase 실행 시뮬레이션

**시나리오**: Phase 5 (플레이어 식별) → Phase 6 (가치사슬 맵핑)

```python
# umis_v9_core/workflow_executor.py

from typing import Dict, Any, List
from dataclasses import dataclass
import yaml

@dataclass
class PhaseResult:
    phase_id: str
    status: str  # "success", "failed", "pending"
    outputs: Dict[str, Any]
    validation_result: Dict[str, Any]

class WorkflowExecutor:
    """Process Phases 기반 워크플로 실행기"""

    def __init__(self, process_phases_config: str):
        with open(process_phases_config) as f:
            self.config = yaml.safe_load(f)

    def execute_phase(self, workflow_id: str, phase_id: str, 
                     inputs: Dict[str, Any]) -> PhaseResult:
        """단일 Phase 실행"""
        
        # Phase 정의 로드
        workflow = self._get_workflow(workflow_id)
        phase_def = self._get_phase(workflow, phase_id)
        
        # 1. Input 검증
        self._validate_inputs(phase_def, inputs)
        
        # 2. Activities 실행
        activities_result = self._execute_activities(phase_def, inputs)
        
        # 3. Outputs 생성
        outputs = self._generate_outputs(phase_def, activities_result)
        
        # 4. Validation 수행
        validation = self._validate_phase(phase_def, outputs)
        
        # 5. PhaseResult 반환
        return PhaseResult(
            phase_id=phase_id,
            status="success" if validation["pass"] else "failed",
            outputs=outputs,
            validation_result=validation
        )

    def execute_workflow(self, workflow_id: str, 
                        initial_inputs: Dict[str, Any]) -> List[PhaseResult]:
        """전체 Workflow 실행 (Phase 1→14)"""
        
        workflow = self._get_workflow(workflow_id)
        results = []
        current_inputs = initial_inputs
        
        for phase_def in workflow["phases"]:
            phase_id = phase_def["phase_id"]
            
            # Phase 실행
            result = self.execute_phase(workflow_id, phase_id, current_inputs)
            results.append(result)
            
            # Validation 실패 시 중단
            if result.status == "failed":
                print(f"Phase {phase_id} failed validation. Stopping.")
                break
            
            # 다음 Phase inputs = 현재 Phase outputs
            current_inputs.update(result.outputs)
        
        return results

# 사용 예시
executor = WorkflowExecutor("umis_v9_process_phases.yaml")

# Phase 5 실행
phase5_result = executor.execute_phase(
    workflow_id="structure_analysis",
    phase_id="PH05_player_identification",
    inputs={
        "domain_id": "Adult_Language_Education_KR",
        "ART-bm_complete_list": bm_list_artifact
    }
)

# Phase 5 outputs → Phase 6 inputs
if phase5_result.status == "success":
    phase6_result = executor.execute_phase(
        workflow_id="structure_analysis",
        phase_id="PH06_value_chain_mapping",
        inputs={
            **phase5_result.outputs,  # ART-player_list 포함
            "value_chain_template": "offline_subscription_like"
        }
    )
```

---

### 예시 2: Agent 협업 구현

```python
# umis_v9_core/agent_collaboration.py

from dataclasses import dataclass
from typing import Dict, Any
import yaml

@dataclass
class AgentRequest:
    request_id: str
    from_role: str
    to_role: str
    pattern: str
    content: Dict[str, Any]
    created_at: str

@dataclass
class AgentResponse:
    request_id: str
    from_role: str
    status: str  # "completed", "partial", "failed"
    content: Dict[str, Any]
    created_at: str

class AgentCollaborationHub:
    """Agent 간 협업 중재"""

    def __init__(self, protocols_config: str):
        with open(protocols_config) as f:
            self.protocols = yaml.safe_load(f)

    def create_request(self, from_role: str, to_role: str, 
                      pattern: str, content: Dict[str, Any]) -> AgentRequest:
        """협업 요청 생성 (템플릿 검증 포함)"""
        
        # 1. Pattern 정의 가져오기
        pattern_def = self._get_pattern(pattern)
        
        # 2. 요청 템플릿 검증
        template = pattern_def["request_template"]
        self._validate_against_template(content, template)
        
        # 3. Request 생성
        request_id = self._allocate_id("REQ")
        
        return AgentRequest(
            request_id=request_id,
            from_role=from_role,
            to_role=to_role,
            pattern=pattern,
            content=content,
            created_at=self._now()
        )

    def create_response(self, request: AgentRequest, 
                       response_content: Dict[str, Any]) -> AgentResponse:
        """협업 응답 생성 (템플릿 검증 포함)"""
        
        # 응답 템플릿 검증
        pattern_def = self._get_pattern(request.pattern)
        template = pattern_def["response_template"]
        self._validate_against_template(response_content, template)
        
        return AgentResponse(
            request_id=request.request_id,
            from_role=request.to_role,
            status="completed",
            content=response_content,
            created_at=self._now()
        )

# 사용 예시: Observer → Validator 데이터 요청

hub = AgentCollaborationHub("umis_v9_agent_protocols.yaml")

# Observer가 Rachel에게 데이터 요청
request = hub.create_request(
    from_role="structure_analyst",
    to_role="validator",
    pattern="data_collection_request",
    content={
        "project": "한국 성인 어학교육 시장 분석",
        "priority": "HIGH",
        "data_collection_priorities": {
            "priority_1": {
                "name": "확정 데이터",
                "items": [
                    {
                        "category": "상장사 공시자료",
                        "targets": ["YBM넷", "능률교육"],
                        "sources": ["DART"],
                        "reliability_target": 90
                    }
                ]
            }
        },
        "deadline": "2025-12-07",
        "required_outputs": ["source_registry.yaml", "data_summary.md"]
    }
)

# Validator가 작업 후 응답
response = hub.create_response(
    request=request,
    response_content={
        "status": "completed",
        "sources_collected": 5,
        "source_registry_file": "source_registry_Adult_Language_KR.yaml",
        "summary": {
            "confirmed_data": 5,
            "reliability_avg": 80,
            "data_gaps": ["비상장사 매출", "도메인별 비율"]
        },
        "src_ids": [
            "SRC_20251205_001",
            "SRC_20251205_002",
            "SRC_20251205_003",
            "SRC_20251205_004",
            "SRC_20251205_005"
        ]
    }
)
```

---

### 예시 3: Validation Gate 실행

```python
# umis_v9_core/validation_gate.py

from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ValidationResult:
    gate_id: str
    validator_role: str
    items_checked: List[str]
    items_passed: List[str]
    items_failed: List[str]
    overall_result: str  # "pass", "fail"
    recommendations: List[str]

class ValidationGateEngine:
    """검증 게이트 실행 엔진"""

    def __init__(self, gates_config: str):
        with open(gates_config) as f:
            self.gates = yaml.safe_load(f)

    def execute_gate(self, gate_type: str, 
                    artifacts: Dict[str, Any],
                    validator_role: str) -> ValidationResult:
        """단일 검증자의 게이트 실행"""
        
        gate_def = self._get_gate_definition(gate_type)
        checklist = gate_def["validator_checklists"][validator_role]
        
        items_passed = []
        items_failed = []
        
        for item in checklist:
            item_id = item["id"]
            criteria = item["criteria"]
            
            # 검증 수행
            check_result = self._check_criteria(artifacts, criteria)
            
            if check_result["pass"]:
                items_passed.append(item_id)
            else:
                items_failed.append({
                    "item_id": item_id,
                    "reason": check_result["reason"]
                })
        
        overall = "pass" if len(items_failed) == 0 else "fail"
        
        return ValidationResult(
            gate_id=f"GATE-{gate_type}-{validator_role}",
            validator_role=validator_role,
            items_checked=[item["id"] for item in checklist],
            items_passed=items_passed,
            items_failed=items_failed,
            overall_result=overall,
            recommendations=self._generate_recommendations(items_failed)
        )

    def execute_three_validator_gate(self, 
                                    artifacts: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """Phase 13: 3자 검증 게이트"""
        
        validators = ["quantifier", "validator", "guardian"]
        results = {}
        
        for validator_role in validators:
            result = self.execute_gate(
                gate_type="three_validator_gate",
                artifacts=artifacts,
                validator_role=validator_role
            )
            results[validator_role] = result
        
        # 모두 통과해야 전체 통과
        all_pass = all(r.overall_result == "pass" for r in results.values())
        
        return {
            "individual_results": results,
            "overall_pass": all_pass,
            "gate_status": "PASS" if all_pass else "FAIL"
        }

# 사용 예시
gate_engine = ValidationGateEngine("umis_v9_validation_gates.yaml")

# Phase 7 완료 후: 4-Method Convergence 검증
artifacts = {
    "market_size_estimates": {
        "method_1": {"estimate": 1500억, "weight": 0.2},
        "method_2": {"estimate": 10000억, "weight": 0.4},
        "method_3": {"estimate": 13000억, "weight": 0.3},
        "method_4": {"estimate": 18000억, "weight": 0.1}
    }
}

convergence_result = gate_engine.execute_gate(
    gate_type="four_method_convergence",
    artifacts=artifacts,
    validator_role="quantifier"
)

if convergence_result.overall_result == "pass":
    print("✅ 4-Method Convergence 검증 통과")
else:
    print("❌ 검증 실패:", convergence_result.items_failed)

# Phase 13: 최종 3자 검증
final_artifacts = {
    "market_reality_report": report_data,
    "source_registry": source_data,
    "estimation_registry": estimation_data,
    # ...
}

three_validator_result = gate_engine.execute_three_validator_gate(final_artifacts)

if three_validator_result["overall_pass"]:
    print("✅ 3자 검증 모두 통과 - 프로젝트 완료")
else:
    for role, result in three_validator_result["individual_results"].items():
        if result.overall_result == "fail":
            print(f"❌ {role} 검증 실패:")
            print(result.recommendations)
```

---

### 예시 4: Value Chain 분석 자동화

```python
# umis_v9_core/value_chain_analyzer.py

class ValueChainAnalyzer:
    """가치사슬 분석 및 R-Graph 업데이트"""

    def __init__(self, templates_config: str, benchmarks_config: str):
        self.templates = self._load_yaml(templates_config)
        self.benchmarks = self._load_yaml(benchmarks_config)

    def analyze_bm_value_chain(self, bm_id: str, 
                               r_graph: InMemoryGraph,
                               estimator) -> Dict[str, Any]:
        """BM의 가치사슬 분석 수행"""
        
        # 1. BM에 맞는 템플릿 선택
        template = self._select_template(bm_id)
        
        # 2. R-Graph에서 관련 Actors 추출
        actors = self._extract_actors(r_graph, bm_id)
        
        # 3. 각 stage별 분석
        stages_analysis = []
        
        for stage in template["stages"]:
            stage_result = {
                "stage_name": stage["name"],
                "actors": self._identify_stage_actors(actors, stage),
                "cost_share": None,
                "margin": None,
                "estimation_needed": []
            }
            
            # 3-1. 벤치마크에서 typical 값 가져오기
            benchmark = self._get_benchmark(template["reference_benchmark"])
            typical_cost = benchmark["stages"][stage["name"]]["typical_cost_share"]
            
            # 3-2. 확정 데이터 확인
            confirmed_data = self._check_confirmed_data(r_graph, stage)
            
            if confirmed_data:
                stage_result["cost_share"] = confirmed_data
                stage_result["source"] = "confirmed"
            else:
                # 3-3. 확정 데이터 없으면 Estimator 요청
                est_request = {
                    "estimation_id": self._allocate_est_id(),
                    "question": f"{bm_id} {stage['name']} 비용 비중은?",
                    "context": {
                        "bm_id": bm_id,
                        "benchmark_typical": typical_cost
                    }
                }
                stage_result["estimation_needed"].append(est_request)
                stage_result["cost_share"] = typical_cost  # Prior로 사용
                stage_result["source"] = "benchmark_prior"
            
            stages_analysis.append(stage_result)
        
        # 4. MoneyFlow edges 생성
        money_flows = self._create_money_flow_edges(stages_analysis, r_graph)
        
        # 5. 결과 반환
        return {
            "bm_id": bm_id,
            "template_used": template["template_id"],
            "stages": stages_analysis,
            "money_flows": money_flows,
            "estimation_requests": [
                req for stage in stages_analysis 
                for req in stage["estimation_needed"]
            ]
        }

# 사용 예시
analyzer = ValueChainAnalyzer(
    templates_config="frameworks/umis_v9_value_chain_templates.yaml",
    benchmarks_config="benchmarks/umis_v9_pattern_benchmarks.yaml"
)

# BM-01 (오프라인 학원) 가치사슬 분석
result = analyzer.analyze_bm_value_chain(
    bm_id="BM-01_offline_academy",
    r_graph=reality_snapshot.graph,
    estimator=estimator_engine
)

print(f"Stages analyzed: {len(result['stages'])}")
print(f"Estimation requests: {len(result['estimation_requests'])}")

# Estimator에 일괄 요청
for est_req in result['estimation_requests']:
    estimator.estimate(est_req)
```

---

### 예시 5: MECE Validation 자동화

```python
# umis_v9_core/mece_validator.py

class MECEValidator:
    """MECE 검증 자동화"""

    def validate_classification(self, 
                                classification: Dict[str, Any],
                                classification_type: str) -> Dict[str, Any]:
        """분류의 MECE 검증"""
        
        # 1. Mutually Exclusive 체크
        me_result = self._check_mutually_exclusive(classification)
        
        # 2. Collectively Exhaustive 체크
        ce_result = self._check_collectively_exhaustive(classification)
        
        # 3. 종합 평가
        passed = me_result["pass"] and ce_result["pass"]
        
        return {
            "classification_type": classification_type,
            "me_check": me_result,
            "ce_check": ce_result,
            "overall_pass": passed,
            "issues": me_result.get("issues", []) + ce_result.get("issues", [])
        }

    def _check_mutually_exclusive(self, classification: Dict) -> Dict:
        """상호 배타성 검증"""
        
        issues = []
        items = classification.get("items", [])
        
        # 각 쌍별로 교집합 확인
        for i, item_a in enumerate(items):
            for item_b in items[i+1:]:
                overlap = self._find_overlap(item_a, item_b)
                if overlap:
                    issues.append({
                        "type": "overlap",
                        "items": [item_a["id"], item_b["id"]],
                        "overlap_details": overlap
                    })
        
        return {
            "pass": len(issues) == 0,
            "issues": issues
        }

    def _check_collectively_exhaustive(self, classification: Dict) -> Dict:
        """전체 포괄성 검증"""
        
        items = classification.get("items", [])
        
        # 비율 합산 (if applicable)
        if "share" in items[0]:
            total_share = sum(item["share"] for item in items)
            
            tolerance = 0.05  # ±5%
            ce_pass = abs(total_share - 1.0) < tolerance
            
            return {
                "pass": ce_pass,
                "total_share": total_share,
                "expected": 1.0,
                "tolerance": tolerance,
                "issues": [] if ce_pass else [
                    {
                        "type": "incomplete_coverage",
                        "total": total_share,
                        "gap": 1.0 - total_share
                    }
                ]
            }
        
        # 정성적 검토
        has_catchall = any(item.get("is_catchall") for item in items)
        
        return {
            "pass": has_catchall,
            "has_catchall_category": has_catchall,
            "issues": [] if has_catchall else [
                {"type": "no_catchall", "recommendation": "'기타' 카테고리 추가"}
            ]
        }

# 사용 예시
validator = MECEValidator()

# 도메인 분류 검증
domain_classification = {
    "items": [
        {"id": "영어", "share": 0.75},
        {"id": "중국어", "share": 0.125},
        {"id": "일본어", "share": 0.075},
        {"id": "기타", "share": 0.05, "is_catchall": True}
    ]
}

result = validator.validate_classification(
    classification=domain_classification,
    classification_type="domain_by_language"
)

if result["overall_pass"]:
    print("✅ MECE 검증 통과")
else:
    print("❌ MECE 검증 실패:")
    for issue in result["issues"]:
        print(f"  - {issue}")
```

---

## 9. 실전 적용 시나리오

### 시나리오: "한국 성인 어학교육 시장 분석" v9로 재실행

#### Step 1: 프로젝트 초기화

```python
from umis_v9_core.workflow_executor import WorkflowExecutor
from umis_v9_core.agent_collaboration import AgentCollaborationHub

# 워크플로 실행기 초기화
executor = WorkflowExecutor("umis_v9_process_phases.yaml")
hub = AgentCollaborationHub("umis_v9_agent_protocols.yaml")

# 프로젝트 입력
project_inputs = {
    "domain_id": "Adult_Language_Education_KR",
    "region": "KR",
    "segment": "adult_language_general",
    "target_workflow": "structure_analysis",
    "quality_profile": "decision_balanced"
}
```

---

#### Step 2: Phase 1-4 실행 (자동)

```python
# Phase 1: 시장 정의
phase1_result = executor.execute_phase(
    workflow_id="structure_analysis",
    phase_id="PH01_market_definition",
    inputs=project_inputs
)

# Phase 1 validation
if phase1_result.validation_result["pass"]:
    print("✅ Phase 1 완료: Needs 분류 MECE 검증 통과")

# Phase 2-4 순차 실행
for phase_id in ["PH02_domain_classification", 
                 "PH03_bm_framework", 
                 "PH04_bm_enumeration"]:
    result = executor.execute_phase(
        workflow_id="structure_analysis",
        phase_id=phase_id,
        inputs=phase1_result.outputs
    )
    
    if result.status == "failed":
        print(f"❌ {phase_id} 실패 - 중단")
        break
```

---

#### Step 3: Phase 5 - Agent 협업

```python
# Phase 5-1: 플레이어 식별
phase5_result = executor.execute_phase(
    workflow_id="structure_analysis",
    phase_id="PH05_player_identification",
    inputs={"ART-bm_complete_list": phase4_result.outputs["bm_list"]}
)

# Observer → Validator 데이터 요청 생성
data_request = hub.create_request(
    from_role="structure_analyst",
    to_role="validator",
    pattern="data_collection_request",
    content={
        "project": "한국 성인 어학교육 시장 분석",
        "player_list": phase5_result.outputs["player_list"],
        "priority_sources": ["DART", "KOSIS", "Commercial_Reports"],
        # ... (템플릿 기반 자동 생성)
    }
)

# Validator 실행 (EvidenceEngine 호출)
evidence_engine = EvidenceEngine(config)
collected_data = evidence_engine.fetch_for_reality_slice(
    scope={
        "domain_id": "Adult_Language_Education_KR",
        "data_request": data_request
    }
)

# Validator → Observer 응답
data_response = hub.create_response(
    request=data_request,
    response_content={
        "sources_collected": len(collected_data),
        "source_registry": "source_registry_Adult_Language_KR.yaml",
        # ...
    }
)
```

---

#### Step 4: Phase 6-7 - 가치사슬 & 시장규모

```python
from umis_v9_core.value_chain_analyzer import ValueChainAnalyzer

# Phase 6: 가치사슬 분석
vc_analyzer = ValueChainAnalyzer(
    templates_config="frameworks/umis_v9_value_chain_templates.yaml",
    benchmarks_config="benchmarks/umis_v9_pattern_benchmarks.yaml"
)

# BM별 가치사슬 분석
bm_list = phase4_result.outputs["bm_list"]
value_chain_results = []

for bm in bm_list:
    vc_result = vc_analyzer.analyze_bm_value_chain(
        bm_id=bm["bm_id"],
        r_graph=reality_snapshot.graph,
        estimator=estimator_engine
    )
    value_chain_results.append(vc_result)

# Phase 7: 시장규모 추정 (Metric Resolver 사용)
from umis_v9_core.value_engine import ValueEngine

value_engine = ValueEngine(config)

market_size_result = value_engine.evaluate_metrics(
    metric_requests=[
        {
            "metric_id": "MET-TAM",
            "context": {
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR",
                "as_of": "2025-01-01"
            }
        }
    ],
    policy_ref="decision_balanced"
)

# Metric Resolver가 자동으로:
# 1. Direct Evidence 검색 (EvidenceEngine)
# 2. Derived 경로 탐색 (N_customers × ARPU)
# 3. Prior 적용 (Pattern benchmarks)
# 4. 4-Method Convergence
# 5. ValueRecord 생성
```

---

#### Step 5: Phase 13 - 최종 검증

```python
# 모든 산출물 수집
final_artifacts = {
    "ART-needs_classification": phase1_result.outputs,
    "ART-domain_classification": phase2_result.outputs,
    "ART-bm_complete_list": phase4_result.outputs,
    "ART-player_list": phase5_result.outputs,
    "ART-value_chain_map": value_chain_results,
    "ART-market_size_estimate": market_size_result,
    "source_registry": data_response.content["source_registry"],
    "estimation_registry": estimator.get_registry(),
    "assumption_registry": quantifier.get_assumptions()
}

# 3자 검증 게이트 실행
validation_result = gate_engine.execute_three_validator_gate(final_artifacts)

if validation_result["overall_pass"]:
    # Phase 14: 리포트 생성
    report_generator = ReportGenerator("schemas/umis_v9_output_formats.yaml")
    
    final_report = report_generator.generate(
        template="market_reality_report",
        artifacts=final_artifacts,
        validation=validation_result
    )
    
    final_report.save("outputs/Market_Reality_Report_Adult_Language_KR_v9.md")
    print("✅ 프로젝트 완료!")
else:
    print("❌ 검증 실패 - 재작업 필요")
    for role, result in validation_result["individual_results"].items():
        if result.overall_result == "fail":
            print(f"\n{role} 실패 항목:")
            for item in result.items_failed:
                print(f"  - {item}")
```

---

## 10. 마이그레이션 로드맵

### Week 1: Priority 1 파일 작성

**Day 1-2**: `umis_v9_process_phases.yaml`
- [ ] structure_analysis 14 Phase 정의
- [ ] 각 Phase: inputs/outputs/validation 명시
- [ ] 의존성 그래프 작성

**Day 3-4**: `umis_v9_agent_protocols.yaml`
- [ ] 4개 협업 패턴 정의
- [ ] 요청/응답 템플릿 작성
- [ ] 예시 워크플로 작성

**Day 5**: `umis_v9_validation_gates.yaml`
- [ ] 5개 Gate Type 정의
- [ ] 검증자별 체크리스트
- [ ] Pass/Fail 기준

**Day 6-7**: umis_v9.yaml 수정 및 통합 테스트
- [ ] 참조 추가
- [ ] YAML 문법 검증
- [ ] 간단한 Phase 실행 테스트

---

### Week 2: Priority 2 파일 작성

**Day 1-2**: Strategic Frameworks 이식
- [ ] v7 파일 복사
- [ ] Pattern Graph 연동 추가

**Day 3-4**: Value Chain Templates
- [ ] 분석 프레임워크 정의
- [ ] 5개 BM 템플릿 작성

**Day 5**: Data Quality Framework
- [ ] 신뢰도 체계 정의
- [ ] Registry 스키마 작성

---

### Week 3-4: 코드 구현 (Sprint 3)

**Week 3**: Core 구현
- [ ] WorkflowExecutor 구현
- [ ] AgentCollaborationHub 구현
- [ ] ValidationGateEngine 구현

**Week 4**: 통합 테스트
- [ ] v7 Market Reality Report 재현
- [ ] 결과 비교
- [ ] 성능/품질 검증

---

## 11. 성공 기준

### Sprint 3 완료 기준

**최소 성공 (Must Have)**:
- [ ] Priority 1 파일 3개 완성
- [ ] umis_v9.yaml 참조 통합
- [ ] Phase 1-7 실행 가능
- [ ] MECE 검증 작동
- [ ] Agent 협업 1회 성공 (Observer→Validator)

**이상적 성공 (Nice to Have)**:
- [ ] Priority 2 파일 완성
- [ ] Phase 1-14 완전 자동화
- [ ] 3자 검증 게이트 작동
- [ ] v7 결과물 재현 (90% 이상 일치)

---

### v7 대비 개선 목표

**품질**:
- v7: 수동 프로세스, Agent별 독립 작업
- v9: 자동화된 Phase 실행, 시스템화된 협업
- 목표: 동등 이상

**속도**:
- v7: 5일 (수동 작업)
- v9: 2-3일 (자동화)
- 목표: 30-50% 단축

**재사용성**:
- v7: 도메인별 재작업 필요
- v9: 템플릿/벤치마크 재사용
- 목표: 새 도메인 적용 시간 70% 단축

**설명력**:
- v7: SRC-/EST-/ASM- ID 추적
- v9: 완전한 Lineage Graph
- 목표: "왜 이 값인가?" 완전 자동 설명

---

## 12. 리스크 및 대응

### 주요 리스크

**리스크 1: Priority 1 파일 작성 지연**
- 영향: Sprint 3 구현 불가
- 확률: 중간
- 대응: 최우선 리소스 할당, 일일 진행 체크

**리스크 2: v7 자산 이식 시 호환성 문제**
- 영향: 재작업 필요
- 확률: 낮음
- 대응: 점진적 이식, 테스트 병행

**리스크 3: 과도한 자동화로 유연성 저하**
- 영향: 새로운 도메인 적용 시 제약
- 확률: 중간
- 대응: 템플릿 override 메커니즘, 수동 개입 포인트 유지

**리스크 4: 검증 게이트가 너무 엄격해서 진행 불가**
- 영향: 프로젝트 병목
- 확률: 낮음
- 대응: Pass 기준 점진적 조정, Override 옵션

---

## 13. 참고 자료

### 필수 읽기

1. **v7 Market Reality Report 전체**
   - 특히: 00_Guardian_Work_Log.md (프로세스 전체 흐름)
   - 특히: 02_Rachel_Data_Request.md (협업 템플릿)
   - 특히: 07_Final_Validation.md (검증 게이트)

2. **v7 Strategic Frameworks**
   - reference/Observer_v7.x/umis_strategic_frameworks.yaml
   - 30개 프레임워크 구조 이해

3. **v7 Value Chain Benchmarks**
   - reference/Observer_v7.x/value_chain_benchmarks.yaml
   - 50개 벤치마크 구조 이해

### 구현 참고

1. **현재 POC 코드**
   - umis_v9_core/graph.py
   - umis_v9_core/world_engine_poc.py
   - 스타일/패턴 참고

2. **도메인 설정 예시**
   - umis_v9_domain_AdultLanguage_KR.yaml
   - seeds/Adult_Language_Education_KR_reality_seed.yaml

---

## 14. Q&A

### Q1: Priority 1 파일 없이 Sprint 3 진행 가능한가?

**A**: 불가능합니다.

**이유**:
- EvidenceEngine을 구현해도 "언제, 어떻게, 누구에게 요청하는지" 프로토콜 없으면 사용 불가
- WorldEngine이 R-Graph를 채워도 "다음에 뭘 해야 하는지" Phase 정의 없으면 멈춤
- 검증 게이트 없으면 품질 보증 불가

**권장**: Sprint 2.5 단계 추가, Priority 1 완성 후 Sprint 3 시작

---

### Q2: v7 파일을 그대로 복사해도 되는가?

**A**: 부분적으로 가능합니다.

**그대로 사용 가능**:
- Strategic Frameworks (30개) - 개념은 불변
- Industry Benchmarks (50개) - 수치는 유효

**수정 필요**:
- v9 구조와 연동 (Pattern Graph, Strategy Engine)
- YAML 스키마 통일 (v9 규칙 준수)

**권장 작업**:
```bash
# 1. 복사
cp reference/Observer_v7.x/umis_strategic_frameworks.yaml \
   frameworks/umis_v9_strategic_frameworks.yaml

# 2. 각 프레임워크에 추가
# - pattern_graph_mapping
# - strategy_engine_usage
# - v9 예시

# 3. 검증
python scripts/validate_yaml.py frameworks/umis_v9_strategic_frameworks.yaml
```

---

### Q3: 모든 Phase를 자동화해야 하는가?

**A**: 아니요, 단계적 자동화가 적절합니다.

**Sprint 3-4**: 수동 + 시스템 지원
- Phase 실행은 수동
- 시스템은 템플릿/체크리스트 제공
- 검증은 자동

**Sprint 5-6**: 반자동
- Phase 일부 자동 실행
- 사람이 검토/승인

**Sprint 7+**: 완전 자동 (선택적)
- 검증된 도메인은 자동 실행
- 새 도메인은 수동 검토

---

### Q4: 14 Phase가 모든 workflow에 필요한가?

**A**: 아니요, workflow별로 다릅니다.

**structure_analysis**: 14 Phase (완전 분석)
**opportunity_discovery**: 8-10 Phase (구조 일부 + 기회 집중)
**strategy_design**: 5-7 Phase (Goal → Strategy → Scenario)
**reality_monitoring**: 3-5 Phase (Outcome → Compare → Learn)

각 workflow별로 적절한 Phase 수 정의 필요.

---

## 15. 최종 체크리스트

### 아키텍트 체크리스트

- [ ] 이 문서 전체 읽기 및 이해
- [ ] v7 Market Reality Report 9개 파일 정독
- [ ] v7 Strategic Frameworks 30개 검토
- [ ] v7 Value Chain Benchmarks 50개 검토
- [ ] Priority 1 파일 작성 계획 수립
- [ ] 팀 리뷰 및 작업 분담

### 개발자 체크리스트

- [ ] 이 문서의 코드 예시 검토
- [ ] graph.py, world_engine_poc.py 구조 이해
- [ ] WorkflowExecutor 구현 범위 파악
- [ ] ValidationGateEngine 구현 범위 파악
- [ ] 테스트 시나리오 작성

### 프로젝트 매니저 체크리스트

- [ ] Priority 1-3 일정 수립
- [ ] 리소스 할당 (1주 집중 작업)
- [ ] Sprint 2.5 단계 추가 여부 결정
- [ ] 마일스톤 재조정

---

## 부록 A: 용어 사전

| 용어 | 설명 | v7 | v9 |
|------|------|-----|-----|
| MECE | Mutually Exclusive, Collectively Exhaustive | ✓ | ✓ |
| CR3 | Concentration Ratio (상위 3개 점유율) | ✓ | ✓ |
| HHI | Herfindahl-Hirschman Index | ✓ | ✓ |
| SRC-ID | Source ID (확정 데이터) | ✓ | ✓ |
| EST-ID | Estimation ID (추정 데이터) | ✓ | ✓ |
| ASM-ID | Assumption ID (가정) | ✓ | ✓ |
| EVD-ID | Evidence ID (공식 Evidence) | - | ✓ |
| VAL-ID | Value Record ID | - | ✓ |
| PAT-ID | Pattern ID | - | ✓ |
| ART-ID | Artifact ID (산출물) | - | ✓ |

---

## 부록 B: 파일 생성 순서 (상세)

### Week 1

```bash
# Day 1
touch umis_v9_process_phases.yaml
# - structure_analysis workflow 정의
# - Phase 1-7 상세 작성

# Day 2
# - Phase 8-14 상세 작성
# - opportunity_discovery workflow 추가

# Day 3
touch umis_v9_agent_protocols.yaml
# - data_collection_request 템플릿
# - estimation_request 템플릿

# Day 4
# - calculation_request 템플릿
# - validation_gate_request 템플릿
# - 협업 워크플로 예시

# Day 5
touch umis_v9_validation_gates.yaml
# - MECE validation gate
# - 4-Method convergence gate
# - Data reliability gate

# Day 6
# - Summation validation gate
# - 3-validator gate
# - 품질 프로파일 연동

# Day 7
# - umis_v9.yaml 수정
# - YAML 검증
# - 문서 업데이트
```

### Week 2

```bash
# Day 1-2
mkdir -p frameworks
cp reference/Observer_v7.x/umis_strategic_frameworks.yaml \
   frameworks/umis_v9_strategic_frameworks.yaml

# v9 연동 추가:
# - pattern_graph_mapping 섹션 (30개 프레임워크)
# - strategy_engine_usage 섹션

# Day 3-4
touch frameworks/umis_v9_value_chain_templates.yaml
# - 분석 프레임워크
# - BM별 템플릿 5-10개
# - Phase 6 가이드

# Day 5
mkdir -p schemas
touch schemas/umis_v9_data_quality.yaml
# - 신뢰도 등급 체계
# - Registry 스키마
# - 품질 프로파일 적용

# Day 6-7
# - 통합 테스트
# - 문서 업데이트
```

### Week 3: 코드 구현

```bash
# umis_v9_core/ 구조

umis_v9_core/
├── __init__.py
├── graph.py                      # ✅ 이미 있음
├── world_engine_poc.py           # ✅ 이미 있음
│
├── workflow_executor.py          # ⭐ NEW
├── agent_collaboration.py        # ⭐ NEW
├── validation_gate.py            # ⭐ NEW
├── value_chain_analyzer.py       # ⭐ NEW
├── mece_validator.py             # ⭐ NEW
│
├── evidence_engine.py            # ⭐ Sprint 3 메인
├── value_engine.py               # ⭐ Sprint 4 메인
└── pattern_engine.py             # ⭐ Sprint 6 메인
```

---

## 부록 C: 빠른 시작 가이드

### 새로 합류한 개발자를 위한 5분 가이드

#### 1. 전체 구조 이해 (2분)

```bash
# 핵심 파일 3개만 읽기
cat umis_v9_philosophy_concept.md    # 철학 이해
cat umis_v9.yaml | head -100          # 구조 파악
cat UMIS_v9_Architecture_Gap_Analysis.md  # 현재 문서
```

#### 2. v7 결과물 확인 (2분)

```bash
# v7 최종 리포트만 읽기
cat reference/output/market_reality_report_v7.x/Market_Reality_Report_Final.md

# → 우리가 만들어야 할 결과물 수준 파악
```

#### 3. 현재 작업 파악 (1분)

```bash
# 현재 위치: Sprint 3 시작 전
# 다음 작업: Priority 1 파일 3개 작성
# 예상 소요: 1주

# 파일 생성 여부 확인
ls umis_v9_process_phases.yaml       # 없으면 생성 필요
ls umis_v9_agent_protocols.yaml      # 없으면 생성 필요
ls umis_v9_validation_gates.yaml     # 없으면 생성 필요
```

---

## 부록 D: 문의 및 논의 사항

### 아키텍처 결정 필요

1. **Agent를 실제 별도 프로세스로 구현할 것인가?**
   - Option A: 클래스/모듈로만 분리
   - Option B: 별도 서비스 (API 통신)
   - 권장: Sprint 3-4는 Option A, 나중에 Option B

2. **Validation Gate를 blocking으로 할 것인가?**
   - Option A: Fail 시 자동 중단
   - Option B: Warning만 표시, 계속 진행
   - 권장: Option A (품질 우선)

3. **Phase 실행을 CLI로 할 것인가 Notebook으로 할 것인가?**
   - 권장: 둘 다 지원 (CLI: 자동화, Notebook: 탐색)

### 추가 논의 필요

- [ ] 14 Phase가 모든 도메인에 적합한가?
- [ ] 협업 프로토콜의 강제성 수준은?
- [ ] 검증 게이트 통과 기준의 엄격함 정도는?
- [ ] v7 벤치마크 50개를 모두 이식할 것인가?

---

**작성일**: 2025-12-05  
**작성자**: UMIS Architecture Review Team  
**버전**: 1.0  
**다음 업데이트**: Priority 1 파일 완성 후

---

## 문서 끝

**이 문서를 읽은 후 즉시 할 일**:

1. ☑️ 팀 미팅 소집 (이 문서 리뷰)
2. ☑️ Priority 1 작업 분담
3. ☑️ 1주 집중 작업 일정 확보
4. ☑️ v7 Market Reality Report 9개 파일 정독
5. ☑️ umis_v9_process_phases.yaml 작성 시작

**목표**: 1주 후 Priority 1 완성, Sprint 3 시작
