import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from test_quality_and_render import ContractTest


@pytest.fixture
def case():
    return ContractTest()
