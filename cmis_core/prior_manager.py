"""Prior Manager

Prior/Belief Distribution 저장/조회/관리를 담당하는 모듈.

BeliefEngine의 핵심 컴포넌트로, Context별로 Prior를 캐싱하고
Pattern Benchmark에서 Prior를 생성하는 역할.

Phase 1: 메모리 dict 기반
Phase 2: value_store 영속성 추가
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import uuid
import json

from cmis_core.types import BeliefRecord


class PriorManager:
    """Prior Distribution 관리자
    
    Context별로 Prior/Belief를 저장하고 조회.
    Pattern Benchmark 기반 Prior 생성 지원.
    
    Phase 2: value_store 연동으로 영속성 확보.
    
    Usage:
        manager = PriorManager(value_store_path=Path("data/value_store"))
        
        # Prior 조회 (value_store → 캐시)
        prior = manager.get_prior("MET-SAM", {"domain_id": "...", "region": "KR"})
        
        # Belief 저장 (value_store + 캐시)
        belief = manager.save_belief(
            metric_id="MET-SAM",
            context={"domain_id": "...", "region": "KR"},
            posterior={"type": "normal", "params": {...}},
            observations=[{"value": 50000, "weight": 1.0}],
            prior=prior
        )
    """
    
    def __init__(self, value_store_path: Optional[Path] = None):
        """Initialize Prior Manager
        
        Args:
            value_store_path: value_store 경로 (Phase 2)
        """
        # Phase 2: value_store 경로
        if value_store_path:
            self.value_store_path = value_store_path
            self.value_store_path.mkdir(parents=True, exist_ok=True)
        else:
            # Phase 1 호환: 기본 경로
            self.value_store_path = Path(__file__).parent.parent / "data" / "value_store"
            self.value_store_path.mkdir(parents=True, exist_ok=True)
        
        # 메모리 캐시 (key: "metric_id:context_hash" → BeliefRecord dict)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1시간
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Pattern Benchmark 캐시 (key: pattern_id → benchmark dict)
        self.pattern_priors: Dict[str, Dict] = {}
    
    def get_prior(
        self,
        metric_id: str,
        context: Dict[str, Any]
    ) -> Optional[BeliefRecord]:
        """Context별 Prior 조회
        
        Phase 2: 캐시 → value_store 순서로 조회.
        
        Args:
            metric_id: "MET-SAM", "MET-TAM", etc.
            context: {"domain_id": "...", "region": "...", "segment": "..."}
        
        Returns:
            BeliefRecord 또는 None (Prior 없으면)
        """
        cache_key = self._make_cache_key(metric_id, context)
        
        # 1. 캐시 확인 (TTL 체크)
        if cache_key in self._cache:
            # TTL 확인
            timestamp = self._cache_timestamps.get(cache_key)
            if timestamp:
                age = (datetime.now(timezone.utc) - timestamp).total_seconds()
                if age < self._cache_ttl:
                    # 캐시 유효
                    return BeliefRecord.from_dict(self._cache[cache_key])
                else:
                    # 캐시 만료
                    del self._cache[cache_key]
                    del self._cache_timestamps[cache_key]
        
        # 2. value_store 조회
        belief = self._load_from_value_store(metric_id, context)
        
        # 3. 캐싱
        if belief:
            self._cache[cache_key] = belief.to_dict()
            self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
        
        return belief
    
    def _load_from_value_store(
        self,
        metric_id: str,
        context: Dict[str, Any]
    ) -> Optional[BeliefRecord]:
        """value_store에서 Belief 로드
        
        Args:
            metric_id: Metric ID
            context: Context dict
        
        Returns:
            BeliefRecord 또는 None
        """
        # 모든 JSON 파일 검색
        all_files = list(self.value_store_path.glob("*.json"))
        
        if not all_files:
            return None
        
        context_hash = self._hash_context(context)
        
        # 파일별로 확인
        matching_files = []
        for filepath in all_files:
            try:
                with open(filepath, "r") as f:
                    value_record = json.load(f)
                
                # metric_id와 context 일치 확인
                if (value_record.get("metric_id") == metric_id and
                    self._hash_context(value_record.get("context", {})) == context_hash):
                    matching_files.append(filepath)
            except Exception:
                continue
        
        if not matching_files:
            return None
        
        # 가장 최근 파일 로드
        latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(latest_file, "r") as f:
                value_record = json.load(f)
            
            # ValueRecord → BeliefRecord 변환
            return self._value_record_to_belief(value_record)
        
        except Exception:
            # 로드 실패 시 None
            return None
    
    def _value_record_to_belief(self, value_record: Dict) -> BeliefRecord:
        """ValueRecord → BeliefRecord 변환
        
        Args:
            value_record: value_store의 ValueRecord dict
        
        Returns:
            BeliefRecord
        """
        # VAL-BELIEF-xxxx → BELIEF-xxxx
        value_id = value_record["value_id"]
        if value_id.startswith("VAL-"):
            belief_id = value_id[4:]  # "VAL-" 제거
        else:
            belief_id = value_id
        
        return BeliefRecord(
            belief_id=belief_id,
            metric_id=value_record["metric_id"],
            context=value_record["context"],
            distribution=value_record["distribution"],
            confidence=value_record["quality"]["confidence"],
            source=value_record.get("origin", "learned"),
            observations=[],  # value_store에는 저장 안 함
            n_observations=0,  # 복원 불가
            created_at=value_record["lineage"].get("created_at", ""),
            updated_at=value_record.get("stored_at", ""),
            lineage=value_record["lineage"]
        )
    
    def _make_cache_key(self, metric_id: str, context: Dict) -> str:
        """캐시 키 생성"""
        context_hash = self._hash_context(context)
        return f"{metric_id}:{context_hash}"
    
    def save_belief(
        self,
        metric_id: str,
        context: Dict[str, Any],
        posterior: Dict,
        observations: List[Dict],
        prior: Optional[BeliefRecord] = None
    ) -> BeliefRecord:
        """Belief 생성/업데이트
        
        Phase 2: value_store에 ValueRecord 형식으로 저장.
        
        Args:
            metric_id: Metric ID
            context: Context dict
            posterior: 업데이트된 분포 dict
            observations: 관측 데이터 list
            prior: 이전 Prior/Belief (있으면)
        
        Returns:
            새로운 BeliefRecord
        """
        # Lineage 구성 (EVD-*/OUT-* 분리)
        evidence_ids = []
        outcome_ids = []
        
        for obs in observations:
            source = obs.get("source", "")
            if source.startswith("EVD-"):
                evidence_ids.append(source)
            elif source.startswith("OUT-"):
                outcome_ids.append(source)
        
        # BeliefRecord 생성
        prior_n_obs = prior.n_observations if prior else 0
        
        belief = BeliefRecord(
            belief_id=f"BELIEF-{uuid.uuid4().hex[:8]}",
            metric_id=metric_id,
            context=context,
            distribution=posterior,
            confidence=self._calculate_confidence(posterior, observations, prior_n_obs),
            source=prior.source if prior else "learned",
            observations=observations,
            n_observations=prior_n_obs + len(observations),
            created_at=prior.created_at if prior else datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "from_evidence_ids": evidence_ids,
                "from_outcome_ids": outcome_ids,
                "from_prior_id": prior.belief_id if prior else None,
                "engine_ids": ["belief_engine"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Phase 2: value_store에 저장
        self._save_to_value_store(belief)
        
        # 캐시 업데이트
        cache_key = self._make_cache_key(metric_id, context)
        self._cache[cache_key] = belief.to_dict()
        self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
        
        return belief
    
    def _save_to_value_store(self, belief: BeliefRecord) -> None:
        """value_store에 ValueRecord 형식으로 저장
        
        Args:
            belief: BeliefRecord
        """
        # BeliefRecord → ValueRecord 변환
        value_record = belief.to_value_record()
        
        # 파일명: VAL-{belief_id}.json
        filename = f"{value_record['value_id']}.json"
        filepath = self.value_store_path / filename
        
        # JSON 저장
        with open(filepath, "w") as f:
            json.dump(value_record, f, indent=2)
    
    def _calculate_spread(self, distribution: Dict) -> float:
        """분포의 spread_ratio 계산
        
        BeliefRecord._calculate_spread()와 동일 로직.
        
        Args:
            distribution: {"type": "normal", "params": {...}}
        
        Returns:
            spread_ratio (0~1+)
        """
        # BeliefRecord에 위임
        dummy_belief = BeliefRecord(
            belief_id="temp",
            metric_id="temp",
            context={},
            distribution=distribution,
            confidence=0.5,
            source="temp",
            observations=[],
            n_observations=0,
            created_at="",
            updated_at="",
            lineage={}
        )
        
        return dummy_belief._calculate_spread()
    
    def load_pattern_benchmark(
        self,
        pattern_id: str
    ) -> Optional[Dict]:
        """Pattern Benchmark 로드
        
        PatternEngine의 learned_benchmarks에서 로드.
        Phase 1: 스텁 (빈 dict 반환)
        Phase 2: 실제 구현
        
        Args:
            pattern_id: "PAT-subscription_model", etc.
        
        Returns:
            Benchmark dict 또는 None
            {
                "pattern_id": "PAT-subscription_model",
                "context": {"domain": "...", "region": "..."},
                "metrics": {
                    "MET-SAM": {"median": 50000, "p10": 30000, "p90": 80000},
                    ...
                }
            }
        """
        return self.pattern_priors.get(pattern_id)
    
    def _hash_context(self, context: Dict) -> str:
        """Context를 해시로 변환
        
        동일 Context = 동일 해시 보장 (캐싱용)
        
        Args:
            context: {"domain_id": "...", "region": "...", ...}
        
        Returns:
            MD5 해시 (8자)
        """
        # 키 정렬하여 일관성 보장
        sorted_items = sorted(context.items())
        context_str = str(sorted_items)
        return hashlib.md5(context_str.encode()).hexdigest()[:8]
    
    def _calculate_confidence(
        self,
        posterior: Dict,
        observations: List[Dict],
        prior_n_observations: int = 0
    ) -> float:
        """Posterior와 Observation 기반 신뢰도 계산
        
        더 많은 관측 (누적) = 더 높은 신뢰도
        더 좁은 분포 = 더 높은 신뢰도
        
        Args:
            posterior: 분포 dict
            observations: 현재 관측 리스트
            prior_n_observations: 이전 누적 관측 횟수
        
        Returns:
            confidence (0~1)
        """
        # 누적 관측 횟수
        n_obs = prior_n_observations + len(observations)
        
        if n_obs == 0:
            base_confidence = 0.1  # Uninformative
        elif n_obs == 1:
            base_confidence = 0.6
        elif n_obs == 2:
            base_confidence = 0.7
        elif n_obs <= 3:
            base_confidence = 0.75
        elif n_obs <= 5:
            base_confidence = 0.8
        else:
            base_confidence = 0.85
        
        # 분포 폭 기반 조정 (좁을수록 높음)
        dist_type = posterior.get("type", "normal")
        
        if dist_type == "normal":
            params = posterior.get("params", {})
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 0)
            if mu > 0:
                cv = sigma / mu  # Coefficient of Variation
                # cv가 작을수록 신뢰도 높음
                if cv < 0.1:
                    spread_factor = 1.1
                elif cv < 0.3:
                    spread_factor = 1.0
                elif cv < 0.5:
                    spread_factor = 0.9
                else:
                    spread_factor = 0.8
            else:
                spread_factor = 1.0
        else:
            spread_factor = 1.0
        
        # 최종 신뢰도 (최대 1.0)
        confidence = min(base_confidence * spread_factor, 1.0)
        
        return confidence
