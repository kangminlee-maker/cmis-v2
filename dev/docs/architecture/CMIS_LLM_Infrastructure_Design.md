# CMIS LLM Infrastructure 설계

**작성일**: 2025-12-09
**목적**: 시스템 전체 LLM 사용을 중앙에서 관리

---

## 1. 설계 원칙

### 핵심 요구사항

**1. 다양한 LLM 인터페이스 지원**
```
- Cursor Agent (native, 무료)
- OpenAI API (gpt-4, gpt-4o-mini 등)
- Anthropic API (claude-3.5-sonnet 등)
- 기타 (Gemini, Llama 등)
```

**2. 단계별 다른 LLM 사용**
```
Evidence 해석: gpt-4o-mini (빠름, 저렴)
Pattern 추론: gpt-4 (정확)
Strategy 설계: claude-3.5-sonnet (창의적)
```

**3. 중앙 관리**
```
설정: cmis.yaml 또는 .env
코드: 추상화된 인터페이스만 사용
변경: 설정 파일만 수정
```

**4. 비용/성능 최적화**
```
Task별 최적 모델 선택
비용 추적
Rate limiting
```

---

## 2. v7 아키텍처 분석

### v7 구조

```
┌─────────────────────────────────────┐
│  LLMProvider (Interface)            │
│  ├─ CursorLLMProvider (Native)      │
│  └─ ExternalLLMProvider (API)       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  ModelRouter                        │
│  - Stage별 모델 선택                 │
│  - 비용 98% 절감                     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Factory (get_llm_provider)         │
│  - settings.llm_mode 기반            │
│  - 싱글톤 패턴                       │
└─────────────────────────────────────┘
```

### v7 TaskType (참고)

```python
class TaskType(Enum):
    # Evidence
    EVIDENCE_COLLECTION = "evidence_collection"
    
    # Prior
    PRIOR_ESTIMATION = "prior_estimation"
    CERTAINTY_EVALUATION = "certainty_evaluation"
    
    # Fermi
    FERMI_DECOMPOSITION = "fermi_decomposition"
    FERMI_VARIABLE_ESTIMATION = "fermi_variable_estimation"
    
    # Fusion
    FUSION_CALCULATION = "fusion_calculation"
    
    # Validation
    BOUNDARY_VALIDATION = "boundary_validation"
    GUARDRAIL_ANALYSIS = "guardrail_analysis"
```

---

## 3. v9 CMIS 설계

### 3.1 전체 아키텍처

```
┌───────────────────────────────────────────────────┐
│            LLMService (Facade)                    │
│  ┌─────────────────────────────────────────────┐ │
│  │  call(task_type, prompt, context)           │ │
│  │  - TaskType → Provider 라우팅              │ │
│  │  - 비용 추적                                 │ │
│  │  - Rate limiting                            │ │
│  └─────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
                      ↓
┌───────────────────────────────────────────────────┐
│         LLMRegistry (Provider 관리)               │
│  ┌─────────────────────────────────────────────┐ │
│  │  register(task_type, provider_id)          │ │
│  │  get_provider(task_type) → BaseLLM         │ │
│  └─────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
                      ↓
┌───────────────────────────────────────────────────┐
│          BaseLLM (Interface)                      │
│  ├─ CursorLLM (Cursor Agent)                     │
│  ├─ OpenAILLM (OpenAI API)                       │
│  ├─ AnthropicLLM (Claude API)                    │
│  └─ MockLLM (테스트용)                            │
└───────────────────────────────────────────────────┘
```

### 3.2 CMIS TaskType

```python
from enum import Enum

class CMISTaskType(Enum):
    """CMIS LLM 작업 유형
    
    v9 Graph-of-Graphs 아키텍처 기반
    """
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Evidence Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    EVIDENCE_ACCOUNT_MATCHING = "evidence_account_matching"
    # DART 계정과목 해석
    # 모델: gpt-4o-mini (빠름, 저렴)
    
    EVIDENCE_NUMBER_EXTRACTION = "evidence_number_extraction"
    # 웹 검색 결과 숫자 추출 (필요 시)
    # 모델: gpt-4o-mini
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Pattern Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    PATTERN_RECOGNITION = "pattern_recognition"
    # R-Graph에서 패턴 인식
    # 모델: gpt-4 (정확)
    
    PATTERN_GAP_ANALYSIS = "pattern_gap_analysis"
    # Gap 탐지 및 설명
    # 모델: gpt-4
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Value Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    VALUE_PRIOR_ESTIMATION = "value_prior_estimation"
    # Prior 추정 (Evidence 없을 때)
    # 모델: gpt-4.1-nano (저렴)
    
    VALUE_FORMULA_DERIVATION = "value_formula_derivation"
    # 공식 유도
    # 모델: gpt-4o-mini
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Strategy Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    STRATEGY_GENERATION = "strategy_generation"
    # 전략 후보 생성
    # 모델: claude-3.5-sonnet (창의적)
    
    STRATEGY_EVALUATION = "strategy_evaluation"
    # 전략 평가
    # 모델: gpt-4
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Validation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    VALIDATION_SANITY_CHECK = "validation_sanity_check"
    # 상식 검증
    # 모델: gpt-4o-mini
```

### 3.3 Config 기반 매핑

**cmis.yaml**:
```yaml
llm:
  # 기본 설정
  default_mode: "cursor"  # cursor | openai | anthropic
  
  # Task별 모델 매핑
  task_models:
    # Evidence
    evidence_account_matching: "gpt-4o-mini"
    evidence_number_extraction: "gpt-4o-mini"
    
    # Pattern
    pattern_recognition: "gpt-4"
    pattern_gap_analysis: "gpt-4"
    
    # Value
    value_prior_estimation: "gpt-4.1-nano"
    value_formula_derivation: "gpt-4o-mini"
    
    # Strategy
    strategy_generation: "claude-3.5-sonnet"
    strategy_evaluation: "gpt-4"
    
    # Validation
    validation_sanity_check: "gpt-4o-mini"
  
  # Provider 설정
  providers:
    cursor:
      enabled: true
      cost: 0  # 구독 포함
    
    openai:
      enabled: true
      api_key_env: "OPENAI_API_KEY"
      models:
        - "gpt-4"
        - "gpt-4o-mini"
        - "gpt-4.1-nano"
    
    anthropic:
      enabled: true
      api_key_env: "ANTHROPIC_API_KEY"
      models:
        - "claude-3.5-sonnet"
        - "claude-3-haiku"
  
  # 비용/성능 제어
  optimization:
    enable_routing: true  # Task별 모델 라우팅
    enable_caching: true  # LLM 응답 캐싱
    max_cost_per_day: 10.0  # USD
    rate_limit_per_minute: 60
```

---

## 4. 핵심 클래스 설계

### 4.1 BaseLLM (Interface)

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum

class BaseLLM(ABC):
    """LLM 추상 인터페이스
    
    모든 LLM 구현체가 준수해야 할 인터페이스
    """
    
    @abstractmethod
    def call(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """LLM 호출
        
        Args:
            prompt: 프롬프트
            context: 컨텍스트 (선택)
            **kwargs: 모델별 옵션
        
        Returns:
            LLM 응답 텍스트
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """사용 가능 여부"""
        pass
    
    def get_cost_estimate(self, prompt: str) -> float:
        """비용 추정 (USD)"""
        return 0.0  # 기본: 무료
```

### 4.2 NativeLLM (Native 환경)

```python
class NativeLLM(BaseLLM):
    """Native 환경 LLM
    
    개념:
    - Native = 현재 작업 중인 LLM 환경 (Cursor, IDE 등)
    - 별도 외부 API 호출 불필요
    - 현재 대화 컨텍스트 내에서 처리
    
    특징:
    - 추가 비용 없음 (구독에 포함)
    - 자동화 가능 (코드에서 직접 호출)
    - 빠름 (외부 API 호출 없음)
    
    구현 방식:
    - Cursor 환경: Cursor AI 사용 (구독 포함)
    - 기타 IDE: 설정된 기본 모델 사용
    - Fallback: Config에 설정된 모델 (예: gpt-4o-mini)
    """
    
    def __init__(self, fallback_provider: Optional[BaseLLM] = None):
        """
        Args:
            fallback_provider: Native 불가 시 사용할 Provider
                               (None이면 기본 OpenAI gpt-4o-mini)
        """
        self._is_native = self._check_native_env()
        
        # Fallback Provider 설정
        if not self._is_native:
            if fallback_provider:
                self._fallback = fallback_provider
            else:
                # 기본 Fallback: OpenAI gpt-4o-mini
                from cmis_core.llm.openai_llm import OpenAILLM
                self._fallback = OpenAILLM(model="gpt-4o-mini")
    
    def call(self, prompt, context=None, **kwargs):
        """LLM 호출
        
        Native 환경:
        - Cursor: Cursor AI가 직접 처리
        - 기타: 설정된 모델 사용
        
        Non-native:
        - Fallback 모델로 API 호출
        """
        if self._is_native:
            # Native 환경에서 실행
            # 실제로는 Cursor AI가 코드 실행 중에 처리
            # (Python 코드에서 "자신"을 호출하는 것은 불가능하므로
            #  실제 구현은 Cursor의 코드 실행 환경에 의존)
            
            # v1: Rule-based로 대체 (LLM 없이)
            # v2: Cursor API 사용 또는 Fallback
            return self._native_process(prompt, context)
        else:
            # Fallback: 외부 API
            return self._fallback.call(prompt, context, **kwargs)
    
    def _check_native_env(self):
        """Native 환경 체크
        
        체크:
        - Cursor 환경
        - IDE 환경
        - 대화형 세션
        """
        import sys
        import os
        
        # Cursor 체크
        if 'cursor' in sys.modules or os.getenv('CURSOR_SESSION'):
            return True
        
        # IDE 체크
        if hasattr(sys, 'ps1'):  # Interactive
            return True
        
        return False
    
    def _native_process(self, prompt, context):
        """Native 환경에서 처리
        
        v1: Rule-based fallback (LLM 실제 호출 없음)
        v2: Cursor API 또는 실제 구현
        """
        # v1: 간단한 응답 (실제 LLM 없이)
        return f"NATIVE_PROCESS: {prompt[:50]}..."
    
    def is_available(self):
        """항상 사용 가능 (Fallback 있음)"""
        return True
    
    def is_automated(self):
        """자동화 가능"""
        return True  # ← 중요: Native도 자동화 가능!
    
    def get_cost_estimate(self, prompt):
        """비용 추정"""
        if self._is_native:
            return 0.0  # Native는 무료 (구독 포함)
        else:
            return self._fallback.get_cost_estimate(prompt)
```

### 4.3 OpenAILLM (OpenAI API)

```python
class OpenAILLM(BaseLLM):
    """OpenAI API LLM"""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required")
        
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
    
    def call(self, prompt, context=None, **kwargs):
        """OpenAI API 호출"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            **kwargs
        )
        
        return response.choices[0].message.content
    
    def is_available(self):
        return bool(self.api_key)
    
    def is_automated(self):
        return True  # 완전 자동화
    
    def get_cost_estimate(self, prompt):
        """비용 추정"""
        # 모델별 가격 (대략)
        costs = {
            "gpt-4": 0.03,  # per 1K tokens
            "gpt-4o-mini": 0.0001,
            "gpt-4.1-nano": 0.00003,
        }
        
        tokens = len(prompt) / 4  # 대략 추정
        return (tokens / 1000) * costs.get(self.model, 0.001)
```

### 4.4 LLMRegistry (Provider 관리)

```python
class LLMRegistry:
    """LLM Provider 레지스트리
    
    역할:
    - Provider 등록/관리
    - TaskType별 Provider 매핑
    - Fallback 체인
    """
    
    def __init__(self, config: CMISConfig):
        self.config = config
        self._providers: Dict[str, BaseLLM] = {}
        self._task_mapping: Dict[str, str] = {}
        
        # Config에서 초기화
        self._init_from_config()
    
    def register_provider(
        self,
        provider_id: str,
        provider_instance: BaseLLM
    ):
        """Provider 등록"""
        self._providers[provider_id] = provider_instance
    
    def register_task_mapping(
        self,
        task_type: CMISTaskType,
        provider_id: str
    ):
        """Task → Provider 매핑"""
        self._task_mapping[task_type.value] = provider_id
    
    def get_provider(
        self,
        task_type: CMISTaskType
    ) -> BaseLLM:
        """Task에 맞는 Provider 반환
        
        Args:
            task_type: CMIS Task Type
        
        Returns:
            BaseLLM 구현체
        """
        # Task mapping 조회
        provider_id = self._task_mapping.get(
            task_type.value,
            "default"  # Fallback
        )
        
        provider = self._providers.get(provider_id)
        
        if provider and provider.is_available():
            return provider
        
        # Fallback: 기본 Provider
        return self._providers.get("default")
    
    def _init_from_config(self):
        """Config에서 초기화"""
        # cmis.yaml llm 설정 로드
        llm_config = self.config.cmis.get("llm", {})
        
        # Provider 등록
        for provider_id, provider_config in llm_config.get("providers", {}).items():
            if not provider_config.get("enabled", False):
                continue
            
            provider = self._create_provider(provider_id, provider_config)
            if provider:
                self.register_provider(provider_id, provider)
        
        # Task mapping 등록
        for task_str, model_name in llm_config.get("task_models", {}).items():
            # model_name → provider_id 변환
            provider_id = self._resolve_provider_id(model_name)
            
            try:
                task_type = CMISTaskType(task_str)
                self.register_task_mapping(task_type, provider_id)
            except ValueError:
                continue
    
    def _create_provider(self, provider_id, config):
        """Provider 생성"""
        if provider_id == "cursor":
            return CursorLLM()
        
        elif provider_id == "openai":
            api_key = os.getenv(config.get("api_key_env", "OPENAI_API_KEY"))
            # 기본 모델 (config에서 조정 가능)
            default_model = config.get("default_model", "gpt-4o-mini")
            return OpenAILLM(model=default_model, api_key=api_key)
        
        elif provider_id == "anthropic":
            api_key = os.getenv(config.get("api_key_env", "ANTHROPIC_API_KEY"))
            return AnthropicLLM(api_key=api_key)
        
        return None
    
    def _resolve_provider_id(self, model_name: str) -> str:
        """모델명 → Provider ID"""
        if "gpt" in model_name.lower():
            return "openai"
        elif "claude" in model_name.lower():
            return "anthropic"
        elif model_name == "cursor":
            return "cursor"
        else:
            return "default"
```

### 4.5 LLMService (Facade)

```python
class LLMService:
    """LLM 중앙 관리 서비스
    
    책임:
    - 단일 진입점 제공
    - TaskType 기반 라우팅
    - 비용 추적
    - Rate limiting
    """
    
    def __init__(self, config: CMISConfig):
        self.config = config
        self.registry = LLMRegistry(config)
        
        # 비용 추적
        self.total_cost = 0.0
        self.call_count = 0
    
    def call(
        self,
        task_type: CMISTaskType,
        prompt: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """LLM 호출 (중앙 진입점)
        
        Args:
            task_type: Task 유형
            prompt: 프롬프트
            context: 컨텍스트
        
        Returns:
            LLM 응답
        
        Example:
            >>> llm_service.call(
            ...     CMISTaskType.EVIDENCE_ACCOUNT_MATCHING,
            ...     prompt="이 중 매출액은?",
            ...     context={"company": "삼성전자"}
            ... )
            "영업수익"
        """
        # 1. Provider 선택
        provider = self.registry.get_provider(task_type)
        
        if not provider:
            raise ValueError(f"No provider for {task_type}")
        
        # 2. 비용 추정
        cost = provider.get_cost_estimate(prompt)
        
        # 3. LLM 호출
        response = provider.call(prompt, context, **kwargs)
        
        # 4. 비용 기록
        self.total_cost += cost
        self.call_count += 1
        
        return response
    
    def get_stats(self) -> Dict:
        """사용 통계"""
        return {
            "total_calls": self.call_count,
            "total_cost_usd": self.total_cost,
            "avg_cost_per_call": self.total_cost / self.call_count if self.call_count else 0
        }
```

---

## 5. 사용 방법

### 5.1 코드에서 사용 (추상화)

```python
# DART AccountMatcher 예시
class AccountMatcher:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
    
    def select_best_account(self, candidates, target):
        # LLM 호출 (TaskType만 지정)
        prompt = self._build_prompt(candidates, target)
        
        # TaskType만 지정 → Config가 모델 선택
        response = self.llm.call(
            CMISTaskType.EVIDENCE_ACCOUNT_MATCHING,
            prompt
        )
        
        # Native 환경 (Cursor):
        #   → NativeLLM이 직접 처리 (추가 비용 없음)
        # External 환경:
        #   → OpenAILLM이 gpt-4o-mini 호출 (Config 기반)
        
        # 코드는 동일! (환경에 무관)
        
        return self._parse_response(response)
```

### 5.2 Config 변경 (중앙)

```yaml
# 시나리오 1: 비용 최적화
task_models:
  evidence_account_matching: "gpt-4o-mini"  # 저렴
  pattern_recognition: "gpt-4"              # 정확

# 시나리오 2: 속도 최적화
task_models:
  evidence_account_matching: "gpt-4.1-nano"  # 빠름
  pattern_recognition: "gpt-4o-mini"         # 빠름

# 시나리오 3: Cursor only
default_mode: "cursor"
task_models:
  evidence_account_matching: "cursor"
  pattern_recognition: "cursor"
```

**코드 수정**: 0줄!

---

## 6. v9 구현 계획

### Phase 1: 기본 인프라 (v2, 1주)

- [ ] BaseLLM 인터페이스
- [ ] CursorLLM, OpenAILLM, MockLLM
- [ ] LLMRegistry
- [ ] LLMService
- [ ] CMISTaskType

### Phase 2: Config 통합 (v2, 2-3일)

- [ ] cmis.yaml에 llm 섹션
- [ ] Config 기반 초기화
- [ ] Task → Model 매핑

### Phase 3: 실제 적용 (v2, 1주)

- [ ] AccountMatcher (DART)
- [ ] PatternMatcher
- [ ] Prior Estimator
- [ ] 비용 추적

---

## 7. v1 vs v2 범위

### v1 (현재)

**LLM 사용 안 함**:
- DART: Rule + Fallback (가장 큰 금액)
- Google: 정규식
- Pattern: 하드코딩 패턴

**충분성**: 80-90%

### v2 (1-2주)

**LLM 인프라 구축**:
- LLMService 구현
- DART AccountMatcher (LLM)
- Pattern 추론 (LLM)

**커버리지**: 95%+

---

## 8. 설계 장점

### 1. 중앙 관리

```
Config만 변경 → 전체 시스템 모델 변경
코드 수정: 0줄
```

### 2. 비용 최적화

```
Task별 최적 모델:
- Evidence: gpt-4o-mini ($0.0001/1K)
- Strategy: claude-3.5-sonnet (창의적)

비용 추적 자동
```

### 3. 유연성

```
새 Provider 추가:
- BaseLLM 구현
- Registry에 등록
- Config에 추가

→ 기존 코드 수정 없음
```

### 4. 테스트 용이

```
MockLLM:
- 실제 API 호출 없이 테스트
- 비용 0
- 빠름
```

---

## 9. 즉시 조치 (v1 → v2 준비)

### 현재 DART 수정

```python
# v1: LLM 없이 (Rule + Fallback)
def _find_account_with_fallback(financials, target):
    # Rule + 가장 큰 금액
    # 80-90% 커버
    ...

# v2: LLM 통합 (선택적)
def _find_account_with_llm(financials, target, use_llm=False):
    if not use_llm:
        return _find_account_with_fallback(...)
    
    # LLM 사용
    response = llm_service.call(
        CMISTaskType.EVIDENCE_ACCOUNT_MATCHING,
        prompt=...
    )
    
    return parse_response(response)
```

---

## 10. 최종 권장사항

### v1 (현재)

**상태**: ✅ Production Ready (LLM 없이)
- Rule + Fallback
- 80-90% 커버
- 즉시 배포 가능

### v2 (1-2주)

**LLM 인프라 구축**:
1. BaseLLM, LLMRegistry, LLMService
2. Config 기반 매핑
3. DART AccountMatcher (LLM)
4. 95%+ 커버리지

### 우선순위

**즉시**:
1. v1 커밋/배포 (현재 상태)
2. LLM 설계 문서 완성 (이 문서)

**다음**:
1. LLM 인프라 구현
2. DART LLM 통합
3. Pattern LLM 통합

---

**결론**: 

1. ✅ v1은 LLM 없이 배포 (충분)
2. 📝 v2 LLM 설계 완성 (이 문서)
3. 🔨 v2 구현 시작 (1-2주 후)

---

**작성**: 2025-12-09
**상태**: LLM 인프라 설계 완료
**다음**: v1 커밋, v2 LLM 구현
