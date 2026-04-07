"""Unit tests for policy loading and validation from policies.yaml."""

import pytest
from app.limiter.policy_loader import PolicyLoader, PolicyConfigError


@pytest.fixture
def valid_policy_file(tmp_path):
    """Create a valid policies.yaml for testing."""
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
tiers:
  high_priority:
    requests_per_minute: 1000
    burst_capacity: 1000
  low_priority:
    requests_per_minute: 10
    burst_capacity: 10

clients:
  client_a: high_priority
  client_b: low_priority
"""
    )
    return str(policy_file)


@pytest.mark.asyncio
async def test_load_valid_policy(valid_policy_file):
    loader = PolicyLoader(valid_policy_file)
    await loader.load()

    policy = loader.get_policy_for_client("client_a")
    assert policy is not None
    assert policy.client_id == "client_a"
    assert policy.tier_name == "high_priority"
    assert policy.requests_per_minute == 1000
    assert policy.burst_capacity == 1000


@pytest.mark.asyncio
async def test_tier_resolution_returns_correct_quota(valid_policy_file):
    loader = PolicyLoader(valid_policy_file)
    await loader.load()

    policy = loader.get_policy_for_client("client_b")
    assert policy is not None
    assert policy.tier_name == "low_priority"
    assert policy.requests_per_minute == 10
    assert policy.burst_capacity == 10


@pytest.mark.asyncio
async def test_unknown_client_returns_none(valid_policy_file):
    loader = PolicyLoader(valid_policy_file)
    await loader.load()

    policy = loader.get_policy_for_client("unknown_client")
    assert policy is None


@pytest.mark.asyncio
async def test_missing_policy_file():
    loader = PolicyLoader("/nonexistent/policies.yaml")
    with pytest.raises(PolicyConfigError, match="Policy file not found"):
        await loader.load()


@pytest.mark.asyncio
async def test_invalid_yaml_syntax(tmp_path):
    policy_file = tmp_path / "bad.yaml"
    policy_file.write_text("tiers:\n  - :\n    invalid: [")

    loader = PolicyLoader(str(policy_file))
    with pytest.raises(PolicyConfigError, match="Invalid YAML"):
        await loader.load()


@pytest.mark.asyncio
async def test_missing_tiers_section(tmp_path):
    policy_file = tmp_path / "no_tiers.yaml"
    policy_file.write_text("clients:\n  client_a: high_priority\n")

    loader = PolicyLoader(str(policy_file))
    with pytest.raises(PolicyConfigError, match="`tiers` must be a non-empty mapping"):
        await loader.load()


@pytest.mark.asyncio
async def test_client_references_unknown_tier(tmp_path):
    policy_file = tmp_path / "bad_ref.yaml"
    policy_file.write_text(
        """
tiers:
  high:
    requests_per_minute: 100
    burst_capacity: 100

clients:
  client_a: nonexistent_tier
"""
    )

    loader = PolicyLoader(str(policy_file))
    with pytest.raises(PolicyConfigError, match="references unknown tier"):
        await loader.load()
