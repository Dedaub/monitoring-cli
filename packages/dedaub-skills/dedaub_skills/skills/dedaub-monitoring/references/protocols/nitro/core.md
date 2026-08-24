# Router Nitro AssetForwarder — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism; Polygon = Gateway only)

**Status:** verified against live RPC on all seven requested chains and the canonical `router-protocol/router-contracts` repo (`asset-forwarder/evm/contracts/AssetForwarder.sol`) on 2026-06-09. Event topic0s additionally cross-checked against the official `@routerprotocol/asset-transfer-sdk-ts` (v0.5.0) hardcoded constants and the on-chain-verified contract name ("AssetForwarder") read from Snowscan/Routescan.
**Scope:** the **AssetForwarder** — Router Nitro's EVM liquidity-bridge entrypoint that emits `FundsDeposited` on the source chain and `FundsPaid` on the destination chain. Topics/selectors are **chain-agnostic**; addresses are network-specific. The companion Router **Gateway** (Router Chain messaging) and the older **AssetBridge / Voyager** mint-burn token bridge are documented in [gateway.md](./gateway.md).

Router Nitro is an intent-style cross-chain bridge: a user calls `iDeposit`/`iDepositMessage` on the source-chain AssetForwarder (escrowing the source token), off-chain **forwarders** front the destination token to the recipient by calling `iRelay`/`iRelayMessage` on the destination AssetForwarder, and **orchestrators** settle the forwarder out of the escrow via the Router Chain. **There is no lock-mint here — the AssetForwarder holds liquidity / pulls from forwarders; settlement and refunds are driven by the Router Chain via the Gateway's `iReceive`.** The contract is **non-upgradeable** on the chains where it acts as the forwarder (plain `AccessControl` + `ReentrancyGuard`, no proxy) — a repo `AssetForwarderUpgradeable` (UUPS) variant exists but is **not** the deployed forwarder on any of the seven target chains.

> **Address-collision trap (verified 2026-06-09, the single most important fact in this file).** Router reused two vanity-ish addresses with **opposite roles per chain**:
> - **`0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9`** is the **AssetForwarder** on **Ethereum / Base / BNB / Optimism** (direct deploy, `depositNonce()` answers), but on **Avalanche / Arbitrum** the *same address* is the **Gateway proxy**, and on **Polygon** it is the **Gateway logic** contract. On Avax/Arb/Polygon `depositNonce()` **reverts** there.
> - **`0x21c1E74CAaDf990E237920d5515955a024031109`** is an **(earlier-generation) AssetForwarder** on **Base / BNB / Avalanche / Arbitrum / Optimism** (`depositNonce()` answers), absent on Ethereum (`0x`), and on **Polygon** the same address is the **Gateway proxy** (`currentVersion()=1`).
>
> **Always key on `(chainId, address, role)` and confirm role by calling `depositNonce()` (AssetForwarder) vs `currentVersion()` (Gateway) — never assume an address has the same role on another chain.** See §3 / §N.

> **Two AssetForwarder generations coexist (verified).** `0xC21e4ebD…` (the newer forwarder, ETH/Base/BNB/OP) and `0x21c1E74C…` (the older forwarder, Base/BNB/Avax/Arb/OP) are **both** live "AssetForwarder" contracts (35.5 KB / 33.6–34.5 KB bytecode, same event ABI). Base/BNB/Optimism run **both** at once. Watch **both** addresses on those chains.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | On-chain verified name |
|----------|------|--------|------------------------|
| **AssetForwarder** (`0xC21e4ebD…`) | Newer Nitro forwarder: `iDeposit`/`iRelay` + message variants + `iReceive` refund hook. | **No** (direct deploy, EIP-1967 impl slot empty) | `AssetForwarder` |
| **AssetForwarder** (`0x21c1E74C…`) | Earlier Nitro forwarder, same event signatures. Co-deployed on Base/BNB/Avax/Arb/OP. | **No** (direct deploy) | `AssetForwarder` |
| **Gateway** (`0x86dfc31d…` / `0xC21e4ebD…` on Avax/Arb) | Router Chain messaging endpoint the forwarder's `iReceive` is gated to. Documented in [gateway.md](./gateway.md). | EIP-1967 / direct (chain-dependent) | `GatewayUpgradeable` |
| **AssetBridge / Voyager** (`0xf0773508…`) | Older mint-burn token bridge (`transferToken`/`Execute`). Documented in [gateway.md](./gateway.md). ETH/Avax/Arb only. | direct | `AssetBridge` |

The two AssetForwarder generations share an identical event/function ABI (the signatures below apply to both). Distinguish them only by address. `AssetForwarderBlastUpgradeable` / `AssetForwarderUpgradeable` exist in the repo for Blast / UUPS deployments but are **not** present at the seven target chains' forwarder addresses.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak256 on 2026-06-09. `FundsDeposited` (`0x6f223106…`) and `FundsDepositedWithMessage` (`0x3dbc28a2…`) additionally match the official asset-transfer SDK's hardcoded `DEPOSIT` topic constants byte-for-byte.

### 1.1 AssetForwarder (both generations — identical signatures)

| topic0 | Event |
|--------|-------|
| `0x6f223106c8e3df857d691613d18d1478cc7c629a1fdf16c7b461d36729fcc7ad` | `FundsDeposited(uint256 partnerId, uint256 amount, bytes32 destChainIdBytes, uint256 destAmount, uint256 depositId, address srcToken, address depositor, bytes recipient, bytes destToken)` |
| `0x3dbc28a2fa93575c89d951d683c45ddb951a2ecf6bc9b9704a61589fa0fcb70f` | `FundsDepositedWithMessage(uint256 partnerId, uint256 amount, bytes32 destChainIdBytes, uint256 destAmount, uint256 depositId, address srcToken, bytes recipient, address depositor, bytes destToken, bytes message)` |
| `0x0f3ca0b27903ec13ef88a7ea8be837cc19b0d7f71a735f2083215739a8004464` | `FundsPaid(bytes32 messageHash, address forwarder, uint256 nonce)` |
| `0x21937deaa62558dad619c8d730a7d1d7ef41731fc194c32973511e1455cb37ad` | `FundsPaidWithMessage(bytes32 messageHash, address forwarder, uint256 nonce, bool execFlag, bytes execData)` |
| `0x86896302632bf6dc8a3ac0ae7ddf17d5a5d5c1ca1aad37b4b920a587c51135b1` | `DepositInfoUpdate(address srcToken, uint256 feeAmount, uint256 depositId, uint256 eventNonce, bool initiatewithdrawal, address depositor)` |
| `0x9593b43c20e09177a4170170ac564123ad8138e040e21eec96d1ae9db9ee5d6d` | `CommunityPaused(address indexed pauser, uint256 stakedAmount)` |
| `0xab40a374bc51de372200a8bc981af8c9ecdc08dfdaef0bb6e09f88f3c616ef3d` | `Paused(address account, uint256 pauseType)` — **NOT** OZ `Paused(address)` |
| `0x3582d1828e26bf56bd801502bc021ac0bc8afb57c826e4986b45593c8fad389c` | `Unpaused(address account, uint256 pauseType)` — **NOT** OZ `Unpaused(address)` |

**Disambiguation notes.**
- `FundsDeposited` ≠ `FundsDepositedWithMessage`: the two structs differ in field *order* (`depositor`/`recipient` swap positions), giving distinct topic0s — pick by the message-or-not variant the integration uses.
- The AssetForwarder's `Paused`/`Unpaused` carry a `uint256 pauseType` (1=deposit, 2=relay, 3=both) and have **different topic0s** from OpenZeppelin's no-arg `Paused(address)` (`0x62e78cea…`) / `Unpaused(address)` (`0x5db9ee0a…`). Don't confuse them.

### 1.2 AccessControl (role admin — same on both generations)

| topic0 | Event |
|--------|-------|
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` |

Role ids: `DEFAULT_ADMIN_ROLE = 0x00…00`; `RESOURCE_SETTER = 0x8b9e7a9f25b0aca3f51c01b8fee30790fb16f4d4deded8385ae6643d054bb078`; `PAUSER = 0x539440820030c4994db4e31b6b800deafd503688728f932addfe7a410515c14c` (keccak of the role strings).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All verified **present** in the live `0xC21e4ebD…` AssetForwarder bytecode on Ethereum via PUSH4 scan (`iDeposit`/`iDepositMessage`/`iDepositInfoUpdate`/`iRelay`/`iRelayMessage`/`iReceive(3-arg)`/`depositNonce`/`gatewayContract`/`communityPause` all present; `rescue` and the 4-arg `iReceive` are **absent** in this version — see notes).

### 2.1 AssetForwarder — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf452ed4d` | `iDeposit((uint256,uint256,uint256,address,address,bytes32) depositData, bytes destToken, bytes recipient)` | **Source-chain deposit.** Emits `FundsDeposited`. Tuple = `DepositData(partnerId, amount, destAmount, srcToken, refundRecipient, destChainIdBytes)`. `payable` (native via `0xEeee…EEeE` sentinel). |
| `0x0421caf0` | `iDepositMessage((uint256,uint256,uint256,address,address,bytes32) depositData, bytes destToken, bytes recipient, bytes message)` | Deposit + arbitrary instruction. Emits `FundsDepositedWithMessage`. |
| `0xad7c17ee` | `iDepositInfoUpdate(address srcToken, uint256 feeAmount, uint256 depositId, bool initiatewithdrawal)` | Top up fee / initiate withdrawal/refund for an existing deposit. Emits `DepositInfoUpdate`. |
| `0x64778c1f` | `iRelay((uint256,bytes32,uint256,address,address) relayData)` | **Destination-chain settlement by a forwarder.** Pulls/sends `destToken` to `recipient`, records `executeRecord[messageHash]`, emits `FundsPaid`. Tuple = `RelayData(amount, srcChainId, depositId, destToken, recipient)`. |
| `0x6fb003da` | `iRelayMessage((uint256,bytes32,uint256,address,address,bytes) relayData)` | Settlement + `IMessageHandler.handleMessage` call on the recipient. Emits `FundsPaidWithMessage`. |
| `0x1aa6485a` | `iReceive(string requestSender, bytes packet, string)` | **Gateway-only refund hook** (`msg.sender == gatewayContract`, `keccak(requestSender)==routerMiddlewareBase`). Decodes `(recipient, address[] tokens, uint256[] amounts)` and disburses refunds. **No event.** |
| `0xddeb5094` | `pause(bool depositPause, bool relayPause)` | PAUSER. Emits `Paused`. |
| `0x7d0da562` | `unpause(bool depositUnpause, bool relayUnpause)` | PAUSER. Emits `Unpaused`. |
| `0x6696821b` | `communityPause()` | `payable` — stake-gated emergency deposit+relay pause. Emits `CommunityPaused`. |
| `0xf627df94` | `toggleCommunityPause()` | DEFAULT_ADMIN. |
| `0x8a27fecb` | `withdrawStakeAmount()` | DEFAULT_ADMIN — recover community-pause stake. |
| `0x5ac62700` | `update(uint256 index, address gateway, bytes routerMiddlewareBase, uint256 minStake, uint256 maxStake)` | RESOURCE_SETTER — index 1 sets gateway, 2 sets middleware base, 3 sets stake bounds. |

> The repo also defines `iReceive(string,bytes,string,bytes)` (`0xfea665fd`) and `rescue(address,uint256)` (`0x7a4e4ecf`); both are **absent** from the live `0xC21e4ebD…` Ethereum bytecode (this deployment predates them). The active refund hook is the **3-arg** `iReceive` (`0x1aa6485a`).

### 2.2 AssetForwarder — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xde35f5cb` | `depositNonce()` | `uint256` — monotonically-increasing per-chain deposit counter (also the `depositId`/`nonce` in events). **Use as the role probe: answers on a forwarder, reverts on a Gateway.** |
| `0xeb0cde1d` | `gatewayContract()` | `address` — the Router Gateway this forwarder trusts for `iReceive`. (Older `0x21c1` deploys on Base/BNB/OP don't expose this getter though `depositNonce` works.) |
| `0xc44e947e` | `routerMiddlewareBase()` | `bytes32` — keccak of the trusted Router middleware bech32 address. |
| `0xfd5ad37c` | `executeRecord(bytes32)` | `bool` — replay guard; `true` once a `messageHash` has been relayed. |
| `0x539440820030…` (role const) | `RESOURCE_SETTER()` / `PAUSER()` | `bytes32` role ids. |

### 2.3 Destination message-handler interface (recipient-side, not on the forwarder)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd00a2d5f` | `handleMessage(address tokenSent, uint256 amount, bytes message)` | `IMessageHandler` — what `iRelayMessage` calls on a contract recipient. Implemented by integrator dApps, not by the forwarder. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **AssetForwarder** (current) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | Nitro forwarder. 35,506-char bytecode, direct (impl slot empty). `depositNonce()` = 63734, `gatewayContract()` = `0x86dfc31d…`. |
| Gateway (proxy) | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | Router Chain messaging — see [gateway.md](./gateway.md). |
| AssetBridge / Voyager | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | Older mint-burn token bridge — see [gateway.md](./gateway.md). |
| Native sentinel | `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` | Pass as `srcToken`/`destToken` to move native ETH (not a contract). |

**The earlier-generation forwarder `0x21c1E74C…` is NOT on Ethereum** (`eth_getCode` = `0x`).

## 4. Addresses — Base (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com` on 2026-06-09. **Both forwarder generations are live here.**

| Role | Address | One-liner |
|------|---------|-----------|
| **AssetForwarder** (current) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | Direct deploy. `depositNonce()` = 6, `gatewayContract()` = `0x86dfc31d…`. |
| **AssetForwarder** (earlier) | `0x21c1E74CAaDf990E237920d5515955a024031109` | Direct deploy. `depositNonce()` = 2062 (higher historical use than the "current" addr). `gatewayContract()` reverts (older ABI). |
| Gateway (proxy) | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | impl `0xac589f48…` — see [gateway.md](./gateway.md). |

AssetBridge `0xf0773508…` **not deployed on Base** (`0x`).

## 5. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com` on 2026-06-09. **Both forwarder generations live.**

| Role | Address | One-liner |
|------|---------|-----------|
| **AssetForwarder** (current) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | Direct deploy. `depositNonce()` = 27. |
| **AssetForwarder** (earlier) | `0x21c1E74CAaDf990E237920d5515955a024031109` | Direct deploy. `depositNonce()` = 8877. |
| Gateway (proxy) | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | impl `0xac589f48…`. |

AssetBridge `0xf0773508…` **not on BNB** (`0x`).

## 6. Addresses — Avalanche C-Chain (chain ID 43114)

Verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com` on 2026-06-09. **Role-flip chain.**

| Role | Address | One-liner |
|------|---------|-----------|
| **AssetForwarder** (earlier) | `0x21c1E74CAaDf990E237920d5515955a024031109` | The forwarder here. `depositNonce()` = 17, `gatewayContract()` = `0xC21e4ebD…` (the Avax Gateway). On-chain name = `AssetForwarder`. |
| **Gateway** (proxy) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | ⚠️ **Here `0xC21e4ebD…` is the Gateway, not the forwarder.** ERC1967 proxy, impl `0x86dfc31d…`. `depositNonce()` reverts. |
| Gateway impl | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | 41,526-char logic contract (the GatewayUpgradeable impl is deployed *directly* at this address on Avax/Arb). |
| AssetBridge / Voyager | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | `AssetBridge` (verified name). 35,470-char direct deploy. |

**The "current" forwarder `0xC21e4ebD…` is the Gateway on Avalanche, NOT a forwarder.**

## 7. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com` on 2026-06-09. **Identical role layout to Avalanche.**

| Role | Address | One-liner |
|------|---------|-----------|
| **AssetForwarder** (earlier) | `0x21c1E74CAaDf990E237920d5515955a024031109` | The forwarder here. `depositNonce()` = 47, `gatewayContract()` = `0xC21e4ebD…`. |
| **Gateway** (proxy) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | ⚠️ Gateway, not forwarder. ERC1967 proxy → impl `0x86dfc31d…`. |
| Gateway impl | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | 41,526-char direct logic. |
| AssetBridge / Voyager | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | 35,470-char direct deploy. |

## 8. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com` on 2026-06-09. **Both forwarder generations live (same layout as Base/BNB).**

| Role | Address | One-liner |
|------|---------|-----------|
| **AssetForwarder** (current) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | Direct deploy. `depositNonce()` = 30. |
| **AssetForwarder** (earlier) | `0x21c1E74CAaDf990E237920d5515955a024031109` | Direct deploy. `depositNonce()` = 249. |
| Gateway (proxy) | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | impl `0xac589f48…`. |

AssetBridge `0xf0773508…` **not on Optimism** (`0x`).

## 9. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com` on 2026-06-09. **No AssetForwarder found at either of the two known forwarder addresses — both are Gateway-role here.**

| Role | Address | One-liner |
|------|---------|-----------|
| **Gateway** (proxy) | `0x21c1E74CAaDf990E237920d5515955a024031109` | ⚠️ On Polygon this address is the **Gateway** (proxy → impl `0x5b97f51c…`, `currentVersion()` = 1). `depositNonce()` reverts. |
| Gateway logic | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | 41,526-char GatewayUpgradeable logic deployed directly. |
| Gateway impl (behind `0x21c1` proxy) | `0x5b97f51c9f5ca8a6ea5e44570aaa09d17c8ab824` | Implementation read from the EIP-1967 slot of the `0x21c1` proxy. |
| **AssetForwarder** | **NOT LOCATED** | Neither known forwarder address is a forwarder on Polygon. Router Nitro does support Polygon (per official docs/SDK); its Polygon AssetForwarder is a **distinct address served by the pathfinder API** (`https://api-beta.pathfinder.routerprotocol.com`), which was unreachable from the verification host. **Unverified — resolve from the live quote API before indexing Polygon deposits.** |

AssetBridge `0xf0773508…` **not on Polygon** (`0x`).

---

## 10. Cross-chain summary

Presence/role matrix (role read live 2026-06-09). **F** = AssetForwarder, **G** = Gateway, **AB** = AssetBridge, **—** = `eth_getCode` returns `0x`.

| Chain | ID | `0xC21e4ebD…` | `0x21c1E74C…` | `0x86dfc31d…` | `0xf0773508…` |
|-------|----|--------------|--------------|--------------|--------------|
| Ethereum | 1 | **F** (nonce 63734) | — | G (proxy→`ac589f48`) | AB |
| Base | 8453 | **F** (nonce 6) | **F** (nonce 2062) | G (proxy→`ac589f48`) | — |
| BNB | 56 | **F** (nonce 27) | **F** (nonce 8877) | G (proxy→`ac589f48`) | — |
| Avalanche | 43114 | **G** (proxy→`86dfc31d`) | **F** (nonce 17) | G logic (direct) | AB |
| Arbitrum | 42161 | **G** (proxy→`86dfc31d`) | **F** (nonce 47) | G logic (direct) | AB |
| Optimism | 10 | **F** (nonce 30) | **F** (nonce 249) | G (proxy→`ac589f48`) | — |
| Polygon | 137 | **G** logic (direct) | **G** (proxy→`5b97f51c`) | — | — |

**Tells:** the AssetForwarder is a 33.6–35.5 KB direct deploy with a working `depositNonce()`; the Gateway is a ~700-byte EIP-1967 proxy (or a 41,526-char direct logic) with a working `currentVersion()`. There is **no single canonical AssetForwarder address** — the role of each address flips by chain.

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **AssetForwarder** (both gens) | **Not a proxy** (direct deploy) | EIP-1967 impl slot `0x3608…382bbc` = `0x000…0`; 33.6–35.5 KB runtime; `depositNonce()`/`AccessControl` answer directly. Confirmed empty impl slot on every chain where it is the forwarder (ETH/Base/BNB/Avax/Arb/OP). | n/a — immutable. Param changes via `update()` (RESOURCE_SETTER), not code upgrade. |
| Gateway | EIP-1967 (proxy on ETH/Base/BNB/OP/Polygon; direct logic on Avax/Arb) | See [gateway.md](./gateway.md) §Proxies. | DEFAULT_ADMIN (`_authorizeUpgrade`, UUPS). |

EIP-1967 implementation slot read live: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. The AssetForwarder returns `0x000…0` there on every chain (confirming "not a proxy"); **the `AssetForwarderUpgradeable` (UUPS) variant in the repo would expose `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`, but no deployed forwarder on the seven chains is upgradeable, so that topic should not fire for these addresses.**

---

## 12. Detection invariants & gotchas

1. **The same address has opposite roles on different chains.** `0xC21e4ebD…` = AssetForwarder on ETH/Base/BNB/OP but Gateway on Avax/Arb/Polygon; `0x21c1E74C…` = AssetForwarder on Base/BNB/Avax/Arb/OP but Gateway on Polygon and absent on ETH. **Confirm role per chain by calling `depositNonce()` (forwarder) vs `currentVersion()` (gateway) before trusting an address.** (§10)
2. **Two forwarder generations run simultaneously on Base/BNB/Optimism.** Index **both** `0xC21e4ebD…` and `0x21c1E74C…` there — the older addr often carries more historical volume (`depositNonce` 2062/8877/249 vs 6/27/30).
3. **A bridge = `FundsDeposited` on the source chain + `FundsPaid` on the destination chain, on two different forwarders.** They are linked by the `messageHash` (in `FundsPaid`) which the relayer recomputes as `keccak256(abi.encode(amount, srcChainId, depositId, destToken, recipient, address(this)))`. There is no single global id — join source→dest by `(srcChainId, depositId)` and the recomputed hash.
4. **`depositor`/`refundRecipient` ≠ `tx.from`.** `FundsDeposited.depositor` is the refund recipient supplied in `DepositData`, not necessarily the sender (aggregators/adapters like the NitroAdapter `0x4C76B661…` on ETH call `iDeposit` on the user's behalf). Attribute to the event field, not `msg.sender`.
5. **`recipient` and `destToken` are `bytes`, not `address`.** They are ABI-encoded as dynamic `bytes` because the destination may be a non-EVM chain (NEAR, Solana, Tron, Cosmos). Decode per destination-chain address format; don't assume a 20-byte EVM address.
6. **`destChainIdBytes` / `srcChainId` are `bytes32`, not numeric chain ids.** Router encodes chain ids as `bytes32` of the *string* chain id (e.g. for non-EVM chains). Map via the SDK's `CHAIN_ID_BYTES` table; don't `uint256`-cast.
7. **`FundsPaid.forwarder` is the off-chain forwarder that fronted liquidity, NOT the end user.** The user is the `recipient` inside the relay data / the original deposit. `FundsPaid` does **not** carry the recipient — you must join back to the matching `FundsDeposited` by `depositId`+`messageHash`.
8. **`FundsDeposited` vs `FundsDepositedWithMessage` have different field order** (`depositor` and `recipient` swap), hence different topic0s. A monitor must subscribe to both.
9. **Native assets use the `0xEeee…EEeE` sentinel** as `srcToken`/`destToken`; for native the contract checks `msg.value == amount`. Don't expect an ERC-20 `Transfer` for native legs.
10. **`iReceive` (refund/settlement hook) emits no event** and is gated to `msg.sender == gatewayContract` + `keccak(requestSender)==routerMiddlewareBase`. Refunds therefore show only as raw token `Transfer`s out of the forwarder, with no Nitro-specific topic — track them via internal traces or the `DepositInfoUpdate` (`initiatewithdrawal=true`) that precedes a withdrawal.
11. **`Paused(address,uint256)` is Router's own, not OZ's `Paused(address)`** — different topic0 (`0xab40a374…` vs `0x62e78cea…`). The `pauseType` (1/2/3) tells whether deposits, relays, or both are halted. `CommunityPaused` (`0x9593b43c…`) is a separate stake-gated emergency pause anyone can trigger — a high-signal alert.
12. **Polygon's AssetForwarder is not at either known address** (both are Gateway-role there). Resolve the real Polygon forwarder from the live pathfinder quote API before indexing Polygon `FundsDeposited` (§9, §13 unverified).
13. **AssetForwarder is immutable** (no proxy) — no `Upgraded` event to watch for the forwarder itself. Code changes mean a *new address* (as the two generations demonstrate). Watch for new forwarder deployments by the Router deployer, not impl rotations.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_FUNDS_DEPOSITED              = '\x6f223106c8e3df857d691613d18d1478cc7c629a1fdf16c7b461d36729fcc7ad'
TOPIC_FUNDS_DEPOSITED_WITH_MSG     = '\x3dbc28a2fa93575c89d951d683c45ddb951a2ecf6bc9b9704a61589fa0fcb70f'
TOPIC_FUNDS_PAID                   = '\x0f3ca0b27903ec13ef88a7ea8be837cc19b0d7f71a735f2083215739a8004464'
TOPIC_FUNDS_PAID_WITH_MSG          = '\x21937deaa62558dad619c8d730a7d1d7ef41731fc194c32973511e1455cb37ad'
TOPIC_DEPOSIT_INFO_UPDATE          = '\x86896302632bf6dc8a3ac0ae7ddf17d5a5d5c1ca1aad37b4b920a587c51135b1'
TOPIC_COMMUNITY_PAUSED             = '\x9593b43c20e09177a4170170ac564123ad8138e040e21eec96d1ae9db9ee5d6d'
TOPIC_PAUSED                       = '\xab40a374bc51de372200a8bc981af8c9ecdc08dfdaef0bb6e09f88f3c616ef3d'
TOPIC_UNPAUSED                     = '\x3582d1828e26bf56bd801502bc021ac0bc8afb57c826e4986b45593c8fad389c'
TOPIC_ROLE_GRANTED                 = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED                 = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'

-- ===== Selectors =====
SEL_IDEPOSIT                       = '\xf452ed4d'
SEL_IDEPOSIT_MESSAGE               = '\x0421caf0'
SEL_IDEPOSIT_INFO_UPDATE           = '\xad7c17ee'
SEL_IRELAY                         = '\x64778c1f'
SEL_IRELAY_MESSAGE                 = '\x6fb003da'
SEL_IRECEIVE_3ARG                  = '\x1aa6485a'
SEL_PAUSE                          = '\xddeb5094'
SEL_UNPAUSE                        = '\x7d0da562'
SEL_COMMUNITY_PAUSE                = '\x6696821b'
SEL_DEPOSIT_NONCE                  = '\xde35f5cb'   -- role probe: answers on forwarder
SEL_GATEWAY_CONTRACT               = '\xeb0cde1d'
SEL_HANDLE_MESSAGE                 = '\xd00a2d5f'   -- IMessageHandler on recipient

-- ===== Proxy slot (forwarder = empty here) =====
EIP1967_IMPL_SLOT                  = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'

-- ===== AssetForwarder addresses (ROLE FLIPS PER CHAIN — see notes) =====
-- 'current' forwarder generation
ETH_ASSETFORWARDER                 = '\xc21e4ebd1d92036cb467b53fe3258f219d909eb9'   -- ETH/Base/BNB/OP = FORWARDER
BASE_ASSETFORWARDER                = '\xc21e4ebd1d92036cb467b53fe3258f219d909eb9'
BNB_ASSETFORWARDER                 = '\xc21e4ebd1d92036cb467b53fe3258f219d909eb9'
OP_ASSETFORWARDER                  = '\xc21e4ebd1d92036cb467b53fe3258f219d909eb9'
-- 'earlier' forwarder generation
BASE_ASSETFORWARDER_V1             = '\x21c1e74caadf990e237920d5515955a024031109'
BNB_ASSETFORWARDER_V1              = '\x21c1e74caadf990e237920d5515955a024031109'
OP_ASSETFORWARDER_V1               = '\x21c1e74caadf990e237920d5515955a024031109'
AVAX_ASSETFORWARDER                = '\x21c1e74caadf990e237920d5515955a024031109'   -- on Avax/Arb the FORWARDER is 0x21c1
ARB_ASSETFORWARDER                 = '\x21c1e74caadf990e237920d5515955a024031109'
-- POLYGON forwarder: NOT 0xC21e4ebD and NOT 0x21c1E74C (both are Gateway-role on Polygon) — UNVERIFIED, resolve from pathfinder API
```

---

## 14. Verification & sources

How the constants were verified (2026-06-09):
- **Topic0 / selectors** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from the canonical Solidity in `router-protocol/router-contracts` (`AssetForwarder.sol`, `IAssetForwarder.sol`). `FundsDeposited` (`0x6f223106…`) and `FundsDepositedWithMessage` (`0x3dbc28a2…`) cross-checked against the hardcoded topic constants in `@routerprotocol/asset-transfer-sdk-ts` v0.5.0 (`dist/asset-transfer-sdk-ts.cjs.production.min.js`) — exact match. Selector presence verified by PUSH4 scan of the live `0xC21e4ebD…` Ethereum runtime bytecode (`iDeposit`/`iDepositMessage`/`iDepositInfoUpdate`/`iRelay`/`iRelayMessage`/`iReceive`-3arg/`depositNonce`/`gatewayContract`/`communityPause` present; 4-arg `iReceive` and `rescue` absent in this deployment).
- **Addresses** existence-checked via `eth_getCode` on each chain's publicnode RPC; **role** confirmed live by `eth_call depositNonce()` (forwarder) vs `currentVersion()` (gateway), and by `gatewayContract()` cross-pointers. Ethereum AssetForwarder corroborated from the verified `NitroAdapter` (`0x4C76B6618fFBE6ABeE41f7AD56D10f434009D313`) constructor arg `__assetForwarder = 0xC21e4ebD…`. Contract **names** (`AssetForwarder`, `AssetBridge`, `GatewayUpgradeable`) read from the Routescan/Snowscan verified-source `getsourcecode` API on Avalanche (43114).
- **Proxy status** read live from the EIP-1967 impl slot: empty on every forwarder (→ not a proxy); populated on the Gateway proxies (→ EIP-1967), see [gateway.md](./gateway.md).
- **Chain coverage:** all seven target chains probed; the role of each of the two reused addresses recorded per chain (§10). Polygon's distinct AssetForwarder address could not be resolved on-chain (the two known addresses are Gateway-role there) and the pathfinder registry API was unreachable from the host — recorded as **unverified** (§9, §13).

Authoritative sources:
- Canonical contracts: [`router-protocol/router-contracts`](https://github.com/router-protocol/router-contracts) — `asset-forwarder/evm/contracts/AssetForwarder.sol`, `IAssetForwarder.sol`, `IMessageHandler.sol`.
- Official SDK (topic constants + pathfinder endpoints): [`@routerprotocol/asset-transfer-sdk-ts`](https://www.npmjs.com/package/@routerprotocol/asset-transfer-sdk-ts).
- Docs: [Router Nitro — High-level Workflow & Supported Chains](https://docs.routerprotocol.com/develop/asset-transfer-via-nitro/) · [Architecture (Medium)](https://routerprotocol.medium.com/router-nitros-architecture-d5f354bbe43c).
- Explorers: [Etherscan AssetForwarder](https://etherscan.io/address/0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9) · [Snowscan AssetBridge](https://snowscan.xyz/address/0xf0773508c585246bd09bfb401aa18b72685b03f9) · [Etherscan NitroAdapter](https://etherscan.io/address/0x4C76B6618fFBE6ABeE41f7AD56D10f434009D313).
- Live registry (per-chain forwarder addresses, incl. Polygon): pathfinder API `https://api-beta.pathfinder.routerprotocol.com/api`.
