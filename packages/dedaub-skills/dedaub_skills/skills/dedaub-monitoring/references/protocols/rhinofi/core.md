# Rhino.fi Bridge — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the verified `DVFDepositContract` implementation source (Ethereum, compiler 0.8.4), the canonical `rhinofi/contracts_public` repo (`bridge-deposit/DVFDepositContract.sol`, an older version), the Rhino.fi docs (contract addresses, EVM contract guide, supported chains, Smart Deposit Addresses) and the public bridge config API (`https://api.rhino.fi/bridge/configs`). Topic0s and selectors are recomputed as `keccak256(sig)`. Addresses are existence-checked with `eth_getCode`. The EIP-1967 implementation and admin slots, `owner()`, `authorized()` and `depositsDisallowed()` are read live.
**Scope:** the Rhino.fi bridge contract (`DVFDepositContract` behind an OpenZeppelin `TransparentUpgradeableProxy`) on each of the eight target chains, its `ProxyAdmin`, its owner, its `BridgeVM`, and the operator wallets that send payouts. Chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114), Robinhood Chain (4663). Topics and selectors are chain-agnostic. Addresses are network-specific. Rhino.fi also runs on chains that are not EVM (Solana, Starknet, TON, Tron, Stellar, Bitcoin); they are out of scope.

Rhino.fi is a liquidity bridge with an off-chain quote system. The user first gets a quote from the Rhino.fi API and commits it. The API returns a `quoteId`. The user then calls `depositWithId` (ERC-20) or `depositNativeWithId` (native) on the bridge contract of the source chain, with `commitmentId = quoteId`. The contract keeps the funds and emits `BridgedDepositWithId`. An authorized Rhino.fi operator then pays the recipient on the destination chain from the bridge contract's own inventory (`withdrawV2`, `withdrawNativeV2`, `withdrawWithData`, `swapWithData`). There is no mint, no burn and no message: each chain's bridge contract is a pool that Rhino.fi rebalances off chain.

**The link key is the `commitmentId`, and it is on chain only on the source side.** It is the API `quoteId` (a 24-hex-digit identifier) stored as a `uint256`. The payout events carry no key: the current code emits `BridgedWithdrawal` with an empty `withdrawalId`, and the sampled `BridgedWithdrawalWithData` has an empty `ref`. The Rhino.fi API maps a `quoteId` to its `depositTxHash` and `withdrawTxHash`. The deposit event also carries no destination chain and no recipient; only the committed quote has them.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Where |
|----------|------|--------|-------|
| **Bridge** (`DVFDepositContract`, the config's `contractAddress`) | Source leg (`BridgedDepositWithId`) and destination leg (`BridgedWithdrawal*`, `SwapWithData`) on every chain. Holds the pool. | **Yes**: OpenZeppelin `TransparentUpgradeableProxy`; one implementation code (13,825 B) on all eight chains | all eight chains; one address per chain (Avalanche and Robinhood Chain share one) |
| **ProxyAdmin** | OpenZeppelin `ProxyAdmin`: `upgrade`, `upgradeAndCall`, `changeProxyAdmin`. | No | one per chain |
| **Owner** | `owner()` of the bridge and of the ProxyAdmin. Adds and removes operators; upgrades. | Safe multisig (threshold 2 where read) on seven chains; an address with no code on Robinhood Chain | one per chain |
| **BridgeVM** | Created by the bridge. Executes the call lists of `withdrawWithData` and `swapWithData`. Only the bridge can call it. | No | one per chain |
| **Operators** | EOAs in `authorized`. Send every payout, swap and rebalance. | n/a (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` is authorized on all eight chains |
| Smart Deposit Addresses (SDAs) | Per-user deposit addresses. Swept into the bridge with EIP-7702. | n/a | not enumerable on chain |
| SameChainSwaps (not a bridge) | Rhino.fi same-chain swap product (`SwapExecuted`). Listed only so a monitor does not confuse it with the bridge. | Transparent proxy | Ethereum, Base, Arbitrum, Optimism, Polygon, BNB |

The config's `multicallContractAddress` is a `Multicall2` read helper (Optimism uses the common Multicall3 `0xcA11bde05977b3631167028862bE2a173976CA11`). It moves no funds.

### Rhino.fi chain keys (API only)

The contracts carry no chain id. The API names chains with its own keys: `ETHEREUM` (1), `BASE` (8453), `ARBITRUM` (42161), `OPTIMISM` (10), `MATIC_POS` (137), `BINANCE` (56), `AVALANCHE` (43114), `ROBINHOOD` (4663).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Bridge — current implementation

No parameter of these events is indexed. Every field is in `data`.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x1655dc426ee0145d9436d28cfb463fb0e0717ae145566e5e534da64b735e49f3` | `BridgedDepositWithId(address sender, address origin, address token, uint256 amount, uint256 commitmentId)` | **Source leg.** `sender` = `msg.sender`, `origin` = `tx.origin` (the signer, also through a router). `token` = `0x0000000000000000000000000000000000000000` for native. `commitmentId` = the API `quoteId`. |
| `0xe4f4f1fb3534fe80225d336f6e5a73007dc992e5f6740152bf13ed2a08f3851a` | `BridgedWithdrawal(address user, address token, uint256 amount, string withdrawalId)` | **Destination leg** (`withdrawV2`, `withdrawNativeV2`). `user` = recipient. `withdrawalId` is an empty string in the current code. |
| `0x446598b3c3f0d9f39b89eb111ba2796b4fcbbf3bb39d64d5fd98c3045218cb31` | `BridgedWithdrawalWithData(address token, uint256 amountToken, uint256 amountNative, bytes ref)` | **Destination leg with calls** (`withdrawWithData`). No recipient field: the funds go to the BridgeVM, which runs the call list. |
| `0x0ec14d41fb8dd758c7a1fc411ce327517caf88a8b9dee8bed60869801990d22c` | `BridgedWithdrawalWithNative(address user, address token, uint256 amountToken, uint256 amountNative)` | Destination leg with a native top-up (`withdrawV2WithNative`). |
| `0xad50835dbfd8ee369e3d3c5ffa2f72b0f250cb3cf4331f29e78fa780f20ef998` | `SwapWithData(address tokenOut, uint256 receivedAmount, address recipient, bytes ref)` | Swap through the BridgeVM (`swapWithData`). A payout with a swap, or a rebalance when `recipient` is the bridge itself. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Admin. The ProxyAdmin emits the same topic. |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` | Initializer (OpenZeppelin v4.x). |

### 1.2 Bridge — older implementation (historical)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x573284f4c36da6a8d8d84cd06662235f8a770cc98e8c80e304b8f382fdc3dca2` | `BridgedDeposit(address indexed user, address indexed token, uint256 amount)` | Emitted by `deposit` / `depositNative` in the `rhinofi/contracts_public` version. The live implementation has neither function nor this event. |

### 1.3 Proxy (EIP-1967)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | **Implementation change on a bridge proxy.** High severity. |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | ProxyAdmin change. |

### 1.4 Related, not a bridge — SameChainSwaps

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x8d4b0b92227416eaf2d1083d2b85ae69e220579a86271193378cabb1d13dfb9c` | `SwapExecuted(address tokenOut, uint256 receivedAmount, address recipient, uint256 commitmentId)` | Same-chain swap. It also carries a `commitmentId`; do not count it as a bridge deposit. |

### 1.5 Value capture

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20. Deposit: user → bridge. Payout: bridge → recipient, or bridge → BridgeVM → targets. SDA sweeps and rebalances also move tokens into and out of the bridge with no bridge event. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Bridge — public deposit functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2700bbaf` | `depositWithId(address token, uint256 amount, uint256 commitmentId)` | `safeTransferFrom(msg.sender, bridge, amount)`, then `BridgedDepositWithId`. Reverts for `token` = zero address. |
| `0xf9068677` | `depositNativeWithId(uint256 commitmentId)` | Payable. The bridge keeps `msg.value`. |
| `0x9a203dbf` | `depositWithPermit(address token, uint256 amount, uint256 deadline, uint8 v, bytes32 r, bytes32 s, uint256 commitmentId)` | EIP-2612 permit, then `depositWithId`. |

### 2.2 Bridge — operator functions (`_isAuthorized`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9c66c25d` | `withdrawV2(address token, address to, uint256 amount)` | Payout. Emits `BridgedWithdrawal(to, token, amount, "")`. |
| `0x535b355c` | `withdrawNativeV2(address to, uint256 amount)` | Native payout. Emits `BridgedWithdrawal(to, 0x0000000000000000000000000000000000000000, amount, "")`. |
| `0xb78b415b` | `withdrawV2WithNative(address token, address to, uint256 amountToken, uint256 amountNative)` | Emits `BridgedWithdrawalWithNative`. |
| `0x36d44bbb` | `withdrawV2WithNativeNoEvent(address token, address to, uint256 amountToken, uint256 amountNative)` | **Payout with no bridge event.** |
| `0xec8acddf` | `withdrawWithData(address token, uint256 amount, uint256 amountNative, (address target, uint256 value, bytes data)[] datas, bytes ref)` | Sends `amount` to the BridgeVM and runs `datas`. Emits `BridgedWithdrawalWithData`. |
| `0x5831419b` | `withdrawWithDataNoEvent(address token, uint256 amount, uint256 amountNative, (address target, uint256 value, bytes data)[] datas)` | **Same with no bridge event.** |
| `0x2090d831` | `swapWithData(address tokenIn, address tokenOut, uint256 amountIn, uint256 amountInNative, uint256 minAmountOut, address recipient, (address target, uint256 value, bytes data)[] datas, bytes ref)` | Swap through the BridgeVM. Checks `minAmountOut` on the recipient's balance. Emits `SwapWithData`. |
| `0xd6c9b6a5` | `removeFunds(address token, address to, uint256 amount)` | **Rebalance out. No event.** |
| `0x143531c0` | `removeFundsNative(address to, uint256 amount)` | **Native rebalance out. No event.** |
| `0xbc4b3365` | `addFunds(address token, uint256 amount)` | Rebalance in. No event. |
| `0x447e346f` | `addFundsNative()` | Payable rebalance in. No event. |

### 2.3 Bridge — owner, views and helpers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2d1fb389` | `authorize(address user, bool value)` | `onlyOwner`. Adds or removes an operator. **No event.** |
| `0x653b954c` | `authorizeMulti(address[] users, bool value)` | `onlyOwner`. **No event.** |
| `0x4fb2e45d` | `transferOwner(address newOwner)` | `onlyOwner`. Moves the operator flag to the new owner, then `transferOwnership`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | `onlyOwner`. Emits `OwnershipTransferred`. |
| `0x1c6dd8a1` | `withdrawVmFunds(address token)` | Anyone. Returns stray BridgeVM funds to the bridge. |
| `0x3fbe4dbb` | `createVMContract()` | Deploys the BridgeVM once. |
| `0xb9181611` | `authorized(address)` | View → `bool`. |
| `0xf80dec97` | `depositsDisallowed()` | View → `bool`. Legacy flag; see §13. |
| `0xd6441046` | `maxDepositAmount(address)` | View → `int256`. Legacy. |
| `0x7729d644` | `processedWithdrawalIds(string)` | View → `bool`. Legacy. |
| `0x8da5cb5b` | `owner()` | View → `address`. |

### 2.4 Bridge — older implementation (historical)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x47e7ef24` | `deposit(address token, uint256 amount)` | Emitted `BridgedDeposit`. Not in the live implementation. |
| `0xdb6b5246` | `depositNative()` | Same. |
| `0x75036de1` | `allowDepositsGlobal(bool value)` | Set `depositsDisallowed`. Not in the live implementation. |
| `0x3308c6b3` | `allowDeposits(address tokenAddress, int256 maxAmount)` | Set `maxDepositAmount`. Not in the live implementation. |

### 2.5 ProxyAdmin (OpenZeppelin)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | `onlyOwner`. The proxy emits `Upgraded`. |
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | `onlyOwner`. |
| `0x7eff275e` | `changeProxyAdmin(address proxy, address newAdmin)` | `onlyOwner`. The proxy emits `AdminChanged`. |

---

## 3. Addresses — Ethereum (chain ID 1)

All verified with `eth_getCode` on 2026-09-29. The bridge address comes from the Rhino.fi contract-addresses page and the `/bridge/configs` API.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0xBCA3039a18c0d2f2F84BA8a028c67290bc045AFa` | 2,227 B transparent proxy. |
| Implementation | `0x7877b41fB0573d1CeD42e995D0f79EcCC1e34d48` | Verified `DVFDepositContract`, 13,825 B. |
| ProxyAdmin | `0x70911642e4eA509735e77CbA23Ce1856AbeD87Bf` | Verified OpenZeppelin `ProxyAdmin`. |
| Owner (bridge and ProxyAdmin) | `0x520Cf70a2D0B3dfB7386A2Bc9F800321F62a5c3a` | Safe (singleton `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552`, threshold 2). |
| BridgeVM | `0x0551e6700a0C7C5a1633E912710ED80c88FACC07` | Verified `BridgeVM`, 3,375 B. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. Sends payouts. Nonce 11,580. |
| Operator (EOA) | `0x51497124089aBDEc0d3749D6dB082f66ca03750a` | `authorized` = true. Sent the sampled `swapWithData`. Nonce 1,064. |
| SameChainSwaps (not a bridge) | `0xF9E67FF0688f4f321b9FB1649F561F6c245327d8` | Transparent proxy, implementation `0x242794484D89F46E679a5F88c1544125Ef2507A9`. |

`0x5e023c31E1d3dCd08a1B3e8c96f6EF8Aa8FcaCd1` is the bridge on Avalanche and Robinhood Chain. On Ethereum the same address holds an unrelated, unverified 3,826-byte contract. It is not the Rhino.fi bridge on Ethereum.

## 4. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0x2f59E9086ec8130E21BD052065a9E6B2497bb102` | 2,112 B transparent proxy. |
| Implementation | `0xECf5f40d7881866397fE540796B05F58a1907563` | Same code hash as Ethereum. |
| ProxyAdmin | `0x2B4553122D960CA98075028d68735cC6b15DeEB5` | 1,891 B. |
| Owner | `0xF07A1288ab71Fa0FFA5aCe4D2E8b79b490065008` | Safe (L2 singleton, threshold 2). |
| BridgeVM | `0x1C128bBd0c70da36A4f13531c92F37D8f1cCc0f2` | 3,375 B, same code hash as the Ethereum BridgeVM. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. Nonce 234,790. |
| SameChainSwaps (not a bridge) | `0x42E592793eE834eF0B76c234241568Eb9f5B8702` | Transparent proxy. |

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0x10417734001162Ea139e8b044DFe28DbB8B28ad0` | 2,141 B transparent proxy. |
| Implementation | `0x6475F3aB14f3e3FF2c8C398a6E21F5Cfd872269D` | Same code hash. |
| ProxyAdmin | `0x934452D12b24b834877D6096ebdeCBBf0e97AddA` | 1,881 B. |
| Owner | `0x15ca1fC728Cce7cd06151C8007e89dEe70260228` | 171-byte Safe proxy. |
| BridgeVM | `0xA166d9e596561C23dC9D46D9E24A5A0315F6fAC2` | 3,375 B, same code hash as the Ethereum BridgeVM. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. |
| SameChainSwaps (not a bridge) | `0x27C0686F9D0C3c3A6f8660E23299083E259F9D69` | Transparent proxy. |

## 6. Addresses — Optimism (chain ID 10)

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0x0bCa65bf4b4c8803d2f0B49353ed57CAAF3d66Dc` | 2,112 B transparent proxy. |
| Implementation | `0x7595433A8D01E8e3183EEd8251d288409D3423e5` | Same code hash. |
| ProxyAdmin | `0x329F5a8d24503fC00B31b229835b6452A6723ae4` | 1,891 B. |
| Owner | `0x09Af25ebbfe4606813C451620a5ba356026d41Fa` | 171-byte Safe proxy. |
| BridgeVM | `0x5DCf421Bf4C724940c8344C629FFB3aBF8011619` | 3,375 B, same code hash as the Ethereum BridgeVM. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. |
| SameChainSwaps (not a bridge) | `0xE66AF6066c285C8963F4A85Af29A731B0897975a` | Transparent proxy. |

## 7. Addresses — Polygon PoS (chain ID 137)

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0xBA4EEE20F434bC3908A0B18DA496348657133A7E` | 2,141 B transparent proxy. |
| Implementation | `0x7d40f6955aF1316c2B67Ec1D00E86c208Db3E69d` | Same code hash. |
| ProxyAdmin | `0xd80a8890f5b07cfFCd5c939f2C63781ef4Fe2642` | 1,881 B. |
| Owner | `0x249aAbb1d67A76404Cc1197fa37ADAf358B1E212` | 171-byte Safe proxy, threshold 2. |
| BridgeVM | `0xde52e32F1efC70b9d7c0dEdD664c7B7A531e7ac1` | 3,375 B, same code hash as the Ethereum BridgeVM. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. |
| SameChainSwaps (not a bridge) | `0xA9bc50895443452c617F873E8A7405D6DC875308` | Transparent proxy. |

## 8. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0xB80A582fa430645A043bB4f6135321ee01005fEf` | 2,141 B transparent proxy. |
| Implementation | `0x5c625402C0586bCf5d7B0B2c68f08A805FEf57AD` | Same code hash. |
| ProxyAdmin | `0xB8ee2CD0E210faC991e441dba767082d9CDcEeC3` | 1,881 B. |
| Owner | `0x7Af3828c0B061552AF3479806Add982eEf04f0c8` | 171-byte Safe proxy. |
| BridgeVM | `0x12ef0730Ca80B618c2789E74faB685bED72491f7` | 3,375 B, same code hash as the Ethereum BridgeVM. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. |
| SameChainSwaps (not a bridge) | `0x242794484D89F46E679a5F88c1544125Ef2507A9` | Transparent proxy. On Ethereum the same address is the SameChainSwaps implementation. |

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0x5e023c31E1d3dCd08a1B3e8c96f6EF8Aa8FcaCd1` | 2,227 B transparent proxy. The same address is the bridge on Robinhood Chain. |
| Implementation | `0x2eF3AB3F8B30f2FA2B092eF1f6A9f46730547D50` | Same code hash. |
| ProxyAdmin | `0x04317f0E4795b1E1Bab333234153Fa10Aaac79E9` | 1,690 B. |
| Owner | `0xb1fDfD298DCaF4e710024c30347AF7D4C598C23c` | 171-byte Safe proxy. |
| BridgeVM | `0x4611caCFC562C882eFb01bDda1E5326440c07cE2` | 3,375 B, same code hash as the Ethereum BridgeVM. Same address on Avalanche and Robinhood Chain. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. |

No SameChainSwaps address is configured for Avalanche.

## 10. Addresses — Robinhood Chain (chain ID 4663)

The docs' contract-addresses table omits Robinhood Chain. The `/bridge/configs` API lists `ROBINHOOD` (network id 4663) with this bridge, and the supported-chains page lists USDG and USDe for Robinhood.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0x5e023c31E1d3dCd08a1B3e8c96f6EF8Aa8FcaCd1` | 2,227 B transparent proxy. Same address as Avalanche. |
| Implementation | `0xe32BD93e602383A591b3369B7D5aC36aC302B904` | Same code hash. |
| ProxyAdmin | `0x04317f0E4795b1E1Bab333234153Fa10Aaac79E9` | 1,690 B. Same address as Avalanche. |
| Owner | `0x478615F37FcCB0DF69C191a8674233f6899D092e` | **No code and nonce 0 on Robinhood Chain.** Not a deployed Safe here. |
| BridgeVM | `0x4611caCFC562C882eFb01bDda1E5326440c07cE2` | 3,375 B, same code hash as the Ethereum BridgeVM. Same address on Avalanche and Robinhood Chain. |
| Operator (EOA) | `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` | `authorized` = true. |

---

## 11. Cross-chain summary

| Chain | ID | Bridge (proxy) | Owner | `BridgedDepositWithId` | `BridgedWithdrawal` | `BridgedWithdrawalWithData` |
|-------|----|----------------|-------|----|----|----|
| Ethereum | 1 | `0xBCA3039a18c0d2f2F84BA8a028c67290bc045AFa` | Safe | 36 | 105 | 11 |
| Base | 8453 | `0x2f59E9086ec8130E21BD052065a9E6B2497bb102` | Safe | 71 | 745 | 1,564 |
| Arbitrum One | 42161 | `0x10417734001162Ea139e8b044DFe28DbB8B28ad0` | Safe | 177 | 358 | 0 |
| Optimism | 10 | `0x0bCa65bf4b4c8803d2f0B49353ed57CAAF3d66Dc` | Safe | 1 | 1,004 | 0 |
| Polygon PoS | 137 | `0xBA4EEE20F434bC3908A0B18DA496348657133A7E` | Safe | 11 | 168 | 5 |
| BNB Smart Chain | 56 | `0xB80A582fa430645A043bB4f6135321ee01005fEf` | Safe | 28 | 332 | 0 |
| Avalanche C-Chain | 43114 | `0x5e023c31E1d3dCd08a1B3e8c96f6EF8Aa8FcaCd1` | Safe | 0 | 41 | 33 |
| Robinhood Chain | 4663 | `0x5e023c31E1d3dCd08a1B3e8c96f6EF8Aa8FcaCd1` | no code | 0 | 288 | 0 |

Counts are from the pinned 12-hour window 2026-09-28 00:00–12:00 UTC. The bridge is deployed on all eight target chains. The config also lists Arc, Celo, Gnosis, HyperEVM, Ink, Kaia, Mantle, Plasma, Stable and Tempo (enabled) and Katana, Linea and opBNB (disabled).

---

## 12. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Bridge** (all eight chains) | OpenZeppelin `TransparentUpgradeableProxy` (EIP-1967) | EIP-1967 implementation slot populated (per-chain implementation in §3–§10, all with code hash `0x3e9099fb0a2ed123665fc37ab856b69c98b27e0e53d3c6867e682bdb4d7837fc`). Admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = the ProxyAdmin. | ProxyAdmin `owner()`: a Safe on seven chains; `0x478615F37FcCB0DF69C191a8674233f6899D092e` (no code) on Robinhood Chain. |
| ProxyAdmin | Immutable OpenZeppelin `ProxyAdmin` (verified on Ethereum; `owner()` answers on all eight chains) | No EIP-1967 slots. | Its `owner()` (same address as the bridge owner on every chain). |
| BridgeVM | Immutable, created by the bridge | No EIP-1967 slots. | None. Only the bridge can call `execute`. |
| SameChainSwaps | OpenZeppelin `TransparentUpgradeableProxy` | EIP-1967 implementation slot populated (7,656-byte implementation on all six chains). | Not researched (not a bridge). |

The three proxy sizes (2,227 B, 2,141 B, 2,112 B) are all EIP-1967 transparent proxies with a ProxyAdmin in the admin slot. The 2,227-byte code is a verified OpenZeppelin `TransparentUpgradeableProxy` (the Ethereum SameChainSwaps proxy has the same code hash). Watch `Upgraded(address)` (`0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`) on every bridge proxy. The implementation addresses above are a snapshot; read the slot live.

---

## 13. Detection invariants & gotchas

1. **The payout has no key on chain.** `BridgedWithdrawal.withdrawalId` is `""` in the current code (the sampled Ethereum log has a 0-length string). The sampled `BridgedWithdrawalWithData.ref` is empty too. Link a payout to its deposit through the Rhino.fi API (`quoteId` → `depositTxHash`, `withdrawTxHash`).
2. **`commitmentId` = the API `quoteId`.** The SDK passes `BigInt('0x' + quoteId)`. Example: Ethereum deposit `0x5b8f94916ac401f5f682faf648a660599d5ff542ba4f07a84863a9cee81384f1` has `commitmentId` `0x6ab9b158ad7a6c21e63c0c9c` (24 hex digits). The docs warn that a deposit with an invalid `commitmentId` is not processed, so its funds stay in the pool.
3. **The deposit event has no destination and no recipient.** Only the committed quote has them. `origin` (`tx.origin`) names the signer when a router or smart account calls the bridge.
4. **Silent value paths.** These move funds with no bridge event: `removeFunds` / `removeFundsNative` (operator rebalance out), `withdrawV2WithNativeNoEvent`, `withdrawWithDataNoEvent`, `addFunds` / `addFundsNative`, SDA sweeps into the bridge (EIP-7702), and plain transfers to the bridge. For drains, alert on a large `Transfer` from the bridge in a transaction with no `Bridged*` or `SwapWithData` log, or on the selectors `0xd6c9b6a5` and `0x143531c0`.
5. **`BridgedWithdrawalWithData` names no recipient.** The token goes bridge → BridgeVM → the targets of the call list (a DEX, a vault, a recipient). Follow the `Transfer` logs of the same transaction. The sampled Base payout `0x350fdab9b2d90a29330a8be634e8c72cbfc821d76f204906bab5e001c5e595cd` routes USDC through the BridgeVM and several vaults.
6. **`SwapWithData` can be a rebalance.** In the sampled Ethereum transaction `0x5d6ac3fa62c5db74fbd55bdef53520fc4de0ec4ac21b1d8990d273894616cc3a`, the output token goes back to the bridge. Treat `recipient` = the bridge as internal.
7. **Operator changes are invisible in logs.** `authorize` and `authorizeMulti` emit no event. Watch their selectors (`0x2d1fb389`, `0x653b954c`) on the bridge, or read `authorized(addr)`. `0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f` is authorized on all eight chains.
8. **`depositsDisallowed()` is a dead flag.** It returns `true` on seven chains (`false` on Robinhood Chain), yet deposits work: the live `depositWithId` and `depositNativeWithId` do not read it. It is not a pause signal. The contract has no pause.
9. **Addresses repeat across chains with different roles.** `0x5e023c31E1d3dCd08a1B3e8c96f6EF8Aa8FcaCd1` is the bridge on Avalanche and Robinhood Chain (and on nine more chains in the config), but an unrelated contract on Ethereum. `0x2B4553122D960CA98075028d68735cC6b15DeEB5` is the Base ProxyAdmin and the opBNB bridge. `0x04317f0E4795b1E1Bab333234153Fa10Aaac79E9` is the Avalanche and Robinhood ProxyAdmin and the Katana bridge. `0x242794484D89F46E679a5F88c1544125Ef2507A9` is a SameChainSwaps proxy on BNB and its implementation on Ethereum. Key on `(chain, address)`.
10. **Robinhood Chain is live, but its upgrade authority is an undeployed address.** 288 `BridgedWithdrawal` in the pinned window, 0 `BridgedDepositWithId` (deposits there may arrive by SDA sweeps or plain transfers; not measured). The ProxyAdmin owner `0x478615F37FcCB0DF69C191a8674233f6899D092e` has no code and nonce 0 there, so no upgrade can happen until something is deployed at that address.
11. **Topic collisions.** `OwnershipTransferred` and `Upgraded` are generic OpenZeppelin topics. `SwapExecuted` (SameChainSwaps) also carries a `commitmentId`. Filter on the emitter.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_BRIDGED_DEPOSIT_WITH_ID          = '\x1655dc426ee0145d9436d28cfb463fb0e0717ae145566e5e534da64b735e49f3'
TOPIC_BRIDGED_WITHDRAWAL               = '\xe4f4f1fb3534fe80225d336f6e5a73007dc992e5f6740152bf13ed2a08f3851a'
TOPIC_BRIDGED_WITHDRAWAL_WITH_DATA     = '\x446598b3c3f0d9f39b89eb111ba2796b4fcbbf3bb39d64d5fd98c3045218cb31'
TOPIC_BRIDGED_WITHDRAWAL_WITH_NATIVE   = '\x0ec14d41fb8dd758c7a1fc411ce327517caf88a8b9dee8bed60869801990d22c'
TOPIC_SWAP_WITH_DATA                   = '\xad50835dbfd8ee369e3d3c5ffa2f72b0f250cb3cf4331f29e78fa780f20ef998'
TOPIC_BRIDGED_DEPOSIT_LEGACY           = '\x573284f4c36da6a8d8d84cd06662235f8a770cc98e8c80e304b8f382fdc3dca2'
TOPIC_OWNERSHIP_TRANSFERRED            = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_UPGRADED                         = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED                    = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_SAME_CHAIN_SWAP_EXECUTED         = '\x8d4b0b92227416eaf2d1083d2b85ae69e220579a86271193378cabb1d13dfb9c'
TOPIC_ERC20_TRANSFER                   = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors (chain-agnostic) =====
SEL_DEPOSIT_WITH_ID                    = '\x2700bbaf'
SEL_DEPOSIT_NATIVE_WITH_ID             = '\xf9068677'
SEL_DEPOSIT_WITH_PERMIT                = '\x9a203dbf'
SEL_WITHDRAW_V2                        = '\x9c66c25d'
SEL_WITHDRAW_NATIVE_V2                 = '\x535b355c'
SEL_WITHDRAW_V2_WITH_NATIVE            = '\xb78b415b'
SEL_WITHDRAW_V2_WITH_NATIVE_NO_EVENT   = '\x36d44bbb'
SEL_WITHDRAW_WITH_DATA                 = '\xec8acddf'
SEL_WITHDRAW_WITH_DATA_NO_EVENT        = '\x5831419b'
SEL_SWAP_WITH_DATA                     = '\x2090d831'
SEL_REMOVE_FUNDS                       = '\xd6c9b6a5'
SEL_REMOVE_FUNDS_NATIVE                = '\x143531c0'
SEL_ADD_FUNDS                          = '\xbc4b3365'
SEL_AUTHORIZE                          = '\x2d1fb389'
SEL_AUTHORIZE_MULTI                    = '\x653b954c'
SEL_TRANSFER_OWNER                     = '\x4fb2e45d'
SEL_PROXYADMIN_UPGRADE                 = '\x99a88ec4'
SEL_PROXYADMIN_UPGRADE_AND_CALL        = '\x9623609d'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                      = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                     = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Bridge proxies (one per chain) =====
ETH_BRIDGE                             = '\xbca3039a18c0d2f2f84ba8a028c67290bc045afa'
BASE_BRIDGE                            = '\x2f59e9086ec8130e21bd052065a9e6b2497bb102'
ARB_BRIDGE                             = '\x10417734001162ea139e8b044dfe28dbb8b28ad0'
OP_BRIDGE                              = '\x0bca65bf4b4c8803d2f0b49353ed57caaf3d66dc'
POLY_BRIDGE                            = '\xba4eee20f434bc3908a0b18da496348657133a7e'
BNB_BRIDGE                             = '\xb80a582fa430645a043bb4f6135321ee01005fef'
AVAX_BRIDGE                            = '\x5e023c31e1d3dcd08a1b3e8c96f6ef8aa8fcacd1'
RH_BRIDGE                              = '\x5e023c31e1d3dcd08a1b3e8c96f6ef8aa8fcacd1'

-- ===== ProxyAdmins =====
ETH_PROXY_ADMIN                        = '\x70911642e4ea509735e77cba23ce1856abed87bf'
BASE_PROXY_ADMIN                       = '\x2b4553122d960ca98075028d68735cc6b15deeb5'
ARB_PROXY_ADMIN                        = '\x934452d12b24b834877d6096ebdecbbf0e97adda'
OP_PROXY_ADMIN                         = '\x329f5a8d24503fc00b31b229835b6452a6723ae4'
POLY_PROXY_ADMIN                       = '\xd80a8890f5b07cffcd5c939f2c63781ef4fe2642'
BNB_PROXY_ADMIN                        = '\xb8ee2cd0e210fac991e441dba767082d9cdceec3'
AVAX_PROXY_ADMIN                       = '\x04317f0e4795b1e1bab333234153fa10aaac79e9'
RH_PROXY_ADMIN                         = '\x04317f0e4795b1e1bab333234153fa10aaac79e9'

-- ===== Owners (Safe multisigs; Robinhood owner has no code) =====
ETH_OWNER_SAFE                         = '\x520cf70a2d0b3dfb7386a2bc9f800321f62a5c3a'
BASE_OWNER_SAFE                        = '\xf07a1288ab71fa0ffa5ace4d2e8b79b490065008'
ARB_OWNER_SAFE                         = '\x15ca1fc728cce7cd06151c8007e89dee70260228'
OP_OWNER_SAFE                          = '\x09af25ebbfe4606813c451620a5ba356026d41fa'
POLY_OWNER_SAFE                        = '\x249aabb1d67a76404cc1197fa37adaf358b1e212'
BNB_OWNER_SAFE                         = '\x7af3828c0b061552af3479806add982eef04f0c8'
AVAX_OWNER_SAFE                        = '\xb1fdfd298dcaf4e710024c30347af7d4c598c23c'
RH_OWNER_NO_CODE                       = '\x478615f37fccb0df69c191a8674233f6899d092e'   -- no code, nonce 0: an EOA or an undeployed Safe

-- ===== BridgeVMs =====
ETH_BRIDGE_VM                          = '\x0551e6700a0c7c5a1633e912710ed80c88facc07'
BASE_BRIDGE_VM                         = '\x1c128bbd0c70da36a4f13531c92f37d8f1ccc0f2'
ARB_BRIDGE_VM                          = '\xa166d9e596561c23dc9d46d9e24a5a0315f6fac2'
OP_BRIDGE_VM                           = '\x5dcf421bf4c724940c8344c629ffb3abf8011619'
POLY_BRIDGE_VM                         = '\xde52e32f1efc70b9d7c0dedd664c7b7a531e7ac1'
BNB_BRIDGE_VM                          = '\x12ef0730ca80b618c2789e74fab685bed72491f7'
AVAX_BRIDGE_VM                         = '\x4611cacfc562c882efb01bdda1e5326440c07ce2'
RH_BRIDGE_VM                           = '\x4611cacfc562c882efb01bdda1e5326440c07ce2'

-- ===== Operators (EOAs) =====
ETH_OPERATOR_EOA                       = '\x7401e624f0e74d041f2d8a6f1429d8eaa51e208f'   -- authorized on all eight chains
ETH_SWAP_OPERATOR_EOA                  = '\x51497124089abdec0d3749d6db082f66ca03750a'
```

---

## 15. Verification & sources

How the constants in this file were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified implementation source on Ethereum (`contracts/DVFDepositContract.sol`, verified 2026-09-18), the older `rhinofi/contracts_public` source (for `BridgedDeposit` and the legacy functions), the verified OpenZeppelin `ProxyAdmin`, and the verified `SameChainSwaps` implementation. The selectors of the sampled transactions match: `0x2700bbaf` (deposit), `0x9c66c25d` (withdrawal), `0xec8acddf` (withdrawal with data), `0x2090d831` (swap).
- **Addresses:** the bridge per chain comes from the Rhino.fi contract-addresses page and the `/bridge/configs` API (which also gives Robinhood Chain). `eth_getCode` confirms every proxy. The implementation of every bridge has code hash `0x3e9099fb0a2ed123665fc37ab856b69c98b27e0e53d3c6867e682bdb4d7837fc` (13,825 B). The EIP-1967 admin slot gives each ProxyAdmin; `owner()` of the ProxyAdmin equals `owner()` of the bridge on every chain. The Ethereum, Base and Polygon owners return `getThreshold()` = 2; the Ethereum and Base owners hold Safe v1.3.0 singletons in slot 0. The BridgeVM of each chain is read from the bridge's storage slot 105 (`0x69`, the private `vm` field after the OpenZeppelin upgradeable layout); on Ethereum and Base it matches the transfer target of the sampled transactions, and the Ethereum one is verified as `BridgeVM`. All eight have the same 3,375-byte code (hash `0x3c39f095d6fcff747a60bf92318812e2bc85012c4fea89ba874009b4790bd456`). `authorized(0x7401e624f0E74d041F2D8A6f1429D8EaA51E208f)` returns true on all eight chains; `authorized(0x51497124089aBDEc0d3749D6dB082f66ca03750a)` returns true on Ethereum.
- **Value movement, read from receipts:** deposit `0x5b8f94916ac401f5f682faf648a660599d5ff542ba4f07a84863a9cee81384f1` (Ethereum: 134,306.05 USDT user → bridge, then `BridgedDepositWithId`, `sender` = `origin` = the user). Withdrawal `0x81614d01818dccc660ff7ae1471ec70d6ce45c63377657f1ec34e8ba1455eb80` (Ethereum: sent by the operator, 5 USDT bridge → recipient, empty `withdrawalId`). Withdrawal with data `0x350fdab9b2d90a29330a8be634e8c72cbfc821d76f204906bab5e001c5e595cd` (Base). Swap `0x5d6ac3fa62c5db74fbd55bdef53520fc4de0ec4ac21b1d8990d273894616cc3a` (Ethereum).
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, emitter = the bridge):** see §11. `BridgedWithdrawalWithNative` was 0 on all eight chains. `SwapWithData`: Ethereum 2, Avalanche 1, the other chains 0. The Ethereum `BridgedDepositWithId` count (36) was measured twice with the same result. A 0 is a measurement of this window only.
- **Chain coverage:** all eight target chains carry a bridge. Robinhood Chain is confirmed by the config API, the supported-chains page and 288 withdrawals in the window.

Authoritative sources:
- Docs — [Contract addresses](https://docs.rhino.fi/general/contract-addresses) · [EVM contract guide](https://docs.rhino.fi/contracts/evm) · [Making a bridge](https://docs.rhino.fi/api-integration/bridge) · [Bridge status & history](https://docs.rhino.fi/api-integration/status-history) · [Smart Deposit Addresses](https://docs.rhino.fi/get-started/sda) · [Supported chains and tokens](https://docs.rhino.fi/get-started/supported-chains) · [Docs index](https://docs.rhino.fi/llms.txt).
- API — [bridge configs](https://api.rhino.fi/bridge/configs) (`contractAddress`, `multicallContractAddress`, `sameChainSwapsAddress` per chain).
- [rhinofi/contracts_public `bridge-deposit/DVFDepositContract.sol`](https://github.com/rhinofi/contracts_public/blob/master/bridge-deposit/DVFDepositContract.sol) (older version).
- Verified sources on Blockscout — [Ethereum implementation](https://eth.blockscout.com/address/0x7877b41fB0573d1CeD42e995D0f79EcCC1e34d48) · [Ethereum ProxyAdmin](https://eth.blockscout.com/address/0x70911642e4eA509735e77CbA23Ce1856AbeD87Bf) · [Ethereum BridgeVM](https://eth.blockscout.com/address/0x0551e6700a0C7C5a1633E912710ED80c88FACC07) · [Ethereum SameChainSwaps](https://eth.blockscout.com/address/0x242794484D89F46E679a5F88c1544125Ef2507A9).
