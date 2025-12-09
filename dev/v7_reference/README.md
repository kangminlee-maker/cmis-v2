# v7 Reference Materials

CMIS 개발 참고용 v7 (UMIS) 자료 모음

---

## 📁 구조

```
v7_reference/
├── code/                  # v7 실제 코드
│   └── v7_reference_code/ # GitHub: kangminlee-maker/umis@alpha
│       ├── umis_rag/      # v7 엔진 (6-Agent, 4-Stage Estimator)
│       ├── config/        # v7 설정
│       └── docs/          # v7 문서
│
├── docs/                  # v7 문서/스키마
│   ├── Observer_v7.x/     # Observer 관련
│   │   ├── umis_strategic_frameworks.yaml
│   │   └── value_chain_benchmarks.yaml
│   └── reference_deprecated/  # 구버전 Blueprint
│       ├── UMIS_ARCHITECTURE_BLUEPRINT.md
│       ├── UMIS_ARCHITECTURE_BLUEPRINT_v8.md
│       └── umis.yaml, umis_v8.yaml
│
└── outputs/               # v7 결과물 예시
    └── market_reality_report_v7.x/
        ├── Market_Reality_Report_Final.md (548줄)
        ├── 00_Guardian_Work_Log.md
        ├── OPP_*.md (기회 카드)
        └── ...
```

---

## 🎯 재사용 분석

**재사용된 v7 코드**:
- ✅ DART API (`umis_rag/utils/dart_api.py`)
  - 11개 기업 검증, 91% 성공률
  - CMIS: `cmis_core/evidence/dart_connector.py`

- ✅ Fusion Layer (`umis_rag/agents/estimator/fusion_layer.py`)
  - 가중 평균, 범위 교집합 알고리즘
  - CMIS: `cmis_core/value_engine.py`

**참고한 v7 설계**:
- Evidence Collector (4-Source, Early Return)
- Fermi Estimator (재귀 없음, max_depth=2)
- 6-Agent 협업 프로토콜

상세: `../docs/analysis/V7_Code_Reuse_Analysis.md`

---

## 📖 v7 vs CMIS 차이

| 측면 | v7 (UMIS) | CMIS |
|------|-----------|------|
| 아키텍처 | 6-Agent + 4-Layer RAG | 4-Graph + 7-Engine |
| 데이터 | 텍스트 중심 | Graph 중심 |
| 패턴 | 54개 고정 | Trait 기반 유연 |
| 추정 | 4-Stage Estimator | 4-Method Fusion |
| 컨텍스트 | 암묵적 | Project Context Layer |
| 실행 | Cursor 대화 | CLI + Python API |

---

**참고 목적**: CMIS 확장 시 v7 경험/검증 활용

**작성일**: 2025-12-09

