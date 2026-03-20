# position-ids

An open standard repo for deterministic, protocol-agnostic position identifiers in crypto/DeFi.

The goal is simple: any position that can be accounted for should have a unique, reproducible ID derived from its defining parameters. This repo collects the **spec**, **reference tables**, and **pre-generated position IDs** for known protocols.

## Quick Idea

We build a canonical, dot-delimited **position string** from parameters like chain id, protocol id, position type, and a protocol-specific identifier. Then we lower-case it and compute `keccak256` to obtain the **Position ID**.

```
position = <chain_id>.<protocol_id>.<position_type>.<identifier>[.<extra>...]
position_id = keccak256(lowercase(position))
```

Examples and pre-generated IDs live in `data/` and `protocols/`.

## Repo Layout

- `SPEC.md` - the position id standard.
- `data/reference/` - canonical chain ids, protocol ids, and position types.
- `data/positions/` - pre-generated positions and their ids, grouped by protocol.
- `protocols/` - protocol-specific docs with examples and guidance.

## Status

This repo is an initial seed. The first protocols are Morpho, MorphoV2, and Grove. Minimal tooling exists under `tools/` for generating and maintaining protocol position ids.

## Contributing

Open a PR to add:
- new protocol ids to `data/reference/protocols.csv`
- new position types to `data/reference/position-types.csv`
- pre-generated position ids under `data/positions/<protocol>/`
- a protocol doc under `protocols/`

Keep identifiers stable and document any protocol-specific interpretation in the protocol doc.
