# EVO DeFi Bridge — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche; not Base or Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the verified explorer source of `BridgePool` (`0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f`), `EvoProxy` (`0x9983d8cdeaf7872501628229d311e2f7df396add`) and `EvoBridgeV2` (`0x62cd928b16b7a92101c3091f5136fd9bb017870a`), the Verilog Solutions analysis (2022-04-29) and the RugDoc update (2022-07-22).
**Scope:** the EVO DeFi cross-chain bridge: the first-generation **BridgePool** (2021 to May 2022), the second-generation **EvoBridgeV2** behind an **EvoProxy** (from June 2022), and a third pool contract on Optimism. The same literals exist on Ethereum (1), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56) and Avalanche C-Chain (43114). **Base (8453) and Robinhood Chain (4663) have none.** Topics and selectors are chain-agnostic; addresses are network-specific.

**The bridge failed.** RugDoc (2022-07-22) reports that the EVO DeFi bridge became insolvent and closed, with about $50 million of user funds trapped, after the team invested user funds in Terra's Anchor and minted unbacked USDT; the affected chains it names are BNB, Polygon and Oasis Emerald. Verilog (2022-04-29) found "high centralization risks": one owner and three "taker" addresses that could move all pool funds with `take()`, about $37.8 million at that time. On chain, EvoBridgeV2 kept processing some deposits and withdrawals after July 2022: Ethereum deposits until block 17,936,111 (2023-08-17) and Polygon withdrawals until block 51,522,231 (2023-12-25) (explorer transaction lists).

EVO is a **custodial lock-and-release bridge**: a user deposits into the pool contract on the source chain (`Deposited`), and an operator (BridgePool) or signer (EvoBridgeV2) pays the user from the pool on the destination chain in a batch (`Withdrawn`). No message proof exists on chain: the operator is the bridge. The contracts are deployed at **the same literal on every chain** (deterministic deployer `0x3350A9dbad8DE3E78bE646b87C12CeD56C929a84`), with the same owner EOA `0x40e0dcd7024030c7b5e1d474fe95aaf7bb880ad0`.

---

## 0. Contract families and the flow

| Contract | Address (same on ETH, ARB, OP, POLY, BNB, AVAX) | Period (explorer activity) | Proxy? |
|----------|------------------------------------------------|----------------------------|--------|
| **BridgePool** | `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` (8,791 B) | 2021 to May 2022; `take` calls on 2022-05-03 (Arbitrum, Optimism) and 2023-06-06 (Ethereum) | No (immutable; `owner` + operator modes) |
| **EvoProxy** → **EvoBridgeV2** | `0x9983d8cdeaf7872501628229d311e2f7df396add` (1,887 B) → implementation `0x62cd928b16b7a92101c3091f5136fd9bb017870a` | From June 2022 (Arbitrum) to 2023 and 2024 | EIP-1967 proxy, admin = ProxyAdmin |
| ProxyAdmin | `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb` (2,632 B) | — | Verified `ProxyAdmin` |
| **Optimism pool (third contract)** | `0x7cca0859058aa03301106ab8aba1707a16a30821` (Optimism only; 1,554 B EIP-1967 proxy, implementation `0x30fe403d12f9a1f680b915f030b291b9b5a202bb`, unverified) | 2022-04-21 to 2022-05-03 | Admin `0x5af70645fd7d5d52030765a324e329fe7e181c44`; `owner()` = the EVO owner EOA |

| Step | Caller | Function | Event | Value movement in the same transaction |
|------|--------|----------|-------|----------------------------------------|
| Deposit (source leg) | the user (an EOA; contracts only if allowed) | `deposit` | `Deposited` | Native coin: `msg.value`, with `token` = `0x0000000000000000000000000000000000000001`. ERC-20: `Transfer` user to the pool contract. EvoBridgeV2 burns its "owned" tokens instead (`Transfer` to `0x0`). |
| Payout (destination leg) | BridgePool operator (mode 4) / EvoBridgeV2 signer | `withdraw` (a batch) | `Withdrawn` per item | `Transfer` from the pool contract to `recipient` (or native coin), plus an optional native `bonus` and fee transfers to `feeTargets`; EvoBridgeV2 mints owned tokens. |
| Refund | — | none | none | No refund path on chain. |
| Drain | BridgePool taker (mode 8) | `take` | **none** | Pool funds to any address, with no event: watch the pool's outgoing `Transfer` logs and native transfers. |

**Link key.** `Withdrawn.id` (topic1) is EVO's off-chain transfer id; the source `Deposited` carries no id. Join a deposit to a payout only through the off-chain id, or by (`recipient`, token, amount, time). The id is not derived from the deposit on chain (unverified scheme).

**Chain index.** `to` (topic3 of `Deposited`) is EVO's own chain index, not an EVM chain id. The contracts do not define it. An older third-party data set maps it as 0 BSC, 1 Polygon, 2 Fantom, 3 HECO, 5 Ethereum, 6 Avalanche, 7 Arbitrum, 8 Solana, 9 Tron, 10 Cronos, 11 Bitcoin, 12 Moonriver, 13 OKC, 14 Terra, 15 Harmony, 16 Gnosis, 17 Optimism, 18 Oasis Emerald, 19 Hoo: **unverified** (no EVO source confirms it). Measured values: `to` = 10 on the Ethereum native deposit of §9 and `to` = 1 on the EvoBridgeV2 deposit of §9.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 BridgePool, EvoBridgeV2 and the Optimism pool — the same two events

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xfeb2da6e3bb63ff64c908271c247558271e7ef50ee44055f410c2bd554552b4e` | `Deposited(address indexed sender, address indexed token, uint8 indexed to, uint256 amount, bool bonus, bytes recipient)` | **Source leg.** `token` = `0x0000000000000000000000000000000000000001` for the native coin (ETH, BNB, ...); `to` = EVO's own chain index; `recipient` = raw bytes (20 bytes for EVM). Both contracts. Verified live. |
| `0xa6786aab7dbbc48b4b0387488b407bd81448030ab207b50bea7dbb5fbc1cd9eb` | `Withdrawn(bytes32 indexed id, address indexed token, address indexed recipient, uint256 amount)` | **Destination leg.** `id` is EVO's off-chain transfer id; one `withdraw` call emits one event per item of the batch. Both contracts. Verified live. |

### 1.2 EvoProxy (admin, status only)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | EvoProxy: implementation change. **Admin event.** |
| `0x7ce7ec0b50378fb6c0186ffb5f48325f6593fcb4ca4386f21861af3129188f5c` | `AdminChanged(address indexed admin)` | EvoProxy (non-standard one-argument form, not the OpenZeppelin `AdminChanged(address,address)`). |

`Withdrawn(bytes32,address,address,uint256)` is a generic signature. In the pinned window it came only from other contracts (§7, item 6). Always filter by the EVO addresses.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x90cfe778` | `deposit(address token, uint256 amount, uint8 to, bool bonus, bytes recipient)` | `payable`; both contracts. Native coin: `token` = `0x0000000000000000000000000000000000000001` and `msg.value = amount`. Otherwise ERC-20 `Transfer` user to the contract (EvoBridgeV2 burns its own "owned" tokens instead). Callers must be EOAs or allowed contracts. |
| `0x94241002` | `withdraw((bytes32 id, address token, uint256 amount, uint256 bonus, address recipient, uint256[] feeAmounts, address[] feeTargets)[] ws)` | BridgePool: operators with mode 4 (or mode 2 under a mode-4 `tx.origin`). Pays `amount` (+ native `bonus`, + fees to `feeTargets`). Emits `Withdrawn` per item. |
| `0x8c3cd29b` | `withdraw((bytes32 id, address token, uint256 amount, uint256 bonus, address recipient, uint256[] feeAmounts, address[] feeTargets, bytes data)[] ws)` | EvoBridgeV2: `isSigner` only. Pays or mints; optional call to an allowed recipient contract with `data`. Emits `Withdrawn` per item. |
| `0x8033d687` | `take(address token, uint256 amount, address to)` | BridgePool, operator mode 8 ("taker") only. **Moves pool funds out with no event.** |
| `0x4b63d0a1` | `setOperatorMode(address account, uint8 mode)` | BridgePool, owner only: 1 contract creator, 2 contract withdrawer, 4 withdrawer, 8 taker. No event. |
| `0x13af4035` | `setOwner(address newOwner)` | Both contracts, owner only. No event. |
| `0x31cb6105` | `setSigner(address account, bool state)` | EvoBridgeV2, owner only. No event. |
| `0x9f839c80` | `setIsOwnedToken(address token, bool _owned)` | EvoBridgeV2, owner only: the token is minted and burned instead of held. No event. |
| `0xfc1fae68` | `setSenderContract(address account, bool state)` | EvoBridgeV2, owner only. |
| `0x7597bf46` | `setRecipientContract(address account, bool state)` | EvoBridgeV2, owner only. |
| `0x9a307391` | `operator(address account)` | BridgePool view: the operator mode. |
| `0x3823d66c` | `withdrawn(bytes32 id)` | BridgePool view: `true` when `id` was paid. |
| `0x0e3a918c` | `isWithdrawn(bytes32 id)` | EvoBridgeV2 view. |
| `0x7df73e27` | `isSigner(address account)` | EvoBridgeV2 view. |
| `0x8da5cb5b` | `owner()` | Both contracts. |
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | EvoProxy, admin only. Emits `Upgraded`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | EvoProxy, admin only. |

---

## 3. Addresses — the six chains with EVO contracts

All verified with `eth_getCode` on 2026-09-29. The BridgePool has the same size (8,791 B) on every chain; the EvoProxy has the same size (1,887 B) and the same implementation `0x62cd928b16b7a92101c3091f5136fd9bb017870a` on every chain (EIP-1967 slot); `owner()` and the admin slot were read on every chain.

| Chain | ID | BridgePool | EvoProxy (EvoBridgeV2) | ProxyAdmin | Owner (EOA) and nonce |
|-------|----|------------|------------------------|------------|-----------------------|
| Ethereum | 1 | `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` | `0x9983d8cdeaf7872501628229d311e2f7df396add` | `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb` | `0x40e0dcd7024030c7b5e1d474fe95aaf7bb880ad0`, 1,183 |
| Arbitrum One | 42161 | `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` | `0x9983d8cdeaf7872501628229d311e2f7df396add` | `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb` | the same EOA, 78 |
| Optimism | 10 | `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` | `0x9983d8cdeaf7872501628229d311e2f7df396add` | `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb` | the same EOA, 43 |
| Polygon PoS | 137 | `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` | `0x9983d8cdeaf7872501628229d311e2f7df396add` | `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb` | the same EOA, 1,123 |
| BNB Smart Chain | 56 | `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` | `0x9983d8cdeaf7872501628229d311e2f7df396add` | `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb` | the same EOA, 1,706 |
| Avalanche C-Chain | 43114 | `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` | `0x9983d8cdeaf7872501628229d311e2f7df396add` | `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb` | the same EOA, 148 |

Optimism also has the third pool `0x7cca0859058aa03301106ab8aba1707a16a30821` (§0); `eth_getCode` returns `0x` at that literal on the other seven chains.

Taker addresses named by Verilog (operator mode 8 on the BridgePool), all EOAs: `0xf758E719d88862F87585F20Acc81417Cae72Df22`, `0x40E0DcD7024030c7b5E1d474fe95Aaf7Bb880ad0` (the owner), `0x2074fF8f6625A9eEE2e3Eac2Fd658df18A5C5166`. Their nonces on 2026-09-29: BNB 994 / 1,706 / 793, Polygon 323 / 1,123 / 324, Ethereum 331 / 1,183 / 133.

## 4. Base (chain ID 8453) and Robinhood Chain (chain ID 4663) — no deployment

`eth_getCode` returns `0x` (nonce 0) on both chains at the BridgePool, EvoProxy, ProxyAdmin and Optimism-pool literals, and the owner and taker addresses have nonce 0 there. Both chains launched after the bridge closed.

---

## 5. Cross-chain summary

| Chain | ID | BridgePool | EvoBridgeV2 (proxy) | Other |
|-------|----|------------|---------------------|-------|
| Ethereum | 1 | ✅ `0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f` | ✅ `0x9983d8cdeaf7872501628229d311e2f7df396add` | — |
| Base | 8453 | — | — | — |
| Arbitrum One | 42161 | ✅ same literal | ✅ same literal | — |
| Optimism | 10 | ✅ same literal | ✅ same literal | third pool `0x7cca0859058aa03301106ab8aba1707a16a30821` |
| Polygon PoS | 137 | ✅ same literal | ✅ same literal | — |
| BNB Smart Chain | 56 | ✅ same literal | ✅ same literal | — |
| Avalanche C-Chain | 43114 | ✅ same literal | ✅ same literal | — |
| Robinhood Chain | 4663 | — | — | — |

Chains outside the eight that Verilog lists for the bridge: Fantom, Oasis Emerald, Cronos, Moonriver, HECO, Gnosis, HarmonyONE and OKExChain.

---

## 6. Proxies (old and new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| BridgePool | Immutable | 8,791 B; no implementation slot. | None. `owner` sets operator modes (`setOperatorMode`) with no event. |
| EvoProxy | EIP-1967 (custom `EvoProxy`) | 1,887 B; implementation slot = `0x62cd928b16b7a92101c3091f5136fd9bb017870a`; admin slot = `0x961cad906ead6aa183f3d27454a9e763e8b7d3eb`. | The verified `ProxyAdmin` (deployed by `0x3350A9dbad8DE3E78bE646b87C12CeD56C929a84`). Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. |
| EvoBridgeV2 (logic) | Implementation | `owner()` through the proxy = `0x40e0dcd7024030c7b5e1d474fe95aaf7bb880ad0`. | The owner sets signers and token modes with no event. |
| Optimism pool | EIP-1967 proxy | Implementation `0x30fe403d12f9a1f680b915f030b291b9b5a202bb` (5,141 B, unverified), admin `0x5af70645fd7d5d52030765a324e329fe7e181c44` (2,758 B). | Its admin. |

---

## 7. Detection invariants and gotchas

1. **One literal, six chains.** The BridgePool and the EvoProxy have the same addresses on Ethereum, Arbitrum, Optimism, Polygon, BNB and Avalanche. Key on `(chainId, address)` and decode `to` to find the other side.
2. **Native coin is `address(1)`.** `Deposited.token` and `Withdrawn.token` = `0x0000000000000000000000000000000000000001` mean ETH, BNB, MATIC or AVAX; the amount is in `msg.value` or an internal transfer, with no `Transfer` log.
3. **`take()` and all admin changes emit nothing.** Pool funds left through `take` (selector `0x8033d687`) by the owner and takers (for example on 2022-05-03 on Arbitrum and Optimism, and on 2023-06-06 on Ethereum). A monitor must watch outgoing token and native transfers of the pool contracts.
4. **`Withdrawn` is per item; `withdraw` is a batch.** One transaction pays several recipients and tokens, plus `bonus` (native) and fees to `feeTargets`; the `amount` in the event excludes the bonus and fees.
5. **No on-chain link key on the source side.** `Withdrawn.id` exists only on the destination; deposits have no id.
6. **Generic `Withdrawn` topic.** In the pinned window, `Withdrawn(bytes32,address,address,uint256)` came from `0x72d04e0760e07511f81121e9ef45408e37617aa4` on Base (verified `RobinhoodChurnProxy`, not EVO) and from `0xfe006acf268f944aa2d03b7b4943e1a3b57a0efd` on BNB (3,794 B, a bytecode that is not an EVO contract; not identified). Neither is EVO.
7. **EvoBridgeV2 can mint and burn.** For tokens marked with `setIsOwnedToken`, deposits burn (`Transfer` to `0x0`) and payouts mint (`Transfer` from `0x0`): the pool holds no balance of those tokens.
8. **The bridge is insolvent and closed (2022), but the contracts still work.** Deposits after the closure may never be paid. Treat any new `Deposited` as funds sent to a failed custodian.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics =====
TOPIC_EVO_DEPOSITED              = '\xfeb2da6e3bb63ff64c908271c247558271e7ef50ee44055f410c2bd554552b4e'
TOPIC_EVO_WITHDRAWN              = '\xa6786aab7dbbc48b4b0387488b407bd81448030ab207b50bea7dbb5fbc1cd9eb'
TOPIC_EVO_PROXY_UPGRADED         = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_EVO_PROXY_ADMIN_CHANGED    = '\x7ce7ec0b50378fb6c0186ffb5f48325f6593fcb4ca4386f21861af3129188f5c'

-- ===== Selectors =====
SEL_EVO_DEPOSIT                  = '\x90cfe778'
SEL_EVO_POOL_WITHDRAW            = '\x94241002'
SEL_EVO_V2_WITHDRAW              = '\x8c3cd29b'
SEL_EVO_TAKE                     = '\x8033d687'
SEL_EVO_SET_OPERATOR_MODE        = '\x4b63d0a1'
SEL_EVO_SET_SIGNER               = '\x31cb6105'

-- ===== BridgePool (same literal on 6 chains) =====
ETH_EVO_BRIDGE_POOL              = '\x06c30af8a82aaf9cfd319f8644584276bfbec42f'
ARB_EVO_BRIDGE_POOL              = '\x06c30af8a82aaf9cfd319f8644584276bfbec42f'
OP_EVO_BRIDGE_POOL               = '\x06c30af8a82aaf9cfd319f8644584276bfbec42f'
POLY_EVO_BRIDGE_POOL             = '\x06c30af8a82aaf9cfd319f8644584276bfbec42f'
BNB_EVO_BRIDGE_POOL              = '\x06c30af8a82aaf9cfd319f8644584276bfbec42f'
AVAX_EVO_BRIDGE_POOL             = '\x06c30af8a82aaf9cfd319f8644584276bfbec42f'
-- ===== EvoProxy -> EvoBridgeV2 (same literal on 6 chains) =====
ETH_EVO_BRIDGE_V2                = '\x9983d8cdeaf7872501628229d311e2f7df396add'
ARB_EVO_BRIDGE_V2                = '\x9983d8cdeaf7872501628229d311e2f7df396add'
OP_EVO_BRIDGE_V2                 = '\x9983d8cdeaf7872501628229d311e2f7df396add'
POLY_EVO_BRIDGE_V2               = '\x9983d8cdeaf7872501628229d311e2f7df396add'
BNB_EVO_BRIDGE_V2                = '\x9983d8cdeaf7872501628229d311e2f7df396add'
AVAX_EVO_BRIDGE_V2               = '\x9983d8cdeaf7872501628229d311e2f7df396add'
ETH_EVO_BRIDGE_V2_IMPL           = '\x62cd928b16b7a92101c3091f5136fd9bb017870a'
ETH_EVO_PROXY_ADMIN              = '\x961cad906ead6aa183f3d27454a9e763e8b7d3eb'
-- ===== Optimism third pool =====
OP_EVO_POOL_3                    = '\x7cca0859058aa03301106ab8aba1707a16a30821'
-- ===== EOAs (owner and takers; the same on every chain) =====
ETH_EVO_OWNER_EOA                = '\x40e0dcd7024030c7b5e1d474fe95aaf7bb880ad0'
ETH_EVO_TAKER_1_EOA              = '\xf758e719d88862f87585f20acc81417cae72df22'
ETH_EVO_TAKER_3_EOA              = '\x2074ff8f6625a9eee2e3eac2fd658df18a5c5166'
-- Base (8453) and Robinhood Chain (4663): no EVO contract
```

---

## 9. Verification and sources

Pinned 12-hour window 2026-09-28 00:00 to 12:00 UTC, any emitter: `Deposited` — Ethereum 0, Base 0, Arbitrum 0, Optimism 0, Polygon 0, BNB 0, Avalanche 0, Robinhood 0. `Withdrawn` — Ethereum 0, Base 1, Arbitrum 0, Optimism 0, Polygon 0, BNB 19, Avalanche 0, Robinhood 0; the Base and BNB logs come from non-EVO contracts (§7, item 6), so the EVO addresses emitted 0 on every chain.

Explorer log pages (the latest 50 logs of each contract): Ethereum BridgePool 21 `Deposited` and 29 `Withdrawn` (latest `Deposited` at block 15,131,766); Ethereum EvoBridgeV2 17 and 33 (latest `Deposited` at block 17,936,111); Polygon BridgePool 25 and 25; Polygon EvoBridgeV2 25 and 25 (latest `Deposited` at block 59,619,371, 2024-07-21); Arbitrum BridgePool 26 and 24; Arbitrum EvoBridgeV2 28 and 22; Optimism EvoBridgeV2 34 and 16; Optimism third pool 26 and 24.

How the constants were verified (2026-09-29):

- **Topic0 and selectors:** recomputed as `keccak256(canonical signature)` from the verified `BridgePool.sol` and `IBridgePool.sol` (compiler 0.8.10), `EvoBridgeV2.sol` (0.8.13) and `EvoProxy.sol` (0.8.13). The `withdraw` selectors `0x94241002` (BridgePool) and `0x8c3cd29b` (EvoBridgeV2) and `deposit` `0x90cfe778` equal the selectors of the sample transactions below; `take` `0x8033d687` equals the Ethereum `take` transaction.
- **Sample transactions read with `eth_getTransactionReceipt` (Ethereum):** `0xc02b8fc6400689f4838946be8e6d932bb2830de7b33fbd6484c0063825554c64` (BridgePool native `deposit`: 0.98 ETH in `msg.value`, `token` = `address(1)`, `to` = 10, 20-byte recipient); `0x158d1bae1c9f0ac960a8ec3f6d98c07888c2c04b014104d498370a361ffa54e2` (BridgePool `withdraw`: USDC `Transfer` from the pool, `Withdrawn`); `0x711158d0be71118bb82d2dba9165eb882f5abb1d8dee5522ef9d7babdac2b28a` (EvoBridgeV2 `deposit`: token `Transfer` user to the proxy, `to` = 1); `0x466179db5727cd229ddaa5f40a54d79659a0de6a9ccb18f99a86c68ed324ee47` (EvoBridgeV2 batch `withdraw`: three `Withdrawn` events, USDT and USDC transfers and a native payout); `0x8ca0e0dde1fbbc62bf5f2c2cfacbc9bb5c30f1a69bac0c49accaf2ff555366e1` (BridgePool `take` by the owner, no log).
- **Addresses:** the verified explorer contracts and Verilog's list (primary contract on 11 chains, the Optimism, Gnosis and HarmonyONE secondary contract, the three takers); every literal checked with `eth_getCode` on all eight chains; EIP-1967 slots and `owner()` read on all six chains.
- **Not verified:** the chain-index mapping of `to`; the derivation of `Withdrawn.id`; the source of the Optimism third pool's implementation; older EVO contracts on chains outside the eight; the BNB history (the public BNB endpoints refuse archive log queries).

Sources:
- [Verilog Solutions, "EVO DeFi analysis" (2022-04-29)](https://hackmd.io/@verilog/evo-defi-analysis)
- [RugDoc, "EvoDeFi update" (2022-07-22)](https://rugdoc.io/education/evodefi-update-2/)
- Explorers: [Blockscout BridgePool (Ethereum)](https://eth.blockscout.com/address/0x06c30Af8A82AAf9cFd319f8644584276Bfbec42f) · [Blockscout EvoProxy (Ethereum)](https://eth.blockscout.com/address/0x9983d8cdeaf7872501628229d311e2f7df396add) · [Blockscout EvoBridgeV2 (Ethereum)](https://eth.blockscout.com/address/0x62cd928b16b7a92101c3091f5136fd9bb017870a) · [Polygon Blockscout](https://polygon.blockscout.com/address/0x9983d8cdeaf7872501628229d311e2f7df396add) · [Arbitrum Blockscout](https://arbitrum.blockscout.com/address/0x9983d8cdeaf7872501628229d311e2f7df396add) · [Optimism explorer, third pool](https://explorer.optimism.io/address/0x7cca0859058aa03301106ab8aba1707a16a30821) · [Base Blockscout, `RobinhoodChurnProxy`](https://base.blockscout.com/address/0x72d04e0760e07511f81121e9ef45408e37617aa4)
