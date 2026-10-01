# THORChain — Topics, Selectors, Addresses (Ethereum + Base + BNB + Avalanche; NOT Arbitrum, Optimism, Polygon, Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the THORNode API (`/thorchain/inbound_addresses`, `/thorchain/vaults/asgard`, `/thorchain/mimir`, `/thorchain/lastblock`, read at THORChain height 28,029,280), and the router sources and deployment records in `gitlab.com/thorchain/thornode` (`chain/evm/contracts/`, `chain/evm/deployment/`, `x/thorchain/router_upgrade_info.go`). Topics and selectors recomputed as `keccak256(sig)`; every address existence-checked with `eth_getCode`; sample receipts decoded on each live chain.
**Scope:** the THORChain Router contracts and the Asgard vault accounts on the four EVM chains that THORChain serves: Ethereum (1), Base (8453), BNB Smart Chain (56) and Avalanche C-Chain (43114). Arbitrum One (42161), OP Mainnet (10), Polygon PoS (137) and Robinhood Chain (4663) have no THORChain deployment. The other leg of most swaps is a non-EVM chain (Bitcoin, Dogecoin, Litecoin, XRP, Tron and others); this file covers only its link key. Topics and selectors are chain-agnostic; addresses are network-specific.

THORChain is a Cosmos-SDK chain that swaps native assets across chains. It has no bridge pool contract on an EVM chain. A small immutable **Router** takes the deposit, moves the funds on, and emits the memo. The funds sit in **Asgard vaults**: EOAs whose key the THORChain nodes hold as a threshold signature. One vault key gives the same EVM address on every EVM chain, so the five live vault EOAs are the same on Ethereum, Base, BNB and Avalanche.

Three facts a monitor must know before indexing:

1. **The memo carries the whole transfer.** `Deposit.memo` names the target asset and the destination address, for example `=:b:<bitcoin address>:<limit>/<interval>/<quantity>:<affiliate>:<bps>`. The payout memo is `OUT:<inbound tx hash>` or `REFUND:<inbound tx hash>`. That hash is the link key, and it is on chain on both sides.
2. **Routers and vaults rotate.** The live router of each chain is the `router` field of `/thorchain/inbound_addresses`. The live vaults are in `/thorchain/vaults/asgard`, and `?height=<H>` returns the set at any past THORChain height. On 2026-09-29, Ethereum and BNB still use V4.1 routers, while Base and Avalanche use the V6.1 router `0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4`.
3. **Two custody models.** The V4.1 router keeps the ERC-20 tokens itself and books a per-vault allowance. The V6.1 router keeps nothing: ERC-20 tokens go straight to the vault EOA. Native coin (ETH, BNB, AVAX) always goes to the vault EOA. A native deposit can also skip the router completely: THORChain watches native transfers whose `to` is a vault, with the memo in the transaction input. Such a deposit emits no router event.

---

## 0. Contract families & versions

| Contract | Chains | Role | State on 2026-09-29 |
|----------|--------|------|---------------------|
| **THORChain_Router V4.1** (`THORChain_RouterV4.sol`, header "Router Version: 4.1") | Ethereum `0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146`; BNB `0xb30ec53f98ff5947ede720d32ac2da7e52a5f56b` | Deposit and payout router. Holds ERC-20 tokens with a per-vault allowance. Forwards native coin to the vault. | **Live inbound router** on Ethereum and BNB |
| **THORChain_Router V6.1** (`THORChain_RouterV6.sol`, header "Router Version: 6.1") | `0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4` on Ethereum, Base, BNB, Avalanche (CREATE2 through the factory `0x4e59b44847b379578588920cA78FbF26c0B4956C`) | Stateless router: ERC-20 and native coin go straight to the vault. Adds `batchTransferOut`, `transferOutAndCallV2`, `TransferFailed`. | **Live inbound router** on Base and Avalanche. Configured upgrade target (`ethNewRouter`, `bscNewRouter`) on Ethereum and BNB, 0 events there |
| THORChain_Router V4.1 (Base) | Base `0x68208D99746b805a1Ae41421950A47b711E35681` | Previous Base router (`baseOldRouter`) | Replaced by V6.1; 0 events in the window |
| AvaxRouter (V4 event set) | Avalanche `0x8F66c4AE756BEbC49Ec8B81966DD8bba9f127549` | Previous Avalanche router (`avaxOldRouter`) | Replaced by V6.1; 0 events in the window |
| THORChain_RouterV4 (CREATE2 re-deploy, constructor RUNE `0x3155BA85D5F96b2d030a4966AF206230e46849cb`) | `0x33c630409883269bc281Dd40824562B066a70512` on Ethereum, Base, BNB, Avalanche | Deployed on 2025-08-05, never made inbound | 0 events in the window |
| THORChain_Router V6 deployments | `0xd5976E83F160B84BE90510b04C27657F240c7049` ("RouterV6"), `0xcAE4F95f7e2356044331E3080C8b65ae98B57c06` ("RouterV6_2"), `0xdEcDECdEc7577852D643f355544E7a4ddDB90659` (vanity) on the same four chains | Earlier V6 builds | Not inbound |
| THORChain_Router V1, V2, V3 | Ethereum `0x42A5Ed456650a09Dc10EBc6361A7480fDd61f27B` (V1), `0xC145990E84155416144C532E31f89B840Ca8c2cE` (V2), `0x3624525075b88B24ecc29CE226b0CEc1fFcB6976` (V3) | Historic Ethereum routers | Same four core events as V4.1; useful for back-fills only |
| Stagenet routers | V6.1 `0x0DC6108C9225Ce93Da589B4CE83c104b34693117` (four chains); old: Ethereum `0xB11a1735C2e3BCC5FC8c1d147fb64629d3d0caC5`, BNB `0x00335da4078f696b98ff619616f1c558e57b9e22`, Base `0xe36dcbf3c0284f756935811d9b9e80829d39bdc5`, Avalanche `0xd6a6c0b3bb4150a98a379811934e440989209db6` | Routers of THORChain's stagenet network, which runs on the same mainnet chains | Emit the same topics; exclude them from mainnet flow |
| **Asgard vaults** | Five EOAs, same address on all four chains (§3.2) | Hold the funds; sign payouts; call `transferOut` | Active since THORChain height 27,914,370 |

**THORChain chain names for the eight target chains.** THORChain names chains; it has no numeric chain ids.

| Target chain | THORChain chain | Memo short code | State |
|--------------|-----------------|-----------------|-------|
| Ethereum (1) | `ETH` | `e` = `ETH.ETH` | live |
| Base (8453) | `BASE` | `f` = `BASE.ETH` | live |
| BNB Smart Chain (56) | `BSC` | `s` = `BSC.BNB` | live |
| Avalanche C-Chain (43114) | `AVAX` | `a` = `AVAX.AVAX` | live |
| Polygon PoS (137) | `POL` in the THORNode EVM client docs; `p` = `POL.POL` in the memo docs | — | **Not live:** absent from `inbound_addresses` and `lastblock`; no router code on Polygon |
| Arbitrum One (42161), OP Mainnet (10), Robinhood Chain (4663) | — | — | not supported |

Other short codes: `b` BTC.BTC, `c` BCH.BCH, `d` DOGE.DOGE, `l` LTC.LTC, `g` GAIA.ATOM, `x` XRP.XRP, `tr` TRON.TRX, `r` THOR.RUNE. Solana (`SOL`) is listed but `halted: true`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Emitter = the Router of each chain (§3–§6). The four core events have the same signature in every router version from V1 to V6.1.

### 1.1 Router — deposit and payout events (all versions)

| topic0 | Event | Side |
|--------|-------|------|
| `0xef519b7eb82aaf6ac376a6df2d793843ebfd593de5f1a0601d3cc6ab49ebb395` | `Deposit(address indexed to, address indexed asset, uint256 amount, string memo)` | **Source leg.** `to` is the vault, not the user. `asset` = `0x0000000000000000000000000000000000000000` for the native coin. The destination is in `memo`. |
| `0xa9cd03aa3c1b4515114539cd53d22085129d495cb9e9f9af77864526240f1bf7` | `TransferOut(address indexed vault, address indexed to, address asset, uint256 amount, string memo)` | **Destination leg** (`memo` = `OUT:<hash>`) and **refund** (`memo` = `REFUND:<hash>`). `vault` is the signing vault EOA. |
| `0x8e5841bcd195b858d53b38bcf91b38d47f3bc800469b6812d35451ab619c6f6c` | `TransferOutAndCall(address indexed vault, address target, uint256 amount, address finalAsset, address to, uint256 amountOutMin, string memo)` | Destination leg through a DEX aggregator (V4.1 and V6.1). Native coin only. `to` is the final recipient; `target` is the aggregator. |
| `0x05b90458f953d3fcb2d7fb25616a2fddeca749d0c47cc5c9832d0266b5346eea` | `TransferAllowance(address indexed oldVault, address indexed newVault, address asset, uint256 amount, string memo)` | Vault migration at a churn (`memo` = `MIGRATE:<height>`). Not a user exit. On V4.1 it moves only the allowance (**status only**); on V6.1 it moves the ERC-20 from the old vault to the new vault. |

### 1.2 Router V1–V4.1 only

| topic0 | Event | Side |
|--------|-------|------|
| `0x281daef48d91e5cd3d32db0784f6af69cd8d8d2e8c612a3568dca51ded51e08f` | `VaultTransfer(address indexed oldVault, address indexed newVault, (address asset, uint256 amount)[] coins, string memo)` | `returnVaultAssets` batch between vaults. The ERC-20 part is an allowance move (**status only**); `msg.value` goes to the new vault. |

### 1.3 Router V6.1 only

| topic0 | Event | Side |
|--------|-------|------|
| `0xde470d7c2e9c3282cad476e5ed6f05f74d68839c406573048f2dee22a8c452c7` | `TransferOutAndCallV2(address indexed vault, address target, address fromAsset, uint256 fromAmount, address toAsset, address recipient, uint256 amountOutMin, string memo, bytes payload, string originAddress)` | Destination leg through an aggregator, with native or ERC-20 input. |
| `0xa6a370fa655359af5f69091e908830c250b8daffb80f6b578741423ae4c47ab1` | `TransferFailed(address indexed vault, address indexed to, address asset, uint256 amount, string memo)` | A native send that failed (the coin goes back to the vault) or an aggregator call that failed (the input goes straight to the recipient). Read it with the payout event of the same transaction. |

### 1.4 Value-movement companion (emitted by the token, not by THORChain)

| topic0 | Event | Side |
|--------|-------|------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 leg of a deposit or payout: user → router (V4.1) or user → vault (V6.1); router → recipient (V4.1) or vault → recipient (V6.1). |

**Topic collisions.** Maya Protocol's routers emit the same five V4 topics (see the `maya` reference). Other routers of the same design also emit them: on Ethereum, `Harbor_RouterV5` at `0x1f21d09c65bc8af92634dcd5a100b6d04f0c81c3` (verified source, "managed by XNode Vaults") emitted 181 `Deposit` and 100 `TransferOut` in the pinned window. Always filter on the router address.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Router V4.1 (Ethereum `0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146`, BNB `0xb30ec53f98ff5947ede720d32ac2da7e52a5f56b`, old Base and Avalanche routers)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x44bc937b` | `depositWithExpiry(address vault, address asset, uint256 amount, string memo, uint256 expiration)` | **User entry.** Payable. Reverts after `expiration`. Emits `Deposit`. |
| `0x1fece7b4` | `deposit(address vault, address asset, uint256 amount, string memo)` | Payable deposit without expiry. Native coin is sent to `vault` with `send`; ERC-20 stays in the router. Emits `Deposit`. |
| `0x574da717` | `transferOut(address to, address asset, uint256 amount, string memo)` | **Payout.** Called by a vault (`msg.sender` = vault). Native: `msg.value` sent to `to` with 2,300 gas; on failure it bounces back to the vault and `TransferOut` still fires. Emits `TransferOut`. |
| `0x4039fd4b` | `transferOutAndCall(address aggregator, address finalToken, address to, uint256 amountOutMin, string memo)` | Payout through an aggregator (`swapOut`). Native only. Emits `TransferOutAndCall`. |
| `0x1b738b32` | `transferAllowance(address router, address newVault, address asset, uint256 amount, string memo)` | Churn and router migration. `router` = this router: allowance move and `TransferAllowance`. Another router: `depositWithExpiry` into that router. |
| `0x2923e82e` | `returnVaultAssets(address router, address asgard, (address asset, uint256 amount)[] coins, string memo)` | Batch vault return. Emits `VaultTransfer` when `router` = this router. |
| `0x03b6a673` | `vaultAllowance(address vault, address token)` | View: the ERC-20 amount the router holds for `vault`. |
| `0x93e4eaa9` | `RUNE()` | View: `0x3155BA85D5F96b2d030a4966AF206230e46849cb` (legacy ERC-20 RUNE) on Ethereum. A RUNE deposit is burned. |

### 2.2 Router V6.1 (`0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4`)

`depositWithExpiry` (`0x44bc937b`), `transferOut` (`0x574da717`), `transferOutAndCall` (`0x4039fd4b`), `transferAllowance` (`0x1b738b32`) and `vaultAllowance` (`0x03b6a673`) keep their V4.1 selectors. There is no `deposit` and no `returnVaultAssets`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x44bc937b` | `depositWithExpiry(address vault, address asset, uint256 amount, string memo, uint256 expiration)` | **User entry.** `expiration = 0` means no expiry. ERC-20: `transferFrom(user, vault)`. Native: sent to the vault with 30,000 gas. Emits `Deposit`. |
| `0x574da717` | `transferOut(address to, address asset, uint256 amount, string memo)` | **Payout.** ERC-20: `transferFrom(vault, to)`, so the vault must approve the router. Emits `TransferOut`. |
| `0x4217e26f` | `batchTransferOut(address[] to, address[] assets, uint256[] amounts, string[] memos)` | One `TransferOut` per item, in one transaction. |
| `0x493ff6e2` | `transferOutAndCallV2((address target, address fromAsset, uint256 fromAmount, address toAsset, address recipient, uint256 amountOutMin, string memo, bytes payload, string originAddress) params)` | Aggregator payout with native or ERC-20 input. Emits `TransferOutAndCallV2` (and `TransferFailed` on a failed call). |
| `0x03b6a673` | `vaultAllowance(address vault, address token)` | View: returns `token.balanceOf(vault)`. |

### 2.3 Aggregator callbacks (the router calls them on the `target`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x48c314f4` | `swapOut(address finalToken, address to, uint256 amountOutMin)` | Called with `msg.value` by `transferOutAndCall`. |
| `0x486e77ba` | `swapOutV2(address fromAsset, uint256 fromAmount, address toAsset, address recipient, uint256 amountOutMin, bytes payload, string originAddress)` | Called by `transferOutAndCallV2`. |

---

## 3. Addresses — Ethereum (chain ID 1)

All verified via `eth_getCode` on 2026-09-29. The live router is from `/thorchain/inbound_addresses`; `ethOldRouter` / `ethNewRouter` are from `x/thorchain/router_upgrade_info.go`.

### 3.1 Routers

| Role | Address | One-liner |
|------|---------|-----------|
| **Router V4.1 (live inbound)** | `0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146` | 5,141 B. Holds the ERC-20 pool. `RUNE()` = `0x3155BA85D5F96b2d030a4966AF206230e46849cb`. |
| Router V6.1 (upgrade target) | `0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4` | 7,521 B. Deployed at block 23,253,245. 0 events in the window. |
| RouterV4 CREATE2 | `0x33c630409883269bc281Dd40824562B066a70512` | 5,630 B. Not inbound. |
| Router V6 | `0xd5976E83F160B84BE90510b04C27657F240c7049` | 7,432 B. Not inbound. |
| Router V6_2 | `0xcAE4F95f7e2356044331E3080C8b65ae98B57c06` | 7,432 B (same bytecode as V6). Not inbound. |
| Router V6 (vanity) | `0xdEcDECdEc7577852D643f355544E7a4ddDB90659` | 7,474 B. Not inbound. |
| Router V3 (historic) | `0x3624525075b88B24ecc29CE226b0CEc1fFcB6976` | 4,963 B. |
| Router V2 (historic) | `0xC145990E84155416144C532E31f89B840Ca8c2cE` | 8,558 B. |
| Router V1 (historic) | `0x42A5Ed456650a09Dc10EBc6361A7480fDd61f27B` | 7,787 B. |
| Stagenet router (old) | `0xB11a1735C2e3BCC5FC8c1d147fb64629d3d0caC5` | Same bytecode as the mainnet V4.1 router. Exclude. |
| Stagenet router V6.1 | `0x0DC6108C9225Ce93Da589B4CE83c104b34693117` | Same bytecode as V6.1. Exclude. |
| ETH.RUNE (legacy ERC-20) | `0x3155BA85D5F96b2d030a4966AF206230e46849cb` | 4,740 B. The V4 routers' constructor argument. |

### 3.2 Asgard vault EOAs (the same five addresses on Ethereum, Base, BNB and Avalanche)

From `/thorchain/vaults/asgard` at THORChain height 28,029,280; all five have `status: ActiveVault` since height 27,914,370. All are EOAs (no code); nonces read on 2026-09-29.

| Vault EOA | Nonce ETH | Nonce Base | Nonce BNB | Nonce AVAX |
|-----------|-----------|------------|-----------|------------|
| `0x0dac1fb302bc428d8dc272a511e7c2f0d2a1c128` | 2,211 | 77 | 329 | 77 |
| `0x0db14a0288f4637f60b46690f1971b756c58a47e` | 2,432 | 114 | 266 | 72 |
| `0x328763072e3ce351ec29318df971b534ca45a0f7` | 2,467 | 83 | 349 | 81 |
| `0x41c88d3c0eda3f4df0bb4e5d0f4c81cc0232902c` | 2,856 | 98 | 466 | 102 |
| `0x4feb8dd18f442ff67b521b5a5bc4c3824e3288ab` | 2,092 | 118 | 289 | 54 |

The previous set (active from height 27,870,660 until the churn at 27,914,370; read with `?height=27900000`) was `0x9bf432de925a039567b4ec376d5906349c10ef51`, `0xbf1b3f4929840439612c73a6a5664604be499a6b`, `0x770544401b68bf03f6d00b04608e0b6c15685268`, `0xb4e6afda6df6feccc5395a1da77de1b3d0d71145` and `0x63601bded74d96822409df986689f3caf0a3af03` (all EOAs on Ethereum). The inbound vault of the moment is `0x0dac1fb302bc428d8dc272a511e7c2f0d2a1c128` on all four chains.

---

## 4. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| **Router V6.1 (live inbound)** | `0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4` | Deployed at block 34,879,513. ERC-20 deposits go straight to the vault. |
| Router V4.1 (previous, `baseOldRouter`) | `0x68208D99746b805a1Ae41421950A47b711E35681` | 4,782 B. 0 events in the window. |
| RouterV4 CREATE2 / V6 / V6_2 / V6 vanity | `0x33c630409883269bc281Dd40824562B066a70512`, `0xd5976E83F160B84BE90510b04C27657F240c7049`, `0xcAE4F95f7e2356044331E3080C8b65ae98B57c06`, `0xdEcDECdEc7577852D643f355544E7a4ddDB90659` | Same bytecode as on Ethereum. Not inbound. |
| Stagenet routers | old `0xe36dcbf3c0284f756935811d9b9e80829d39bdc5` (same bytecode as `0x68208D99746b805a1Ae41421950A47b711E35681`); V6.1 `0x0DC6108C9225Ce93Da589B4CE83c104b34693117` | Exclude. |
| Asgard vaults | the five EOAs of §3.2 | Nonces 77–118. |

Not on Base: the V1–V4.1 Ethereum router addresses (`eth_getCode` = `0x`).

## 5. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| **Router V4.1 (live inbound, `bscOldRouter`)** | `0xb30ec53f98ff5947ede720d32ac2da7e52a5f56b` | 4,782 B; verified as `THORChain_Router` 4.1 (Sourcify full match). Holds the ERC-20 pool. |
| Router V6.1 (upgrade target, `bscNewRouter`) | `0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4` | 0 events in the window. |
| RouterV4 CREATE2 / V6 / V6_2 / V6 vanity | `0x33c630409883269bc281Dd40824562B066a70512`, `0xd5976E83F160B84BE90510b04C27657F240c7049`, `0xcAE4F95f7e2356044331E3080C8b65ae98B57c06`, `0xdEcDECdEc7577852D643f355544E7a4ddDB90659` | Not inbound. |
| Stagenet routers | old `0x00335da4078f696b98ff619616f1c558e57b9e22` (same bytecode as `0xb30ec53f98ff5947ede720d32ac2da7e52a5f56b`); V6.1 `0x0DC6108C9225Ce93Da589B4CE83c104b34693117` | Exclude. |
| Asgard vaults | the five EOAs of §3.2 | Nonces 266–466. |

## 6. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | One-liner |
|------|---------|-----------|
| **Router V6.1 (live inbound)** | `0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4` | Deployed at block 67,877,233. |
| AvaxRouter (previous, `avaxOldRouter`) | `0x8F66c4AE756BEbC49Ec8B81966DD8bba9f127549` | 6,752 B; verified as `AvaxRouter` (Sourcify exact match), V4 event set. 0 events in the window. |
| RouterV4 CREATE2 / V6 / V6_2 / V6 vanity | `0x33c630409883269bc281Dd40824562B066a70512`, `0xd5976E83F160B84BE90510b04C27657F240c7049`, `0xcAE4F95f7e2356044331E3080C8b65ae98B57c06`, `0xdEcDECdEc7577852D643f355544E7a4ddDB90659` | Not inbound. |
| Stagenet routers | old `0xd6a6c0b3bb4150a98a379811934e440989209db6` (same bytecode as `0x8F66c4AE756BEbC49Ec8B81966DD8bba9f127549`); V6.1 `0x0DC6108C9225Ce93Da589B4CE83c104b34693117` | Exclude. |
| Asgard vaults | the five EOAs of §3.2 | Nonces 54–102. |

---

## 7. Cross-chain summary

| Chain | ID | Live router | V6.1 `0x00dc6100103BC402d490aEE3F9a5560cBd91f1d4` | Other THORChain routers | Vault EOAs | Window `Deposit` / `TransferOut` |
|-------|----|-------------|---------------------------------------------------|-------------------------|------------|-----------------------------------|
| Ethereum | 1 | V4.1 `0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146` | deployed, upgrade target | V1, V2, V3, RouterV4 CREATE2, V6 ×3 | 5 (active) | 506 / 1,028 |
| Base | 8453 | V6.1 | **live** | old V4.1 `0x68208D99746b805a1Ae41421950A47b711E35681`, RouterV4 CREATE2, V6 ×3 | 5 | 40 / 26 |
| BNB Smart Chain | 56 | V4.1 `0xb30ec53f98ff5947ede720d32ac2da7e52a5f56b` | deployed, upgrade target | RouterV4 CREATE2, V6 ×3 | 5 | 56 / 91 |
| Avalanche C-Chain | 43114 | V6.1 | **live** | AvaxRouter `0x8F66c4AE756BEbC49Ec8B81966DD8bba9f127549`, RouterV4 CREATE2, V6 ×3 | 5 | 39 / 19 |
| Arbitrum One | 42161 | — | `0x` | none (`0x` at every address of this file) | nonce 0 | 0 / 0 (any emitter) |
| OP Mainnet | 10 | — | `0x` | none | nonce 0 | 0 / 0 |
| Polygon PoS | 137 | — | `0x` | none | nonce 0 | 0 / 0 |
| Robinhood Chain | 4663 | — | `0x` | none | nonce 0 | 0 / 0 |

The V6.1 router, the RouterV4 CREATE2 copy and the three V6 builds share one address on all four chains (CREATE2 through `0x4e59b44847b379578588920cA78FbF26c0B4956C`). The V4.1 routers do not: key them on `(chain, address)`.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| All routers (V1–V6.1, AvaxRouter, stagenet) | **Immutable**, no proxy | EIP-1967 implementation slot empty; not an EIP-1167 clone; no `owner` or admin function in the source | None on chain. A router change is a new deployment plus the THORChain mimir key `MimirUpgradeContract<CHAIN>`; funds then move to the new router. |
| Asgard vaults | EOAs (TSS keys) | `eth_getCode` = `0x`, nonce > 0 | Rotated by THORChain at each churn (`CHURNINTERVAL` = 43,200 THORChain blocks); `HALTCHURNING` = 1 on 2026-09-29 |

Admin control lives on THORChain, not in the EVM contracts: mimir keys such as `HALT<CHAIN>CHAIN`, `HALT<CHAIN>TRADING`, `HALTSIGNING<CHAIN>` and `HALTCHURNING` (read them at `/thorchain/mimir`). On chain, a router change shows as a new `router` value in `/thorchain/inbound_addresses`, and as migration transfers from the old router or the old vaults into the new ones.

---

## 9. Detection invariants & gotchas

1. **Filter on the router address.** The topics are shared with Maya's routers, with `Harbor_RouterV5` `0x1f21d09c65bc8af92634dcd5a100b6d04f0c81c3` on Ethereum, and with THORChain's own stagenet routers.
2. **`Deposit.to` is the vault.** The destination chain and address are in `memo`. The depositor is not in the event: take it from `tx.from` or from the ERC-20 `Transfer.from`. Aggregators (for example the Rango diamond `0x69460570c93f9de5e2edbc3052bf10125f0ca22d`) often call the router, so `tx.to` can be the aggregator.
3. **Link key = the memo hash.** A payout memo is `OUT:<HASH>` or `REFUND:<HASH>`: 64 upper-case hex characters without `0x`. For an EVM source, lower-case it and add `0x` to get the source transaction hash. For a Bitcoin source it is the txid. On a non-EVM destination the same `OUT:` memo is in the payout transaction (the `OP_RETURN` on Bitcoin). In the window, the Ethereum router's 1,028 `TransferOut` held 1,017 `OUT:` and 11 `REFUND:` memos; Base's 26 held 25 `OUT:` and 1 `REFUND:`.
4. **Join one-to-many.** An expired limit swap refunds its remaining funds, so one inbound hash can have both an `OUT:` and a `REFUND:` payout. `batchTransferOut` (V6.1) puts several payouts in one transaction.
5. **Native deposits can have no event.** THORChain watches native transfers whose `to` is a vault EOA, with the memo in the transaction input. Watch plain native transfers into the vault EOAs of §3.2 as well as the router.
6. **Custody by router version.** V4.1 (Ethereum, BNB): the ERC-20 `Transfer` goes user → router, and the payout goes router → recipient; the router's token balance is the ERC-20 pool. V6.1 (Base, Avalanche): user → vault EOA and vault → recipient (`transferFrom`, the router is only the spender). Verified in sample receipts on each chain (§11).
7. **A V4.1 `TransferOut` does not prove delivery of native coin.** If `send` to the recipient fails, the coin goes back to the vault and the event still shows the full amount. V6.1 emits `TransferFailed` in that case.
8. **Not every `Deposit` is an exit.** `=` / `SWAP` / `s` is a swap; `=<` is a limit swap; `TRADE+` and `SECURE+` credit a THORChain account (no payout); `+` adds liquidity; `DONATE`, `BOND` and `REFERENCE` (memoless registration) are internal. In the window, Ethereum's 506 `Deposit` memos began with `=` (430), `TRADE+` (73), `=<` (2) and `trade+` (1).
9. **Short codes differ from Maya.** THORChain `a` = AVAX.AVAX, `d` = DOGE.DOGE, `x` = XRP.XRP. Maya uses the same letters for ARB.ETH, DASH.DASH and XRD.XRD.
10. **Pending router upgrades.** `router_upgrade_info.go` names V6.1 as the new router for Ethereum and BNB, but the inbound routers are still V4.1. Watch both addresses. When the upgrade runs, the V4.1 router's tokens move through `transferAllowance(newRouter, ...)`, which calls `depositWithExpiry` on the new router: that `Deposit` is a migration, not a user deposit.
11. **Churn migrations are not exits.** At a churn, `TransferAllowance` (memo `MIGRATE:<height>`) and native transfers between vault EOAs move the whole pool. Load the vault set of each height before you classify a vault-to-vault transfer.
12. **Deployed ≠ live.** The RouterV4 CREATE2 copy, the V6 builds and V6.1 on Ethereum and BNB have code but emitted 0 events in the window. Key alerts on the `router` field of the API, and keep the others for anomaly checks.
13. **Large-transfer and drain triggers.** Key on `TransferOut.amount` per `asset` at the live routers, on native outflows from the vault EOAs that do not go through a router, and (V4.1) on drops of the router's ERC-20 balance.
14. **Base and BNB share the 4,782-byte size, not the code.** `0x68208D99746b805a1Ae41421950A47b711E35681` (Base) and `0xb30ec53f98ff5947ede720d32ac2da7e52a5f56b` (BNB) have different code hashes; identify routers by address.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Router topics (all versions unless noted) =====
TOPIC_DEPOSIT                    = '\xef519b7eb82aaf6ac376a6df2d793843ebfd593de5f1a0601d3cc6ab49ebb395'
TOPIC_TRANSFER_OUT               = '\xa9cd03aa3c1b4515114539cd53d22085129d495cb9e9f9af77864526240f1bf7'
TOPIC_TRANSFER_OUT_AND_CALL      = '\x8e5841bcd195b858d53b38bcf91b38d47f3bc800469b6812d35451ab619c6f6c'
TOPIC_TRANSFER_ALLOWANCE         = '\x05b90458f953d3fcb2d7fb25616a2fddeca749d0c47cc5c9832d0266b5346eea'
TOPIC_VAULT_TRANSFER             = '\x281daef48d91e5cd3d32db0784f6af69cd8d8d2e8c612a3568dca51ded51e08f'   -- V1-V4.1
TOPIC_TRANSFER_OUT_AND_CALL_V2   = '\xde470d7c2e9c3282cad476e5ed6f05f74d68839c406573048f2dee22a8c452c7'   -- V6.1
TOPIC_TRANSFER_FAILED            = '\xa6a370fa655359af5f69091e908830c250b8daffb80f6b578741423ae4c47ab1'   -- V6.1
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_DEPOSIT_WITH_EXPIRY          = '\x44bc937b'
SEL_DEPOSIT                      = '\x1fece7b4'   -- V4.1 only
SEL_TRANSFER_OUT                 = '\x574da717'
SEL_BATCH_TRANSFER_OUT           = '\x4217e26f'   -- V6.1
SEL_TRANSFER_OUT_AND_CALL        = '\x4039fd4b'
SEL_TRANSFER_OUT_AND_CALL_V2     = '\x493ff6e2'   -- V6.1
SEL_TRANSFER_ALLOWANCE           = '\x1b738b32'
SEL_RETURN_VAULT_ASSETS          = '\x2923e82e'   -- V4.1 only
SEL_VAULT_ALLOWANCE              = '\x03b6a673'
SEL_RUNE                         = '\x93e4eaa9'
SEL_SWAP_OUT                     = '\x48c314f4'
SEL_SWAP_OUT_V2                  = '\x486e77ba'

-- ===== Ethereum (1) =====
ETH_ROUTER_V4_1                  = '\xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146'   -- live inbound
ETH_ROUTER_V6_1                  = '\x00dc6100103bc402d490aee3f9a5560cbd91f1d4'   -- upgrade target
ETH_ROUTER_V4_CREATE2            = '\x33c630409883269bc281dd40824562b066a70512'
ETH_ROUTER_V6                    = '\xd5976e83f160b84be90510b04c27657f240c7049'
ETH_ROUTER_V6_2                  = '\xcae4f95f7e2356044331e3080c8b65ae98b57c06'
ETH_ROUTER_V6_VANITY             = '\xdecdecdec7577852d643f355544e7a4dddb90659'
ETH_ROUTER_V3                    = '\x3624525075b88b24ecc29ce226b0cec1ffcb6976'
ETH_ROUTER_V2                    = '\xc145990e84155416144c532e31f89b840ca8c2ce'
ETH_ROUTER_V1                    = '\x42a5ed456650a09dc10ebc6361a7480fdd61f27b'
ETH_STAGENET_ROUTER_OLD          = '\xb11a1735c2e3bcc5fc8c1d147fb64629d3d0cac5'
ETH_STAGENET_ROUTER_V6_1         = '\x0dc6108c9225ce93da589b4ce83c104b34693117'
ETH_RUNE_ERC20                   = '\x3155ba85d5f96b2d030a4966af206230e46849cb'
-- Asgard vault EOAs: the same five addresses on ETH, BASE, BNB and AVAX
ETH_ASGARD_VAULT_1_EOA           = '\x0dac1fb302bc428d8dc272a511e7c2f0d2a1c128'
ETH_ASGARD_VAULT_2_EOA           = '\x0db14a0288f4637f60b46690f1971b756c58a47e'
ETH_ASGARD_VAULT_3_EOA           = '\x328763072e3ce351ec29318df971b534ca45a0f7'
ETH_ASGARD_VAULT_4_EOA           = '\x41c88d3c0eda3f4df0bb4e5d0f4c81cc0232902c'
ETH_ASGARD_VAULT_5_EOA           = '\x4feb8dd18f442ff67b521b5a5bc4c3824e3288ab'

-- ===== Base (8453) =====
BASE_ROUTER_V6_1                 = '\x00dc6100103bc402d490aee3f9a5560cbd91f1d4'   -- live inbound
BASE_ROUTER_V4_1_OLD             = '\x68208d99746b805a1ae41421950a47b711e35681'
BASE_STAGENET_ROUTER_OLD         = '\xe36dcbf3c0284f756935811d9b9e80829d39bdc5'
BASE_STAGENET_ROUTER_V6_1        = '\x0dc6108c9225ce93da589b4ce83c104b34693117'

-- ===== BNB Smart Chain (56) =====
BNB_ROUTER_V4_1                  = '\xb30ec53f98ff5947ede720d32ac2da7e52a5f56b'   -- live inbound
BNB_ROUTER_V6_1                  = '\x00dc6100103bc402d490aee3f9a5560cbd91f1d4'   -- upgrade target
BNB_STAGENET_ROUTER_OLD          = '\x00335da4078f696b98ff619616f1c558e57b9e22'
BNB_STAGENET_ROUTER_V6_1         = '\x0dc6108c9225ce93da589b4ce83c104b34693117'

-- ===== Avalanche C-Chain (43114) =====
AVAX_ROUTER_V6_1                 = '\x00dc6100103bc402d490aee3f9a5560cbd91f1d4'   -- live inbound
AVAX_ROUTER_OLD                  = '\x8f66c4ae756bebc49ec8b81966dd8bba9f127549'
AVAX_STAGENET_ROUTER_OLD         = '\xd6a6c0b3bb4150a98a379811934e440989209db6'
AVAX_STAGENET_ROUTER_V6_1        = '\x0dc6108c9225ce93da589b4ce83c104b34693117'

-- Same-topic router of another protocol (exclude): Harbor_RouterV5 on Ethereum
ETH_HARBOR_ROUTER_V5             = '\x1f21d09c65bc8af92634dcd5a100b6d04f0c81c3'
-- Arbitrum (42161), OP Mainnet (10), Polygon (137), Robinhood Chain (4663): no THORChain contract
```

---

## 11. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` / `[0:4]` from `THORChain_RouterV4.sol` (4.1) and `THORChain_RouterV6.sol` (6.1) in `gitlab.com/thorchain/thornode` `chain/evm/contracts/`, with `Coin` written as `(address,uint256)` and the V6.1 `Params` struct as a 9-field tuple. The verified sources of the V1, V2 and V3 Ethereum routers (Blockscout) and of the BNB router (Sourcify, "Router Version: 4.1") declare the same `Deposit`, `TransferOut`, `TransferAllowance` and `VaultTransfer`.
- **Addresses:** live routers and vaults from `/thorchain/inbound_addresses` and `/thorchain/vaults/asgard` (THORChain height 28,029,280); old and new routers from `x/thorchain/router_upgrade_info.go` (mainnet) and `router_upgrade_info_stagenet.go`; CREATE2 deployments from `chain/evm/deployment/routerv4/*.json` and `routerv6/*.md`. Every address was checked with `eth_getCode` on all eight chains; the vaults returned no code and nonces > 0 on Ethereum, Base, BNB and Avalanche, and nonce 0 elsewhere. The "RouterV4 (Legacy)" table of `chain/evm/deployment/README.md` gives a value with only 39 hex digits; it is a typo of the V3 router `0x3624525075b88B24ecc29CE226b0CEc1fFcB6976`, and that README also still calls `0xd5976E83F160B84BE90510b04C27657F240c7049` the current router. The live API and `router_upgrade_info.go` win over it.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `Deposit` / `TransferOut` at the live routers: Ethereum 506 / 1,028, Base 40 / 26, BNB 56 / 91, Avalanche 39 / 19. `TransferOutAndCall`, `TransferOutAndCallV2`, `TransferFailed`, `TransferAllowance` and `VaultTransfer`: 0 on every chain. All seven topics at V6.1 on Ethereum and BNB, at the old Base router and at the old Avalanche router: 0. Arbitrum, OP Mainnet, Polygon and Robinhood Chain: 0 logs of these topics from any emitter. A 0 is a measurement of this window only.
- **Sample receipts (value movement confirmed):** Ethereum native deposit `0x99d9d33249e19a6154f3e5020b4062d3ccffbad5c395af92c4665c62a80a043f` (`depositWithExpiry`, 0.00065 ETH to vault `0x0db14a0288f4637f60b46690f1971b756c58a47e`, memo `=:s:...`); Ethereum USDC deposit `0xbf5524a329d798536c1b3a25aec53a88fcae71705f56bda485f4626eabf847af` (USDC user → router); Ethereum payout `0x05e6e2c0cafd99241b46d9091b9106ce1ec406bcb56ac263b13955d735d2ff56` (vault `0x41c88d3c0eda3f4df0bb4e5d0f4c81cc0232902c` calls `transferOut`, memo `OUT:2641CB74A6356FA68256BACC219F77951965AB23ECA05C8364D3470AAA75ADAC`); Ethereum refund `0x2d6339620fd8d6ed6765bb6922e2214350c3d85b76a5ecefd8b22e8cb2f420f3`; Base USDC deposit `0x415df96352257e26ec7238c89c275805e0387e713835e1578e040530d4bc7950` (USDC user → vault EOA); Base USDC payout `0x3d0cef58c53f03f14cd43bcafa0b5bdff8e865227490838eefbc704432e09b6d` (USDC vault → recipient); BNB deposit `0x4888ef1bbb7796458d6d0f96e73dce0999cd4f5f7b1bb57f57b9bbe95f6ba8c8` (BUSD user → router) and payout `0x45c7d75d50feb1f5d1ab395b801d74bb4eda827aa0e9e471f3da9ed33e46dca9` (router → recipient); Avalanche deposit `0x1030f0cd506c2ee9c9b1df860c9d28f7af3ec082a6b7d20ba83219b125bb97ba` and payout `0x2c62722ad171a165b09b234500ab5af53717fe9a23497c2fe6dac2081e846f77`.
- **Not measured:** the share of native deposits that skip the router (it needs a scan of every native transfer to the vaults). No doc or source defines a Polygon router, so Polygon is absent, not unverified.

Authoritative sources:
- THORNode repository — [chain/evm](https://gitlab.com/thorchain/thornode/-/tree/develop/chain/evm) (`contracts/THORChain_RouterV4.sol`, `contracts/THORChain_RouterV6.sol`, `deployment/`), [x/thorchain/router_upgrade_info.go](https://gitlab.com/thorchain/thornode/-/blob/develop/x/thorchain/router_upgrade_info.go), docs `docs/concepts/memos.md`, `docs/concepts/memo-length-reduction.md`, `docs/chain-clients/evm.md`, `docs/concepts/sending-transactions.md`
- THORNode API — [inbound_addresses](https://gateway.liquify.com/chain/thorchain_api/thorchain/inbound_addresses) · [vaults/asgard](https://gateway.liquify.com/chain/thorchain_api/thorchain/vaults/asgard) · [mimir](https://gateway.liquify.com/chain/thorchain_api/thorchain/mimir) · [lastblock](https://gateway.liquify.com/chain/thorchain_api/thorchain/lastblock)
- Dev docs — [Upgrade Router](https://dev.thorchain.org/upgrade_router.html) · [Sending Transactions](https://dev.thorchain.org/concepts/sending-transactions.html)
- Explorers — [Etherscan router V4.1](https://etherscan.io/address/0xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146) · [Basescan old router](https://basescan.org/address/0x68208d99746b805a1ae41421950a47b711e35681) · [Blockscout (Ethereum, Base)](https://eth.blockscout.com) · [Sourcify](https://sourcify.dev) (BNB router, Avalanche old router)
