import os
import time
from typing import Tuple, Optional, Any, List
import statistics
from web3 import Web3

GWEI = 10**9

def gwei_to_wei(g: float) -> int:
    return int(g * GWEI)

def wei_to_gwei(w: int) -> float:
    return w / GWEI

def to_int_hexsafe(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val, 16) if val.startswith("0x") else int(val)
        except Exception:
            return None
    try:
        return int(val)
    except Exception:
        return None

def int_median(data: list[int]) -> Optional[int]:
    if not data:
        return None
    return int(round(statistics.median(data)))

def _flatten_rewards(rewards) -> List[int]:
    out = []
    if not rewards:
        return out
    for block_rewards in rewards:
        if block_rewards is None:
            continue
        for r in block_rewards:
            rv = to_int_hexsafe(r)
            if rv is not None:
                out.append(rv)
    return out

def estimate_eip1559_fees(
    w3: Web3,
    lookback_blocks: int = 7,
    reward_percentile: float = 40.0,
    priority_fee_buffer: float = 0.10,
    max_priority_fee_cap_gwei: float = 1.0,
    base_fee_bump_blocks: int = 2,
    rpc_retry_attempts: int = 3,
    rpc_retry_delay: float = 0.2,
) -> Tuple[int, int, int]:

    # Gather historical priority fee (from fee_history)
    median_unbuffered = None
    try:
        fh = w3.eth.fee_history(lookback_blocks, "latest", [reward_percentile])
        rewards = fh.get("reward", [])
        flat = _flatten_rewards(rewards)
        print(sorted(flat))
        median_unbuffered = int_median(flat)
    except Exception as e:
        median_unbuffered = None

    # Ask node for its max priority fee suggestion if available
    node_tip = None
    for attempt in range(rpc_retry_attempts):
        try:
            if hasattr(w3.eth, "max_priority_fee"):
                try:
                    raw = w3.eth.max_priority_fee
                    node_tip = to_int_hexsafe(raw() if callable(raw) else raw)
                except TypeError:
                    node_tip = to_int_hexsafe(getattr(w3.eth, "max_priority_fee", None))
            else:
                node_tip = None
            break
        except Exception as e:
            node_tip = None
            time.sleep(rpc_retry_delay)

    MAX_PRIORITY_CAP_WEI = gwei_to_wei(max_priority_fee_cap_gwei)
    if node_tip is not None:
        node_tip = min(node_tip, MAX_PRIORITY_CAP_WEI)

    if median_unbuffered is not None:
        median_unbuffered = min(median_unbuffered, MAX_PRIORITY_CAP_WEI)

    # Decide tip (priority fee) to use 
    buffered_median = int(median_unbuffered * (1.0 + priority_fee_buffer)) if median_unbuffered is not None else None
    buffered_node_tip = int(node_tip * (1.0 + priority_fee_buffer)) if node_tip is not None else None

    tip_candidates = [c for c in (buffered_median, buffered_node_tip) if c is not None]
    if tip_candidates:
        tip = max(tip_candidates)
    else:
        # last-resort tip (0.1 gwei)
        tip = gwei_to_wei(0.1)

    tip = min(tip, MAX_PRIORITY_CAP_WEI)

    # Get base fee (pending preferred) 
    base_fee = None
    for bname in ("pending", "latest"):
        try:
            blk = w3.eth.get_block(bname)
            base_fee = to_int_hexsafe(blk.get("baseFeePerGas") or blk.get("baseFee"))
            if base_fee is not None:
                break
        except Exception as e:
            base_fee = None
            time.sleep(rpc_retry_delay)
    if base_fee is None:
        raise RuntimeError("Failed to fetch base fee from node")

    # max_fee using EIP-1559 base fee change rules 
    per_block_bump = 1 + (1 / 8.0)  # +12.5% per block 
    projected_base_max = int(base_fee * (per_block_bump ** base_fee_bump_blocks))
    max_fee = int(projected_base_max) + tip

    return base_fee, tip, max_fee


if __name__ == "__main__":
    rpc_url = os.getenv("ETH_INFURA")
    if not rpc_url:
        raise ValueError("ETH_RPC_URL (or ETH_INFURA) environment variable not set")

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
    base_fee, tip, max_fee = estimate_eip1559_fees(w3)

    print("baseFeePerGas (gwei):", round(wei_to_gwei(base_fee), 6))
    print("maxPriorityFeePerGas (gwei):", round(wei_to_gwei(tip), 6))
    print("Recommended maxFeePerGas (gwei):", round(wei_to_gwei(max_fee), 6))
