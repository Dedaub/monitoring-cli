# Maple Syrup — Cross-Chain Tokens (SYRUP, syrupUSDC, syrupUSDT) across all 7 chains

**Status:** verified 2026-05-29 against `MapleAddressRegistryETH.sol` / `MapleAddressRegistryBASEL2.sol`, the **Chainlink CCIP mainnet token directory API** (`docs.chain.link/api/ccip/v1/tokens?environment=mainnet`), block-explorer contract verification, and live `eth_getCode` / `eth_getLogs`. Token topic0s recomputed locally with keccak.
**Scope:** Maple's **lending protocol** is Ethereum + Base only ([v2.md](v2.md)). This file covers the **tokens** that move cross-chain: the governance token **SYRUP** and the yield tokens **syrupUSDC / syrupUSDT / syrupUSDG**, across the 7 requested chains: Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137).

> **Two different bridges — the single most important fact:**
> - **SYRUP** (governance) bridges via **LayerZero OFT v2** (OFT Adapter on Ethereum, OFT token on remotes).
> - **syrupUSDC / syrupUSDT** (yield) bridge via **Chainlink CCIP** using the **CCT (Cross-Chain Token)** standard: a `BurnMintERC20` token + a CCIP Token Pool per chain; Ethereum is canonical via a `lockRelease` pool.
> The **MapleCCIPReceiver** (Ethereum) is part of the CCIP deposit/redeem flow for the yield tokens; it is **not** used by SYRUP.

---

## 1. Deployment matrix (the 7 requested chains)

| Chain | ID | SYRUP (LZ OFT) | syrupUSDC (CCIP) | syrupUSDT (CCIP) | Lending protocol |
|-------|-----|----------------|------------------|------------------|------------------|
| **Ethereum** | 1 | `0x643C…2d66` (proxy) + OFT adapter `0x688A…9a2F` | `0x80ac…Cc0b` (canonical Pool) | `0x356B…BA7D` (canonical Pool) | ✅ full ([v2.md](v2.md)) |
| **Base** | 8453 | OFT `0x688A…9a2F` | `0x6609…00f5` | — | ✅ Cash USDC pool |
| **Arbitrum** | 42161 | — | `0x41CA…42b5` | — | ✗ token only |
| **BNB** | 56 | — | — | `0x8E9d…6c4e` | ✗ token only |
| **Optimism** | 10 | — | — | — | ✗ **nothing** |
| **Polygon PoS** | 137 | — (impostor only⚠️) | — | — | ✗ **nothing** |
| **Avalanche** | 43114 | — | — | — | ✗ **nothing** |

**Of the 6 non-Ethereum chains: only Base+Arbitrum carry syrupUSDC, only BNB carries syrupUSDT, and SYRUP OFT is only on Base.** Optimism, Polygon, and Avalanche have **no** Maple deployment of any kind.

> ⚠️ **Impostor tokens** named "Maple syrup" exist on Polygon (`0x6d1e6ba0097de189efe88265378244e48d6f0be6`, **0 supply**) and BNB (`0x63551015d3d6d79a98b37f217fd99524385db503`, **large non-zero supply** ≈ `0x…4e18e40a48b3f380196c0000000`) — both **unrelated** to Maple. Exclude them.

---

## 2. Token addresses (verified)

### 2.1 SYRUP (governance, LayerZero OFT v2)

| Chain | Contract | Address | Notes |
|-------|----------|---------|-------|
| Ethereum | SYRUP token (proxy) | `0x643C4E15d7d62Ad0aBeC4a9BD4b001aA3Ef52d66` | impl `0x6eD767EBCfF51533E5181f7bf818F2b9bD767aec` |
| Ethereum | SYRUP **OFT Adapter** (lockbox) | `0x688AEe022AA544f150678B8E5720b6b96a9E9a2F` | locks canonical SYRUP, mints on remote |
| Ethereum | stSYRUP (staked) | `0xc7E8b36E0766D9B04c93De68A9D47dD11f260B45` | non-bridged |
| Base | SYRUP **OFT** | `0x688AEe022AA544f150678B8E5720b6b96a9E9a2F` | **same address** as Eth adapter (deterministic deploy); here it IS the token |

The OFT adapter proxy impl on both chains = `0x08881c46f82325ce2e403097be40066fa8c326b2` (verified identical bytecode, 2739B).

### 2.2 syrupUSDC (yield, Chainlink CCIP `BurnMintERC20`, 6 decimals)

| Chain | Token | CCIP Token Pool |
|-------|-------|-----------------|
| Ethereum (canonical) | `0x80ac24aA929eaF5013f6436cdA2a7ba190f5Cc0b` (the Pool itself) | lockRelease `0x20B79D39Bd44dEee4F89B1e9d0e3b945fde06491` |
| Base | `0x660975730059246A68521a3e2FBD4740173100f5` | `0xA36955b2Bc12Aee77FF7519482D16C7B86DBe42a` |
| Arbitrum | `0x41CA7586cC1311807B4605fBB748a3B8862b42b5` | `0x660975730059246A68521a3e2FBD4740173100f5` |

### 2.3 syrupUSDT (yield, CCIP `BurnMintERC20`, 6 decimals)

| Chain | Token | CCIP Token Pool |
|-------|-------|-----------------|
| Ethereum (canonical) | `0x356B8d89c1e1239Cbbb9dE4815c39A1474d5BA7D` (the Pool itself) | lockRelease `0xDE76A096C5eadDdf97Af3fE15ee49d32AEDa9822` |
| **BNB** | `0x8E9d4cEa39299323FE8eda678cAD449718556c4e` | `0xEAA7E1f805747ae29d5618b568d1b044A8b37A01` |

### 2.4 syrupUSDG (Ethereum only)

syrupUSDG Pool `0x87b65C4aAFFA76881f9E96F3e7ED945ddFC3Cd7A` — not bridged to any of the 7 chains as of this writing.

### 2.5 MapleCCIPReceiver (Ethereum) — CCIP deposit/redeem hook

Proxy `0x02B6A75c5D1F430F0614dc5AC8aD5F9D35fbA2c4`, impl `0x23CEF2965Db19f67A996371F9Cb1A2F33D2b4821`.

### 2.6 Beyond the 7 chains (from CCIP registry, for completeness)

syrupUSDC also on Solana (non-EVM `AvZZF1Ya…ZeUj`) and chain IDs 143 (Monad?), 4217, 57073 (Ink?). syrupUSDT also on Plasma (9745), Mantle (5000), 57073. Chain-ID→name mapping for 143/4217/57073 is tentative — verify before use.

---

## 3. Token-layer event topics (chain-agnostic)

### 3.1 ERC-20 (all SYRUP / syrupUSDC / syrupUSDT carry these)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` ✅ live on all |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` ✅ |

Cross-chain mint/burn appear as `Transfer` to/from `0x0` (the CCIP pool mints/burns on the BurnMintERC20).

### 3.2 LayerZero OFT v2 (SYRUP bridging — on the OFT adapter/token `0x688A…9a2F`)

| topic0 | Event |
|--------|-------|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` |

**LayerZero v2 endpoint IDs (eids)** used as `dstEid`/`srcEid` (standard, not Maple-custom): Ethereum `30101`, Base `30184`, Arbitrum `30110`, Optimism `30111`, Polygon `30109`, BNB `30102`, Avalanche `30106`. (Maple's SYRUP peers are only Ethereum↔Base today — confirm the active peer set by reading `peers(eid)` on the OFT.)

### 3.3 Chainlink CCIP token pools (syrupUSDC / syrupUSDT bridging)

`BurnMintTokenPool` (remote chains) emits:

| topic0 | Event |
|--------|-------|
| `0x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7` | `Burned(address indexed sender, uint256 amount)` |
| `0x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0` | `Minted(address indexed sender, address indexed recipient, uint256 amount)` |

`LockReleaseTokenPool` (Ethereum canonical) emits:

| topic0 | Event |
|--------|-------|
| `0x9f1ec8c880f76798e7b793325d625e9b60e4082a553c98f42b6cda368dd60008` | `Locked(address indexed sender, uint256 amount)` |
| `0x2d87480f50083e2b2759522a8fdda59802650a8055e609a7772cf70c07748f52` | `Released(address indexed sender, address indexed recipient, uint256 amount)` |

(For full CCIP `CCIPSendRequested` / `ExecutionStateChanged` router/onramp topics, see the Chainlink CCIP reference; those live on the CCIP Router/OnRamp, not the token pool.)

---

## 4. Proxies

| Contract | Proxy? | Slot |
|----------|--------|------|
| SYRUP token (Eth) | ✓ EIP-1967 | impl `0x6eD767EB…` |
| SYRUP OFT adapter/token (Eth+Base) | ✓ EIP-1967 | impl `0x08881c46…` |
| MapleCCIPReceiver (Eth) | ✓ EIP-1967 | impl `0x23CEF296…` |
| syrupUSDC/USDT BurnMintERC20 (Base/Arb/BNB) | ✗ **non-proxy** | plain CCT token (7475B, no 1967 impl — verified) |
| CCIP Token Pools | ✗ (standard Chainlink deploys) | |

Read EIP-1967 impl at `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`.

---

## 5. Detection invariants & gotchas

1. **SYRUP ≠ syrupUSDC bridge.** SYRUP = LayerZero OFT (`OFTSent`/`OFTReceived`); syrupUSDC/USDT = Chainlink CCIP (`Locked`/`Released` on Eth, `Burned`/`Minted` on remotes). Don't cross-wire them.
2. **The remote yield token IS a `BurnMintERC20`** — cross-chain receipt = `Transfer` from `0x0` (mint) by the CCIP pool; bridge-out = `Transfer` to `0x0` (burn). Watch the pool address as `sender`.
3. **SYRUP OFT shares one address `0x688A…9a2F` on Ethereum and Base** — disambiguate by chain ID. On Ethereum it's an **adapter** (locks canonical SYRUP `0x643C…2d66`); on Base it's the **token** itself.
4. **Only Base+Arbitrum (syrupUSDC) and BNB (syrupUSDT)** among the 6 non-Eth chains. **Optimism / Polygon / Avalanche have nothing** — any "Maple/Syrup" token there is an impostor.
5. **6-decimal yield tokens** (match the underlying USDC/USDT), unlike the 18-dec SYRUP governance token.
6. **eids are LayerZero's, not EVM chain IDs** — `dstEid=30184` means Base, not chain 8453.
7. **CCIP canonical = Ethereum lockRelease**; total remote supply is collateralized by the Ethereum lock. A mint on a remote without a corresponding Eth lock/CCIP message would be anomalous.

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Token events =====
TOPIC_TRANSFER        = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL        = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- LayerZero OFT v2 (SYRUP)
TOPIC_OFT_SENT        = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED    = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
-- Chainlink CCIP token pools (syrupUSDC/USDT)
TOPIC_CCIP_BURNED     = '\x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7'
TOPIC_CCIP_MINTED     = '\x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0'
TOPIC_CCIP_LOCKED     = '\x9f1ec8c880f76798e7b793325d625e9b60e4082a553c98f42b6cda368dd60008'
TOPIC_CCIP_RELEASED   = '\x2d87480f50083e2b2759522a8fdda59802650a8055e609a7772cf70c07748f52'

-- ===== SYRUP (LayerZero) =====
ETH_SYRUP_TOKEN       = '\x643c4e15d7d62ad0abec4a9bd4b001aa3ef52d66'
ETH_SYRUP_OFT_ADAPTER = '\x688aee022aa544f150678b8e5720b6b96a9e9a2f'
BASE_SYRUP_OFT        = '\x688aee022aa544f150678b8e5720b6b96a9e9a2f'   -- same addr, chain 8453
ETH_STSYRUP           = '\xc7e8b36e0766d9b04c93de68a9d47dd11f260b45'

-- ===== syrupUSDC (CCIP) =====
ETH_SYRUPUSDC         = '\x80ac24aa929eaf5013f6436cda2a7ba190f5cc0b'   -- canonical pool/token
ETH_SYRUPUSDC_POOL    = '\x20b79d39bd44deee4f89b1e9d0e3b945fde06491'   -- lockRelease CCIP pool
BASE_SYRUPUSDC        = '\x660975730059246a68521a3e2fbd4740173100f5'
BASE_SYRUPUSDC_POOL   = '\xa36955b2bc12aee77ff7519482d16c7b86dbe42a'
ARB_SYRUPUSDC         = '\x41ca7586cc1311807b4605fbb748a3b8862b42b5'
ARB_SYRUPUSDC_POOL    = '\x660975730059246a68521a3e2fbd4740173100f5'

-- ===== syrupUSDT (CCIP) =====
ETH_SYRUPUSDT         = '\x356b8d89c1e1239cbbb9de4815c39a1474d5ba7d'   -- canonical pool/token
ETH_SYRUPUSDT_POOL    = '\xde76a096c5eadddf97af3fe15ee49d32aeda9822'   -- lockRelease CCIP pool
BNB_SYRUPUSDT         = '\x8e9d4cea39299323fe8eda678cad449718556c4e'
BNB_SYRUPUSDT_POOL    = '\xeaa7e1f805747ae29d5618b568d1b044a8b37a01'

-- ===== CCIP deposit/redeem hook (Eth) =====
ETH_MAPLE_CCIP_RECEIVER = '\x02b6a75c5d1f430f0614dc5ac8ad5f9d35fba2c4'

-- LayerZero v2 eids: ETH 30101, BASE 30184, ARB 30110, OP 30111, POLYGON 30109, BNB 30102, AVAX 30106
```

---

## 7. Verification & sources

- **Addresses:** `MapleAddressRegistryETH.sol` / `MapleAddressRegistryBASEL2.sol`; the **Chainlink CCIP mainnet token directory** (authoritative for which chains hold syrupUSDC/USDT + their pools); explorer contract verification. Confirmed live via `eth_getCode`: Base syrupUSDC `0x6609…00f5` (7475B), Arb syrupUSDC `0x41CA…42b5` (7475B), BNB syrupUSDT `0x8E9d…6c4e` (7475B), Base SYRUP OFT `0x688A…9a2F` (2739B, impl `0x08881c46…`).
- **Live logs:** Base syrupUSDC token and Base SYRUP OFT both emit `Transfer`+`Approval` (confirmed 40k-block window). Optimism/Polygon/Avalanche: no Maple token entries in the CCIP registry or registries.
- **Topics:** ERC-20 `Transfer`/`Approval` confirmed live; OFT v2 + CCIP pool topics computed locally with keccak (standard LayerZero v2 / Chainlink CCT signatures).
- Explorers: [Basescan syrupUSDC](https://basescan.org/token/0x660975730059246A68521a3e2FBD4740173100f5) · [Arbiscan syrupUSDC](https://arbiscan.io/token/0x41CA7586cC1311807B4605fBB748a3B8862b42b5) · [BscScan syrupUSDT](https://bscscan.com/token/0x8E9d4cEa39299323FE8eda678cAD449718556c4e).
