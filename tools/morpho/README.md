# Morpho Position ID Generator

Minimal generator for Morpho vaults and markets using the official GraphQL API.

## Setup (uv)

```
cd tools/morpho
uv venv
uv sync
```

## Run

```
uv run morpho-fetch
```

Optional flags:

- `--chain-ids 1,10,130,137,143,988,999,8453,42161,747474`
- `--skip-v1`
- `--skip-v2`
- `--skip-markets`
- `--api-url https://api.morpho.org/graphql`

## Output

- `data/positions/morpho/vaults.csv`
- `data/positions/morpho/markets.csv`
- `data/positions/morpho-v2/vaults.csv`

By default, the script targets Morpho's currently documented chain ids: `1,10,130,137,143,988,999,8453,42161,747474`.
