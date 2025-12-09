"""YAML 문법 에러 자동 수정 스크립트"""

import re

def fix_yaml_inline_dict_spacing(filepath):
    """inline dictionary의 key: { 사이에 공백 추가"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 패턴: key:{ → key: {
    # 단, 이미 공백이 있으면 건너뛰기
    fixed = re.sub(r'(\w+):\s*{', r'\1: {', content)
    
    # list[...] 표현 제거
    # inline dict 내부: { type: "list[...]", ... } → { type: "list", ... }
    fixed = re.sub(r'type:\s*"list\[[^\]]+\]"', 'type: "list"', fixed)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(fixed)
    
    print(f"✅ {filepath} 수정 완료")


if __name__ == "__main__":
    fix_yaml_inline_dict_spacing("umis_v9.yaml")
    
    # 검증
    import yaml
    try:
        with open("umis_v9.yaml", "r") as f:
            data = yaml.safe_load(f)
        print("✅ YAML 파싱 성공!")
        print(f"   umis_v9 섹션: {'umis_v9' in data}")
    except yaml.YAMLError as e:
        print(f"❌ 여전히 에러: {e}")
