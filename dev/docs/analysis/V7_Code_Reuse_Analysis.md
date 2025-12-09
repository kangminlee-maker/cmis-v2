---
**이력**: 2025-12-09 UMIS v9 → CMIS로 브랜드 변경
- Universal Market Intelligence → Contextual Market Intelligence
- v9 핵심 차별점 (Project Context Layer) 반영
---

# v7.x 코드 재사용 분석: v9 구현에 활용 가능한 모듈

**문서 목적**: v7.x 레포 (https://github.com/kangminlee-maker/umis/tree/alpha)에서 v9 구현 시 재사용 가능한 코드/로직/패턴 분석

**작성일**: 2025-12-05

**v7.x 버전**: v7.11.0 (4-Stage Fusion Architecture)

---

## 1. 재사용 가능 모듈 요약

| v7.x 모듈 | v9 대응 | 재사용 가능성 | 우선순위 |
|----------|---------|-------------|---------|
| `dart_api.py` | Evidence Engine | **100%** | ⭐⭐⭐ 최우선 |
| `evidence_collector.py` | Evidence Engine | **80%** | ⭐⭐⭐ 최우선 |
| `fusion_layer.py` | Value Engine (Fusion) | **90%** | ⭐⭐⭐ 최우선 |
| `fermi_estimator.py` | Value Engine (Fermi) | **70%** | ⭐⭐ 중요 |
| `rag_searcher.py` | Pattern Engine | **60%** | ⭐⭐ 중요 |
| `config.py` | Config Loader | **80%** | ⭐⭐ 중요 |
| `validator_source.py` | Evidence Engine | **50%** | ⭐ 참고 |
| `excel/*` | Report Generator | **30%** | ⭐ 참고 |

---

## 2. 최우선 재사용: DART API (100%)

### 2.1 v7.x 코드

**파일**: `umis_rag/utils/dart_api.py` (335줄)

**핵심 기능**:
```python
class DARTClient:
    def get_corp_code(company_name: str) -> str
        # ✅ 정확한 이름 매칭 우선
        # ✅ 부분 매칭 시 상장사 우선 (stock_code 기준)
        # ✅ "하이브" 검색 시 29개 중 자동 선별
    
    def get_financials(corp_code, year, fs_div='OFS') -> Dict
        # ✅ 개별재무제표 (OFS) 우선
        # ✅ fs_div 불일치 시 명시적 에러
        # ✅ strict 모드 지원
    
    def get_report_list(corp_code, year, max_retries=3) -> List
        # ✅ 900 오류 재시도 (3회, 2초 대기)
        # ✅ [기재정정] > 원본 > [첨부정정] 우선순위
    
    def download_document(rcept_no) -> str
        # ✅ ZIP 압축 자동 해제
        # ✅ XML 원문 파싱
```

**검증 현황**:
- ✅ 11개 기업으로 검증 완료 (삼성전자, LG전자, GS리테일 등)
- ✅ 537개 항목 성공률 91%
- ✅ 프로덕션 사용 중

### 2.2 v9 적용 방안

**거의 그대로 복사 가능**:

```python
# v9: umis_v9_core/evidence/dart_connector.py
# v7 dart_api.py를 그대로 복사 + 소폭 수정

from v7_reference_code.umis_rag.utils.dart_api import DARTClient  # 임시

class DARTConnector:
    """v9 Evidence Engine용 DART 연동"""
    
    def __init__(self, api_key: str = None):
        self.client = DARTClient(api_key)  # v7 코드 재사용
        self.evidence_store = get_evidence_store()
    
    def fetch_company_revenue(
        self,
        company_name: str,
        year: int
    ) -> Evidence:
        """v7 로직 + v9 Evidence 스키마로 변환"""
        
        # 1. v7 DARTClient 호출
        corp_code = self.client.get_corp_code(company_name)
        if not corp_code:
            return None
        
        financials = self.client.get_financials(corp_code, year, fs_div='OFS')
        if not financials:
            return None
        
        # 2. 매출액 항목 찾기
        revenue_items = [
            item for item in financials
            if '매출액' in item.get('account_nm', '')
            and item.get('sj_div') == '재무상태표'  # 손익계산서 확인
        ]
        
        if not revenue_items:
            return None
        
        revenue = float(revenue_items[0]['thstrm_amount'])  # 당기금액
        
        # 3. v9 Evidence 스키마로 변환
        evidence = Evidence(
            evidence_id=f"EVD-DART-{corp_code}-{year}",
            source_tier="official",  # v9 스키마
            url_or_path=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo=...",
            content_ref=f"{company_name} {year} 사업보고서",
            metadata={
                "company": company_name,
                "corp_code": corp_code,
                "year": year,
                "revenue": revenue,
                "currency": "KRW"
            },
            retrieved_at=datetime.now().isoformat(),
            source_id="KR_DART_filings"  # v9 data_sources 참조
        )
        
        # 4. Evidence Store 저장
        self.evidence_store.save(evidence)
        
        return evidence
```

**작업량 절감**: 90% (DART API 연동/재시도/파싱 로직 검증 완료)

**TODO 업데이트**:
- evidence-1: ~~DART API 연동~~ → **v7 코드 복사 + 스키마 변환만**

---

## 3. 최우선 재사용: Fusion Layer (90%)

### 3.1 v7.x 코드

**파일**: `umis_rag/agents/estimator/fusion_layer.py` (344줄)

**핵심 로직**:
```python
class FusionLayer:
    def synthesize(
        self,
        evidence: Evidence,
        prior_result: Optional[EstimationResult],
        fermi_result: Optional[EstimationResult]
    ) -> EstimationResult:
        """여러 추정 결과 융합"""
        
        # Case 1: 확정 값이 있으면 100% 사용
        if evidence.definite_value is not None:
            return create_definite_result(evidence.definite_value)
        
        # Case 2: Prior만 있음
        if prior_result and not fermi_result:
            return clip_to_hard_bounds(prior_result)
        
        # Case 3: Prior + Fermi 융합
        if prior_result and fermi_result:
            # 가중 평균 (certainty 기반)
            weights = self._calculate_weights(prior_result, fermi_result)
            fused_value = (
                prior_result.value * weights['prior'] +
                fermi_result.value * weights['fermi']
            )
            
            # 범위 교집합
            final_range = self._intersect_ranges(
                prior_result.range,
                fermi_result.range
            )
            
            return EstimationResult(
                value=fused_value,
                range=final_range,
                fusion_weights=weights
            )
```

**핵심 알고리즘**:
1. **Certainty 기반 가중치**: high=0.9, medium=0.6, low=0.3
2. **범위 교집합**: 두 추정의 겹치는 범위만 사용
3. **Hard Bounds 클리핑**: 논리적 제약 절대 위반 불가

### 3.2 v9 적용 방안

**v9 Value Engine Fusion Stage로 직접 이식**:

```python
# v9: umis_v9_core/value_engine.py

class MetricResolver:
    
    def _stage_4_fusion(
        self,
        candidates: List[ValueRecord]  # v9 용어
    ) -> ValueRecord:
        """v7 FusionLayer 로직 재사용"""
        
        # v7 코드를 v9 스키마로 변환만 하면 됨
        
        # 1. Certainty → quality.literal_ratio 매핑
        weights = {
            c.method: self._certainty_to_weight(c.quality.get("certainty", "medium"))
            for c in candidates
        }
        
        # 2. 가중 평균 (v7과 동일)
        weighted_avg = sum(
            c.point_estimate * weights[c.method]
            for c in candidates
        ) / sum(weights.values())
        
        # 3. 범위 교집합 (v7과 동일)
        ranges = [c.distribution for c in candidates if c.distribution]
        intersected_range = self._intersect_ranges(ranges)  # v7 로직 복사
        
        # 4. v9 ValueRecord 생성
        return ValueRecord(
            metric_id=candidates[0].metric_id,
            point_estimate=weighted_avg,
            distribution=intersected_range,
            quality={
                "method": "4_method_fusion",
                "literal_ratio": self._calculate_literal_ratio(candidates),
                "fusion_weights": weights
            },
            lineage={
                "from_value_ids": [c.value_id for c in candidates],
                "methods_used": [c.method for c in candidates]
            }
        )
    
    @staticmethod
    def _certainty_to_weight(certainty: str) -> float:
        """v7 Certainty를 가중치로 변환"""
        mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
        return mapping.get(certainty, 0.6)
```

**작업량 절감**: 80% (Fusion 로직 검증 완료, 스키마 변환만 필요)

**TODO 업데이트**:
- value-3: ~~Fusion Stage 구현~~ → **v7 로직 복사 + 스키마 변환**

---

## 4. 최우선 재사용: Evidence Collection (80%)

### 4.1 v7.x 코드

**파일**: `umis_rag/agents/estimator/evidence_collector.py` (394줄)

**핵심 설계**:
```python
class EvidenceCollector:
    """4가지 소스에서 증거 수집"""
    
    def collect(question, context) -> (EstimationResult, Evidence):
        """
        Stage 1: Evidence Collection
        
        Sources:
        1. Literal Source (프로젝트 데이터)
        2. RAG Source (학습된 규칙)
        3. Validator Source (외부 확정 데이터)
        4. Guardrail Analyzer (논리적 제약)
        
        Early Return:
        - 확정 값 발견 시 즉시 반환 (85% 케이스)
        """
        
        # Phase 0: Literal
        definite_value = self.literal_source.search(question)
        if definite_value:
            return create_definite_result(definite_value), evidence
        
        # Phase 1: Direct RAG
        rag_rules = self.rag_source.search(question, k=5)
        evidence.rag_rules = rag_rules
        
        # Phase 2: Validator Search (85% 성공!)
        validator_data = self.validator_source.search(question, context)
        if validator_data and validator_data.certainty == 'high':
            return create_definite_result(validator_data.value), evidence
        
        # Guardrail
        guardrails = self.guardrail_analyzer.analyze(question)
        evidence.hard_bounds = guardrails.hard_bounds
        
        return None, evidence  # 추정 필요
```

**핵심 아이디어**:
- **Early Return**: 확정 값이 있으면 추정 단계 스킵 (속도 10배)
- **4가지 소스 병렬 탐색**: Literal / RAG / Validator / Guardrail
- **85% Direct 성공률**: Validator Source가 강력

### 4.2 v9 적용 방안

**v9 Evidence Engine Stage 1에 직접 이식**:

```python
# v9: umis_v9_core/evidence_engine.py

class EvidenceEngine:
    
    def fetch_for_metrics(
        self,
        metric_requests: List[MetricRequest],
        policy_ref: str
    ) -> EvidenceBundle:
        """v7 EvidenceCollector 로직 재사용"""
        
        bundle = EvidenceBundle()
        
        for req in metric_requests:
            # v7의 4가지 소스 활용
            
            # 1. Literal Source (프로젝트 데이터)
            # → v9에서는 Project Context baseline_state로 대체
            if req.project_context_id:
                project_ctx = self.project_context_store.get(req.project_context_id)
                baseline_value = project_ctx.baseline_state.get(req.metric_id)
                if baseline_value:
                    bundle.add_definite(baseline_value)
                    continue  # Early Return
            
            # 2. Validator Source (외부 확정 데이터)
            # → v7 validator_source.py 로직 재사용
            validator_result = self.validator_source.search(req)
            if validator_result and validator_result.certainty == 'high':
                bundle.add_evidence(validator_result)
                continue  # Early Return
            
            # 3. Direct Evidence (DART/웹 검색)
            # → v7 dart_api.py 활용
            dart_evidence = self.dart_connector.fetch(req)
            if dart_evidence:
                bundle.add_evidence(dart_evidence)
            
            # 4. RAG Source (패턴/사례)
            # → v9에서는 Pattern Graph로 대체
            # (v7 RAG → v9 Pattern Benchmarks 매핑)
        
        return bundle
```

**작업량 절감**: 70% (Early Return 로직, Validator Source 재사용)

---

## 5. 중요 재사용: Fermi Estimator (70%)

### 5.1 v7.x 코드

**파일**: `umis_rag/agents/estimator/fermi_estimator.py`

**핵심 로직**:
```python
class FermiEstimator:
    """Fermi 분해 추정 (재귀 없음, max_depth=2)"""
    
    def estimate(question, context, budget) -> EstimationResult:
        """
        Stage 3: Fermi Decomposition
        
        특징:
        - 재귀 없음 (v7.11.0)
        - max_depth=2 고정
        - Budget 기반 (max_llm_calls)
        """
        
        # Step 1: 변수 식별 (LLM)
        variables = self._identify_variables(question)
        # 예: "SAM = N_customers × ARPU"
        #     variables = ["N_customers", "ARPU"]
        
        # Step 2: 각 변수를 Prior로 추정 (재귀 ❌, Stage 2 호출)
        var_values = {}
        for var in variables:
            # PriorEstimator 호출 (Stage 2)
            var_values[var] = self.prior_estimator.estimate(var, context)
        
        # Step 3: 공식 계산
        result_value = self._calculate_formula(variables, var_values)
        
        return EstimationResult(
            value=result_value,
            source="fermi",
            fermi_variables=var_values
        )
```

**v7.11.0 혁신**:
- ✅ 재귀 제거로 속도 3-10배 향상 (10-30초 → 3-5초)
- ✅ Budget 기반 제어 (max_llm_calls=10)
- ✅ 예측 가능한 실행 시간

### 5.2 v9 적용 방안

**v9 Value Engine Derived Stage에 통합**:

```python
# v9: umis_v9_core/value_engine.py

class MetricResolver:
    
    def _method_fermi(
        self,
        metric_id: str,
        context: dict
    ) -> ValueRecord:
        """v7 Fermi 로직 재사용"""
        
        # v7 FermiEstimator와 거의 동일
        spec = self.config.get_metric_spec(metric_id)
        fermi_hint = spec.resolution_protocol.get("fermi_decomposition")
        
        # 1. 변수 식별 (v7 프롬프트 재사용)
        variables = self._identify_variables_llm(metric_id, fermi_hint)
        
        # 2. 각 변수 추정 (재귀 ❌, Stage 2 Prior 호출)
        var_values = {}
        for var_id in variables:
            # v9 Metric Resolver를 Stage 2 (Prior)로 호출
            var_value = self._stage_3_prior(var_id, context)
            var_values[var_id] = var_value
        
        # 3. 공식 계산 (v7과 동일)
        result = self._calculate_formula(variables, var_values, fermi_hint)
        
        return ValueRecord(
            metric_id=metric_id,
            point_estimate=result,
            quality={
                "method": "fermi",
                "literal_ratio": 0.3  # 추정치
            },
            lineage={
                "fermi_variables": var_values
            }
        )
```

**작업량 절감**: 60% (Fermi 로직/프롬프트 재사용)

---

## 6. 중요 참고: Config Loader (80%)

### 6.1 v7.x 코드

**파일**: `umis_rag/core/config.py` (224줄)

**핵심 패턴**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Environment 기반 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    # API Keys
    openai_api_key: str
    dart_api_key: str
    
    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default_factory=lambda: project_root / "data")
    
    # Phase별 모델 설정
    llm_model_phase0_2: str = Field(default="gpt-4.1-nano")
    llm_model_phase3: str = Field(default="gpt-4o-mini")
```

### 6.2 v9 적용 방안

**동일한 패턴 활용**:

```python
# v9: umis_v9_core/config.py

from pydantic_settings import BaseSettings
import yaml

class UMISConfig(BaseSettings):
    """v7 패턴 + v9 YAML 로딩"""
    
    # .env 기반 설정 (v7과 동일)
    dart_api_key: str
    tavily_api_key: str
    
    # v9 추가: YAML 로딩
    yaml_config: dict = None
    
    def __init__(self, yaml_path: str = "umis_v9.yaml"):
        super().__init__()
        
        # v9 YAML 로드
        with open(yaml_path) as f:
            self.yaml_config = yaml.safe_load(f)
        
        # Metric 스펙 인덱싱 (v7과 유사)
        self.metrics = self._index_metrics()
        self.patterns = self._index_patterns()
        self.data_sources = self._index_data_sources()
    
    def _index_metrics(self) -> Dict[str, MetricSpec]:
        """umis_v9.yaml에서 Metric 스펙 인덱싱"""
        metrics = {}
        
        for m in self.yaml_config["umis_v9"]["planes"]["cognition_plane"]["engines"]["value_engine"]["metrics_spec"]["metrics"]:
            metric_id = m["metric_id"]
            metrics[metric_id] = MetricSpec(**m)
        
        return metrics
```

**작업량 절감**: 70% (pydantic 패턴, YAML 로딩 구조 재사용)

---

## 7. 재사용 매트릭스 및 작업 우선순위

### 7.1 즉시 복사 가능 (Week 1)

| v7 파일 | v9 파일 | 변경 사항 | 우선순위 |
|---------|---------|----------|---------|
| `dart_api.py` | `evidence/dart_connector.py` | Evidence 스키마 변환 | ⭐⭐⭐ |
| `fusion_layer.py` | `value_engine.py` (Fusion) | ValueRecord 변환 | ⭐⭐⭐ |
| `config.py` (패턴) | `config.py` | YAML 로딩 추가 | ⭐⭐⭐ |

**예상 작업 시간**: 2-3일 (7일 → 2-3일, **60% 절감**)

---

### 7.2 로직 재사용 (Week 2-3)

| v7 파일 | v9 대응 | 재사용 부분 | 작업량 |
|---------|---------|------------|--------|
| `evidence_collector.py` | `evidence_engine.py` | Early Return, 4-Source 패턴 | -50% |
| `fermi_estimator.py` | `value_engine.py` (Fermi) | 변수 식별, 재귀 없음 | -40% |
| `prior_estimator.py` | `value_engine.py` (Prior) | LLM 프롬프트 | -30% |

**예상 작업 시간**: 7-10일 (14일 → 7-10일, **40% 절감**)

---

### 7.3 참고용 (Week 4+)

| v7 파일 | v9 대응 | 활용 방법 |
|---------|---------|----------|
| `rag_searcher.py` | `pattern_engine.py` | 패턴 검색 로직 참고 |
| `validator_source.py` | `evidence_engine.py` | 데이터 소스 우선순위 |
| `excel/*` | `report_generator.py` | 템플릿 구조 참고 |

---

## 8. 마이그레이션 가이드

### 8.1 v7 → v9 용어 매핑

| v7 | v9 | 설명 |
|-----|-----|------|
| `Phase 0-2` | `Stage 1 (Direct Evidence)` | 증거 수집 |
| `Phase 3` | `Stage 2 (Derived)` + `Stage 3 (Prior)` | 추정 |
| `Phase 4` | `Stage 4 (Fusion)` | 융합 |
| `EstimationResult` | `ValueRecord` | 결과 객체 |
| `certainty (high/medium/low)` | `quality.literal_ratio (0~1)` | 품질 지표 |
| `Evidence.definite_value` | `Direct Evidence 성공` | 확정 값 |

### 8.2 직접 복사 가능한 함수

**DART API (100% 복사)**:
```python
# v7 → v9 그대로 복사
DARTClient.get_corp_code()  → DARTConnector.get_corp_code()
DARTClient.get_financials() → DARTConnector.get_financials()
```

**Fusion 로직 (90% 복사)**:
```python
# v7 → v9 스키마만 변경
FusionLayer._calculate_weights()       → MetricResolver._calculate_weights()
FusionLayer._intersect_ranges()        → MetricResolver._intersect_ranges()
FusionLayer._clip_to_hard_bounds()     → MetricResolver._clip_to_bounds()
```

**Config 패턴 (80% 복사)**:
```python
# v7 → v9 YAML 추가
Settings (pydantic) → UMISConfig (pydantic + YAML)
```

---

## 9. 작업 리스트 업데이트

### Before (원래 예상)

- evidence-1: DART API 연동 (3일)
- value-2: Derived Stage (5일)
- value-3: Fusion Stage (3일)
- **총 11일**

### After (v7 재사용)

- evidence-1: DART API 복사 + 스키마 변환 (**1일**)
- value-2: Derived Stage (Fermi 로직 재사용, **3일**)
- value-3: Fusion Stage 복사 + 변환 (**1일**)
- **총 5일** (절감: **55%**)

---

## 10. 즉시 실행 가능 액션

### Step 1: v7 코드 복사 (오늘)

```bash
# DART API 복사
cp v7_reference_code/umis_rag/utils/dart_api.py \
   umis_v9_core/evidence/dart_connector.py

# Fusion Layer 복사
cp v7_reference_code/umis_rag/agents/estimator/fusion_layer.py \
   umis_v9_core/value_engine_fusion.py
```

### Step 2: 스키마 변환 (1-2일)

```python
# dart_connector.py 수정
class DARTConnector:
    # v7 DARTClient 로직 그대로
    # + v9 Evidence 스키마로 변환만 추가
    
    def fetch_company_revenue(...) -> Evidence:  # v9 타입
        # v7 로직 호출
        financials = self.dart_client.get_financials(...)
        
        # v9 Evidence 변환
        return Evidence(
            evidence_id=f"EVD-DART-{corp_code}-{year}",
            source_tier="official",
            # v9 필드들...
        )
```

### Step 3: 테스트 (반나절)

```python
# tests/test_dart_connector.py
def test_dart_ybm():
    connector = DARTConnector()
    evidence = connector.fetch_company_revenue("YBM넷", 2023)
    
    assert evidence.evidence_id.startswith("EVD-DART-")
    assert evidence.metadata["revenue"] == 817억원 (±5%)
    assert evidence.source_tier == "official"
```

---

## 11. 권고사항

### 우선순위 1: 즉시 복사 (Week 1)

1. ✅ **dart_api.py → dart_connector.py**
   - 검증 완료된 API 호출 로직
   - 재시도/에러 처리 포함
   - **복사 후 스키마만 변환**

2. ✅ **fusion_layer.py → value_engine.py (Fusion)**
   - 가중 평균/범위 교집합 알고리즘
   - Certainty 기반 가중치
   - **복사 후 ValueRecord 변환**

3. ✅ **config.py 패턴**
   - pydantic BaseSettings
   - .env 기반 설정
   - **패턴만 참고**

### 우선순위 2: 로직 참고 (Week 2-3)

1. ⭐ **evidence_collector.py**
   - Early Return 전략
   - 4-Source 병렬 탐색
   - **85% Direct 성공 노하우**

2. ⭐ **fermi_estimator.py**
   - 재귀 없는 Fermi
   - LLM 프롬프트
   - **로직 이해 후 v9 스타일로 재작성**

### 우선순위 3: 구조 참고 (Week 4+)

1. **rag_searcher.py**: 패턴 검색 아이디어
2. **excel/***: 템플릿 구조 참고
3. **validator_source.py**: 데이터 소스 우선순위

---

## 12. 총 절감 효과

**원래 예상 (로드맵)**:
- 7주 (49일) 작업

**v7 재사용 후 예상**:
- Week 1: 5일 → **3일** (DART/Fusion 복사)
- Week 2-3: 10일 → **6일** (Evidence/Fermi 로직 재사용)
- Week 4-7: 34일 → **30일** (참고용)
- **총 39일** (절감: **20%**)

**핵심 효과**:
- ✅ DART API: 검증 완료 (11개 기업)
- ✅ Fusion 알고리즘: 프로덕션 검증
- ✅ Fermi 로직: 속도 최적화 완료
- ✅ Early Return: 85% Direct 성공률

---

**결론**: v7 코드는 **즉시 활용 가능한 프로덕션 품질**이며, v9 스키마 변환만 추가하면 됩니다.

**작성일**: 2025-12-05
**상태**: 분석 완료
