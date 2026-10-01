# Squid Intents (Coral) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; NOT Robinhood Chain)

**Status:** verified on 2026-09-29 to 2026-10-01 against live RPC on all eight target chains, the verified `contracts/Spoke.sol` source of each listed Spoke (Blockscout), and the Squid docs. Topic0 and selectors recomputed as `keccak256(signature)`. Addresses existence-checked with `eth_getCode`.
**Scope:** Squid's intent product, named CORAL ("Cross-chain Order Routing and Auction Layer") and now "Squid Intents". Two generations: **Coral V1**, a Spoke contract per chain plus a Hub on Fantom, with on-chain order events; and **Coral V2**, the current product, which settles through TEE-governed wallets and has no contract events. The SquidRouter is in [`router.md`](router.md). Topics and selectors are chain-agnostic. Addresses are network-specific.

**Coral V1 had no activity in the pinned window.** `OrderCreated` and `OrderFilled` returned 0 logs from any emitter on all eight chains in 2026-09-28 00:00–12:00 UTC. On Base, the newest Spoke's last `OrderCreated` is at block 46,215,933 (May 2026) and its last transaction (`forwardSettlements`) is from 2026-06-18. Keep the V1 constants for history and back-fill.

**Coral V2 replaces the Spoke contracts.** The Squid docs say that "only a token transfer ever touched the chain": the user deposits on the source chain to an escrow wallet that a Cubist TEE key controls (the "CORAL spoke address"), a market maker pays the user on the destination chain with a direct transfer, and the TEE key then releases the deposit to the market maker on the source chain. Refunds go back on the source chain within about 15 minutes, to `order.fromAddress`. The link key is the Squid `quoteId`, which lives only in the Squid API (`/v2/status?quoteId=`) and on `https://scan.squidrouter.com`. Squid does not publish the escrow wallet addresses, so this doc lists none (§6, item 6).

---

## 0. Contract families & versions

| Component | Generation | Role | Chains |
|-----------|-----------|------|--------|
| **Spoke** (six verified deployments, §3) | Coral V1 | Source escrow (`createOrder`), destination fill (`fillOrder`), settlement forwarding and release, refunds | Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche. Not Robinhood Chain |
| **Hub** | Coral V1 | Matches fills to orders and sends release messages to the source Spoke | Fantom only (outside the eight chains) |
| `Create2Deployer` | Coral V1 | CREATE2 factory that deployed every Spoke at one address on all chains | The seven chains above |
| TEE escrow wallets | Coral V2 | Hold deposits until release or refund | Not published |

The flow of one V1 order:

| Step | Chain | Event (emitter) | Value movement in the same tx |
|------|-------|-----------------|-------------------------------|
| Deposit | Source | `OrderCreated(orderHash, order)` (source Spoke) | `fromAmount` of `fromToken`: `Transfer` `msg.sender` → Spoke, or native `msg.value` |
| Fill | Destination | `OrderFilled(orderHash, order)` (destination Spoke) | `fillAmount` of `toToken`: `Transfer` filler → `toAddress` (or → SquidMulticall when `postHookHash` is set) |
| Forward | Destination | `SettlementForwarded(orderHash)`, then Axelar `ContractCall` or a LayerZero send to the Hub | Message gas only. Status only |
| Release | Source | `TokensReleased(orderHash)` (source Spoke, called by the Axelar relayer or the LayerZero executor) | Escrowed `fromToken` Spoke → `order.filler`, minus the protocol fee |
| Refund | Source | `OrderRefunded(orderHash)` | `fromAmount` Spoke → `order.fromAddress` |

**Link key: `orderHash = keccak256(abi.encode(order))`.** It is topic1 of every Spoke event on both chains, and the full `order` tuple is in the data of `OrderCreated` and `OrderFilled`. `order.fromChain` and `order.toChain` are EVM chain ids.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Spoke (emitter: a Spoke of §3)

| topic0 | Event | Leg / meaning |
|--------|-------|---------------|
| `0x181de28643611afcf1cb4c095a1ef99c157e78437294f478c978e4a56e1ca77e` | `OrderCreated(bytes32 indexed orderHash, (address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash) order)` | **Source leg.** Source Spoke. `fromAmount` of `fromToken` moved from `msg.sender` into the Spoke (or `msg.value` for native). |
| `0x6955fd9b2a7639a9baac024897cad7007b45ffa74cbfe9582d58401ff6b977b7` | `OrderFilled(bytes32 indexed orderHash, (address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash) order)` | **Destination leg.** Destination Spoke. The filler paid `fillAmount` of `toToken` to `toAddress` (or to SquidMulticall for a post-hook) in this tx. |
| `0xa60671d8537ed193e567f86ddf28cf35dc67073b5ad80a2d41359cfa78db0a1e` | `OrderRefunded(bytes32 indexed orderHash)` | **Refund.** Source Spoke paid `fromAmount` back to `order.fromAddress`. The amount is not in the event. |
| `0x69f975bd70ea51b973eb6aff3812f49adf595bd59d6f3d29840d5695cc19ba30` | `SettlementForwarded(bytes32 indexed orderHash)` | Destination Spoke: the fill was batched to the Hub (Axelar `callContract` or LayerZero). **Status only.** |
| `0xd48052bf92f3eec93ecdeeec72ea80e1071c926cb4d6e5a37ee71be8a0ce9a10` | `TokensReleased(bytes32 indexed orderHash)` | Source Spoke: the Hub confirmed the fill; the escrowed tokens went to `order.filler` (the solver), minus the protocol fee. **Escrow pays solver.** |
| `0x9bcb6d1f38f6800906185471a11ede9a8e16200853225aa62558db6076490f2d` | `FeesCollected(address indexed feeCollector, address indexed token, uint256 indexed amount)` | Protocol fees withdrawn by `feeCollector`. |
| `0x66b86e9a862484192b40f4e2dc828c11d9e09ca77f9d2c226a96e743f99e4ec8` | `SpokeInitialized(address indexed gateway, address indexed gasService, address indexed permit2, address squidMulticall, address feeCollector, string hubChainName, string hubAddress)` | Init, spokes of 2024-10 to 2025-02. Names the Hub. **Status only.** |
| `0xf25a5e989fb7e02dc64e8a2c85e4fbaae049d3ce88c8cbb840860122201da24b` | `SpokeInitialized(address indexed gateway, address indexed gasService, address squidMulticall, address feeCollector, string hubChainName, string hubAddress)` | Init, spokes of 2025-10. **Status only.** |
| `0xdb6b260ea45f7fe513e1d3b8c21017a29e3a41610e95aefb8862b81c69aec61c` | `TrustedAddressSet(string chain, string address_)` | Trusted Hub set. Admin. |
| `0xf9400637a329865492b8d0d4dba4eafc7e8d5d0fae5e27b56766816d2ae1b2ca` | `TrustedAddressRemoved(string chain)` | Admin. |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` | LayerZero peer (Hub) set, spokes of 2025 only. Admin. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | OpenZeppelin `Ownable`, spokes of 2025 only. Admin. |

`FeesCollected` indexes `amount` (topic3). The Hub emits `SettlementFilled` and `SettlementProcessed` on Fantom only; they are not listed.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

`Order` = `(address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash)`. Native token = `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`. Fee = `fromAmount * feeRate / 1000000`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0d77797c` | `createOrder((address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash) order)` | Source. Payable. Pulls `fromAmount` from `msg.sender`; the order belongs to `order.fromAddress`. |
| `0xaab59a09` | `fillOrder((address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash) order, (uint8 callType, address target, uint256 value, bytes callData, bytes payload)[] calls)` | Destination. Only `order.filler`. Payable for a native `toToken`. |
| `0x1e44fb97` | `refundOrder((address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash) order)` | Source. The filler at any time, anyone after `expiry` + 24 hours. |
| `0x0630dea4` | `forwardSettlements(bytes32[] orderHashes, uint256 lzFee, uint128 gasLimit, uint8 provider)` | Destination. `provider` 0 = Axelar, 1 = LayerZero. Payable (message gas). Spokes of 2025-10. |
| `0x58c0f729` | `collectFees(address[] tokens)` | Fee collector only. |
| `0x02cf7c19` | `forwardSettlements(bytes32[] orderHashes)` | Destination. Axelar only. Spokes of 2024-10 to 2024-12. Payable. |
| `0x79db29c8` | `sponsorOrder((address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash) order, bytes signature)` | Source, gasless: a relayer creates the order with `fromAddress`'s EIP-712 signature. Spokes of 2024-10 to 2025-02. |
| `0x2e3d6cf9` | `sponsorOrderUsingPermit2((address fromAddress, address toAddress, address filler, address fromToken, address toToken, uint256 expiry, uint256 fromAmount, uint256 fillAmount, uint256 feeRate, uint256 fromChain, uint256 toChain, bytes32 postHookHash) order, ((address token, uint256 amount) permitted, uint256 nonce, uint256 deadline) permit, bytes signature)` | Same, funded by Permit2. Spokes of 2024-10 to 2025-02. |

`forwardSettlements(bytes32[])` is on the Spokes `0xDdDDD043bD7A886a26C1231e4305582faB219667`, `0xcd6A73e91Da4026ce3931557829ef0E08f5aCCcC` and `0xA4cE01bD7Dd91DA968a7C4A8D04282a3f5eA06bB`. The four-argument form is on `0xdf4fFDa22270c12d0b5b3788F1669D709476111E`, `0xD6C94698E5D8fA506d544d92AdE1436Dda7d933D` and `0xfe91aAA1012B47499CfE8758874F2D2c52B22cD8`. The two sponsor functions are on the four Spokes before October 2025.

---

## 3. Addresses — Ethereum (1), Base (8453), Arbitrum (42161), Optimism (10), Polygon (137), BNB (56), Avalanche (43114)

Each Spoke has the same address on all seven chains (CREATE2 through `Create2Deployer` `0x73c94A113D49Fc3d4C5733Dc195acf623F793f97`, called by `0xD9c9c62Dc51784b2C651Dd21bac294938AD8EB3D`). `eth_getCode` is non-empty for all six on all seven chains. Creation dates are from Base.

| Spoke | Created (Base) | Code size | Hub on Fantom (`hubAddress` in `SpokeInitialized`) | Messaging | Last direct tx on Base |
|-------|----------------|----------:|------------------------------------------------------|-----------|------------------------|
| `0xDdDDD043bD7A886a26C1231e4305582faB219667` | 2024-10-26 | 19,713 B | `0xcCCCc988a6234BF96c48Bb2651bb1e67a8cbA4C8` | Axelar | 2024-12-04 |
| `0xcd6A73e91Da4026ce3931557829ef0E08f5aCCcC` | 2024-12-04 | 19,787 B | `0xDDDD0825722C99a678C115C1E3E38C32a9cadECd` | Axelar | 2026-01-01 |
| `0xA4cE01bD7Dd91DA968a7C4A8D04282a3f5eA06bB` | 2024-12-04 | 19,711 B | `0x3A394B6678D24C5680E845EEb8e1cbdb7815E247` | Axelar | 2025-08-16 |
| `0xdf4fFDa22270c12d0b5b3788F1669D709476111E` | 2025-02-07 | 24,099 B | `0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8` | Axelar, LayerZero | 2025-12-30 |
| `0xD6C94698E5D8fA506d544d92AdE1436Dda7d933D` | 2025-10-08 | 17,229 B | `0x064116FCe099A5d275efA71dB80f1Dd12733bf5c` | Axelar, LayerZero | 2025-11-03 |
| `0xfe91aAA1012B47499CfE8758874F2D2c52B22cD8` | 2025-10-28 | 17,229 B | `0x3cb85e44711ABc19B81Baa18828A66F8e245442d` | Axelar, LayerZero | 2026-06-18 |

The four older Spokes have a different code hash on each chain (same size); the two Spokes of October 2025 have one code hash on all seven chains. The Spokes are not proxies. The 2025 Spokes are OpenZeppelin `Ownable`; the owner can set the trusted Hub and LayerZero peers but has no withdraw function. All Spokes on Base name the AxelarGateway `0xe432150cce91c13a887f7D836923d5597adD8E31`, the gas service `0x2d5d7d31F671F86C782533cc367F14109a082712` and SquidMulticall `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4`. Fee collectors: `0xC507c32c06f9672674c8F31dEE90060fBe23f8cD` (Spokes before October 2025) and `0xC98eF22Ece8faAba7e0fEc3654f36d094a3c1FBc` (October 2025).

Hub chain identifiers: Axelar chain name `Fantom`, LayerZero eid `30112`. The Hub addresses were read from the `SpokeInitialized` and `TrustedAddressSet` events on Base. They are not existence-checked: Fantom is outside the eight chains.

Earlier prototype Spokes with unverified source, created by the same deployer and emitting the same `OrderCreated` topic0 on Base: `0xD9777d8460E861906B1613D49287988C0de52E7F`, `0x6edfbA4425A1B86883De2615fc906CFfEe4ECCCC`, `0x817d1a328c1Ac1ab88f7Fcf8Dd6015aD1cFacCCc`, `0xa8594af6B4733cDdBeE4b46206bb73d5b6DE2D92`, `0xF877C84254fA411d1673a40AED0f92d442ad2C74`, `0x8bAAa019D048cb2e48CE3E3286c5AB9B014EE91C` (September 2024 to January 2025). Their presence differs by chain (§4).

## 4. Cross-chain summary

| Chain | ID | Six verified Spokes (§3) | `Create2Deployer` | Prototypes `0x6edfbA4425A1B86883De2615fc906CFfEe4ECCCC`, `0x817d1a328c1Ac1ab88f7Fcf8Dd6015aD1cFacCCc` | Other prototypes | Coral V2 |
|-------|----|--------------------------|-------------------|-----------|------------------|----------|
| Ethereum | 1 | all six | yes | yes | none | listed by Squid |
| Base | 8453 | all six | yes | yes | all four | listed |
| Arbitrum One | 42161 | all six | yes | yes | `0xD9777d8460E861906B1613D49287988C0de52E7F`, `0xa8594af6B4733cDdBeE4b46206bb73d5b6DE2D92` | listed |
| Optimism | 10 | all six | yes | yes | `0xD9777d8460E861906B1613D49287988C0de52E7F`, `0xa8594af6B4733cDdBeE4b46206bb73d5b6DE2D92` | listed |
| Polygon PoS | 137 | all six | yes | yes | `0xD9777d8460E861906B1613D49287988C0de52E7F`, `0xa8594af6B4733cDdBeE4b46206bb73d5b6DE2D92` | listed |
| BNB Smart Chain | 56 | all six | yes | yes | `0xD9777d8460E861906B1613D49287988C0de52E7F` | listed |
| Avalanche C-Chain | 43114 | all six | yes | yes | `0xD9777d8460E861906B1613D49287988C0de52E7F`, `0xa8594af6B4733cDdBeE4b46206bb73d5b6DE2D92` | listed |
| Robinhood Chain | 4663 | none (`eth_getCode` = `0x`, nonce 0 at all twelve addresses) | no | no | none | not listed |

"Listed" = in the Squid Intents column of the Squid "Supported Chains by Bridge Type" page.

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Spoke (all six) | Immutable, initialised once (`initialize`, `Initialized(uint64)`) | No EIP-1967 implementation; Blockscout reports no proxy | None. A new version is a new address |
| Create2Deployer | Immutable | 1,835 B, same code hash on the seven chains | none |

---

## 6. Detection invariants & gotchas

1. **Coral V1 is dormant; Coral V2 is invisible to event filters.** A zero count of `OrderCreated` today does not mean that Squid Intents is idle. V2 deposits are plain token transfers to unpublished TEE wallets.
2. **`orderHash` is exact on both sides (V1).** Join `OrderCreated` on the source Spoke to `OrderFilled` on the destination Spoke by topic1, and check `order.fromChain` / `order.toChain` against the emitting chains.
3. **`fromAmount` is the user's deposit; `fillAmount` is what the recipient gets.** The solver's profit and the protocol fee are the difference. `TokensReleased` and `OrderRefunded` carry no amount: take it from the matching `OrderCreated`.
4. **The payer of the deposit can differ from the order owner.** `createOrder` pulls from `msg.sender` (often the SquidRouter or SquidMulticall inside a route), while refunds go to `order.fromAddress`.
5. **Release goes to the solver, not to the user.** `TokensReleased` moves the escrow to `order.filler` on the source chain. Do not count it as a second payout.
6. **No V2 escrow addresses here.** Squid does not publish the TEE escrow wallets, and an address found by heuristics is a guess. Use the Squid status API with `quoteId` for V2 attribution.
7. **Several Spoke generations at once.** Index all six addresses for back-fill. Several Spoke and Hub addresses look like vanity addresses; match on the full address, never on a prefix or suffix.
8. **Admin triggers (V1).** `TrustedAddressSet`, `TrustedAddressRemoved` and `PeerSet` change which Hub can release escrow. On the 2025 Spokes, `OwnershipTransferred` at creation set the owner to `0xD9c9c62Dc51784b2C651Dd21bac294938AD8EB3D`, an externally owned account. The current owner was not read.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_CORAL_ORDER_CREATED         = '\x181de28643611afcf1cb4c095a1ef99c157e78437294f478c978e4a56e1ca77e'
TOPIC_CORAL_ORDER_FILLED          = '\x6955fd9b2a7639a9baac024897cad7007b45ffa74cbfe9582d58401ff6b977b7'
TOPIC_CORAL_ORDER_REFUNDED        = '\xa60671d8537ed193e567f86ddf28cf35dc67073b5ad80a2d41359cfa78db0a1e'
TOPIC_CORAL_SETTLEMENT_FORWARDED  = '\x69f975bd70ea51b973eb6aff3812f49adf595bd59d6f3d29840d5695cc19ba30'
TOPIC_CORAL_TOKENS_RELEASED       = '\xd48052bf92f3eec93ecdeeec72ea80e1071c926cb4d6e5a37ee71be8a0ce9a10'
TOPIC_CORAL_FEES_COLLECTED        = '\x9bcb6d1f38f6800906185471a11ede9a8e16200853225aa62558db6076490f2d'
TOPIC_CORAL_TRUSTED_ADDRESS_SET   = '\xdb6b260ea45f7fe513e1d3b8c21017a29e3a41610e95aefb8862b81c69aec61c'
TOPIC_CORAL_PEER_SET              = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'

-- ===== Selectors (chain-agnostic) =====
SEL_CORAL_CREATE_ORDER            = '\x0d77797c'
SEL_CORAL_FILL_ORDER              = '\xaab59a09'
SEL_CORAL_REFUND_ORDER            = '\x1e44fb97'
SEL_CORAL_FORWARD_SETTLEMENTS     = '\x0630dea4'
SEL_CORAL_FORWARD_SETTLEMENTS_V0  = '\x02cf7c19'

-- ===== Addresses (the same on ETH, BASE, ARB, OP, POLY, BNB, AVAX; none on RH) =====
ETH_CORAL_SPOKE_2024_10           = '\xddddd043bd7a886a26c1231e4305582fab219667'
ETH_CORAL_SPOKE_2024_12A          = '\xcd6a73e91da4026ce3931557829ef0e08f5acccc'
ETH_CORAL_SPOKE_2024_12B          = '\xa4ce01bd7dd91da968a7c4a8d04282a3f5ea06bb'
ETH_CORAL_SPOKE_2025_02           = '\xdf4ffda22270c12d0b5b3788f1669d709476111e'
ETH_CORAL_SPOKE_2025_10A          = '\xd6c94698e5d8fa506d544d92ade1436dda7d933d'
ETH_CORAL_SPOKE_2025_10B          = '\xfe91aaa1012b47499cfe8758874f2d2c52b22cd8'
BASE_CORAL_SPOKE_2024_10          = '\xddddd043bd7a886a26c1231e4305582fab219667'
BASE_CORAL_SPOKE_2024_12A         = '\xcd6a73e91da4026ce3931557829ef0e08f5acccc'
BASE_CORAL_SPOKE_2024_12B         = '\xa4ce01bd7dd91da968a7c4a8d04282a3f5ea06bb'
BASE_CORAL_SPOKE_2025_02          = '\xdf4ffda22270c12d0b5b3788f1669d709476111e'
BASE_CORAL_SPOKE_2025_10A         = '\xd6c94698e5d8fa506d544d92ade1436dda7d933d'
BASE_CORAL_SPOKE_2025_10B         = '\xfe91aaa1012b47499cfe8758874f2d2c52b22cd8'
ETH_CORAL_CREATE2_DEPLOYER        = '\x73c94a113d49fc3d4c5733dc195acf623f793f97'
ETH_CORAL_DEPLOYER_EOA            = '\xd9c9c62dc51784b2c651dd21bac294938ad8eb3d'
```

---

## 8. Verification & sources

How the constants were verified (2026-09-29 to 2026-10-01):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified ABI of each Spoke (Blockscout, `contracts/Spoke.sol`, Solidity 0.8.23). `OrderCreated`, `OrderFilled`, `OrderRefunded`, `SettlementForwarded` and `TokensReleased` were also seen with these topic0 in the Base log history of `0xfe91aAA1012B47499CfE8758874F2D2c52B22cD8`, `0xD6C94698E5D8fA506d544d92AdE1436Dda7d933D` and `0xA4cE01bD7Dd91DA968a7C4A8D04282a3f5eA06bB`. The event list matches the `SpokeEventType` enum of `0xsquid/squid-types` (`src/rfq/index.ts`).
- **Addresses:** the Spokes and their creation transactions from the internal transactions of `Create2Deployer` on Base; Hubs from `SpokeInitialized` and `TrustedAddressSet` in those creation transactions. All twelve Spoke-family addresses and the deployer existence-checked with `eth_getCode` on all eight chains.
- **Measured activity**, pinned window 2026-09-28 00:00–12:00 UTC, any emitter: `OrderCreated` 0 and `OrderFilled` 0 on Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain. On Base, all three Spokes `0xA4cE01bD7Dd91DA968a7C4A8D04282a3f5eA06bB`, `0xdf4fFDa22270c12d0b5b3788F1669D709476111E` and `0xfe91aAA1012B47499CfE8758874F2D2c52B22cD8` emitted 0 logs of any topic in the window. A zero says that V1 was quiet in this window; it says nothing about V2.
- **Coral V2:** described from the Squid docs and the Cubist announcement; not measured on chain, because it has no contract events.

Sources:
- [Squid docs — Squid Intents](https://docs.squidrouter.com/api-and-sdk-integration/coral-intent-swaps) · [Integrating Squid Intents](https://docs.squidrouter.com/api-and-sdk-integration/coral-intent-swaps/integrating-squid-intents) · [Supported Chains by Bridge Type](https://docs.squidrouter.com/chains-and-tokens/coral-intent-swaps) · [Architecture](https://docs.squidrouter.com/additional-resources/architecture) · [Liquidity model](https://docs.squidrouter.com/additional-resources/architecture/liquidity-model)
- [Cubist — Squid launches sub-second cross-chain swaps](https://cubist.dev/blog/squid-launches-sub-second-cross-chain-swaps-enabled-by-cubists-new-private-smart-contract-tech)
- [0xsquid/squid-types `src/rfq/index.ts`](https://github.com/0xsquid/squid-types/blob/main/src/rfq/index.ts) · [0xsquid/examples](https://github.com/0xsquid/examples)
- Verified source: [Blockscout Base, Spoke `0xfe91aAA1012B47499CfE8758874F2D2c52B22cD8`](https://base.blockscout.com/address/0xfe91aAA1012B47499CfE8758874F2D2c52B22cD8) · [Blockscout Base, `Create2Deployer`](https://base.blockscout.com/address/0x73c94A113D49Fc3d4C5733Dc195acf623F793f97)
