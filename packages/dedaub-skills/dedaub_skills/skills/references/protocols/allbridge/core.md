# Allbridge Core — Topics, Selectors, Addresses (Ethereum, BNB, Polygon, Avalanche, Arbitrum, Optimism, Base)

**Status:** verified against live RPC on all seven chains and the canonical `allbridge-io/allbridge-core-evm-contracts` repo on 2026-06-09. Topic0s/selectors recomputed locally as `keccak256(signature)` and cross-checked against live `eth_getLogs`; addresses parsed from the official Core contracts page (`docs-core.allbridge.io`) and existence-checked via `eth_getCode`.
**Scope:** Allbridge Core — the stablecoin bridge built on a virtual-USD (vUSD) pool model, plus the bundled CCTP / CCTPv2 / OFT bridge adapters that share the same docs page and admin. Topics + selectors are **chain-agnostic**; addresses are **network-specific**. All seven requested chains carry a Core deployment.

Allbridge Core is a **liquidity-pool stablecoin bridge**. A swap-and-bridge transfer routes the source stablecoin into a per-token `Pool`, converting it to an internal accounting unit **vUSD** (`SwappedToVUsd`), emits a `TokensSent` event on the `Bridge`, and ships a 32-byte message hash through a pluggable messaging layer (`Messenger` = Allbridge's own validator protocol, or `WormholeMessenger`). On the destination chain `receiveTokens` validates the message, swaps vUSD back out of the destination `Pool` (`SwappedFromVUsd`), and emits `TokensReceived`. Same-chain swaps between two pools go through `swap` → `Swapped`.

**Every Core contract is immutable — there are NO proxies.** The EIP-1967 implementation slot (`0x360894…382bbc`) reads `0x0` on the `Bridge`, every `Pool`, the `Messenger`, the `GasOracle`, and the CCTP/OFT adapters. Upgrades are done by deploying a new contract and re-pointing references via owner-only setters (`Bridge.addPool`, `Pool.setRouter`, `Messenger.setOtherChainIds`, …). The single protocol admin **`0x01a494079dcb715f622340301463ce50cd69a4d0`** owns the `Bridge` and `Messenger` on **all seven chains** (read from Ownable storage slot 0). Addresses are **NOT** vanity / deterministic — each chain has unrelated addresses (unlike Allbridge Classic, which uses one cross-chain vanity address — see [classic.md](classic.md)).

Three things to internalize before indexing:
1. The user-facing `Bridge` contract is also the `Router` (same address) — `Swapped` (same-chain) and `TokensSent`/`TokensReceived` (cross-chain) all emit from the **one** Bridge address per chain.
2. The CCTP / CCTPv2 / OFT adapters are **separate contracts** with their own `TokensSent` topic0s that **collide by name** with the Bridge's `TokensSent` but have **different signatures and different topic0s** — disambiguate by emitter and topic0 (§1).
3. Most Core volume now flows through Circle CCTP (the v1/v2 adapters), not the original vUSD pool bridge. Both are live; index both.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Source |
|----------|------|--------|--------|
| **Bridge** (= GasUsage + Router + MessengerGateway) | User entrypoint for `swapAndBridge` / `receiveTokens` / same-chain `swap`. Holds the per-token Pool registry and the other-chain bridge registry. | **No** (immutable, 10,784 B) | `Bridge.sol` |
| **Pool** (one per token per chain; = RewardManager + ERC-20 LP) | vUSD AMM for a single stablecoin; LP token; deposit/withdraw liquidity; `swapToVUsd`/`swapFromVUsd` (router-only). | **No** (immutable) | `Pool.sol`, `RewardManager.sol` |
| **Messenger** | Allbridge's own cross-chain messaging protocol (1 primary + N secondary ECDSA validators). | **No** (immutable, 3,977 B) | `Messenger.sol` |
| **WormholeMessenger** | Alternate messaging backend via Wormhole. Selected per-transfer by the `MessengerProtocol` enum. | **No** (immutable) | `WormholeMessenger.sol` |
| **GasOracle** | Stores per-chain native-token USD price + gas price; used to quote the cross-chain messaging fee. | **No** (immutable, 2,330 B) | `GasOracle.sol` |
| **CctpBridge** ("CCTP Interface") | Adapter that bridges native USDC over Circle CCTP **v1** with Allbridge relayer/gas logic. | **No** (immutable, 7,127 B) | `CctpBridge.sol` |
| **CctpV2Bridge** ("CCTP v2 Interface") | Same for Circle CCTP **v2** (fast/finality-threshold transfers). | **No** (immutable, 6,605 B) | `CctpV2Bridge.sol` |
| **OftBridge** ("OFT Interface") | Adapter that bridges LayerZero OFT tokens with Allbridge relayer/gas logic. | **No** (immutable, 11,266 B) | `OftBridge.sol` |

`MessengerProtocol` enum (from `IBridge.sol`): `0=None, 1=Allbridge, 2=Wormhole, 3=CCTP, 4=CCTPv2, 5=LayerZero`. The trailing `uint8 messenger` field of `TokensSent`/`swapAndBridge` is this enum.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Bridge (= Router) — one address per chain (§3)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x9cd6008e8d4ebd34fd9d022278fec7f95d133780ecc1a0dea459fae3e9675390` | `TokensSent(uint256 amount, bytes32 recipient, uint256 destinationChainId, bytes32 receiveToken, uint256 nonce, uint8 messenger)` | Source-chain send. **`amount` is vUSD (3-dec system precision)**, not the raw token. *(verified live on ETH)* |
| `0xe9d840d27ab4032a839c20760fb995af8e3ad1980b9428980ca1c7e072acd87a` | `TokensReceived(uint256 amount, bytes32 recipient, uint256 nonce, uint8 messenger, bytes32 message)` | Destination-chain receive. *(verified live on ETH)* |
| `0x706abb59b8db30e9e92cb7e272fbe6682712ec97e7b117d7ee3389b24bb3de21` | `ReceiveFee(uint256 bridgeTransactionCost, uint256 messageTransactionCost)` | Native-fee accounting on send. *(verified live on ETH)* |
| `0x02a1962fff2ae0f895c1fcd8481ce39cce1e8083e752ce6f5e80d2b5366382c8` | `BridgingFeeFromTokens(uint256 gas)` | Fee paid in tokens (gasless flow). *(verified live on ETH)* |
| `0xe85f63622be58135a84c6e9de632115a3c471b0540a04d37a7c53a0647cd0c39` | `Swapped(address sender, address recipient, bytes32 sendToken, bytes32 receiveToken, uint256 sendAmount, uint256 receiveAmount)` | **Same-chain** pool-to-pool swap (no bridging). |
| `0x88a5966d370b9919b20f3e2c13ff65706f196a4e32cc2c12bf57088f88525874` | `Received(address sender, uint256 amount)` | Native gas received from admin top-up. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` | Ownable. |

### 1.2 Pool (one address per token per chain — §3) + RewardManager + ERC-20

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xa930da1d3f27a25892307dd59cec52dd9b881661a0f20364757f83a0da2f6873` | `SwappedToVUsd(address sender, address token, uint256 amount, uint256 vUsdAmount, uint256 fee)` | Token → vUSD (entry leg). *(verified live on ETH USDC pool)* |
| `0xfc1df7b9ba72a13350b8a4e0f094e232eebded9edd179950e74a852a0f405112` | `SwappedFromVUsd(address recipient, address token, uint256 vUsdAmount, uint256 amount, uint256 fee)` | vUSD → token (exit leg). *(verified live on ARB USDC pool)* |
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed user, uint256 amount)` | LP added. **Same topic0 as ERC-4626/WETH `Deposit(address,uint256)` — filter by pool address.** |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed user, uint256 amount)` | LP removed. |
| `0xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe` | `RewardsClaimed(address indexed user, uint256 amount)` | LP rewards claimed. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` | Pool LP token is an ERC-20 (but internal `_transfer`/`_approve` are disabled — LP is non-transferable). |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` | Ownable. |

### 1.3 Messenger — one address per chain (§3)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x54791b38f3859327992a1ca0590ad3c0f08feba98d1a4f56ab0dca74d203392a` | `MessageSent(bytes32 indexed message)` | Outbound message hash. *(verified live on ETH Messenger 0x203e8785…)* |
| `0xe29dc34207c78fc0f6048a32f159139c33339c6d6df8b07dcd33f6d699ff2327` | `MessageReceived(bytes32 indexed message)` | Inbound message hash accepted by validators. |
| `0x88a5966d370b9919b20f3e2c13ff65706f196a4e32cc2c12bf57088f88525874` | `Received(address, uint256)` | Native gas received. |
| `0x55981f511768d27d1efe9b8e19f36310c3db332ea190227d182d0af4d64c27c4` | `SecondaryValidatorsSet(address[] oldValidators, address[] newValidators)` | **Validator-set rotation — high-value admin signal.** |

### 1.4 WormholeMessenger (alternate backend; deployed where Wormhole routing is enabled)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x3d268d705c99ec99e84748365f374dea1d745080faad9ddfa8c2715d20b50cb0` | `MessageSent(bytes32 indexed message, uint64 sequence)` | **2-arg — distinct topic0 from the Allbridge `Messenger.MessageSent`.** |
| `0x556d717a59d7ef2969f5a9f2c6f9199f9a4e78cb7704aa4162ee70f7d2b771f1` | `MessageReceived(bytes32 indexed message, uint64 sequence)` | |
| `0x88a5966d370b9919b20f3e2c13ff65706f196a4e32cc2c12bf57088f88525874` | `Received(address, uint256)` | |

### 1.5 CctpBridge (CCTP v1 adapter) — one per chain (§3)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xaf142c08d51839efeb25c71c958dec48ffa3a832ba72324fbf8802dea6ec2bd1` | `TokensSent(uint256 amount, address sender, bytes32 recipient, uint256 destinationChainId, uint256 nonce, uint256 receivedRelayerFeeFromGas, uint256 receivedRelayerFeeFromTokens, uint256 relayerFee, uint256 receivedRelayerFeeTokenAmount, uint256 adminFeeTokenAmount)` | **10-arg — different topic0 from Bridge.TokensSent.** *(verified live on ETH CCTP 0xC51397…)* |
| `0x95fcfca390614e1aac005a21c415843c9ec9d9d32ea180cf5c1901422f54a958` | `TokensSentExtras(bytes32 recipientWalletAddress)` | Optional non-EVM recipient hint. *(verified live on ETH)* |
| `0x004e74b82cca19ab607251d92cf8d3147a281463adb41c6dbf2629f396337bca` | `RecipientReplaced(address sender, uint256 nonce, bytes32 newRecipient)` | Sender re-targets an in-flight CCTP transfer. |
| `0xcb213a07f467a18546d6296f2850c3b891d3918fd44a941ca501932229f45fc7` | `ReceivedGas(address sender, uint256 amount)` | |
| `0x0d46b66d2c8a984b124fbfee6aa2c757ca68de14666d1884867bb69cce652acf` | `ReceivedExtraGas(address recipient, uint256 amount)` | Extra destination gas delivered. |

### 1.6 CctpV2Bridge (CCTP v2 adapter) — one per chain (§3)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x2f76d450a444053faafc76ad43e8bac6f5092b83a06461face925b6221d5a226` | `TokensSent(address sender, bytes32 recipient, uint256 amount, uint256 destinationChainId, uint256 receivedRelayerFeeFromGas, uint256 receivedRelayerFeeFromTokens, uint256 relayerFee, uint256 receivedRelayerFeeTokenAmount, uint256 adminFeeTokenAmount, uint256 maxFee)` | **10-arg, different field order — distinct topic0 from both Bridge and CctpBridge `TokensSent`.** No `nonce`/`TokensSentExtras` pair; ends with `maxFee`. |
| `0x95fcfca390614e1aac005a21c415843c9ec9d9d32ea180cf5c1901422f54a958` | `TokensSentExtras(bytes32 recipientWalletAddress)` | Same topic0 as v1. |
| `0x0d605cc2ed964920ed498c9723390d3585b30aa403f7cf5bc0d7c53113d2f57d` | `ReceivedMessageId(bytes32 messageId)` | v2 message-id receipt. |
| `0xcb213a07f467a18546d6296f2850c3b891d3918fd44a941ca501932229f45fc7` | `ReceivedGas(address, uint256)` | |
| `0x0d46b66d2c8a984b124fbfee6aa2c757ca68de14666d1884867bb69cce652acf` | `ReceivedExtraGas(address, uint256)` | |

### 1.7 OftBridge (LayerZero OFT adapter) — ETH + Arbitrum (§3)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xeb30a1ea9476f0902725e947bd1d6d5e9026c15f73aad8515682a61354f05eea` | `OftTokensSent(address sender, bytes32 recipient, address tokenAddress, uint256 amount, uint256 destinationChainId, uint256 receivedRelayerFeeFromGas, uint256 receivedRelayerFeeFromTokens, uint256 relayerFeeWithExtraGas, uint256 receivedRelayerFeeTokenAmount, uint256 adminFeeTokenAmount, uint256 extraGasDestinationToken)` | **Named `OftTokensSent`, not `TokensSent`** — unique topic0. |
| `0xcb213a07f467a18546d6296f2850c3b891d3918fd44a941ca501932229f45fc7` | `ReceivedGas(address, uint256)` | |

> **`TokensSent` topic0 disambiguation (critical):** four contracts emit an event literally named `TokensSent` but with three distinct signatures → three distinct topic0s. Bridge = `0x9cd6008e…`, CctpBridge = `0xaf142c08…`, CctpV2Bridge = `0x2f76d450…`. OftBridge avoids the clash entirely (`OftTokensSent`). Always key on `(topic0, emitter)`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Bridge (= Router)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4cd480bd` | `swapAndBridge(bytes32 token, uint256 amount, bytes32 recipient, uint256 destinationChainId, bytes32 receiveToken, uint256 nonce, uint8 messenger, uint256 feeTokenAmount)` | `payable`. The user entrypoint. Emits `SwappedToVUsd` + `TokensSent` (+ `MessageSent`). |
| `0xe43bfe5e` | `receiveTokens(uint256 amount, bytes32 recipient, uint256 sourceChainId, bytes32 receiveToken, uint256 nonce, uint8 messenger, uint256 receiveAmountMin)` | `payable`. Relayer completes the transfer. Emits `SwappedFromVUsd` + `TokensReceived`. |
| `0x331838b2` | `swap(uint256 amount, bytes32 token, bytes32 receiveToken, address recipient, uint256 receiveAmountMin)` | Same-chain pool swap. Emits `Swapped`. |
| `0x2ed1084b` | `hashMessage(uint256 amount, bytes32 recipient, uint256 sourceChainId, uint256 destinationChainId, bytes32 receiveToken, uint256 nonce, uint8 messenger)` | View — the message preimage hash. |
| `0x7d18330b` | `getBridgingCostInTokens(uint256 destinationChainId, uint8 messenger, address tokenAddress)` | View — fee quote in source tokens. |
| `0x3ee2594e` | `registerBridge(uint256 chainId, bytes32 bridgeAddress)` | owner-only — register a counterparty bridge. |
| `0xc7c56d7e` | `addBridgeToken(uint256 chainId, bytes32 tokenAddress)` | owner-only. |
| `0x1268cee8` | `withdrawGasTokens(uint256 amount)` | owner-only. |
| `0x8da5cb5b` | `owner()` | `= 0x01a494…a4d0` on every chain. |

### 2.2 Pool

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb6b55f25` | `deposit(uint256 amount)` | Add liquidity. Emits `Deposit`. |
| `0x2e1a7d4d` | `withdraw(uint256 amountLp)` | Remove liquidity. Emits `Withdraw`. **Same selector as WETH `withdraw(uint256)`.** |
| `0x28fdb481` | `swapToVUsd(address user, uint256 amount, bool zeroFee)` → `uint256` | **`onlyRouter`** — token → vUSD. Emits `SwappedToVUsd`. |
| `0x2d46f63e` | `swapFromVUsd(address user, uint256 amount, uint256 receiveAmountMin, bool zeroFee)` → `uint256` | **`onlyRouter`** — vUSD → token. Emits `SwappedFromVUsd`. |
| `0x372500ab` | `claimRewards()` | Emits `RewardsClaimed`. |
| `0x98d5fdca` | `getPrice()` → `uint256` | LP virtual price. |
| `0xfc0c546a` | `token()` → `address` | Pool underlying stablecoin (e.g. ETH USDC pool → `0xa0b8…eb48`). |
| `0xc0d78655` | `setRouter(address)` | owner-only — re-point the Router/Bridge. |

### 2.3 Messenger

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe12c9ca8` | `sendMessage(bytes32 message)` | `payable`. Emits `MessageSent`. |
| `0xd8de8503` | `receiveMessage(bytes32 message, uint256 v1v2, bytes32 r1, bytes32 s1, bytes32 r2, bytes32 s2)` | Validator-signed delivery (1 primary + 1 secondary ECDSA sig). Emits `MessageReceived`. |
| `0x1268cee8` | `withdrawGasTokens(uint256)` | owner-only. |
| `0x8da5cb5b` | `owner()` | `= 0x01a494…a4d0`. |

### 2.4 CctpBridge / CctpV2Bridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7dfb08f1` | `bridge(uint256 amount, bytes32 recipient, uint256 destinationChainId, uint256 relayerFeeTokenAmount)` | `payable`. **Identical selector on CctpBridge and CctpV2Bridge** (same signature). Emits the respective `TokensSent`. |
| `0x7d677480` | `bridgeWithWalletAddress(uint256 amount, bytes32 recipient, bytes32 recipientWalletAddress, uint256 destinationChainId, uint256 relayerFeeTokenAmount)` | `payable`. Adds `TokensSentExtras`. |
| `0x1e976500` | `receiveTokens(address recipient, bytes message, bytes signature)` | `payable`. CctpBridge v1 mint side. |
| `0xf3b1f721` | `changeRecipient(uint256 nonce, bytes32 newRecipient)` | v1 — re-target. Emits `RecipientReplaced`. |
| `0xf8754aa7` | `withdrawFeeInTokens()` | owner-only — sweep accrued admin fee in tokens. |
| `0xe99fee3e` | `claimAdminFee()` | owner-only — Pool admin-fee claim (`RewardManager`). |

### 2.5 OftBridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7daca3a4` | `bridge(address tokenAddress, uint256 amount, bytes32 recipient, uint256 destinationChainId, uint256 relayerFeeTokenAmount, uint256 extraGasInDestinationToken, uint256 slippageBP)` | `payable`. Emits `OftTokensSent`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge (Router)** | `0x609c690e8F7D68a59885c9132e812eEbDaAf0c9e` | vUSD swap-and-bridge entrypoint (10,784 B). owner `0x01a494…a4d0`. |
| **Messenger** | `0x203e8785b4d4312c4152d0c42ba3fa8bd79086da` | Allbridge validator messaging (3,977 B). gasOracle `0x0bdf61…96e0`. |
| **GasOracle** | `0x0bdf6139f2841a7856ca154d851182c52f5b96e0` | Native-token-price / gas oracle (2,330 B). |
| **Pool — USDC** | `0xa7062bbA94c91d565Ae33B893Ab5dFAF1Fc57C4d` | `token()` = USDC `0xa0b8…eb48`. |
| **Pool — USDT** | `0x7DBF07Ad92Ed4e26D5511b4F285508eBF174135D` | |
| **Pool — USDe** | `0xCab34D4d532a9c9929f4f96d239653646351abAd` | `token()` = Ethena USDe `0x4c9E…68B3` (13,385 B). **NB: the USDe _token_ is `0x4c9EDD5852cd905f086C759E8383e09bff1E68B3` — do NOT confuse it with the pool; the token has no `token()`/`getPrice()` and is Ethena-owned.** |
| **CctpBridge (CCTP v1)** | `0xC51397b75B783E31469bFaADE79913F3f82210d6` | Native-USDC over Circle CCTP v1 (7,127 B). |
| **CctpV2Bridge (CCTP v2)** | `0x7972d6907739593C00e6284c53C83dB3ECd15c33` | Circle CCTP v2 (6,605 B). |
| **OftBridge (OFT)** | `0xeC455fFC19811e573eb5700a1bDff6ee1C47AB7B` | LayerZero OFT adapter (11,266 B). |
| Protocol admin (owner) | `0x01a494079dcb715f622340301463ce50cd69a4d0` | Owns Bridge + Messenger on all chains. |

## 4. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** | `0x3C4FA639c8D7E65c603145adaD8bD12F2358312f` | (10,784 B, identical to ETH Bridge). |
| **Messenger** | `0x3c37bdd7acae01a8b14e0ad8be52e7ea5066c27f` | gasOracle `0xcaf00d…689b`. |
| **GasOracle** | `0xcaf00d24ebdde93729aef967ffa5864eb3b9689b` | |
| **Pool — USDT** | `0xf833afA46fCD100e62365a0fDb0734b7c4537811` | |
| **Pool — USDC** | `0x731822532CbC1c7C48462c9e5Dc0c04A1Ff29953` | (larger 13,385 B build). |
| **CctpBridge / CctpV2Bridge / OftBridge** | **not deployed** | `eth_getCode` = `0x`. CCTP/OFT are only on the chains in §3/§5/§6 below; BNB is not a Circle CCTP domain. |

## 5. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x7775d63836987f444E2F14AA0fA2602204D7D3E0` |
| **Messenger** | `0x3e03835dbf5cbd4cfa28f1b8587b80810838451c` |
| **GasOracle** | `0x163f2070eb345836b7321d1c2168bcb1f329d612` |
| **Pool — USDC** | `0x4C42DfDBb8Ad654b42F66E0bD4dbdC71B52EB0A6` |
| **Pool — USDT** | `0x0394c4f17738A10096510832beaB89a9DD090791` |
| **CctpBridge (CCTP v1)** | `0x710282BfeB554Ed0A34dFaD061C7c343221AC82C` |
| **CctpV2Bridge / OftBridge** | **not deployed** (`0x`). |

## 6. Addresses — Avalanche C-Chain (chain ID 43114)

Verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x9068E1C28941D0A680197Cc03be8aFe27ccaeea9` |
| **Messenger** | `0xfd6e9dce8f98b1093049430de242ffaa7336446f` |
| **GasOracle** | `0x175fda4260b8be64eaf6090a9c7b84b9c1a2d29e` |
| **Pool — USDC** | `0xe827352A0552fFC835c181ab5Bf1D7794038eC9f` |
| **Pool — USDT** | `0x2d2f460d7a1e7a4fcC4Ddab599451480728b5784` |
| **CctpBridge (CCTP v1)** | `0x65dE05Fccce36Ce7FdDd668Ef4348D9e933B57Ff` |
| **CctpV2Bridge (CCTP v2)** | `0x5FBf8d23fa705A0bADb6f398fDcdC28FCCB521c0` |
| **OftBridge** | **not deployed** (`0x`). |

## 7. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x9Ce3447B58D58e8602B7306316A5fF011B92d189` |
| **Messenger** | `0xd5826d4d30c112b2ba0178a03be0cdd3f6bc4f9d` |
| **GasOracle** | `0x2476b2f821612afbf01dfc51e4cd4d7b77ebcb10` |
| **Pool — USDC** | `0x690e66fc0F8be8964d40e55EdE6aEBdfcB8A21Df` |
| **Pool — USDT** | `0x47235cB71107CC66B12aF6f8b8a9260ea38472c7` |
| **Pool — USDe** | `0x2b5e5E6008742Cd9d139C6Add9Cac57679C59D6d` | `token()` = USDe `0x5d3a…ef34` (13,385 B). **NB: the USDe _token_ is `0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34` — not the pool.** |
| **CctpBridge (CCTP v1)** | `0x23e1aec13c92158643cf2aa17e155d27a792ccdb` |
| **CctpV2Bridge (CCTP v2)** | `0x7ED5343dFC95dc3eBe5B6de64F5B5423A888Ca18` |
| **OftBridge (OFT)** | `0xB074e73e637E778BE6411c3732bD58D44194FDEa` |

## 8. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x97E5BF5068eA6a9604Ee25851e6c9780Ff50d5ab` |
| **Messenger** | `0x309a090e3fe6b122b23c6ca6df51f83d7a093695` |
| **GasOracle** | `0x4ad835ffa57e5e1e82514b2ba01d21fc15199d9a` |
| **Pool — USDC** | `0x3B96F88b2b9EB87964b852874D41B633e0f1f68F` |
| **Pool — USDT** | `0xb24A05d54fcAcfe1FC00c59209470d4cafB0deEA` |
| **CctpBridge (CCTP v1)** | `0x08391edF36f41f05d27A1e0fD7a29448417C1CD0` |
| **CctpV2Bridge / OftBridge** | **not deployed** (`0x`). |

## 9. Addresses — Base (chain ID 8453)

Verified via `eth_getCode` on `https://base-rpc.publicnode.com`.

| Role | Address |
|------|---------|
| **Bridge** | `0x001E3f136c2f804854581Da55Ad7660a2b35DEf7` |
| **Messenger** | `0x9bc674e2ce891f34dd8a7531ff291e9579558271` |
| **GasOracle** | `0x7b806aebcf82cecfb43e0e3df749c5232942f6d6` |
| **Pool — USDC** | `0xDA6bb1ec3BaBA68B26bEa0508d6f81c9ec5e96d5` |
| **Pool — USDT** | **none listed** (Base USDC-only Core pool). |
| **CctpBridge (CCTP v1)** | `0x1eFE2C85989D97fEBbD0743cdd79B9F0826314f6` |
| **CctpV2Bridge (CCTP v2)** | `0x214D972b8c869cfcE50D55B595adC7eF336D7FAd` |
| **OftBridge** | **not deployed** (`0x`). |

---

## 10. Cross-chain summary

| Chain | ID | Bridge | Messenger | GasOracle | Pools | CCTP v1 | CCTP v2 | OFT |
|---|---|---|---|---|---|---|---|---|
| Ethereum | 1 | ✓ `0x609c…0c9e` | ✓ `0x203e…86da` | ✓ `0x0bdf…96e0` | USDC, USDT, USDe | ✓ | ✓ | ✓ |
| BNB | 56 | ✓ `0x3C4F…312f` | ✓ `0x3c37…c27f` | ✓ `0xcaf0…689b` | USDT, USDC | — | — | — |
| Polygon | 137 | ✓ `0x7775…D3E0` | ✓ `0x3e03…451c` | ✓ `0x163f…d612` | USDC, USDT | ✓ | — | — |
| Avalanche | 43114 | ✓ `0x9068…eea9` | ✓ `0xfd6e…446f` | ✓ `0x175f…d29e` | USDC, USDT | ✓ | ✓ | — |
| Arbitrum | 42161 | ✓ `0x9Ce3…d189` | ✓ `0xd582…4f9d` | ✓ `0x2476…cb10` | USDC, USDT, USDe | ✓ | ✓ | ✓ |
| Optimism | 10 | ✓ `0x97E5…d5ab` | ✓ `0x309a…3695` | ✓ `0x4ad8…9d9a`† | USDC, USDT | ✓ | — | — |
| Base | 8453 | ✓ `0x001E…DEf7` | ✓ `0x9bc6…8271` | ✓ `0x7b80…f6d6` | USDC | ✓ | ✓ | — |

† OP GasOracle full address `0x4ad835ffa57e5e1e82514b2ba01d21fc15199d9a`.

**No vanity / deterministic addressing** — every chain's Core contracts are at unrelated addresses (the Bridge runtime bytecode is identical, 10,784 B, but the deployment addresses differ). The **shared invariant** is the owner `0x01a494…a4d0`, not the address. **Counterparty chains outside the seven:** Core also bridges to/from **Tron** (`TAuErcuAtU6BPt6YwL51JZ4RpDCPQASCU2`), **Solana** (`BrdgN2RPzEMWF96ZbnnJaUtQDQx7VRXYaHHbYCBvceWB`), **Celo** (`0x80858f5F8EFD2Ab6485Aba1A0B9557ED46C6ba0e`), and **Sui** (`0x83d6f864a6b0f16898376b486699aa6321eb6466d1daf6a2e3764a51908fe99d`) — record these as bridge destinations seen in `destinationChainId`.

---

## 11. Proxies (old & new)

**There are no proxies in Allbridge Core. Every contract is immutable.**

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Bridge, Pool(s), Messenger, WormholeMessenger, GasOracle, CctpBridge, CctpV2Bridge, OftBridge | **Immutable (no proxy)** | EIP-1967 impl slot `0x360894…382bbc` reads `0x000…000` on every one (confirmed live on ETH Bridge, ETH USDC Pool, ETH CCTP). Full runtime bytecode is in the deployed account, not a delegatecall target. | n/a — "upgrade" = deploy new contract + owner-only re-pointing (`addPool`/`setRouter`/`registerBridge`). |

EIP-1967 implementation slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (reads `0x0` everywhere). Admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` is likewise empty. **There is no `Upgraded(address)` event to watch** — instead watch the owner-only setters and `SecondaryValidatorsSet` (§1.3) for the validator-set rotations that govern message acceptance.

---

## 12. Detection invariants & gotchas

1. **The `Bridge` is also the `Router`.** Same-chain `Swapped`, cross-chain `TokensSent`/`TokensReceived`, and the fee events all emit from the one Bridge address per chain. There is no separate Router contract on-chain.
2. **`TokensSent` topic0 collides by name across 3 contracts.** Bridge `0x9cd6008e…` (6-arg) ≠ CctpBridge `0xaf142c08…` (10-arg) ≠ CctpV2Bridge `0x2f76d450…` (10-arg, reordered). OftBridge uses `OftTokensSent` (`0xeb30a1ea…`). Always key on `(topic0, emitter)`.
3. **`amount` in Bridge `TokensSent` is vUSD in 3-decimal system precision**, NOT the raw token amount. The raw token amount appears in the Pool `SwappedToVUsd.amount` (entry leg) and `SwappedFromVUsd.amount` (exit leg). For USD value, use the Pool event amounts or convert vUSD (1 vUSD ≈ $1, 3-dec).
4. **`recipient` / `receiveToken` / counterparty-bridge addresses are `bytes32`,** left-padded for EVM (20-byte addr in the low bytes) and full-width for Solana/Tron/Sui. Don't truncate before checking which chain you're decoding for.
5. **`nonce` is the cross-chain key.** The message preimage (see `hashMessage`) binds `(amount, recipient, srcChainId, dstChainId, receiveToken, nonce, messenger)`; the on-chain `message` is that hash. Match a source `TokensSent` to a destination `TokensReceived` by `nonce` + chain pair, and to the messaging layer by the `message` hash in `MessageSent`/`MessageReceived`.
6. **Pool `Deposit(address,uint256)` shares topic0 `0xe1fffcc4…` with WETH/canonical `Deposit`,** and `Pool.withdraw(uint256)` shares selector `0x2e1a7d4d` with WETH `withdraw`. Filter Pool events strictly by the Pool address.
7. **`swapToVUsd`/`swapFromVUsd` are `onlyRouter`.** A direct call from a non-Bridge address reverts — these always appear inside a `swapAndBridge`/`receiveTokens`/`swap` tx, with the Bridge as caller.
8. **Most current Core volume is CCTP, not the vUSD pool bridge.** The original swap bridge still fires (verified live on ETH), but for USDC the CCTP v1/v2 adapters carry the bulk. Index both families.
9. **Transfers arrive via aggregators.** The sampled ETH `swapAndBridge` tx had `tx.to` = LI.FI (`0x1231deb6…`), not the Bridge — attribute by the Bridge **event emitter**, never by `tx.to`.
10. **The destination relayer, not the user, calls `receiveTokens`.** The real beneficiary is the `recipient` field of `TokensReceived`, not the tx sender.
11. **Validator-set is the security boundary for Allbridge-protocol messages.** `MessageReceived` is only emitted after `ecrecover` against the primary + a secondary validator. Watch `SecondaryValidatorsSet` (`0x55981f51…`) — a validator rotation is a governance-grade signal.
12. **Wormhole `MessageSent` is 2-arg (`0x3d268d70…`) and distinct from Allbridge `MessageSent` (1-arg, `0x54791b38…`).** Which backend a transfer used is the `messenger` enum field (2=Wormhole, 1=Allbridge).
13. **CCTP v1 vs v2 share the `bridge(...)` selector `0x7dfb08f1` and the `TokensSentExtras` topic0.** Disambiguate v1/v2 purely by emitter address (§3) and by the `TokensSent` topic0.
14. **CctpBridge/CctpV2Bridge/OftBridge are NOT on every chain.** OFT is ETH + Arbitrum only; CCTP v2 is ETH/Avax/Arb/Base only; CCTP v1 is everywhere except BNB. BNB has no CCTP/OFT adapter at all (not a Circle CCTP domain). An `eth_getCode` = `0x` here is a recorded absence, not a gap.
15. **`USDe` pools exist only on ETH + Arbitrum;** Base has a USDC pool only; the rest carry USDC + USDT. The pool set is per-chain — read the Bridge's pool registry (`pools(bytes32)`), don't assume.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- Bridge / Router
TOPIC_BRIDGE_TOKENS_SENT      = '\x9cd6008e8d4ebd34fd9d022278fec7f95d133780ecc1a0dea459fae3e9675390'
TOPIC_BRIDGE_TOKENS_RECEIVED  = '\xe9d840d27ab4032a839c20760fb995af8e3ad1980b9428980ca1c7e072acd87a'
TOPIC_RECEIVE_FEE             = '\x706abb59b8db30e9e92cb7e272fbe6682712ec97e7b117d7ee3389b24bb3de21'
TOPIC_BRIDGING_FEE_FROM_TOKENS= '\x02a1962fff2ae0f895c1fcd8481ce39cce1e8083e752ce6f5e80d2b5366382c8'
TOPIC_SWAPPED                 = '\xe85f63622be58135a84c6e9de632115a3c471b0540a04d37a7c53a0647cd0c39'
-- Pool
TOPIC_SWAPPED_TO_VUSD         = '\xa930da1d3f27a25892307dd59cec52dd9b881661a0f20364757f83a0da2f6873'
TOPIC_SWAPPED_FROM_VUSD       = '\xfc1df7b9ba72a13350b8a4e0f094e232eebded9edd179950e74a852a0f405112'
TOPIC_POOL_DEPOSIT            = '\xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'
TOPIC_POOL_WITHDRAW           = '\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'
TOPIC_REWARDS_CLAIMED         = '\xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe'
-- Messenger (Allbridge)
TOPIC_MESSAGE_SENT            = '\x54791b38f3859327992a1ca0590ad3c0f08feba98d1a4f56ab0dca74d203392a'
TOPIC_MESSAGE_RECEIVED        = '\xe29dc34207c78fc0f6048a32f159139c33339c6d6df8b07dcd33f6d699ff2327'
TOPIC_SECONDARY_VALIDATORS_SET= '\x55981f511768d27d1efe9b8e19f36310c3db332ea190227d182d0af4d64c27c4'
-- WormholeMessenger (2-arg)
TOPIC_WH_MESSAGE_SENT         = '\x3d268d705c99ec99e84748365f374dea1d745080faad9ddfa8c2715d20b50cb0'
TOPIC_WH_MESSAGE_RECEIVED     = '\x556d717a59d7ef2969f5a9f2c6f9199f9a4e78cb7704aa4162ee70f7d2b771f1'
-- CctpBridge v1
TOPIC_CCTP_TOKENS_SENT        = '\xaf142c08d51839efeb25c71c958dec48ffa3a832ba72324fbf8802dea6ec2bd1'
TOPIC_CCTP_TOKENS_SENT_EXTRAS = '\x95fcfca390614e1aac005a21c415843c9ec9d9d32ea180cf5c1901422f54a958'
TOPIC_CCTP_RECIPIENT_REPLACED = '\x004e74b82cca19ab607251d92cf8d3147a281463adb41c6dbf2629f396337bca'
TOPIC_CCTP_RECEIVED_GAS       = '\xcb213a07f467a18546d6296f2850c3b891d3918fd44a941ca501932229f45fc7'
TOPIC_CCTP_RECEIVED_EXTRA_GAS = '\x0d46b66d2c8a984b124fbfee6aa2c757ca68de14666d1884867bb69cce652acf'
-- CctpV2Bridge
TOPIC_CCTPV2_TOKENS_SENT      = '\x2f76d450a444053faafc76ad43e8bac6f5092b83a06461face925b6221d5a226'
TOPIC_CCTPV2_RECEIVED_MSG_ID  = '\x0d605cc2ed964920ed498c9723390d3585b30aa403f7cf5bc0d7c53113d2f57d'
-- OftBridge
TOPIC_OFT_TOKENS_SENT         = '\xeb30a1ea9476f0902725e947bd1d6d5e9026c15f73aad8515682a61354f05eea'
-- common
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== Selectors =====
SEL_SWAP_AND_BRIDGE           = '\x4cd480bd'
SEL_RECEIVE_TOKENS            = '\xe43bfe5e'
SEL_SWAP                      = '\x331838b2'
SEL_HASH_MESSAGE              = '\x2ed1084b'
SEL_GET_BRIDGING_COST_TOKENS  = '\x7d18330b'
SEL_POOL_DEPOSIT              = '\xb6b55f25'
SEL_POOL_WITHDRAW             = '\x2e1a7d4d'
SEL_SWAP_TO_VUSD              = '\x28fdb481'
SEL_SWAP_FROM_VUSD            = '\x2d46f63e'
SEL_CLAIM_REWARDS             = '\x372500ab'
SEL_MESSENGER_SEND_MESSAGE    = '\xe12c9ca8'
SEL_MESSENGER_RECEIVE_MESSAGE = '\xd8de8503'
SEL_CCTP_BRIDGE               = '\x7dfb08f1'   -- CctpBridge AND CctpV2Bridge
SEL_CCTP_BRIDGE_WALLET        = '\x7d677480'
SEL_CCTP_RECEIVE_TOKENS       = '\x1e976500'
SEL_CCTP_CHANGE_RECIPIENT     = '\xf3b1f721'
SEL_OFT_BRIDGE                = '\x7daca3a4'

-- ===== Proxy slots (all read 0x0 — Core is immutable) =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Protocol admin (all chains) =====
CORE_OWNER                    = '\x01a494079dcb715f622340301463ce50cd69a4d0'

-- ===== Ethereum (chain ID 1) =====
ETH_BRIDGE                    = '\x609c690e8f7d68a59885c9132e812eebdaaf0c9e'
ETH_MESSENGER                 = '\x203e8785b4d4312c4152d0c42ba3fa8bd79086da'
ETH_GAS_ORACLE                = '\x0bdf6139f2841a7856ca154d851182c52f5b96e0'
ETH_POOL_USDC                 = '\xa7062bba94c91d565ae33b893ab5dfaf1fc57c4d'
ETH_POOL_USDT                 = '\x7dbf07ad92ed4e26d5511b4f285508ebf174135d'
ETH_POOL_USDE                 = '\xcab34d4d532a9c9929f4f96d239653646351abad'  -- pool (token()=USDe 0x4c9edd…68b3); the 0x4c9edd… addr is the USDe TOKEN, not the pool
ETH_CCTP                      = '\xc51397b75b783e31469bfaade79913f3f82210d6'
ETH_CCTP_V2                   = '\x7972d6907739593c00e6284c53c83db3ecd15c33'
ETH_OFT                       = '\xec455ffc19811e573eb5700a1bdff6ee1c47ab7b'

-- ===== BNB (chain ID 56) =====
BNB_BRIDGE                    = '\x3c4fa639c8d7e65c603145adad8bd12f2358312f'
BNB_MESSENGER                 = '\x3c37bdd7acae01a8b14e0ad8be52e7ea5066c27f'
BNB_GAS_ORACLE                = '\xcaf00d24ebdde93729aef967ffa5864eb3b9689b'
BNB_POOL_USDT                 = '\xf833afa46fcd100e62365a0fdb0734b7c4537811'
BNB_POOL_USDC                 = '\x731822532cbc1c7c48462c9e5dc0c04a1ff29953'
-- BNB: no CCTP / OFT adapter

-- ===== Polygon (chain ID 137) =====
POLY_BRIDGE                   = '\x7775d63836987f444e2f14aa0fa2602204d7d3e0'
POLY_MESSENGER                = '\x3e03835dbf5cbd4cfa28f1b8587b80810838451c'
POLY_GAS_ORACLE               = '\x163f2070eb345836b7321d1c2168bcb1f329d612'
POLY_POOL_USDC                = '\x4c42dfdbb8ad654b42f66e0bd4dbdc71b52eb0a6'
POLY_POOL_USDT                = '\x0394c4f17738a10096510832beab89a9dd090791'
POLY_CCTP                     = '\x710282bfeb554ed0a34dfad061c7c343221ac82c'

-- ===== Avalanche (chain ID 43114) =====
AVAX_BRIDGE                   = '\x9068e1c28941d0a680197cc03be8afe27ccaeea9'
AVAX_MESSENGER                = '\xfd6e9dce8f98b1093049430de242ffaa7336446f'
AVAX_GAS_ORACLE               = '\x175fda4260b8be64eaf6090a9c7b84b9c1a2d29e'
AVAX_POOL_USDC                = '\xe827352a0552ffc835c181ab5bf1d7794038ec9f'
AVAX_POOL_USDT                = '\x2d2f460d7a1e7a4fcc4ddab599451480728b5784'
AVAX_CCTP                     = '\x65de05fccce36ce7fddd668ef4348d9e933b57ff'
AVAX_CCTP_V2                  = '\x5fbf8d23fa705a0badb6f398fdcdc28fccb521c0'

-- ===== Arbitrum (chain ID 42161) =====
ARB_BRIDGE                    = '\x9ce3447b58d58e8602b7306316a5ff011b92d189'
ARB_MESSENGER                 = '\xd5826d4d30c112b2ba0178a03be0cdd3f6bc4f9d'
ARB_GAS_ORACLE                = '\x2476b2f821612afbf01dfc51e4cd4d7b77ebcb10'
ARB_POOL_USDC                 = '\x690e66fc0f8be8964d40e55ede6aebdfcb8a21df'
ARB_POOL_USDT                 = '\x47235cb71107cc66b12af6f8b8a9260ea38472c7'
ARB_POOL_USDE                 = '\x2b5e5e6008742cd9d139c6add9cac57679c59d6d'  -- pool (token()=USDe 0x5d3a1ff2…ef34); the 0x5d3a1ff2… addr is the USDe TOKEN, not the pool
ARB_CCTP                      = '\x23e1aec13c92158643cf2aa17e155d27a792ccdb'
ARB_CCTP_V2                   = '\x7ed5343dfc95dc3ebe5b6de64f5b5423a888ca18'
ARB_OFT                       = '\xb074e73e637e778be6411c3732bd58d44194fdea'

-- ===== Optimism (chain ID 10) =====
OP_BRIDGE                     = '\x97e5bf5068ea6a9604ee25851e6c9780ff50d5ab'
OP_MESSENGER                  = '\x309a090e3fe6b122b23c6ca6df51f83d7a093695'
OP_GAS_ORACLE                 = '\x4ad835ffa57e5e1e82514b2ba01d21fc15199d9a'
OP_POOL_USDC                  = '\x3b96f88b2b9eb87964b852874d41b633e0f1f68f'
OP_POOL_USDT                  = '\xb24a05d54fcacfe1fc00c59209470d4cafb0deea'
OP_CCTP                       = '\x08391edf36f41f05d27a1e0fd7a29448417c1cd0'

-- ===== Base (chain ID 8453) =====
BASE_BRIDGE                   = '\x001e3f136c2f804854581da55ad7660a2b35def7'
BASE_MESSENGER                = '\x9bc674e2ce891f34dd8a7531ff291e9579558271'
BASE_GAS_ORACLE               = '\x7b806aebcf82cecfb43e0e3df749c5232942f6d6'
BASE_POOL_USDC                = '\xda6bb1ec3baba68b26bea0508d6f81c9ec5e96d5'
BASE_CCTP                     = '\x1efe2c85989d97febbd0743cdd79b9f0826314f6'
BASE_CCTP_V2                  = '\x214d972b8c869cfce50d55b595adc7ef336d7fad'
```

---

## 14. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from the Solidity sources in `allbridge-io/allbridge-core-evm-contracts` (`Bridge.sol`, `Router.sol`, `Pool.sol`, `RewardManager.sol`, `Messenger.sol`, `WormholeMessenger.sol`, `GasOracle.sol`, `CctpBridge.sol`, `CctpV2Bridge.sol`, `OftBridge.sol`). Field types/orders taken verbatim from the event declarations.
- **Live event cross-checks (`eth_getLogs`):** on Ethereum, the Bridge `0x609c…0c9e` emits `TokensSent 0x9cd6008e…`, `TokensReceived 0xe9d840d2…`, `ReceiveFee 0x706abb59…`, `BridgingFeeFromTokens 0x02a1962f…`; the ETH CCTP bridge `0xC51397…` emits `TokensSent 0xaf142c08…` + `TokensSentExtras 0x95fcfca3…` (sample tx `0xce2c9b94…cd…`, block 25,265,482); the ETH USDC pool `0xa7062bba…` emits `SwappedToVUsd 0xa930da1d…`; the ARB USDC pool `0x690e…` emits `SwappedFromVUsd 0xfc1df7b9…`; the ETH Messenger `0x203e8785…` emits `MessageSent 0x54791b38…` (all in the same routed tx `0x38ae9501…`).
- **Addresses:** Bridge / Pool / CCTP / CCTPv2 / OFT parsed from the official Core contracts page (`docs-core.allbridge.io/.../allbridge-core-contracts`); Messenger + GasOracle (not published) discovered on-chain (Messenger = the `MessageSent` emitter in a real Bridge tx; GasOracle = storage slot 1 of the Messenger). Every address existence-checked via `eth_getCode` returning non-empty bytecode on the listed RPC.
- **Immutability:** EIP-1967 impl slot `0x360894…382bbc` read live = `0x0` on the ETH Bridge, ETH USDC Pool, and ETH CCTP bridge → no proxies. Admin slot likewise empty.
- **Admin:** Ownable slot 0 of the Bridge and Messenger reads `0x01a494079dcb715f622340301463ce50cd69a4d0` identically on all seven chains. Classic admin (validator/feeCollector/feeOracle) is in [classic.md](classic.md).
- **Chain coverage:** `eth_getCode` run for every Bridge/Pool/Messenger/GasOracle/CCTP/OFT address on all seven RPCs; absences (`0x`) recorded explicitly in §4–§9 and §10 (BNB has no CCTP/OFT; OP/Polygon/BNB have no CCTP v2; only ETH+Arb have OFT).

**Authoritative sources:**
- Canonical contracts: [`github.com/allbridge-io/allbridge-core-evm-contracts`](https://github.com/allbridge-io/allbridge-core-evm-contracts)
- Official docs: [`docs-core.allbridge.io`](https://docs-core.allbridge.io) · contract list [`/product/how-does-allbridge-core-work/allbridge-core-contracts`](https://docs-core.allbridge.io/product/how-does-allbridge-core-work/allbridge-core-contracts)
- SDK / API: [`github.com/allbridge-io/allbridge-core-js-sdk`](https://github.com/allbridge-io/allbridge-core-js-sdk) · [`allbridge-core-rest-api`](https://github.com/allbridge-io/allbridge-core-rest-api)
- Explorers: [Etherscan Bridge](https://etherscan.io/address/0x609c690e8F7D68a59885c9132e812eEbDaAf0c9e) · [BscScan](https://bscscan.com/address/0x3C4FA639c8D7E65c603145adaD8bD12F2358312f) · [Arbiscan](https://arbiscan.io/address/0x9Ce3447B58D58e8602B7306316A5fF011B92d189) · [Basescan](https://basescan.org/address/0x001E3f136c2f804854581Da55Ad7660a2b35DEf7)
