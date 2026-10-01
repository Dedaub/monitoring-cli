# OP Stack native bridges — reference index

**Status:** all constants verified against live RPC on the eight target chains, the Superchain Registry (commit `2507d80d5eee7b1e0c8aa1485489936be62b7fd1`, 2026-09-28), the `ethereum-optimism/optimism` contracts and the L2BEAT discovery files on 2026-09-29.
**Scope:** the canonical bridges of 57 OP Stack deployments: 49 chains that settle on Ethereum (the Superchain Registry, the chains that left it, the chains outside it, Mantle, two unidentified deployments), Metis, an unofficial deployment that uses GIWA's chain id, opBNB and one more chain on BNB Smart Chain, four L3s on Base, and the L2 predeploys of Optimism and Base. Blast is in [`../blast_native/`](../blast_native/core.md) and is not repeated here.

## The OP Stack bridge model

An OP Stack chain has one bridge, on its settlement layer, and one set of predeploys on the chain itself.

- **Settlement layer (Ethereum for an L2; BNB Smart Chain for opBNB; Base for an L3):** an **OptimismPortal** holds the ETH (or an **ETHLockbox** holds it, on OP Mainnet, Ink, Soneium and Unichain; or the portal holds an ERC-20 gas token) and emits `TransactionDeposited` for every deposit; an **L1StandardBridge** escrows ERC-20 tokens and emits the bridge events; an **L1CrossDomainMessenger** carries the bridge messages through the portal. A **SystemConfig**, a **DisputeGameFactory** or **L2OutputOracle**, a **ProxyAdmin** and a **SuperchainConfig** (the pause switch) complete the set.
- **L2 (the predeploys at `0x4200000000000000000000000000000000000000` and up):** the **L2StandardBridge** `0x4200000000000000000000000000000000000010` pays deposits (`DepositFinalized`) and starts withdrawals (`WithdrawalInitiated`); the **L2CrossDomainMessenger** `0x4200000000000000000000000000000000000007` relays messages; the **L2ToL1MessagePasser** `0x4200000000000000000000000000000000000016` records every withdrawal (`MessagePassed`).
- **Deposit:** Ethereum `TransactionDeposited` → an L2 deposit transaction (type `0x7e`) whose hash is computable from the L1 block hash and log index. **Withdrawal:** L2 `MessagePassed` → Ethereum `WithdrawalProven` → days later `WithdrawalFinalized` (the payout), keyed by `withdrawalHash`. All link keys are on chain on both sides.

## File map

| File | Covers | Chains of the eight |
|---|---|---|
| [l1.md](l1.md) | The settlement side: topics, selectors and one address row per chain (portal, bridge, messenger, NFT bridge, lockbox, SystemConfig, proof contract, batch inbox, ProxyAdmin and owner, SuperchainConfig); Mantle and Metis variants; token-specific bridges; opBNB | Ethereum, BNB Smart Chain |
| [l2.md](l2.md) | The L2 predeploys on Optimism and Base, the deposit transaction and link keys, the interop predeploys (inactive), and the L3 settlement contracts on Base | Optimism, Base (Robinhood Chain checked: no predeploys) |
| [`../blast_native/`](../blast_native/core.md) | Blast (OP Stack fork with a yield escrow) | Ethereum |

## Chains covered

| Chain | Chain id | Status | Settles on | File |
|---|---|---|---|---|
| OP Mainnet | 10 | Superchain Registry; ETHLockbox | Ethereum | [l1.md §3.1](l1.md) |
| Base | 8453 | Left the registry 2026-04-27 | Ethereum | [l1.md §3.1](l1.md) |
| Automata | 65536 | Superchain Registry; custom gas token | Ethereum | [l1.md §3.1](l1.md) |
| Binary | 624 | Superchain Registry; custom gas token | Ethereum | [l1.md §3.1](l1.md) |
| BOB | 60808 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Boba | 288 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Celo | 42220 | Superchain Registry; custom gas token | Ethereum | [l1.md §3.1](l1.md) |
| Cyber | 7560 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Ethernity | 183 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Fraxtal | 252 | Superchain Registry; custom gas token | Ethereum | [l1.md §3.1](l1.md) |
| Funki | 33979 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| HashKey Chain | 177 | Superchain Registry; custom gas token | Ethereum | [l1.md §3.1](l1.md) |
| Ink | 57073 | Superchain Registry; ETHLockbox | Ethereum | [l1.md §3.1](l1.md) |
| Lisk | 1135 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Lyra Chain (Derive) | 957 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Metal L2 | 1750 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Mint | 185 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Mode | 34443 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Orderly | 291 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Polynomial | 8008 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| RACE | 6805 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Redstone | 690 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Settlus | 5371 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Shape | 360 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Silent Data | 380929 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Soneium | 1868 | Superchain Registry; ETHLockbox | Ethereum | [l1.md §3.1](l1.md) |
| Superseed | 5330 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Swan Chain | 254 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Unichain | 130 | Superchain Registry; ETHLockbox | Ethereum | [l1.md §3.1](l1.md) |
| World Chain | 480 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Xterio Chain (ETH) | 2702128 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Zora | 7777777 | Superchain Registry | Ethereum | [l1.md §3.1](l1.md) |
| Arena-Z | 7897 | Left the registry 2026-05-26 | Ethereum | [l1.md §3.1](l1.md) |
| Swellchain | 1923 | Left the registry 2026-05-26 | Ethereum | [l1.md §3.1](l1.md) |
| SnaxChain | 2192 | Left the registry 2025-11-17 | Ethereum | [l1.md §3.1](l1.md) |
| Aevo | 2999 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| DBK Chain | 20240603 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| Hemi | 43111 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| Manta Pacific | 169 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| MegaETH | 4326 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| Nillion | 98875 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| OpenLedger | 1612 | Outside the registry; custom gas token | Ethereum | [l1.md §3.1](l1.md) |
| Phala | 2035 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| RISE | 4153 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| X Layer | 196 | Outside the registry; custom gas token | Ethereum | [l1.md §3.1](l1.md) |
| Zircuit | 48900 | Outside the registry | Ethereum | [l1.md §3.1](l1.md) |
| Mantle | 5000 | Fork (MNT gas token, own events) | Ethereum | [l1.md §3.1](l1.md) |
| Unidentified chain A (inbox pattern suggests id 960) | not read | Unidentified | Ethereum | [l1.md §3.1](l1.md) |
| Unidentified chain B (OptimismPortal 2.6.0) | not read | Unidentified | Ethereum | [l1.md §3.1](l1.md) |
| Metis Andromeda | 1088 | Fork (OVM era, no portal, own events) | Ethereum | [l1.md §3.4](l1.md) |
| Unofficial deployment that uses GIWA's chain id (not GIWA) | 9134 | Unofficial; drained 2026-09-27 | Ethereum | [l1.md §3.5](l1.md) |
| opBNB | 204 | Outside the registry | BNB Smart Chain | [l1.md §4](l1.md) |
| Unidentified chain (BNB portal 2.5.0) | not read | Unidentified | BNB Smart Chain | [l1.md §4](l1.md) |
| Horizen (L3) | 26514 | Outside the registry | Base | [l2.md §5](l2.md) |
| Unidentified L3 | 845300012 | Unidentified; EOA owner | Base | [l2.md §5](l2.md) |
| B3 (L3) | 8333 | Outside the registry | Base | [l2.md §5](l2.md) |
| Ham (L3) | 5112 | Outside the registry; last batch 2025-11-24 | Base | [l2.md §5](l2.md) |
| Blast | 81457 | Fork with a yield escrow | Ethereum | [`../blast_native/`](../blast_native/core.md) |

## Topic collisions (read before indexing)

- **Every OP Stack chain uses the same topic0 values.** `TransactionDeposited` came from 22 portals on Ethereum in one 12-hour window, `DisputeGameCreated` from 41 factories. Key every rule on `(chain, emitter address)`.
- **Other bridges reuse the names.** The Lido token bridges emit `ERC20DepositInitiated` and `ERC20WithdrawalFinalized`; Blast emits the bridge and messenger events; Metis emits `ERC20DepositInitiated`; Scroll's `L1ScrollMessenger` `0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367` and Morph's `L1CrossDomainMessenger` `0xDc71366EFFA760804DCFC3EDF87fa2A6f1623304` emit `RelayedMessage(bytes32)` (195 of the 298 on Ethereum in the window).
- **Forks change some topics.** Mantle: `SentMessageExtension1(address,uint256,uint256)`, `MessagePassed` with `mntValue` and `ethValue`, and the `MNT*` events. Metis: `ETHDepositInitiated` and `ETHWithdrawalFinalized` with a `chainId`, `SentMessage` with a `chainId`. The L2ToL2 interop messenger uses other `SentMessage` and `RelayedMessage` topic0 values than the L2CrossDomainMessenger.
- **Generic events.** `Paused(address)` and `Unpaused(address)` are also OpenZeppelin `Pausable` events; `Upgraded(address)`, `OwnershipTransferred` and `Initialized(uint8)` come from every proxy.
- **On Base, the L2 predeploys and the L3 settlement contracts share the topic0 values** (`SentMessage`, `ETHBridgeInitiated`, `TransactionDeposited`).

## Cross-cutting facts

1. **Decode one event of each legacy/new pair** (`ETHDepositInitiated`/`ETHBridgeInitiated`, `ERC20DepositInitiated`/`ERC20BridgeInitiated`, `DepositFinalized`/`*BridgeFinalized`, `WithdrawalInitiated`/`*BridgeInitiated`, and the finalization pairs). `SentMessage` and `SentMessageExtension1` are complementary: join them.
2. **`TransactionDeposited` covers every deposit and `MessagePassed` every withdrawal; the bridge events do not.** Read ETH from the `mint` field (`version` 0; `version` 1 on Mantle).
3. **The registry is not the population.** Base left it on 2026-04-27 and still carries most of the traffic. X Layer's OP Stack bridges are disabled (its token bridge is the Agglayer bridge). GIWA's chain id is used by an unofficial deployment that was drained through a portal upgrade on 2026-09-27.
4. **Upgrades:** `Upgraded` on the EIP-1967 proxies, `AddressSet` on the AddressManager for the messenger, and no event for the `L1ChugSplashProxy` of the L1StandardBridge. The ProxyAdmin owners are Safes, except on Polynomial and one L3 on Base (EOAs).
5. **`SystemConfig.batchInbox()` is not reliable** on 12 chains; l1.md lists the inbox that receives the batches.

## Cross-chain summary

| Chain | ID | OP Stack contracts | Where |
|---|---|---|---|
| Ethereum | 1 | ✅ settlement contracts of 49 chains + Metis + Blast | l1.md |
| Base | 8453 | ✅ L2 predeploys + L3 settlement contracts (4 L3s) | l2.md |
| Optimism | 10 | ✅ L2 predeploys | l2.md |
| BNB Smart Chain | 56 | ✅ settlement contracts of opBNB + 1 unidentified chain | l1.md §4 |
| Arbitrum One | 42161 | ❌ none | — |
| Polygon PoS | 137 | ❌ none | — |
| Avalanche C-Chain | 43114 | ❌ none | — |
| Robinhood Chain | 4663 | ❌ none (Arbitrum Orbit; no code at the predeploy addresses) | l2.md §7 |
