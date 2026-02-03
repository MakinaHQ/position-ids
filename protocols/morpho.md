# Morpho (protocol_id = 1)

## Position Types

- `vault` (1)
- `supply` (2)
- `borrow` (3)

## Identifier Rules

- **Vaults:** `identifier` is the vault address.
- **Markets:** `identifier` is the market id (bytes32 hex string).

## Data

- `data/positions/morpho/vaults.csv`
- `data/positions/morpho/markets.csv`

## Examples

Vault (Base):

```
position = 8453.1.1.0xbeefe94c8ad530842bfe7d8b397938ffc1cb83b2
position_id = 107748699282353890608450452296395923511697059219688206203817978138856427849492
```

Market supply (Ethereum):

```
position = 1.1.2.0x64d65c9a2d91c36d56fbc42d69e979335320169b3df63bf92789e2c8883fcc64
position_id = 72686274391330981562498936126154096098244612796773365020661383009123026656622
```

Market borrow (Ethereum):

```
position = 1.1.3.0x64d65c9a2d91c36d56fbc42d69e979335320169b3df63bf92789e2c8883fcc64
position_id = 94391678444873856202043078480557702914203483983035827457242084158242742343135
```
