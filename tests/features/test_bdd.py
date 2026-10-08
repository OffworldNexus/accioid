"""BDD entry points for the Accioid feature files."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.bdd

scenarios("actions.feature")
