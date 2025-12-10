# PatternEngine 설계 v1.1 - 피드백 반영 개선안

**작성일**: 2025-12-10  
**버전**: v1.1 (피드백 반영)  
**기반**: PatternEngine_Design_Blueprint.md v1.0

---

## 📋 개선 요약

이 문서는 v1.0 설계안에 대한 피드백을 반영한 **핵심 개선사항**을 정리합니다.

### 구조 평가

✅ **CMIS 상위 아키텍처와 정합성 양호**  
✅ **큰 틀은 유지, 세부 보강만 진행**

### 주요 개선 항목 (우선순위)

| 항목 | 문제 | 해결 | 상태 |
|------|------|------|------|
| A. PatternSpec 데이터 모델 | required_capabilities/assets 누락 | 필드 추가 | ✅ 완료 |
| B. combined_score 일관성 | 정의만 있고 구현 불일치 | 스키마 확정 | ✅ 완료 |
| C. Trait Score 계산 | 스키마와 로직 불일치 | 2단계 계산 | ✅ 완료 |
| D. Pattern Instance 모델 | 템플릿/인스턴스 구분 없음 | Instance 개념 추가 | ✅ 완료 |
| E. GapDiscovery 성능 | 중복 스캔 | precomputed 파라미터 | ✅ 완료 |
| F. P-Graph 관계 이중화 | 중복 표현 | 컴파일 프로세스 명시 | ✅ 완료 |
| G. Context Archetype | 마법 상자 | 3단계 로직 명시 | ✅ 완료 |
| H. 내부 컴포넌트 분할 | 2개 → 6개로 세분화 | Pipeline/Index/Scorer | ✅ 완료 |

---

## 🔧 A. PatternSpec 데이터 모델 보완

### 문제

- `calculate_execution_fit()`에서 `pattern.required_capabilities`, `pattern.required_assets` 사용
- 그러나 `PatternSpec`에 해당 필드 없음

### 해결

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class PatternSpec:
    """Pattern 정의 (완전판)"""
    pattern_id: str
    name: str
    family: str
    description: str
    
    # 기존 필드
    trait_constraints: Dict[str, Any]
    graph_structure: Dict[str, Any]
    quantitative_bounds: Optional[Dict[str, Any]] = None
    composes_with: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    specializes: Optional[str] = None
    benchmark_metrics: List[str] = field(default_factory=list)
    suited_for_contexts: List[str] = field(default_factory=list)
    
    # ===== [신규] Execution Fit 계산용 =====
    
    # Capability 요구사항
    required_capabilities: List[Dict[str, Any]] = field(default_factory=list)
    # 예시:
    # [
    #   {"technology_domain": "AI_ML", "maturity_level": "production_ready"},
    #   {"domain_expertise": "education", "scale_tier": "growth_stage"}
    # ]
    
    # Asset 요구사항
    required_assets: Dict[str, Any] = field(default_factory=dict)
    # 예시:
    # {
    #   "channels": {
    #     "online": True,
    #     "min_reach": 10000
    #   },
    #   "brand_awareness_level": ["medium", "high", "dominant"],
    #   "organizational_assets": {
    #     "min_team_size": 10,
    #     "org_maturity": ["scaleup", "established"]
    #   }
    # }
    
    # 제약 조건 체크
    constraint_checks: List[str] = field(default_factory=list)
    # 예시: ["min_financial_buffer_1M", "regulatory_compliance_GDPR"]
```

### YAML 예시

```yaml
pattern:
  pattern_id: "PAT-subscription_model"
  name: "구독형 비즈니스 모델"
  
  # ... 기존 필드 ...
  
  # Execution Fit 요구사항
  required_capabilities:
    - technology_domain: "platform_tech"
      maturity_level: "mvp"  # 최소 MVP 수준
    - domain_expertise: null  # 도메인 무관
  
  required_assets:
    channels:
      online: true
      min_reach: 1000  # 최소 1000명 도달 가능
    
    brand_awareness_level:
      - "low"
      - "medium"
      - "high"  # low 이상이면 OK
  
  constraint_checks:
    - "min_monthly_revenue_10K"  # 월 1만 이상 수익 필요
```

---

## 🔧 B. combined_score 일관성 확보

### 문제

- 문서에서 "Combined Score = structure_fit × execution_fit" 정의
- 그러나 `PatternMatch` 스키마, 정렬 로직, 예시가 불일치

### 해결

#### PatternMatch 스키마 확정

```python
@dataclass
class PatternMatch:
    """Pattern 매칭 결과"""
    pattern_id: str
    description: str
    
    # 점수 (필수)
    structure_fit_score: float  # 0.0 ~ 1.0
    execution_fit_score: Optional[float] = None  # 0.0 ~ 1.0 (Project Context 있을 때만)
    combined_score: float = 0.0  # structure × execution (or structure if no execution)
    
    # 증거
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # ===== [신규] Instance 정보 =====
    anchor_nodes: Dict[str, List[str]] = field(default_factory=dict)
    # {"actor": ["ACT-001"], "money_flow": ["MFL-101", "MFL-102"]}
    
    instance_scope: Optional[Dict[str, Any]] = None
    # {"domain": "education", "segment": "adult_language", "focal_actor": "ACT-001"}
```

#### Combined Score 계산 규칙

```python
def calculate_combined_score(
    structure_fit: float,
    execution_fit: Optional[float]
) -> float:
    """Combined Score 계산 (단일 규칙)
    
    규칙:
    - Project Context 없음 → combined = structure_fit
    - Project Context 있음 → combined = structure_fit × execution_fit
    
    이유:
    - Greenfield: 구조 적합도만으로 판단
    - Brownfield: 실행 가능성을 곱해서 현실성 반영
    """
    if execution_fit is None:
        return structure_fit
    else:
        return structure_fit * execution_fit
```

#### 정렬 규칙 통일

```python
# match_patterns() 반환 전 정렬
matches.sort(
    key=lambda m: m.combined_score,  # combined_score만 사용
    reverse=True
)
```

---

## 🔧 C. Trait Score 계산 로직 수정

### 문제

- `trait_constraints`는 `node_type → (required/optional traits)` 구조
- 그러나 계산 로직은 `len(matched_traits) / len(required_traits)` (단순 나눗셈)
- 의미가 맞지 않음

### 해결

#### 2단계 Trait Score 계산

```python
def calculate_trait_score(
    pattern: PatternSpec,
    trait_match: Dict[str, Any]
) -> float:
    """Trait Score 계산 (2단계)
    
    trait_match 구조:
    {
        "money_flow": {
            "required": {"matched": 2, "total": 2},
            "optional": {"matched": 1, "total": 3}
        },
        "actor": {
            "required": {"matched": 1, "total": 1},
            "optional": {"matched": 0, "total": 0}
        }
    }
    
    계산:
    1. required_traits 일치율 (핵심)
    2. optional_traits 일치 시 보너스 (+10%)
    """
    required_total = 0
    required_matched = 0
    optional_matched = 0
    optional_total = 0
    
    for node_type, stats in trait_match.items():
        required_total += stats["required"]["total"]
        required_matched += stats["required"]["matched"]
        optional_total += stats["optional"]["total"]
        optional_matched += stats["optional"]["matched"]
    
    # Required 점수 (0.0 ~ 1.0)
    if required_total == 0:
        required_score = 1.0  # 필수 trait 없으면 만점
    else:
        required_score = required_matched / required_total
    
    # Optional 보너스 (최대 +0.1)
    if optional_total > 0:
        optional_bonus = (optional_matched / optional_total) * 0.1
    else:
        optional_bonus = 0.0
    
    # 최종 점수 (최대 1.1 → 1.0으로 clamp)
    final_score = min(required_score + optional_bonus, 1.0)
    
    return final_score
```

#### check_trait_constraints 개선

```python
def check_trait_constraints(
    graph: RealityGraph,
    trait_constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """Trait 제약 체크 (상세 결과 반환)"""
    
    trait_match = {}
    matched_node_ids = []
    
    for node_type, constraints in trait_constraints.items():
        required_traits = constraints.get("required_traits", {})
        optional_traits = constraints.get("optional_traits", {})
        
        # node_type에 해당하는 노드 조회
        nodes = graph.nodes_by_type(node_type)
        
        req_matched = 0
        req_total = len(required_traits)
        opt_matched = 0
        opt_total = len(optional_traits)
        
        for node in nodes:
            node_traits = node.data.get("traits", {})
            
            # Required traits 체크
            req_match_count = sum(
                1 for k, v in required_traits.items()
                if node_traits.get(k) == v
            )
            
            if req_match_count == req_total:
                # 모든 required traits 만족
                req_matched += 1
                matched_node_ids.append(node.id)
                
                # Optional traits 체크
                opt_match_count = sum(
                    1 for k, v in optional_traits.items()
                    if node_traits.get(k) in (v if isinstance(v, list) else [v])
                )
                opt_matched += opt_match_count
        
        trait_match[node_type] = {
            "required": {
                "matched": min(req_matched, req_total),  # 최대 req_total
                "total": req_total
            },
            "optional": {
                "matched": opt_matched,
                "total": opt_total
            }
        }
    
    return {
        "trait_match": trait_match,
        "matched_node_ids": matched_node_ids
    }
```

---

## 🔧 D. Pattern Instance 모델 추가

### 문제

- 같은 Pattern이 여러 Actor/Segment에 적용될 수 있음
- 그러나 PatternMatch는 "시장 전체에 패턴이 있다/없다" 수준만 표현
- Instance 개념 없음

### 해결

#### PatternMatch에 Instance 정보 추가

```python
@dataclass
class PatternMatch:
    pattern_id: str
    structure_fit_score: float
    execution_fit_score: Optional[float]
    combined_score: float
    
    evidence: Dict[str, Any]
    
    # ===== [신규] Instance 관련 =====
    
    # Anchor Nodes: 이 패턴이 어떤 노드들에서 발견됐는지
    anchor_nodes: Dict[str, List[str]] = field(default_factory=dict)
    # {
    #   "actor": ["ACT-samsung-electronics"],
    #   "money_flow": ["MFL-subscription-001", "MFL-subscription-002"],
    #   "event": ["EVT-payment-001"]
    # }
    
    # Instance Scope: 이 패턴의 범위
    instance_scope: Optional[Dict[str, Any]] = None
    # {
    #   "focal_actor": "ACT-samsung-electronics",
    #   "domain": "b2b_saas",
    #   "region": "KR",
    #   "time_range": {"start": "2023", "end": "2024"}
    # }
```

#### P-Graph에 pattern_instance 노드 추가 (v2 로드맵)

```yaml
# v2에서 추가될 노드 타입
pattern_instance:
  fields:
    instance_id: string  # PINST-*
    pattern_id: pattern_id  # 어떤 Pattern의 인스턴스인지
    context: dict  # domain, region, actor, time_range
    scores:
      structure_fit: float
      execution_fit: float
      combined_score: float
    anchor_nodes: dict  # node_type → [node_ids]
    detected_at: datetime
    lineage: lineage_ref

# Edge: pattern_instance → R-Graph
pattern_applied_to:
  from: "pattern_instance"
  to: "actor"  # or "market_segment"
  properties:
    role: enum  # "focal" | "participant" | "competitor"
```

#### v1 vs v2 차이

**v1 (현재 설계)**:
- PatternMatch는 함수 반환값 (일회성)
- anchor_nodes, instance_scope는 메타데이터로만 존재

**v2 (향후 확장)**:
- P-Graph에 pattern_instance 노드 생성
- LearningEngine, StrategyEngine이 재사용 가능
- Outcome과 연결하여 Pattern 성능 학습

---

## 🔧 E. GapDiscovery 성능 개선

### 문제

- `discover_gaps()`가 내부에서 `match_patterns()` 재호출
- Workflow에서 이미 매칭했는데 또 스캔

### 해결

#### API 개선

```python
class PatternEngine:
    def match_patterns(
        self,
        graph: RealityGraph,
        project_context_id: Optional[str] = None,
        return_internal_state: bool = False  # 내부 상태 반환 여부
    ) -> Union[List[PatternMatch], Tuple[List[PatternMatch], Dict]]:
        """Pattern 매칭
        
        Args:
            return_internal_state: True면 (matches, internal_state) 튜플 반환
        """
        ...
        
        if return_internal_state:
            return matches, internal_state
        else:
            return matches
    
    def discover_gaps(
        self,
        graph: RealityGraph,
        project_context_id: Optional[str] = None,
        precomputed_matches: Optional[List[PatternMatch]] = None  # [신규]
    ) -> List[GapCandidate]:
        """Gap 탐지
        
        Args:
            precomputed_matches: 이미 계산된 매칭 결과 (성능 최적화)
        """
        # 재사용 가능하면 재사용
        if precomputed_matches is None:
            precomputed_matches = self.match_patterns(graph, project_context_id)
        
        # Gap 계산 (Context Archetype, Expected Patterns만 새로 조회)
        ...
```

#### Workflow 사용 예시

```python
# 기존 (비효율)
matches = pattern_engine.match_patterns(graph, prj_ctx)
gaps = pattern_engine.discover_gaps(graph, prj_ctx)  # 또 스캔!

# 개선 (효율)
matches = pattern_engine.match_patterns(graph, prj_ctx)
gaps = pattern_engine.discover_gaps(graph, prj_ctx, precomputed_matches=matches)
```

---

## 🔧 F. P-Graph 컴파일 프로세스 명시

### 문제

- Pattern 관계가 PatternSpec과 P-Graph 양쪽에 표현됨
- 이중화, 불일치 가능성

### 해결

#### 컴파일 프로세스 명확화

```python
class PatternLibrary:
    """Pattern 정의 → P-Graph 컴파일 담당"""
    
    def load_and_compile(self, yaml_paths: List[str]) -> None:
        """YAML → PatternSpec → P-Graph 컴파일
        
        프로세스:
        1. YAML 파싱 → PatternSpec
        2. Validation (trait 키, metric ID, pattern ID 참조 체크)
        3. P-Graph에 pattern 노드 생성
        4. P-Graph에 관계 edge 생성
        """
        for yaml_path in yaml_paths:
            pattern_spec = self._parse_yaml(yaml_path)
            
            # 1. Validation
            self._validate_pattern_spec(pattern_spec)
            
            # 2. P-Graph에 pattern 노드 추가
            self.p_graph.add_node(
                node_type="pattern",
                node_id=pattern_spec.pattern_id,
                data={
                    "name": pattern_spec.name,
                    "family": pattern_spec.family,
                    "description": pattern_spec.description,
                    # ... PatternSpec 전체 저장
                }
            )
            
            # 3. Pattern Family edge
            self.p_graph.add_edge(
                edge_type="pattern_belongs_to_family",
                source=pattern_spec.pattern_id,
                target=pattern_spec.family
            )
            
            # 4. Pattern 관계 edges
            for related_id in pattern_spec.composes_with:
                self.p_graph.add_edge(
                    edge_type="pattern_composes_with",
                    source=pattern_spec.pattern_id,
                    target=related_id,
                    data={"relationship": "composes_with"}
                )
            
            for conflicting_id in pattern_spec.conflicts_with:
                self.p_graph.add_edge(
                    edge_type="pattern_composes_with",
                    source=pattern_spec.pattern_id,
                    target=conflicting_id,
                    data={"relationship": "conflicts_with"}
                )
            
            if pattern_spec.specializes:
                self.p_graph.add_edge(
                    edge_type="pattern_composes_with",
                    source=pattern_spec.pattern_id,
                    target=pattern_spec.specializes,
                    data={"relationship": "specializes"}
                )
            
            # 5. Context Archetype edges
            for archetype_id in pattern_spec.suited_for_contexts:
                self.p_graph.add_edge(
                    edge_type="pattern_suited_for_context",
                    source=pattern_spec.pattern_id,
                    target=archetype_id
                )
```

#### 역할 분리

- **PatternSpec**: 사람 친화적 정의 (YAML)
- **P-Graph**: 런타임 그래프 (조회/탐색)
- **PatternLibrary**: 컴파일러 (YAML → Graph)

---

## 🔧 G. Context Archetype 결정 로직 명시

### 문제

- `determine_context_archetype(graph)` 한 줄로만 표현
- 실제로는 중요한 로직

### 해결

#### 3단계 Context Archetype 결정

```python
def determine_context_archetype(
    graph: RealityGraph,
    project_context_id: Optional[str] = None
) -> Optional[ContextArchetype]:
    """Context Archetype 결정 (3단계)
    
    우선순위:
    1. Project Context의 scope 사용 (있다면 거의 정답)
    2. RealityGraph의 Actor/Resource trait 기반 majority voting
    3. Fallback archetype (confidence 낮음)
    """
    
    # 1차: Project Context 기반 (가장 정확)
    if project_context_id:
        project_context = load_project_context(project_context_id)
        scope = project_context.scope
        
        # domain_id + region 기반 Archetype 조회
        archetype = ContextArchetypeLibrary.find_by_criteria(
            domain=scope.get("domain_id"),
            region=scope.get("region"),
            segment=scope.get("segment")
        )
        
        if archetype:
            archetype.confidence = 0.95  # 높은 신뢰도
            return archetype
    
    # 2차: RealityGraph Trait 기반 (Majority Voting)
    trait_votes = defaultdict(int)
    
    actors = graph.nodes_by_type("actor")
    resources = graph.nodes_by_type("resource")
    
    for actor in actors:
        traits = actor.data.get("traits", {})
        
        # Region trait
        if "region" in traits:
            trait_votes[("region", traits["region"])] += 1
        
        # Domain expertise
        if "domain_expertise" in traits:
            trait_votes[("domain", traits["domain_expertise"])] += 1
    
    for resource in resources:
        traits = resource.data.get("traits", {})
        
        # Delivery channel
        if "delivery_channel" in traits:
            trait_votes[("channel", traits["delivery_channel"])] += 1
        
        # Resource kind
        if "kind" in resource.data:
            trait_votes[("resource_kind", resource.data["kind"])] += 1
    
    # 가장 많이 나타난 trait 조합으로 Archetype 검색
    if trait_votes:
        top_traits = sorted(trait_votes.items(), key=lambda x: x[1], reverse=True)
        
        criteria = {}
        for (trait_type, value), _ in top_traits[:3]:  # 상위 3개
            criteria[trait_type] = value
        
        archetype = ContextArchetypeLibrary.find_by_criteria(**criteria)
        
        if archetype:
            archetype.confidence = 0.7  # 중간 신뢰도
            return archetype
    
    # 3차: Fallback (가장 일반적인 Archetype)
    fallback = ContextArchetypeLibrary.get_fallback()
    
    if fallback:
        fallback.confidence = 0.3  # 낮은 신뢰도
        return fallback
    
    return None


@dataclass
class ContextArchetype:
    """Context Archetype (신뢰도 추가)"""
    archetype_id: str
    name: str
    criteria: Dict[str, Any]
    expected_patterns: Dict[str, List[Dict]]
    
    confidence: float = 1.0  # 0.0 ~ 1.0 (결정 신뢰도)
```

---

## 🔧 H. 내부 컴포넌트 분할 (Pipeline/Index/Scorer)

### 문제

- PatternMatcher가 너무 많은 책임 (Filtering, Matching, Scoring)
- 성능 최적화/품질 튜닝 시 어디를 손대야 할지 불명확

### 해결

#### 6개 컴포넌트로 세분화

```python
# 1. PatternEngine (Facade)
class PatternEngine:
    """Public API"""
    def __init__(self):
        self.pipeline = PatternPipeline()
        self.lineage_tracker = LineageTracker()
    
    def match_patterns(...):
        return self.pipeline.run_matching(...)
    
    def discover_gaps(...):
        return self.pipeline.run_gap_discovery(...)


# 2. PatternPipeline (Orchestration)
class PatternPipeline:
    """전체 플로우 조율"""
    def __init__(self):
        self.index = PatternIndex()
        self.matcher = PatternMatcher()
        self.scorer = PatternScorer()
        self.gap_discoverer = GapDiscoverer()
    
    def run_matching(self, graph, project_context_id):
        # Filter → Match → Score → Persist
        candidates = self.index.filter_candidates(graph, project_context_id)
        matches = self.matcher.match(graph, candidates)
        scored_matches = self.scorer.score_all(matches, project_context_id)
        # (선택) P-Graph에 instance 저장
        return scored_matches


# 3. PatternIndex (Pre-filtering)
class PatternIndex:
    """Trait/Family/Context 기반 후보 패턴 필터링"""
    def __init__(self):
        self.trait_index = {}  # trait_key → [pattern_ids]
        self.family_index = {}  # family → [pattern_ids]
        self.archetype_index = {}  # archetype → [pattern_ids]
    
    def filter_candidates(
        self,
        graph: RealityGraph,
        project_context_id: Optional[str]
    ) -> List[PatternSpec]:
        """후보 패턴 필터링 (P개 → P'개)"""
        # Context Archetype 결정
        archetype = determine_context_archetype(graph, project_context_id)
        
        if archetype:
            # Archetype에 맞는 Pattern subset만
            candidates = self.archetype_index.get(archetype.archetype_id, [])
        else:
            # 전체 Pattern
            candidates = PatternLibrary.get_all()
        
        return candidates


# 4. PatternMatcher (Graph Matching)
class PatternMatcher:
    """실제 그래프 매칭 (Node/Edge 레벨)"""
    def match(
        self,
        graph: RealityGraph,
        pattern_candidates: List[PatternSpec]
    ) -> List[Dict]:
        """Pattern 후보에 대해 매칭 수행"""
        results = []
        
        for pattern in pattern_candidates:
            # Trait Check
            trait_result = check_trait_constraints(graph, pattern.trait_constraints)
            
            if not trait_result["trait_match"]:
                continue  # 빠른 제거
            
            # Graph Structure Check
            structure_result = check_graph_structure(graph, pattern.graph_structure)
            
            if not structure_result["satisfied"]:
                continue
            
            results.append({
                "pattern": pattern,
                "trait_result": trait_result,
                "structure_result": structure_result
            })
        
        return results


# 5. PatternScorer (Scoring)
class PatternScorer:
    """Structure/Execution/Combined 점수 계산"""
    def score_all(
        self,
        match_results: List[Dict],
        project_context_id: Optional[str]
    ) -> List[PatternMatch]:
        """매칭 결과에 점수 부여"""
        scored_matches = []
        
        project_context = None
        if project_context_id:
            project_context = load_project_context(project_context_id)
        
        for result in match_results:
            pattern = result["pattern"]
            
            # Structure Fit
            structure_fit = self.calculate_structure_fit(
                pattern,
                result["trait_result"],
                result["structure_result"]
            )
            
            # Execution Fit
            execution_fit = None
            if project_context:
                execution_fit = self.calculate_execution_fit(
                    pattern,
                    project_context
                )
            
            # Combined Score
            combined_score = calculate_combined_score(structure_fit, execution_fit)
            
            match = PatternMatch(
                pattern_id=pattern.pattern_id,
                description=pattern.description,
                structure_fit_score=structure_fit,
                execution_fit_score=execution_fit,
                combined_score=combined_score,
                evidence={
                    "trait_result": result["trait_result"],
                    "structure_result": result["structure_result"]
                },
                anchor_nodes=result["trait_result"]["matched_node_ids"]
            )
            
            scored_matches.append(match)
        
        # Sort by combined_score
        scored_matches.sort(key=lambda m: m.combined_score, reverse=True)
        
        return scored_matches


# 6. GapDiscoverer (Gap Detection)
class GapDiscoverer:
    """Expected vs Matched, Feasibility 평가"""
    # (기존과 유사, precomputed_matches 재사용)
```

---

## 📊 추가 고려사항

### 1. Lineage & Memory 연결

```python
@dataclass
class PatternMatch:
    # ... 기존 필드 ...
    
    lineage: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "from_evidence_ids": [...],
    #   "from_pattern_id": "PAT-xxx",
    #   "engine_ids": ["pattern_engine"],
    #   "policy_id": "reporting_strict",
    #   "created_at": "2024-12-10T...",
    #   "pattern_version": "v1.0"
    # }
```

### 2. PolicyEngine 연동

```python
def match_patterns(
    graph,
    project_context_id,
    policy_ref: Optional[str] = None  # [선택] PolicyEngine
):
    """
    policy_ref에 따라:
    - reporting_strict: confidence 낮은 Pattern 필터링
    - exploration_friendly: 모든 Gap 표시
    """
    ...
```

### 3. Pattern 검증 툴

```python
class PatternLibrary:
    def _validate_pattern_spec(self, pattern: PatternSpec) -> List[str]:
        """Pattern 정의 검증
        
        체크:
        - trait_constraints의 trait key가 Ontology에 존재하는지
        - quantitative_bounds의 metric_id가 metrics_spec에 존재하는지
        - composes_with/conflicts_with가 실제 pattern_id인지
        - required_capabilities가 올바른 trait key인지
        """
        errors = []
        
        # Trait key 검증
        for node_type, constraints in pattern.trait_constraints.items():
            for trait_key in constraints.get("required_traits", {}):
                if not OntologyValidator.is_valid_trait_key(trait_key):
                    errors.append(f"Invalid trait key: {trait_key}")
        
        # Metric ID 검증
        if pattern.quantitative_bounds:
            for metric_id in pattern.quantitative_bounds.keys():
                if not MetricsSpecValidator.exists(metric_id):
                    errors.append(f"Unknown metric_id: {metric_id}")
        
        # Pattern 관계 검증
        for related_id in pattern.composes_with + pattern.conflicts_with:
            if not self.exists(related_id):
                errors.append(f"Unknown pattern_id: {related_id}")
        
        return errors
```

---

## 🎯 구현 우선순위

### Phase 1 (즉시 적용)

1. ✅ PatternSpec 데이터 모델 보완 (A)
2. ✅ combined_score 일관성 (B)
3. ✅ Trait Score 로직 (C)
4. ✅ PatternMatch에 anchor_nodes 추가 (D 일부)

### Phase 2 (v1 구현 중)

5. ✅ GapDiscovery precomputed (E)
6. ✅ Context Archetype 로직 (G)
7. ✅ 내부 컴포넌트 분할 (H)

### Phase 3 (v1.5~v2)

8. ⏳ P-Graph에 pattern_instance 노드 추가 (D 완전)
9. ⏳ PatternLibrary Validator
10. ⏳ Lineage/Policy 연동

---

## 📝 v1.0 대비 변경 요약

| 항목 | v1.0 | v1.1 (개선) |
|------|------|------------|
| PatternSpec 필드 | 10개 | 13개 (+3: capabilities, assets, constraints) |
| PatternMatch 필드 | 5개 | 8개 (+3: combined, anchor, scope) |
| 내부 컴포넌트 | 2개 | 6개 (Pipeline, Index, Matcher, Scorer, Gap, Lineage) |
| Trait Score 계산 | 단순 나눗셈 | 2단계 (required + optional) |
| Context Archetype | 마법 상자 | 3단계 로직 명시 |
| GapDiscovery | 중복 스캔 | precomputed 재사용 |
| P-Graph 관계 | 이중화 | 컴파일 프로세스 명시 |
| Pattern Instance | 개념 없음 | anchor_nodes (v1), instance 노드 (v2) |

---

**작성**: 2025-12-10  
**상태**: 피드백 반영 완료  
**다음**: v1.0 문서 업데이트 또는 v1.1로 대체

