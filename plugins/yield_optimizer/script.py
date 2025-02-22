from plugins.yield_optimizer.yield_optimizer import execute_rebalance

def yield_optimizer_tool(prompt: str) -> str:
    # The prompt is ignored; on-chain data triggers the rebalance.
    return execute_rebalance()