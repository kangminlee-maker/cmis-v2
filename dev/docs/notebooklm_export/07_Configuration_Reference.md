# CMIS 설정 레퍼런스

**생성일**: 2025-12-21 10:20:00
**목적**: 모든 YAML 설정 파일 상세

---

### policies.yaml

**경로**: `config/policies.yaml`

```yaml
policy_pack:
  schema_version: 2
  pack_version: 2.1.0
  last_updated: 2025-12-13
  description: CMIS Policy Pack v2 (routing + profiles + gates)
  changelog:
    -
    -
  routing:
    by_usage:
    by_role:
    fallback: decision_balanced
  profiles:
    evidence_profiles:
    value_profiles:
    prior_profiles:
    convergence_profiles:
    orchestration_profiles:
  modes:
    reporting_strict:
    decision_balanced:
    exploration_friendly:
```

### search_strategy_registry_v3.yaml

**경로**: `config/search_strategy_registry_v3.yaml`

```yaml
registry_version: 3
phases_allowed:
  - authoritative
  - generic_web
providers:
  GenericWebSearch:
    adapter: google_cse
    api_key_ref: GOOGLE_API_KEY
    default_timeout_sec: 10
    rate_limit_qps: 1.0
    burst: 2
    cache_ttl_sec: 86400
    locale_mapping:
    notes:
metrics:
  MET-TAM:
    reporting_strict:
    decision_balanced:
    exploration_friendly:
```

### search_strategy_spec.yaml

**경로**: `config/search_strategy_spec.yaml`

```yaml
strategies:
  MET-TAM:
    per_source:
  MET-SAM:
    per_source:
  MET-Revenue:
    per_source:
  MET-GDP:
    per_source:
policy_defaults:
  reporting_strict:
    max_queries_per_metric: 3
    use_llm: False
    max_time: 10
    prefer_official: True
  decision_balanced:
    max_queries_per_metric: 5
    use_llm: True
    max_time: 20
    prefer_official: True
  exploration_friendly:
    max_queries_per_metric: 10
    use_llm: True
    max_time: 30
    prefer_official: False
language_strategy:
  KR:
    default_languages:
    primary: ko
  US:
    default_languages:
  JP:
    default_languages:
    primary: ja
  CN:
    default_languages:
    primary: zh
```

### validation_guidelines.yaml

**경로**: `config/validation_guidelines.yaml`

```yaml
cmis_validation:
  description: UMIS v9 YAML/도메인 설정 검증 가이드 (도구/체크리스트 요약)
  tools:
    yamllint:
    python_safe_load:
  checks:
    -
    -
    -
    -
```

### workflows.yaml

**경로**: `config/workflows.yaml`

```yaml
canonical_workflows:
  structure_analysis:
    id: structure_analysis
    role_id: structure_analyst
    description: 시장 구조/규모/경쟁 분석
    default_policy: reporting_strict
    steps:
    outputs:
  opportunity_discovery:
    id: opportunity_discovery
    role_id: opportunity_designer
    description: 패턴 기반 기회 발굴
    default_policy: exploration_friendly
    steps:
    outputs:
  strategy_design:
    id: strategy_design
    role_id: strategy_architect
    description: 전략 후보 탐색 및 평가
    default_policy: decision_balanced
    steps:
    outputs:
  reality_monitoring:
    id: reality_monitoring
    role_id: reality_monitor
    description: 실적 모니터링 및 학습
    default_policy: reporting_strict
    steps:
    outputs:
```

## archetypes/

### ARCH-b2b_saas.yaml

**경로**: `config/archetypes/ARCH-b2b_saas.yaml`

```yaml
archetype:
  archetype_id: ARCH-b2b_saas
  name: B2B SaaS 시장
  description: 기업 대상 SaaS (Software as a Service) 시장.
클라우드 기반, 구독형, 엔터프라이즈 소프트웨어.

  criteria:
    domain: b2b_saas
    delivery_channel: online
    resource_kind: software_license
  expected_patterns:
    core:
    common:
    rare:
```

### ARCH-digital_service_KR.yaml

**경로**: `config/archetypes/ARCH-digital_service_KR.yaml`

```yaml
archetype:
  archetype_id: ARCH-digital_service_KR
  name: 한국 디지털 서비스
  description: 한국 시장 디지털 서비스 업체의 전형적인 특징.
온라인 플랫폼, SaaS, 구독 서비스 등을 포함.
네트워크 효과와 구독 모델이 일반적.

  criteria:
    region: KR
    domain:
    delivery_channel: online
  expected_patterns:
    core:
    common:
    rare:
  typical_metrics:
    churn_rate:
    gross_margin:
    ltv_cac_ratio:
    revenue_growth_yoy:
```

### ARCH-education_platform_KR.yaml

**경로**: `config/archetypes/ARCH-education_platform_KR.yaml`

```yaml
archetype:
  archetype_id: ARCH-education_platform_KR
  name: 한국 교육 플랫폼
  description: 한국 교육 시장 온라인 플랫폼의 전형적인 특징.
성인 교육, K-12 교육, 직업 교육 등을 포함.
구독형 + 콘텐츠 판매 혼합 모델이 일반적.

  criteria:
    region: KR
    domain:
    delivery_channel: online
  expected_patterns:
    core:
    common:
    rare:
  typical_metrics:
    churn_rate:
    gross_margin:
    ltv_cac_ratio:
    revenue_growth_yoy:
    completion_rate:
```

### ARCH-marketplace_global.yaml

**경로**: `config/archetypes/ARCH-marketplace_global.yaml`

```yaml
archetype:
  archetype_id: ARCH-marketplace_global
  name: 글로벌 마켓플레이스
  description: 글로벌 시장의 양면/다면 마켓플레이스 플랫폼.
공급자-수요자 연결이 핵심 가치.
네트워크 효과와 거래 수수료 모델이 일반적.

  criteria:
    region:
    domain:
    delivery_channel: online
  expected_patterns:
    core:
    common:
    rare:
  typical_metrics:
    take_rate:
    gmv_growth_yoy:
    gross_margin:
    supplier_retention_rate:
    buyer_retention_rate:
    liquidity_score:
```

### ARCH-platform_global.yaml

**경로**: `config/archetypes/ARCH-platform_global.yaml`

```yaml
archetype:
  archetype_id: ARCH-platform_global
  name: 글로벌 플랫폼 시장
  description: 글로벌 디지털 플랫폼 시장.
양면/다면 시장, 네트워크 효과, 규모의 경제.

  criteria:
    institution_type: online_platform
    delivery_channel: online
  expected_patterns:
    core:
    common:
    rare:
```

### ARCH-simple_digital.yaml

**경로**: `config/archetypes/ARCH-simple_digital.yaml`

```yaml
archetype:
  archetype_id: ARCH-simple_digital
  name: 간단한 디지털 서비스
  description: 디지털 서비스 기본 Archetype (테스트/POC용).
Criteria가 단순하여 매칭하기 쉬움.

  criteria:
    resource_kind: digital_service
  expected_patterns:
    core:
    common:
    rare:
```

## sources/

### ecos_statistics.yaml

**경로**: `config/sources/ecos_statistics.yaml`

```yaml
statistics:
  -
    stat_type: gdp
    keyword: GDP(명목, 계절조정)
    name: GDP (명목, 계절조정)
    unit: 십억원
    keywords_match:
    keywords_exclude:
  -
    stat_type: gdp_growth
    keyword: 경제성장률(실질, 계절조정 전기대비)
    name: 경제성장률 (실질, 전기대비)
    unit: %
    keywords_match:
  -
    stat_type: gdp_real
    keyword: GDP(실질)
    name: GDP (실질)
    unit: 십억원
    keywords_match:
  -
    stat_type: cpi
    keyword: 소비자물가지수
    name: 소비자물가지수 (2020=100)
    unit: 지수
    keywords_match:
    keywords_exclude:
  -
    stat_type: base_rate
    keyword: 한국은행 기준금리
    name: 한국은행 기준금리
    unit: %
    keywords_match:
  # ... (1개 더)
```

### kosis_regions.yaml

**경로**: `config/sources/kosis_regions.yaml`

```yaml
regions:
  -
    name: KR
    code: 00
    name_kr: 전국
  -
    name: 전국
    code: 00
  -
    name: 서울
    code: 11
  -
    name: 부산
    code: 26
  -
    name: 대구
    code: 27
  # ... (14개 더)
```

### kosis_tables.yaml

**경로**: `config/sources/kosis_tables.yaml`

```yaml
tables:
  -
    stat_type: population
    orgId: 101
    tblId: DT_1B04006
    name: 주민등록인구 (시군구/성/연령)
    itmId: T2
    prdSe: Y
    description: 주민등록 기준 인구 수
    keywords:
  -
    stat_type: household
    orgId: 101
    tblId: DT_1B04005N
    name: 가구 및 세대 현황
    itmId: T2
    prdSe: Y
    description: 주민등록 기준 가구 수
    keywords:
```

### rate_limits.yaml

**경로**: `config/sources/rate_limits.yaml`

```yaml
limits:
  -
    source_id: ECOS
    calls: 100
    period: 60
    burst: 10
    note: 한국은행 ECOS - 100 calls/min
  -
    source_id: KOSIS
    calls: 1000
    period: 86400
    burst: 50
    note: 통계청 KOSIS - 1000 calls/day
  -
    source_id: DART
    calls: 10000
    period: 86400
    burst: 100
    note: 전자공시 DART - 10000 calls/day
  -
    source_id: GoogleSearch
    calls: 100
    period: 86400
    burst: 10
    note: Google Custom Search - 100 calls/day
  -
    source_id: DuckDuckGo
    calls: 1000
    period: 86400
    burst: 50
    note: DuckDuckGo - 1000 calls/day (추정)
```

### search_query_templates.yaml

**경로**: `config/sources/search_query_templates.yaml`

```yaml
templates:
  MET-TAM:
    template: {domain} {region} total addressable market size {year}
    keywords:
  MET-SAM:
    template: {domain} {region} serviceable available market {year}
    keywords:
  MET-Revenue:
    template: {domain} {region} market size revenue {year}
    keywords:
  MET-GDP:
    template: {region} GDP gross domestic product {year}
    keywords:
  MET-CPI:
    template: {region} consumer price index inflation {year}
    keywords:
default:
  template: {domain} {region} {metric} {year}
  keywords:
    - market size
```

### worldbank_indicators.yaml

**경로**: `config/sources/worldbank_indicators.yaml`

```yaml
indicators:
  -
    stat_type: gdp
    indicator_code: NY.GDP.MKTP.CD
    name: GDP (current US$)
    unit: current US$
    keywords:
    exclude_keywords:
  -
    stat_type: gdp_growth
    indicator_code: NY.GDP.MKTP.KD.ZG
    name: GDP growth (annual %)
    unit: %
    keywords:
  -
    stat_type: gdp_per_capita
    indicator_code: NY.GDP.PCAP.CD
    name: GDP per capita (current US$)
    unit: current US$
    keywords:
  -
    stat_type: population
    indicator_code: SP.POP.TOTL
    name: Population, total
    unit: people
    keywords:
  -
    stat_type: internet_users
    indicator_code: IT.NET.USER.ZS
    name: Internet users (% of population)
    unit: % of population
    keywords:
  # ... (3개 더)
```
