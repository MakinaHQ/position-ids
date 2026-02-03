# Position ID Standard (v0)

## 1. Definitions

**Position string** is a dot-delimited, lowercased string that uniquely identifies a protocol position.

**Position ID** is `keccak256(position_string)`.

## 2. Canonical Form

The canonical position string is:

```
<chain_id>.<protocol_id>.<position_type>.<identifier>[.<extra>...]
```

- `chain_id` is the EVM chain id (integer). See `data/reference/chain-ids.csv` (`id` column).
- `protocol_id` is a repo-assigned integer. See `data/reference/protocols.csv` (`id` column).
- `position_type` is a repo-assigned integer. See `data/reference/position-types.csv` (`id` column).
- `identifier` is protocol-specific and MUST be sufficient to uniquely identify the position.
- `extra` segments are optional and only used when needed for uniqueness (documented per protocol).

Before hashing, the entire string MUST be lowercased ASCII.

## 3. Hashing

`position_id = keccak256(lowercase(position_string))`

The repo stores `position_id` as a base-10 unsigned integer (uint256) in CSV files.

## 4. Protocol Responsibilities

Each protocol document under `protocols/` MUST specify:

- which `position_type` values are used
- how to build the `identifier`
- any `extra` segments
- examples with pre-generated ids

## 5. Backwards Compatibility

Position strings are immutable. If a protocol changes its identification rules, it MUST use a new `protocol_id`.
