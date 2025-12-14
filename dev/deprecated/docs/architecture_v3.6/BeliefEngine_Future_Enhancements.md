# BeliefEngine Future Enhancements

**작성일**: 2025-12-12
**현재 버전**: v1.0 (Production Ready)
**계획**: v1.1, v1.2, v2.0

---

## v1.1: Human-in-the-loop (예상 1주)

### 목표

Belief 업데이트의 안전성 강화 - 사람이 검토/승인.

### 설계

#### API 추가

```yaml
belief_engine:
  api:
    - name: "propose_belief_update"
      description: "업데이트 제안만 (실제 반영 ❌)"
      input:
        metric_id: "metric_id"
        context: "dict"
        observations: "list"
      output:
        proposal_id: "string"
        proposed_belief: "belief_record"
        impact_assessment: "dict"
    
    - name: "approve_belief_update"
      description: "제안 승인 (실제 반영 ✅)"
      input:
        proposal_id: "string"
        approved_by: "role_id"
        notes: "string (optional)"
      output:
        belief_id: "string"
    
    - name: "reject_belief_update"
      description: "제안 거부"
      input:
        proposal_id: "string"
        rejected_by: "role_id"
        reason: "string"
      output:
        status: "rejected"
```

#### 구현

```python
class BeliefEngine:
    def __init__(self):
        # ...
        self.proposals: Dict[str, Dict] = {}  # proposal_id → proposal
    
    def propose_belief_update_api(
        self,
        metric_id: str,
        context: Dict,
        observations: List[Dict]
    ) -> Dict:
        """Belief 업데이트 제안"""
        
        # 1. 현재 Prior
        prior = self.prior_manager.get_prior(metric_id, context)
        
        # 2. 예상 Posterior 계산
        proposed_posterior = self.belief_updater.bayesian_update(
            prior.distribution,
            observations
        )
        
        # 3. Impact 평가
        delta = self._calculate_delta(prior.distribution, proposed_posterior)
        impact = self._assess_impact(metric_id, delta)
        
        # 4. Proposal 저장
        proposal_id = f"PROPOSAL-{uuid.uuid4().hex[:8]}"
        self.proposals[proposal_id] = {
            "proposal_id": proposal_id,
            "metric_id": metric_id,
            "context": context,
            "prior": prior.to_dict(),
            "proposed_posterior": proposed_posterior,
            "observations": observations,
            "delta": delta,
            "impact": impact,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        return self.proposals[proposal_id]
    
    def approve_belief_update_api(
        self,
        proposal_id: str,
        approved_by: str,
        notes: Optional[str] = None
    ) -> Dict:
        """Proposal 승인 및 실제 반영"""
        
        proposal = self.proposals.get(proposal_id)
        if not proposal or proposal["status"] != "pending":
            raise ValueError(f"Invalid proposal: {proposal_id}")
        
        # 실제 Belief 업데이트
        belief = self.prior_manager.save_belief(
            metric_id=proposal["metric_id"],
            context=proposal["context"],
            posterior=proposal["proposed_posterior"],
            observations=proposal["observations"],
            prior=BeliefRecord.from_dict(proposal["prior"])
        )
        
        # Proposal 상태 업데이트
        proposal["status"] = "approved"
        proposal["approved_by"] = approved_by
        proposal["approved_at"] = datetime.now().isoformat()
        proposal["notes"] = notes
        
        return {
            "belief_id": belief.belief_id,
            "proposal_id": proposal_id,
            "status": "approved"
        }
```

#### Impact Assessment

```python
def _assess_impact(
    self,
    metric_id: str,
    delta: Dict
) -> Dict:
    """Belief 변화의 영향 평가"""
    
    impact = {
        "magnitude": "low",  # low | medium | high
        "affected_metrics": [],  # 연관 Metric
        "risk_level": "low"
    }
    
    # Mean shift 크기
    mean_shift_pct = abs(delta.get("mean_shift_pct", 0))
    if mean_shift_pct > 0.5:
        impact["magnitude"] = "high"
    elif mean_shift_pct > 0.2:
        impact["magnitude"] = "medium"
    
    # 연관 Metric 찾기
    # (metrics_spec에서 formula 추적)
    impact["affected_metrics"] = self._find_dependent_metrics(metric_id)
    
    # Risk 평가
    if impact["magnitude"] == "high" and len(impact["affected_metrics"]) > 3:
        impact["risk_level"] = "high"
    
    return impact
```

#### UI 연동

```python
# CLI
python3 -m cmis_cli belief-propose --metric MET-SAM --context {...}
# → Proposal 생성

python3 -m cmis_cli belief-approve --proposal-id PROPOSAL-xxx --by analyst
# → 승인

# Web UI
# Proposal 리스트 → Review → Approve/Reject
```

---

## v1.2: 다변량 Belief (예상 2주)

### 목표

여러 Metric의 Joint Prior Distribution.

### 배경

**현재**: Metric별 독립 Prior

**문제**:
- TAM/SAM/SOM은 강한 종속성 (TAM > SAM > SOM)
- Revenue = N_customers × ARPU (완벽한 상관)
- Gross_margin + Net_margin (트레이드오프)

### 설계

#### Joint Prior

```python
@dataclass
class JointBeliefRecord:
    """여러 Metric의 Joint Belief"""
    
    joint_belief_id: str
    metric_ids: List[str]  # ["MET-TAM", "MET-SAM", "MET-SOM"]
    context: Dict
    
    # Joint Distribution
    distribution: Dict
    # {
    #   "type": "multivariate_normal",
    #   "params": {
    #     "mean": [100000, 50000, 20000],  # TAM, SAM, SOM
    #     "cov": [[...], [...], [...]]     # Covariance matrix
    #   }
    # }
    
    # 또는 Copula
    # {
    #   "type": "gaussian_copula",
    #   "marginals": {
    #     "MET-TAM": {"type": "lognormal", ...},
    #     "MET-SAM": {"type": "lognormal", ...}
    #   },
    #   "correlation": [[1.0, 0.8], [0.8, 1.0]]
    # }
    
    confidence: float
    source: str
    ...
```

#### API

```python
def query_joint_prior_api(
    self,
    metric_ids: List[str],
    context: Dict
) -> Dict:
    """여러 Metric의 Joint Prior 조회"""
    
    # 1. 개별 Prior 조회
    marginals = {}
    for metric_id in metric_ids:
        prior = self.query_prior_api(metric_id, context)
        marginals[metric_id] = prior["distribution"]
    
    # 2. Correlation 추정
    corr = self._estimate_correlation(metric_ids, context)
    
    # 3. Copula 구성
    joint_dist = {
        "type": "gaussian_copula",
        "marginals": marginals,
        "correlation": corr
    }
    
    return joint_dist

def _estimate_correlation(
    self,
    metric_ids: List[str],
    context: Dict
) -> np.ndarray:
    """Metric 간 Correlation 추정"""
    
    # Pattern Benchmark 또는 공식 기반
    # TAM → SAM: 0.95
    # SAM → SOM: 0.90
    # Revenue ↔ N_customers: 0.85
    
    pass
```

---

## v1.2: Active Learning (예상 1주)

### 목표

불확실성 높은 Metric 우선 수집 제안.

### 설계

#### API

```python
def suggest_evidence_priorities_api(self) -> List[Dict]:
    """불확실성 높은 Metric 우선 수집 제안
    
    Returns:
        [
            {
                "metric_id": "MET-SAM",
                "context": {...},
                "reason": "low_confidence_0.2",
                "urgency": "high",
                "expected_value_of_information": 0.8
            },
            ...
        ]
    """
    priorities = []
    
    for belief in self.prior_manager.all_beliefs():
        # 낮은 confidence
        if belief.confidence < 0.3:
            voi = self._calculate_voi(belief)
            priorities.append({
                "metric_id": belief.metric_id,
                "context": belief.context,
                "reason": f"low_confidence_{belief.confidence}",
                "urgency": "high" if voi > 0.7 else "medium",
                "expected_value_of_information": voi
            })
        
        # Uninformative source
        if belief.source == "uninformative":
            priorities.append({
                "metric_id": belief.metric_id,
                "context": belief.context,
                "reason": "uninformative_prior",
                "urgency": "high",
                "expected_value_of_information": 0.9
            })
    
    # 우선순위 정렬
    priorities.sort(key=lambda x: x["expected_value_of_information"], reverse=True)
    
    return priorities

def _calculate_voi(self, belief: BeliefRecord) -> float:
    """Value of Information 계산"""
    
    # 간단 버전: (1 - confidence) × importance
    # importance: 해당 Metric이 다른 Metric에 미치는 영향
    
    importance = self._get_metric_importance(belief.metric_id)
    voi = (1 - belief.confidence) * importance
    
    return voi
```

#### EvidenceEngine 연동

```python
# BeliefEngine → EvidenceEngine

priorities = belief_engine.suggest_evidence_priorities_api()

for priority in priorities[:5]:  # Top 5
    evidence_engine.fetch_for_metrics([
        MetricRequest(
            metric_id=priority["metric_id"],
            context=priority["context"]
        )
    ])
```

---

## v2.0: Causal Inference (예상 1개월)

### 목표

인과 추론 통합.

### 배경

**현재**: Correlation 기반
**문제**: "A와 B가 상관있다" ≠ "A가 B를 유발"

### 설계

#### Causal DAG

```python
causal_dag = {
    "nodes": ["MET-TAM", "MET-SAM", "MET-SOM", "MET-Revenue"],
    "edges": [
        ("MET-TAM", "MET-SAM"),  # TAM → SAM
        ("MET-SAM", "MET-SOM"),  # SAM → SOM
        ("MET-SOM", "MET-Revenue")  # SOM → Revenue
    ]
}
```

#### Do-calculus

```python
def do_intervention_api(
    self,
    metric_id: str,
    intervention_value: float,
    context: Dict
) -> Dict:
    """Do-intervention 시뮬레이션
    
    "MET-SAM을 50%로 증가시키면 Revenue는?"
    
    Args:
        metric_id: "MET-SAM"
        intervention_value: 1.5 (50% 증가)
        context: {...}
    
    Returns:
        affected_distributions: {
            "MET-SOM": {...},
            "MET-Revenue": {...}
        }
    """
    
    # 1. Causal DAG에서 downstream Metric 찾기
    downstream = self._find_downstream_metrics(metric_id)
    
    # 2. Do-calculus 적용
    # P(Revenue | do(SAM = 1.5*SAM))
    
    # 3. 결과 분포 반환
    
    pass
```

---

## 부록: 구현 우선순위

| 버전 | 기능 | 우선순위 | 예상 시간 | 비고 |
|------|------|---------|----------|------|
| v1.1 | Human-in-the-loop | ⭐⭐⭐ | 1주 | 안전성 |
| v1.2 | 다변량 Belief | ⭐⭐ | 2주 | 정확성 |
| v1.2 | Active Learning | ⭐⭐ | 1주 | 효율성 |
| v1.3 | Drift Alert 고도화 | ⭐ | 3일 | 모니터링 |
| v2.0 | Causal Inference | ⭐ | 1개월 | 연구 단계 |

---

**작성**: 2025-12-12
**현재**: v1.0 (Production Ready)
**다음**: v1.1 (Human-in-the-loop)

