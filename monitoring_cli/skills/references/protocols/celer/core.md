# Celer cBridge & MessageBus — Topics, Selectors, Addresses (Ethereum, BNB, Avalanche, Arbitrum, Optimism, Polygon, Base)

**Status:** verified against live RPC on every listed chain and the canonical `celer-network/sgn-v2-contracts` repo on 2026-06-09.
**Scope:** the **liquidity-pool cBridge** (`Bridge`/`Pool`) and the **Celer IM `MessageBus`** (cross-chain arbitrary-message layer). The **pegged-token mint/burn bridge** (`PeggedTokenBridge[V2]` + `OriginalTokenVault[V2]`) is a separate product line — see [pegged.md](./pegged.md). Topics/selectors are **chain-agnostic** (`topic0 = keccak256(event sig)`, selector = `keccak256(sig)[0:4]`); addresses are **network-specific**.

Celer cBridge is the liquidity-network successor to cBridge 1.0. The **`Bridge`** contract is a **non-upgradeable immutable singleton** — its EIP-1967 implementation *and* admin slots are both empty (`0x`), and it is deployed directly (not behind a proxy) on every chain. Cross-chain settlement is **off-chain attested**: a user calls `send()` on the source chain (emits `Send`), the off-chain State Guardian Network (SGN) signs a relay request, and a relayer calls `relay()` on the destination chain (emits `Relay`) which pays out from the destination pool's liquidity. **There is no on-chain link between a source `Send` and a destination `Relay`** — they live on different chains and are correlated only by the deterministic `transferId` (see §Detection invariants). Liquidity providers call `addLiquidity()`/`withdraw()`.

The **`MessageBus`** (Celer IM) is the opposite: a **Transparent (EIP-1967) upgradeable proxy** with a populated admin (ProxyAdmin) and impl slot on every chain. The source side (`MessageBusSender`) emits `Message`/`Message2`/`MessageWithTransfer`; the destination side (`MessageBusReceiver`) verifies SGN signatures and emits `Executed`. `MessageBus` is a single contract that inherits both Sender and Receiver. Its `liquidityBridge`/`pegBridge`/`pegVault`/`pegBridgeV2`/`pegVaultV2` pointers wire it to the cBridge and pegged contracts (verified live on Ethereum — see §Verification).

**Governance:** the `Bridge` `owner()` on Ethereum and Base is the same multisig/EOA `0xf380166f8490f24af32bf47d1aa217fba62b6575`. The `MessageBus` proxy is upgraded by a per-chain `ProxyAdmin` (different address per chain — see §Proxies). Signing power is held by the SGN validator set, rotated via `resetSigners`/`updateSigners` (emits `SignersUpdated`).

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Where |
|----------|------|--------|-------|
| **Bridge** (extends `Pool`) | Liquidity-pool cBridge. `send`/`sendNative` (src), `relay` (dst), `addLiquidity`/`withdraw` (LP). Emits `Send`/`Relay`/`LiquidityAdded`/`WithdrawDone`. | **No** — immutable singleton (impl & admin slots empty) | ETH, BNB, Avax, Arb, OP, Polygon, **Base** |
| **MessageBus** (Sender+Receiver) | Celer IM arbitrary cross-chain message layer. `sendMessage` (src) / `executeMessage` (dst). Emits `Message`/`Message2`/`MessageWithTransfer`/`Executed`/`NeedRetry`. | **Yes** — Transparent EIP-1967 proxy | ETH, BNB, Avax, Arb, OP, Polygon (**NOT Base**) |
| `WithdrawInbox` | Optional peg/cooldown refund inbox (`WithdrawalRequest`). | No | Not at the historic literal on ETH (returns `0x`); chain-specific |

`Bridge` inherits `Pool`, which inherits the safeguard mixins `Signers`, `Pauser`, `VolumeControl`, `DelayedTransfer` — so `Bridge` also emits `SignersUpdated`, `Paused`/`Unpaused`, `EpochVolumeUpdated`, `DelayedTransferAdded`/`DelayedTransferExecuted`, etc. Those same mixin events appear on the pegged contracts in [pegged.md](./pegged.md) — **disambiguate by emitter address**.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Bridge / Pool — emits all cBridge liquidity activity

Emitter = the chain's `Bridge` address (§3+). **None of `Send`'s 8 params are `indexed`** — everything is in `data` (verified live, §Verification), so you cannot filter a `Send` by token/receiver via topics; filter by `(address, topic0)` and decode the data.

| topic0 | Event |
|--------|-------|
| `0x89d8051e597ab4178a863a5190407b98abfeff406aa8db90c59af76612e58f01` | `Send(bytes32 transferId, address sender, address receiver, address token, uint256 amount, uint64 dstChainId, uint64 nonce, uint32 maxSlippage)` |
| `0x79fa08de5149d912dce8e5e8da7a7c17ccdf23dd5d3bfe196802e6eb86347c7c` | `Relay(bytes32 transferId, address sender, address receiver, address token, uint256 amount, uint64 srcChainId, bytes32 srcTransferId)` |
| `0xd5d28426c3248963b1719df49aa4c665120372e02c8249bbea03d019c39ce764` | `LiquidityAdded(uint64 seqnum, address provider, address token, uint256 amount)` |
| `0x48a1ab26f3aa7b62bb6b6e8eed182f292b84eb7b006c0254386b268af20774be` | `WithdrawDone(bytes32 withdrawId, uint64 seqnum, address receiver, address token, uint256 amount, bytes32 refid)` |
| `0x8b59d386e660418a48d742213ad5ce7c4dd51ae81f30e4e2c387f17d907010c9` | `MinSendUpdated(address token, uint256 amount)` |
| `0x4f12d1a5bfb3ccd3719255d4d299d808d50cdca9a0a5c2b3a5aaa7edde73052c` | `MaxSendUpdated(address token, uint256 amount)` |
| `0xc56b0d14c4940515800d94ebbd0f3f5d8cc58ba1109c12536bd993b72e466e4f` | `MinAddUpdated(address token, uint256 amount)` |

### 1.2 Safeguard mixins (also emitted by Bridge AND by the pegged contracts in pegged.md — key on emitter)

| topic0 | Event | Mixin |
|--------|-------|-------|
| `0xf126123539a68393c55697f617e7d1148e371988daed246c2f41da99965a23f8` | `SignersUpdated(address[] _signers, uint256[] _powers)` | Signers |
| `0x68e825132f7d4bc837dea2d64ac9fc19912bf0224b67f9317d8f1a917f5304a1` | `ResetNotification(uint256 resetTime)` | Signers |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | Pauser |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | Pauser |
| `0x6719d08c1888103bea251a4ed56406bd0c3e69723c8a1686e017e7bbe159b6f8` | `PauserAdded(address account)` | Pauser |
| `0xcd265ebaf09df2871cc7bd4133404a235ba12eff2041bb89d9c714a2621c7c7e` | `PauserRemoved(address account)` | Pauser |
| `0xdc5a48d79e2e147530ff63ecdbed5a5a66adb9d5cf339384d5d076da197c40b5` | `GovernorAdded(address account)` | Governor |
| `0x1ebe834e73d60a5fec822c1e1727d34bc79f2ad977ed504581cc1822fe20fb5b` | `GovernorRemoved(address account)` | Governor |
| `0x2664fec2ff76486ac58ed087310855b648b15b9d19f3de8529e95f7c46b7d6b3` | `EpochLengthUpdated(uint256 length)` | VolumeControl |
| `0x608e49c22994f20b5d3496dca088b88dfd81b4a3e8cc3809ea1e10a320107e89` | `EpochVolumeUpdated(address token, uint256 cap)` | VolumeControl |
| `0xc0a39f234199b125fb93713c4d067bdcebbf691087f87b79c0feb92b156ba8b6` | `DelayPeriodUpdated(uint256 period)` | DelayedTransfer |
| `0xceaad6533bfb481492fb3e08ef19297f46611b8fa9de5ef4cf8dc23a56ad09ce` | `DelayThresholdUpdated(address token, uint256 threshold)` | DelayedTransfer |
| `0xcbcfffe5102114216a85d3aceb14ad4b81a3935b1b5c468fadf3889eb9c5dce6` | `DelayedTransferAdded(bytes32 id)` | DelayedTransfer |
| `0x3b40e5089937425d14cdd96947e5661868357e224af59bd8b24a4b8a330d4426` | `DelayedTransferExecuted(bytes32 id, address receiver, address token, uint256 amount)` | DelayedTransfer |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address previousOwner, address newOwner)` | Ownable |

### 1.3 MessageBusSender (source side)

Emitter = the chain's `MessageBus` proxy (§3+). `sender` is **indexed** (topic[1]).

| topic0 | Event |
|--------|-------|
| `0xce3972bfffe49d317e1d128047a97a3d86b25c94f6f04409f988ef854d25e0e4` | `Message(address indexed sender, address receiver, uint256 dstChainId, bytes message, uint256 fee)` |
| `0xe66fbe37d84ca73c589f782ac278844918ea6c56a4917f58707f715588080df2` | `Message2(address indexed sender, bytes receiver, uint256 dstChainId, bytes message, uint256 fee)` (to non-EVM chains, >20-byte receiver) |
| `0x172762498a59a3bc4fed3f2b63f94f17ea0193cffdc304fe7d3eaf4d342d2f66` | `MessageWithTransfer(address indexed sender, address receiver, uint256 dstChainId, address bridge, bytes32 srcTransferId, bytes message, uint256 fee)` |
| `0x78473f3f373f7673597f4f0fa5873cb4d375fea6d4339ad6b56dbd411513cb3f` | `FeeWithdrawn(address receiver, uint256 amount)` |
| `0x892dfdc99ecd3bb4f2f2cb118dca02f0bd16640ff156d3c6459d4282e336a5f2` | `FeeBaseUpdated(uint256 feeBase)` |
| `0x210d4d5d2d36d571207dac98e383e2441c684684c885fb2d7c54f8d24422074c` | `FeePerByteUpdated(uint256 feePerByte)` |

### 1.4 MessageBusReceiver (destination side)

`receiver` is **indexed** in `Executed` (topic[1]). `msgType`/`status` are Solidity enums → canonicalize to `uint8`.

| topic0 | Event |
|--------|-------|
| `0xa635eb05143f74743822bbd96428928de4c8ee8cc578299749be9425c17bb34d` | `Executed(uint8 msgType, bytes32 msgId, uint8 status, address indexed receiver, uint64 srcChainId, bytes32 srcTxHash)` |
| `0xe49c2c954d381d1448cf824743aeff9da7a1d82078a7c9e5817269cc359bd26c` | `NeedRetry(uint8 msgType, bytes32 msgId, uint64 srcChainId, bytes32 srcTxHash)` |
| `0xffdd6142bbb721f3400e3908b04b86f60649b2e4d191e3f4c50c32c3e6471d2f` | `CallReverted(string reason)` (debug helper inside a reverted app call) |
| `0xbf9977180dc6e6cff25598c8e59150cecd7f8e448e092633d38ab7ee223ae058` | `LiquidityBridgeUpdated(address liquidityBridge)` |
| `0xd60e9ceb4f54f1bfb1741a4b35fc9d806d7ed48200b523203b92248ea38fa17d` | `PegBridgeUpdated(address pegBridge)` |
| `0xa9db0c32d9c6c2f75f3b95047a9e67cc1c010eab792a4e6ca777ce918ad94aad` | `PegVaultUpdated(address pegVault)` |
| `0xfb337a6c76476534518d5816caeb86263972470fedccfd047a35eb1825eaa9e8` | `PegBridgeV2Updated(address pegBridgeV2)` |
| `0x918a691a2a82482a10e11f43d7b627b2ba220dd08f251cb61933c42560f6fcb5` | `PegVaultV2Updated(address pegVaultV2)` |

`msgType`: `0 = MessageOnly`, `1 = MessageWithTransfer`. `status` (TxStatus): `0 = Null`, `1 = Success`, `2 = Fail`, `3 = Fallback`, `4 = Pending`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Bridge / Pool

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa5977fbb` | `send(address _receiver, address _token, uint256 _amount, uint64 _dstChainId, uint64 _nonce, uint32 _maxSlippage)` | Source-chain transfer. Emits `Send`. `transferId = keccak256(sender,receiver,token,amount,dstChainId,nonce,uint64(srcChainId))`. **Verified present in Base Bridge bytecode.** |
| `0x3f2e5fc3` | `sendNative(address _receiver, uint256 _amount, uint64 _dstChainId, uint64 _nonce, uint32 _maxSlippage)` | `payable` — wraps native to `nativeWrap` then `send`. |
| `0xcdd1b25d` | `relay(bytes _relayRequest, bytes[] _sigs, address[] _signers, uint256[] _powers)` | Destination-chain payout. Emits `Relay`. SGN-signed. |
| `0x56688700` | `addLiquidity(address _token, uint256 _amount)` | LP deposit. Emits `LiquidityAdded`. |
| `0x7044c89e` | `addNativeLiquidity(uint256 _amount)` | `payable` LP deposit of native. |
| `0xa21a9280` | `withdraw(bytes _wdmsg, bytes[] _sigs, address[] _signers, uint256[] _powers)` | LP / refund withdrawal. Emits `WithdrawDone`. **Same selector as OriginalTokenVault.withdraw — disambiguate by contract.** |
| `0x3c64f04b` | `transfers(bytes32)` → `bool` | Replay-guard map: has this `transferId` been processed. |
| `0xe09ab428` | `withdraws(bytes32)` → `bool` | Replay-guard map for withdrawals. |
| `0xf8b30d7d` | `minSend(address)` → `uint256` | Per-token minimum send amount. |
| `0x618ee055` | `maxSend(address)` → `uint256` | Per-token max (0 = no cap). |
| `0xccde517a` | `minAdd(address)` → `uint256` | Per-token min add-liquidity. |
| `0x2fd1b0a4` | `minimalMaxSlippage()` → `uint32` | Global min slippage (slippage × 1e6). |
| `0x457bfa2f` | `nativeWrap()` → `address` | WETH-equivalent for this chain. |
| `0x682dbc22` | `verifySigs(bytes _msg, bytes[] _sigs, address[] _signers, uint256[] _powers)` | SGN quorum check (also the `ISigsVerifier` used by pegged contracts). |
| `0xa7bdf45a` | `resetSigners(address[] _signers, uint256[] _powers)` | Owner reset of validator set. |
| `0xfbd51ae6` | `updateSigners(uint256 _triggerTime, bytes _newSigners, address[] _curSigners, uint256[] _curPowers, bytes[] _sigs, address[] _signers, uint256[] _powers)` | SGN-signed validator rotation. Emits `SignersUpdated`. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | Pauser. |
| `0x8da5cb5b` / `0xf2fde38b` | `owner()` / `transferOwnership(address)` | Ownable. |

### 2.2 MessageBus (Sender + Receiver)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9f3ce55a` | `sendMessage(address _receiver, uint256 _dstChainId, bytes _message)` | `payable`. Emits `Message`. |
| `0x7d7a101d` | `sendMessage(bytes _receiver, uint256 _dstChainId, bytes _message)` | `payable`, non-EVM receiver. Emits `Message2`. |
| `0x4289fbb3` | `sendMessageWithTransfer(address _receiver, uint256 _dstChainId, address _srcBridge, bytes32 _srcTransferId, bytes _message)` | `payable`. Emits `MessageWithTransfer`. |
| `0x5335dca2` | `calcFee(bytes _message)` → `uint256` | `feeBase + feePerByte*len`. |
| `0x2ff4c411` | `withdrawFee(address _account, uint256 _cumulativeFee, bytes[] _sigs, address[] _signers, uint256[] _powers)` | SGN-signed fee withdrawal. Emits `FeeWithdrawn`. |
| `0x3f395aff` | `executeMessageWithTransfer(bytes, (uint8,address,address,address,uint256,uint64,uint64,bytes32,bytes32), bytes[], address[], uint256[])` | `payable`. Delivers msg+transfer; emits `Executed`/`NeedRetry`. |
| `0x7b80ab20` | `executeMessageWithTransferRefund(bytes, (uint8,address,address,address,uint256,uint64,uint64,bytes32,bytes32), bytes[], address[], uint256[])` | `payable`. Refund path. |
| `0x468a2d04` | `executeMessage(bytes, (address,address,uint64,bytes32), bytes[], address[], uint256[])` | `payable`. Message-only (RouteInfo). Emits `Executed`. |
| `0xdb2c20c8` | `executeMessage(bytes, (bytes,address,uint64,bytes32), bytes[], address[], uint256[])` | `payable`. Message-only from non-EVM (RouteInfo2). |
| `0x82980dc4` / `0xdfa2dbaf` / `0xd8257d17` / `0x95b12c27` / `0xc66a9c5a` | `liquidityBridge()` / `pegBridge()` / `pegVault()` / `pegBridgeV2()` / `pegVaultV2()` → `address` | Wiring getters (verified live, §Verification). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (cBridge pool) | `0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820` | Liquidity-pool bridge. Immutable singleton (20,574 B). `owner()` = `0xf380166f…6575`. |
| **MessageBus** (proxy) | `0x4066d196a423b2b3b8b054f4f40efb47a74e200c` | Celer IM. Transparent proxy → impl `0x479ec366ae4ec016ce25b918bdea8f78d4fa5dd8`, ProxyAdmin `0x520d812604e7b2ce71819fdbfe9ac40e56327f8f`. |

`MessageBus` wiring (read live on ETH): `liquidityBridge` → `0x5427…1820` (Bridge), `pegBridge` → `0x16365b45…95eB` (PeggedTokenBridge), `pegVault` → `0xB37D31b2…8595` (OriginalTokenVault), `pegBridgeV2` → `0x52E4f244…E084` (PeggedTokenBridgeV2), `pegVaultV2` → `0x7510792A…bAE1` (OriginalTokenVaultV2). Those five pegged addresses are documented in [pegged.md](./pegged.md).

## 4. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0xdd90E5E87A2081Dcf0391920868eBc2FFB81a1aF` (immutable singleton, 20,574 B — identical bytecode size to ETH) |
| **MessageBus** (proxy) | `0x95714818fdd7a5454f73da9c777b3ee6ebaeea6b` → impl `0x186ad38ae889b477d34a7cdcf630f89a8f38682f`, ProxyAdmin `0x5e8e7d39089e937b708065f9cd99409048631b23` |

## 5. Addresses — Avalanche C-Chain (chain ID 43114)

Verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0xef3c714c9425a8F3697A9C969Dc1af30ba82e5d4` (immutable singleton, 20,574 B) |
| **MessageBus** (proxy) | `0x5a926eeeafc4d217add17e9641e8ce23cd01ad57` → impl `0x26c76f7fef00e02a5dd4b5cc8a0f717eb61e1e4b`, ProxyAdmin `0xbade2a874e27b5b0920da93efe6845036c6fb5a4` |

> **Address-collision trap:** the Avalanche `MessageBus` *impl* `0x26c76f7fef00e02a5dd4b5cc8a0f717eb61e1e4b` is the **same literal** as the BNB `PeggedTokenBridgeV2` proxy address. Different contracts on different chains — always key on `(chainId, address)`.

## 6. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x1619DE6B6B20eD217a58d00f37B9d47C7663feca` (immutable singleton, 20,574 B) |
| **MessageBus** (proxy) | `0x3ad9d0648cdaa2426331e894e980d0a5ed16257f` → impl `0xcfb342d6ad6b27ae906212ec1128bab36adb2593`, ProxyAdmin `0xf753e41a28ed77c12bed1498b0b37b62d3682568` |

## 7. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x9D39Fc627A6d9d9F8C831c16995b209548cc3401` (immutable singleton, 20,574 B) |
| **MessageBus** (proxy) | `0x0D71D18126E03646eb09FEc929e2ae87b7CAE69d` → impl `0xf8bfeac18a838ace22110e499922623d54ea26da`, ProxyAdmin `0x3b53d2c7b44d40be05fa5e2309ffeb6eb2492d88` |

## 8. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x88DCDC47D2f83a99CF0000FDF667A468bB958a78` (immutable singleton, 20,574 B). **Note:** this literal is also the Avalanche `PeggedTokenBridge` address — `(chainId,addr)` keying required. |
| **MessageBus** (proxy) | `0xaFDb9C40C7144022811F034EE07Ce2E110093fe6` → impl `0x643017bf85ef399dd76aa8a46ed3c6e22a68d393`, ProxyAdmin `0x1cad030fe10152be0ed6e3921113473a6a0fa178` |

## 9. Addresses — Base (chain ID 8453)

Verified via `eth_getCode` on `https://base-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x7d43AABC515C356145049227CeE54B608342c0ad` (immutable singleton, 20,954 B; explorer label "Celer Network: cBridge"). `owner()` = `0xf380166f…6575`. |
| **MessageBus** | **NOT DEPLOYED.** No Celer IM `MessageBus` on Base. |

> **Base has the pool Bridge ONLY.** Bytecode scan of the Base `0x7d43…` contract confirms `send`/`relay`/`addLiquidity`/`transfers`/`withdraws` are **present** but `sendMessage`/`sendMessageWithTransfer`/`calcFee`/`executeMessage` (MessageBus) and `mint`/`deposit` (pegged) are **all absent**. Some third-party docs/search results conflate the Base cBridge address with a "Base MessageBus" — that is wrong: there is no MessageBus, no pegged bridge, and no vault on Base.

---

## 10. Cross-chain summary

| Chain | ID | Bridge (cBridge pool) | MessageBus (IM) |
|---|---|---|---|
| **Ethereum** | 1 | `0x5427FEFA…1820` | `0x4066d196…200c` (proxy) |
| **BNB** | 56 | `0xdd90E5E8…a1aF` | `0x95714818…ea6b` (proxy) |
| **Avalanche** | 43114 | `0xef3c714c…e5d4` | `0x5a926eee…ad57` (proxy) |
| **Arbitrum** | 42161 | `0x1619DE6B…feca` | `0x3ad9d064…257f` (proxy) |
| **Optimism** | 10 | `0x9D39Fc62…3401` | `0x0D71D181…E69d` (proxy) |
| **Polygon** | 137 | `0x88DCDC47…8a78` | `0xaFDb9C40…3fe6` (proxy) |
| **Base** | 8453 | `0x7d43AABC…c0ad` | — **none** |

**Vanity / collision tells:** No shared CREATE2 vanity address — every chain's Bridge is a different literal. But several **literals are reused across chains for *different* contracts**: Polygon `Bridge` = Avalanche `PeggedTokenBridge` (`0x88DCDC47…`); Avalanche `MessageBus` impl = BNB `PeggedTokenBridgeV2` (`0x26c76f7f…`); the Ethereum `Bridge` literal `0x5427…1820` is reused on Avalanche as the `OriginalTokenVault` v1 (the Avalanche `Bridge` itself is the different literal `0xef3c714c…e5d4`). Always key on `(chainId, address)`.

The pool `Bridge` bytecode is **byte-identical (20,574 B) on all six non-Base chains** and slightly larger on Base (20,954 B) — a tell that all non-Base deployments were cut from one build.

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Bridge** | **Immutable, no proxy** | EIP-1967 impl slot `0x3608…2bbc` = `0x0` AND admin slot `0xb531…6103` = `0x0` (confirmed empty on ETH). 20,574 B full contract. | none — code is fixed; `owner()` only governs params (signers, caps, pause). |
| **MessageBus** | **Transparent proxy (EIP-1967)** | Small proxy bytecode (1,554 B ETH / 2,304 B others); impl slot populated; **admin slot populated** (ProxyAdmin per chain). | per-chain `ProxyAdmin` (the admin-slot address). |

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. Beacon slot (unused here) `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50`.

**Live `MessageBus` impl / admin (read 2026-06-09):**

| Chain | MessageBus proxy | impl | ProxyAdmin (admin slot) |
|---|---|---|---|
| Ethereum | `0x4066d196…200c` | `0x479ec366ae4ec016ce25b918bdea8f78d4fa5dd8` | `0x520d812604e7b2ce71819fdbfe9ac40e56327f8f` |
| BNB | `0x95714818…ea6b` | `0x186ad38ae889b477d34a7cdcf630f89a8f38682f` | `0x5e8e7d39089e937b708065f9cd99409048631b23` |
| Avalanche | `0x5a926eee…ad57` | `0x26c76f7fef00e02a5dd4b5cc8a0f717eb61e1e4b` | `0xbade2a874e27b5b0920da93efe6845036c6fb5a4` |
| Arbitrum | `0x3ad9d064…257f` | `0xcfb342d6ad6b27ae906212ec1128bab36adb2593` | `0xf753e41a28ed77c12bed1498b0b37b62d3682568` |
| Optimism | `0x0D71D181…E69d` | `0xf8bfeac18a838ace22110e499922623d54ea26da` | `0x3b53d2c7b44d40be05fa5e2309ffeb6eb2492d88` |
| Polygon | `0xaFDb9C40…3fe6` | `0x643017bf85ef399dd76aa8a46ed3c6e22a68d393` | `0x1cad030fe10152be0ed6e3921113473a6a0fa178` |

**The `Bridge` is NOT a proxy** (confirmed: both EIP-1967 slots read `0x0` on Ethereum; `eth_getCode` returns a full 20 KB runtime, not a delegating stub). There is **no `Upgraded(address)` event to watch on `Bridge`** — code never changes. For `MessageBus`, watch the standard EIP-1967 `Upgraded(address)` topic0 `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on the proxy address.

---

## 12. Detection invariants & gotchas

1. **`Send` (source) and `Relay` (destination) are on DIFFERENT chains and never appear in the same tx.** A user's bridge = a `Send` on chain A + a `Relay` on chain B. Correlate by `transferId`: chain A's `Send.transferId = keccak256(sender, receiver, token, amount, dstChainId, nonce, uint64(srcChainId))`; chain B's `Relay` carries that same value plus `srcTransferId`. **Do not expect a matching `Relay` on the same chain as the `Send`.**
2. **None of `Send`'s 8 params are `indexed`** (verified by decoding a live log — `transferId/sender/receiver/token/amount/dstChainId/nonce/maxSlippage` are all in `data`, topics length = 1). You cannot pre-filter a `Send` by token or receiver via topic filters; filter by `(address, topic0)` then ABI-decode `data`. Same for `Relay`, `LiquidityAdded`, `WithdrawDone`.
3. **`tx.to` ≠ `Bridge` for relays.** `relay()` is called by SGN relayer EOAs/contracts; attribute the payout to `Relay.receiver`, not the transaction sender.
4. **The `Bridge` is immutable** — no `Upgraded` event, code never rotates. Only `MessageBus` is upgradeable (Transparent proxy) — watch `Upgraded(address)` `0xbc7cd75a…` on the six MessageBus proxies (none on Base).
5. **`maxSend(token) == 0` means "no maximum"**, not "zero allowed" (see `_send`: `require(maxSend==0 || amount<=maxSend)`). `minSend` is a strict `>` lower bound.
6. **`maxSlippage` is slippage × 1e6** (e.g. 5000 = 0.5%). Must exceed `minimalMaxSlippage()`.
7. **`relay` enforces volume caps + a delay queue.** Large transfers above `delayThresholds[token]` do NOT pay out immediately — they emit `DelayedTransferAdded(id)` and only later `DelayedTransferExecuted(id, receiver, token, amount)`. A monitor expecting an immediate `Relay` payout will miss delayed ones. `EpochVolumeUpdated` tracks the per-epoch volume against the cap.
8. **`Bridge.withdraw` and `OriginalTokenVault.withdraw` share selector `0xa21a9280`.** Same 4-arg `(bytes,bytes[],address[],uint256[])` shape; disambiguate by the called contract.
9. **Safeguard-mixin events (`Paused`, `SignersUpdated`, `DelayedTransfer*`, `EpochVolumeUpdated`, `OwnershipTransferred`) are emitted by BOTH `Bridge` and the pegged contracts** (they share the mixins). Always attribute by emitter address.
10. **`MessageBus.Executed` carries `srcChainId` and `srcTxHash`** — that is how an off-chain indexer co-verifies the source send happened. `status` (uint8): `1=Success, 2=Fail, 3=Fallback`. A `NeedRetry` (not `Executed`) means the app returned `Retry` and the message can be re-executed (the executedMessages map was reset to `Null`).
11. **Base has the pool Bridge only** — no `MessageBus`, no pegged bridge, no vault (bytecode-confirmed). Do not index those contracts on Base.
12. **Fee-on-transfer / rebasing tokens are unsupported** by `send`/`addLiquidity` (the contract NatSpec says so and accounting assumes 1:1 `transferFrom`). Such tokens, if listed, will mis-account.
13. **`dstChainId`/`srcChainId` use `uint64(block.chainid)`** internally — they are Celer's own uint64 chain IDs which match EVM chain IDs for these seven chains, but for non-EVM counterparties (Aptos, Sui, etc.) Celer assigns its own IDs. Don't assume `dstChainId` is an EVM chainId for non-EVM routes.
14. **Counterparty chains extend well beyond these seven.** cBridge/MessageBus also live on Linea (MessageBus `0x6F2bD3De…`), Polygon zkEVM (`0x9Bb46D51…`), zkSync Era (`0x9a98a376…`), and many others — a `Send` with `dstChainId` outside {1,56,137,43114,42161,10,8453} is a valid bridge to an out-of-scope chain, not an error.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- Bridge / Pool
TOPIC_SEND                    = '\x89d8051e597ab4178a863a5190407b98abfeff406aa8db90c59af76612e58f01'
TOPIC_RELAY                   = '\x79fa08de5149d912dce8e5e8da7a7c17ccdf23dd5d3bfe196802e6eb86347c7c'
TOPIC_LIQUIDITY_ADDED         = '\xd5d28426c3248963b1719df49aa4c665120372e02c8249bbea03d019c39ce764'
TOPIC_WITHDRAW_DONE           = '\x48a1ab26f3aa7b62bb6b6e8eed182f292b84eb7b006c0254386b268af20774be'
TOPIC_MIN_SEND_UPDATED        = '\x8b59d386e660418a48d742213ad5ce7c4dd51ae81f30e4e2c387f17d907010c9'
TOPIC_MAX_SEND_UPDATED        = '\x4f12d1a5bfb3ccd3719255d4d299d808d50cdca9a0a5c2b3a5aaa7edde73052c'
TOPIC_MIN_ADD_UPDATED         = '\xc56b0d14c4940515800d94ebbd0f3f5d8cc58ba1109c12536bd993b72e466e4f'
-- Safeguard mixins (Bridge + pegged contracts)
TOPIC_SIGNERS_UPDATED         = '\xf126123539a68393c55697f617e7d1148e371988daed246c2f41da99965a23f8'
TOPIC_RESET_NOTIFICATION      = '\x68e825132f7d4bc837dea2d64ac9fc19912bf0224b67f9317d8f1a917f5304a1'
TOPIC_PAUSED                  = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_DELAYED_ADDED           = '\xcbcfffe5102114216a85d3aceb14ad4b81a3935b1b5c468fadf3889eb9c5dce6'
TOPIC_DELAYED_EXECUTED        = '\x3b40e5089937425d14cdd96947e5661868357e224af59bd8b24a4b8a330d4426'
TOPIC_EPOCH_VOLUME_UPDATED    = '\x608e49c22994f20b5d3496dca088b88dfd81b4a3e8cc3809ea1e10a320107e89'
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- MessageBus
TOPIC_MESSAGE                 = '\xce3972bfffe49d317e1d128047a97a3d86b25c94f6f04409f988ef854d25e0e4'
TOPIC_MESSAGE2                = '\xe66fbe37d84ca73c589f782ac278844918ea6c56a4917f58707f715588080df2'
TOPIC_MESSAGE_WITH_TRANSFER   = '\x172762498a59a3bc4fed3f2b63f94f17ea0193cffdc304fe7d3eaf4d342d2f66'
TOPIC_EXECUTED                = '\xa635eb05143f74743822bbd96428928de4c8ee8cc578299749be9425c17bb34d'
TOPIC_NEED_RETRY              = '\xe49c2c954d381d1448cf824743aeff9da7a1d82078a7c9e5817269cc359bd26c'
TOPIC_CALL_REVERTED           = '\xffdd6142bbb721f3400e3908b04b86f60649b2e4d191e3f4c50c32c3e6471d2f'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
-- Bridge / Pool
SEL_SEND                      = '\xa5977fbb'
SEL_SEND_NATIVE               = '\x3f2e5fc3'
SEL_RELAY                     = '\xcdd1b25d'
SEL_ADD_LIQUIDITY             = '\x56688700'
SEL_ADD_NATIVE_LIQUIDITY      = '\x7044c89e'
SEL_WITHDRAW                  = '\xa21a9280'   -- also OriginalTokenVault.withdraw
SEL_TRANSFERS                 = '\x3c64f04b'
SEL_WITHDRAWS                 = '\xe09ab428'
SEL_MIN_SEND                  = '\xf8b30d7d'
SEL_MAX_SEND                  = '\x618ee055'
SEL_MINIMAL_MAX_SLIPPAGE      = '\x2fd1b0a4'
SEL_VERIFY_SIGS               = '\x682dbc22'
SEL_UPDATE_SIGNERS            = '\xfbd51ae6'
-- MessageBus
SEL_SEND_MESSAGE              = '\x9f3ce55a'
SEL_SEND_MESSAGE_BYTES        = '\x7d7a101d'
SEL_SEND_MESSAGE_WITH_XFER    = '\x4289fbb3'
SEL_CALC_FEE                  = '\x5335dca2'
SEL_EXEC_MSG_WITH_XFER        = '\x3f395aff'
SEL_EXEC_MSG_WITH_XFER_REFUND = '\x7b80ab20'
SEL_EXEC_MSG_ROUTEINFO        = '\x468a2d04'
SEL_EXEC_MSG_ROUTEINFO2       = '\xdb2c20c8'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Bridge addresses (cBridge pool — immutable) =====
ETH_BRIDGE                    = '\x5427fefa711eff984124bfbb1ab6fbf5e3da1820'
BNB_BRIDGE                    = '\xdd90e5e87a2081dcf0391920868ebc2ffb81a1af'
AVAX_BRIDGE                   = '\xef3c714c9425a8f3697a9c969dc1af30ba82e5d4'
ARB_BRIDGE                    = '\x1619de6b6b20ed217a58d00f37b9d47c7663feca'
OP_BRIDGE                     = '\x9d39fc627a6d9d9f8c831c16995b209548cc3401'
POLY_BRIDGE                   = '\x88dcdc47d2f83a99cf0000fdf667a468bb958a78'
BASE_BRIDGE                   = '\x7d43aabc515c356145049227cee54b608342c0ad'

-- ===== MessageBus addresses (proxy; NONE on Base) =====
ETH_MESSAGEBUS                = '\x4066d196a423b2b3b8b054f4f40efb47a74e200c'
BNB_MESSAGEBUS                = '\x95714818fdd7a5454f73da9c777b3ee6ebaeea6b'
AVAX_MESSAGEBUS               = '\x5a926eeeafc4d217add17e9641e8ce23cd01ad57'
ARB_MESSAGEBUS                = '\x3ad9d0648cdaa2426331e894e980d0a5ed16257f'
OP_MESSAGEBUS                 = '\x0d71d18126e03646eb09fec929e2ae87b7cae69d'
POLY_MESSAGEBUS               = '\xafdb9c40c7144022811f034ee07ce2e110093fe6'

-- ===== Governance =====
BRIDGE_OWNER_ETH_BASE         = '\xf380166f8490f24af32bf47d1aa217fba62b6575'
```

---

## 14. Verification & sources

How constants were verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` (`[0:4]` for selectors) with no param names / `uint`→`uint256` / enums (`MsgType`, `TxStatus`, `TransferType`) → `uint8` / tuples as `(type,…)`, from the exact event/function declarations in `celer-network/sgn-v2-contracts` (`liquidity-bridge/Bridge.sol`, `liquidity-bridge/Pool.sol`, `message/messagebus/MessageBusSender.sol`, `MessageBusReceiver.sol`, `message/libraries/MsgDataTypes.sol`).
- **Live cross-check (eth_getLogs, Ethereum):** `Send` topic0 `0x89d8051e…` returned 145 logs and `Relay` `0x79fa08de…` returned 9 logs on Bridge `0x5427…1820` in a ~9k-block window (latest ≈ block 25,279,436); a sampled `Send` (tx `0x889f8c54…`) decoded cleanly with all 8 params in `data` (topics length 1), token = USDT, `dstChainId = 0x38 = 56` (BNB) — confirming field order and the non-indexed layout. `OriginalTokenVault.Deposited` `0x15d2eeef…` returned 10 logs on `0xB37D…8595`.
- **Addresses:** taken from the official cBridge contract-addresses doc and the cBridge config API (`getTransferConfigsForAll` `contract_addr` matches the pool Bridge per chain), then existence-checked via `eth_getCode` on each chain's publicnode RPC. The pool `Bridge` is 20,574 B on all six non-Base chains and 20,954 B on Base. `MessageBus` impl/admin read live from the EIP-1967 slots. **Base has no MessageBus** — confirmed by scanning the Base `0x7d43…` runtime: `send`/`relay`/`addLiquidity`/`transfers`/`withdraws` present, `sendMessage`/`calcFee`/`executeMessage`/`mint`/`deposit` absent.
- **Wiring:** `MessageBus` (ETH) `liquidityBridge()/pegBridge()/pegVault()/pegBridgeV2()/pegVaultV2()` read live and resolve to the Bridge + the four pegged contracts in pegged.md.
- **Proxy classification:** `Bridge` EIP-1967 impl AND admin slots both read `0x0` on Ethereum (immutable, non-proxy); `MessageBus` impl + admin slots populated on all six chains (Transparent proxy).

**Authoritative sources:**
- Canonical contracts: [`celer-network/sgn-v2-contracts`](https://github.com/celer-network/sgn-v2-contracts) (`contracts/liquidity-bridge/`, `contracts/message/messagebus/`).
- cBridge addresses: [cBridge docs — Contract Addresses](https://cbridge-docs.celer.network/reference/contract-addresses).
- Celer IM (MessageBus) addresses: [im-docs — Contract Addresses & RPC Info](https://im-docs.celer.network/developer/contract-addresses-and-rpc-info).
- Config API: `https://cbridge-prod2.celer.app/v1/getTransferConfigsForAll`.
- Explorers: [Etherscan Bridge](https://etherscan.io/address/0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820) · [BaseScan cBridge](https://basescan.org/address/0x7d43AABC515C356145049227CeE54B608342c0ad).
