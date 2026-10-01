# Snowbridge (Polkadot ↔ Ethereum) — Topics, Selectors, Addresses (Ethereum + adaptors on Base, Arbitrum, Optimism)

**Status:** verified on 2026-09-29 against Ethereum, Base, Arbitrum and Optimism RPC (`eth_getCode`, `eth_call`, EIP-1967 slot, `eth_getLogs`), `eth_getCode` on the other target chains, the `Snowfork/snowbridge` repository (contracts, `web/packages/registry/src/polkadot_mainnet_bridge_info.g.ts`, `contracts/scripts/l2-integration/across/constants/Mainnet.sol`), the Snowbridge docs, and Sourcify.
**Scope:** the EVM side of Snowbridge, the trustless bridge between Polkadot (Asset Hub, Bridge Hub and other parachains) and Ethereum: the `Gateway` proxy, the `BeefyClient` light client, the `Agent` contracts that hold the escrowed funds, the `AgentExecutor`, and the Across-based L2 route (`SnowbridgeL1Adaptor` on Ethereum, `SnowbridgeL2Adaptor` on Base, Arbitrum and Optimism). Polkadot is not an EVM chain, so its side is not EVM-queryable. Topics and selectors are chain-agnostic; addresses are network-specific.

**One Gateway, two protocol versions.** V1 uses channels and carries token transfers as `sendToken` → `TokenSent` + `OutboundMessageAccepted(channelID, nonce, messageID, payload)`; V2 uses one global nonce and XCM payloads: `v2_sendMessage` → `OutboundMessageAccepted(nonce, payload)`. Inbound (Polkadot → Ethereum) messages arrive through `submitV1` or `v2_submit`, which verify a Polkadot proof against the `BeefyClient` and dispatch commands (unlock or mint); each emits `InboundMessageDispatched` in its own version's format. Both versions live in the same Gateway and both are active (§9).

**Funds sit in Agents, not in the Gateway.** An Agent is a small contract per Polkadot origin that only the Gateway can drive (`invoke` → `AgentExecutor`). Every Ethereum-native token and all bridged ETH are escrowed in the **Asset Hub agent** `0xd803472c47a87D7B63E888DE53f03B4191B846a8` (the "AssetHub Sovereign" in the docs). Polkadot-native assets (for example DOT) exist on Ethereum as Snowbridge `Token` ERC-20 contracts that the Gateway mints and burns. The Gateway keeps only the V1 fees in ETH.

---

## 0. Contract families & versions

| Contract | Chain | Address | Role |
|----------|-------|---------|------|
| **Gateway** (`GatewayProxy`) | Ethereum | `0x27ca963C279c93801941e1eB8799c23f407d68e7` | Entry point for both versions; message verification and dispatch. Implementation `0x36e74FCAAcb07773b144Ca19Ef2e32Fc972aC50b` (`Gateway202602`, block 24,676,688). |
| **Asset Hub agent** | Ethereum | `0xd803472c47a87D7B63E888DE53f03B4191B846a8` | **Escrow** of all Ethereum-native tokens and ETH bridged to Polkadot. Agent id `0x81c5ab2571199e3188135178f3c2c8e2d268be1313d029b30f534fa579b69b79`. |
| Bridge Hub agent | Ethereum | `0xb31623f670675501b07F027F406cea76F38ed1eE` | Agent of Bridge Hub (para 1002). Agent id `0x03170a2e7597b7b7e3d84c05391d139a62b157e78786d8c082f29dcf4c111314`. |
| **BeefyClient** (live) | Ethereum | `0x7cfc5C8b341991993080Af67D940B6aD19a010E1` | Polkadot BEEFY light client; the Gateway's `BEEFY_CLIENT()` (block 24,676,648). |
| BeefyClient (previous) | Ethereum | `0x6eD05bAa904df3DE117EcFa638d4CB84e1B8A00C` | Still listed on the docs' Infrastructure page; not the Gateway's client; 0 `NewMMRRoot` in the window. |
| AgentExecutor | Ethereum | `0x836b7B5B850ac1F21Cf32Fe2f3FF7a01B521ACd2` | Code the Agents delegate-call to move tokens and ETH (`AGENT_EXECUTOR()`). |
| SnowbridgeL1Adaptor | Ethereum | `0xd3b11C36404B092645522B682832fCdeE07D2668` | Takes funds unlocked by a V2 message and deposits them into Across toward an L2. |
| SnowbridgeL2Adaptor | Base | `0x9E41656f3457F21Fd566dA6e8E9d9158f1390122` | Sends L2 funds through Across to Ethereum, then into `Gateway.v2_sendMessage`. |
| SnowbridgeL2Adaptor | Arbitrum One | `0x16543A52030b9525a95Bc41Ab5594e8514694203` | Same. |
| SnowbridgeL2Adaptor | Optimism | `0x523309B0fdF6990383bcE3FbE1283940B3B6cBc3` | Same. |

Polkadot ids used by the bridge: Asset Hub para id **1000**, Bridge Hub para id **1002** (both read from the registry and `Constants.sol`); the registry sets `v2_parachains` to 1000 and 2034 (Hydration) and also lists parachains 2000, 2030, 2043, 3369 and 3397. Ethereum's chain id is 1. V1 channel ids: primary governance `0x0000000000000000000000000000000000000000000000000000000000000001`, secondary governance `0x0000000000000000000000000000000000000000000000000000000000000002`, Asset Hub `0xc173fac324158e77fb5840738a1a541f633cbec8884c6a601c567d2b376a0539`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Gateway V1 (emitter `0x27ca963C279c93801941e1eB8799c23f407d68e7`)

| topic0 | Event |
|--------|-------|
| `0x24c5d2de620c6e25186ae16f6919eba93b6e2c1a33857cc419d9f3a00d6967e9` | `TokenSent(address indexed token, address indexed sender, uint32 indexed destinationChain, (uint8 kind, bytes data) destinationAddress, uint128 amount)` — **source leg (V1)**; `destinationChain` is a para id; `token = 0x0000000000000000000000000000000000000000` means ETH |
| `0x7153f9357c8ea496bba60bf82e67143e27b64462b49041f8e689e1b05728f84f` | `OutboundMessageAccepted(bytes32 indexed channelID, uint64 nonce, bytes32 indexed messageID, bytes payload)` — V1 message out; pairs with `TokenSent` in the same transaction |
| `0x617fdb0cb78f01551a192a3673208ec5eb09f20a90acf673c63a0dcb11745a7a` | `InboundMessageDispatched(bytes32 indexed channelID, uint64 nonce, bytes32 indexed messageID, bool success)` — **destination leg (V1)**; the unlock or mint happens in the same transaction; check `success` |
| `0xf953871855f78d5ccdd6268f2d9d69fc67f26542a35d2bba1c615521aed57054` | `AgentFundsWithdrawn(bytes32 indexed agentID, address indexed recipient, uint256 amount)` — ETH out of an agent |
| `0x2da466a7b24304f47e87fa2e1e5a81b9831ce54fec19055ce277ca2f39ba42c4` | `Deposited(address sender, uint256 amount)` — ETH sent to `depositEther` (fee top-up) |
| `0x5e3c25378b5946068b94aa2ea10c4c1e215cc975f994322b159ddc9237a973d4` | `PricingParametersChanged()` — governance |
| `0x4793c0cb5bef4b1fdbbfbcf17e06991844eb881088b012442af17a12ff38d5cd` | `TokenTransferFeesChanged()` — governance |

### 1.2 Gateway V2 (same emitter)

| topic0 | Event |
|--------|-------|
| `0x550e2067494b1736ea5573f2d19cdc0ac95b410fff161bf16f11c6229655ec9c` | `OutboundMessageAccepted(uint64 nonce, (address origin, (uint8 kind, bytes data)[] assets, (uint8 kind, bytes data) xcm, bytes claimer, uint128 value, uint128 executionFee, uint128 relayerFee) payload)` — **source leg (V2)**; **no indexed field**; there is no `TokenSent` in V2 |
| `0x8856ab63954e6c2938803a4654fb704c8779757e7bfdbe94a578e341ec637a95` | `InboundMessageDispatched(uint64 indexed nonce, bytes32 topic, bool success, bytes32 rewardAddress)` — **destination leg (V2)**; `topic` is the XCM topic id; `rewardAddress` is the relayer's Polkadot account |
| `0xa6dc208277bb3da3666e7305baf550db2daf26f8f386a431a4b27cc7a02965a2` | `CommandFailed(uint64 indexed nonce, uint256 index)` — one command of a V2 message failed; funds of that command did not move |
| `0x7c96960a1ebd8cc753b10836ea25bd7c9c4f8cd43590db1e8b3648cb0ec4cc89` | `AgentCreated(bytes32 agentID, address agent)` — a new Agent (V2 lets anyone create one) |

### 1.3 Gateway shared admin, BeefyClient, adaptors

| topic0 | Event |
|--------|-------|
| `0x4016a1377b8961c4aa6f3a2d3de830a685ddbfe0f228ffc0208eb96304c4cf1a` | `OperatingModeChanged(uint8 mode)` — Gateway; **0 = Normal, 1 = RejectingOutboundMessages: a halt** |
| `0x57f58171b8777633d03aff1e7408b96a3d910c93a7ce433a8cb7fb837dc306a6` | `ForeignTokenRegistered(bytes32 indexed tokenID, address token)` — Gateway created a Polkadot-native ERC-20 |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — Gateway implementation changed |
| `0xd95fe1258d152dc91c81b09380498adc76ed36a6079bcb2ed31eff622ae2d0f1` | `NewMMRRoot(bytes32 mmrRoot, uint64 blockNumber)` — BeefyClient; status only (a new Polkadot commitment) |
| `0xbee983fc706c692efb9b0240bddc5666c010a53af55ed5fb42d226e7e4293869` | `NewTicket(address relayer, uint64 blockNumber)` — BeefyClient; a relayer started a commitment submission |
| `0x40d3544771f3c2382030d7a42c371f55cb608ac0eaf54ef2fa846da65af1b985` | `TicketExpired()` — BeefyClient |
| `0x14bfd4fd7e654256d3222db5d1ec5e59cd23dd5df10bd8faccc1cabe984b3508` | `DepositCallInvoked(bytes32 topic, uint256 depositId)` — L1 and L2 adaptors; links the Snowbridge `topic` to the Across `depositId` |
| `0x759aee2ba41080c1e3a57140ba7b446c1347cff289214a2fd1c81554ddc17380` | `DepositCallFailed(bytes32 topic)` — L1 adaptor; the Across deposit failed and the funds went back to the `recipient` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Gateway

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x52054834` | `sendToken(address token, uint32 destinationChain, (uint8 kind, bytes data) destinationAddress, uint128 destinationFee, uint128 amount)` | **V1 deposit**: token → Asset Hub agent (or burn of a Polkadot-native token; ETH `msg.value` → the agent); emits `TokenSent` + `OutboundMessageAccepted` (V1). |
| `0xf2e500b2` | `v2_sendMessage(bytes xcm, bytes[] assets, bytes claimer, uint128 executionFee, uint128 relayerFee)` | **V2 deposit**: assets → Asset Hub agent, `msg.value` → the agent; emits `OutboundMessageAccepted` (V2). |
| `0xdf4ed829` | `submitV1((bytes32 channelID, uint64 nonce, uint8 command, bytes params, uint64 maxDispatchGas, uint256 maxFeePerGas, uint256 reward, bytes32 id) message, bytes32[] leafProof, ((bytes32 parentHash, uint256 number, bytes32 stateRoot, bytes32 extrinsicsRoot, (uint256 kind, bytes4 consensusEngineID, bytes data)[] digestItems) header, (uint256 pos, uint256 width, bytes32[] proof) headProof, (uint8 version, uint32 parentNumber, bytes32 parentHash, uint64 nextAuthoritySetID, uint32 nextAuthoritySetLen, bytes32 nextAuthoritySetRoot) leafPartial, bytes32[] leafProof, uint256 leafProofOrder) headerProof)` | **V1 inbound** (relayer); pays the relayer a gas refund + reward in ETH from the Gateway. |
| `0xde469bc7` | `v2_submit((bytes32 origin, uint64 nonce, bytes32 topic, (uint8 kind, uint64 gas, bytes payload)[] commands) message, bytes32[] leafProof, ((bytes32 parentHash, uint256 number, bytes32 stateRoot, bytes32 extrinsicsRoot, (uint256 kind, bytes4 consensusEngineID, bytes data)[] digestItems) header, (uint256 pos, uint256 width, bytes32[] proof) headProof, (uint8 version, uint32 parentNumber, bytes32 parentHash, uint64 nextAuthoritySetID, uint32 nextAuthoritySetLen, bytes32 nextAuthoritySetRoot) leafPartial, bytes32[] leafProof, uint256 leafProofOrder) headerProof, bytes32 rewardAddress)` | **V2 inbound** (relayer). |
| `0xd58a8be4` | `v2_registerToken(address token, uint8 network, uint128 executionFee, uint128 relayerFee)` | `payable`; registers an ERC-20 on Asset Hub. |
| `0xb39053c5` | `v2_createAgent(bytes32 id)` | Emits `AgentCreated`. |
| `0x98ea5fca` | `depositEther()` | `payable`; emits `Deposited`. |
| `0x928bc49d` | `quoteSendTokenFee(address token, uint32 destinationChain, uint128 destinationFee)` | View. |
| `0x5e6dae26` | `agentOf(bytes32 agentID)` | View; the Asset Hub agent id → `0xd803472c47a87D7B63E888DE53f03B4191B846a8`. |
| `0x2a6c3229` | `channelNoncesOf(bytes32 channelID)` | View → `(inbound, outbound)`; Asset Hub channel 10,731 / 12,539 on 2026-09-29. |
| `0x860929ee` | `v2_outboundNonce()` | View; 972 on 2026-09-29. |
| `0xc66414c5` | `v2_isDispatched(uint64 nonce)` | View; V2 replay guard. |
| `0x38004f69` | `operatingMode()` | View; 0 (Normal). |
| `0x26aa101f` | `isTokenRegistered(address token)` | View. |
| `0xfe61cc49` | `tokenAddressOf(bytes32 tokenID)` | View; the ERC-20 of a Polkadot-native token. |
| `0x90ffc4f9` | `BEEFY_CLIENT()` | View; the live light client. |
| `0x423e69b6` | `AGENT_EXECUTOR()` | View. |
| `0x5c60da1b` | `implementation()` | View; the ERC-1967 implementation. |

### 2.2 BeefyClient, Agent, adaptors

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xbb51f1eb` | `submitInitial((uint32 blockNumber, uint64 validatorSetID, (bytes2 payloadID, bytes data)[] payload) commitment, uint256[] bitfield, (uint8 v, bytes32 r, bytes32 s, uint256 index, address account, bytes32[] proof) proof)` | BeefyClient; opens a ticket (`NewTicket`). |
| `0x623b223d` | `submitFinal((uint32 blockNumber, uint64 validatorSetID, (bytes2 payloadID, bytes data)[] payload) commitment, uint256[] bitfield, (uint8 v, bytes32 r, bytes32 s, uint256 index, address account, bytes32[] proof)[] proofs, (uint8 version, uint32 parentNumber, bytes32 parentHash, uint64 nextAuthoritySetID, uint32 nextAuthoritySetLen, bytes32 nextAuthoritySetRoot, bytes32 parachainHeadsRoot) leaf, bytes32[] leafProof, uint256 leafProofOrder)` | BeefyClient; emits `NewMMRRoot`. |
| `0xc7d6e93d` | `submitFiatShamir((uint32 blockNumber, uint64 validatorSetID, (bytes2 payloadID, bytes data)[] payload) commitment, uint256[] bitfield, (uint8 v, bytes32 r, bytes32 s, uint256 index, address account, bytes32[] proof)[] proofs, (uint8 version, uint32 parentNumber, bytes32 parentHash, uint64 nextAuthoritySetID, uint32 nextAuthoritySetLen, bytes32 nextAuthoritySetRoot, bytes32 parachainHeadsRoot) leaf, bytes32[] leafProof, uint256 leafProofOrder)` | BeefyClient; single-transaction variant. |
| `0xa77cf3d2` | `commitPrevRandao(bytes32 commitmentHash)` | BeefyClient; second step of the interactive submission. |
| `0x9bb66b28` | `invoke(address executor, bytes data)` | Agent; Gateway only. |
| `0xd14484ad` | `depositToken((address inputToken, address outputToken, uint256 inputAmount, uint256 outputAmount, uint256 destinationChainId, uint32 fillDeadlineBuffer) params, address recipient, bytes32 topic)` | L1 adaptor; called by the Gateway in a V2 `CallContract` command. |
| `0xc554c2ef` | `depositNativeEther((address inputToken, address outputToken, uint256 inputAmount, uint256 outputAmount, uint256 destinationChainId, uint32 fillDeadlineBuffer) params, address recipient, bytes32 topic)` | L1 adaptor; ETH variant. |
| `0xe3be31bd` | `sendTokenAndCall((address inputToken, address outputToken, uint256 inputAmount, uint256 outputAmount, uint256 destinationChainId, uint32 fillDeadlineBuffer) params, (uint256 inputAmount, address router, bytes callData) swapParams, (bytes xcm, bytes[] assets, bytes claimer, uint128 executionFee, uint128 relayerFee, uint128 destinationExecutionFee) sendParams, address recipient, bytes32 topic)` | L2 adaptor; user entry on the L2. |
| `0xce8b5271` | `sendEtherAndCall((address inputToken, address outputToken, uint256 inputAmount, uint256 outputAmount, uint256 destinationChainId, uint32 fillDeadlineBuffer) params, (bytes xcm, bytes[] assets, bytes claimer, uint128 executionFee, uint128 relayerFee, uint128 destinationExecutionFee) sendParams, address recipient, bytes32 topic)` | L2 adaptor; `payable`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on 2026-09-29. Wiring read live: Gateway `implementation()`, `BEEFY_CLIENT()`, `AGENT_EXECUTOR()`, `agentOf(Asset Hub id)`, `agentOf(Bridge Hub id)` → the addresses below.

| Role | Address | One-liner |
|------|---------|-----------|
| **Gateway** (proxy) | `0x27ca963C279c93801941e1eB8799c23f407d68e7` | 357-byte `GatewayProxy`. |
| Gateway implementation | `0x36e74FCAAcb07773b144Ca19Ef2e32Fc972aC50b` | `Gateway202602`, 16,860 bytes. |
| **Asset Hub agent** | `0xd803472c47a87D7B63E888DE53f03B4191B846a8` | The escrow (899-byte `Agent`). |
| Bridge Hub agent | `0xb31623f670675501b07F027F406cea76F38ed1eE` | `Agent`. |
| BeefyClient (live) | `0x7cfc5C8b341991993080Af67D940B6aD19a010E1` | Light client used by the Gateway. |
| BeefyClient (previous) | `0x6eD05bAa904df3DE117EcFa638d4CB84e1B8A00C` | Superseded. |
| AgentExecutor | `0x836b7B5B850ac1F21Cf32Fe2f3FF7a01B521ACd2` | Delegate-call target of the Agents. |
| SnowbridgeL1Adaptor | `0xd3b11C36404B092645522B682832fCdeE07D2668` | Across bridge to L2s (4,154 bytes). |
| BEEFY relay (EOA) | `0xB8124B07467E46dE73eb5c73a7b1E03863F18062` | EOA (no code, nonce 12,347), from the docs. |
| Governance relay (EOA) | `0x0f51678Ac675C1abf2BeC1DAC9cA701cFcfFF5E2` | EOA (no code, nonce 478). |
| Asset Hub parachain relay (EOA) | `0x1F1819C3C68F9533adbB8E51C8E8428a818D693E` | EOA (no code, nonce 5,491). |

Across contracts that the adaptors call (not Snowbridge contracts): SpokePool `0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5` and MulticallHandler `0x924a9f036260DdD5808007E1AA95f08eD08aA569` on Ethereum.

## 4. Addresses — Base (8453), Arbitrum One (42161), Optimism (10)

Only the `SnowbridgeL2Adaptor` exists on these chains (9,104 bytes each, verified via `eth_getCode`); there is no Gateway, Agent or light client. The adaptor calls the Across SpokePool of its chain.

| Chain | SnowbridgeL2Adaptor | Across SpokePool used | Created (block) |
|-------|---------------------|-----------------------|-----------------|
| Base | `0x9E41656f3457F21Fd566dA6e8E9d9158f1390122` | `0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64` | 47,224,834 |
| Arbitrum One | `0x16543A52030b9525a95Bc41Ab5594e8514694203` | `0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A` | 472,628,111 |
| Optimism | `0x523309B0fdF6990383bcE3FbE1283940B3B6cBc3` | `0x6f26Bf09B1C792e3228e5467807a900A503c0281` | 152,823,036 |

---

## 5. Cross-chain summary

| Chain | ID | Gateway | Agents / BeefyClient | Snowbridge adaptor | Note |
|-------|----|---------|----------------------|--------------------|------|
| **Ethereum** | 1 | ✅ `0x27ca963C279c93801941e1eB8799c23f407d68e7` | ✅ | ✅ L1 `0xd3b11C36404B092645522B682832fCdeE07D2668` | The bridge's EVM side. |
| Base | 8453 | — | — | ✅ L2 `0x9E41656f3457F21Fd566dA6e8E9d9158f1390122` | Route through Across. |
| Arbitrum One | 42161 | — | — | ✅ L2 `0x16543A52030b9525a95Bc41Ab5594e8514694203` | Route through Across. |
| Optimism | 10 | — | — | ✅ L2 `0x523309B0fdF6990383bcE3FbE1283940B3B6cBc3` | Route through Across. |
| Polygon PoS | 137 | — | — | — | no deployment: `eth_getCode` = `0x` at the Gateway, the Asset Hub agent and all four adaptor addresses; not in the registry |
| BNB Smart Chain | 56 | — | — | — | same |
| Avalanche C-Chain | 43114 | — | — | — | same |
| Robinhood Chain | 4663 | — | — | — | same |

The counterparty is **Polkadot** (Bridge Hub 1002, Asset Hub 1000, and parachains), outside the eight chains. The registry lists Ethereum chains 1, 10, 8453 and 42161 only.

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Gateway | Custom ERC-1967 proxy (`GatewayProxy`) | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` → `0x36e74FCAAcb07773b144Ca19Ef2e32Fc972aC50b`; no admin; `receive()` rejects plain ETH. | **Polkadot governance only**: an `Upgrade` command in a governance-channel message (V1 `v1_handleUpgrade`, or V2) that passes the BEEFY proof; the new code hash must match. Emits `Upgraded`. |
| BeefyClient, Agent, AgentExecutor, adaptors | Immutable | Full runtimes, no proxy slot. A new BeefyClient means a new Gateway implementation (the address is an immutable of the implementation). | None. |

---

## 7. Detection invariants & gotchas

1. **V1 source leg:** `sendToken` → ERC-20 `Transfer(user → Asset Hub agent)` + `TokenSent` + `OutboundMessageAccepted` (V1). ETH (`token` = zero): the bridged `amount` goes to the agent by an internal transfer (no ERC-20 row), the fee stays in the Gateway, and any excess `msg.value` is refunded to the sender. A Polkadot-native token is burned (`Transfer(user → 0x0000000000000000000000000000000000000000)`) instead.
2. **V2 source leg:** `v2_sendMessage` → ERC-20 `Transfer(user → Asset Hub agent)` per asset, all `msg.value` → the agent, and one `OutboundMessageAccepted` (V2) with **no indexed topic and no `TokenSent`**. Decode `payload.assets` for the tokens and amounts.
3. **Destination leg (both versions):** a relayer (`submitV1` / `v2_submit`, often through a multicall) → `NewMMRRoot` from the BeefyClient when a new commitment is needed → ERC-20 `Transfer(Asset Hub agent → recipient)` (or a mint of a Polkadot-native token, or an internal ETH transfer from the agent) → `InboundMessageDispatched`. Check `success`; in V2 also `CommandFailed`.
4. **Link keys.** V1: `messageID = keccak256(abi.encodePacked(channelID, nonce))`, topic 2 of `OutboundMessageAccepted` and `InboundMessageDispatched` (V1); Bridge Hub uses the same id. V2 out: the global `nonce` in the data (no topic); V2 in: `nonce` (topic 1) and the XCM `topic` (data). The Polkadot side is not EVM-queryable.
5. **Two `OutboundMessageAccepted` and two `InboundMessageDispatched` topics.** Index all four; a monitor on the V1 topics misses every V2 transfer.
6. **Escrow is the Asset Hub agent.** A drain would be an outflow from `0xd803472c47a87D7B63E888DE53f03B4191B846a8` without a matching `InboundMessageDispatched(success = true)` in the same transaction. The Gateway itself holds only V1 fees.
7. **Admin and halt triggers.** `Upgraded` (Gateway); `OperatingModeChanged` (1 = outbound rejected); `PricingParametersChanged`; `TokenTransferFeesChanged`; `ForeignTokenRegistered`; a `NewMMRRoot` from a BeefyClient other than `BEEFY_CLIENT()`; `AgentFundsWithdrawn`.
8. **Two BeefyClient addresses.** The docs page lists `0x6eD05bAa904df3DE117EcFa638d4CB84e1B8A00C`, but the Gateway reads `0x7cfc5C8b341991993080Af67D940B6aD19a010E1`. Key on `BEEFY_CLIENT()`.
9. **The L2 route is Across plus Snowbridge.** Polkadot → L2: a V2 message unlocks funds to the L1 adaptor and calls it in the same transaction; it deposits into the Across SpokePool (`DepositCallInvoked(topic, depositId)`); an Across relayer fills on the L2. L2 → Polkadot: `sendTokenAndCall` / `sendEtherAndCall` on the L2 adaptor deposits into Across (`DepositCallInvoked`); the fill on Ethereum calls `Gateway.v2_sendMessage` through the Across MulticallHandler. Join the legs with the Across `depositId` (see the Across doc) and the Snowbridge `topic`.
10. **`DepositCallFailed` is a refund.** The L1 adaptor sends the unlocked funds back to the `recipient` on Ethereum when the Across deposit fails.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Gateway topics (chain-agnostic) =====
TOPIC_TOKEN_SENT                 = '\x24c5d2de620c6e25186ae16f6919eba93b6e2c1a33857cc419d9f3a00d6967e9'
TOPIC_OUTBOUND_ACCEPTED_V1       = '\x7153f9357c8ea496bba60bf82e67143e27b64462b49041f8e689e1b05728f84f'
TOPIC_OUTBOUND_ACCEPTED_V2       = '\x550e2067494b1736ea5573f2d19cdc0ac95b410fff161bf16f11c6229655ec9c'
TOPIC_INBOUND_DISPATCHED_V1      = '\x617fdb0cb78f01551a192a3673208ec5eb09f20a90acf673c63a0dcb11745a7a'
TOPIC_INBOUND_DISPATCHED_V2      = '\x8856ab63954e6c2938803a4654fb704c8779757e7bfdbe94a578e341ec637a95'
TOPIC_COMMAND_FAILED             = '\xa6dc208277bb3da3666e7305baf550db2daf26f8f386a431a4b27cc7a02965a2'
TOPIC_AGENT_CREATED              = '\x7c96960a1ebd8cc753b10836ea25bd7c9c4f8cd43590db1e8b3648cb0ec4cc89'
TOPIC_AGENT_FUNDS_WITHDRAWN      = '\xf953871855f78d5ccdd6268f2d9d69fc67f26542a35d2bba1c615521aed57054'
TOPIC_OPERATING_MODE_CHANGED     = '\x4016a1377b8961c4aa6f3a2d3de830a685ddbfe0f228ffc0208eb96304c4cf1a'
TOPIC_FOREIGN_TOKEN_REGISTERED   = '\x57f58171b8777633d03aff1e7408b96a3d910c93a7ce433a8cb7fb837dc306a6'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== BeefyClient / adaptors =====
TOPIC_NEW_MMR_ROOT               = '\xd95fe1258d152dc91c81b09380498adc76ed36a6079bcb2ed31eff622ae2d0f1'
TOPIC_DEPOSIT_CALL_INVOKED       = '\x14bfd4fd7e654256d3222db5d1ec5e59cd23dd5df10bd8faccc1cabe984b3508'
TOPIC_DEPOSIT_CALL_FAILED        = '\x759aee2ba41080c1e3a57140ba7b446c1347cff289214a2fd1c81554ddc17380'

-- ===== Selectors =====
SEL_SEND_TOKEN                   = '\x52054834'
SEL_V2_SEND_MESSAGE              = '\xf2e500b2'
SEL_SUBMIT_V1                    = '\xdf4ed829'
SEL_V2_SUBMIT                    = '\xde469bc7'
SEL_V2_REGISTER_TOKEN            = '\xd58a8be4'
SEL_V2_CREATE_AGENT              = '\xb39053c5'
SEL_L1_DEPOSIT_TOKEN             = '\xd14484ad'
SEL_L1_DEPOSIT_NATIVE_ETHER      = '\xc554c2ef'
SEL_L2_SEND_TOKEN_AND_CALL       = '\xe3be31bd'
SEL_L2_SEND_ETHER_AND_CALL       = '\xce8b5271'

-- ===== Ids =====
SNOW_ASSET_HUB_AGENT_ID          = '\x81c5ab2571199e3188135178f3c2c8e2d268be1313d029b30f534fa579b69b79'
SNOW_BRIDGE_HUB_AGENT_ID         = '\x03170a2e7597b7b7e3d84c05391d139a62b157e78786d8c082f29dcf4c111314'
SNOW_ASSET_HUB_CHANNEL_ID        = '\xc173fac324158e77fb5840738a1a541f633cbec8884c6a601c567d2b376a0539'

-- ===== Addresses — Ethereum (chain ID 1) =====
ETH_SNOW_GATEWAY                 = '\x27ca963c279c93801941e1eb8799c23f407d68e7'
ETH_SNOW_GATEWAY_IMPL            = '\x36e74fcaacb07773b144ca19ef2e32fc972ac50b'
ETH_SNOW_ASSET_HUB_AGENT         = '\xd803472c47a87d7b63e888de53f03b4191b846a8'
ETH_SNOW_BRIDGE_HUB_AGENT        = '\xb31623f670675501b07f027f406cea76f38ed1ee'
ETH_SNOW_BEEFY_CLIENT            = '\x7cfc5c8b341991993080af67d940b6ad19a010e1'
ETH_SNOW_BEEFY_CLIENT_OLD        = '\x6ed05baa904df3de117ecfa638d4cb84e1b8a00c'
ETH_SNOW_AGENT_EXECUTOR          = '\x836b7b5b850ac1f21cf32fe2f3ff7a01b521acd2'
ETH_SNOW_L1_ADAPTOR              = '\xd3b11c36404b092645522b682832fcdee07d2668'
ETH_SNOW_BEEFY_RELAY_EOA         = '\xb8124b07467e46de73eb5c73a7b1e03863f18062'
-- ===== L2 adaptors =====
BASE_SNOW_L2_ADAPTOR             = '\x9e41656f3457f21fd566da6e8e9d9158f1390122'
ARB_SNOW_L2_ADAPTOR              = '\x16543a52030b9525a95bc41ab5594e8514694203'
OP_SNOW_L2_ADAPTOR               = '\x523309b0fdf6990383bce3fbe1283940b3b6cbc3'
-- Polygon, BNB, Avalanche, Robinhood: no deployment
```

---

## 9. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` (and `[0:4]`) from the verified ABIs on Sourcify of the live Gateway implementation (`Gateway202602`), the BeefyClient, the Asset Hub agent, the L1 adaptor and the Base L2 adaptor; struct layouts from `contracts/src/v1/Types.sol`, `v2/Types.sol` and `l2-integration/Types.sol`. The value paths from `v1/Calls.sol` (`_submitOutbound`, `_sendNativeTokenOrEther`, `_sendForeignToken`), `v2/Calls.sol` (`sendMessage`) and `Gateway.sol` (`submitV1` refund, `v2_submit`); the upgrade path from `GatewayProxy.sol` and `Upgrade.sol`; the agent and channel ids from `Constants.sol` and a live `TokenSent` receipt.
- **Addresses:** the Gateway, the previous BeefyClient, the relayers and the Asset Hub agent from the docs' Infrastructure page; the live BeefyClient, AgentExecutor and the Bridge Hub agent from Gateway getters; the adaptors and the Across addresses from the mainnet registry (`l2Bridge`) and `Mainnet.sol`; all existence-checked with `eth_getCode`, and named by Sourcify. The Gateway, the Asset Hub agent and the four adaptors: `eth_getCode` = `0x` on every other target chain (§5).
- **State:** `operatingMode()` = 0; `v2_outboundNonce()` = 972; `channelNoncesOf` Asset Hub = 10,731 / 12,539, primary governance inbound 7, secondary governance inbound 25.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26,072,222–26,075,812):** `TokenSent` 4, `OutboundMessageAccepted` V1 4 and V2 2, `InboundMessageDispatched` V1 4 and V2 1, `CommandFailed` 0, `AgentCreated` 0, `ForeignTokenRegistered` 0, `OperatingModeChanged` 0; BeefyClient `NewMMRRoot` 6 (live) and 0 (previous); L1 adaptor `DepositCallInvoked` 0 and `DepositCallFailed` 0; L2 adaptors (Base, Arbitrum, Optimism) `DepositCallInvoked` 0. Over the L1 adaptor's life (blocks 24,440,524–26,075,812): 53 `DepositCallInvoked`, 6 `DepositCallFailed`.
- **Sample transactions (receipts read):** V1 deposit `0xb68988f525646a785979cc1afdcb881bde097c9373b1d34ed166a26c88cfa4dc` (`sendToken`: ERC-20 `Transfer` user → Asset Hub agent, `TokenSent` to para 2034, `OutboundMessageAccepted` on the Asset Hub channel); V2 deposit `0xf2509710b90655dd5cc427e89a188ef3a887cda12aa661155b7731af150c4ef6` (`v2_sendMessage`, 0.78 ETH, one `OutboundMessageAccepted` V2 with no topics); V1 payout `0xc69470a406790928e6f477bad99205a9ced82c7eb8d30af6fbaf03f1f2dd9344` (`NewMMRRoot`, two `Transfer` Asset Hub agent → user, two `InboundMessageDispatched` V1); V2 payout `0xa17a6568b750b1ac35febf2aeaac295d62228634769df65a07d1e4cb12682a92` (`NewMMRRoot`, USDC `Transfer` agent → recipient, `InboundMessageDispatched` V2 nonce 1,422).

Authoritative sources (opened):
- [Snowfork/snowbridge](https://github.com/Snowfork/snowbridge) — `contracts/src/` (`Gateway.sol`, `GatewayProxy.sol`, `Upgrade.sol`, `Constants.sol`, `v1/IGateway.sol`, `v1/Calls.sol`, `v2/IGateway.sol`, `v2/Calls.sol`, `v2/Types.sol`, `l2-integration/SnowbridgeL1Adaptor.sol`, `l2-integration/SnowbridgeL2Adaptor.sol`), `contracts/scripts/l2-integration/across/constants/Mainnet.sol`, `web/packages/registry/src/polkadot_mainnet_bridge_info.g.ts`
- Snowbridge docs — [Infrastructure](https://docs.snowbridge.network/resources/infrastructure.md) · [V1 to V2 upgrade guide](https://docs.snowbridge.network/developers/v1-to-v2-upgrade-guide.md)
- Sourcify — [Gateway impl](https://sourcify.dev/server/v2/contract/1/0x36e74fcaacb07773b144ca19ef2e32fc972ac50b) · [BeefyClient](https://sourcify.dev/server/v2/contract/1/0x7cfc5c8b341991993080af67d940b6ad19a010e1) · [L1 adaptor](https://sourcify.dev/server/v2/contract/1/0xd3b11c36404b092645522b682832fcdee07d2668) · [Base L2 adaptor](https://sourcify.dev/server/v2/contract/8453/0x9e41656f3457f21fd566da6e8e9d9158f1390122)
