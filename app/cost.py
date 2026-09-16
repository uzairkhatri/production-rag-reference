from dataclasses import dataclass
@dataclass(frozen=True)
class Usage:
    estimated_input_tokens:int
    estimated_cost_usd:float
def estimate_usage(words:int,cost_per_1k_tokens:float=0.0)->Usage:
    tokens=max(0,round(words*1.33))
    return Usage(tokens,(tokens/1000)*cost_per_1k_tokens)
