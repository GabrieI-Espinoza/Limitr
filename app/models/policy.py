from pydantic import BaseModel, Field


# Defines the rules for a Tier
class TierConfiguration(BaseModel):
    requests_per_minute: int = Field(gt=0)
    burst_capacity: int = Field(gt=0)


# Represents the resolved policy for a specific client
class ResolvedPolicy(BaseModel):
    client_id: str
    tier_name: str
    requests_per_minute: int
    burst_capacity: int
