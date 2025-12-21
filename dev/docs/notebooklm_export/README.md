# NotebookLM용 CMIS 문서 패키지

**생성일**: 2025-12-21
**자동 생성**: `dev/tools/generate_notebooklm_docs.py`

---

## 📚 문서 구성

이 디렉토리는 NotebookLM이 CMIS 시스템을 학습할 수 있도록 자동 생성된 문서 패키지입니다.

### 문서 목록 (총 10개)

| 파일명 | 설명 | 라인 수 |
|--------|------|---------|
| `00_CMIS_System_Overview.md` | 시스템 전체 개요 및 철학 | 251 |
| `01_Core_Types_and_Schemas.md` | 타입 시스템 및 스키마 정의 | 326 |
| `02_Core_Engines_Implementation.md` | 9개 핵심 엔진 구현 상세 | 953 |
| `03_Evidence_System_Detail.md` | Evidence 수집/검증 시스템 | 382 |
| `04_Orchestration_Implementation.md` | Orchestration Kernel | 262 |
| `05_Search_Strategy_v3.md` | Search v3 구현 | 354 |
| `06_CLI_Commands_Reference.md` | CLI 명령어 레퍼런스 | 206 |
| `07_Configuration_Reference.md` | YAML 설정 파일 상세 | 503 |
| `08_Stores_and_Persistence.md` | 데이터 저장 및 관리 | 315 |
| `09_Integration_Guide.md` | 통합 가이드 및 사용 예제 | 168 |
| **총계** | | **3,720줄** |

---

## 🎯 NotebookLM 업로드 방법

### 1단계: NotebookLM 접속

https://notebooklm.google.com/ 에서 새 노트북 생성

### 2단계: 문서 업로드

다음 순서로 업로드하면 체계적으로 학습됩니다:

1. **기본 개념** (먼저 업로드)
   - `00_CMIS_System_Overview.md`
   - `01_Core_Types_and_Schemas.md`

2. **핵심 구현** (다음 업로드)
   - `02_Core_Engines_Implementation.md`
   - `03_Evidence_System_Detail.md`
   - `04_Orchestration_Implementation.md`
   - `05_Search_Strategy_v3.md`

3. **사용 및 설정** (마지막 업로드)
   - `06_CLI_Commands_Reference.md`
   - `07_Configuration_Reference.md`
   - `08_Stores_and_Persistence.md`
   - `09_Integration_Guide.md`

**참고**: NotebookLM은 최대 50개 소스를 지원하므로 모든 문서를 업로드할 수 있습니다.

### 3단계: 질문 예시

NotebookLM에 다음과 같은 질문을 해보세요:

- "CMIS의 핵심 철학은 무엇인가?"
- "BeliefEngine은 어떻게 작동하는가?"
- "Reality Graph의 구조는?"
- "Evidence 수집 프로세스를 설명해줘"
- "Orchestration Kernel의 Reconcile Loop는?"
- "CLI로 구조 분석을 실행하는 방법은?"

---

## 🔄 문서 재생성

코드베이스가 업데이트되면 다음 명령으로 문서를 재생성할 수 있습니다:

```bash
cd /Users/kangmin/v9_dev
python3 dev/tools/generate_notebooklm_docs.py
```

### 자동 생성 내용

스크립트는 다음을 자동으로 분석하고 문서화합니다:

- ✅ **Python 파일**: AST 파싱, docstring 추출, 타입 힌트 분석
- ✅ **YAML 파일**: 구조 파싱 및 설명
- ✅ **클래스/함수**: 시그니처, docstring, 주요 메서드
- ✅ **모듈 구조**: import, 의존성, 계층
- ✅ **설정 파일**: 전체 YAML 구조 및 값

---

## 📊 생성 통계

- **분석 대상**:
  - Python 파일: 121개 (cmis_core/)
  - CLI 명령어: 15개 (cmis_cli/commands/)
  - YAML 설정: 20+ 파일 (config/, schemas/)

- **생성 결과**:
  - 총 문서: 10개
  - 총 라인: 3,720줄
  - 크기: 96KB

---

## 🎨 문서 특징

### 1. 고품질 코드 스니펫

```python
# 실제 코드 예시가 포함됨
from cmis_core import WorldEngine

engine = WorldEngine()
reality_graph = engine.build_reality(...)
```

### 2. 상세한 타입 정보

모든 클래스와 함수의 타입 힌트가 포함되어 있습니다:

```python
def query_prior_api(
    self,
    metric_id: str,
    context: Dict[str, Any],
    policy_ref: Optional[str]
) -> Dict[str, Any]
```

### 3. YAML 구조 설명

설정 파일의 전체 구조가 포함되어 있습니다:

```yaml
policy_pack:
  schema_version: 2
  profiles:
    evidence_profiles: ...
```

---

## ⚙️ 커스터마이징

문서 생성 스크립트는 다음과 같이 커스터마이징할 수 있습니다:

1. **분석 깊이 조정**: `dev/tools/generate_notebooklm_docs.py`에서 `max_depth` 수정
2. **포함 파일 제어**: 각 `generate_*` 메서드 수정
3. **문서 템플릿 변경**: `_add_module_detail` 등의 헬퍼 메서드 수정

---

## 📝 업데이트 이력

### 2025-12-21 (v1.0)

- ✅ 초기 자동 생성 스크립트 구현
- ✅ 10개 문서 생성 (시스템 개요 → 통합 가이드)
- ✅ Python AST 기반 코드 분석
- ✅ YAML 파싱 및 구조화
- ✅ 3,720줄 고품질 문서 생성

---

## 🚀 다음 단계

1. NotebookLM에 문서 업로드
2. 시스템 이해도 테스트 (질문/답변)
3. 필요시 문서 추가/수정
4. 주기적 재생성 (코드 변경 시)

---

**생성 스크립트**: `dev/tools/generate_notebooklm_docs.py`
**문서 버전**: v1.0
**CMIS 버전**: v3.6.1

