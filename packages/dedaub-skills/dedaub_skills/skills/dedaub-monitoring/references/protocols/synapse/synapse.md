# Synapse Bridge (classic) — Topics, Selectors, Addresses (Ethereum, BNB, Avalanche, Arbitrum, Optimism, Polygon, Base; NOT Robinhood)

**Status:** verified against live RPC on every listed chain and the canonical `synapsecns/synapse-contracts` + `synapsecns/sanguine` repos on 2026-06-09. Extended on 2026-09-29 with the `SynapseBridgeAdapter` (LayerZero V2) path, `TokenRedeemV2`, and the Robinhood Chain (4663) check.
**Scope:** the **classic Synapse "mint/burn + nexus-pool" bridge** — `SynapseBridge` (the upgradeable vault that emits `TokenDeposit`/`TokenRedeem`/`TokenMint`/`TokenWithdraw`), the `SynapseBridgeAdapter` that now carries its cross-chain messages over LayerZero V2, the unified `SynapseRouter`, the `L1BridgeZap`/`L2BridgeZap` helpers, and the `SwapFlashLoan` nUSD/nETH stableswap pools that wrap the bridge. The newer **RFQ FastBridge** is documented in [rfq.md](./rfq.md); the **Circle-CCTP** router is summarised in §6 here. Chains + IDs: Ethereum 1, Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Optimism 10, Polygon 137; **Robinhood Chain 4663 and Arc 5042 have no Synapse deployment** (§4.7, §4.8). **Topics/selectors are chain-agnostic; addresses are network-specific.**

Synapse is a **lock/burn-and-mint bridge with a swap layer on each end**. The bridge token (e.g. `nUSD`, `nETH`) is the canonical cross-chain asset; on the *origin* chain a user `deposit`s (Ethereum-anchored assets locked) or `redeem`s (burns the bridge token), the off-chain validator network ("NodeGroup") observes the event, then on the *destination* chain the relayer calls `mint`/`withdraw`, optionally swapping nUSD→USDC through the local `SwapFlashLoan` nexus pool. **In this legacy validator path there is no on-chain message-passing contract** — attribution is by the `kappa` (a `bytes32` = origin tx hash digest) carried in the destination `TokenMint`/`TokenWithdraw` event.

**The current path runs through the `SynapseBridgeAdapter`** (`0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA`, the same address on all seven chains, a LayerZero V2 OApp; source in `synapsecns/sanguine` `packages/contracts-adapter`). On the source chain the user calls `bridgeERC20`: the adapter burns the token from the user (`burnFrom`, a `Transfer` to `0x0`) or moves it from the user into the local `SynapseBridge` (a `Transfer` user → bridge), sends a LayerZero message, and emits `TokenSent`. **`SynapseBridge` emits no `TokenDeposit`/`TokenRedeem` on this path.** On the destination chain the LayerZero executor delivers the message, and the adapter calls `SynapseBridge.mint`/`withdraw` with `fee = 0` and **`kappa = the LayerZero guid`**, then emits `TokenReceived`. The guid is in `TokenSent`, `TokenReceived` and the destination `TokenMint`/`TokenWithdraw`, so this path has an on-chain link key on both sides. In the pinned 12-hour window of 2026-09-28 every destination `TokenMint`/`TokenWithdraw` on the seven chains came with an adapter `TokenReceived` in the same transaction (§10).

Three deployment facts a monitoring engineer must internalise before indexing:

1. **`SynapseBridge` is the same role on all 7 chains but a different address each** (it predates vanity deploys). It is a **Transparent (OZ) upgradeable proxy**, and on **all 7 chains the live implementation is the single CREATE2 vanity address `0x5b0000258c622551a1c7c45b9f860ef90200005b`** — which does **not** match the per-chain implementation recorded in the `synapse-contracts` deployment JSONs (those are stale; the bridge was upgraded to a shared impl). Read the EIP-1967 slot, never the repo's `_Implementation.json`.
2. **`SynapseRouter` IS the single vanity address `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` on all 7 chains** (CREATE2). It is **immutable** (no proxy). It re-exposes the bridge's `deposit`/`redeem`/… selectors *and* a unified `bridge((SwapQuery),(SwapQuery))` entrypoint, so the router — not the bridge — is the contract end-users actually call today.
3. **The nUSD/nETH `SwapFlashLoan` pools are EIP-1167 minimal-proxy clones** (45-byte `0x363d3d37…` runtime) minted by a `SwapDeployer`, all delegating to one `SwapFlashLoan` master per chain. The pool **emits `TokenSwap`/`AddLiquidity`/… under the clone address**, so index per-clone, never by the master.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Notes |
|----------|------|--------|-------|
| **SynapseBridge** | The mint/burn vault. Emits every §1.1 bridge event. | **Transparent proxy** (OZ `TransparentUpgradeableProxy`) | Per-chain proxy address; **shared live impl `0x5b00…005b` on all 7** (repo `_Implementation.json` is stale). Admin = a per-chain `ProxyAdmin`. |
| **SynapseBridgeAdapter** | LayerZero V2 OApp. Source leg: `bridgeERC20` burns or escrows and emits `TokenSent`. Destination leg: `lzReceive` calls the bridge's `mint`/`withdraw` (`kappa` = LayerZero guid) and emits `TokenReceived`. | **No** (immutable, 10,604 B, `Ownable`) | Single address `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA` on all 7; `bridge()` = the chain's SynapseBridge proxy; endpoint = LayerZero EndpointV2 `0x1a44076050125825900e736c501f859c50fE728c`. |
| **SynapseRouter** | Unified swap+bridge entrypoint; re-dispatches into the bridge. | **No** (immutable, 21 KB) | Single vanity `0x7E7A…C96a` on all 7. |
| **SynapseCCTPRouter** | Front for the Circle-CCTP path. | **No** (immutable) | Single vanity `0xd5a5…2F48`; on 6/7 (**not BSC** — Circle CCTP has no BNB domain). |
| **SynapseCCTP** | The CCTP burn/mint base contract behind the router. | proxy (small) | ETH `0x12715a66…`. Emits `CircleRequestSent`/`CircleRequestFulfilled`. |
| **L1BridgeZap / L2BridgeZap** | Convenience wrapper: swaps the user token → bridge token then calls the bridge in one tx. | **No** (immutable) | L1 only on Ethereum; L2 on every chain **except Base**. |
| **SwapFlashLoan** (nUSD/nETH pools) | Saddle-style stableswap that holds nUSD↔USDC/USDT/DAI and nETH↔WETH. | **EIP-1167 clone** | 45-byte clones; one master per chain; emits §1.4 events. |
| **BridgeConfigV3** | On-chain registry of bridge-token config (Ethereum only). | **No** | ETH `0x5217…12a1`. |
| **FastBridge (RFQ)** | The current intent/RFQ bridge. | **No** (immutable) | See [rfq.md](./rfq.md). Vanity `0x5523…fB59E` on ETH/BSC/Arb/OP/Base only. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak256 on 2026-06-09. `TokenWithdraw`/`TokenMint` confirmed live on the Ethereum bridge (41 + 15 logs in a recent 50k-block window); the RFQ topics confirmed live on the Base FastBridge (see [rfq.md](./rfq.md)).

### 1.1 SynapseBridge (emits all classic bridge activity)

`*Deposit`/`*Redeem` fire on the **origin** chain (user-initiated). `*Mint`/`*Withdraw` fire on the **destination** chain (relayer-initiated) and carry the `kappa`.

| topic0 | Event | Side |
|--------|-------|------|
| `0xda5273705dbef4bf1b902a131c2eac086b7e1476a8ab0cb4da08af1fe1bd8e3b` | `TokenDeposit(address indexed to, uint256 chainId, address token, uint256 amount)` | origin (lock) |
| `0xdc5bad4651c5fbe9977a696aadc65996c468cde1448dd468ec0d83bf61c4b57c` | `TokenRedeem(address indexed to, uint256 chainId, address token, uint256 amount)` | origin (burn) |
| `0x8e57e8c5fea426159af69d47eda6c5052c7605c9f70967cf749d4aa55b70b499` | `TokenRedeemV2(bytes32 indexed to, uint256 chainId, address token, uint256 amount)` | origin (burn to a non-EVM `bytes32` recipient; emitted by `redeemV2`) |
| `0xbf14b9fde87f6e1c29a7e0787ad1d0d64b4648d8ae63da21524d9fd0f283dd38` | `TokenMint(address indexed to, address token, uint256 amount, uint256 fee, bytes32 indexed kappa)` | dest (mint) |
| `0x8b0afdc777af6946e53045a4a75212769075d30455a212ac51c9b16f9c5c9b26` | `TokenWithdraw(address indexed to, address token, uint256 amount, uint256 fee, bytes32 indexed kappa)` | dest (release) |
| `0x79c15604b92ef54d3f61f0c40caab8857927ca3d5092367163b4562c1699eb5f` | `TokenDepositAndSwap(address indexed to, uint256 chainId, address token, uint256 amount, uint8 tokenIndexFrom, uint8 tokenIndexTo, uint256 minDy, uint256 deadline)` | origin |
| `0x91f25e9be0134ec851830e0e76dc71e06f9dade75a9b84e9524071dbbc319425` | `TokenRedeemAndSwap(address indexed to, uint256 chainId, address token, uint256 amount, uint8 tokenIndexFrom, uint8 tokenIndexTo, uint256 minDy, uint256 deadline)` | origin |
| `0x9a7024cde1920aa50cdde09ca396229e8c4d530d5cfdc6233590def70a94408c` | `TokenRedeemAndRemove(address indexed to, uint256 chainId, address token, uint256 amount, uint8 swapTokenIndex, uint256 swapMinAmount, uint256 swapDeadline)` | origin |
| `0x4f56ec39e98539920503fd54ee56ae0cbebe9eb15aa778f18de67701eeae7c65` | `TokenMintAndSwap(address indexed to, address token, uint256 amount, uint256 fee, uint8 tokenIndexFrom, uint8 tokenIndexTo, uint256 minDy, uint256 deadline, bool swapSuccess, bytes32 indexed kappa)` | dest |
| `0xc1a608d0f8122d014d03cc915a91d98cef4ebaf31ea3552320430cba05211b6d` | `TokenWithdrawAndRemove(address indexed to, address token, uint256 amount, uint256 fee, uint8 swapTokenIndex, uint256 swapMinAmount, uint256 swapDeadline, bool swapSuccess, bytes32 indexed kappa)` | dest |

> **`*AndSwap`/`*AndRemove` are legacy.** The *current* shared bridge impl `0x5b0000258c622551a1c7c45b9f860ef90200005b` still defines and can emit these topics, but the swap-on-destination is now done by `SynapseRouter` after a plain `mint`/`withdraw`, so most recent flows emit only `TokenMint`/`TokenWithdraw`. Index all ten, but expect the plain pair to dominate post-2023. `TokenRedeemV2` (canonical form `TokenRedeemV2(bytes32,uint256,address,uint256)`, the `token` parameter is `IERC20` in source) had 0 logs on all eight chains in the pinned 12-hour window of 2026-09-28; no historical log was sampled for it.

### 1.2 SynapseRouter

The router declares **no events** (verified against source) — it delegates economic effect into the bridge and the swap pools, which emit. Watch the **bridge** and **pool** topics, attributing the actor from the bridge event's `to`, not the router.

### 1.3 SynapseCCTP (Circle path — base contract, not the router front)

| topic0 | Event |
|--------|-------|
| `0xc4980459837e213aedb84d9046eab1db050fec66cb9e046c4fe3b5578b01b20c` | `CircleRequestSent(uint256 chainId, address indexed sender, uint64 nonce, address token, uint256 amount, uint32 requestVersion, bytes formattedRequest, bytes32 requestID)` |
| `0x7864397c00beabf21ab17a04795e450354505d879a634dd2632f4fdc4b5ba04e` | `CircleRequestFulfilled(uint32 originDomain, address indexed recipient, address mintToken, uint256 fee, address token, uint256 amount, bytes32 requestID)` |

### 1.4 SwapFlashLoan nUSD / nETH pools (Saddle-fork stableswap)

| topic0 | Event |
|--------|-------|
| `0xc6c1e0630dbe9130cc068028486c0d118ddcea348550819defd5cb8c257f8a38` | `TokenSwap(address indexed buyer, uint256 tokensSold, uint256 tokensBought, uint128 soldId, uint128 boughtId)` |
| `0x189c623b666b1b45b83d7178f39b8c087cb09774317ca2f53c2d3c3726f222a2` | `AddLiquidity(address indexed provider, uint256[] tokenAmounts, uint256[] fees, uint256 invariant, uint256 lpTokenSupply)` |
| `0x88d38ed598fdd809c2bf01ee49cd24b7fdabf379a83d29567952b60324d58cef` | `RemoveLiquidity(address indexed provider, uint256[] tokenAmounts, uint256 lpTokenSupply)` |
| `0x43fb02998f4e03da2e0e6fff53fdbf0c40a9f45f145dc377fc30615d7d7a8a64` | `RemoveLiquidityOne(address indexed provider, uint256 lpTokenIndex, uint256 lpTokenAmount, uint256 boughtId, uint256 tokensBought)` |
| `0x7be1d9f43655fba7c836b600f6ffad89197fd4e5f7cde55a82224960e2cedf79` | `FlashLoan(address indexed receiver, uint8 tokenIndex, uint256 amount, uint256 amountFee)` |
| `0xd88ea5155021c6f8dafa1a741e173f595cdf77ce7c17d43342131d7f06afdfe5` | `NewSwapFee(uint256 newSwapFee)` |
| `0xab599d640ca80cde2b09b128a4154a8dfe608cb80f4c9399c8b954b01fd35f38` | `NewAdminFee(uint256 newAdminFee)` |
| `0xa2b71ec6df949300b59aab36b55e189697b750119dd349fcfa8c0f779e83c254` | `RampA(uint256 oldA, uint256 newA, uint256 initialTime, uint256 futureTime)` |
| `0x46e22fb3709ad289f62ce63d469248536dbc78d82b84a3d7e74ad606dc201938` | `StopRampA(uint256 currentA, uint256 time)` |

> `TokenSwap` (`0xc6c1…f8a36`) is the **Saddle/Aave-StableSwap canonical topic** and is **identical across every Saddle fork** — always filter on `(chainId, pool address, topic0)`.

### 1.5 Proxy / admin (Transparent proxy on SynapseBridge)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch on every bridge proxy to catch impl rotation** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` (bridge has `pause()`) |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` (AccessControl — NODEGROUP_ROLE/GOVERNANCE_ROLE) |

### 1.6 SynapseBridgeAdapter (LayerZero V2 path) — emitter `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA` on all 7

`TokenSent` is the **source leg** (value leaves the user in the same transaction: a burn to `0x0` or a `Transfer` into the SynapseBridge). `TokenReceived` is the **destination leg** and fires in the same transaction as the bridge's `TokenMint`/`TokenWithdraw`. The `guid` (LayerZero message id, in the data of both events) equals the destination `kappa`. `dstEid`/`srcEid` are LayerZero endpoint ids (§8, item 15). `BridgeSet`, `TokenAdded`, `PeerSet` and `OwnershipTransferred` are admin events (no value moves).

| topic0 | Event | Side |
|--------|-------|------|
| `0xe24e6284bb4ec2f5820189573deff7603191eb850be5a872ac3b72d477cdc58d` | `TokenSent(uint32 indexed dstEid, address indexed to, address indexed token, uint256 amount, bytes32 guid)` | origin (burn or escrow) |
| `0xdacad4857568b1be1bc81a68218d331a0b5cb59e116a32d2121cb960c6c7f4f5` | `TokenReceived(uint32 indexed srcEid, address indexed to, address indexed token, uint256 amount, bytes32 guid)` | dest (mint or release) |
| `0xa49730bff544fd0b716395c592e39c6fd2d2481a19b9229b5b240483db95a495` | `BridgeSet(address bridge)` | admin (set once) |
| `0x704ec8f592a58838b2937e7bddea11f797098b397e89b4651afccd08b7e33f9c` | `TokenAdded(address token, uint8 tokenType, (uint32 eid, address addr)[] remoteTokens)` | admin (`tokenType`: 1 MintBurn, 2 WithdrawDeposit) |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` | admin (LayerZero OApp peer) |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | admin |

The LayerZero EndpointV2 (`0x1a44076050125825900e736c501f859c50fE728c`) emits `PacketSent` in the source transaction and `PacketDelivered` in the destination transaction; see [`../layerzero/`](../layerzero/) for those topics.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 SynapseBridge — origin (user-facing)

All present in the live shared impl `0x5b00…005b` (PUSH4 dispatch scan on Ethereum, 2026-06-09) unless noted.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x90d25074` | `deposit(address to, uint256 chainId, address token, uint256 amount)` | Locks an Ethereum-anchored asset. Emits `TokenDeposit`. |
| `0xf3f094a1` | `redeem(address to, uint256 chainId, address token, uint256 amount)` | Burns the bridge token. Emits `TokenRedeem`. |
| `0xa07ed975` | `redeemV2(bytes32 to, uint256 chainId, address token, uint256 amount)` | Newer redeem to a non-EVM `bytes32` recipient. Burns the bridge token. Emits `TokenRedeemV2`. |
| `0xa2a2af0b` | `depositAndSwap(address,uint256,address,uint256,uint8,uint8,uint256,uint256)` | Emits `TokenDepositAndSwap`. |
| `0x839ed90a` | `redeemAndSwap(address,uint256,address,uint256,uint8,uint8,uint256,uint256)` | Emits `TokenRedeemAndSwap`. |
| `0x36e712ed` | `redeemAndRemove(address,uint256,address,uint256,uint8,uint256,uint256)` | Emits `TokenRedeemAndRemove`. |

### 2.2 SynapseBridge — destination (NODEGROUP_ROLE relayer only)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x20d7b327` | `mint(address to, address token, uint256 amount, uint256 fee, bytes32 kappa)` | Mints on destination. Emits `TokenMint`. |
| `0x1cf5f07f` | `withdraw(address to, address token, uint256 amount, uint256 fee, bytes32 kappa)` | Releases a locked asset. Emits `TokenWithdraw`. |
| *(absent in current impl)* | `mintAndSwap(...)` / `withdrawAndRemove(...)` | The legacy AndSwap/AndRemove **minter** functions are **not in the live shared impl** — destination swaps now route via SynapseRouter after a plain `mint`/`withdraw`. The legacy *event* topics (§1.1) remain defined. *(selector not pinned — superseded.)* |

### 2.3 SynapseBridge — admin / views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8456cb59` | `pause()` | GOVERNANCE_ROLE. Emits `Paused`. |
| `0x3f4ba83a` | `unpause()` | |
| `0xb250fe6b` | `setChainGasAmount(uint256)` | Airdrop gas on destination. |
| `0xa96e2423` | `setWethAddress(address)` | |
| `0xe7a59998` | `addKappas(bytes32[])` | Pre-seed processed-kappa set (replay guard). |
| `0xf2555278` | `withdrawFees(address token, address to)` | GOVERNANCE_ROLE — sweeps accrued bridge fees. |
| `0x2fe87b95` | `kappaExists(bytes32)` → `bool` | **Replay-guard read** — true once a destination kappa is processed. |
| `0xc78f6803` | `getFeeBalance(address)` → `uint256` | Accrued fee for a token. |
| `0xe00a83e0` | `chainGasAmount()` → `uint256` | |
| `0xac865626` | `bridgeVersion()` → `uint256` | |
| `0x498a4c2d` | `startBlockNumber()` → `uint256` | First block of the deployment (backfill anchor). |
| `0x040141e5` | `WETH_ADDRESS()` → `address` | |
| `0xf3befd01` | `NODEGROUP_ROLE()` → `bytes32` | |
| `0xf36c8f5c` | `GOVERNANCE_ROLE()` → `bytes32` | |

### 2.4 SynapseRouter (verified against the live router bytecode `0x7E7A…C96a`)

The router uses `SwapQuery = (address swapAdapter, address tokenOut, uint256 minAmountOut, uint256 deadline, bytes rawParams)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2288147` | `bridge(address to, uint256 chainId, address token, uint256 amount, (address,address,uint256,uint256,bytes) originQuery, (address,address,uint256,uint256,bytes) destQuery)` | **The main modern entrypoint.** Swaps origin token → bridge token, then calls the bridge. |
| `0xb5d1cdd4` | `swap(address to, address token, uint256 amount, (address,address,uint256,uint256,bytes) query)` | Local-only swap (no bridge). |
| `0x58b5b777` | `calculateBridgeFee(address token, uint256 amount)` → `uint256` | |
| `0xd38e7888` | `getConnectedBridgeTokens(address tokenOut)` → struct[] | Routing discovery. |
| `0x3bc758fd` | `getOriginAmountOut(address,string[],uint256)` | Quote. |
| `0x077e1199` | `getDestinationAmountOut((string,uint256)[],address)` | Quote. |
| `0xf8a06888` | `bridgeTokens()` → `address[]` | All supported bridge tokens. |
| `0xda46098c` | `setAllowance(address,address,uint256)` | owner — token approvals to the bridge. |
| — | The router **also re-dispatches** the bridge selectors `0x90d25074`/`0xf3f094a1`/`0x839ed90a`/`0x36e712ed`/`0xa2a2af0b` and the pool selectors `0x91695586`/`0x3e3a1560`, all present in its bytecode. |

### 2.5 SwapFlashLoan nUSD / nETH pool

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x91695586` | `swap(uint8 tokenIndexFrom, uint8 tokenIndexTo, uint256 dx, uint256 minDy, uint256 deadline)` → `uint256` | Emits `TokenSwap`. |
| `0xa95b089f` | `calculateSwap(uint8,uint8,uint256)` → `uint256` | View. |
| `0x4d49e87d` | `addLiquidity(uint256[] amounts, uint256 minToMint, uint256 deadline)` → `uint256` | Emits `AddLiquidity`. |
| `0x31cd52b0` | `removeLiquidity(uint256 amount, uint256[] minAmounts, uint256 deadline)` → `uint256[]` | Emits `RemoveLiquidity`. |
| `0x3e3a1560` | `removeLiquidityOneToken(uint256 tokenAmount, uint8 tokenIndex, uint256 minAmount, uint256 deadline)` → `uint256` | Emits `RemoveLiquidityOne`. |
| `0x82b86600` | `getToken(uint8 index)` → `address` | Index → underlying. Live check: `getToken(0)` on the Ethereum nUSD pool returns DAI. |
| `0x66c0bd24` | `getTokenIndex(address tokenAddress)` → `uint8` | Underlying → index. Live check: `getTokenIndex(USDC)` on the Ethereum nUSD pool returns 1. |
| `0xd46300fd` | `getA()` → `uint256` | Amplification coefficient. |

### 2.6 SynapseCCTP

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x304ddb4c` | `sendCircleToken(address recipient, uint256 chainId, address burnToken, uint256 amount, uint32 requestVersion, bytes swapParams)` | Emits `CircleRequestSent`. |
| `0x4a5ae51d` | `receiveCircleToken(bytes message, bytes signature, uint32 requestVersion, bytes formattedRequest)` | Emits `CircleRequestFulfilled`. |

### 2.7 Transparent-proxy upgrade surface (SynapseBridge proxy)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3659cfe6` | `upgradeTo(address)` | ProxyAdmin-only (called on the proxy by the admin). Emits `Upgraded`. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | |
| `0x8f283970` | `changeAdmin(address)` | Emits `AdminChanged`. |

### 2.8 SynapseBridgeAdapter (`RemoteToken = (uint32 eid, address addr)`, `TokenType` = `uint8`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa811504f` | `bridgeERC20(uint32 dstEid, address to, address token, uint256 amount, uint64 gasLimit)` | **User entrypoint (source leg).** `payable`: `msg.value` is the LayerZero native fee. Burns or escrows `amount`; emits `TokenSent`. |
| `0x13137d65` | `lzReceive((uint32 srcEid, bytes32 sender, uint64 nonce) origin, bytes32 guid, bytes message, address executor, bytes extraData)` | Called by the LayerZero EndpointV2 only (destination leg). Calls the bridge's `mint`/`withdraw`; emits `TokenReceived`. |
| `0x1c3eab28` | `getNativeFee(uint32 dstEid, uint64 gasLimit)` → `uint256` | View: the LayerZero fee quote. |
| `0xe78cea92` | `bridge()` → `address` | View: the local SynapseBridge proxy (read live on all 7). |
| `0xd82d0531` | `getLocalAddress(uint32 eid, address remoteAddr)` → `address` | View: remote token → local token. |
| `0x6e035876` | `getRemoteAddress(uint32 eid, address localAddr)` → `address` | View: local token → remote token. |
| `0x93272baf` | `getTokenType(address localAddr)` → `uint8` | View: 0 Unknown, 1 MintBurn, 2 WithdrawDeposit. |
| `0x4099dba0` | `addToken(address token, uint8 tokenType, (uint32 eid, address addr)[] remoteTokens)` | `onlyOwner`. Emits `TokenAdded`. **Route-change signal.** |
| `0x8dd14802` | `setBridge(address newBridge)` | `onlyOwner`, once only. Emits `BridgeSet`. |
| `0x3400288b` | `setPeer(uint32 eid, bytes32 peer)` | `onlyOwner` (OApp). Emits `PeerSet`. **A peer change redirects trust for a chain.** |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. The bridge proxy's live impl + admin read from the EIP-1967 slots.

| Role | Address | One-liner |
|------|---------|-----------|
| **SynapseBridge** (proxy) | `0x2796317b0fF8538F253012862c06787Adfb8cEb6` | Mint/burn vault; emits all §1.1 events. Live impl `0x5b00…005b`; admin `0x7b3c1f09…`. |
| SynapseBridge live impl | `0x5b0000258c622551a1c7c45b9f860ef90200005b` | **Shared CREATE2 impl across all 7 chains** (repo's `0x31fe3938…` is stale). |
| SynapseBridge ProxyAdmin | `0x7b3c1f09088bdc9f136178e170ac668c8ed095f2` | OZ ProxyAdmin (2.7 KB) — upgrade authority on Ethereum. |
| **SynapseBridgeAdapter** | `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA` | LayerZero V2 path; **same address on all 7 chains**; immutable. `bridge()` = `0x2796317b0fF8538F253012862c06787Adfb8cEb6`; `owner()` = `0x67F60b0891EBD842Ebe55E4CCcA1098d7Aac1A55` (a 2-of-3 Safe). |
| **SynapseRouter** | `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` | Vanity, **same on all 7 chains**; immutable. |
| **SynapseCCTPRouter** | `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48` | Vanity, on 6/7 (not BSC); immutable. |
| SynapseCCTP (base) | `0x12715a66773BD9C54534a01aBF01d05F6B4Bd35E` | CCTP burn/mint contract behind the router; emits §1.3 events. |
| **L1BridgeZap** | `0x6571d6be3d8460CF5F7d6711Cd9961860029D85F` | One-tx swap-then-bridge helper (Ethereum-only). |
| **BridgeConfigV3** | `0x5217c83ca75559B1f8a8803824E5b7ac233A12a1` | On-chain bridge-token config registry. |
| **nUSD nexus pool** (SwapFlashLoan clone) | `0x1116898DdA4015eD8dDefb84b6e8Bc24528Af2d8` | 45-byte EIP-1167 clone → master `0x5A5f…1655`; nUSD↔DAI/USDC/USDT. |
| SwapFlashLoan master | `0x5A5fFf6F753d7C11A56A52FE47a177a87e431655` | The pool implementation every clone delegates to. |
| nUSD bridge token | `0x1B84765dE8B7566e4cEAF4D0fD3c5aF52D3DdE4F` | Canonical stable bridge asset. |
| FastBridge (RFQ) | `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` | See [rfq.md](./rfq.md). |

> The Ethereum bridge proxy is mostly a **destination** today: in a recent 50k-block window it logged 41 `TokenWithdraw` + 15 `TokenMint` and 0 `TokenDeposit`/`TokenRedeem`.

---

## 4. Addresses — other chains

`SynapseRouter` (`0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a`), `SynapseCCTPRouter` (`0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48`) and `SynapseBridgeAdapter` (`0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA`) are **byte-identical addresses on every chain that has them**; only the bridge proxy, its per-chain ProxyAdmin, the zap, the pools, and the bridge tokens diverge. Every address below verified live via `eth_getCode` on its chain's publicnode RPC, 2026-06-09; the adapter rows on 2026-09-29.

**SynapseBridgeAdapter per chain** (one runtime, 10,604 bytes, code hash `0x4de8c184d0cc14beb38bf3b7245cc253650f5d0cae411893f54e32bd2fa078c1` on all 7; `bridge()` and `owner()` read live on 2026-09-29; deployment files in `synapsecns/sanguine` `packages/contracts-adapter/deployments/<chain>/SynapseBridgeAdapter.json`):

| Chain | `bridge()` (the local SynapseBridge proxy) | `owner()` |
|-------|--------------------------------------------|-----------|
| Ethereum 1 | `0x2796317b0fF8538F253012862c06787Adfb8cEb6` | `0x67F60b0891EBD842Ebe55E4CCcA1098d7Aac1A55` |
| Base 8453 | `0xf07d1C752fAb503E47FEF309bf14fbDD3E867089` | `0xE48de7c3A9094b2CbA88D4f72E3cbc2E60Fad8cF` |
| Arbitrum 42161 | `0x6F4e8eBa4D337f874Ab57478AcC2Cb5BACdc19c9` | `0x1d9Bfc24d9e7EeDa4119Ceca11EaF4c24E622E62` |
| Optimism 10 | `0xAf41a65F786339e7911F4acDAD6BD49426F2Dc6b` | `0x2431CBdc0792F5485c4cb0a9bEf06C4f21541D52` |
| Polygon 137 | `0x8F5BBB2BB8c2Ee94639E55d5F41de9b4839C1280` | `0xBdD38B2eaae34C9FCe187909e81e75CBec0dAA7A` |
| BNB 56 | `0xd123f70AE324d34A9E76b67a27bf77593bA8749f` | `0xA316d83e67EEfD136f4C077de1cD4163A681F8A8` |
| Avalanche 43114 | `0xC05e61d0E7a63D27546389B7aD62FdFf5A91aACE` | `0xE9530411510c4D6CF699712904bECA2849488176` |
| Robinhood 4663 | — (no code at `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA`) | — |

### 4.1 BNB Smart Chain (chain ID 56) — RPC `https://bsc-rpc.publicnode.com`

| Role | Address |
|------|---------|
| SynapseBridge (proxy) | `0xd123f70AE324d34A9E76b67a27bf77593bA8749f` (impl `0x5b00…005b`; admin `0x35e4edd1f12aba7d0c46a8e48513a5b0b679c89c`) |
| SynapseRouter | `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` |
| L2BridgeZap | `0x749F37Df06A99D6A8E065dd065f8cF947ca23697` |
| nUSD pool (V3) | `0x740B36494A5Ebe0F18f3e05f3a951ae292080d33` |
| nUSD token | `0x23b891e5c62e0955ae2bd185990103928ab817b3` |
| FastBridge (RFQ) | `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` |
| **SynapseCCTPRouter** | **NOT DEPLOYED** (`0x` — Circle CCTP has no BNB domain). |
| nETH | **none** (no nETH market on BSC). |

### 4.2 Avalanche C-Chain (chain ID 43114) — RPC `https://avalanche-c-chain-rpc.publicnode.com`

| Role | Address |
|------|---------|
| SynapseBridge (proxy) | `0xC05e61d0E7a63D27546389B7aD62FdFf5A91aACE` (impl `0x5b00…005b`; admin `0xe2f6d34fd09d21f4121d648e191e842ac95ac0dc`) |
| SynapseRouter | `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` |
| SynapseCCTPRouter | `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48` |
| L2BridgeZap | `0x0EF812f4c68DC84c22A4821EF30ba2ffAB9C2f3A` |
| nUSD pool (V3) | `0xA196a03653f6cc5cA0282A8BD7Ec60e93f620afc` |
| nUSD token | `0xCFc37A6AB183dd4aED08C204D1c2773c0b1BDf46` |
| nETH token | `0x19E1ae0eE35c0404f835521146206595d37981ae` |
| **FastBridge (RFQ)** | **NOT DEPLOYED** (`0x`). |

### 4.3 Arbitrum One (chain ID 42161) — RPC `https://arbitrum-one-rpc.publicnode.com`

| Role | Address |
|------|---------|
| SynapseBridge (proxy) | `0x6F4e8eBa4D337f874Ab57478AcC2Cb5BACdc19c9` (impl `0x5b00…005b`; admin `0x432036208d2717394d2614d6697c46df3ed69540`) |
| SynapseRouter | `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` |
| SynapseCCTPRouter | `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48` |
| L2BridgeZap | `0x37f9aE2e0Ea6742b9CAD5AbCfB6bBC3475b3862B` |
| nUSD pool (V3) | `0x9Dd329F5411466d9e0C488fF72519CA9fEf0cb40` |
| nETH pool | `0xa067668661C84476aFcDc6fA5D758C4c01C34352` |
| nUSD token | `0x2913E812Cf0dcCA30FB28E6Cac3d2DCFF4497688` |
| nETH token | `0x3ea9B0ab55F34Fb188824Ee288CeaEfC63cf908e` |
| FastBridge (RFQ) | `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` |

### 4.4 Optimism (chain ID 10) — RPC `https://optimism-rpc.publicnode.com`

| Role | Address |
|------|---------|
| SynapseBridge (proxy) | `0xAf41a65F786339e7911F4acDAD6BD49426F2Dc6b` (impl `0x5b00…005b`; admin `0x8745773cc6e70577819bb76f51fa7640cece505f`) |
| SynapseRouter | `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` |
| SynapseCCTPRouter | `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48` |
| L2BridgeZap | `0x470f9522ff620eE45DF86C58E54E6A645fE3b4A7` |
| nUSD pool (V3) | `0xF44938b0125A6662f9536281aD2CD6c499F22004` |
| nETH pool (ETHPool, full deploy) | `0xE27BFf97CE92C3e1Ff7AA9f86781FDd6D48F5eE9` |
| nUSD token | `0x67C10C397dD0Ba417329543c1a40eb48AAa7cd00` |
| nETH token | `0x809DC529f07651bD43A172e8dB6f4a7a0d771036` |
| FastBridge (RFQ) | `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` |

### 4.5 Polygon PoS (chain ID 137) — RPC `https://polygon-bor-rpc.publicnode.com`

| Role | Address |
|------|---------|
| SynapseBridge (proxy) | `0x8F5BBB2BB8c2Ee94639E55d5F41de9b4839C1280` (impl `0x5b00…005b`; admin `0x612f3a0226463599ccbcabff89623904ef38bcb9`) |
| SynapseRouter | `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` |
| SynapseCCTPRouter | `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48` |
| L2BridgeZap | `0xb883A9f35650ff82fdBC9Ed867e98FEd0457b584` |
| nUSD pool (V2) | `0x85fCD7Dd0a1e1A9FCD5FD886ED522dE8221C3EE5` *(USDPool/MetaSwap; the nUSDPoolV3 file is absent — see note)* |
| nUSD token | `0xb6c473756050de474286bed418b77aeac39b02af` |
| **FastBridge (RFQ)** | **NOT DEPLOYED** (`0x`). |
| nETH | **none** (no nETH market on Polygon). |

### 4.6 Base (chain ID 8453) — RPC `https://base-rpc.publicnode.com`

| Role | Address |
|------|---------|
| SynapseBridge (proxy) | `0xf07d1C752fAb503E47FEF309bf14fbDD3E867089` (impl `0x5b00…005b`; admin `0xaed5b25be1c3163c907a471082640450f928ddfe`) |
| SynapseRouter | `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` |
| SynapseCCTPRouter | `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48` |
| nETH pool (45-byte EIP-1167 clone → master `0x9508bf380c1e6f751d97604732ef1bae6673f299`) | `0x6223bD82010E2fB69F329933De20897e7a4C225f` |
| nETH token | `0xb554A55358fF0382Fb21F0a478C3546d1106Be8c` |
| FastBridge (RFQ) | `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` |
| **L2BridgeZap** | **NOT DEPLOYED** (`0x` — Base post-dates the zap pattern; bridging goes through `SynapseRouter`). |
| nUSD | **none** as a Base-native nUSD pool (Base is an nETH + USDC-via-CCTP/RFQ chain). |

### 4.7 Robinhood Chain (chain ID 4663) — **no Synapse deployment**

`eth_getCode` returns `0x` (nonce 0) on `https://rpc.mainnet.chain.robinhood.com` on 2026-09-29 at every Synapse address of this doc and of [rfq.md](./rfq.md): SynapseBridgeAdapter `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA`, SynapseRouter `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a`, SynapseCCTPRouter `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48`, SynapseCCTP `0x12715a66773BD9C54534a01aBF01d05F6B4Bd35E`, the shared bridge implementation `0x5b0000258c622551a1c7c45b9f860ef90200005b`, the Ethereum and Base bridge proxy literals `0x2796317b0fF8538F253012862c06787Adfb8cEb6` and `0xf07d1C752fAb503E47FEF309bf14fbDD3E867089`, FastBridge `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E`, FastBridgeRouterV2 `0x00cD000000003f7F682BE4813200893d4e690000`, FastBridgeRouter `0x0000000000489d89D2B233D3375C045dfD05745F` and FastBridgeInterceptor `0xFb1fb1060C550A9b274C64f70dadF16f2aD34fB1`. Chain id 4663 is not in the SDK's `SupportedChainId` enum (`synapsecns/sanguine` `packages/sdk-router/src/constants/chainIds.ts`), and `packages/contracts-adapter/deployments/` has no Robinhood folder. The bridge events of §1.1 had 0 logs on Robinhood Chain in the pinned 12-hour window of 2026-09-28.

### 4.8 Arc (chain ID 5042) — **no Synapse deployment**

`eth_getCode` returns `0x` on `https://rpc.mainnet.arc.io` on 2026-10-05 at the same address list as §4.7. The only Arc hit among the SDK addresses is `0xBBbfD134E9b44BfB5123898BA36b01dE7ab93d98`, the Relay protocol's ApprovalProxy v2 (SDK `RELAY_ADDRESS`), which is not a Synapse contract.

---

## 5. Cross-chain summary

| Chain | ID | SynapseBridge (proxy) | SynapseBridgeAdapter | SynapseRouter | CCTPRouter | FastBridge (RFQ) | L2/L1 Zap | nUSD pool | nETH pool |
|---|---|---|---|---|---|---|---|---|---|
| Ethereum | 1 | `0x2796317b0fF8538F253012862c06787Adfb8cEb6` | ✓ | ✓ `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` | ✓ | ✓ | L1 ✓ | ✓ | (via ETHPool elsewhere) |
| BNB | 56 | `0xd123f70AE324d34A9E76b67a27bf77593bA8749f` | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ |
| Avalanche | 43114 | `0xC05e61d0E7a63D27546389B7aD62FdFf5A91aACE` | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ (token) |
| Arbitrum | 42161 | `0x6F4e8eBa4D337f874Ab57478AcC2Cb5BACdc19c9` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Optimism | 10 | `0xAf41a65F786339e7911F4acDAD6BD49426F2Dc6b` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Polygon | 137 | `0x8F5BBB2BB8c2Ee94639E55d5F41de9b4839C1280` | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ |
| Base | 8453 | `0xf07d1C752fAb503E47FEF309bf14fbDD3E867089` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| **Robinhood** | 4663 | ✗ `0x` | ✗ `0x` | ✗ `0x` | ✗ `0x` | ✗ `0x` | ✗ | ✗ | ✗ |

**Vanity / address tells:**
- `SynapseRouter` = `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a` on **all 7** (CREATE2 vanity).
- `SynapseBridgeAdapter` = `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA` on **all 7** (a vanity address: it starts with `5ba0` and ends with `05ba`), one code hash on all 7.
- `SynapseBridge` **impl** = `0x5b0000258c622551a1c7c45b9f860ef90200005b` on **all 7** (note the symmetric `5b…5b` vanity) — the *proxy* address differs per chain.
- `SynapseCCTPRouter` = `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48` (6/7, not BNB).
- `FastBridge` (RFQ) = `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` (5/7, not Avax/Polygon — see [rfq.md](./rfq.md)).
- The bridge **proxies have no shared vanity**; key bridge presence on `(chainId, proxy address)`.
- **Robinhood Chain (4663): nothing** — no code at any Synapse address, not in the SDK chain list (§4.7).

**Counterparty chains outside the seven:** Synapse also bridges to/from chains *not* in this set — historically Fantom, Harmony, Boba, Moonbeam, Moonriver, Aurora, Metis, Cronos, Canto, Klaytn, DFK, Blast (router exception `0x0000000000365b1d…`), Linea, Scroll, Berachain, HyperEVM, Unichain, Worldchain (all present in the SDK `SWAP_QUOTER_V2`/router maps). The `chainId` field inside `TokenDeposit`/`TokenRedeem` may therefore reference a destination outside these seven — treat an out-of-set `chainId` as a valid cross-chain leg, not bad data.

---

## 6. SynapseCCTP (Circle path) — chain coverage

The `SynapseCCTPRouter` (`0xd5a5…2F48`) wraps Circle's CCTP for native USDC transfers and is present on **Ethereum, Avalanche, Arbitrum, Optimism, Polygon, Base** (all returned 13,019-byte code) — **not on BNB** (Circle has no BNB CCTP domain; `0x`). USDC moved via this path emits `CircleRequestSent`/`CircleRequestFulfilled` on the **base SynapseCCTP** contract (ETH `0x12715a66…`), not the router. CCTP is also documented protocol-wide under [`../cctp/`](../cctp/).

---

## 7. Proxies (old & new)

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. Both read live via `eth_getStorageAt` on 2026-06-09.

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **SynapseBridge** | **Transparent (OZ) proxy** | Impl slot populated (= `0x5b00…005b` on all 7); admin slot populated (per-chain ProxyAdmin); `Upgraded`/`AdminChanged` topics. | Per-chain `ProxyAdmin` (ETH `0x7b3c1f09…`), itself owned by Synapse multisig/DAO. |
| **SynapseBridgeAdapter** | **Immutable** (`Ownable` OApp) | 10,604-byte runtime, code hash `0x4de8c184d0cc14beb38bf3b7245cc253650f5d0cae411893f54e32bd2fa078c1` on all 7; EIP-1967 impl slot empty (read live 2026-09-29). | No upgrade path. `owner()` (per chain, §4) can `setPeer`, `addToken`, and `setBridge` once; watch `PeerSet`/`TokenAdded`/`OwnershipTransferred` (§1.6). |
| **SynapseRouter** | **Immutable** | 21,216-byte runtime; EIP-1967 impl slot = `0x000…0`. | none. |
| **SynapseCCTPRouter** | **Immutable** | 13,019-byte runtime; impl slot empty. | none. |
| **SwapFlashLoan pools** | **EIP-1167 minimal-proxy clone** | 45-byte runtime `0x363d3d373d3d3d363d73<master>5af43d…`; impl slot **empty** (the target is hard-coded in the clone bytecode, not in the EIP-1967 slot). ETH clone → master `0x5A5fFf6F…1655`. | none (clone target fixed at deploy). |
| **L1/L2BridgeZap** | **Immutable** | 7–10 KB runtime; impl slot empty. | none. |
| **SynapseCCTP (base)** | small proxy | ETH `0x12715a66…` is 2,206 bytes (proxy/minimal). | governance. |
| **FastBridge** | **Immutable** | see [rfq.md](./rfq.md). | none. |

### 7.1 The implementation-drift gotcha (verified 2026-06-09)

The `synapse-contracts` repo records a *different* per-chain `SynapseBridge_Implementation` for each chain (e.g. ETH `0x31fe3938…`, BSC `0x2264C281…`, Arb `0x97a7af2A…`). **All are stale.** The live EIP-1967 impl slot on **every one of the 7 proxies** reads the same shared CREATE2 vanity `0x5b0000258c622551a1c7c45b9f860ef90200005b` (15,381-byte impl). Always resolve the impl from the slot; treat the repo `_Implementation.json` as historical only. Watch `Upgraded(address)` (`0xbc7cd75a…`) on each proxy to catch the next rotation.

---

## 8. Detection invariants & gotchas

1. **Origin vs destination is the event, not the contract.** `TokenDeposit`/`TokenRedeem`/`TokenRedeemV2`/`TokenDepositAndSwap`/`TokenRedeemAndSwap`/`TokenRedeemAndRemove` fire on the **source** chain; `TokenMint`/`TokenWithdraw`/`TokenMintAndSwap`/`TokenWithdrawAndRemove` fire on the **destination** chain and carry the indexed `bytes32 kappa`. A complete transfer = an origin event on chain A linked to a destination event on chain B sharing the same `kappa`. On the adapter path (item 13) the origin event is the adapter's `TokenSent`, not a bridge event.
2. **`kappa` is the cross-chain join key** (a `bytes32` digest of the origin tx in the legacy path; the LayerZero `guid` on the adapter path). It is `indexed` in `TokenMint`/`TokenWithdraw` (topic[2]) but **absent from the origin bridge events** — to link both legs of a legacy transfer you compute/track the kappa off-chain or watch `kappaExists(kappa)` flipping true. On the adapter path the same value is in the data of the source `TokenSent` (`guid`), so both legs join on chain. Use `kappa` to dedupe destination replays.
3. **`to` is the recipient, not the sender.** It is `indexed` (topic[1]) in every bridge event. The actual `msg.sender` on the origin is often `SynapseRouter`/a zap/an aggregator, and on the destination it is the NODEGROUP relayer (legacy) or the `SynapseBridgeAdapter` (adapter path; `tx.to` is then the LayerZero executor). Attribute the user by `to`, never `tx.from`.
4. **The router, not the bridge, is what users call now.** Most modern origin transfers are `SynapseRouter.bridge(...)` (`0xc2288147`) which swaps then internally calls `deposit`/`redeem` on the bridge — so the `TokenDeposit`/`TokenRedeem` log's `tx.to` is the router `0x7E7A…`. Don't filter origin volume by `tx.to == bridge`.
5. **Live bridge impl ≠ repo impl** (§7.1). Read `0x5b00…005b` from the slot; the per-chain `_Implementation.json` addresses are stale decoys.
6. **`*AndSwap`/`*AndRemove` minter functions are gone from the current impl**, but their *event topics* are still defined and historical logs exist. Index the ten bridge topics for backfill; expect only the plain `TokenMint`/`TokenWithdraw` (+ origin `TokenDeposit`/`TokenRedeem`, or the adapter's `TokenSent`) going forward.
7. **`TokenSwap` (`0xc6c1…f8a36`) is a generic Saddle topic** shared by every Saddle/StableSwap fork — filter on `(chainId, pool address)`. Pools are 45-byte **EIP-1167 clones**; the clone, not the master, is the emitter.
8. **`SynapseRouter`/`SynapseCCTPRouter` are the SAME literal address on every chain that has them** — always key on `(chainId, address)` to avoid cross-chain confusion; the bridge proxy is the only per-chain-unique core address.
9. **Chain absences are real:** **no FastBridge on Avalanche or Polygon**; **no SynapseCCTP on BNB**; **no L2BridgeZap on Base**; **no nETH market on BNB/Polygon**; **no nUSD pool on Base**. Each is `0x` on `eth_getCode` (verified), not an indexing miss.
10. **Out-of-set destination chainIds are valid** (§5) — Synapse spans ~25 chains; an inner `chainId` of e.g. 250 (Fantom) or 81457 (Blast) in a `TokenDeposit` is a genuine bridge leg to a chain outside the seven.
11. **Replay/pause watch:** the bridge is **pausable** (`Paused`/`Unpaused` topics, `pause()` `0x8456cb59`) and has `setChainGasAmount` + `withdrawFees` admin functions — monitor `Upgraded`, `AdminChanged`, `RoleGranted`, `Paused`, and `withdrawFees` as security signals on each proxy.
12. **`nUSD` ERC-20 on Ethereum is a 45-byte clone too** (`0x1B84…dE4F`) — it is the nexus LP-style token, not a full ERC-20 deploy; reading its `Transfer` works normally but its code is a clone.
13. **The adapter path has no bridge event on the source chain.** `bridgeERC20` (`0xa811504f`) on `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA` burns the token from the user (MintBurn tokens: an ERC-20 `Transfer` user → `0x0`) or moves it straight into the local SynapseBridge proxy (WithdrawDeposit tokens: a `Transfer` user → bridge). The only Synapse log is `TokenSent` (`0xe24e6284bb4ec2f5820189573deff7603191eb850be5a872ac3b72d477cdc58d`). A monitor keyed on `TokenDeposit`/`TokenRedeem` sees no source leg: in the pinned window of 2026-09-28 those had 0 logs on all eight chains, while `TokenSent` had 12 on the seven chains. `msg.value` of `bridgeERC20` is the LayerZero fee, not bridged value.
14. **On the destination, `TokenReceived` + `TokenMint`/`TokenWithdraw` share one transaction and one id.** The adapter calls `mint`/`withdraw` with `fee = 0` and `kappa = guid`, then emits `TokenReceived(srcEid, to, token, amount, guid)`. Count the value once: `TokenMint`/`TokenWithdraw` is the bridge's record of the same payout.
15. **`dstEid`/`srcEid` are LayerZero endpoint ids, not chain ids:** Ethereum 30101, BNB 30102, Avalanche 30106, Polygon 30109, Arbitrum 30110, Optimism 30111, Base 30184 (see [`../layerzero/v2.md`](../layerzero/v2.md)). Samples: an Ethereum `TokenSent` with `dstEid` 30110 (Arbitrum); an Ethereum `TokenReceived` with `srcEid` 30184 (Base).
16. **Adapter admin signals:** `PeerSet` (a new trusted remote adapter for an eid), `TokenAdded` (a new route or token pair) and `OwnershipTransferred` on the adapter; the adapter is immutable, so there is no `Upgraded` to watch on it. The adapter holds `NODEGROUP_ROLE` (`0xb5c00e6706c3d213edd70ff33717fac657eacc5fe161f07180cf1fcab13cc4cd`) on the SynapseBridge proxy (`hasRole` read live on Ethereum, 2026-09-29): a `RoleGranted`/`RoleRevoked` for that role changes who can mint and release.
17. **Robinhood Chain (4663) has no Synapse contract** (§4.7). A `TokenSent.dstEid` or `TokenDeposit.chainId` never points to it today.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== SynapseBridge event topics (chain-agnostic) =====
TOPIC_TOKEN_DEPOSIT             = '\xda5273705dbef4bf1b902a131c2eac086b7e1476a8ab0cb4da08af1fe1bd8e3b'
TOPIC_TOKEN_REDEEM             = '\xdc5bad4651c5fbe9977a696aadc65996c468cde1448dd468ec0d83bf61c4b57c'
TOPIC_TOKEN_REDEEM_V2          = '\x8e57e8c5fea426159af69d47eda6c5052c7605c9f70967cf749d4aa55b70b499'
TOPIC_TOKEN_MINT               = '\xbf14b9fde87f6e1c29a7e0787ad1d0d64b4648d8ae63da21524d9fd0f283dd38'
TOPIC_TOKEN_WITHDRAW           = '\x8b0afdc777af6946e53045a4a75212769075d30455a212ac51c9b16f9c5c9b26'
TOPIC_TOKEN_DEPOSIT_AND_SWAP   = '\x79c15604b92ef54d3f61f0c40caab8857927ca3d5092367163b4562c1699eb5f'
TOPIC_TOKEN_REDEEM_AND_SWAP    = '\x91f25e9be0134ec851830e0e76dc71e06f9dade75a9b84e9524071dbbc319425'
TOPIC_TOKEN_REDEEM_AND_REMOVE  = '\x9a7024cde1920aa50cdde09ca396229e8c4d530d5cfdc6233590def70a94408c'
TOPIC_TOKEN_MINT_AND_SWAP      = '\x4f56ec39e98539920503fd54ee56ae0cbebe9eb15aa778f18de67701eeae7c65'
TOPIC_TOKEN_WITHDRAW_AND_REMOVE= '\xc1a608d0f8122d014d03cc915a91d98cef4ebaf31ea3552320430cba05211b6d'
-- ===== SynapseCCTP =====
TOPIC_CIRCLE_REQUEST_SENT      = '\xc4980459837e213aedb84d9046eab1db050fec66cb9e046c4fe3b5578b01b20c'
TOPIC_CIRCLE_REQUEST_FULFILLED = '\x7864397c00beabf21ab17a04795e450354505d879a634dd2632f4fdc4b5ba04e'
-- ===== SwapFlashLoan nexus pools =====
TOPIC_TOKEN_SWAP               = '\xc6c1e0630dbe9130cc068028486c0d118ddcea348550819defd5cb8c257f8a38'
TOPIC_ADD_LIQUIDITY            = '\x189c623b666b1b45b83d7178f39b8c087cb09774317ca2f53c2d3c3726f222a2'
TOPIC_REMOVE_LIQUIDITY         = '\x88d38ed598fdd809c2bf01ee49cd24b7fdabf379a83d29567952b60324d58cef'
TOPIC_REMOVE_LIQUIDITY_ONE     = '\x43fb02998f4e03da2e0e6fff53fdbf0c40a9f45f145dc377fc30615d7d7a8a64'
TOPIC_POOL_FLASHLOAN           = '\x7be1d9f43655fba7c836b600f6ffad89197fd4e5f7cde55a82224960e2cedf79'
-- ===== Proxy / admin =====
TOPIC_UPGRADED                 = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED            = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_PAUSED                   = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                 = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_ROLE_GRANTED             = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
-- ===== SynapseBridgeAdapter (LayerZero V2 path) =====
TOPIC_SBA_TOKEN_SENT           = '\xe24e6284bb4ec2f5820189573deff7603191eb850be5a872ac3b72d477cdc58d'
TOPIC_SBA_TOKEN_RECEIVED       = '\xdacad4857568b1be1bc81a68218d331a0b5cb59e116a32d2121cb960c6c7f4f5'
TOPIC_SBA_BRIDGE_SET           = '\xa49730bff544fd0b716395c592e39c6fd2d2481a19b9229b5b240483db95a495'
TOPIC_SBA_TOKEN_ADDED          = '\x704ec8f592a58838b2937e7bddea11f797098b397e89b4651afccd08b7e33f9c'
TOPIC_SBA_PEER_SET             = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_OWNERSHIP_TRANSFERRED    = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== SynapseBridge selectors =====
SEL_DEPOSIT                    = '\x90d25074'
SEL_REDEEM                     = '\xf3f094a1'
SEL_REDEEM_V2                  = '\xa07ed975'
SEL_DEPOSIT_AND_SWAP           = '\xa2a2af0b'
SEL_REDEEM_AND_SWAP            = '\x839ed90a'
SEL_REDEEM_AND_REMOVE          = '\x36e712ed'
SEL_MINT                       = '\x20d7b327'
SEL_WITHDRAW                   = '\x1cf5f07f'
SEL_PAUSE                      = '\x8456cb59'
SEL_SET_CHAIN_GAS_AMOUNT       = '\xb250fe6b'
SEL_WITHDRAW_FEES              = '\xf2555278'
SEL_KAPPA_EXISTS               = '\x2fe87b95'
SEL_ADD_KAPPAS                 = '\xe7a59998'
-- ===== SynapseRouter selectors =====
SEL_ROUTER_BRIDGE              = '\xc2288147'
SEL_ROUTER_SWAP                = '\xb5d1cdd4'
SEL_CALCULATE_BRIDGE_FEE       = '\x58b5b777'
SEL_BRIDGE_TOKENS              = '\xf8a06888'
-- ===== SwapFlashLoan pool selectors =====
SEL_POOL_SWAP                  = '\x91695586'
SEL_POOL_CALCULATE_SWAP        = '\xa95b089f'
SEL_POOL_ADD_LIQUIDITY         = '\x4d49e87d'
SEL_POOL_REMOVE_LIQUIDITY_ONE  = '\x3e3a1560'
SEL_POOL_GET_TOKEN             = '\x82b86600'
SEL_POOL_GET_TOKEN_INDEX       = '\x66c0bd24'
-- ===== SynapseCCTP selectors =====
SEL_SEND_CIRCLE_TOKEN          = '\x304ddb4c'
SEL_RECEIVE_CIRCLE_TOKEN       = '\x4a5ae51d'
-- ===== SynapseBridgeAdapter selectors =====
SEL_SBA_BRIDGE_ERC20           = '\xa811504f'
SEL_SBA_LZ_RECEIVE             = '\x13137d65'
SEL_SBA_GET_NATIVE_FEE         = '\x1c3eab28'
SEL_SBA_BRIDGE                 = '\xe78cea92'
SEL_SBA_ADD_TOKEN              = '\x4099dba0'
SEL_SBA_SET_BRIDGE             = '\x8dd14802'
SEL_SBA_SET_PEER               = '\x3400288b'
-- ===== Proxy slots =====
EIP1967_IMPL_SLOT              = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT             = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Cross-chain singletons =====
SYNAPSE_ROUTER_ALL_CHAINS      = '\x7e7a0e201fd38d3adaa9523da6c109a07118c96a'   -- same on all 7
SYNAPSE_BRIDGE_IMPL_ALL_CHAINS = '\x5b0000258c622551a1c7c45b9f860ef90200005b'   -- shared live impl on all 7
SYNAPSE_CCTP_ROUTER            = '\xd5a597d6e7ddf373a92c8f477daaa673b0902f48'   -- 6/7 (not BNB)
FAST_BRIDGE_RFQ                = '\x5523d3c98809dddb82c686e152f5c58b1b0fb59e'   -- 5/7 (not Avax/Polygon)
SYNAPSE_BRIDGE_ADAPTER         = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'   -- same on all 7; none on Robinhood
LZ_ENDPOINT_V2                 = '\x1a44076050125825900e736c501f859c50fe728c'   -- the adapter's endpoint on all 7
ETH_SYNAPSE_BRIDGE_ADAPTER     = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'
BASE_SYNAPSE_BRIDGE_ADAPTER    = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'
ARB_SYNAPSE_BRIDGE_ADAPTER     = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'
OP_SYNAPSE_BRIDGE_ADAPTER      = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'
POLY_SYNAPSE_BRIDGE_ADAPTER    = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'
BNB_SYNAPSE_BRIDGE_ADAPTER     = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'
AVAX_SYNAPSE_BRIDGE_ADAPTER    = '\x5ba000bb06230e0582e111f08e1f2f2f200005ba'
ETH_SBA_OWNER_SAFE             = '\x67f60b0891ebd842ebe55e4ccca1098d7aac1a55'   -- 2-of-3 Safe
-- Robinhood Chain (4663): no Synapse contract; every address of this block returns 0x there

-- ===== SynapseBridge proxy (per chain) =====
ETH_BRIDGE                     = '\x2796317b0ff8538f253012862c06787adfb8ceb6'
BSC_BRIDGE                     = '\xd123f70ae324d34a9e76b67a27bf77593ba8749f'
AVAX_BRIDGE                    = '\xc05e61d0e7a63d27546389b7ad62fdff5a91aace'
ARB_BRIDGE                     = '\x6f4e8eba4d337f874ab57478acc2cb5bacdc19c9'
OP_BRIDGE                      = '\xaf41a65f786339e7911f4acdad6bd49426f2dc6b'
POLY_BRIDGE                    = '\x8f5bbb2bb8c2ee94639e55d5f41de9b4839c1280'
BASE_BRIDGE                    = '\xf07d1c752fab503e47fef309bf14fbdd3e867089'

-- ===== Ethereum extras =====
ETH_BRIDGE_PROXY_ADMIN         = '\x7b3c1f09088bdc9f136178e170ac668c8ed095f2'
ETH_L1_BRIDGE_ZAP              = '\x6571d6be3d8460cf5f7d6711cd9961860029d85f'
ETH_BRIDGE_CONFIG_V3           = '\x5217c83ca75559b1f8a8803824e5b7ac233a12a1'
ETH_NUSD_POOL                  = '\x1116898dda4015ed8ddefb84b6e8bc24528af2d8'
ETH_SWAPFLASHLOAN_MASTER       = '\x5a5fff6f753d7c11a56a52fe47a177a87e431655'
ETH_NUSD_TOKEN                 = '\x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f'
ETH_SYNAPSE_CCTP_BASE          = '\x12715a66773bd9c54534a01abf01d05f6b4bd35e'

-- ===== L2BridgeZap (per chain; NONE on Base) =====
BSC_L2_BRIDGE_ZAP              = '\x749f37df06a99d6a8e065dd065f8cf947ca23697'
AVAX_L2_BRIDGE_ZAP             = '\x0ef812f4c68dc84c22a4821ef30ba2ffab9c2f3a'
ARB_L2_BRIDGE_ZAP              = '\x37f9ae2e0ea6742b9cad5abcfb6bbc3475b3862b'
OP_L2_BRIDGE_ZAP               = '\x470f9522ff620ee45df86c58e54e6a645fe3b4a7'
POLY_L2_BRIDGE_ZAP             = '\xb883a9f35650ff82fdbc9ed867e98fed0457b584'

-- ===== nUSD / nETH pools & tokens =====
BSC_NUSD_POOL                  = '\x740b36494a5ebe0f18f3e05f3a951ae292080d33'
AVAX_NUSD_POOL                 = '\xa196a03653f6cc5ca0282a8bd7ec60e93f620afc'
ARB_NUSD_POOL                  = '\x9dd329f5411466d9e0c488ff72519ca9fef0cb40'
ARB_NETH_POOL                  = '\xa067668661c84476afcdc6fa5d758c4c01c34352'
OP_NUSD_POOL                   = '\xf44938b0125a6662f9536281ad2cd6c499f22004'
OP_NETH_POOL                   = '\xe27bff97ce92c3e1ff7aa9f86781fdd6d48f5ee9'
BASE_NETH_POOL                 = '\x6223bd82010e2fb69f329933de20897e7a4c225f'
BSC_NUSD_TOKEN                 = '\x23b891e5c62e0955ae2bd185990103928ab817b3'
AVAX_NUSD_TOKEN                = '\xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46'
AVAX_NETH_TOKEN                = '\x19e1ae0ee35c0404f835521146206595d37981ae'
ARB_NUSD_TOKEN                 = '\x2913e812cf0dcca30fb28e6cac3d2dcff4497688'
ARB_NETH_TOKEN                 = '\x3ea9b0ab55f34fb188824ee288ceaefc63cf908e'
OP_NUSD_TOKEN                  = '\x67c10c397dd0ba417329543c1a40eb48aaa7cd00'
OP_NETH_TOKEN                  = '\x809dc529f07651bd43a172e8db6f4a7a0d771036'
POLY_NUSD_TOKEN                = '\xb6c473756050de474286bed418b77aeac39b02af'
BASE_NETH_TOKEN                = '\xb554a55358ff0382fb21f0a478c3546d1106be8c'
```

---

## 10. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` (full = topic0; `[0:4]` = selector) with keccak256. The eight bridge topics, the CCTP topics, the pool `TokenSwap`/`AddLiquidity`/… topics, and all proxy topics were computed from the canonical event signatures. Router and bridge **selectors were cross-checked by PUSH4 dispatch scan of the live runtime bytecode** (router `0x7E7A…`, bridge impl `0x5b00…005b`) — every router selector and every bridge origin/destination/admin selector listed was found present; `bridge`'s exact `SwapQuery=(address,address,uint256,uint256,bytes)` layout was confirmed by matching `0xc2288147` against the live router code. The legacy `mintAndSwap`/`withdrawAndRemove` *minter selectors* were **NOT** found in the current impl (recorded as superseded).
- **Live event cross-check (`eth_getLogs`):** `TokenWithdraw` (`0x8b0afdc7…`, 41 logs) and `TokenMint` (`0xbf14b9fd…`, 15 logs) confirmed on the Ethereum bridge `0x2796317b…` in a recent 50k-block window; the pool `TokenSwap` topic matches the Saddle canonical. RFQ topics confirmed live on Base — see [rfq.md](./rfq.md).
- **Addresses:** parsed from the `synapsecns/synapse-contracts` `deployments/<chain>/*.json` files and the `synapsecns/sanguine` `packages/sdk-router/src/constants/addresses.ts` maps, then **existence-checked via `eth_getCode`** on each chain's publicnode RPC. Non-empty = present; `0x` recorded as not-deployed (FastBridge on Avax/Polygon, CCTP on BNB, L2BridgeZap on Base, nETH on BNB/Polygon, nUSD pool on Base).
- **Proxies:** the EIP-1967 impl + admin slots were read live via `eth_getStorageAt` on all 7 bridge proxies — every one returned impl `0x5b0000258c…00005b` (the shared CREATE2 impl, contradicting the repo `_Implementation.json`) and a per-chain `ProxyAdmin` in the admin slot. SynapseRouter/CCTPRouter/zaps returned an empty impl slot (immutable); SwapFlashLoan pools are 45-byte EIP-1167 clones with an empty slot and a hard-coded master (`0x363d3d373d3d3d363d73<master>5af43d…`, ETH master `0x5A5f…1655`).

Additions of 2026-09-29:

- **`TokenRedeemV2`:** the event line `event TokenRedeemV2(bytes32 indexed to, uint256 chainId, IERC20 token, uint256 amount);` read from `contracts/bridge/SynapseBridge.sol`; topic0 recomputed as `keccak256("TokenRedeemV2(bytes32,uint256,address,uint256)")`.
- **Pool selectors:** `getToken(uint8)` is `0x82b86600` and `getTokenIndex(address)` is `0x66c0bd24` (recomputed). The earlier row paired `0x66c0bd24` with `getToken(uint8)`; that was wrong and is corrected in §2.5. Both selectors answered live `eth_call`s on the Ethereum nUSD pool `0x1116898DdA4015eD8dDefb84b6e8Bc24528Af2d8`.
- **SynapseBridgeAdapter:** source `packages/contracts-adapter/src/SynapseBridgeAdapter.sol` and `src/interfaces/ISynapseBridgeAdapter.sol` in `synapsecns/sanguine`; every topic0 and selector of §1.6 and §2.8 recomputed with `keccak256`. The address and the constructor arguments (EndpointV2 `0x1a44076050125825900e736c501f859c50fE728c`, deployer-owner `0x0fea3e5840334Fc758A3DECf14546bFdfBef5cd3`) come from `deployments/<chain>/SynapseBridgeAdapter.json` for ethereum, base, arbitrum, optimism, polygon, bnb and avalanche. `eth_getCode` on all 8 chains: 10,604 bytes with one code hash on the 7, `0x` on Robinhood Chain; EIP-1967 slot empty. `bridge()` and `owner()` read live on the 7 (§4). Etherscan shows the contract as verified, name `SynapseBridgeAdapter`.
- **Measured activity** (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, all emitters of each topic0):
  - SynapseBridge `TokenMint`: Ethereum 0, Base 0, Arbitrum 1, Optimism 1, Polygon 1, BNB 0, Avalanche 4, Robinhood 0.
  - SynapseBridge `TokenWithdraw`: Ethereum 4, Avalanche 1, all others 0.
  - `TokenDeposit`, `TokenRedeem`, `TokenRedeemV2` and the `*AndSwap`/`*AndRemove` topics: 0 on all eight chains.
  - Adapter `TokenSent` at `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA`: Ethereum 1, Base 1, Arbitrum 4, Optimism 0, Polygon 1, BNB 0, Avalanche 5 (12 in total).
  - Adapter `TokenReceived`: Ethereum 4, Base 0, Arbitrum 1, Optimism 1, Polygon 1, BNB 0, Avalanche 5. Each chain's count equals its `TokenMint` + `TokenWithdraw` count.
- **Sample transactions** (read with `eth_getTransactionReceipt`): Ethereum `0xdad3fb07a6a5fa074306012d3f60037639a11d845b538c57ecd6eae346fcd543` (the LayerZero executor calls in; the bridge emits `TokenWithdraw` and moves the token from the bridge to the recipient; the adapter emits `TokenReceived` with `srcEid` 30184; EndpointV2 emits `PacketDelivered`); Avalanche `0xb26c0ce1e5af3ad71448113c0aefffcab0ffc54fade45318b781ab428b3f82e4` (`TokenMint`: a mint from `0x0` to the bridge, then a transfer from the bridge to the recipient, then `TokenReceived`); Ethereum `0xfddcc9841ca69b934e99b7f8aaccbe7a608ec72242d19b421f691cf2d979d432` (`bridgeERC20` with a LayerZero fee in `msg.value`, a burn of the token from the user to `0x0`, `PacketSent`, then `TokenSent` with `dstEid` 30110).
- **Robinhood Chain:** §4.7 lists the addresses read with `eth_getCode` (all `0x`, nonce 0) and the official lists checked.

Authoritative sources:
- Canonical repos: [`synapsecns/synapse-contracts`](https://github.com/synapsecns/synapse-contracts) (`deployments/`, `contracts/bridge/`) · [`synapsecns/sanguine`](https://github.com/synapsecns/sanguine) (`packages/sdk-router`, `packages/contracts-rfq`, [`packages/contracts-adapter`](https://github.com/synapsecns/sanguine/tree/master/packages/contracts-adapter), [`sdk-router/src/constants/chainIds.ts`](https://github.com/synapsecns/sanguine/blob/master/packages/sdk-router/src/constants/chainIds.ts)).
- Explorer: [Etherscan SynapseBridgeAdapter](https://etherscan.io/address/0x5ba000bb06230e0582e111f08e1f2f2f200005ba).
- Docs: [Synapse contract addresses](https://docs.synapseprotocol.com/reference/contract-addresses) · [SynapseRouter docs](https://docs.synapseprotocol.com/docs/Routers/Synapse-Router/) · [SynapseBridge.md](https://github.com/synapsecns/synapse-contracts/blob/master/docs/bridge/SynapseBridge.md).
- Explorers: [Etherscan SynapseBridge](https://etherscan.io/address/0x2796317b0ff8538f253012862c06787adfb8ceb6) · [Blockscan multichain](https://blockscan.com/Address/0x2796317b0ff8538f253012862c06787adfb8ceb6).
