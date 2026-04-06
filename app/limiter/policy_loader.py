import asyncio
from pathlib import Path
import yaml

from app.models.policy import TierConfiguration, ResolvedPolicy


class PolicyConfigError(Exception):
    """Custom exception for policy configuration errors."""


class PolicyLoader:
    def __init__(self, config_path: str) -> None:
        self.config_path = Path(config_path)
        # Maps Tier name to its configuration
        self._tiers: dict[str, TierConfiguration] = {}
        # Maps Client ID to Tier name
        self._clients: dict[str, str] = {}

    async def load(self) -> None:
        # Check if the config file exists
        if not self.config_path.exists():
            raise PolicyConfigError(f"Policy file not found: {self.config_path}")

        def _read_and_parse() -> dict:
            try:
                # Open and parse the YAML file into a dictionary
                with self.config_path.open("r", encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}  # Handle empty file case
            except yaml.YAMLError as exc:
                # Catch and handle YAML parsing errors
                raise PolicyConfigError(f"Invalid YAML in policy file: {exc}") from exc

        raw_config = await asyncio.to_thread(_read_and_parse)

        # Extract tiers and clients from the raw config
        tiers = raw_config.get("tiers")
        clients = raw_config.get("clients")

        # Validate that tiers is not empty and is a dictionary
        if not isinstance(tiers, dict) or not tiers:
            raise PolicyConfigError("`tiers` must be a non-empty mapping")

        # Validate that clients is not empty and is a dictionary
        if not isinstance(clients, dict) or not clients:
            raise PolicyConfigError("`clients` must be a non-empty mapping")

        parsed_tiers: dict[str, TierConfiguration] = {}

        # Iterate over each tier and config pair and validate
        for tier_name, tier_data in tiers.items():
            try:
                # Unpack dictonary values into the TierConfiguration for validation
                parsed_tiers[tier_name] = TierConfiguration(**tier_data)
            except Exception as exc:
                # Catch validation errors
                raise PolicyConfigError(
                    f"Invalid configuration for tier `{tier_name}`: {exc}"
                ) from exc

        # Iterate over each client and assgned tier pair and validate
        for client_id, tier_name in clients.items():
            # Validate that the assigned tier exists in the parsed tiers
            if tier_name not in parsed_tiers:
                # Catch and handle the case where a client references a non-existent tier
                raise PolicyConfigError(
                    f"Client `{client_id}` references unknown tier `{tier_name}`"
                )

        # After successful validation, assign the parsed tiers and clients to the instance variables
        self._tiers = parsed_tiers
        self._clients = clients

    def get_policy_for_client(self, client_id: str) -> ResolvedPolicy | None:
        """Returns the resolved policy for a given client ID, with correct Tier configuration."""
        # Extract the tier name for the given client ID
        tier_name = self._clients.get(client_id)

        # If no client ID is found, tier_name will be None
        if tier_name is None:
            return None

        # Extract the Tier configuration for the given tier name
        tier = self._tiers[tier_name]

        # Build and return the ResolvedPolicy object
        return ResolvedPolicy(
            client_id=client_id,
            tier_name=tier_name,
            requests_per_minute=tier.requests_per_minute,
            burst_capacity=tier.burst_capacity,
        )
