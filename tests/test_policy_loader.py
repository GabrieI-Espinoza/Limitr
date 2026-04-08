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
  enterprise:
    requests_per_minute: 120
    burst_capacity: 20
  free:
    requests_per_minute: 6
    burst_capacity: 3

clients:
  client_a: enterprise
  client_b: free
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
    assert policy.tier_name == "enterprise"
    assert policy.requests_per_minute == 120
    assert policy.burst_capacity == 20


@pytest.mark.asyncio
async def test_tier_resolution_returns_correct_quota(valid_policy_file):
    loader = PolicyLoader(valid_policy_file)
    await loader.load()

    policy = loader.get_policy_for_client("client_b")
    assert policy is not None
    assert policy.tier_name == "free"
    assert policy.requests_per_minute == 6
    assert policy.burst_capacity == 3


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
    policy_file.write_text("clients:\n  client_a: enterprise\n")

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
