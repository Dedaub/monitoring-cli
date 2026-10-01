# Meson — Topics, Selectors, Addresses (all eight chains: Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the Sourcify-verified `UpgradableMeson` implementation on Base (`0x03650533d2a35847c007f25bc630f468905f6241`, solc 0.8.28), the Sourcify-verified `ProxyToMeson` on Ethereum, the official Meson relayer chain list (`https://relayer.meson.fi/api/v1/list`) and the Meson Solidity docs.
**Scope:** the single Meson contract (one UUPS proxy at `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` on every chain), which is both the source-side escrow (`MesonSwap`) and the destination-side LP pool (`MesonPools`). Topics and selectors are chain-agnostic. Addresses are network-specific, but this one proxy address is the same on all eight target chains.

Meson is an atomic-swap style bridge for stablecoins, ETH, BNB, BTC and a few other assets. Every swap is described by one 256-bit integer, `encodedSwap`. The same `encodedSwap` is `topic1` of the source event and of the destination event, so it is an exact on-chain link key on both sides. The swap amount, the LP fee, the expiry, both Meson chain codes and both token indexes are packed inside it.

The proxy is EIP-1967 UUPS. Each chain has its own implementation, because the chain's own Meson code (`SHORT_COIN_TYPE`) is compiled in as a constant. One EOA (`_owner`, the same on all chains) can upgrade every proxy.

---

## 0. Contract families & flow

| Component | Contract | Role |
|-----------|----------|------|
| Source leg | `MesonSwap` (inside the proxy) | Takes the user's tokens. Emits `SwapPosted` (two-step flow) or `SwapExecuted` (one-step flow). |
| Destination leg | `MesonPools` (inside the proxy) | LP locks and releases funds to the recipient. Emits `SwapLocked` then `SwapReleased`, or `SwapReleased` alone (`directRelease`). |
| Admin | `MesonManager` / `UpgradableMeson` | Owner adds tokens, moves service fees, upgrades. Premium manager signs fee-waived swaps. |
| Helper (not deployed at a fixed address) | `TransferToMesonContract` | Per-destination deposit contract made by CREATE2. Its `transferToMeson(uint256)` calls `simpleExecuteSwap`. |

Flow of one swap:

1. **Source (one-step, the current flow):** `simpleExecuteSwap(encodedSwap)` or `directExecuteSwap` pulls the tokens from the user (ERC-20 `Transfer` user to proxy, or native value in `msg.value`) and emits `SwapExecuted(encodedSwap)`.
2. **Source (two-step, older flow):** `postSwap` / `postSwapWithSignature` pulls the tokens and emits `SwapPosted`. An LP may `bondSwap` (`SwapBonded`). After the release, the LP calls `executeSwap` to claim the escrow, which emits `SwapExecuted` again (no user deposit in that transaction).
3. **Destination:** an LP calls `lockSwap` (`SwapLocked`) and later `release`, or calls `directRelease` in one step. Both emit `SwapReleased(encodedSwap)`. The pool pays the recipient: ERC-20 `Transfer` proxy to recipient, or a native internal transfer.
4. **Refund and expiry:** after `expireTs`, the initiator calls `cancelSwap` (or the premium manager calls `cancelSwapTo`) on the source. It emits `SwapCancelled`. On the destination, an unreleased lock can be reverted with `unlock` (`SwapUnlocked`), which moves no tokens out.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Swap lifecycle (`IMesonSwapEvents`, `IMesonPoolsEvents`)

| topic0 | Event |
|--------|-------|
| `0x8d92c805c252261fcfff21ee60740eb8a38922469a7e6ee396976d57c22fc1c9` | `SwapExecuted(uint256 indexed encodedSwap)` |
| `0x5ce4019f772fda6cb703b26bce3ec3006eb36b73f1d3a0eb441213317d9f5e9d` | `SwapPosted(uint256 indexed encodedSwap)` |
| `0x60a99b51ae498c44acbbe11031aed2a06a32be66d2122e6e2a7a16c087865cc9` | `SwapBonded(uint256 indexed encodedSwap)` |
| `0xf6b6b4f7a13f02512c1b3aa8dcc4a07d7775a6a4becbd439efcbd37c5408e67f` | `SwapCancelled(uint256 indexed encodedSwap)` |
| `0xbfb879c34323c5601fafe832c3a8a1e31e12c288695838726ddeada86034edb4` | `SwapLocked(uint256 indexed encodedSwap)` |
| `0xac7d23c4f0137a4cc35b0e4b4bc8061ea6cb65805e87ceb0a77ca0c85814858c` | `SwapUnlocked(uint256 indexed encodedSwap)` |
| `0xfa628b578e095243f0544bfad9255f49d79d03a5bbf6c85875d05a215e247ad2` | `SwapReleased(uint256 indexed encodedSwap)` |

Side of each event: `SwapExecuted` = source deposit (one-step) **or** LP claim (two-step); `SwapPosted` = source deposit (two-step); `SwapReleased` = destination payout; `SwapCancelled` = source refund. `SwapBonded`, `SwapLocked` and `SwapUnlocked` are status-only: no tokens leave or enter the contract.

### 1.2 LP pools (status and LP liquidity)

| topic0 | Event |
|--------|-------|
| `0xb8d9c35a714d4e29eaf036b9bf8183a093c5573ac809453b4e8434e25c9126d2` | `PoolRegistered(uint40 indexed poolIndex, address owner)` |
| `0x7d7d1df74ef3a6434d8d63dc0a25d13d5fa94dbe738c38a3cce26e6f892e2a76` | `PoolDeposited(uint48 indexed poolTokenIndex, uint256 amount)` |
| `0x34c3d1c46f89307d63d8818fcc5c2a9c07a5f7a01ea4319bfba1899f40c6f400` | `PoolWithdrawn(uint48 indexed poolTokenIndex, uint256 amount)` |
| `0xd49cde4f679ccef3d23ff07aae4f6845e1c661e23e9fe6a54da26f0723fb695f` | `PoolAuthorizedAddrAdded(uint40 indexed poolIndex, address addr)` |
| `0x475b83c893df40ee19fd0783cf26478cdb58478dff65bb62560e1e7c36e0f22f` | `PoolAuthorizedAddrRemoved(uint40 indexed poolIndex, address addr)` |
| `0xc94089e0c0b1b79fdecc6e64fb759cdd390590a15c7e50d281e681ea8273261c` | `PoolOwnerTransferred(uint40 indexed poolIndex, address prevOwner, address newOwner)` |

`poolTokenIndex` = `tokenIndex:uint8 | poolIndex:uint40`. `PoolWithdrawn` is an LP taking liquidity out of the pool (a value movement, but not a bridge transfer).

### 1.3 Admin and proxy

| topic0 | Event |
|--------|-------|
| `0x8934ce4adea8d9ce0d714d2c22b86790e41b7731c84b926fbbdc1d40ff6533c9` | `OwnerTransferred(address indexed prevOwner, address indexed newOwner)` |
| `0x4798f31ad3d0ccde6359edf35fc39b882e4e1cff2968ca749b72074d373db27a` | `PremiumManagerTransferred(address indexed prevPremiumManager, address indexed newPremiumManager)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e` | `BeaconUpgraded(address indexed beacon)` |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Source side (`MesonSwap`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x264849e7` | `simpleExecuteSwap(uint256 encodedSwap)` | Payable. One-step deposit from `msg.sender`. Emits `SwapExecuted`. The main source entrypoint today. |
| `0xc8173c44` | `directExecuteSwap(uint256 encodedSwap, bytes32 r, bytes32 yParityAndS, address initiator, address recipient)` | Payable. One-step deposit from `initiator` with a release signature. Emits `SwapExecuted`. |
| `0x6f9b41fd` | `postSwap(uint256 encodedSwap, address initiator, uint40 poolIndex)` | Payable. Two-step deposit. Emits `SwapPosted`. |
| `0x0ffad9c0` | `postSwapWithSignature(uint256 encodedSwap, bytes32 r, bytes32 yParityAndS, address initiator, uint40 poolIndex)` | Two-step deposit pulled from `initiator`. Emits `SwapPosted`. |
| `0xdecf2a48` | `postSwapFromInitiator(uint256 encodedSwap, uint200 postingValue)` | Deprecated wrapper of `postSwap`. |
| `0x35eff30f` | `bondSwap(uint256 encodedSwap, uint40 poolIndex)` | LP bonds a posted swap. Emits `SwapBonded`. |
| `0x827c87cc` | `executeSwap(uint256 encodedSwap, bytes32 r, bytes32 yParityAndS, address recipient, bool depositToPool)` | LP claims the escrow of a posted swap. Emits `SwapExecuted`. Tokens go to the pool owner, or stay as pool balance. |
| `0x54d6a2b7` | `cancelSwap(uint256 encodedSwap)` | After expiry. Refunds the initiator. Emits `SwapCancelled`. |
| `0x16f35d23` | `cancelSwapTo(uint256 encodedSwap, address recipient)` | Premium manager only. Refund to any `recipient`. Emits `SwapCancelled`. |
| `0x1e2a6075` | `getPostedSwap(uint256 encodedSwap)` | View: `(address initiator, address poolOwner, bool exist)`. |

### 2.2 Destination side (`MesonPools`) and LP management

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x58d9b4e1` | `lockSwap(uint256 encodedSwap, address initiator)` | LP reserves pool funds. Emits `SwapLocked`. |
| `0x515147ab` | `lock(uint256 encodedSwap, bytes32 r, bytes32 yParityAndS, address initiator)` | Deprecated wrapper of `lockSwap`. |
| `0xf1d2ec1d` | `unlock(uint256 encodedSwap, address initiator)` | After the lock period. Emits `SwapUnlocked`. |
| `0xa5c9c66c` | `release(uint256 encodedSwap, bytes32 r, bytes32 yParityAndS, address initiator, address recipient)` | Pays the recipient of a locked swap. `tx.origin` must be the caller. Emits `SwapReleased`. |
| `0xab115fd8` | `directRelease(uint256 encodedSwap, bytes32 r, bytes32 yParityAndS, address initiator, address recipient)` | Lock and release in one call by an authorized LP address. Emits `SwapReleased`. The main destination entrypoint today. |
| `0x741c8e2d` | `directSwap(uint256 encodedSwap, address recipient, bytes32 r, bytes32 yParityAndS)` | Same-chain swap (in-chain = out-chain) signed by the premium manager. Emits `SwapReleased` only. |
| `0x60a2da98` | `getLockedSwap(uint256 encodedSwap, address initiator)` | View: `(address poolOwner, uint40 until)`. |
| `0x8f487dc9` | `depositAndRegister(uint256 amount, uint48 poolTokenIndex)` | Payable. New LP pool. Emits `PoolRegistered`, `PoolDeposited`. |
| `0x37b90a4f` | `deposit(uint256 amount, uint48 poolTokenIndex)` | Payable. LP adds liquidity. Emits `PoolDeposited`. |
| `0xce7f79b9` | `withdraw(uint256 amount, uint48 poolTokenIndex)` | Pool owner removes liquidity. Emits `PoolWithdrawn`. |
| `0xff22f272` | `addAuthorizedAddr(address addr)` | Emits `PoolAuthorizedAddrAdded`. |
| `0x051119f5` | `removeAuthorizedAddr(address addr)` | Emits `PoolAuthorizedAddrRemoved`. |
| `0x30f00f3a` | `transferPoolOwner(address addr)` | Emits `PoolOwnerTransferred`. |

### 2.3 Admin, upgrade and views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd4f82322` | `addSupportToken(address token, uint8 index)` | Owner only. |
| `0xc11d9ecb` | `addMultipleSupportedTokens(address[] tokens, uint8[] indexes)` | Owner only. |
| `0xcb4f999b` | `removeSupportToken(uint8 index)` | Owner only. |
| `0x7234cd95` | `withdrawServiceFee(uint8 tokenIndex, uint256 amount, uint40 toPoolIndex)` | Owner only. Moves service-fee balance (pool 0) to a pool. |
| `0xeaf250b5` | `adjustToPool(uint8 tokenIndex, uint256 amount, uint40 toPoolIndex)` | Owner only. Credits a pool balance with no token movement. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner only. Emits `OwnerTransferred`. |
| `0xb805f321` | `transferPremiumManager(address newPremiumManager)` | Premium manager only. |
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | UUPS. Owner only (`_authorizeUpgrade`). Emits `Upgraded`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | UUPS. Owner only. |
| `0x485cc955` | `initialize(address owner, address premiumManager)` | Run once by the proxy constructor. |
| `0x52d1902d` | `proxiableUUID()` | UUPS marker (reverts through the proxy). |
| `0xeba7fb77` | `getShortCoinType()` | View: `bytes2`, the chain's own Meson code (read live, §4). |
| `0xff378719` | `tokenForIndex(uint8)` | View: token address of an index (`0x0000000000000000000000000000000000000001` = native coin). |
| `0x2335093c` | `indexOfToken(address)` | View. |
| `0xd3c7c2c7` | `getSupportedTokens()` | View: `(address[] tokens, uint8[] indexes)`. |
| `0x7fe0282b` | `poolOfAuthorizedAddr(address)` | View. |
| `0x89a734c0` | `ownerOfPool(uint40)` | View. |
| `0xd3e95ea4` | `poolTokenBalance(address token, address addr)` | View. |
| `0x8b0a7765` | `serviceFeeCollected(uint8 tokenIndex)` | View. |

### 2.4 Integration helpers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xea78d39a` | `transferToMeson(uint256 encodedSwap)` | `TransferToMesonContract`: forwards its own balance into `simpleExecuteSwap`. |
| `0x0e9a72a1` | `deploy(address mesonAddress, uint16 destChain, bytes32 destAddr, address via)` | `TransferToMesonFactory`: CREATE2 deposit contract. |
| `0xbff4163f` | `depositWithBeneficiary(address token, uint256 amount, address beneficiary, uint64 data)` | Called by Meson on a third-party contract when a release goes to a contract (§6 item 6). |

---

## 3. The `encodedSwap` layout and the Meson chain codes

`encodedSwap` (bit 0 = least significant):

| Bits | Field | Meaning |
|------|-------|---------|
| 248–255 | `version` | Must be `1`. |
| 208–247 | `amount` | Swap amount, always 6 decimals (`amount / 1e6` units). Capped at 100,000. |
| 128–207 | `salt` | Flags in the top byte: `0x80` release to an EOA (clear = release to a contract), `0x40` service fee waived, `0x30` = 3 from `TransferToMesonContract`, 2 meson.to, 1 API, `0x08` non-typed signature, `0x04` swap part to the core coin, `0x02` share with a partner pool. |
| 88–127 | `fee` | LP fee, 6 decimals. |
| 48–87 | `expireTs` | Source-side expiry (unix seconds). |
| 32–47 | `outChain` | Destination Meson chain code. |
| 24–31 | `outToken` | Destination token index. |
| 8–23 | `inChain` | Source Meson chain code. |
| 0–7 | `inToken` | Source token index. |

SQL decode from `topic1` (bytea): `outChain = substring(topic1 from 27 for 2)`, `inChain = substring(topic1 from 30 for 2)`, `amount = substring(topic1 from 2 for 5)`.

Meson chain codes are the last two bytes of the SLIP-44 coin type. Read live with `getShortCoinType()` on each chain:

| Chain | Chain ID | Meson code | Notes |
|-------|----------|-----------|-------|
| Ethereum | 1 | `0x003c` | SLIP-44 60 |
| Base | 8453 | `0x2105` | |
| Arbitrum One | 42161 | `0x2329` | |
| Optimism | 10 | `0x0266` | |
| Polygon PoS | 137 | `0x03c6` | |
| BNB Smart Chain | 56 | `0x02ca` | |
| Avalanche C-Chain | 43114 | `0x2328` | |
| Robinhood Chain | 4663 | `0x1237` | the EVM chain ID itself |
| Tron (off-target) | — | `0x00c3` | special signing paths in the source |
| Solana (off-target) | — | `0x01f5` | seen as `inChain` of a Base payout (§9) |

Token index ranges (from `MesonTokens`): 1–32 stablecoins with 6 decimals (1 USDC, 2 USDT, 9 USDC.e, 10 USDT.e, 16 USD1), 33–48 stablecoins with 18 decimals (33 USDC, 34 USDT, 48 USD1), 49–64 stablecoins as the core coin, 65–128 third-party tokens, 191+ native and wrapped assets (243 BTC as core, 251 BNB as core, 252–255 ETH family, 255 ETH as core). An index with `(index > 190 && index % 4 == 3)` or 49–64 is the chain's native coin: no ERC-20 log.

---

## 4. Addresses — all eight chains (same proxy address everywhere)

All existence-checked with `eth_getCode` on 2026-09-29. The proxy is in the official relayer list for every chain below.

| Chain | ID | Meson proxy | Proxy code | Current implementation (EIP-1967 slot) | Tokens in the relayer list |
|-------|----|-------------|-----------|----------------------------------------|----------------------------|
| Ethereum | 1 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 802 B | `0x3c774719e0126415b870b4abfff89f8f59c5d906` | USDC `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48`, USDT `0xdac17f958d2ee523a2206206994597c13d831ec7`, PYUSD `0x6c3ea9036406852006290770BEdFcAbA0e23A0e8`, USD1 `0x8d0D000Ee44948FC98c9B98A4FA4921476f08B0d`, WBTC `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599`, ETH |
| Base | 8453 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 643 B | `0x03650533d2a35847c007f25bc630f468905f6241` | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, ETH |
| Arbitrum One | 42161 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 802 B | `0xa96e19d0f696690a416c610b4b34aac5be6fafc0` | USDC `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`, USDT0 `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9`, WBTC `0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f`, ETH |
| Optimism | 10 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 802 B | `0xe70e9a845fabd41fb3de258c41f4bfe395cd30c2` | USDC `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`, USDT `0x94b008aA00579c1307B0EF2c499aD98a8ce58e58`, USDT0 `0x01bFF41798a0BcF287b996046Ca68b395DbC1071`, ETH |
| Polygon PoS | 137 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 802 B | `0x2d90717e5400a83845c1f4f9d121492d328fceb7` | USDC `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`, USDT0 `0xc2132d05d31c914a87c6611c10748aeb04b58e8f`, WBTC `0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6`, POL |
| BNB Smart Chain | 56 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 802 B | `0x685ffe830e9d8b510df67d5d7453535456fa3bcc` | USDC `0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d`, USDT `0x55d398326f99059ff775485246999027b3197955`, USD1 `0x8d0D000Ee44948FC98c9B98A4FA4921476f08B0d`, BTCB `0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c`, BNB (all 18 decimals) |
| Avalanche C-Chain | 43114 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 802 B | `0x98b35a04356a354a089e5e741b4b9b02a7b0b822` | USDC `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`, USDt `0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7` |
| Robinhood Chain | 4663 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | 169 B | `0x512fc5156493792db24d0ce6ce9baacbadd69734` | USDG `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168`, ETH |

Roles (read live from the proxy storage, same value on all eight chains):

| Role | Address | How read |
|------|---------|----------|
| Owner (`_owner`, upgrade authority) | `0x000039DdCF1F63Cf3555e62a8D32a11bD1E7E1E1` | storage slot `0x134`. An EOA on every chain (no code; nonce 235 on Ethereum). Also the deployer of the Base implementation. |
| Premium manager (`_premiumManager`) | `0x666d6b8a44d226150ca9058beebafe0e3ac065a2` | storage slot `0x135`. An EOA. On Ethereum it carries a 23-byte EIP-7702 delegation code. It is also the caller of most `directRelease` payouts. |

---

## 5. Cross-chain summary

| Chain | ID | Meson proxy | Meson code | `SwapExecuted` / `SwapReleased` in the pinned window |
|-------|----|-------------|-----------|------------------------------------------------------|
| Ethereum | 1 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x003c` | 10 / 47 |
| Base | 8453 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x2105` | 9 / 5 |
| Arbitrum One | 42161 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x2329` | 64 / 72 |
| Optimism | 10 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x0266` | 5 / 0 |
| Polygon PoS | 137 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x03c6` | 31 / 20 |
| BNB Smart Chain | 56 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x02ca` | 64 / 207 |
| Avalanche C-Chain | 43114 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x2328` | 1 / 0 |
| Robinhood Chain | 4663 | `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` | `0x1237` | 0 / 0 |

Meson is on many more chains outside the eight (the relayer list has about 45: Linea, Scroll, zkSync Era at `0x2DcC88Fa6b6950EE28245C3238B8993BE5feeA42`, Mantle, Sonic, Tron, Solana, Sui, Starknet, Bitcoin and others). The counterpart of a swap is often off-target: decode `inChain` / `outChain` before you assume the other side.

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Meson proxy (all eight chains) | **UUPS** (ERC-1967 proxy + `UUPSUpgradeable`) | EIP-1967 implementation slot populated (§4). Admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` reads zero on all eight chains. | `_owner` EOA `0x000039DdCF1F63Cf3555e62a8D32a11bD1E7E1E1` (`_authorizeUpgrade` is `onlyOwner`). |

- The proxy bytecode differs per chain family: 802 B (`ProxyToMeson`) on six chains, 643 B on Base, 169 B on Robinhood Chain. All three keep the implementation in the EIP-1967 slot.
- The implementations differ per chain: each has its chain code compiled in, so each code hash is unique. Treat any `Upgraded` (topic `TOPIC_UPGRADED` in §8) on the proxy as a privileged change.
- The owner can also credit pool balances with no token movement (`adjustToPool`) and add tokens. These are admin actions to alert on.

---

## 7. Detection invariants & gotchas

1. **The link key is `encodedSwap` (`topic1`), exact on both chains.** Source `SwapExecuted` or `SwapPosted` and destination `SwapReleased` carry the same value. The destination storage key is `keccak256(encodedSwap, initiator)`, but the event carries only `encodedSwap`.
2. **`SwapExecuted` has two meanings.** From `simpleExecuteSwap` / `directExecuteSwap` it is a user deposit (tokens enter the proxy). From `executeSwap` it is an LP claim of an earlier `SwapPosted` (tokens leave the proxy to the pool owner, or stay as pool balance). Use the direction of the ERC-20 `Transfer` in the same transaction, or the call selector.
3. **Filter on `inChain` / `outChain`.** On a given chain, `SwapReleased` with `outChain` = that chain is an inbound payout. `directSwap` emits `SwapReleased` with `inChain == outChain`: that is a same-chain token swap, not a bridge.
4. **Native coin moves have no ERC-20 row.** For a core-coin index the deposit is `msg.value` and the payout is an internal call. The amount scale is `amount * 1e12` wei.
5. **18-decimal tokens.** On BNB Smart Chain the stablecoins have 18 decimals: the ERC-20 amount is `amount * 1e12`. The event amount is always 6 decimals.
6. **Release to a contract.** When the `salt` bit `0x80` is clear, Meson approves the token to the recipient contract and calls `depositWithBeneficiary(token, amount, initiator, data)`. The ERC-20 `Transfer` then goes from Meson to that contract (pulled by it), not to an EOA.
7. **Fees.** The recipient gets `amount - fee - serviceFee` (service fee 0.05%, minimum 0.5 USD, or 0.0005 ETH, 0.005 BNB, 0.00001 BTC), unless the fee is waived. The service fee stays in the contract as pool 0 balance.
8. **`TransferToMesonContract` deposits.** A user can pay a counterfactual CREATE2 deposit contract first (a plain transfer, no Meson event). The later `simpleExecuteSwap` then shows that contract, not the user, as the `Transfer` sender. Its `salt` top bits read 3.
9. **Status-only events.** `SwapBonded`, `SwapLocked`, `SwapUnlocked` move no tokens. In the pinned window `SwapPosted`, `SwapLocked` and `SwapCancelled` were 0 on all eight chains: the one-step flow (`simpleExecuteSwap` + `directRelease`) is the live path.
10. **`release` and `directRelease` require `msg.sender == tx.origin`.** Payouts are always top-level transactions by an LP EOA (mostly the premium manager), never internal calls of another contract.
11. **Large-transfer trigger.** Key on `SwapExecuted` / `SwapPosted` / `SwapReleased` at the proxy and decode `amount` from `topic1`. Admin triggers: `Upgraded`, `OwnerTransferred`, `PremiumManagerTransferred`, and calls to `adjustToPool` / `withdrawServiceFee` / `addSupportToken`.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_SWAP_EXECUTED              = '\x8d92c805c252261fcfff21ee60740eb8a38922469a7e6ee396976d57c22fc1c9'
TOPIC_SWAP_POSTED                = '\x5ce4019f772fda6cb703b26bce3ec3006eb36b73f1d3a0eb441213317d9f5e9d'
TOPIC_SWAP_BONDED                = '\x60a99b51ae498c44acbbe11031aed2a06a32be66d2122e6e2a7a16c087865cc9'
TOPIC_SWAP_CANCELLED             = '\xf6b6b4f7a13f02512c1b3aa8dcc4a07d7775a6a4becbd439efcbd37c5408e67f'
TOPIC_SWAP_LOCKED                = '\xbfb879c34323c5601fafe832c3a8a1e31e12c288695838726ddeada86034edb4'
TOPIC_SWAP_UNLOCKED              = '\xac7d23c4f0137a4cc35b0e4b4bc8061ea6cb65805e87ceb0a77ca0c85814858c'
TOPIC_SWAP_RELEASED              = '\xfa628b578e095243f0544bfad9255f49d79d03a5bbf6c85875d05a215e247ad2'
TOPIC_POOL_REGISTERED            = '\xb8d9c35a714d4e29eaf036b9bf8183a093c5573ac809453b4e8434e25c9126d2'
TOPIC_POOL_DEPOSITED             = '\x7d7d1df74ef3a6434d8d63dc0a25d13d5fa94dbe738c38a3cce26e6f892e2a76'
TOPIC_POOL_WITHDRAWN             = '\x34c3d1c46f89307d63d8818fcc5c2a9c07a5f7a01ea4319bfba1899f40c6f400'
TOPIC_OWNER_TRANSFERRED          = '\x8934ce4adea8d9ce0d714d2c22b86790e41b7731c84b926fbbdc1d40ff6533c9'
TOPIC_PREMIUM_MANAGER_TRANSFERRED= '\x4798f31ad3d0ccde6359edf35fc39b882e4e1cff2968ca749b72074d373db27a'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_SIMPLE_EXECUTE_SWAP          = '\x264849e7'
SEL_DIRECT_EXECUTE_SWAP          = '\xc8173c44'
SEL_POST_SWAP                    = '\x6f9b41fd'
SEL_POST_SWAP_WITH_SIGNATURE     = '\x0ffad9c0'
SEL_BOND_SWAP                    = '\x35eff30f'
SEL_EXECUTE_SWAP                 = '\x827c87cc'
SEL_CANCEL_SWAP                  = '\x54d6a2b7'
SEL_CANCEL_SWAP_TO               = '\x16f35d23'
SEL_LOCK_SWAP                    = '\x58d9b4e1'
SEL_UNLOCK                       = '\xf1d2ec1d'
SEL_RELEASE                      = '\xa5c9c66c'
SEL_DIRECT_RELEASE               = '\xab115fd8'
SEL_DIRECT_SWAP                  = '\x741c8e2d'
SEL_POOL_WITHDRAW                = '\xce7f79b9'
SEL_ADJUST_TO_POOL               = '\xeaf250b5'
SEL_WITHDRAW_SERVICE_FEE         = '\x7234cd95'
SEL_UPGRADE_TO                   = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'
SEL_GET_SHORT_COIN_TYPE          = '\xeba7fb77'
SEL_TRANSFER_TO_MESON            = '\xea78d39a'

-- ===== Addresses (the same proxy on all eight chains) =====
ETH_MESON                        = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
BASE_MESON                       = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
ARB_MESON                        = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
OP_MESON                         = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
POLY_MESON                       = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
BNB_MESON                        = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
AVAX_MESON                       = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
RH_MESON                         = '\x25ab3efd52e6470681ce037cd546dc60726948d3'
-- implementations (point-in-time; read the EIP-1967 slot)
ETH_MESON_IMPL                   = '\x3c774719e0126415b870b4abfff89f8f59c5d906'
BASE_MESON_IMPL                  = '\x03650533d2a35847c007f25bc630f468905f6241'
ARB_MESON_IMPL                   = '\xa96e19d0f696690a416c610b4b34aac5be6fafc0'
OP_MESON_IMPL                    = '\xe70e9a845fabd41fb3de258c41f4bfe395cd30c2'
POLY_MESON_IMPL                  = '\x2d90717e5400a83845c1f4f9d121492d328fceb7'
BNB_MESON_IMPL                   = '\x685ffe830e9d8b510df67d5d7453535456fa3bcc'
AVAX_MESON_IMPL                  = '\x98b35a04356a354a089e5e741b4b9b02a7b0b822'
RH_MESON_IMPL                    = '\x512fc5156493792db24d0ce6ce9baacbadd69734'
-- roles (same on all eight chains)
ETH_MESON_OWNER_EOA              = '\x000039ddcf1f63cf3555e62a8d32a11bd1e7e1e1'
ETH_MESON_PREMIUM_MANAGER_EOA    = '\x666d6b8a44d226150ca9058beebafe0e3ac065a2'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified `UpgradableMeson` source (`IMesonSwapEvents.sol`, `IMesonPoolsEvents.sol`, `MesonSwap.sol`, `MesonPools.sol`, `MesonManager.sol`, `TransferToMesonContract.sol`). The four lifecycle topics seen in the window match live logs at the proxy.
- **Addresses:** the official relayer list gives `0x25aB3Efd52e6470681CE037cD546Dc60726948D3` for all eight chains (Robinhood as `hood`, chain `0x1237`). `eth_getCode` confirms code on all eight. The EIP-1967 implementation slot was read on each chain.
- **Chain codes:** `getShortCoinType()` was called on the proxy on each chain (§3). They match the Meson docs list (Ethereum `0x003c`, Optimism `0x0266`, BNB `0x02ca`, Polygon `0x03c6`, Avalanche `0x2328`, Arbitrum `0x2329`) and the Base source constant `0x2105`.
- **Roles:** storage slots `0x134` (`_owner`) and `0x135` (`_premiumManager`), derived from the verified storage layout, read the same value on all eight chains. Both addresses were existence-checked as EOAs.
- **Activity:** `eth_getLogs` at the proxy in the pinned 12-hour window 2026-09-28 00:00–12:00 UTC. `SwapExecuted`: Ethereum 10, Base 9, Arbitrum 64, Optimism 5, Polygon 31, BNB 64, Avalanche 1, Robinhood 0. `SwapReleased`: Ethereum 47, Base 5, Arbitrum 72, Optimism 0, Polygon 20, BNB 207, Avalanche 0, Robinhood 0. `SwapPosted`, `SwapLocked`, `SwapCancelled`, `SwapBonded`, `SwapUnlocked`: 0 on all eight. A 0 is a measurement of this window only.
- **Sample transactions (receipts read):**
  - Ethereum `0x21e3f93b8f219ef76d7fb39b4656711e3604d7a617d0757c75d33d42352d0713`: `simpleExecuteSwap`, USDC `Transfer` user to proxy, then `SwapExecuted`. `encodedSwap` `0x010004414665d80000000000b8dc1977000001fbd0006ab9d72102ca21003c01` decodes to 71.386725 USDC, Ethereum (`0x003c`) to BNB (`0x02ca`), out token 33.
  - Ethereum `0x90375bd4c8c31fcfe05d14113bd73a6c9f6300d43de67df4ef60b258e2c0c099`: `directRelease` by the premium manager, USDT `Transfer` proxy to recipient, then `SwapReleased`. `inChain` `0x2328` (Avalanche), `outChain` `0x003c`.
  - Base `0x1dcc29f389545e305c9bd6dce1c3294f0280d6bac908a5166d22e07a5b14c8fd` (`SwapExecuted`, 50.5 USDC to Ethereum) and `0x446df09c27a24de7c89eaad602326165f750f92c7b4cef9d80540d1e30cef187` (`SwapReleased`, `inChain` `0x01f5` Solana).

Authoritative sources:
- Verified source — Sourcify `UpgradableMeson` (chain 8453, `0x03650533d2a35847c007f25bc630f468905f6241`) and `ProxyToMeson` (chain 1, `0x25aB3Efd52e6470681CE037cD546Dc60726948D3`). The former public repo `MesonFi/meson-contracts-solidity` is no longer available.
- Docs — [Meson in Solidity](https://docs.meson.fi/implementation/smart-contracts/solidity.md)
- Official chain list — [relayer.meson.fi/api/v1/list](https://relayer.meson.fi/api/v1/list)
- Explorers — [Etherscan](https://etherscan.io/address/0x25aB3Efd52e6470681CE037cD546Dc60726948D3) · [Basescan](https://basescan.org/address/0x25aB3Efd52e6470681CE037cD546Dc60726948D3) · [Robinhood Blockscout](https://robinhoodchain.blockscout.com/address/0x25aB3Efd52e6470681CE037cD546Dc60726948D3)
