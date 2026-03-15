from pydantic import BaseModel, Field, field_validator
from typing import Counter, Optional, Any, Sequence
from typing_extensions import Annotated
import random

class FilterSpec(BaseModel):
    field: str
    op: str
    values: Optional[list[Any]]
    @field_validator("values", mode="before")
    def check_values(cls, v, info):
        requires_value = {"eq", "neq", "in", "not_in", "contains", "not_contains", "range"}
        op = info.data.get("op")
        if op in requires_value:
            if not v or len(v) == 0:
                raise ValueError(f"filter with op '{op}' requires a non-empty values list")
        return v

class SelectionSpec(BaseModel):
    # weighted, random top n
    mode: str = "weighted"
    distinct_within_slot: bool = False

class ItemWeight(BaseModel):
    name: str
    pack_weight: float = Field(gt=0)

class SlotSpec(BaseModel):
    name: str|None
    rolls: int = 1
    rarity_weights: Optional[dict[str, float]] = None
    selection: SelectionSpec = SelectionSpec()
    filters: list[FilterSpec] = []
    per_rarity_filters: Optional[dict[str, list[FilterSpec]]] = None
    item_weights: Optional[list[ItemWeight]] = None

class PitySpec(BaseModel):
    enabled: bool = False
    after_consecutive_opens: int = Field(ge=1)
    boost: dict[str, float] = {}

class DuplicationSpec(BaseModel):
    allow_duplicates_across_slots: bool = True
    allow_duplicates_per_user: bool = True
    # reroll|downgrade|keep|replace_with_currency
    duplicate_policy: str = "keep"

class PostProcessingSpec(BaseModel):
    #  "downgrade|fallback_to_pool|raise_error"
    on_empty: str = "raise_error"
    on_new: dict[str, Any] = {}

class HooksSpec(BaseModel):
    pre_roll_sql: str = ""
    post_commit_actions: list[str] = []

class PackConfig(BaseModel):
    slots: list[SlotSpec]
    global_filters: list[FilterSpec] = []
    duplication: DuplicationSpec = DuplicationSpec()
    pity: Optional[PitySpec]
    post_processing: PostProcessingSpec = PostProcessingSpec()
    hooks: HooksSpec = HooksSpec()