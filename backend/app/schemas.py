from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re

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
        text=value.strip()
        bad = (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",r"(system|developer)\s+prompt",r"reveal\s+(the\s+)?(instructions|prompt)",r"jailbreak",r"act\s+as\s+(an?\s+)?(assistant|system)",r"disregard\s+(all\s+)?rules")
        if any(re.search(item,text,re.I) for item in bad):
            raise ValueError("Query contains unsafe instruction-like content.")
        if any(ord(char)<32 and char not in "\n\t\r" for char in text):
            raise ValueError("Query contains unsupported control characters.")
        return text

    @field_validator("neighborhood")
    @classmethod
    def validate_neighborhood(cls,value):
        if value is None:return value
        value=value.strip()
        if not value or len(value)>60 or not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _'-]*",value):
            raise ValueError("Neighborhood must be a short place name.")
        return value

class FeedbackIn(BaseModel):
    query_id: Optional[int] = None
    rating: int = Field(ge=-1, le=1)
    comment: str = Field(default="", max_length=1000)

class WhatIfIn(BaseModel):
    property: PropertyInput
    changes: dict[str, float | int | str]

    @model_validator(mode="after")
    def validate_changes(self):
        allowed=set(PropertyInput.model_fields)-{'query'}
        unknown=set(self.changes)-allowed
        if unknown: raise ValueError(f"Unsupported scenario fields: {', '.join(sorted(unknown))}")
        PropertyInput.model_validate({**self.property.model_dump(),**self.changes})
        return self
