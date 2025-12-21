# Search Strategy v2 → v3 마이그레이션 체크리스트

**작성일**: 2025-12-21
**목적**: Search Strategy v2 관련 파일들을 정리하고 v3로 완전 전환

---

## 🔍 전수 조사 결과

### v2 관련 파일 (Deprecated 처리 필요)

| 파일/디렉토리 | 경로 | 상태 | 조치 |
|--------------|------|------|------|
| `search_strategy_spec.yaml` | `config/` | ❌ v2 표기, v2 구조 | → `dev/deprecated/config/` |
| `Search_Strategy_Design_v2.md` | `dev/docs/architecture/` | ❌ v2 문서 | → `dev/deprecated/docs/architecture_v3.6/` |
| `search_strategy_v2/` | `cmis_core/experimental/` | ❌ v2 구현 (3파일) | → `dev/deprecated/code/search_strategy_v2/` |
| `test_search_strategy_v2_executor.py` | `dev/tests/unit/` | ❌ v2 테스트 | → `dev/deprecated/tests/` |
| `SEARCH_STRATEGY_V2_COMPLETE.md` | `dev/session_summary/20251210/` | ℹ️  v2 완료 기록 | 유지 (히스토리) |

### v3 관련 파일 (현재 사용 중)

| 파일/디렉토리 | 경로 | 상태 | 조치 |
|--------------|------|------|------|
| `Search_Strategy_Design_v3.md` | `dev/docs/architecture/` | ✅ v3 문서 (최신) | Link Following 추가 완료 |
| `search_strategy_registry_v3.yaml` | `config/` | ✅ v3 레지스트리 | link_selection 설정 추가 권장 |
| `search_v3/` | `cmis_core/` | ✅ v3 구현 (14파일) | Link Following 구현 예정 |
| `test_search_strategy_v3_*.py` | `dev/tests/unit/` | ✅ v3 테스트 (3파일) | 정상 |
| `search_v3_source.py` | `cmis_core/evidence/` | ✅ Evidence 통합 | 정상 |

---

## ✅ 수행할 작업

### 1. Deprecated 파일 이동

```bash
# Config
mkdir -p dev/deprecated/config
mv config/search_strategy_spec.yaml dev/deprecated/config/

# Docs
mv dev/docs/architecture/Search_Strategy_Design_v2.md dev/deprecated/docs/architecture_v3.6/

# Code
mkdir -p dev/deprecated/code
mv cmis_core/experimental/search_strategy_v2 dev/deprecated/code/

# Tests
mkdir -p dev/deprecated/tests
mv dev/tests/unit/test_search_strategy_v2_executor.py dev/deprecated/tests/
```

### 2. search_strategy_registry_v3.yaml 보완

Link Following 설정 예시 추가 (주석):

```yaml
# Link Following (Section 7 확장, 구현 예정)
# link_selection:
#   max_links_per_doc: 3
#   min_relevance_score: 0.6
#   same_domain_only: true
#   priority_patterns:
#     - "*.pdf"
#     - "*/ir/*"
```

### 3. NotebookLM 문서 재생성

```bash
python3 dev/tools/generate_notebooklm_docs.py
```

### 4. 참조 제거

- `cmis_core/experimental/search_strategy_v2/` 관련 import 제거
- 문서에서 v2 참조 제거

---

## 📝 마이그레이션 노트

### v2 → v3 주요 변경사항

1. **구조 변경**:
   - v2: `per_source` 기반 (source 중심)
   - v3: `phases` 기반 (authoritative/generic_web)

2. **Registry 개선**:
   - v2: `search_strategy_spec.yaml` (단순 템플릿)
   - v3: `search_strategy_registry_v3.yaml` (versioned, digest pinning)

3. **확장 기능** (v3 only):
   - Phase-based execution
   - Budget/Policy enforcement
   - Trace/Event logging
   - Link Following (설계 완료, 구현 예정)

### 호환성

- v2 파일들은 더 이상 런타임에서 사용되지 않음
- v3 구현이 이미 작동 중
- 테스트는 v3 기반으로 전환 완료

---

**상태**: 조치 대기 중
**다음 단계**: 파일 이동 및 registry 보완

