from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx
from web3 import Web3

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "positions"
REF_CHAIN_IDS = ROOT / "data" / "reference" / "chain-ids.csv"

MORPHO_PROTOCOL_ID = 1
MORPHO_V2_PROTOCOL_ID = 2

POSITION_TYPE_VAULT = 1
POSITION_TYPE_SUPPLY = 2
POSITION_TYPE_BORROW = 3

DEFAULT_API_URL = "https://api.morpho.org/graphql"


@dataclass(frozen=True)
class VaultRow:
    chain: str
    chain_id: int
    protocol_id: int
    identifier: str
    position: str
    position_id: str


@dataclass(frozen=True)
class MarketRow:
    chain: str
    chain_id: int
    protocol_id: int
    identifier: str
    supply_or_borrow: int
    position: str
    position_id: str


def _load_chain_name_map() -> dict[int, str]:
    if not REF_CHAIN_IDS.exists():
        return {}
    with REF_CHAIN_IDS.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        out: dict[int, str] = {}
        for row in reader:
            try:
                chain_id = int(row["id"])
            except (KeyError, ValueError):
                continue
            name = (row.get("chain_name") or "").strip().lower()
            if name:
                out[chain_id] = name
        return out


def _default_chain_ids(chain_name_map: dict[int, str]) -> list[int]:
    # Based on Morpho API supported networks list in docs.
    supported = [1, 10, 130, 137, 143, 988, 999, 8453, 42161, 747474]
    if not chain_name_map:
        return sorted(set(supported))
    filtered = [cid for cid in supported if cid in chain_name_map]
    return sorted(set(filtered or supported))


def _post_graphql(url: str, query: str, variables: dict) -> dict:
    payload = {"query": query, "variables": variables}
    headers = {"Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]


def _paginate_for_chain(url: str, query: str, root_key: str, chain_id: int) -> list[dict]:
    items: list[dict] = []
    skip = 0
    first = 100
    while True:
        variables = {"first": first, "skip": skip, "chainIds": [chain_id]}
        data = _post_graphql(url, query, variables)
        block = data.get(root_key, {})
        page_items = block.get("items") or []
        if not page_items:
            break
        for item in page_items:
            item["_chainId"] = chain_id
        items.extend(page_items)
        if len(page_items) < first:
            break
        skip += first
    return items


def _paginate_all(url: str, query: str, root_key: str) -> list[dict]:
    items: list[dict] = []
    skip = 0
    first = 100
    while True:
        variables = {"first": first, "skip": skip}
        data = _post_graphql(url, query, variables)
        block = data.get(root_key, {})
        page_items = block.get("items") or []
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < first:
            break
        skip += first
    return items


def _lower_keccak_decimal(text: str) -> str:
    lowered = text.lower().encode("ascii")
    return str(int.from_bytes(Web3.keccak(lowered), "big"))


def _build_position(chain_id: int, protocol_id: int, position_type: int, identifier: str) -> str:
    return f"{chain_id}.{protocol_id}.{position_type}.{identifier.lower()}"


def _extract_chain_id(item: dict) -> int | None:
    if "_chainId" in item:
        return _coerce_int(item.get("_chainId"))
    if "chainId" in item:
        return _coerce_int(item.get("chainId"))
    chain = item.get("chain") or {}
    return _coerce_int(chain.get("id"))


def _coerce_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def fetch_vaults_v1(url: str, chain_ids: list[int]) -> list[dict]:
    query = """
    query Vaults($first: Int!, $skip: Int!, $chainIds: [Int!]) {
      vaults(first: $first, skip: $skip, where: { chainId_in: $chainIds }) {
        items { address chain { id } }
      }
    }
    """
    items: list[dict] = []
    for chain_id in chain_ids:
        items.extend(_paginate_for_chain(url, query, "vaults", chain_id))
    return items


def fetch_vaults_v2(url: str, chain_ids: list[int]) -> list[dict]:
    query = """
    query VaultV2s($first: Int!, $skip: Int!, $chainIds: [Int!]) {
      vaultV2s(first: $first, skip: $skip, where: { chainId_in: $chainIds }) {
        items { address chain { id } }
      }
    }
    """
    items: list[dict] = []
    for chain_id in chain_ids:
        items.extend(_paginate_for_chain(url, query, "vaultV2s", chain_id))
    return items


def fetch_markets(url: str, chain_ids: list[int]) -> list[dict]:
    query_filtered = """
    query Markets($first: Int!, $skip: Int!, $chainIds: [Int!]) {
      markets(first: $first, skip: $skip, where: { chainId_in: $chainIds }) {
        items { uniqueKey }
      }
    }
    """
    items: list[dict] = []
    try:
        for chain_id in chain_ids:
            items.extend(_paginate_for_chain(url, query_filtered, "markets", chain_id))
        return items
    except RuntimeError:
        query_all = """
        query Markets($first: Int!, $skip: Int!) {
          markets(first: $first, skip: $skip) {
            items { uniqueKey chain { id } }
          }
        }
        """
        all_items = _paginate_all(url, query_all, "markets")
        filtered: list[dict] = []
        for item in all_items:
            chain_id = _extract_chain_id(item)
            if chain_id in chain_ids:
                item["_chainId"] = chain_id
                filtered.append(item)
        return filtered


def build_vault_rows(
    items: Iterable[dict],
    chain_name_map: dict[int, str],
    protocol_id: int,
) -> list[VaultRow]:
    rows: list[VaultRow] = []
    for item in items:
        chain_id = _extract_chain_id(item)
        address = item.get("address")
        if chain_id is None or not address:
            continue
        chain_name = chain_name_map.get(chain_id, "")
        position = _build_position(chain_id, protocol_id, POSITION_TYPE_VAULT, address)
        position_id = _lower_keccak_decimal(position)
        rows.append(
            VaultRow(
                chain=chain_name,
                chain_id=chain_id,
                protocol_id=protocol_id,
                identifier=address,
                position=position,
                position_id=position_id,
            )
        )
    rows.sort(key=lambda r: (r.chain_id, r.identifier.lower()))
    return rows


def build_market_rows(
    items: Iterable[dict],
    chain_name_map: dict[int, str],
    protocol_id: int,
) -> list[MarketRow]:
    rows: list[MarketRow] = []
    for item in items:
        chain_id = _extract_chain_id(item)
        unique_key = item.get("uniqueKey")
        if chain_id is None or not unique_key:
            continue
        chain_name = chain_name_map.get(chain_id, "")
        for position_type in (POSITION_TYPE_SUPPLY, POSITION_TYPE_BORROW):
            position = _build_position(chain_id, protocol_id, position_type, unique_key)
            position_id = _lower_keccak_decimal(position)
            rows.append(
                MarketRow(
                    chain=chain_name,
                    chain_id=chain_id,
                    protocol_id=protocol_id,
                    identifier=unique_key,
                    supply_or_borrow=position_type,
                    position=position,
                    position_id=position_id,
                )
            )
    rows.sort(key=lambda r: (r.chain_id, r.identifier.lower(), r.supply_or_borrow))
    return rows


def write_vault_csv(path: Path, rows: list[VaultRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Chain",
                "Chain ID",
                "Morpho Protocol ID",
                "Identifier",
                "Position",
                "Position ID",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.chain,
                    row.chain_id,
                    row.protocol_id,
                    row.identifier,
                    row.position,
                    row.position_id,
                ]
            )


def write_market_csv(path: Path, rows: list[MarketRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Chain",
                "Chain ID",
                "Morpho Protocol ID",
                "Identifier",
                "Supply or borrow",
                "Position",
                "Position ID",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.chain,
                    row.chain_id,
                    row.protocol_id,
                    row.identifier,
                    row.supply_or_borrow,
                    row.position,
                    row.position_id,
                ]
            )


def parse_chain_ids(value: str | None, chain_name_map: dict[int, str]) -> list[int]:
    if value:
        ids = []
        for chunk in value.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                ids.append(int(chunk))
            except ValueError as exc:
                raise ValueError(f"Invalid chain id: {chunk}") from exc
        if not ids:
            raise ValueError("No chain ids parsed from --chain-ids")
        return sorted(set(ids))
    return _default_chain_ids(chain_name_map)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Morpho vaults/markets and generate position ids")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Morpho GraphQL API URL")
    parser.add_argument("--chain-ids", default=None, help="Comma-separated chain ids")
    parser.add_argument("--skip-v1", action="store_true", help="Skip Morpho v1 vaults")
    parser.add_argument("--skip-v2", action="store_true", help="Skip Morpho v2 vaults")
    parser.add_argument("--skip-markets", action="store_true", help="Skip Morpho markets")
    args = parser.parse_args()

    chain_name_map = _load_chain_name_map()
    chain_ids = parse_chain_ids(args.chain_ids, chain_name_map)

    if not (args.skip_v1 and args.skip_v2 and args.skip_markets):
        print(f"Using chain ids: {chain_ids}")

    if not args.skip_v1:
        v1_items = fetch_vaults_v1(args.api_url, chain_ids)
        v1_rows = build_vault_rows(v1_items, chain_name_map, MORPHO_PROTOCOL_ID)
        write_vault_csv(DATA_DIR / "morpho" / "vaults.csv", v1_rows)
        print(f"Wrote Morpho v1 vaults: {len(v1_rows)}")

    if not args.skip_v2:
        v2_items = fetch_vaults_v2(args.api_url, chain_ids)
        v2_rows = build_vault_rows(v2_items, chain_name_map, MORPHO_V2_PROTOCOL_ID)
        write_vault_csv(DATA_DIR / "morpho-v2" / "vaults.csv", v2_rows)
        print(f"Wrote Morpho v2 vaults: {len(v2_rows)}")

    if not args.skip_markets:
        market_items = fetch_markets(args.api_url, chain_ids)
        market_rows = build_market_rows(market_items, chain_name_map, MORPHO_PROTOCOL_ID)
        write_market_csv(DATA_DIR / "morpho" / "markets.csv", market_rows)
        print(f"Wrote Morpho markets: {len(market_rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
