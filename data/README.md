# Data

- `reference/` contains canonical lookup tables (chain ids, protocol ids, position types). Each table uses a lowercase `id` column as the first column.
- `positions/` contains pre-generated position strings and ids, grouped by protocol.

Example paths:

- `data/positions/morpho/vaults.csv`
- `data/positions/morpho/markets.csv`
- `data/positions/morpho-v2/vaults.csv`

All CSVs use headers and are UTF-8.
