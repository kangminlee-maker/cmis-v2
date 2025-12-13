# CMIS LLM Infrastructure 설계 개정

**작성일**: 2025-12-09
**이전 버전**: CMIS_LLM_Infrastructure_Design.md
**개정 사유**: 아키텍처 리뷰 피드백 반영

---

## 개정 요약

### 피드백 반영 우선순위

| 항목 | 임팩트 | 반영 | 비고 |
|------|--------|------|------|
| **(A) Task→모델 매핑** | 최상 | ✅ TaskRoute 도입 | 구조 변경 |
| **(B) default provider** | 상 | ✅ 명시적 등록 | 즉시 수정 |
| **(C) optimization 연결** | 상 | ✅ 훅 추가 | v2 구현 |
| **(H) Policy 연결** | 상 | ✅ 매트릭스 정의 | 문서화 |
| **(D) TaskType 검증** | 중 | ✅ 경고 추가 | 즉시 수정 |
| **(E) 구조화 응답** | 중 | ✅ 인터페이스 확장 | v2 |
| **(F) is_available** | 중 | ✅ 개선 | 즉시 수정 |
| **(G) memory_store** | 중 | ✅ trace 구조 | v2 |
| **(I) 기타** | 중하~하 | 📝 문서화 | v2+ |

---

## 1. TaskRoute 도입 (임팩트: 최상)

### 문제점

**현재 설계**:
```python
# Config
task_models:
  evidence_account_matching: "gpt-4o-mini"
  pattern_recognition: "gpt-4"

# 구현
provider_id = resolve_provider_id("gpt-4")  # → "openai"
register_task_mapping(task, provider_id)    # 모델명 손실!

# 실제 사용
provider = get_provider(task)  # OpenAILLM(default_model)
# → "gpt-4" 지정이 무시됨!
```

**결과**: Task별 모델 튜닝 불가능

### 해결: TaskRoute 도입

```python
@dataclass
class TaskRoute:
    """Task → (Provider, Model, Options) 매핑"""
    task_type: CMISTaskType
    provider_id: str
    model_name: str
    
    # LLM 옵션
    temperature: float = 0.2
    max_tokens: int = 1024
    mode: str = "chat"  # chat, completion, json
    
    # 메타
    cost_weight: float = 1.0  # 비용 가중치
    enable_cache: bool = True
```

**사용 흐름**:
```python
# 1. Config 로드
route = TaskRoute(
    task_type=CMISTaskType.EVIDENCE_ACCOUNT_MATCHING,
    provider_id="openai",
    model_name="gpt-4o-mini",
    temperature=0.1
)

# 2. Registry에 등록
registry.register_route(route)

# 3. 호출
provider = registry.get_provider(route.provider_id)
response = provider.call(
    prompt,
    model=route.model_name,        # ← 모델 명시!
    temperature=route.temperature  # ← 옵션 전달!
)
```

---

## 2. 개정된 아키텍처

### 2.1 전체 구조 (TaskRoute 중심)

```
┌───────────────────────────────────────────────────┐
│            LLMService (Facade)                    │
│  - call(task_type, prompt)                        │
│  - optimization hooks (cache, rate limit)         │
└───────────────────────────────────────────────────┘
                      ↓
┌───────────────────────────────────────────────────┐
│          TaskRouter (Task → Route)                │
│  - get_route(task_type) → TaskRoute               │
│  - fallback chain                                 │
└───────────────────────────────────────────────────┘
                      ↓
┌───────────────────────────────────────────────────┐
│        LLMRegistry (Provider 관리)                │
│  - get_provider(provider_id) → BaseLLM            │
│  - default provider                               │
└───────────────────────────────────────────────────┘
                      ↓
┌───────────────────────────────────────────────────┐
│         BaseLLM (확장된 인터페이스)                │
│  - call(prompt, model, **opts)                    │
│  - call_structured(prompt, schema)  ← 신규        │
│  - stream(prompt) → Iterator        ← 신규        │
└───────────────────────────────────────────────────┘
```

### 2.2 핵심 클래스 (개정)

**TaskRouter**:
```python
class TaskRouter:
    """Task → Route 매핑 관리"""
    
    def __init__(self, config: CMISConfig):
        self.routes: Dict[str, TaskRoute] = {}
        self._init_from_config(config)
    
    def register_route(self, route: TaskRoute):
        """Route 등록"""
        self.routes[route.task_type.value] = route
    
    def get_route(self, task_type: CMISTaskType) -> Optional[TaskRoute]:
        """Task → Route 조회
        
        Fallback chain:
        1. 정확한 매칭
        2. 기본 route
        3. None (오류)
        """
        route = self.routes.get(task_type.value)
        
        if route:
            return route
        
        # Fallback
        default_route = self.routes.get("__default__")
        
        if default_route:
            return default_route
        
        return None
    
    def _init_from_config(self, config):
        """Config에서 Route 로드"""
        llm_config = config.cmis.get("llm", {})
        routes_config = llm_config.get("routes", {})
        
        for task_str, route_config in routes_config.items():
            try:
                task_type = CMISTaskType(task_str)
                
                route = TaskRoute(
                    task_type=task_type,
                    provider_id=route_config.get("provider"),
                    model_name=route_config.get("model"),
                    temperature=route_config.get("temperature", 0.2),
                    max_tokens=route_config.get("max_tokens", 1024)
                )
                
                self.register_route(route)
                
            except ValueError as e:
                # TaskType 오타 → 경고
                logger.warning(
                    f"Unknown CMISTaskType in config: {task_str}"
                )
                continue
        
        # Default route 등록
        default_config = llm_config.get("default", {})
        if default_config:
            default_route = TaskRoute(
                task_type=None,  # Wildcard
                provider_id=default_config.get("provider", "openai"),
                model_name=default_config.get("model", "gpt-4o-mini")
            )
            self.routes["__default__"] = default_route
```

**LLMRegistry (개정)**:
```python
class LLMRegistry:
    """Provider 관리 (단순화)"""
    
    def __init__(self, config: CMISConfig):
        self.config = config
        self._providers: Dict[str, BaseLLM] = {}
        self._init_from_config()
    
    def register_provider(self, provider_id: str, provider: BaseLLM):
        """Provider 등록"""
        self._providers[provider_id] = provider
    
    def get_provider(self, provider_id: str) -> Optional[BaseLLM]:
        """Provider 조회"""
        return self._providers.get(provider_id)
    
    def _init_from_config(self):
        """Config에서 Provider 생성"""
        llm_config = self.config.cmis.get("llm", {})
        providers_config = llm_config.get("providers", {})
        
        for provider_id, provider_config in providers_config.items():
            if not provider_config.get("enabled", False):
                continue
            
            provider = self._create_provider(provider_id, provider_config)
            
            if provider:
                self.register_provider(provider_id, provider)
        
        # Default provider 명시적 등록
        default_mode = llm_config.get("default_mode", "native")
        
        if default_mode in self._providers:
            self._providers["__default__"] = self._providers[default_mode]
            logger.info(f"Default provider: {default_mode}")
        else:
            logger.warning(f"Default provider '{default_mode}' not found!")
```

**LLMService (개정)**:
```python
class LLMService:
    """LLM 중앙 관리 (개정)"""
    
    def __init__(self, config: CMISConfig):
        self.config = config
        self.registry = LLMRegistry(config)
        self.router = TaskRouter(config)  # ← 신규
        
        # Optimization hooks
        llm_opt = config.cmis.get("llm", {}).get("optimization", {})
        
        self.enable_caching = llm_opt.get("enable_caching", False)
        self.cache: Dict[str, str] = {}  # (cache_key, response)
        
        self.rate_limiter = RateLimiter(
            max_per_minute=llm_opt.get("rate_limit_per_minute", 60)
        ) if llm_opt.get("enable_routing") else None
        
        self.max_cost_per_day = llm_opt.get("max_cost_per_day", float('inf'))
        self.daily_cost = 0.0
        self.daily_reset_date = datetime.now().date()
        
        # 추적
        self.total_cost = 0.0
        self.call_count = 0
        self.traces: List[Dict] = []
    
    def call(
        self,
        task_type: CMISTaskType,
        prompt: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """LLM 호출 (개정)
        
        알고리즘:
        1. TaskRoute 조회
        2. Cache 확인
        3. Rate limit 체크
        4. 비용 체크
        5. Provider 호출
        6. Trace 기록
        """
        # 1. Route 조회
        route = self.router.get_route(task_type)
        
        if not route:
            raise ValueError(f"No route for {task_type}")
        
        # 2. Cache 확인
        if self.enable_caching:
            cache_key = self._build_cache_key(task_type, prompt, context)
            
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        # 3. Rate limit
        if self.rate_limiter:
            self.rate_limiter.check_or_wait()
        
        # 4. 비용 체크
        self._check_daily_cost()
        
        # 5. Provider 조회
        provider = self.registry.get_provider(route.provider_id)
        
        if not provider:
            raise ValueError(f"Provider not found: {route.provider_id}")
        
        # 6. 비용 추정
        cost = provider.get_cost_estimate(prompt)
        
        if self.daily_cost + cost > self.max_cost_per_day:
            raise CostLimitExceededError(
                f"Daily cost limit exceeded: {self.daily_cost:.2f} + {cost:.2f} > {self.max_cost_per_day}"
            )
        
        # 7. LLM 호출
        response = provider.call(
            prompt,
            context=context,
            model=route.model_name,      # ← 모델 명시!
            temperature=route.temperature,
            max_tokens=route.max_tokens,
            **kwargs
        )
        
        # 8. 비용 기록
        self.daily_cost += cost
        self.total_cost += cost
        self.call_count += 1
        
        # 9. Cache 저장
        if self.enable_caching and cache_key:
            self.cache[cache_key] = response
        
        # 10. Trace 기록
        trace = self._build_trace(task_type, route, prompt, cost)
        self.traces.append(trace)
        
        return response
    
    def _build_trace(
        self,
        task_type: CMISTaskType,
        route: TaskRoute,
        prompt: str,
        cost: float
    ) -> Dict:
        """Trace 생성 (memory_store 연동용)"""
        return {
            "task_type": task_type.value,
            "provider_id": route.provider_id,
            "model": route.model_name,
            "prompt_preview": prompt[:100],  # 보안: 전체 저장 안 함
            "cost_usd": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def _check_daily_cost(self):
        """일일 비용 리셋"""
        today = datetime.now().date()
        
        if today != self.daily_reset_date:
            self.daily_cost = 0.0
            self.daily_reset_date = today
    
    def _build_cache_key(
        self,
        task_type: CMISTaskType,
        prompt: str,
        context: Optional[Dict]
    ) -> str:
        """Cache 키 생성"""
        import hashlib
        
        context_str = json.dumps(context, sort_keys=True) if context else ""
        key_raw = f"{task_type.value}|{prompt}|{context_str}"
        
        return hashlib.sha256(key_raw.encode()).hexdigest()[:16]
```

---

## 3. BaseLLM 인터페이스 확장

### 구조화 응답 (신규)

```python
class BaseLLM(ABC):
    """LLM 추상 인터페이스 (확장)"""
    
    @abstractmethod
    def call(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        model: Optional[str] = None,  # ← 모델 override
        **kwargs
    ) -> str:
        """기본 LLM 호출"""
        pass
    
    def call_structured(
        self,
        prompt: str,
        schema: Optional[Dict] = None,
        context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """구조화된 응답 (JSON)
        
        기본 구현: call() + json.loads()
        Provider별 override: OpenAI JSON mode 등
        """
        response_text = self.call(prompt, context, **kwargs)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: 원문 반환
            return {"raw": response_text}
    
    def stream(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> Iterator[str]:
        """스트리밍 응답 (v2)
        
        기본 구현: 전체 응답을 한 번에
        Provider별 override: 실제 streaming
        """
        response = self.call(prompt, context, **kwargs)
        yield response
    
    @abstractmethod
    def is_available(self) -> bool:
        """사용 가능 여부"""
        pass
    
    def is_automated(self) -> bool:
        """자동화 가능 여부"""
        return True  # 기본: 자동화 가능
    
    def get_cost_estimate(self, prompt: str) -> float:
        """비용 추정 (USD)"""
        return 0.0
    
    def estimate_token_count(self, text: str) -> int:
        """토큰 수 추정 (v2)"""
        return len(text) // 4  # 대략
```

---

## 4. Config 스키마 (개정)

### cmis.yaml

```yaml
llm:
  # 기본 설정
  default_mode: "native"  # native | openai | anthropic
  
  # Default route (fallback)
  default:
    provider: "openai"
    model: "gpt-4o-mini"
    temperature: 0.2
  
  # Task별 Route (핵심!)
  routes:
    # Evidence Layer
    evidence_account_matching:
      provider: "openai"
      model: "gpt-4o-mini"
      temperature: 0.1
      max_tokens: 512
      enable_cache: true
    
    evidence_number_extraction:
      provider: "openai"
      model: "gpt-4o-mini"
      temperature: 0.0
    
    # Pattern Layer
    pattern_recognition:
      provider: "openai"
      model: "gpt-4"
      temperature: 0.0
      max_tokens: 2048
    
    pattern_gap_analysis:
      provider: "openai"
      model: "gpt-4"
      temperature: 0.3
    
    # Value Layer
    value_prior_estimation:
      provider: "openai"
      model: "gpt-4.1-nano"
      temperature: 0.2
    
    # Strategy Layer
    strategy_generation:
      provider: "anthropic"
      model: "claude-3.5-sonnet"
      temperature: 0.7
      max_tokens: 4096
    
    # Validation
    validation_sanity_check:
      provider: "openai"
      model: "gpt-4o-mini"
      temperature: 0.0
  
  # Provider 설정
  providers:
    native:
      enabled: true
      fallback_provider: "openai"
      fallback_model: "gpt-4o-mini"
    
    openai:
      enabled: true
      api_key_env: "OPENAI_API_KEY"
      default_model: "gpt-4o-mini"  # route에 없을 때만
    
    anthropic:
      enabled: true
      api_key_env: "ANTHROPIC_API_KEY"
      default_model: "claude-3.5-sonnet"
  
  # Optimization
  optimization:
    enable_routing: true
    enable_caching: true
    max_cost_per_day: 10.0  # USD
    rate_limit_per_minute: 60
```

---

## 5. Policy 연결 (임팩트: 상)

### TaskType × Policy 허용 매트릭스

```yaml
llm:
  policy_rules:
    # reporting_strict: allow_prior=false
    reporting_strict:
      allowed_tasks:
        - evidence_account_matching  # ✅ 허용
        - evidence_number_extraction # ✅ 허용
        - validation_sanity_check    # ✅ 허용
      
      blocked_tasks:
        - value_prior_estimation     # ❌ Prior 금지
        - pattern_gap_analysis       # ❌ 추론 금지
    
    # decision_balanced: allow_prior=true
    decision_balanced:
      allowed_tasks: "*"  # 전체 허용
    
    # exploration_friendly: allow_prior=true
    exploration_friendly:
      allowed_tasks: "*"  # 전체 허용
```

**사용**:
```python
# ValueEngine에서
if policy_ref == "reporting_strict":
    # prior_estimation 단계 스킵
    if not policy.allow_prior:
        # LLM Prior 사용 안 함
        pass
    else:
        # LLM Prior 사용
        llm_service.call(
            CMISTaskType.VALUE_PRIOR_ESTIMATION,
            prompt=...
        )
```

---

## 6. Optimization Hooks (임팩트: 상)

### RateLimiter

```python
class RateLimiter:
    """Rate limiting (Token Bucket)"""
    
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.tokens = max_per_minute
        self.last_refill = time.time()
    
    def check_or_wait(self):
        """Rate limit 체크 (대기 또는 오류)"""
        self._refill()
        
        if self.tokens <= 0:
            # 대기 또는 오류
            wait_time = 60 - (time.time() - self.last_refill)
            
            if wait_time > 0:
                time.sleep(wait_time)
                self._refill()
        
        self.tokens -= 1
    
    def _refill(self):
        """토큰 리필"""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed >= 60:
            self.tokens = self.max_per_minute
            self.last_refill = now
```

---

## 7. 기타 개선사항

### (D) TaskType 검증

```python
# Config 로드 시 경고
except ValueError:
    logger.warning(f"Unknown CMISTaskType: {task_str}")
    continue  # ← 경고만, 계속 진행
```

### (F) NativeLLM is_available

```python
def _check_native_env(self):
    """Native 환경 체크 (개선)"""
    import os
    
    # 명시적 환경 변수
    if os.getenv('CMIS_NATIVE_MODE') == 'true':
        return True
    
    # Cursor 체크
    if os.getenv('CURSOR_SESSION'):
        return True
    
    # 기타 IDE
    import sys
    if hasattr(sys, 'ps1'):
        return True
    
    return False
```

### (G) memory_store 연결

```python
# LLMService에 trace 저장 메서드
def save_traces_to_memory_store(self, memory_store):
    """Trace를 memory_store에 저장"""
    for trace in self.traces:
        memory_id = f"MEM-llm-{uuid.uuid4().hex[:8]}"
        
        memory_store.save({
            "memory_id": memory_id,
            "memory_type": "llm_trace",
            "content_ref": json.dumps(trace),
            "created_at": trace["timestamp"]
        })
    
    self.traces.clear()
```

---

## 8. 구현 우선순위

### v2 즉시 (1주)

**필수 (임팩트 최상~상)**:
- [x] TaskRoute 도입
- [x] Default provider 수정
- [x] TaskType 오타 경고
- [x] Policy 매트릭스 정의

**선택 (임팩트 상)**:
- [ ] Rate limiter 구현
- [ ] Cache 구현
- [ ] Daily cost guard

### v2.5 (1-2주)

**구조화 응답**:
- [ ] call_structured() 구현
- [ ] OpenAI JSON mode
- [ ] Schema validation

**Trace**:
- [ ] memory_store 연동
- [ ] Trace 분석 도구

### v3+ (장기)

- [ ] stream() 구현
- [ ] PromptTemplateRegistry
- [ ] Offline evaluation
- [ ] Multi-tenant

---

## 9. 최종 권장사항

### 즉시 반영 (v2)

**1. TaskRoute 도입** ✅ (핵심!)
- Task → (Provider, Model, Options)
- Config 정합성

**2. Default provider 수정** ✅
- 명시적 등록
- Fallback 보장

**3. Optimization hooks** ✅
- Rate limiter
- Cache
- Cost guard

**4. Policy 연결** ✅
- 허용 매트릭스
- 문서화

### 점진적 개선 (v2.5+)

- 구조화 응답
- Streaming
- PromptTemplate

---

**최종 상태**: 
- 구조 방향: ✅ 올바름
- 세부 개선: TaskRoute + Hooks
- 구현 우선순위: 명확

**다음**: v2 LLM 인프라 구현 (TaskRoute 중심)

---

**작성**: 2025-12-09
**개정**: 피드백 반영 완료
**상태**: 설계 확정, 구현 ready
