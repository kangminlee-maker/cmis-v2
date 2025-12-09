"""pytest configuration and fixtures for CMIS tests"""

import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """프로젝트 루트 디렉토리"""
    # dev/scripts/tests/ → 프로젝트 루트 (3단계 위)
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def seed_path(project_root):
    """Adult Language seed 파일 경로"""
    return project_root / "seeds" / "Adult_Language_Education_KR_reality_seed.yaml"


@pytest.fixture
def config_path(project_root):
    """cmis.yaml 경로"""
    return project_root / "cmis.yaml"
