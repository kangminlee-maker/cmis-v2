---
**이력**:
- 2025-12-09: UMIS v9 → CMIS 브랜드 변경
- 2025-12-12: v3.3 완성 상태 반영 (89% → 100% 예정, BeliefEngine 추가)

**버전**: v3.0 (CMIS v3.3 기준)
**상태**: Production Ready

**주요 변경**:
- Universal Market Intelligence → Contextual Market Intelligence
- 9개 엔진 완성 (BeliefEngine 추가)
- 4단계 루프 완성 (Understand → Discover → Decide → Learn)
- World Engine v2.0, Strategy Engine v1.0, Learning Engine v1.0 반영
---

# CMIS v3.3 Structure Analysis 워크플로우 다이어그램

**문서 목적**: CMIS v3.3 Structure Analysis 워크플로우를 시각적으로 표현한 다이어그램 모음

**참조**:
- `CMIS_Architecture_Blueprint_v3.3.md`
- `BeliefEngine_Design_Enhanced.md`

---

## 1. 전체 아키텍처 구조도 (4 Planes)

```mermaid
graph TB
    subgraph IP[Interaction Plane]
        CLI[CLI]
        NB[Notebook]
        WEB[Web App]
        API[API]
    end

    subgraph RP[Role Plane]
        SA[Structure Analyst]
        OD[Opportunity Designer]
        STR[Strategy Architect]
        NM[Numerical Modeler]
        RM[Reality Monitor]
    end

    subgraph CP[Cognition Plane - 9 Engines]
        EE[Evidence Engine<br/>외부 데이터 수집]
        WE[World Engine v2.0<br/>R-Graph 구축]
        PE[Pattern Engine v2.0<br/>패턴 매칭/갭 탐지]
        VE[Value Engine<br/>Metric Resolver]
        BE[Belief Engine<br/>Prior/Belief 관리]
        SE[Strategy Engine v1.0<br/>전략 탐색]
        LE[Learning Engine v1.0<br/>실적 기반 학습]
        POL[Policy Engine<br/>검증 게이트]
        WF[Workflow CLI<br/>워크플로우 실행]
    end

    subgraph SP[Substrate Plane - Graphs & Stores]
        RG[Reality Graph<br/>Actor/Event/MoneyFlow/State]
        PG[Pattern Graph<br/>BM/패턴 정의]
        VG[Value Graph<br/>Metric/ValueRecord]
        DG[Decision Graph<br/>Goal/Strategy/Scenario]
        
        EVS[Evidence Store<br/>EVD-*]
        VLS[Value Store<br/>VAL-*]
        MEM[Memory Store<br/>MEM-*, ART-*]
        OUT[Outcome Store<br/>OUT-*]
        PCS[Project Context Store<br/>PRJ-*]
    end

    IP --> RP
    RP --> CP
    CP --> SP

    SA -.주로 사용.-> WE
    SA -.주로 사용.-> PE
    NM -.주로 사용.-> VE
    RM -.주로 사용.-> EE

    EE --> EVS
    WE --> RG
    PE --> PG
    VE --> VG
    VE --> VLS
    BE --> VG
    SE --> DG
    LE --> VG
    LE --> PCS
    
    EE -.Evidence 수집.-> WE
    WE -.구조 제공.-> PE
    WE -.구조 제공.-> VE
    PE -.패턴 제공.-> VE
    PE -.패턴 제공.-> BE
    BE -.Prior 제공.-> VE
    VE -.Metric.-> SE
    SE -.전략.-> LE
    LE -.학습.-> BE
    POL -.검증.-> VE

    style IP fill:#e1f5ff
    style RP fill:#fff4e1
    style CP fill:#e8f5e9
    style SP fill:#f3e5f5
```

---

## 2. Greenfield vs Brownfield 워크플로우 분기

```mermaid
flowchart TD
    START([사용자 질문])
    
    MODE_CHECK{조직 컨텍스트<br/>필요?}
    
    subgraph GREENFIELD[Greenfield: 시장 전체 분석]
        GF_START[structure_analysis]
        GF_PHASES[Phase 1-14<br/>시장 구조/규모/경쟁]
        GF_OUTPUT[Market Reality Report<br/>시장 관점]
    end
    
    subgraph BROWNFIELD[Brownfield: 조직 통합 분석]
        BF_START[structure_analysis_for_project]
        PH00[Phase 0: Project Context Setup<br/>조직 현황/역량/제약]
        BF_PHASES[Phase 1-14<br/>시장 + 조직 통합 분석]
        BF_OUTPUT[Market Reality Report<br/>+ Position/Opportunity<br/>조직 관점]
    end
    
    START --> MODE_CHECK
    
    MODE_CHECK -->|"시장만 알면 됨"| GF_START
    MODE_CHECK -->|"우리 관점 필요"| BF_START
    
    GF_START --> GF_PHASES
    GF_PHASES --> GF_OUTPUT
    
    BF_START --> PH00
    PH00 --> BF_PHASES
    BF_PHASES --> BF_OUTPUT
    
    GF_OUTPUT --> END_GF([완료])
    BF_OUTPUT --> END_BF([완료])

    style GREENFIELD fill:#e1f5ff
    style BROWNFIELD fill:#fff4e1
    style PH00 fill:#ffeb3b,stroke:#f57c00,stroke-width:2px
    style MODE_CHECK fill:#e8f5e9
```

---

## 3. 전체 워크플로우 순서도 (Greenfield: 14 Phases)

**Note**: Greenfield = 시장 전체 분석, project_context_id 불필요

```mermaid
flowchart TD
    START([사용자 질문:<br/>한국 성인 어학교육 시장...])
    
    PH01[Phase 1: 시장 정의<br/>Needs A-D 분류]
    PH02[Phase 2: 도메인 분류<br/>15개 언어 도메인]
    PH03[Phase 3-4: BM 분류<br/>23개 BM Pattern]
    
    PH05[Phase 5: 플레이어 식별]
    PH05_1[Evidence Engine:<br/>외부 데이터 수집]
    PH05_2[World Engine:<br/>R-Graph 구축]
    
    PH06[Phase 6: 가치사슬 맵핑]
    PH06_1[Pattern Engine:<br/>가치사슬 템플릿]
    PH06_2[World Engine:<br/>MoneyFlow 추적]
    
    PH07[Phase 7: 시장규모 추정]
    PH07_1[Value Engine:<br/>Metric Resolver 4-Stage]
    PH07_2[4-Method Convergence<br/>±30% 수렴]
    
    PH08[Phase 8-11: 경쟁구조<br/>CR3/HHI/교섭력]
    
    PH12[Phase 12: MECE 검증<br/>합산 = 전체?]
    MECE_PASS{PASS?}
    
    PH13[Phase 13: 3자 검증 게이트]
    NM_CHECK[Numerical Modeler:<br/>계산 논리]
    RM_CHECK[Reality Monitor:<br/>출처 품질]
    SA_CHECK[Structure Analyst:<br/>목표 정렬]
    GATE_PASS{3명 모두<br/>PASS?}
    
    PH14[Phase 14: 리포트 생성<br/>Artifact 통합]
    
    END([Market Reality<br/>Report Final.md])

    START --> PH01
    PH01 --> PH02
    PH02 --> PH03
    PH03 --> PH05
    
    PH05 --> PH05_1
    PH05_1 --> PH05_2
    PH05_2 --> PH06
    
    PH06 --> PH06_1
    PH06_1 --> PH06_2
    PH06_2 --> PH07
    
    PH07 --> PH07_1
    PH07_1 --> PH07_2
    PH07_2 --> PH08
    
    PH08 --> PH12
    PH12 --> MECE_PASS
    MECE_PASS -->|Yes| PH13
    MECE_PASS -->|No| PH03
    
    PH13 --> NM_CHECK
    PH13 --> RM_CHECK
    PH13 --> SA_CHECK
    NM_CHECK --> GATE_PASS
    RM_CHECK --> GATE_PASS
    SA_CHECK --> GATE_PASS
    
    GATE_PASS -->|Yes| PH14
    GATE_PASS -->|No| PH07
    
    PH14 --> END

    style START fill:#e1f5ff
    style END fill:#c8e6c9
    style PH07 fill:#fff9c4
    style PH13 fill:#ffccbc
    style GATE_PASS fill:#ffccbc
```

---

## 3. Phase 5: 플레이어 식별 & 데이터 수집 상세도

```mermaid
sequenceDiagram
    participant User as 사용자
    participant SA as Structure Analyst
    participant RM as Reality Monitor
    participant EE as Evidence Engine
    participant DS as Data Sources
    participant ES as Evidence Store
    participant WE as World Engine
    participant RG as R-Graph

    User->>SA: "Top-N 플레이어 확인해줘"
    
    SA->>SA: Phase 5 시작<br/>플레이어 목록 템플릿 작성
    
    Note over SA,RM: Agent 협업 프로토콜<br/>data_collection_request
    SA->>RM: 데이터 수집 요청<br/>(YBM넷, 링글, 야나두...)
    
    RM->>EE: fetch_for_reality_slice()
    
    Note over EE,DS: Data Sources 선택
    EE->>DS: DART API 호출<br/>(YBM넷 매출)
    DS-->>EE: 817억원 (2023)
    
    EE->>DS: 웹 검색<br/>(링글 매출)
    DS-->>EE: 상반기 100억원 (2024)
    
    EE->>DS: 웹 검색<br/>(야나두 매출)
    DS-->>EE: 1Q 107억원 (2024)
    
    Note over EE,ES: Evidence 정규화
    EE->>ES: EVD-001 저장<br/>(YBM넷, 신뢰도 95%)
    EE->>ES: EVD-002 저장<br/>(링글, 신뢰도 85%)
    EE->>ES: EVD-003 저장<br/>(야나두, 신뢰도 85%)
    
    EE-->>RM: EvidenceBundle 반환<br/>(25개 Evidence)
    RM-->>SA: 데이터 수집 완료
    
    SA->>WE: ingest_evidence()<br/>(EVD-001~025)
    
    Note over WE,RG: R-Graph 업데이트
    WE->>RG: Actor 노드 생성<br/>(ACT-YBM_Net)
    WE->>RG: Actor 노드 생성<br/>(ACT-Ringle)
    WE->>RG: Actor 노드 생성<br/>(ACT-Yanadoo)
    WE->>RG: MoneyFlow 노드 생성<br/>(MFL-customers_to_YBM)
    WE->>RG: Edge 생성<br/>(actor_pays_actor)
    
    WE-->>SA: R-Graph 업데이트 완료<br/>(Top 50+ 플레이어)
    
    SA->>SA: ART-player_list 생성
```

---

## 4. Phase 7: 시장규모 추정 (4-Stage Metric Resolver) 상세도

```mermaid
flowchart TD
    START([Metric Request:<br/>MET-SAM])
    
    subgraph STAGE1[Stage 1: Direct Evidence]
        DIR_START[Evidence Engine 호출:<br/>직접 값 검색]
        DIR_SEARCH[Commercial Research<br/>Consulting Reports<br/>Brokerage Research]
        DIR_RESULT{직접 값<br/>발견?}
    end
    
    subgraph STAGE2[Stage 2: Derived - 4-Method]
        DER_START[Derived 경로 실행]
        
        M1[Method 1: Top-down<br/>e-러닝 시장 × 비율<br/>= 1,500억]
        
        M2[Method 2: Bottom-up<br/>R-Graph Actor 집계<br/>Top10 합산 ÷ 점유율<br/>= 10,000억]
        
        M3[Method 3: Fermi<br/>인구 × 참여율 × 지출<br/>42M × 15% × 20만원<br/>= 13,000억]
        
        M4[Method 4: Proxy<br/>일본 시장 × 조정계수<br/>= 18,000억]
    end
    
    subgraph STAGE3[Stage 3: Fusion]
        FUSION[가중 평균 계산]
        W1[Top-down: 0.2 가중치]
        W2[Bottom-up: 0.4 가중치]
        W3[Fermi: 0.3 가중치]
        W4[Proxy: 0.1 가중치]
        WEIGHTED[가중 평균<br/>= 10,000억]
    end
    
    subgraph STAGE4[Stage 4: Validation]
        CONV_CHECK{±30% 내<br/>수렴?}
        OUTLIER[Outlier 제거<br/>Top-down/Proxy]
        FINAL[최종 범위 설정<br/>7,000~13,000억]
    end
    
    VALUE_RECORD[ValueRecord 생성<br/>VAL-SAM<br/>point_estimate: 10,000억<br/>quality: 75%<br/>lineage: EVD-001,002,003...]
    
    VALUE_STORE[(Value Store<br/>저장)]
    
    END([Phase 7 완료])

    START --> DIR_START
    DIR_START --> DIR_SEARCH
    DIR_SEARCH --> DIR_RESULT
    
    DIR_RESULT -->|No| DER_START
    DIR_RESULT -->|Yes| VALUE_RECORD
    
    DER_START --> M1
    DER_START --> M2
    DER_START --> M3
    DER_START --> M4
    
    M1 --> FUSION
    M2 --> FUSION
    M3 --> FUSION
    M4 --> FUSION
    
    FUSION --> W1
    FUSION --> W2
    FUSION --> W3
    FUSION --> W4
    
    W1 --> WEIGHTED
    W2 --> WEIGHTED
    W3 --> WEIGHTED
    W4 --> WEIGHTED
    
    WEIGHTED --> CONV_CHECK
    CONV_CHECK -->|No| OUTLIER
    OUTLIER --> FINAL
    CONV_CHECK -->|Yes| FINAL
    
    FINAL --> VALUE_RECORD
    VALUE_RECORD --> VALUE_STORE
    VALUE_STORE --> END

    style STAGE1 fill:#e3f2fd
    style STAGE2 fill:#fff3e0
    style STAGE3 fill:#f1f8e9
    style STAGE4 fill:#fce4ec
    style VALUE_RECORD fill:#c8e6c9
```

---

## 3-1. 전체 워크플로우 순서도 (Brownfield: 15 Phases)

**Note**: Brownfield = 조직 통합 분석, **PH00** + PH01-PH14

```mermaid
flowchart TD
    START([사용자 질문:<br/>우리 회사가 이 시장에...])
    
    PH00[Phase 0: Project Context Setup<br/>조직 현황/역량/제약]
    PH00_1[내부 데이터 수집<br/>EVD-internal-*]
    PH00_2[focal_actor R-Graph<br/>ACT-CLIENT-*]
    PH00_3[Project Context 생성<br/>PRJ-*]
    
    PH01[Phase 1: 시장 정의<br/>+ focal_actor 위치]
    PH02[Phase 2: 도메인 분류<br/>+ 현재 도메인 믹스]
    PH03[Phase 3-4: BM 분류<br/>+ 현재 BM 패턴]
    
    PH05[Phase 5: 플레이어 식별<br/>+ 경쟁사 대비 포지션]
    
    PH06[Phase 6: 가치사슬<br/>+ 우리 현재 구조]
    
    PH07[Phase 7: 시장규모<br/>+ SOM_for_project]
    PH07_1[Market-level Metric:<br/>TAM/SAM]
    PH07_2[Project-level Metric:<br/>SOM/Baseline/Delta]
    
    PH08[Phase 8-11: 경쟁구조<br/>+ 우리 경쟁력]
    
    PH12[Phase 12: MECE 검증]
    MECE_PASS{PASS?}
    
    PH13[Phase 13: 3자 검증]
    GATE_PASS{PASS?}
    
    PH14[Phase 14: 리포트<br/>+ Position/Opportunity]
    
    END([Market Reality Report<br/>+ Organization Perspective])

    START --> PH00
    
    PH00 --> PH00_1
    PH00_1 --> PH00_2
    PH00_2 --> PH00_3
    
    PH00_3 --> PH01
    PH01 --> PH02
    PH02 --> PH03
    PH03 --> PH05
    
    PH05 --> PH06
    PH06 --> PH07
    
    PH07 --> PH07_1
    PH07 --> PH07_2
    PH07_1 --> PH08
    PH07_2 --> PH08
    
    PH08 --> PH12
    PH12 --> MECE_PASS
    MECE_PASS -->|Yes| PH13
    MECE_PASS -->|No| PH03
    
    PH13 --> GATE_PASS
    GATE_PASS -->|Yes| PH14
    GATE_PASS -->|No| PH07
    
    PH14 --> END

    style START fill:#fff4e1
    style END fill:#c8e6c9
    style PH00 fill:#ffeb3b,stroke:#f57c00,stroke-width:3px
    style PH00_1 fill:#fff9c4
    style PH00_2 fill:#fff9c4
    style PH00_3 fill:#fff9c4
    style PH07 fill:#ffe0b2
    style PH13 fill:#ffccbc
```

---

## 4. Phase 0: Project Context Setup (Brownfield 전용)

```mermaid
sequenceDiagram
    autonumber
    
    participant User as 사용자/조직
    participant SA as Structure Analyst
    participant RM as Reality Monitor
    participant EE as Evidence Engine
    participant INT_DATA as 내부 데이터
    participant ES as Evidence Store
    participant WE as World Engine
    participant RG as R-Graph
    participant PCS as Project Context Store

    User->>SA: "우리 회사가 이 시장에 진입하려면?"
    
    Note over SA: PH00 Phase 시작
    SA->>User: 조직 현황 폼/인터뷰
    User-->>SA: 매출/역량/제약/목표 제공
    
    Note over SA,RM: 내부 데이터 수집
    SA->>RM: data_collection_request (internal)
    RM->>EE: fetch_internal_data()
    
    EE->>INT_DATA: ERP 매출 데이터
    INT_DATA-->>EE: 800억원 (2024)
    
    EE->>INT_DATA: CRM 고객 데이터
    INT_DATA-->>EE: 45,000명
    
    EE->>INT_DATA: 재무제표
    INT_DATA-->>EE: 마진 구조
    
    Note over EE,ES: Evidence 정규화
    EE->>ES: EVD-internal-001 (재무제표)
    EE->>ES: EVD-internal-002 (CRM)
    EE-->>RM: EvidenceBundle (내부)
    RM-->>SA: 내부 데이터 수집 완료
    
    Note over SA,WE: focal_actor R-Graph 구성
    SA->>WE: ingest_project_context()
    WE->>RG: Actor 노드 생성 (ACT-CLIENT-*)
    WE->>RG: MoneyFlow/State 추가
    WE-->>SA: focal_actor 구성 완료
    
    Note over SA: Capability → Trait 매핑
    SA->>SA: "120개 지점" → capability_traits
    
    Note over SA,PCS: Project Context 생성
    SA->>PCS: PRJ-* 저장
    PCS-->>SA: project_context_id 반환
    
    Note over SA: PH00 완료 → PH01-PH14 진행
    SA-->>User: project_context_id + 분석 시작
```

---

## 5. 데이터 흐름도 (Evidence → Graph → Report)

```mermaid
flowchart LR
    subgraph EXTERNAL[외부 데이터 소스]
        DART[DART<br/>상장사 재무]
        WEB[웹 검색<br/>언론/IR]
        KOSIS[KOSIS<br/>인구통계]
        MKT[시장조사<br/>리포트]
    end
    
    subgraph EVIDENCE[Evidence Store]
        EVD1[EVD-001<br/>YBM 817억]
        EVD2[EVD-002<br/>링글 100억]
        EVD3[EVD-003<br/>야나두 107억]
        EVD_N[EVD-...<br/>총 25개]
    end
    
    subgraph RGRAPH[Reality Graph]
        ACT[Actor 노드<br/>Top 50+ 플레이어]
        MFL[MoneyFlow 노드<br/>30+ 흐름]
        STA[State 노드<br/>시장 구조]
    end
    
    subgraph PGRAPH[Pattern Graph]
        BM[23개 BM<br/>Pattern 노드]
        VC[가치사슬<br/>템플릿]
    end
    
    subgraph VGRAPH[Value Graph]
        MET[Metric 노드<br/>TAM/SAM/HHI...]
        VAL[ValueRecord<br/>47개 계산 결과]
    end
    
    subgraph ARTIFACTS[Artifacts & Memory]
        ART1[ART-needs<br/>분류]
        ART2[ART-domain<br/>분류]
        ART3[ART-player<br/>목록]
        ART4[ART-market_size<br/>추정]
        ART_N[ART-...<br/>총 15개]
    end
    
    REPORT[Market Reality<br/>Report Final.md<br/>548줄]

    DART --> EVD1
    WEB --> EVD2
    WEB --> EVD3
    KOSIS --> EVD_N
    MKT --> EVD_N
    
    EVD1 --> ACT
    EVD2 --> ACT
    EVD3 --> ACT
    EVD_N --> STA
    
    ACT --> MFL
    
    BM -.패턴 매칭.-> ACT
    VC -.가치사슬.-> MFL
    
    ACT --> VAL
    MFL --> VAL
    BM --> VAL
    
    MET --> VAL
    
    EVD1 -.lineage.-> VAL
    EVD2 -.lineage.-> VAL
    EVD3 -.lineage.-> VAL
    
    VAL --> ART4
    ACT --> ART3
    BM --> ART2
    
    ART1 --> REPORT
    ART2 --> REPORT
    ART3 --> REPORT
    ART4 --> REPORT
    ART_N --> REPORT
    VAL --> REPORT

    style EXTERNAL fill:#e1f5ff
    style EVIDENCE fill:#fff9c4
    style RGRAPH fill:#c8e6c9
    style PGRAPH fill:#f3e5f5
    style VGRAPH fill:#ffe0b2
    style ARTIFACTS fill:#d1c4e9
    style REPORT fill:#80deea,stroke:#006064,stroke-width:3px
```

---

## 6. Phase 13: 3자 검증 게이트 상세도

```mermaid
flowchart TB
    START[Phase 12 MECE 검증 완료]
    
    REQUEST[Structure Analyst:<br/>3자 검증 요청]
    
    subgraph NM_VALIDATION[Numerical Modeler 검증]
        NM_START[체크리스트 시작]
        NM_1{계산 논리<br/>타당성?}
        NM_2{4-Method<br/>수렴?}
        NM_3{합산<br/>일치?}
        NM_RESULT[검증 결과:<br/>PASS/FAIL]
    end
    
    subgraph RM_VALIDATION[Reality Monitor 검증]
        RM_START[체크리스트 시작]
        RM_1{출처 품질<br/>≥70%?}
        RM_2{추적성<br/>100%?}
        RM_RESULT[검증 결과:<br/>PASS/FAIL]
    end
    
    subgraph SA_VALIDATION[Structure Analyst 검증]
        SA_START[체크리스트 시작]
        SA_1{목표<br/>정렬?}
        SA_2{UMIS 원칙<br/>준수?}
        SA_3{전체 품질<br/>A급?}
        SA_RESULT[검증 결과:<br/>PASS/FAIL]
    end
    
    AGGREGATE{3명 모두<br/>PASS?}
    
    SUCCESS[✅ 검증 통과<br/>Phase 14로 진행]
    FAIL[❌ 검증 실패<br/>해당 Phase 재수행]
    
    START --> REQUEST
    
    REQUEST --> NM_START
    REQUEST --> RM_START
    REQUEST --> SA_START
    
    NM_START --> NM_1
    NM_1 -->|Yes| NM_2
    NM_1 -->|No| NM_RESULT
    NM_2 -->|Yes| NM_3
    NM_2 -->|No| NM_RESULT
    NM_3 -->|Yes| NM_RESULT
    NM_3 -->|No| NM_RESULT
    
    RM_START --> RM_1
    RM_1 -->|Yes| RM_2
    RM_1 -->|No| RM_RESULT
    RM_2 -->|Yes| RM_RESULT
    RM_2 -->|No| RM_RESULT
    
    SA_START --> SA_1
    SA_1 -->|Yes| SA_2
    SA_1 -->|No| SA_RESULT
    SA_2 -->|Yes| SA_3
    SA_2 -->|No| SA_RESULT
    SA_3 -->|Yes| SA_RESULT
    SA_3 -->|No| SA_RESULT
    
    NM_RESULT --> AGGREGATE
    RM_RESULT --> AGGREGATE
    SA_RESULT --> AGGREGATE
    
    AGGREGATE -->|Yes| SUCCESS
    AGGREGATE -->|No| FAIL

    style NM_VALIDATION fill:#e3f2fd
    style RM_VALIDATION fill:#f1f8e9
    style SA_VALIDATION fill:#fff3e0
    style SUCCESS fill:#c8e6c9
    style FAIL fill:#ffcdd2
```

---

## 7. Value Engine 내부 구조도 (Metric Resolver + BeliefEngine)

```mermaid
graph TB
    subgraph INPUT[입력]
        REQ["MetricRequest
        metric_id: MET-SAM
        context: {...}"]
        POL["Policy:
        decision_balanced"]
    end
    
    subgraph SPEC[Metric Spec 조회]
        SPEC_LOAD["cmis.yaml에서
        MET-SAM 정의 로드"]
        SPEC_DATA["직접 소스 목록
        파생 경로
        Prior 설정
        resolution_protocol"]
    end
    
    subgraph RESOLVER[Metric Resolver - 4 Stages]
        STAGE1["Stage 1:
        Direct Evidence"]
        STAGE2["Stage 2:
        Derived"]
        STAGE3["Stage 3:
        Prior Estimation<br/>⭐ BeliefEngine 호출"]
        STAGE4["Stage 4:
        Fusion & Validation"]
    end
    
    subgraph ENGINES[다른 엔진 호출]
        EE_CALL["Evidence Engine:
        외부 데이터 수집"]
        WE_CALL["World Engine v2.0:
        R-Graph 쿼리"]
        PE_CALL["Pattern Engine v2.0:
        패턴 매칭"]
        BE_CALL["Belief Engine:
        Prior Distribution 조회<br/>⭐ 신규"]
        POL_CALL["Policy Engine:
        검증 게이트"]
    end
    
    subgraph GRAPHS[그래프 참조]
        RG_READ["R-Graph 읽기:
        Actor 매출 집계"]
        PG_READ["P-Graph 읽기:
        패턴 벤치마크"]
        VG_READ["V-Graph 읽기:
        공식/관계"]
    end
    
    subgraph OUTPUT[출력]
        VR["ValueRecord
        point_estimate
        quality
        lineage"]
        VP["Value Program
        실행 로그"]
    end
    
    REQ --> SPEC_LOAD
    POL --> SPEC_LOAD
    SPEC_LOAD --> SPEC_DATA
    
    SPEC_DATA --> STAGE1
    
    STAGE1 --> EE_CALL
    EE_CALL -.-> |실패| STAGE2
    EE_CALL -.-> |성공| VR
    
    STAGE2 --> RG_READ
    STAGE2 --> VG_READ
    RG_READ --> STAGE3
    VG_READ --> STAGE3
    
    STAGE3 --> BE_CALL
    BE_CALL -.-> PE_CALL
    PE_CALL --> PG_READ
    PG_READ -.Pattern Benchmark.-> BE_CALL
    BE_CALL -.Prior Distribution.-> STAGE3
    
    STAGE3 --> STAGE4
    STAGE4 --> POL_CALL
    POL_CALL --> VR
    
    VR --> VP
    
    style INPUT fill:#e1f5ff
    style SPEC fill:#fff9c4
    style RESOLVER fill:#c8e6c9
    style ENGINES fill:#f3e5f5
    style GRAPHS fill:#ffe0b2
    style OUTPUT fill:#80deea
```

---

## 8. 협업 프로토콜 다이어그램

```mermaid
sequenceDiagram
    autonumber
    
    participant User as 사용자
    participant SA as Structure Analyst
    participant NM as Numerical Modeler
    participant RM as Reality Monitor
    participant WE as World Engine
    participant VE as Value Engine
    participant PE as Pattern Engine
    
    User->>SA: "한국 성인 어학교육 시장..."
    
    Note over SA: Phase 1-4: 시장/도메인/BM 정의
    SA->>SA: Needs/Domain/BM 분류
    
    Note over SA,RM: data_collection_request 프로토콜
    SA->>RM: 데이터 수집 요청
    RM->>WE: Evidence 수집 + R-Graph 구축
    WE-->>RM: R-Graph 완료
    RM-->>SA: 데이터 수집 완료
    
    Note over SA,NM: structure_to_numerical_support 프로토콜
    SA->>NM: 가치사슬 Metric 계산 요청
    NM->>VE: evaluate_metrics()
    VE->>WE: R-Graph 쿼리 (Actor 매출)
    WE-->>VE: Actor 데이터 반환
    VE->>PE: Pattern Prior 조회
    PE-->>VE: 패턴 벤치마크 반환
    VE-->>NM: ValueRecord 반환
    NM-->>SA: 계산 결과 전달
    
    Note over SA: Phase 8-11: 경쟁구조 분석
    SA->>NM: 경쟁 Metric 계산 요청
    NM->>VE: HHI/CR3 계산
    VE-->>NM: 경쟁 Metric 반환
    NM-->>SA: 경쟁 분석 완료
    
    Note right of SA: structure_validation_request 프로토콜 (3자 검증)
    SA->>NM: 검증 요청
    SA->>RM: 검증 요청
    SA->>SA: 자체 검증
    
    NM->>NM: 계산 논리/수렴/합산 검증
    RM->>RM: 출처 품질/추적성 검증
    SA->>SA: 목표 정렬/원칙/품질 검증
    
    NM-->>SA: ✅ PASS
    RM-->>SA: ✅ PASS
    SA->>SA: ✅ PASS
    
    Note over SA: Phase 14: 리포트 생성
    SA->>SA: Artifact 통합
    SA-->>User: Market Reality Report
```

---

## 9. 전체 시스템 통합 다이어그램

```mermaid
graph TB
    USER([사용자])
    
    subgraph INTERACTION[Interaction Plane]
        CLI[CLI/Notebook]
    end
    
    subgraph ROLE[Role Plane]
        SA[Structure Analyst<br/>워크플로우 주도]
    end
    
    subgraph WORKFLOW[14-Phase Workflow]
        P1_4[Phase 1-4<br/>정의/분류]
        P5[Phase 5<br/>데이터 수집]
        P6[Phase 6<br/>가치사슬]
        P7[Phase 7<br/>시장규모]
        P8_11[Phase 8-11<br/>경쟁구조]
        P12[Phase 12<br/>MECE]
        P13[Phase 13<br/>3자 검증]
        P14[Phase 14<br/>리포트]
    end
    
    subgraph COGNITION[Cognition Plane - 9 Engines]
        direction LR
        EE[Evidence<br/>Engine]
        WE[World<br/>Engine<br/>v2.0]
        PE[Pattern<br/>Engine<br/>v2.0]
        VE[Value<br/>Engine]
        BE[Belief<br/>Engine<br/>⭐]
        SE[Strategy<br/>Engine<br/>v1.0]
        LE[Learning<br/>Engine<br/>v1.0]
        POL[Policy<br/>Engine]
        WF[Workflow<br/>CLI]
    end
    
    subgraph SUBSTRATE[Substrate Plane]
        direction TB
        
        subgraph GRAPHS[Graphs]
            RG[Reality<br/>Graph]
            PG[Pattern<br/>Graph]
            VG[Value<br/>Graph]
        end
        
        subgraph STORES[Stores]
            EVS[Evidence<br/>Store]
            VLS[Value<br/>Store]
            MEM[Memory<br/>Store]
        end
    end
    
    OUTPUT[Market Reality<br/>Report.md<br/>548줄]
    
    USER --> CLI
    CLI --> SA
    SA --> P1_4
    
    P1_4 --> P5
    P5 --> EE
    EE --> EVS
    EE --> WE
    WE --> RG
    
    P5 --> P6
    P6 --> PE
    PE --> PG
    PE --> RG
    
    P6 --> P7
    P7 --> VE
    VE --> RG
    VE --> PG
    VE --> BE
    BE --> VG
    VE --> VG
    VE --> VLS
    
    P7 --> P8_11
    P8_11 --> VE
    VE -.Strategy.-> SE
    SE --> LE
    
    P8_11 --> P12
    P12 --> POL
    POL --> P13
    
    P13 --> P14
    P14 --> MEM
    MEM --> OUTPUT
    VLS --> OUTPUT
    
    OUTPUT --> USER

    style USER fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    style OUTPUT fill:#80deea,stroke:#006064,stroke-width:3px
    style INTERACTION fill:#e1f5ff
    style ROLE fill:#fff4e1
    style WORKFLOW fill:#fff9c4
    style COGNITION fill:#e8f5e9
    style SUBSTRATE fill:#f3e5f5
    style P7 fill:#ffeb3b
    style P13 fill:#ff9800
    style BE fill:#ffeb3b,stroke:#f57c00,stroke-width:2px
```

---

## 10. Lineage 추적 흐름도

```mermaid
flowchart TD
    START[사용자 질문]
    
    EVD1["Evidence 수집
    EVD-001: YBM 817억
    source: DART
    reliability: 95%"]
    
    EVD2["Evidence 수집
    EVD-002: 링글 100억
    source: 언론
    reliability: 85%"]
    
    RG_ACT["R-Graph Actor 생성
    ACT-YBM_Net
    metadata.revenue: 817억
    lineage.from_evidence: EVD-001"]
    
    VE_CALC["Value Engine 계산
    Bottom-up Method
    R-Graph Actor 집계"]
    
    VAL_SAM["ValueRecord 생성
    VAL-SAM
    point_estimate: 10,000억
    quality.literal_ratio: 0.75"]
    
    LINEAGE["Lineage 자동 기록
    from_evidence_ids:
    - EVD-001, EVD-002, EVD-003
    from_value_ids: []
    engine_ids:
    - value_engine
    - evidence_engine"]
    
    ART["Artifact 생성
    ART-market_size_estimate
    references: VAL-SAM"]
    
    REPORT["리포트 섹션
    시장 규모: 1조원
    근거: EVD-001,002,003"]
    
    USER_VIEW["사용자가 보는 내용:
    YBM넷 817억(DART)을 포함한
    Top10 합산 기반 추정"]
    
    START --> EVD1
    START --> EVD2
    
    EVD1 --> RG_ACT
    EVD2 --> RG_ACT
    
    RG_ACT --> VE_CALC
    VE_CALC --> VAL_SAM
    
    VAL_SAM --> LINEAGE
    LINEAGE --> ART
    ART --> REPORT
    REPORT --> USER_VIEW

    style EVD1 fill:#fff9c4
    style EVD2 fill:#fff9c4
    style RG_ACT fill:#c8e6c9
    style VAL_SAM fill:#ffe0b2
    style LINEAGE fill:#ffccbc,stroke:#d84315,stroke-width:2px
    style USER_VIEW fill:#80deea
```

---

## 11. 4단계 루프 다이어그램 (CMIS 핵심)

**신규 추가 (2025-12-12)**:

```mermaid
flowchart LR
    subgraph UNDERSTAND[1️⃣ Understand]
        WE[World Engine v2.0<br/>R-Graph 구축]
        PE_M[Pattern Engine v2.0<br/>패턴 매칭]
    end
    
    subgraph DISCOVER[2️⃣ Discover]
        PE_G[Pattern Engine v2.0<br/>Gap 탐지]
        VE_O[Value Engine<br/>기회 Sizing]
    end
    
    subgraph DECIDE[3️⃣ Decide]
        SE[Strategy Engine v1.0<br/>전략 생성/평가]
        VE_S[Value Engine<br/>시나리오 시뮬레이션]
    end
    
    subgraph LEARN[4️⃣ Learn]
        LE[Learning Engine v1.0<br/>Outcome 비교]
        BE[Belief Engine<br/>Prior 업데이트]
    end
    
    UNDERSTAND --> DISCOVER
    DISCOVER --> DECIDE
    DECIDE --> LEARN
    LEARN -.개선된 Prior.-> UNDERSTAND
    
    style UNDERSTAND fill:#e3f2fd
    style DISCOVER fill:#f1f8e9
    style DECIDE fill:#fff3e0
    style LEARN fill:#fce4ec
    style BE fill:#ffeb3b,stroke:#f57c00,stroke-width:2px
```

**4단계 루프 설명**:
1. **Understand** - 시장 구조/패턴 이해 (World + Pattern)
2. **Discover** - 기회/갭 발굴 (Pattern Gap + Value)
3. **Decide** - 전략 설계/선택 (Strategy + Value)
4. **Learn** - 실행 결과 학습 (Learning + Belief) → 다시 Understand로

---

## 12. BeliefEngine 통합 다이어그램 (신규)

**신규 추가 (2025-12-12)**:

```mermaid
flowchart TD
    START[ValueEngine<br/>Metric 계산 시작]
    
    S1[Stage 1: Direct Evidence]
    S1_FAIL{Evidence<br/>발견?}
    
    S2[Stage 2: Derived]
    S2_FAIL{계산<br/>가능?}
    
    S3[Stage 3: Prior Estimation]
    
    subgraph BELIEF[BeliefEngine]
        BE_START[query_prior_api 호출]
        BE_PATTERN[Pattern Benchmark 조회]
        BE_PRIOR[Prior Distribution 생성]
        BE_CONF[Confidence 계산]
    end
    
    S4[Stage 4: Fusion]
    
    OUT[ValueRecord 반환]
    
    LEARN[LearningEngine<br/>Outcome 관측]
    
    subgraph BELIEF_UPDATE[BeliefEngine Update]
        BU_START[update_belief_api 호출]
        BU_BAYES[Bayesian Update]
        BU_SAVE[업데이트된 Belief 저장]
    end
    
    START --> S1
    S1 --> S1_FAIL
    S1_FAIL -->|No| S2
    S1_FAIL -->|Yes| OUT
    
    S2 --> S2_FAIL
    S2_FAIL -->|No| S3
    S2_FAIL -->|Yes| S4
    
    S3 --> BE_START
    BE_START --> BE_PATTERN
    BE_PATTERN --> BE_PRIOR
    BE_PRIOR --> BE_CONF
    BE_CONF --> S4
    
    S4 --> OUT
    OUT --> LEARN
    
    LEARN --> BU_START
    BU_START --> BU_BAYES
    BU_BAYES --> BU_SAVE
    BU_SAVE -.다음 조회 시<br/>개선된 Prior.-> BE_START
    
    style BELIEF fill:#ffeb3b,stroke:#f57c00,stroke-width:2px
    style BELIEF_UPDATE fill:#ffe0b2,stroke:#f57c00,stroke-width:2px
    style S3 fill:#fff9c4
```

---

## 13. 문서 업데이트 요약

**2025-12-12 최신 업데이트** (v3.0):
- ✅ BeliefEngine 추가 (9번째 엔진)
- ✅ 4단계 루프 다이어그램 추가 (Understand → Discover → Decide → Learn)
- ✅ BeliefEngine 통합 다이어그램 추가
- ✅ ValueEngine 내부 구조 업데이트 (BeliefEngine 연동)
- ✅ Cognition Plane 9개 엔진 반영
- ✅ World Engine v2.0, Strategy Engine v1.0, Learning Engine v1.0 버전 표시
- ✅ Workflow CLI 추가

**2025-12-05 업데이트** (v2.0):
- ✅ Substrate Plane에 Project Context Store (PRJ-*) 추가
- ✅ Greenfield vs Brownfield 워크플로우 분기 다이어그램 추가
- ✅ Brownfield 15-Phase 순서도 추가 (PH00 포함)
- ✅ Phase 0: Project Context Setup 상세 시퀀스 다이어그램 추가

**다이어그램 목록** (총 15개):
1. 전체 아키텍처 (4 Planes + 9 Engines)
2. Greenfield vs Brownfield 분기
3. Greenfield 워크플로우 (14 Phases)
4. Brownfield 워크플로우 (15 Phases, PH00 포함)
5. Phase 0: Project Context Setup
6. Phase 5: 플레이어 식별
7. Phase 7: 시장규모 추정 (4-Stage Metric Resolver + BeliefEngine)
8. 데이터 흐름도
9. Phase 13: 3자 검증 게이트
10. Value Engine 내부 구조 (BeliefEngine 연동)
11. 협업 프로토콜
12. 전체 시스템 통합 (9 Engines)
13. Lineage 추적 흐름
14. **4단계 루프** (신규)
15. **BeliefEngine 통합** (신규)

---

**작성일**: 2025-12-12
**버전**: v3.0 (CMIS v3.3 기준, BeliefEngine 포함)
**상태**: Production Ready (9/9 엔진 완성)
**노트**: 이 다이어그램들은 Mermaid 형식으로 작성되어 GitHub/Markdown 렌더러에서 자동으로 시각화됩니다.

