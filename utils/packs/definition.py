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

def parse_payload(payload: dict[str, Any]) -> PackConfig:
    slots = []
    for slot in payload.get("slots", []):
        item_weights = None
        if "item_weights" in slot:
            item_weights = [ItemWeight(**iw) for iw in slot["item_weights"]]
        raw_prf = slot.get("per_rarity_filters")
        per_rarity_filters = None
        if raw_prf:
            per_rarity_filters = {
                k: [FilterSpec(**f) for f in v]
                for k, v in raw_prf.items()
            }
        selection = SelectionSpec(**slot.get("selection", {}))
        filters = [FilterSpec(**f) for f in slot.get("filters", {})]
        
        rarity_weights = slot.get("rarity_weights")

        slots.append(
            SlotSpec(
                name=slot.get("name"),
                rolls=slot.get("rolls", 1),
                rarity_weights=rarity_weights,
                filters=filters,
                per_rarity_filters=per_rarity_filters,
                selection=selection,
                item_weights=item_weights
            ))
        
    duplication = DuplicationSpec(**payload.get("duplication", {}))

    pity_data = payload.get("pity")
    pity = None
    if pity_data:
        pity = PitySpec(**pity_data)
    
    post_processing = PostProcessingSpec(**payload.get("post_processing", {}))

    hooks = HooksSpec(**payload.get("hooks", {}))

    pack_config = PackConfig(
        slots=slots,
        global_filters=[FilterSpec(**f) for f in payload.get("global_filters", [])],
        duplication=duplication,
        pity=pity,
        post_processing=post_processing,
        hooks=hooks
    )
    return pack_config
        

def compile_filters(filters: list[FilterSpec]) -> tuple[str, list[str]]:
    sql = []
    params = []

    for f in filters:
        if f.values is None:
            raise ValueError("f.values[0] is None in compile_filters")
        match f.op:
            case "eq":
                sql.append(f"{f.field} = %s")
                params.append(f.values[0])
            case "neq":
                sql.append(f"{f.field} != %s")
                params.append(f.values[0])

            case "in":
                sql.append(f"{f.field} IN (%s)")
                params.append(tuple(f.values))
            case "not_in":
                sql.append(f"{f.field} NOT IN (%s)")
                params.append(tuple(f.values))

            case "exists":
                sql.append(f"{f.field} IS NOT NULL")
            case "not_exists":
                sql.append(f"{f.field} IS NULL")

            case "contains":
                sql.append(f"{f.field} LIKE %s")
                params.append(f"%{f.values[0]}%")
            case "not_contains":
                sql.append(f"{f.field} LIKE %s")
                params.append(f"%{f.values[0]}%")
            
            case "range":
                if len(f.values) != 2:
                    raise ValueError(f"Filter with op 'range' requires exactly 2 values [min, max]")
                sql.append(f"{f.field} BETWEEN %s AND %s")
                params.extend(f.values[:2])

            case _:
                raise ValueError(f"Invalid op: {f.op}")
        
    return " AND ".join(sql), params

def filter_item(item: dict, f: FilterSpec) -> bool:
    if f.values is None:
        raise ValueError("f.values is None")
    val = item.get(f.field)
    match f.op:
        case "eq":
            return val == f.values[0]
        case "neq":
            return val != f.values[0]
        case "in":
            return val in f.values
        case "not_in":
            return val not in f.values
        case "exists":
            return val is not None
        case "not_exists":
            return val is None
        case "contains":
            return any(v in val for v in f.values) if isinstance(val, list) else f.values[0] in str(val)
        case "not_contains":
            return all(v not in val for v in f.values) if isinstance(val, list) else f.values[0] not in str(val)
        case "range":
            return f.values[0] <= val <= f.values[1]
        case _:
            raise ValueError(f"Unsupported op {f.op}")
        
def apply_filters(items: Sequence[dict], filters: Sequence[FilterSpec]) -> list:
    result = []
    for item in items:
        ok = True
        for f in filters:
            if not filter_item(item, f):
                ok = False
                break
        if ok:
            result.append(item)
    return result

def compute_weights(
    items: Sequence[dict],
    item_weights: Optional[Sequence],
    rarity_weights: Optional[dict[str, float]]
) -> list[float]:

    name_to_weight = {iw.name: iw.pack_weight for iw in (item_weights or [])}

    rarity_counts = Counter(str(it["rarity_id"]) for it in items)

    weights = []
    for it in items:
        name = it.get("name")
        if name in name_to_weight:
            weights.append(name_to_weight[name])
            continue

        r = str(it["rarity_id"])

        if rarity_weights:
            if r in rarity_weights:
                weights.append(rarity_weights[r] / rarity_counts[r])
            else:
                weights.append(0.0)
        else:
            weights.append(1.0)

    return weights

def weighted_sample(items: Sequence[dict], weights: Sequence[float], k: int, distinct: bool) -> list:
    if k <= 0:
        return []
    if not distinct:
        return random.choices(list(items), weights=weights, k=k)
    items_list = list(items)
    weights_list = list(weights)
    picked = []
    for _ in range(min(k, len(items_list))):
        total = sum(weights_list)
        if total == 0:
            break
        r = random.random() * total
        accum = 0.0
        for idx, w in enumerate(weights_list):
            accum += w
            if r <= accum:
                picked.append(items_list.pop(idx))
                weights_list.pop(idx)
                break
    return picked

