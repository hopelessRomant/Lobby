import os
import time
from typing import Tuple, Optional, Any, Union
from decimal import Decimal, getcontext
from web3 import Web3

getcontext().prec = 36
GWEI = 10**9

def gwei_to_wei(g: Union[int, float, str, Decimal]) -> int:
    d = Decimal(str(g))
    return int((d * GWEI).to_integral_value(rounding="ROUND_HALF_UP"))

def wei_to_gwei(w: int) -> Decimal:
    return (Decimal(w) / GWEI).quantize(Decimal("1e-6"))

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
    if isinstance(val, (bytes, bytearray)):
        try:
            return int.from_bytes(val, "big")
        except Exception:
            return None
    try:
        return int(val)
    except Exception:
        return None

def eip1559_fees(
    w3: Web3,
    lookback_blocks: int = 8,
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
        fh = w3.eth.fee_history(block_count=lookback_blocks, newest_block="latest", reward_percentiles=[reward_percentile])
        rewards = fh.get("reward", []) 
        tips = []
        for br in rewards:
            if not br:
                continue
            val = to_int_hexsafe(br[0])
            if val is not None:
                tips.append(val)
        if tips:
            tips.sort()
            mid = len(tips) // 2
            median_unbuffered = tips[mid] if len(tips) % 2 == 1 else (tips[mid-1] + tips[mid]) // 2
    except Exception:
        median_unbuffered = None

    # Ask node for its max priority fee suggestion if available
    node_tip = None
    for attempt in range(rpc_retry_attempts):
        try:
            raw = getattr(w3.eth, "max_priority_fee", None)
            node_tip = to_int_hexsafe(raw)
            break
        except Exception:
            node_tip = None
            time.sleep(rpc_retry_delay)

    # enforce a hard cap on priority fee
    MAX_PRIORITY_CAP_WEI = gwei_to_wei(max_priority_fee_cap_gwei)
    if node_tip is not None:
        node_tip = min(node_tip, MAX_PRIORITY_CAP_WEI)
    if median_unbuffered is not None:
        median_unbuffered = min(median_unbuffered, MAX_PRIORITY_CAP_WEI)

    # Decide tip (priority fee) to use 
    buf = Decimal(str(priority_fee_buffer))
    candidates = []
    if median_unbuffered is not None:
        candidates.append(int((Decimal(median_unbuffered) * (Decimal(1) + buf)).to_integral_value()))
    if node_tip is not None:
        candidates.append(int((Decimal(node_tip) * (Decimal(1) + buf)).to_integral_value()))
    if candidates:
        tip = max(candidates)
    else:
        # last-resort
        tip = gwei_to_wei(Decimal("0.2"))

    tip = min(tip, MAX_PRIORITY_CAP_WEI)

    # Get base fee (pending preferred) 
    base_fee = None
    for bname in ("pending", "latest"):
        try:
            blk = w3.eth.get_block(bname)
            base_fee = to_int_hexsafe(blk.get("baseFeePerGas") or blk.get("baseFee"))
            if base_fee is not None:
                break
        except Exception:
            base_fee = None
            time.sleep(rpc_retry_delay)
    if base_fee is None:
        raise RuntimeError("Failed to fetch base fee from node")

    # max_fee using EIP-1559 base fee change rules +12.5% per block 
    nr: int = base_fee * pow(9, base_fee_bump_blocks)
    dr: int = pow(8, base_fee_bump_blocks)
    max_base_fee: int = (nr + dr - 1) // dr  

    max_fee = max_base_fee + tip

    return base_fee, tip, max_fee

def get_tx_fees(w3: Web3) -> dict:
    base_fee, tip, max_fee = eip1559_fees(w3)
    return {
        "baseFeePerGas": base_fee,
        "maxPriorityFeePerGas": tip,
        "maxFeePerGas": max_fee
    }

if __name__ == "__main__":
    rpc_url = os.getenv("ETH_INFURA")
    if not rpc_url:
        raise ValueError("ETH_RPC_URL environment variable not set")

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
    print(get_tx_fees(w3))
