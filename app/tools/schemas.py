from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeSearchArguments(BaseModel):
    query: str = Field(
        min_length=1,
        description="Enterprise troubleshooting or knowledge question.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of knowledge results to retrieve.",
    )


class SqlReadArguments(BaseModel):
    query: str = Field(
        min_length=1,
        description="Read-only SQL query against operational data.",
    )


class PythonAnalysisArguments(BaseModel):
    operation: Literal[
        "summary",
        "percentage_change",
    ] = Field(
        description="Approved numerical analysis operation.",
    )
    values: list[float] = Field(
        min_length=1,
        description="Numerical values to analyze.",
    )


class ServiceRestartArguments(BaseModel):
    service: str = Field(
        min_length=1,
        description="Name of the operational service to restart.",
    )