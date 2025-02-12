from pydantic import BaseModel, Field
from typing import Literal


class IntentResponse(BaseModel):
    """
    Defines the structure of the LLM's response for intent classification.
    """
    intent: Literal[
        "search",
        "filter",
        "action",
        "exploratory",
        "help"] = Field(
            ...,
            description="The classified intent of the query."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for intent classification (0.0 to 1.0)."
    )
    rationale: str = Field(
        ...,
        description="Brief explanation of why this intent was chosen."
    )
    alternatives_considered: list[dict[str, str]] = Field(
        ...,
        description="List of alternative intents considered."
    )
