# Fuel Canonical Bridge — Topics, Selectors, Addresses (Ethereum only)

**Status:** verified on 2026-09-29 against Ethereum mainnet RPC (`eth_getCode`, `eth_call`, EIP-1967 slots, `eth_getLogs`), `eth_getCode` on the seven other target chains, the `FuelLabs/fuel-bridge` repository (mainnet deployment records and Solidity/Sway sources), Sourcify, and L2BEAT.
**Scope:** the Ethereum-side contracts of the canonical bridge of Fuel Ignition, the Fuel L2 that settles to Ethereum: `FuelMessagePortal` (messages and the ETH escrow), `FuelERC20Gateway` (the ERC-20 escrow) and `FuelChainState` (Fuel block commitments). Fuel runs the FuelVM, not the EVM, so the Fuel side is not EVM-queryable. Of the eight target chains, only Ethereum (chain ID 1) has a deployment. Topics and selectors are chain-agnostic; addresses are network-specific.

The **portal** is the message bus and holds the bridged ETH. `depositETH` and `sendMessage` emit `MessageSent`; `relayMessage` proves a Fuel message against a finalized Fuel block and emits `MessageRelayed`, paying ETH when the message carries an amount. The **gateway** escrows ERC-20 tokens: `deposit` pulls the tokens and sends a deposit message through the portal; the Fuel-side bridge answers with a withdrawal message that the portal relays into `gateway.finalizeWithdrawal`. The **chain state** stores Fuel block hashes that a permissioned committer posts; a commitment is final after `TIME_TO_FINALIZE` (86,400 s, read live). Ethereum checks no validity or fraud proof.

All three contracts are UUPS proxies (ERC-1967, admin slot empty). The **Fuel Security Council** Safe (4 of 6) holds `DEFAULT_ADMIN_ROLE` on all three and can upgrade them with no delay. Amounts on the portal use Fuel's **9-decimal** base asset: multiply `MessageSent.amount` and `MessageRelayed.amount` by 10^9 to get wei.

---

## 0. Contract families & versions

| Contract | Address (Ethereum) | Live implementation (EIP-1967) | Role |
|----------|--------------------|--------------------------------|------|
| **FuelMessagePortal** (proxy) | `0xAEB0c00D0125A8a788956ade4f4F12Ead9f65DDf` | `0x2C4df10a82CF077122eD99573acA6daCd76F2E67` (`FuelMessagePortalV3`) | Message send and relay; **ETH escrow**; ETH withdrawal rate limit. |
| **FuelERC20Gateway** (proxy) | `0xa4cA04d02bfdC3A2DF56B9b6994520E69dF43F67` | `0xdE2D792ca3C4d02DE3CE1cD1456d8D0990cC3fab` (`FuelERC20GatewayV4`) | **ERC-20 escrow**; token whitelist (`whitelistRequired()=true`) and per-token limits. |
| **FuelChainState** (proxy) | `0xf3D20Db1D16A4D0ad2f280A5e594FF3c7790f130` | `0x621850dbB9160b54002B4a25b9fC9b2F26315f7e` (`FuelChainState`) | Fuel block commitments (`commit`, `finalized`). |
| Fuel-side bridge contract id | `0x4ea6ccef1215d9479f1024dff70fc055ca538215d2c8c348beddffd54583d0e8` (bytes32, on Fuel) | — | The gateway's `assetIssuerId()`: the sender of every token-withdrawal message. |
| Contract-message predicate | `0xe821b978bcce9abbf40c3e50ea30143e68c65fa95b9da8907fef59c02d954cec` (bytes32, on Fuel) | — | `CommonPredicates.CONTRACT_MESSAGE_PREDICATE`: the `recipient` of every gateway deposit message. |

The repository's `FuelChainState.json` still names implementation `0x725B2b1a15D818E1f25c68be77816802e6036559`; the live EIP-1967 slot reads `0x621850dbB9160b54002B4a25b9fC9b2F26315f7e` (deployed at block 23,174,852, the same ABI). Read the slot, not the file.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 FuelMessagePortal (emitter `0xAEB0c00D0125A8a788956ade4f4F12Ead9f65DDf`)

| topic0 | Event |
|--------|-------|
| `0x2e8c88b204c4fc9f27811757a7ca53a385ca4d1c8a2c6b0aa2bc386646f0ca63` | `MessageSent(bytes32 indexed sender, bytes32 indexed recipient, uint256 indexed nonce, uint64 amount, bytes data)` — **source leg** of every deposit (ETH and ERC-20) and of every Ethereum→Fuel message; `amount` is ETH in 9-decimal units |
| `0xd9e6225aff5cf09ee2f0b39b98941e3c2beca6957b16b9e02b674a69e0e83ee7` | `MessageRelayed(bytes32 indexed messageId, bytes32 indexed sender, bytes32 indexed recipient, uint64 amount)` — **destination leg** of every withdrawal; ETH is paid in the same call when `amount > 0` |
| `0xc0fd249af978a3c3d72e439fc68d57dced24cd9bca6fcb51b6d9f8db31703caa` | `RateLimitStatusUpdated(bool status)` — ETH withdrawal rate limit switched on or off |
| `0x53d83924cffa510ecaf1520ed9de204b6a2b1314d7dc3b20d8a970623841db8c` | `ResetRateLimit(uint256 amount)` — new ETH limit per period (wei) |
| `0x42e4ca4602039e4eee7055c852f2b9116333675ff2826aa7f05adb0839562f6e` | `FuelChainStateUpdated(address indexed sender, address indexed oldValue, address indexed newValue)` — **the portal now trusts another chain-state contract** |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` — also on the gateway and the chain state |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — UUPS upgrade; also on the gateway and the chain state |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` |

`pauseWithdrawals`, `unpauseWithdrawals`, `addMessageToBlacklist` and `removeMessageFromBlacklist` change state **without an event**: detect them by selector (§2.1).

### 1.2 FuelERC20Gateway (emitter `0xa4cA04d02bfdC3A2DF56B9b6994520E69dF43F67`)

| topic0 | Event |
|--------|-------|
| `0x182fa52899142d44ff5c45a6354d3b3e868d5b07db6a65580b39bd321bdaf8ac` | `Deposit(bytes32 indexed sender, address indexed tokenAddress, uint256 amount)` — **source leg** of an ERC-20 deposit; `sender` is `msg.sender` left-padded (a router when one is used); `amount` in token decimals |
| `0x028ab133c73f6c00ad0c5896ef40eff18378acd3d7f2ecf573c2706582bf73bf` | `Withdrawal(bytes32 indexed recipient, address indexed tokenAddress, uint256 amount)` — **destination leg** of an ERC-20 withdrawal or refund; `recipient` is the Ethereum address left-padded |
| `0xc5f291321b52c0a880f53a520482ae7920b1e570181bea4971307e9ba13026de` | `RateLimitUpdated(address indexed tokenAddress, uint256 amount)` — per-token withdrawal limit changed |
| `0x8ac921afb63648e691280b72420b87f54bbdfebd4ba46618e07dc0231542e837` | `RateLimitStatusUpdated(address indexed tokenAddress, bool status)` — per-token limit switched on or off |

### 1.3 FuelChainState (emitter `0xf3D20Db1D16A4D0ad2f280A5e594FF3c7790f130`)

| topic0 | Event |
|--------|-------|
| `0x1216b936e7a60e132d92c23737227ff7219df68ab525a98fa65f09b655f31e32` | `CommitSubmitted(uint256 indexed commitHeight, bytes32 blockHash)` — **status only**: a Fuel block hash was committed; withdrawals from it become provable after 86,400 s |

Role ids (read live): `COMMITTER_ROLE` `0x0b60b5d7f7e737e4561eecda7c6a01e19e626c495c26e6f45e5b255f76a20106`, `SET_RATE_LIMITER_ROLE` `0x7e5b1c957d4df4bad29cdaceffe50f28f282a0d5096601b958917550d4b2e016`, `DEFAULT_ADMIN_ROLE` `0x0000000000000000000000000000000000000000000000000000000000000000`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Struct tuples: `Message = (bytes32 sender, bytes32 recipient, bytes32 nonce, uint64 amount, bytes data)`; `FuelBlockHeaderLite = (bytes32 prevRoot, uint32 height, uint64 timestamp, bytes32 applicationHash)`; `FuelBlockHeader` has 11 fields; `MerkleProof = (uint256 key, bytes32[] proof)`.

### 2.1 FuelMessagePortal

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd68d9d4e` | `depositETH(bytes32 recipient)` | `payable`; ETH stays in the portal; emits `MessageSent` with empty `data`. `msg.value` must be a multiple of 10^9 wei. |
| `0x23c640e7` | `sendMessage(bytes32 recipient, bytes data)` | `payable`; generic Ethereum→Fuel message (the gateway uses it). |
| `0x3c6524f2` | `relayMessage((bytes32 sender, bytes32 recipient, bytes32 nonce, uint64 amount, bytes data) message, (bytes32 prevRoot, uint32 height, uint64 timestamp, bytes32 applicationHash) rootBlockHeader, (bytes32 prevRoot, uint64 timestamp, uint64 daHeight, uint32 outputMessagesCount, uint32 consensusParametersVersion, uint32 stateTransitionBytecodeVersion, uint32 height, bytes32 txRoot, bytes32 outputMessagesRoot, bytes32 eventInboxRoot, uint16 txCount) blockHeader, (uint256 key, bytes32[] proof) blockInHistoryProof, (uint256 key, bytes32[] proof) messageInBlockProof)` | Anyone may call. Checks the root block is `finalized`, the Merkle proofs and the blacklist; emits `MessageRelayed`. |
| `0x69b1e00d` | `incomingMessageSuccessful(bytes32 messageId)` | View; replay guard. |
| `0xe04c8bca` | `getNextOutgoingMessageNonce()` | View; 250,136 on 2026-09-29. |
| `0xff50abdc` | `totalDeposited()` | View; bridged ETH on the books (1,409.42 ETH on 2026-09-29). |
| `0x78abafaf` | `limitAmount()` | View; ETH withdrawal limit per period (7,829 ETH). |
| `0x32ad6268` | `RATE_LIMIT_DURATION()` | View; 604,800 s. |
| `0x56bb54a7` | `pauseWithdrawals()` | `PAUSER_ROLE`; **no event**. |
| `0xe4c4be58` | `unpauseWithdrawals()` | `DEFAULT_ADMIN_ROLE`; **no event**. |
| `0xdb0e2cc6` | `addMessageToBlacklist(bytes32 messageId)` | `PAUSER_ROLE`; blocks one withdrawal; **no event**. |
| `0x06720bbb` | `removeMessageFromBlacklist(bytes32 messageId)` | `DEFAULT_ADMIN_ROLE`; **no event**. |
| `0x1abefcaf` | `setFuelChainState(address newFuelChainState)` | `DEFAULT_ADMIN_ROLE`; emits `FuelChainStateUpdated`. |
| `0x557eac73` | `resetRateLimitAmount(uint256 _amount)` | `SET_RATE_LIMITER_ROLE`. |
| `0xb905c4f1` | `updateRateLimitStatus(bool value)` | `SET_RATE_LIMITER_ROLE`. |
| `0x8456cb59` | `pause()` | `PAUSER_ROLE`; stops deposits and relays. |
| `0x3f4ba83a` | `unpause()` | `DEFAULT_ADMIN_ROLE`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | UUPS; `DEFAULT_ADMIN_ROLE`. |
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | UUPS; `DEFAULT_ADMIN_ROLE`. |

### 2.2 FuelERC20Gateway

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd954863c` | `deposit(bytes32 to, address tokenAddress, uint256 amount)` | Pulls the tokens into the gateway, sends the deposit message, emits `Deposit`. |
| `0x5714b5a9` | `depositWithData(bytes32 to, address tokenAddress, uint256 amount, bytes data)` | Deposit to a Fuel contract, with optional data. |
| `0x64a7fad9` | `finalizeWithdrawal(address to, address tokenAddress, uint256 l2BurntAmount, uint256 tokenId)` | Portal only, and only when the message sender is `assetIssuerId`; emits `Withdrawal`. |
| `0x52148c23` | `sendMetadata(address tokenAddress)` | Sends token name and symbol to Fuel (no value). |
| `0xd810e6f8` | `depositLimits(address tokenAddress)` | View; the whitelist cap (0 = not whitelisted). |
| `0xa161c205` | `tokensDeposited(address tokenAddress)` | View; escrowed amount in Fuel units. |
| `0xb37b363b` | `setGlobalDepositLimit(address token, uint256 limit)` | `DEFAULT_ADMIN_ROLE`; whitelists a token. |
| `0xb46f77e4` | `requireWhitelist(bool value)` | `DEFAULT_ADMIN_ROLE`. |
| `0xfdec40a5` | `resetRateLimitAmount(address _token, uint256 _amount, uint256 _rateLimitDuration)` | `SET_RATE_LIMITER_ROLE`; emits `RateLimitUpdated`. |
| `0xa5d74961` | `updateRateLimitStatus(address _token, bool _rateLimitStatus)` | `SET_RATE_LIMITER_ROLE`; emits `RateLimitStatusUpdated`. |
| `0xcaa9147c` | `setAssetIssuerId(bytes32 id)` | `DEFAULT_ADMIN_ROLE`; **changes which Fuel contract can release tokens**. |
| `0x20800a00` | `rescueETH()` | `DEFAULT_ADMIN_ROLE`. |
| `0x8456cb59` | `pause()` | `PAUSER_ROLE`. |

### 2.3 FuelChainState

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe900ead8` | `commit(bytes32 blockHash, uint256 commitHeight)` | `COMMITTER_ROLE`; emits `CommitSubmitted`. |
| `0xc8902398` | `finalized(bytes32 blockHash, uint256 blockHeight)` | View; true after `TIME_TO_FINALIZE`. |
| `0x31c8b817` | `blockHashAtCommit(uint256 commitHeight)` | View. |
| `0xa42747da` | `TIME_TO_FINALIZE()` | View; 86,400 s. |
| `0x735808b7` | `BLOCKS_PER_COMMIT_INTERVAL()` | View; 10,800. |
| `0x84cbff5f` | `COMMIT_COOLDOWN()` | View; 86,400 s. |
| `0x8456cb59` | `pause()` | `PAUSER_ROLE`. |

Shared by all three: `grantRole(bytes32 role, address account)` `0x2f2ff15d`, `revokeRole(bytes32 role, address account)` `0xd547741f`, `hasRole(bytes32 role, address account)` `0x91d14854`, `paused()` `0x5c975abb`, `proxiableUUID()` `0x52d1902d`.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on 2026-09-29. Wiring read live: gateway `fuelMessagePortal()` → the portal; portal `fuelChainStateContract()` → the chain state; gateway `assetIssuerId()` → the Fuel bridge id above.

| Role | Address | One-liner |
|------|---------|-----------|
| **FuelMessagePortal** (proxy) | `0xAEB0c00D0125A8a788956ade4f4F12Ead9f65DDf` | Deposits of ETH, all messages, ETH payouts. 170-byte proxy. |
| **FuelERC20Gateway** (proxy) | `0xa4cA04d02bfdC3A2DF56B9b6994520E69dF43F67` | ERC-20 escrow. 170-byte proxy. |
| **FuelChainState** (proxy) | `0xf3D20Db1D16A4D0ad2f280A5e594FF3c7790f130` | Fuel block commitments. 170-byte proxy. |
| Portal implementation | `0x2C4df10a82CF077122eD99573acA6daCd76F2E67` | `FuelMessagePortalV3`, 15,513 bytes. |
| Gateway implementation | `0xdE2D792ca3C4d02DE3CE1cD1456d8D0990cC3fab` | `FuelERC20GatewayV4`, 13,168 bytes. |
| Chain-state implementation | `0x621850dbB9160b54002B4a25b9fC9b2F26315f7e` | `FuelChainState`, 8,163 bytes. |
| Fuel Security Council (Safe, 4 of 6) | `0x32da601374b38154f05904B16F44A1911Aa6f314` | `DEFAULT_ADMIN_ROLE` on all three (upgrades, unpause, limits); also a `COMMITTER_ROLE` holder. |
| Committer (EOA) | `0x83dC58504D1d2276Bc8D9Cf01d0B341D84A49cfF` | EOA (no code, nonce 6,046) with `COMMITTER_ROLE`: posts Fuel block hashes. |

L2BEAT lists 10 pauser accounts across the portal and the chain state (the council and individual signers); they are not enumerated here. Watch `RoleGranted` for changes.

---

## 4. Cross-chain summary

| Chain | ID | FuelMessagePortal | FuelERC20Gateway | FuelChainState | Note |
|-------|----|-------------------|------------------|----------------|------|
| **Ethereum** | 1 | ✅ `0xAEB0c00D0125A8a788956ade4f4F12Ead9f65DDf` | ✅ `0xa4cA04d02bfdC3A2DF56B9b6994520E69dF43F67` | ✅ `0xf3D20Db1D16A4D0ad2f280A5e594FF3c7790f130` | The only EVM side. |
| Base | 8453 | — | — | — | no deployment: `eth_getCode` = `0x` at the three Ethereum addresses; the repository has only a `mainnet` (chain 1) deployment set |
| Arbitrum One | 42161 | — | — | — | same |
| Optimism | 10 | — | — | — | same |
| Polygon PoS | 137 | — | — | — | same |
| BNB Smart Chain | 56 | — | — | — | same |
| Avalanche C-Chain | 43114 | — | — | — | same |
| Robinhood Chain | 4663 | — | — | — | same |

The counterparty is **Fuel Ignition** (FuelVM), outside the eight chains. The bridge uses no protocol chain ids: there is one route, Ethereum ↔ Fuel.

---

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| FuelMessagePortal | UUPS (ERC-1967) | 170-byte proxy; impl slot → `0x2C4df10a82CF077122eD99573acA6daCd76F2E67`; admin slot empty. | `DEFAULT_ADMIN_ROLE` = Security Council, **no delay**. |
| FuelERC20Gateway | UUPS (ERC-1967) | impl slot → `0xdE2D792ca3C4d02DE3CE1cD1456d8D0990cC3fab`; admin slot empty. | Same. |
| FuelChainState | UUPS (ERC-1967) | impl slot → `0x621850dbB9160b54002B4a25b9fC9b2F26315f7e`; admin slot empty. | Same. |

EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. Watch `Upgraded` on all three proxies. The three proxies share one runtime code hash (`0xee8a105971995661291a9f284262a87abf2381b3cdc93b2c8fbeffe4cd636dd9`), so identify each by address, not by code.

---

## 6. Detection invariants & gotchas

1. **ETH deposit:** `depositETH` → ETH stays in the portal (`msg.value`, no ERC-20 row) → `MessageSent(sender = user left-padded, recipient = Fuel address, nonce, amount in 10^-9 ETH, data = empty)`.
2. **ERC-20 deposit:** `gateway.deposit` → ERC-20 `Transfer(user or router → gateway)` + portal `MessageSent(sender = gateway, recipient = 0xe821b978bcce9abbf40c3e50ea30143e68c65fa95b9da8907fef59c02d954cec, amount = 0, data = deposit payload)` + gateway `Deposit`. The Fuel recipient `to` is **only in the `MessageSent` data** (after the bridge id, message type, token, token id and sender words); `Deposit` does not carry it.
3. **Withdrawal (payout):** a Fuel burn → the committer posts a block (`CommitSubmitted`) → after 86,400 s anyone calls `relayMessage`. ETH: `MessageRelayed(amount > 0)` and an internal ETH transfer of `amount × 10^9` wei to `recipient`, with no ERC-20 row. ERC-20: `MessageRelayed(sender = 0x4ea6ccef1215d9479f1024dff70fc055ca538215d2c8c348beddffd54583d0e8, recipient = gateway, amount = 0)` + ERC-20 `Transfer(gateway → user)` + `Withdrawal`.
4. **Refunds use the withdrawal path.** A deposit that the Fuel bridge rejects is registered as a refund on Fuel (`RefundRegisteredEvent`); `claim_refund` sends a Fuel→Ethereum message, which ends as `MessageRelayed` + `Withdrawal` on Ethereum. No Ethereum event marks it as a refund.
5. **Link keys.** Ethereum→Fuel: `MessageSent.nonce` (topic 3); the Fuel message id is `sha256(sender, recipient, nonce, amount, data)`, computed off the EVM. Fuel→Ethereum: `MessageRelayed.messageId` (topic 1), the same SHA-256 id; the burn happened on Fuel. Only the Ethereum side of each is EVM-queryable.
6. **Decimals.** Portal amounts are `uint64` in 9-decimal units. The gateway converts tokens with more than 9 decimals to 9 on Fuel, but `Deposit.amount` and `Withdrawal.amount` are in the token's own decimals.
7. **`Deposit.sender` can be a router.** It is `msg.sender` of the gateway call (the sampled deposit came through a router contract). Use `tx.from` or the transfer row for the user.
8. **`Withdrawal` topic collision.** `Withdrawal(bytes32,address,uint256)` is also emitted by unrelated contracts: in the pinned window, a LayerZero `LiquidStakingTokenLockbox` at `0xf2B2BBdC9975cF680324De62A30a31BC3AB8A4d5` emitted 2 of the 3 Ethereum logs with this topic0. Always filter by the gateway address.
9. **Silent admin actions.** `pauseWithdrawals`, `addMessageToBlacklist` and their reverses emit nothing. Watch calls to the portal with selectors `0x56bb54a7`, `0xe4c4be58`, `0xdb0e2cc6`, `0x06720bbb`.
10. **Drain and admin triggers.** `Upgraded` on any proxy; `FuelChainStateUpdated` (the portal would trust another commitment source); `setAssetIssuerId` (call, no event) on the gateway; `RoleGranted` of `COMMITTER_ROLE` or `DEFAULT_ADMIN_ROLE`; `ResetRateLimit` / `RateLimitUpdated` (a higher limit weakens the drain brake); `Paused`. A `MessageRelayed` with a large `amount` or a large gateway `Withdrawal` is the payout itself.
11. **The trust is in the committer.** `commit` checks only the role, and Ethereum verifies no state transition. An unexpected `CommitSubmitted` sender, or a commit from a new account, is a high-severity signal.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MESSAGE_SENT               = '\x2e8c88b204c4fc9f27811757a7ca53a385ca4d1c8a2c6b0aa2bc386646f0ca63'
TOPIC_MESSAGE_RELAYED            = '\xd9e6225aff5cf09ee2f0b39b98941e3c2beca6957b16b9e02b674a69e0e83ee7'
TOPIC_GATEWAY_DEPOSIT            = '\x182fa52899142d44ff5c45a6354d3b3e868d5b07db6a65580b39bd321bdaf8ac'
TOPIC_GATEWAY_WITHDRAWAL         = '\x028ab133c73f6c00ad0c5896ef40eff18378acd3d7f2ecf573c2706582bf73bf'
TOPIC_COMMIT_SUBMITTED           = '\x1216b936e7a60e132d92c23737227ff7219df68ab525a98fa65f09b655f31e32'
TOPIC_PORTAL_RATE_LIMIT_STATUS   = '\xc0fd249af978a3c3d72e439fc68d57dced24cd9bca6fcb51b6d9f8db31703caa'
TOPIC_PORTAL_RESET_RATE_LIMIT    = '\x53d83924cffa510ecaf1520ed9de204b6a2b1314d7dc3b20d8a970623841db8c'
TOPIC_GATEWAY_RATE_LIMIT_UPDATED = '\xc5f291321b52c0a880f53a520482ae7920b1e570181bea4971307e9ba13026de'
TOPIC_GATEWAY_RATE_LIMIT_STATUS  = '\x8ac921afb63648e691280b72420b87f54bbdfebd4ba46618e07dc0231542e837'
TOPIC_FUEL_CHAIN_STATE_UPDATED   = '\x42e4ca4602039e4eee7055c852f2b9116333675ff2826aa7f05adb0839562f6e'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                   = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED               = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'

-- ===== Selectors =====
SEL_DEPOSIT_ETH                  = '\xd68d9d4e'
SEL_SEND_MESSAGE                 = '\x23c640e7'
SEL_RELAY_MESSAGE                = '\x3c6524f2'
SEL_GATEWAY_DEPOSIT              = '\xd954863c'
SEL_GATEWAY_DEPOSIT_WITH_DATA    = '\x5714b5a9'
SEL_FINALIZE_WITHDRAWAL          = '\x64a7fad9'
SEL_COMMIT                       = '\xe900ead8'
SEL_PAUSE_WITHDRAWALS            = '\x56bb54a7'
SEL_UNPAUSE_WITHDRAWALS          = '\xe4c4be58'
SEL_ADD_MESSAGE_TO_BLACKLIST     = '\xdb0e2cc6'
SEL_REMOVE_MESSAGE_FROM_BLACKLIST = '\x06720bbb'
SEL_SET_FUEL_CHAIN_STATE         = '\x1abefcaf'
SEL_SET_ASSET_ISSUER_ID          = '\xcaa9147c'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'
SEL_UPGRADE_TO                   = '\x3659cfe6'

-- ===== Fuel-side identifiers (bytes32, on Fuel) =====
FUEL_L2_BRIDGE_ID                = '\x4ea6ccef1215d9479f1024dff70fc055ca538215d2c8c348beddffd54583d0e8'
FUEL_CONTRACT_MESSAGE_PREDICATE  = '\xe821b978bcce9abbf40c3e50ea30143e68c65fa95b9da8907fef59c02d954cec'
ROLE_COMMITTER                   = '\x0b60b5d7f7e737e4561eecda7c6a01e19e626c495c26e6f45e5b255f76a20106'

-- ===== Addresses — Ethereum (chain ID 1), the only chain with a deployment =====
ETH_FUEL_MESSAGE_PORTAL          = '\xaeb0c00d0125a8a788956ade4f4f12ead9f65ddf'
ETH_FUEL_ERC20_GATEWAY           = '\xa4ca04d02bfdc3a2df56b9b6994520e69df43f67'
ETH_FUEL_CHAIN_STATE             = '\xf3d20db1d16a4d0ad2f280a5e594ff3c7790f130'
ETH_FUEL_PORTAL_IMPL             = '\x2c4df10a82cf077122ed99573aca6dacd76f2e67'
ETH_FUEL_GATEWAY_IMPL            = '\xde2d792ca3c4d02de3ce1cd1456d8d0990cc3fab'
ETH_FUEL_CHAIN_STATE_IMPL        = '\x621850dbb9160b54002b4a25b9fc9b2f26315f7e'
ETH_FUEL_SECURITY_COUNCIL        = '\x32da601374b38154f05904b16f44a1911aa6f314'
ETH_FUEL_COMMITTER_EOA           = '\x83dc58504d1d2276bc8d9cf01d0b341d84a49cff'
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood: no deployment
```

---

## 8. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` (and `[0:4]`) from the ABIs in the repository's mainnet deployment records (`FuelMessagePortal.json`, `FuelERC20GatewayV4.json`, `FuelChainState.json`) and the live chain-state implementation's verified ABI on Sourcify. The event-free admin functions were read from `FuelMessagePortalV3.sol`; the deposit payload layout and the predicate constant from `FuelERC20GatewayV4.sol` and `CommonPredicates.sol`; the refund flow from the Sway bridge (`bridge-fungible-token/implementation/src/main.sw`).
- **Addresses:** from the repository's `deployments/mainnet/*.json` and L2BEAT, each existence-checked with `eth_getCode`; the implementations read from the EIP-1967 slot (the chain-state file is stale, see §0). `eth_getCode` = `0x` at the three proxy addresses on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain.
- **Roles and state:** `hasRole` read live (the council has `DEFAULT_ADMIN_ROLE` on all three and `COMMITTER_ROLE`; the committer EOA has `COMMITTER_ROLE`); Safe `getThreshold()` = 4 and `getOwners()` = 6; `paused()` = false on all three; `withdrawalsPaused()` = false; `rateLimitEnabled()` = true; `whitelistRequired()` = true; the constants in §2 read live.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26,072,222–26,075,812):** `MessageSent` 1 and `MessageRelayed` 3 (portal), `Deposit` 0 and `Withdrawal` 1 (gateway; 2 more `Withdrawal` logs came from the unrelated lockbox in §6), `CommitSubmitted` 4 (chain state). Over blocks 25,900,000–26,075,812: 17 gateway `Deposit`. The seven other chains: 0 logs of `MessageSent`, `MessageRelayed`, `Deposit` and `Withdrawal` from any emitter in the window.
- **Sample transactions (receipts read):** ETH deposit `0x937d86719edc9266b088d0174e726aafae0ad9df976ca0c97a2ef3b8394e5130` (`depositETH`, 0.0005 ETH, `MessageSent` nonce 250,129); ETH withdrawal `0x66a7a819519f98214d20a7aad8a1d170dbfa6328edef4e5fa6d4b31746fe63e2` (`relayMessage` → `MessageRelayed`); token withdrawal `0x5296f31c55794dcc1e75ee56494f65a8cc7a621b4924cfd91e386aec58bbc97d` (`relayMessage` → FUEL `Transfer` gateway → user, `Withdrawal`, `MessageRelayed` from the Fuel bridge id); token deposit `0xd6ba03d4b79c4c914b9bf6351a934ed0eac11543be7d0ae0193d41e62da05c13` (via a router → `MessageSent` to the predicate, FUEL `Transfer` → gateway, `Deposit`).

Authoritative sources (opened):
- [FuelLabs/fuel-bridge](https://github.com/FuelLabs/fuel-bridge) — `packages/solidity-contracts/deployments/mainnet/` (`FuelMessagePortal.json`, `FuelERC20GatewayV4.json`, `FuelChainState.json`, `FuelL2BridgeId.json`, `.migrations.json`), `contracts/fuelchain/FuelMessagePortal/v3/FuelMessagePortalV3.sol`, `contracts/fuelchain/FuelMessagePortal.sol`, `contracts/messaging/gateway/FuelERC20Gateway/FuelERC20GatewayV4.sol`, `contracts/lib/CommonPredicates.sol`, `contracts/lib/Cryptography.sol`, `packages/fungible-token/bridge-fungible-token/implementation/src/main.sw`
- L2BEAT — [Fuel Ignition](https://l2beat.com/scaling/projects/fuel) (contracts, permissions, upgrade delay)
- Sourcify — [FuelChainState impl](https://sourcify.dev/server/v2/contract/1/0x621850dbb9160b54002b4a25b9fc9b2f26315f7e) · [FuelMessagePortalV3 impl](https://sourcify.dev/server/v2/contract/1/0x2c4df10a82cf077122ed99573aca6dacd76f2e67) · [FuelERC20GatewayV4 impl](https://sourcify.dev/server/v2/contract/1/0xde2d792ca3c4d02de3ce1cd1456d8d0990cc3fab) · [LiquidStakingTokenLockbox](https://sourcify.dev/server/v2/contract/1/0xf2b2bbdc9975cf680324de62a30a31bc3ab8a4d5)
