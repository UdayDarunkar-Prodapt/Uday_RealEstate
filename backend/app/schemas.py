from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

class PropertyInput(BaseModel):
    query: str = Field(default="", max_length=1200)
    neighborhood: Optional[str] = None
    OverallQual: Optional[int] = Field(None, ge=1, le=10)
    OverallCond: Optional[int] = Field(None, ge=1, le=10)
    GrLivArea: Optional[float] = Field(None, ge=100, le=20000)
    TotalBsmtSF: Optional[float] = Field(None, ge=0, le=20000)
    GarageCars: Optional[float] = Field(None, ge=0, le=10)
    GarageArea: Optional[float] = Field(None, ge=0, le=5000)
    YearBuilt: Optional[int] = Field(None, ge=1800, le=2026)
    YearRemodAdd: Optional[int] = Field(None, ge=1800, le=2026)
    FullBath: Optional[float] = Field(None, ge=0, le=10)
    BedroomAbvGr: Optional[float] = Field(None, ge=0, le=20)
    TotRmsAbvGrd: Optional[float] = Field(None, ge=0, le=30)
    LotArea: Optional[float] = Field(None, ge=0, le=200000)
    GarageYrBlt: Optional[float] = Field(None, ge=1800, le=2026)

    @field_validator("query")
    @classmethod
    def reject_injection(cls, value: str):
        bad = ("ignore previous", "system prompt", "reveal instructions", "jailbreak")
        if any(item in value.lower() for item in bad):
            raise ValueError("Query contains unsafe instruction-like content.")
        return value.strip()

class FeedbackIn(BaseModel):
    query_id: Optional[int] = None
    rating: int = Field(ge=-1, le=1)
    comment: str = Field(default="", max_length=1000)

class WhatIfIn(BaseModel):
    property: PropertyInput
    changes: dict[str, float | int | str]
