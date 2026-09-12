from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Parameters(Strict):
    filter_policy: Literal["published", "cpm1"] = "published"
    min_count: int = Field(default=10, ge=1, le=100)
    min_total_count: int = Field(default=15, ge=1, le=1000)
    min_samples: int = Field(default=3, ge=2, le=9)
    contrast: Literal["BasalvsLP", "BasalvsML", "LPvsML"] = "BasalvsLP"
    fdr: float = Field(default=0.05, ge=0.001, le=0.2)
    seed: int = Field(default=1, ge=0, le=2147483647)

class Limits(Strict):
    wall_seconds: int = Field(default=600, ge=5, le=1800)
    memory_mib: int = Field(default=4096, ge=256, le=8192)
    cpu: float = Field(default=2, ge=0.25, le=4)

class PlanCreate(Strict):
    workspace_id: str
    title: str = Field(min_length=1, max_length=160)
    dataset_id: Literal["law2018", "chen2016"] = "law2018"
    recipe: Literal["density", "differential", "mds"] = "density"
    parameters: Parameters = Field(default_factory=Parameters)
    parent_id: str | None = None
    reason: str = Field(default="", max_length=2000)
    @model_validator(mode="after")
    def supported(self):
        if (self.dataset_id == "chen2016") != (self.recipe == "mds"):
            raise ValueError("Chen supports MDS; Law supports density and differential expression")
        if self.dataset_id == "chen2016":
            if "min_samples" not in self.parameters.model_fields_set:
                self.parameters.min_samples = 2
            elif self.parameters.min_samples != 2:
                raise ValueError("Chen MDS requires two samples per group")
        return self

class Correction(Strict):
    expected_revision: int
    parameters: Parameters
    reason: str = Field(min_length=3, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)

class LockRequest(Strict):
    expected_revision: int
    reviewed_fields: list[str] = Field(min_length=1, max_length=30)

class RunCreate(Strict):
    plan_id: str
    limits: Limits = Field(default_factory=Limits)
    use_cache: bool = False

class Review(Strict):
    status: Literal["accepted_with_limits", "disputed"]
    note: str = Field(min_length=3, max_length=4000)

class Membership(Strict):
    subject: str = Field(min_length=1, max_length=200)
    role: Literal["owner", "editor", "reviewer", "viewer"]

class ExtractionField(Strict):
    key: str = Field(max_length=100)
    value: str | int | float | None
    origin: Literal["reported", "inferred", "missing"]
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)
    explanation: str = Field(max_length=2000)

    quote: str = Field(default="", max_length=2000)
