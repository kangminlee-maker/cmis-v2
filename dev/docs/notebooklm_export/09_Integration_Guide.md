# CMIS 통합 가이드

**생성일**: 2025-12-21 10:20:00
**목적**: CMIS 시스템 통합 및 사용 예제

---

## 1. 기본 사용 흐름

### 1.1 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp env.example .env
vi .env
```

### 1.2 Cursor Agent 온보딩

```bash
# 초기 환경 점검
python3 -m cmis_cli cursor bootstrap

# 시스템 진단
python3 -m cmis_cli cursor doctor

# 기능 목록 확인
python3 -m cmis_cli cursor manifest
```

---

## 2. 주요 워크플로우

### 2.1 구조 분석

```bash
python -m cmis_cli structure-analysis \
  --domain "Adult_Language_KR" \
  --actor "Ringle" \
  --output analysis_result.json
```

### 2.2 기회 발견

```bash
python -m cmis_cli opportunity-discovery \
  --context "context.yaml" \
  --output opportunities.json
```

---

## 3. 프로그래밍 인터페이스

### 3.1 기본 사용

```python
from cmis_core import (
    WorldEngine,
    EvidenceEngine,
    PatternEngine,
    ValueEngine,
)

# Evidence 수집
evidence_engine = EvidenceEngine()
evidence = evidence_engine.collect(
    query="Ringle revenue 2024",
    sources=["dart", "news"]
)

# Reality Graph 구성
world_engine = WorldEngine()
reality_graph = world_engine.build_reality(
    domain="Adult_Language_KR",
    evidence=evidence
)

# Pattern 매칭
pattern_engine = PatternEngine()
matched_patterns = pattern_engine.match(
    reality_graph=reality_graph
)

# Value 평가
value_engine = ValueEngine()
valuation = value_engine.evaluate(
    reality_graph=reality_graph,
    patterns=matched_patterns
)
```

---

## 4. 데이터 모델

### 4.1 Reality Graph

```python
from cmis_core.types import Node, Edge, RealityGraph

# Actor 노드
actor = Node(
    id="actor-ringle",
    type="actor",
    data={
        "name": "Ringle",
        "domain": "Adult_Language_KR"
    }
)

# MoneyFlow 노드
revenue_flow = Node(
    id="flow-subscription-revenue",
    type="money_flow",
    data={
        "amount": {"value": 5000000, "currency": "KRW"}
    }
)

# Edge
edge = Edge(
    type="actor_receives_money",
    source="actor-customer",
    target="actor-ringle",
    data={"flow_id": "flow-subscription-revenue"}
)
```

---

## 5. 확장 및 커스터마이징

### 5.1 커스텀 Evidence Source

```python
from cmis_core.evidence.base_search_source import BaseSearchSource

class CustomSource(BaseSearchSource):
    def search(self, query: str) -> List[SearchResult]:
        # 커스텀 검색 로직
        pass
```

### 5.2 커스텀 Pattern

```yaml
# libraries/patterns/custom_pattern.yaml
pattern_id: "PATTERN-Custom"
name: "Custom Business Pattern"
description: "커스텀 비즈니스 패턴"

structure:
  actors:
    - role: provider
      count: 1
  money_flows:
    - type: subscription
      direction: customer_to_provider
```

---

이 문서는 CMIS 시스템의 통합 가이드를 제공합니다.
