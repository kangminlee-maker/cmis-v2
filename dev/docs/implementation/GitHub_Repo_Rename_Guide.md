# GitHub 레포 이름 변경 가이드

**목표**: umis_v9 → cmis

**작성일**: 2025-12-09

---

## 1. GitHub에서 레포 이름 변경

### 웹사이트에서 변경
1. https://github.com/kangminlee-maker/cmis 접속
2. **Settings** 탭 클릭
3. 페이지 상단 **Repository name** 섹션
4. `umis_v9` → `cmis` 변경
5. **Rename** 버튼 클릭

---

## 2. 로컬 remote URL 업데이트

### 변경 후 자동 리다이렉트
- GitHub가 자동으로 `umis_v9` → `cmis` 리다이렉트 생성
- 기존 git push/pull 계속 작동 (당분간)

### 하지만 권장: remote URL 업데이트

```bash
# 현재 remote 확인
git remote -v

# 새 URL로 업데이트
git remote set-url origin https://github.com/kangminlee-maker/cmis.git

# 확인
git remote -v

# 테스트
git pull
git push
```

---

## 3. 문서 업데이트

### README.md
```markdown
# 변경 전
GitHub: [kangminlee-maker/cmis](https://github.com/kangminlee-maker/cmis)

# 변경 후
GitHub: [kangminlee-maker/cmis](https://github.com/kangminlee-maker/cmis)
```

### 변경 필요 파일
- README.md
- dev/docs/ 내 문서들 (GitHub 링크 포함된 경우)

---

## 4. 레포 이름 변경 영향

### ✅ 영향 없음
- 로컬 코드 (그대로)
- 파일 구조 (그대로)
- 테스트 (그대로)
- 브랜치/커밋 이력 (그대로)

### ⚠️ 업데이트 필요
- remote URL (권장)
- README 링크
- 다른 곳에서 clone한 경우

---

## 5. 체크리스트

변경 전:
- [ ] 커밋 완료 (unstaged 없음)
- [ ] 브랜치 확인 (main)

GitHub 변경:
- [ ] Settings → Rename
- [ ] 새 URL 확인: https://github.com/kangminlee-maker/cmis

로컬 업데이트:
```bash
cd /Users/kangmin/v9_dev
git remote set-url origin https://github.com/kangminlee-maker/cmis.git
git pull  # 테스트
git push  # 테스트
```

문서 업데이트:
- [ ] README.md GitHub 링크
- [ ] 기타 문서 GitHub 링크

최종 확인:
- [ ] pytest 통과
- [ ] git push 정상

---

**완료 후**: umis_v9 → cmis ✅


