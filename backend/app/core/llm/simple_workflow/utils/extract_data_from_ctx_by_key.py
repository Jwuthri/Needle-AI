from llama_index.core.workflow import Context

import pandas as pd


async def extract_data_from_ctx_by_key(ctx: Context, key: str, dataset: str) -> pd.DataFrame:
    state = await ctx.store.get("state", {})
    dataset_data = state.get("dataset_data", {})
    if not dataset_data:
        return None

    return dataset_data.get(dataset)
