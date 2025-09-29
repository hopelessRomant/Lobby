import os
import time
import statistics
from web3 import Web3
from typing import Tuple, Any

GWEI = 10**9

def gwei_to_wei(x: float) -> int:
    return int(x * GWEI)

def require_int(value: Any, field: str) -> int:
    if value is None:
        raise ValueError(f"Missing: {field}")
    return int(value)

def estimate_eip1559_fees(
    w3: Web3,
    lookback_blocks: int = 7,
    percentile: int = 10,
    priority_fee_buffer: float = 0.10,
    max_priority_rpc_retries: int = 5,
    rpc_retry_delay_seconds: float = 0.25
) -> Tuple[int, int, Any, int]:
    # Fetch the 10th percentile of the reward (priority fee) from recent blocks
    try:
        fee_history = w3.eth.fee_history(lookback_blocks, "pending", [percentile])
        rewards = fee_history.get("reward", [])
        rewards_flat = [int(r[0]) for r in rewards if r]
        print(sorted(rewards_flat))
        median_tip = statistics.median(rewards_flat) if rewards_flat else None
        print(median_tip)
    except Exception:
        median_tip = None

    # Retry fetching the node's max priority fee if the above fails
    node_tip = None
    for _ in range(max_priority_rpc_retries):
        try:
            node_tip = int((w3.eth.max_priority_fee)*(1+priority_fee_buffer))
            print(node_tip)
            break
        except Exception:
            node_tip = None
            time.sleep(rpc_retry_delay_seconds)

    # Determine the tip to use
    if median_tip is None and node_tip is None:
        tip = gwei_to_wei(0.01) # Fallback to 0.01 gwei if both methods fail
    elif median_tip is None:
        tip = node_tip
    else:
        buffered_tip = int(median_tip * (1.0 + priority_fee_buffer))
        tip = min(buffered_tip, node_tip) if node_tip is not None else buffered_tip
        print(buffered_tip)

    # Fetch the base fee from the pending block
    try:
        pending_block = w3.eth.get_block("pending")
        base_fee = require_int(pending_block.get("baseFeePerGas", pending_block.get("baseFee")), "baseFeePerGas")
    except Exception:
        latest_block = w3.eth.get_block("latest")
        base_fee = require_int(latest_block.get("baseFeePerGas", latest_block.get("baseFee")), "baseFeePerGas")

    # Calculate maxFeePerGas as 2 * baseFee + tip
    int_tip = require_int(tip, "tip")
    max_fee = base_fee * 2 + int_tip

    return base_fee, int_tip, buffered_tip, max_fee

if __name__ == "__main__":
    rpc_url = os.getenv("ETH_INFURA")
    if rpc_url is None:
        raise ValueError("ETH_RPC_URL environment variable is not set.")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    base_fee, min_priority_fee, history_buffered_median, max_fee = estimate_eip1559_fees(w3)

    print("Base Fee (gwei):", base_fee / GWEI)
    print("min Priority fee (gwei):", min_priority_fee / GWEI)
    print("history_buffered_median fee (gwei):", history_buffered_median / GWEI)
    print("Max Fee (gwei):", max_fee / GWEI)
