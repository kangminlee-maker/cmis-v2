"""pytest configuration and fixtures for CMIS tests"""

import pytest
import sys
from pathlib import Path


@pytest.fixture
def project_root():
    """프로젝트 루트 디렉토리"""
    # dev/tests/ → 프로젝트 루트 (2단계 위)
    return Path(__file__).parent.parent.parent


# Ensure repo root is importable even when running `pytest` as a script.
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def seed_path(project_root):
    """Adult Language seed 파일 경로"""
    # 새 위치
    new_path = project_root / "dev" / "examples" / "seeds" / "Adult_Language_Education_KR_reality_seed.yaml"
    if new_path.exists():
        return new_path
    # Fallback
    return project_root / "seeds" / "Adult_Language_Education_KR_reality_seed.yaml"


@pytest.fixture
def config_path(project_root):
    """cmis.yaml 경로"""
    return project_root / "cmis.yaml"
