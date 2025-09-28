import os
import time
from web3 import Web3
from typing import Tuple

GWEI = 10**9

def gwei_to_wei(x: float) -> int:
    return int(x * GWEI)

def estimate_eip1559_fees(
    w3: Web3,
    lookback_blocks: int = 4,
    percentile: int = 10,
    priority_fee_buffer: float = 0.10,
    max_priority_rpc_retries: int = 5,
    rpc_retry_delay_seconds: float = 0.25
) -> Tuple[int, int, int]:
    # Fetch the 10th percentile of the reward (priority fee) from recent blocks
    try:
        fee_history = w3.eth.fee_history(lookback_blocks, "pending", [percentile])
        rewards = fee_history.get("reward", [])
        rewards_flat = [int(r[0]) for r in rewards if r]
        avg_tip = int(sum(rewards_flat) / len(rewards_flat)) if rewards_flat else None
    except Exception:
        avg_tip = None

    # Retry fetching the node's max priority fee if the above fails
    node_tip = None
    for _ in range(max_priority_rpc_retries):
        try:
            node_tip = int(w3.eth.max_priority_fee)
            break
        except Exception:
            node_tip = None
            time.sleep(rpc_retry_delay_seconds)

    # Determine the tip to use
    if avg_tip is None and node_tip is None:
        tip = gwei_to_wei(2.0)  # Default to 2 gwei if both methods fail
    elif avg_tip is None:
        tip = node_tip
    else:
        buffered_tip = int(avg_tip * (1.0 + priority_fee_buffer))
        tip = min(buffered_tip, node_tip) if node_tip is not None else buffered_tip

    # Fetch the base fee from the pending block
    try:
        pending_block = w3.eth.get_block("pending")
        base_fee = int(pending_block.get("baseFeePerGas", pending_block.get("baseFee")))
    except Exception:
        latest_block = w3.eth.get_block("latest")
        base_fee = int(latest_block.get("baseFeePerGas", latest_block.get("baseFee")))

    # Calculate maxFeePerGas as 2 * baseFee + tip
    max_fee = base_fee * 2 + tip

    return base_fee, tip, max_fee

if __name__ == "__main__":
    # Load RPC URL from environment variables
    rpc_url = os.getenv("ETH_INFURA")
    if rpc_url is None:
        raise ValueError("ETH_RPC_URL environment variable is not set.")

    # Initialize Web3 instance
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    # Estimate fees
    base_fee, max_priority_fee, max_fee = estimate_eip1559_fees(w3)

    # Print the estimated fees in gwei
    print("Base Fee (gwei):", base_fee / GWEI)
    print("Max Priority Fee (gwei):", max_priority_fee / GWEI)
    print("Max Fee (gwei):", max_fee / GWEI)
