# Grove Position ID Generator

Manual generator for Grove staking entries.

## Setup (uv)

```
cd tools/grove
uv venv
uv sync
```

## Run

```
uv run python add_staking.py --chain ethereum --staking-contract 0x3bD276885c070Fe3D9bafdc5e699E85D2d776A15
```

`--chain` accepts either a canonical chain name from `data/reference/chain-ids.csv` or a numeric chain id.

## Output

- `data/positions/grove/staking.csv`

The command upserts the staking contract row, keeping the CSV sorted by chain id then identifier.
