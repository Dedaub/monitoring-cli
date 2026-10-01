# UniversalX (Particle Network) — Topics, Selectors, Addresses (Universal Accounts v1 liquidity pools on Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; current v2 contracts not published; NOT Robinhood for v1)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the DefiLlama UniversalX bridge adapter (the only public list of UniversalX pool addresses), the UniversalX and Particle Network docs, the `@particle-network/universal-account-sdk` 3.0.1 package, the Blockscout explorers and sample receipts. Every topic0 and selector was recomputed as `keccak256(signature)`. Every address was existence-checked with `eth_getCode`; proxy slots, `owner()` and `paused()` were read live.
**Scope:** the on-chain liquidity pools of **Universal Accounts v1**, through which UniversalX (Particle Network's chain-abstracted trading app) moved user value between chains, and what is known about the **v2** system that replaced it. Topics and selectors are chain-agnostic. Addresses are network-specific.

**How it works.** A UniversalX user holds a **Universal Account** (UA): an ERC-4337 smart-contract account (v1) or an EIP-7702-delegated EOA (v2, the SDK default since 3.0.0). Deposits are plain transfers to the user's UA address. A cross-chain action is a set of user operations, executed through the ERC-4337 EntryPoint by Particle's bundlers: on the source chain the UA pays into Particle's **liquidity pool** (`Deposited`), and on the destination chain the pool pays the UA (`Released`). Particle's L1 (the Particle Chain) orders and settles these; solvers are operated by Particle.

**Status of v1.** On **2026-04-20** the Ethereum and Base pools were paused, their owner was changed, they were upgraded, and their balances were withdrawn (`Withdrawal`). UniversalX relaunched on Universal Accounts v2 (the docs page "Depositing to Universal Accounts V2": users get a new account address and move their balance). The Polygon pool last logged on 2026-05-26 and the Arbitrum pool on 2026-06-17. **No v1 pool emitted any log in the pinned window.** The v2 liquidity and settlement contracts are not published: the SDK reads them from Particle's server (`universal_getEIP7702Deployments` on `https://universal-rpc-proxy.particle.network`), which requires credentials and a device id. **Current UniversalX flows therefore have no documented contract event; see §7 for the capture.**

---

## 0. Contract families & versions

| Contract | Chains | Role | Proxy? | Status |
|----------|--------|------|--------|--------|
| **Universal Liquidity pool (v1)** | Ethereum (two), Base, Arbitrum, Optimism, Polygon, BNB, Avalanche (+ Linea, Blast, Manta, Mode, Merlin, Conflux, Berachain, Sonic outside the eight) | Holds Particle's liquidity; receives a UA's payment (`Deposited`), pays a UA (`Released`), refunds (`Refunded`); owner withdrawals (`Withdrawal`). Exposes `PAYMASTER()`, `ENTRY_POINT_ADDRESS()`, `getVerifyingSigner()` (ERC-4337 integration). Implementation unverified. | Transparent proxy (EIP-1967) | Retired / idle (§9) |
| **ERC-4337 EntryPoint v0.6** | all EVM chains | Executes the UA user operations (`handleOps`), emits `UserOperationEvent`. Not a Particle contract. | No | Live |
| **Universal Account (v1)** | per user | ERC-4337 smart account; the user's deposit address. | — | Replaced by v2 |
| **Universal Account (v2)** | per user | EIP-7702-delegated EOA (or a classic account); contract addresses served by Particle's server only. | — | Live, unverified |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Universal Liquidity pool (v1)

| topic0 | Event |
|--------|-------|
| `0xb4e1304f97b5093610f51b33ddab6622388422e2dac138b0d32f93dcfbd39edf` | `Deposited(address indexed user, uint256 amount, address tokenAddress)` |
| `0xa8e623c654132d1367fecfb903b1095f106e72026399650b54dbbf24d981d4d1` | `Released(address indexed recipient, uint256 amount, address tokenAddress)` |
| `0xb44b3631755227290f8fbd7b248fa4be405129d15351313e3c332a3fb9919417` | `Refunded(address indexed recipient, uint256 amount, address tokenAddress)` |
| `0x001a143d5b175701cb3246058ffac3d63945192075a926ff73a19930f09d587a` | `Withdrawal(address indexed recipient, uint256 amount, address tokenAddress)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

- `Deposited` — **source leg.** `user` is the Universal Account (topic1). The value moves in the same transaction: ERC-20 `Transfer(user, pool, amount)` (`tokenAddress`).
- `Released` — **destination leg.** ERC-20 `Transfer(pool, recipient, amount)` in the same transaction; `recipient` is a Universal Account.
- `Refunded` — **refund** of a failed operation to `recipient`.
- `Withdrawal` — **owner withdrawal** of pool liquidity (`withdraw(uint256,address,address)`); the sample on Ethereum moved WBTC to the EOA `0x12d5ad9445464f310cce7ea35a56279b409c08b3`. The parameter names of `Withdrawal` are not published (implementation unverified); the first argument is indexed (topic1 = recipient in the sample).
- The parameter names of `Deposited`, `Released` and `Refunded` are those of the DefiLlama adapter ABI.

### 1.2 ERC-4337 EntryPoint (context; same transaction)

| topic0 | Event |
|--------|-------|
| `0x49628fd1471006c1482da88028e9ce4dbb080b815c9b0344d39e5a8e6ec1419f` | `UserOperationEvent(bytes32 indexed userOpHash, address indexed sender, address indexed paymaster, uint256 nonce, bool success, uint256 actualGasCost, uint256 actualGasUsed)` |

`sender` is the Universal Account; `userOpHash` identifies the operation. In both samples, the paymaster was `0xf7bb387ecdea4b8ffff53e6b1a8cd9f93bfbdcc4` (Particle's paymaster, by its role in the UA operations; not in an official list).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Resolved from the `PUSH4` constants of the Ethereum pool implementation `0xab8a2cfc2e4ca8f44cbd0bce309a361bb4c9aeb5` (unverified bytecode); seven further selectors there have no public signature.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb460af94` | `withdraw(uint256 amount, address to, address token)` | Owner path; emits `Withdrawal`. Parameter names inferred. |
| `0x37a66d85` | `setPaused()` | Emits `Paused`. |
| `0x3c89edce` | `setUnpaused()` | Emits `Unpaused`. |
| `0x485cc955` | `initialize(address owner, address signer)` | Proxy initialization. Parameter names inferred. |
| `0x521e47b9` | `getVerifyingSigner()` | `address` — the signer that authorizes pool operations. |
| `0x82c78fb8` | `PAYMASTER()` | `address`. |
| `0xa905054d` | `ENTRY_POINT_ADDRESS()` | `address`. |
| `0xffa1ad74` | `VERSION()` | `uint256` — 2 on the Ethereum pool. |
| `0x5c975abb` | `paused()` | `bool`. |
| `0x8da5cb5b` | `owner()` | `address`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Emits `OwnershipTransferred`. |
| `0x1fad948c` | `handleOps((address sender, uint256 nonce, bytes initCode, bytes callData, uint256 callGasLimit, uint256 verificationGasLimit, uint256 preVerificationGas, uint256 maxFeePerGas, uint256 maxPriorityFeePerGas, bytes paymasterAndData, bytes signature)[] ops, address beneficiary)` | EntryPoint v0.6; the transaction that carries UA operations (both samples). |

---

## 3. Addresses — v1 pools per chain

All are EIP-1967 transparent proxies (1,159 B) deployed by `0xac6a87c681a5ed4cb58bc4fa7bf81a83b928c83c` (EOA) or `0xd77dbd0699582ca487f8519d2fecc4c0b41b78f9` (EOA).

| Chain | Pool (proxy) | Implementation | ProxyAdmin | `owner()` | `paused()` | Last log |
|-------|--------------|----------------|------------|-----------|------------|----------|
| Ethereum (1) | `0x3762a79b34dfb6774cfd45dbf5fd9a2780873783` | `0xab8a2cfc2e4ca8f44cbd0bce309a361bb4c9aeb5` | `0x166fd12e962290250aebf178f60ff0a250e2159c` | `0x82d04d2b250c3e017fcc2e333ec043b6b9bf7c77` (EOA) | true | 2026-04-20 14:35 UTC (`Withdrawal`) |
| Ethereum (1), second pool | `0x5f77b1fe53ba406b0ac3ef10c007a7b16e9f04f6` | `0x9cea88ee39b6cc09c478942bbf83bfa77d87b5f3` | `0x1264b0ae06d196c8d04d39ed0f6dd8081bc599de` | `0xca1d61d78e0790e371413a5192a18c126c420cb3` | false | 2026-04-20 08:20 UTC |
| Base (8453) | `0x73791161b3d3a6fedf2b17fb79810b277c5ce517` | `0xc1320dae6bfa1d58c1464216c344310b10ab865c` | `0x0b96a2086c5b7902cc657cc51deeedb5532fb92b` | `0x82d04d2b250c3e017fcc2e333ec043b6b9bf7c77` (EOA) | true | 2026-04-20 14:34 UTC |
| Arbitrum One (42161) | `0x5f77b1fe53ba406b0ac3ef10c007a7b16e9f04f6` | `0xac22e322cf2c0491572d0cf84e4093b3457a7ad4` | `0x1264b0ae06d196c8d04d39ed0f6dd8081bc599de` | `0x82d04d2b250c3e017fcc2e333ec043b6b9bf7c77` (EOA) | false | 2026-06-17 16:56 UTC |
| Optimism (10) | `0x5535df3a1f2b2ce2eb3b6673638833420bc79cad` | `0xdc85db1f2c49edf1e59186736fe9e43ab0641c80` | `0x1d2dcaa1c47a4b025ecd1b61981f3537d3b12150` | `0xdf51b03712c9b398de18dfb4c60c9e1bbcaa2e0e` | false | not read |
| BNB Smart Chain (56) | `0x9cea88ee39b6cc09c478942bbf83bfa77d87b5f3` | `0xbd82cd2aafd2105889a0068130d772aa0cd8217d` | `0x233a97684bc93ec674168a0d9ba496935eb08cb3` | `0xdf51b03712c9b398de18dfb4c60c9e1bbcaa2e0e` | false | not read |
| Polygon PoS (137) | `0xde5af64abc426d63c3bcf13d8f672948227a745a` | `0xd75c7d6534f6054a5573297b2f57c07bcbe6ed58` | `0xe3c609aedfe582ab3a96806f959a7372c3c17589` | `0xdf51b03712c9b398de18dfb4c60c9e1bbcaa2e0e` | false | 2026-05-26 14:41 UTC |
| Avalanche C-Chain (43114) | `0xde5af64abc426d63c3bcf13d8f672948227a745a` | `0xb29aa971984f8b1a124e2a76334b9f519bd6ab35` | `0xe3c609aedfe582ab3a96806f959a7372c3c17589` | `0xdf51b03712c9b398de18dfb4c60c9e1bbcaa2e0e` | false | not read |
| Robinhood Chain (4663) | — | — | — | — | — | `eth_getCode` = `0x` at every pool address |

**Same address, other contracts.** `0x3762a79b34dfb6774cfd45dbf5fd9a2780873783` and `0x73791161b3d3a6fedf2b17fb79810b277c5ce517` also have code on Polygon (same deployer); they logged only their own deployment (initialization, upgrade, ownership) and no pool event. `0x3762a79b34dfb6774cfd45dbf5fd9a2780873783` on Arbitrum is a 15,293 B non-proxy contract. `0x9cea88ee39b6cc09c478942bbf83bfa77d87b5f3` on Ethereum is the second pool's implementation, not a pool.

**Rejected leads** (contracts that emit the same `Deposited(address,uint256,address)` topic): BNB `0xde7080148044e659fefba3c650c9b16090cb5ecd` (94 `Deposited` in the window; a proxy whose implementation has `Deposited` but no `Released`, `Refunded` or `Paused` topic, with another admin `0x40497b0b682118c82737fd75a23720405c9d0c11` and owner `0x477f05d5382d722d6f23167dd3d3bbe296d4aa47`); BNB `0xa53b869c883b5036ddf8d7a12b7618e4612c503e` (4 in the window, not in any UniversalX list); Polygon `0xea459c173753da4126e665530e6c82ccb7bf370a` (verified `Pyromancy`, an unrelated game). None is a UniversalX contract by any source.

**Particle operators seen in the samples** (EOAs; not in an official list): bundlers `0x7f0fa0bab21c6749f12116aa8cbab7bbae8f50f2` and `0x596680f2ea1bdb041570c74fb5fc8c0c0a9fad80` (funded by the pool deployer `0xac6a87c681a5ed4cb58bc4fa7bf81a83b928c83c`), the `withdraw` caller `0xdf51b03712c9b398de18dfb4c60c9e1bbcaa2e0e`.

---

## 4. Cross-chain summary

| Chain | ID | v1 pool | Window logs (§9) | v2 (UniversalX today) |
|-------|----|---------|------------------|-----------------------|
| Ethereum | 1 | `0x3762a79b34dfb6774cfd45dbf5fd9a2780873783`, `0x5f77b1fe53ba406b0ac3ef10c007a7b16e9f04f6` | 0 | supported chain; contracts unpublished |
| Base | 8453 | `0x73791161b3d3a6fedf2b17fb79810b277c5ce517` | 0 | supported; unpublished |
| Arbitrum One | 42161 | `0x5f77b1fe53ba406b0ac3ef10c007a7b16e9f04f6` | 0 | supported; unpublished |
| Optimism | 10 | `0x5535df3a1f2b2ce2eb3b6673638833420bc79cad` | 0 | not in the v2 chain list |
| Polygon PoS | 137 | `0xde5af64abc426d63c3bcf13d8f672948227a745a` | 0 pool events | not in the v2 chain list |
| BNB Smart Chain | 56 | `0x9cea88ee39b6cc09c478942bbf83bfa77d87b5f3` | 0 pool events | supported; unpublished |
| Avalanche C-Chain | 43114 | `0xde5af64abc426d63c3bcf13d8f672948227a745a` | 0 pool events | not in the v2 chain list |
| Robinhood Chain | 4663 | — (`0x`) | — | **supported by the SDK 3.0.1** (EIP-7702 mode only; USDG `0x5fc5360d0400a0fd4f2af552add042d716f1d168`); contracts unpublished |

Universal Accounts v2 chains (Particle docs and SDK 3.0.1): Ethereum, BNB, Base, Arbitrum, X Layer, Robinhood Chain, Solana. Primary assets: ETH, USDT, USDC, SOL, BNB, and USDG on Robinhood. UniversalX uses EVM chain ids (Solana = 101 in the SDK).

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority |
|----------|---------|-----------|-------------------|
| v1 pools | **Transparent proxy** (EIP-1967, 1,159 B) | Implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` set (§3); admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = a ProxyAdmin per pool (§3); `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. | The ProxyAdmin's owner (not read). `owner()` of the pool controls `withdraw`, pause and the signer. The Ethereum and Base pools were upgraded on 2026-04-20 (Ethereum: `Upgraded` to `0xab8a2cfc2e4ca8f44cbd0bce309a361bb4c9aeb5` in block 24,921,716) before the final `Withdrawal`. |

---

## 6. Detection invariants & gotchas

1. **`Deposited` / `Released` are a generic signature.** Many unrelated contracts emit `Deposited(address,uint256,address)` (in the window: 94 logs from one BNB contract, 4 from another, 1 from a Polygon game, 0 from any UniversalX pool). Always filter by the pool addresses of §3.
2. **The user is a Universal Account, not an EOA.** `Deposited.user` and `Released.recipient` are UA smart-account addresses; the transaction is `handleOps` on the EntryPoint, sent by a Particle bundler. The owner EOA of the UA is not in the pool event.
3. **No on-chain link key.** A source `Deposited` and a destination `Released` are joined only by Particle's settlement (Particle Chain / API). On chain the best join is the UA address (`user` = `recipient`), the token and the amount, which is a heuristic. In the Ethereum sample, a `Deposited` and a `Released` for the same UA appear in one transaction.
4. **v1 is retired on Ethereum and Base, idle elsewhere.** The Ethereum and Base pools are paused and were drained by `Withdrawal` on 2026-04-20. A monitor of the v1 pools today sees owner and admin actions only.
5. **Current UniversalX value moves without a documented contract.** Users deposit by plain transfer (ERC-20 `Transfer` or native value) to their own UA address; cross-chain payouts come from Particle's solvers. Without Particle's published v2 addresses, the capture is: transfers **to a known UA address** (from the UniversalX app or the SDK `getSmartAccountOptions`), and transfers from the bundler and operator EOAs of §3. The addresses of the v2 liquidity sources are **unverified and not listed here**.
6. **Admin actions:** `Paused`, `OwnershipTransferred`, `Upgraded`, `AdminChanged` and `Withdrawal` on a pool. `Withdrawal` moves pool liquidity to an arbitrary recipient.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== v1 pool topics =====
TOPIC_UNIVERSALX_DEPOSITED        = '\xb4e1304f97b5093610f51b33ddab6622388422e2dac138b0d32f93dcfbd39edf'
TOPIC_UNIVERSALX_RELEASED         = '\xa8e623c654132d1367fecfb903b1095f106e72026399650b54dbbf24d981d4d1'
TOPIC_UNIVERSALX_REFUNDED         = '\xb44b3631755227290f8fbd7b248fa4be405129d15351313e3c332a3fb9919417'
TOPIC_UNIVERSALX_WITHDRAWAL       = '\x001a143d5b175701cb3246058ffac3d63945192075a926ff73a19930f09d587a'
TOPIC_PAUSED                      = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED               = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_ERC4337_USER_OPERATION      = '\x49628fd1471006c1482da88028e9ce4dbb080b815c9b0344d39e5a8e6ec1419f'
-- ===== Selectors =====
SEL_UNIVERSALX_POOL_WITHDRAW      = '\xb460af94'
SEL_UNIVERSALX_POOL_SET_PAUSED    = '\x37a66d85'
SEL_ERC4337_HANDLE_OPS_V06        = '\x1fad948c'
-- ===== v1 pools (network-specific) =====
ETH_UNIVERSALX_POOL               = '\x3762a79b34dfb6774cfd45dbf5fd9a2780873783'
ETH_UNIVERSALX_POOL_2             = '\x5f77b1fe53ba406b0ac3ef10c007a7b16e9f04f6'
BASE_UNIVERSALX_POOL              = '\x73791161b3d3a6fedf2b17fb79810b277c5ce517'
ARB_UNIVERSALX_POOL               = '\x5f77b1fe53ba406b0ac3ef10c007a7b16e9f04f6'
OP_UNIVERSALX_POOL                = '\x5535df3a1f2b2ce2eb3b6673638833420bc79cad'
BNB_UNIVERSALX_POOL               = '\x9cea88ee39b6cc09c478942bbf83bfa77d87b5f3'
POLY_UNIVERSALX_POOL              = '\xde5af64abc426d63c3bcf13d8f672948227a745a'
AVAX_UNIVERSALX_POOL              = '\xde5af64abc426d63c3bcf13d8f672948227a745a'
-- ===== Operators seen in samples (EOAs; not officially listed) =====
ETH_UNIVERSALX_POOL_OWNER_EOA     = '\x82d04d2b250c3e017fcc2e333ec043b6b9bf7c77'
ETH_UNIVERSALX_DEPLOYER_EOA       = '\xac6a87c681a5ed4cb58bc4fa7bf81a83b928c83c'
ETH_UNIVERSALX_BUNDLER_1_EOA      = '\x7f0fa0bab21c6749f12116aa8cbab7bbae8f50f2'
ETH_UNIVERSALX_BUNDLER_2_EOA      = '\x596680f2ea1bdb041570c74fb5fc8c0c0a9fad80'
ETH_UNIVERSALX_OPERATOR_EOA       = '\xdf51b03712c9b398de18dfb4c60c9e1bbcaa2e0e'
ETH_UNIVERSALX_PAYMASTER          = '\xf7bb387ecdea4b8ffff53e6b1a8cd9f93bfbdcc4'
ETH_ERC4337_ENTRYPOINT_V06        = '\x5ff137d4b0fdcd49dca30c7cf57e578a026d2789'
-- Robinhood (4663): no v1 pool; v2 contracts unpublished
```

---

## 8. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)`. `Deposited`, `Released`, `Refunded`: from the DefiLlama adapter ABI, and found in the live logs and in the BNB pool implementation bytecode. `Withdrawal(address,uint256,address)`: resolved from the live topic in the public signature database and seen in the Ethereum receipt. Pool selectors: resolved from the `PUSH4` constants of the Ethereum implementation. The pool implementations are not verified on any explorer.
- **Addresses:** the DefiLlama UniversalX bridge adapter (commits of 2024-12-04, 2025-02-19, 2025-03-03); `eth_getCode` on all eight chains; EIP-1967 slots, `owner()`, `paused()`, `VERSION()` read live; last-log dates from the Blockscout block timestamps.
- **Current contracts searched:** the UniversalX docs (Universal Account, Depositing to Universal Accounts V2, FAQ), the Particle docs (Technology / Universal Liquidity, Chains), the Universal Account SDK 3.0.1 package (it contains only token addresses and the server URL), the Particle server (`universal_getEIP7702Deployments` returns "device ID is required"), and an explorer name search. No published v2 settlement or liquidity contract was found.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC** (all logs of each pool): Ethereum 0 (both pools), Base 0, Arbitrum 0, Optimism 0. BNB, Polygon and Avalanche: 0 `Deposited`, `Released` and `Refunded` logs from the pool (topic counts over all emitters in the window; the only emitters were the rejected leads of §3). The same query returned 42 logs for the Aori contract on Ethereum in this window (positive control).
- **Sample transactions (receipts read, Ethereum):** `Deposited` `0xfe0f6f4258d44651fb7f20bc3133bd5d340ca62b5ce88174629bb2f9a3f0734d` (block 24,921,381; `handleOps`; USDC `Transfer` UA `0x033067bc795989c9a8b2f9c95124d04c8a7a16de` to the pool; `Deposited` and `Released` for the same UA; `UserOperationEvent`). `Released` `0x41a26b160d022b868b1a469a9cee602d5fd2a086901bbbee915cfe146fbddfb8` (block 24,921,389; USDC `Transfer` pool to UA `0xdbc84977a9c7eb7c1abc74a61a86c6afb58b552d`). `Withdrawal` `0xf1275fae6c0b390a872131f51947739e68d1e58d5c6f663ded5180b126c2df20` (block 24,921,745; `withdraw` by `0xdf51b03712c9b398de18dfb4c60c9e1bbcaa2e0e`; WBTC to `0x12d5ad9445464f310cce7ea35a56279b409c08b3`).

Authoritative sources:
- [DefiLlama bridges-server adapter `universalx`](https://github.com/DefiLlama/bridges-server/tree/master/src/adapters/universalx).
- UniversalX docs — [Universal Account](https://docs.universalx.app/universal-account) · [Depositing to Universal Accounts V2](https://docs.universalx.app/use/depositing-to-universal-accounts-v2) · [FAQ](https://docs.universalx.app/more-info-1/frequently-asked-questions-faqs).
- Particle docs — [Technology / Universal Liquidity](https://developers.particle.network/intro/what-is-ul) · [Chains and Primary Assets](https://developers.particle.network/universal-accounts/chains); npm [`@particle-network/universal-account-sdk`](https://www.npmjs.com/package/@particle-network/universal-account-sdk) 3.0.1 (CHANGELOG).
- Explorers — [Ethereum pool](https://eth.blockscout.com/address/0x3762a79b34dfb6774cfd45dbf5fd9a2780873783) · [Base pool](https://base.blockscout.com/address/0x73791161b3d3a6fedf2b17fb79810b277c5ce517) · [Arbitrum pool](https://arbitrum.blockscout.com/address/0x5f77b1fe53ba406b0ac3ef10c007a7b16e9f04f6) · [Polygon pool](https://polygon.blockscout.com/address/0xde5af64abc426d63c3bcf13d8f672948227a745a).
