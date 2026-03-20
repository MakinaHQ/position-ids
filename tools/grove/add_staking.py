from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from web3 import Web3

ROOT = Path(__file__).resolve().parents[2]
REF_CHAIN_IDS = ROOT / "data" / "reference" / "chain-ids.csv"
OUTPUT_PATH = ROOT / "data" / "positions" / "grove" / "staking.csv"

GROVE_PROTOCOL_ID = 50
POSITION_TYPE_STAKE = 4


@dataclass(frozen=True)
class StakingRow:
    chain: str
    chain_id: int
    protocol_id: int
    identifier: str
    position: str
    position_id: str


def load_chain_maps() -> tuple[dict[int, str], dict[str, int]]:
    id_to_name: dict[int, str] = {}
    name_to_id: dict[str, int] = {}
    with REF_CHAIN_IDS.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                chain_id = int(row["id"])
            except (KeyError, TypeError, ValueError):
                continue
            name = (row.get("chain_name") or "").strip().lower()
            if not name:
                continue
            id_to_name[chain_id] = name
            name_to_id[name] = chain_id
    return id_to_name, name_to_id


def parse_chain(value: str, id_to_name: dict[int, str], name_to_id: dict[str, int]) -> tuple[int, str]:
    raw = value.strip().lower()
    if not raw:
        raise ValueError("Chain value cannot be empty")
    if raw in name_to_id:
        chain_id = name_to_id[raw]
        return chain_id, id_to_name[chain_id]
    try:
        chain_id = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"Unknown chain '{value}'. Use a canonical chain name or numeric chain id."
        ) from exc
    if chain_id not in id_to_name:
        raise ValueError(
            f"Unknown chain id '{chain_id}'. Add it to data/reference/chain-ids.csv first."
        )
    return chain_id, id_to_name[chain_id]


def normalize_address(value: str) -> str:
    if not Web3.is_address(value):
        raise ValueError(f"Invalid staking contract address: {value}")
    return value.lower()


def build_position(chain_id: int, identifier: str) -> str:
    return f"{chain_id}.{GROVE_PROTOCOL_ID}.{POSITION_TYPE_STAKE}.{identifier}"


def lower_keccak_decimal(text: str) -> str:
    lowered = text.lower().encode("ascii")
    return str(int.from_bytes(Web3.keccak(lowered), "big"))


def read_rows() -> list[StakingRow]:
    if not OUTPUT_PATH.exists():
        return []
    rows: list[StakingRow] = []
    with OUTPUT_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                chain_id = int(row["Chain ID"])
                protocol_id = int(row["Grove Protocol ID"])
            except (KeyError, TypeError, ValueError):
                continue
            identifier = (row.get("Identifier") or "").strip().lower()
            position = (row.get("Position") or "").strip().lower()
            position_id = (row.get("Position ID") or "").strip()
            chain = (row.get("Chain") or "").strip().lower()
            if not identifier or not position or not position_id:
                continue
            rows.append(
                StakingRow(
                    chain=chain,
                    chain_id=chain_id,
                    protocol_id=protocol_id,
                    identifier=identifier,
                    position=position,
                    position_id=position_id,
                )
            )
    return rows


def upsert_row(rows: list[StakingRow], new_row: StakingRow) -> list[StakingRow]:
    filtered = [
        row
        for row in rows
        if not (row.chain_id == new_row.chain_id and row.identifier == new_row.identifier)
    ]
    filtered.append(new_row)
    filtered.sort(key=lambda row: (row.chain_id, row.identifier))
    return filtered


def write_rows(rows: list[StakingRow]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Chain",
                "Chain ID",
                "Grove Protocol ID",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Manually add a Grove staking position id")
    parser.add_argument(
        "--chain",
        required=True,
        help="Canonical chain name from data/reference/chain-ids.csv or numeric chain id",
    )
    parser.add_argument(
        "--staking-contract",
        required=True,
        help="Grove staking contract address",
    )
    args = parser.parse_args()

    id_to_name, name_to_id = load_chain_maps()
    chain_id, chain_name = parse_chain(args.chain, id_to_name, name_to_id)
    identifier = normalize_address(args.staking_contract)
    position = build_position(chain_id, identifier)
    position_id = lower_keccak_decimal(position)

    new_row = StakingRow(
        chain=chain_name,
        chain_id=chain_id,
        protocol_id=GROVE_PROTOCOL_ID,
        identifier=identifier,
        position=position,
        position_id=position_id,
    )
    rows = upsert_row(read_rows(), new_row)
    write_rows(rows)
    print(f"Upserted Grove staking entry: {position}")
    print(f"Position ID: {position_id}")
    print(f"Output: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
