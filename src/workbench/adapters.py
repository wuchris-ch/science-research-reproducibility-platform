"""Validated, versioned scientific capabilities. Manifests never supply executable code."""

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .artifacts import digest

MANIFESTS = Path(__file__).parent / "manifests"


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["integer", "number", "string", "boolean"]
    default: str | int | float | bool
    label: str
    minimum: float | None = None
    maximum: float | None = None
    choices: list[str | int | float | bool] = Field(default_factory=list)
    sensitivity: list[str | int | float | bool] = Field(default_factory=list, max_length=4)

    def validate_value(self, value):
        types = {"integer": (int,), "number": (int, float), "string": (str,), "boolean": (bool,)}
        if type(value) not in types[self.type]:
            raise ValueError(f"{self.label} requires {self.type}")
        if self.type in ("integer", "number"):
            if not math.isfinite(value):
                raise ValueError(f"{self.label} must be finite")
            if self.minimum is not None and value < self.minimum:
                raise ValueError(f"{self.label} is below its supported minimum")
            if self.maximum is not None and value > self.maximum:
                raise ValueError(f"{self.label} exceeds its supported maximum")
        if self.choices and value not in self.choices:
            raise ValueError(f"Unsupported {self.label}")
        return value

    @model_validator(mode="after")
    def valid_default(self):
        self.validate_value(self.default)
        for value in self.sensitivity:
            self.validate_value(value)
        return self


class Adapter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,60}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    recipe: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,40}$")
    title: str
    runtime: Literal["historical", "deseq2"]
    environment: str
    input_contract: Literal["legacy-curated", "paired-counts-v1"]
    parameters: dict[str, Rule]
    required_outputs: list[str] = Field(min_length=1)
    numeric_outputs: list[str] = Field(min_length=1)
    methods: dict[str, str]
    adaptations: list[str]
    references: list[str]

    @model_validator(mode="after")
    def safe_outputs(self):
        for name in self.required_outputs + self.numeric_outputs:
            if not re.fullmatch(r"[a-zA-Z0-9_.-]+", name) or name in (".", ".."):
                raise ValueError("Output names must be flat relative file names")
        if not set(self.numeric_outputs) <= set(self.required_outputs):
            raise ValueError("Numeric outputs must be required outputs")
        return self

    def resolve(self, values=None, defaults=None):
        values = values or {}
        unknown = set(values) - self.parameters.keys()
        if unknown:
            raise ValueError("Unsupported parameters: " + ", ".join(sorted(unknown)))
        merged = {k: r.default for k, r in self.parameters.items()} | (defaults or {}) | values
        return {k: self.parameters[k].validate_value(v) for k, v in merged.items()}

    def snapshot(self):
        body = self.model_dump()
        return {**body, "sha256": digest(body)}


@lru_cache
def registry():
    entries = [
        Adapter.model_validate_json(path.read_text()) for path in sorted(MANIFESTS.glob("adapter-*.json"))
    ]
    result = {entry.recipe: entry for entry in entries}
    if not entries or len(result) != len(entries) or len({e.id for e in entries}) != len(entries):
        raise ValueError("Adapter identities and recipe names must be unique")
    return result


@lru_cache
def datasets():
    result = json.loads((MANIFESTS / "datasets.json").read_text())
    for identity, data in result.items():
        validate_dataset(identity, data)
    return result


def validate_dataset(identity, data):
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,60}", identity):
        raise ValueError("Invalid registered dataset identity")
    if not data.get("recipes") or any(recipe not in registry() for recipe in data["recipes"]):
        raise ValueError("Dataset requires registered recipes")
    for name, value in data.get("input_hashes", {}).items():
        if name not in ("counts.tsv", "samples.tsv") or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("Invalid registered input hash")
    geometry = data.get("geometry_file")
    if geometry and not re.fullmatch(r"[a-z0-9-]+\.json", geometry):
        raise ValueError("Geometry must name a local fixture")
    spec = data.get("legacy_input")
    if not spec:
        return
    if (
        set(spec) != {"reader", "filter", "sample_map"}
        or spec["reader"] not in ("count-files", "annotated-matrix")
        or spec["filter"] not in ("group-rule", "annotated-cpm")
    ):
        raise ValueError("Unknown registered input operation")
    rows = spec["sample_map"]
    if not 2 <= len(rows) <= 64 or len({r["sample"] for r in rows}) != len(rows):
        raise ValueError("Sample declarations must be bounded and unique")
    column = "file" if spec["reader"] == "count-files" else "column"
    if len({r.get(column) for r in rows}) != len(rows):
        raise ValueError("Input columns must map one-to-one to samples")
    for row in rows:
        if not row.get("group") or any(
            not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", v) for v in row.values()
        ):
            raise ValueError("Sample declarations require flat identifiers")


def resolve(dataset_id, recipe, parameters=None, *, imported=False):
    if recipe not in registry():
        raise ValueError("Unknown registered adapter")
    adapter = registry()[recipe]
    if imported:
        if adapter.input_contract != "paired-counts-v1":
            raise ValueError("Uploaded datasets require an adapter with a validated input contract")
        defaults = {}
    else:
        dataset = datasets().get(dataset_id)
        if not dataset or recipe not in dataset["recipes"]:
            raise ValueError("Dataset does not support this adapter")
        defaults = dataset.get("parameter_defaults", {})
    values = adapter.resolve(parameters, defaults)
    if not imported:
        for key, allowed in dataset.get("parameter_constraints", {}).items():
            if values[key] not in allowed:
                raise ValueError(f"Dataset requires {key} in {allowed}")
    return adapter, values
