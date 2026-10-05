# Hyperlane warp routes — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; Robinhood Chain: no registry route)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the canonical `hyperlane-xyz/hyperlane-registry` (`deployments/warp_routes/*/*-config.yaml`, commit `09aa8356`, 2026-09-28) and `hyperlane-xyz/hyperlane-monorepo` (`solidity/contracts/token`, commit `c52b7280`). Topics and selectors recomputed as `keccak256(signature)` and matched against deployed route bytecode; every listed route address existence-checked with `eth_getCode` (all are EIP-1967 proxies, except the non-proxy routes marked below).
**Scope:** warp routes, Hyperlane's token bridges: **HypERC20Collateral** (lock and release), **HypERC20** (synthetic: burn and mint), **HypNative** (native ETH), **HypXERC20** and **HypXERC20Lockbox** (xERC20 burn and mint), **CrossCollateralRouter** (multi-token collateral) and the **CCTP routes** (USDC by Circle CCTP under a Hyperlane message). Any team can deploy a route, so the address lists are a floor: they hold the major registry routes on the seven chains and every route that was active in the pinned window. The messaging core (Mailbox, hooks, domains) is in [core.md](core.md).

A warp route is a set of router contracts, one per chain, that trust each other (`enrollRemoteRouter`). The user calls `transferRemote` on the source route. The route takes the tokens (lock, burn or CCTP burn), emits `SentTransferRemote`, and dispatches a message through the Mailbox. On the destination, `Mailbox.process` calls the destination route's `handle`, which emits `ReceivedTransferRemote` and releases or mints the tokens to the recipient.

Facts to know before indexing:

1. **The two warp events are generic.** `SentTransferRemote` and `ReceivedTransferRemote` have the same topic0 on every route type and every chain. Catch them from any emitter, then classify the emitter (§3–§10, or `mailbox()` / `token()` with `eth_call`).
2. **The link key is the Mailbox `messageId`**, taken from `DispatchId` in the source transaction and `ProcessId` in the destination transaction. The warp events carry no id. Pair a warp event with the Mailbox id event of the same transaction.
3. **The registry is incomplete.** In the pinned window, routes absent from the registry emitted 7 of 45 `SentTransferRemote` logs on Ethereum, 28 of 64 on Base and 9 of 12 on Polygon. Some of them dispatch through independent Mailboxes ([core.md](core.md) §12).

---

## 0. Route types, value movement and the flow

| Route type (registry `standard`) | Source leg in the same transaction | Destination leg in the same transaction |
|-----------------------------------|------------------------------------|------------------------------------------|
| Collateral (`EvmHypCollateral`, `HypERC20Collateral`) | ERC-20 `Transfer(user → route)`; the route holds the collateral. | ERC-20 `Transfer(route → recipient)`. |
| Synthetic (`EvmHypSynthetic`, `HypERC20`) | The route is the token: `Transfer(user → 0x0)` emitted by the route. | `Transfer(0x0 → recipient)` emitted by the route. |
| Native (`EvmHypNative`, `HypNative`) | Native value in `msg.value` (amount + gas fee); no ERC-20 row. | Internal native transfer to the recipient; no log. |
| xERC20 (`EvmHypXERC20`) | `xERC20.burn(user)`: `Transfer(user → 0x0)` on the xERC20 token. | `xERC20.mint`: `Transfer(0x0 → recipient)`. |
| xERC20 lockbox (`EvmHypXERC20Lockbox`) | `Transfer(user → route)`, lockbox deposit, then the xERC20 burn. | xERC20 mint to the route, lockbox withdraw, `Transfer(lockbox → recipient)`. |
| CrossCollateralRouter (`EvmHypCrossCollateralRouter`) | Like Collateral. `transferRemoteTo` can target a router of another token or the same chain. | Like Collateral. A **same-chain** transfer emits `ReceivedTransferRemote` with no `SentTransferRemote` and no Mailbox event. |
| CCTP routes (`USDC/mainnet-cctp*`) | `Transfer(user → route)`, then a CCTP burn (`DepositForBurn`, USDC `Transfer(→ 0x0)`). | Inside `Mailbox.process`: a CCTP `receiveMessage` mints USDC **directly to the recipient** (`Transfer(0x0 → recipient)`); the route moves no USDC. |

| Step | Call | Event(s), in log order (current source) | Notes |
|------|------|------------------------------------------|-------|
| **Source leg** | user → route `transferRemote` | token movement, `SentTransferRemote` (route), `Dispatch`, `DispatchId` (Mailbox), `InsertedIntoTree`, `GasPayment` | Older routes emit `SentTransferRemote` **after** the Mailbox and hook events (seen on the Base ezETH route). Do not rely on the order. |
| **Destination leg** | relayer → `Mailbox.process` → route `handle` | `Process`, `ProcessId` (Mailbox), `ReceivedTransferRemote` (route), token movement | The relayer is the transaction sender, not the user. |
| Rebalance | rebalancer → route `rebalance` | `CollateralMoved`, then the bridge's own events | Collateral leaves through an allowed bridge (CCTP, LayerZero OFT, ...). Not a user transfer. |
| LP exit | LP → route `withdraw` | ERC-4626 `Withdraw`, `Transfer(route → receiver)` | LP-enabled collateral routes only. |
| Refund / cancel / expiry | none | — | A failed delivery stays pending; there is no on-chain refund. |

**Decoding.** `recipient` is `bytes32` (topic2 of both warp events): the low 20 bytes on EVM chains, a full 32-byte key for Solana (`solanamainnet` domain 1399811149). `destination` / `origin` (topic1) are Hyperlane domains, equal to the chain id on the eight target chains ([core.md](core.md) §0).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Transfer events (emitter = the route)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd229aacb94204188fe8042965fa6b269c62dc5818b21238779ab64bdd17efeec` | `SentTransferRemote(uint32 indexed destination, bytes32 indexed recipient, uint256 amountOrId)` | **Source leg.** Emitted by the route (any emitter). `amountOrId` is the message amount (scaled, see §13.4). |
| `0xba20947a325f450d232530e5f5fce293e7963499d5309a07cee84a269f2f15a6` | `ReceivedTransferRemote(uint32 indexed origin, bytes32 indexed recipient, uint256 amountOrId)` | **Destination leg (payout).** Emitted by the route inside `handle`. |
| `0xb1e1b117ddf429b1b8a359fe0e978f0ae191c0f70e0babfea7acaad1b0ee8a2d` | `CollateralMoved(uint32 indexed domain, bytes32 recipient, uint256 amount, address indexed rebalancer)` | **Rebalance.** Collateral leaves the route through an allowed bridge to `domain`. Not a user transfer. |
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` | ERC-4626 LP deposit into an LP-enabled collateral route (collateral in, no message). |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` | ERC-4626 LP withdrawal (collateral out, no message). **Drain signal.** |
| `0x5d8bc849764969eb1bcc6d0a2f55999d0167c1ccec240a4f39cf664ca9c4148e` | `Donation(address sender, uint256 amount)` | Collateral added to an LP route without shares. |

### 1.2 Route admin events

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xc47cbcc588c67679e52261c45cc315e56562f8d0ccaba16facb9093ff9498799` | `IsmSet(address _ism)` | The route's ISM changed. **Controls which messages the route accepts.** |
| `0x4eab7b127c764308788622363ad3e9532de3dfba7845bd4f84c125a22544255a` | `HookSet(address _hook)` | The route's post-dispatch hook changed. |
| `0xc3de732a98b24a2b5c6f67e8a7fb057ffc14046b83968a2c73e4148d2fba978b` | `GasSet(uint32 domain, uint256 gas)` | Destination gas for a remote domain. |
| `0xbf9a9534339a9d6b81696e05dcfb614b7dc518a31d48be3cfb757988381fb323` | `FeeRecipientSet(address feeRecipient)` | Transfer-fee recipient changed. |
| `0xd6e2f80c31feccfd7c896d69ad9963871021131ff84f2a9828b40bad60dd8cb4` | `FeeHookSet(address feeHook)` | ERC-20 fee hook changed. |
| `0xe2cfaeba7e1fe770315538798648c0aed8b9d4c3e5096bf0a36b8185c1cd2f29` | `CrossCollateralRouterEnrolled(uint32 indexed domain, bytes32 indexed router)` | CrossCollateralRouter: a router that may send to or receive from this one. |
| `0x080702c2e9e59f89368b5aa4256101325de453b6c71535ac84afdedff8852e5c` | `CrossCollateralRouterUnenrolled(uint32 indexed domain, bytes32 indexed router)` | CrossCollateralRouter. |
| `0x86eee369bdd5e8620b595131597759ddadaf57f38cc5f5f76172ad2b60c9c1f4` | `DomainAdded(uint32 indexed hyperlaneDomain, uint32 circleDomain)` | CCTP route: Hyperlane domain to CCTP domain map. |
| `0xb57c8371d6ea920b3e40e9c8451448f643bcd1080cb0d4b76b5e9398ca608f9a` | `MaxFeePpmSet(uint256 maxFeePpm)` | CCTP v2 route: fast-transfer fee cap. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Route owner change. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | Route proxy implementation change. |

`enrollRemoteRouter` and `unenrollRemoteRouter` emit **no event**: a change of the trusted remote route is visible only as a call (§2.2).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 User functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x81b4e8b4` | `transferRemote(uint32 destination, bytes32 recipient, uint256 amountOrId)` | **Source-leg entry point**, every route type. Payable (gas fee; on HypNative also the amount). Returns `messageId`. |
| `0x51debffc` | `transferRemote(uint32 destination, bytes32 recipient, uint256 amountOrId, bytes hookMetadata, address hook)` | Older routes (for example the ezETH lockbox): custom hook overload. |
| `0xd9755d0f` | `transferRemoteTo(uint32 destination, bytes32 recipient, uint256 amount, bytes32 targetRouter)` | CrossCollateralRouter: send to a chosen enrolled router (another token or the same chain). |
| `0x8bd90b82` | `quoteTransferRemote(uint32 destination, bytes32 recipient, uint256 amount)` | `(address token, uint256 amount)[]` quotes: gas, fee, amount. |
| `0xf2ed8c53` | `quoteGasPayment(uint32 destinationDomain)` | `uint256` native gas quote. |
| `0x56d5d475` | `handle(uint32 origin, bytes32 sender, bytes message)` | **Destination entry point**, callable only by the Mailbox (and, on a CrossCollateralRouter, by enrolled local routers). |
| `0x6e553f65` | `deposit(uint256 assets, address receiver)` | ERC-4626 LP deposit (LP-enabled collateral routes). |
| `0xb460af94` | `withdraw(uint256 assets, address receiver, address owner)` | ERC-4626 LP withdrawal. |

### 2.2 Admin functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb49c53a7` | `enrollRemoteRouter(uint32 domain, bytes32 router)` | Owner. **No event**: watch the selector. Adds or replaces the trusted remote route. |
| `0xe9198bf9` | `enrollRemoteRouters(uint32[] domains, bytes32[] addresses)` | Owner. No event. |
| `0xefae508a` | `unenrollRemoteRouter(uint32 domain)` | Owner. No event. |
| `0x081954bc` | `enrollCrossCollateralRouters(uint32[] domains, bytes32[] routers)` | Owner (CrossCollateralRouter). Emits `CrossCollateralRouterEnrolled`. |
| `0x0e72cc06` | `setInterchainSecurityModule(address module)` | Owner. Emits `IsmSet`. |
| `0x3dfd3873` | `setHook(address hook)` | Owner. Emits `HookSet`. |
| `0x49d462ef` | `setDestinationGas(uint32 domain, uint256 gas)` | Owner. Emits `GasSet`. |
| `0xe74b981b` | `setFeeRecipient(address recipient)` | Owner. Emits `FeeRecipientSet`. |
| `0x92c18454` | `setFeeHook(address feeHook)` | Owner. Emits `FeeHookSet`. |
| `0x6a99c333` | `rebalance(uint32 domain, uint256 collateralAmount, address bridge)` | Allowed rebalancer. Moves collateral out through an allowed bridge. Emits `CollateralMoved`. |
| `0x0c979919` | `addRebalancer(address rebalancer)` | Owner. No event. |
| `0xfbaca44c` | `addBridge(uint32 domain, address bridge)` | Owner. No event. |
| `0xf83c1a6b` | `addDomain(uint32 hyperlaneDomain, uint32 circleDomain)` | Owner (CCTP route). Emits `DomainAdded`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner. Emits `OwnershipTransferred`. |

### 2.3 Views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2ead72f6` | `routers(uint32 domain)` | `bytes32` enrolled remote route. |
| `0x440df4f4` | `domains()` | `uint32[]` enrolled domains. |
| `0xfc0c546a` | `token()` | `address`: the collateral token, the route itself (synthetic), or `0x0` (native). Reverts on some older routes. |
| `0x996c6cc3` | `wrappedToken()` | `address`: the collateral or xERC20 token (older routes). |
| `0xd5438eae` | `mailbox()` | `address`: the Mailbox this route dispatches through. **Use it to tell canonical routes from routes on another Mailbox.** |
| `0x7f5a7c7b` | `hook()` | `address`. |
| `0xde523cf3` | `interchainSecurityModule()` | `address`. |

---

## 3. Routes — Ethereum mainnet (chain ID 1)

Mailbox `0xc005dc82818d67AF737725bD4bf75435d065D239`. Pinned window, any emitter: `SentTransferRemote` 45, `ReceivedTransferRemote` 82. Registry routes: the major routes of §11 plus every registry route active in the window. `Sent / Received` = `SentTransferRemote` / `ReceivedTransferRemote` logs of that route in the pinned window.

| Registry route | Symbol | Type | Route address | Collateral / token | Sent / Received |
|----------------|--------|------|---------------|--------------------|-----------------|
| USDC/mainnet-cctp | USDC | Collateral via CCTP v1 | `0xedCBAa585FD0F80f20073F9958246476466205b8` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 1 / 0 |
| USDC/mainnet-cctp-v2-standard | USDC | Collateral via CCTP v2 | `0x8c8D831E1e879604b4B304a2c951B8AEe3aB3a23` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 0 / 1 |
| USDC/mainnet-cctp-v2-fast | USDC | Collateral via CCTP v2 fast | `0x7A576Bb5291567cfDbB4585B1911CF7C9891ea07` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 0 / 0 |
| CROSS/moonpay, USDC/moonpay | USDC | CrossCollateral | `0xA9C9a8FB36Ce3e5ffBAC3757dA7141262723541F` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 15 / 18 |
| CROSS/moonpay, USDT/moonpay | USDT | CrossCollateral | `0xeB1b48b238E15A62e1858a601B6BfFdf41163AE3` | `0xdac17f958d2ee523a2206206994597c13d831ec7` | 10 / 24 |
| EZETH/renzo-prod | ezETH | xERC20 lockbox | `0xC59336D8edDa9722B4f1Ec104007191Ec16f7087` | `0xC8140dA31E6bCa19b287cC35531c2212763C2059` | 0 / 4 |
| oUSDT/production | USDT | xERC20 lockbox (VS) | `0x88AC0fC430130983c0DDEB4C22574056D8340Ca8` | `0x6D265C7dD8d76F25155F1a7687C693FDC1220D12` | 0 / 0 |
| oXAUT/production | XAUt | xERC20 lockbox | `0x9A9C33115455a929D3d821CEE4A01e38241bF375` | `0x0797c6f55f5c9005996A55959A341018cF69A963` | 0 / 1 |
| USDT/eni | USDT | Collateral | `0x291A485Fd288786728Ba34052b95DDb60278AB49` | `0xdac17f958d2ee523a2206206994597c13d831ec7` | 0 / 0 |
| USDC/aleo | USDC | Collateral | `0x78Ac7FECD1857f5BEEe98AB39096c9781F976D97` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 0 / 0 |
| ETH/aleo | ETH | Native | `0x38D447694f5c1f773ae3132cf93bF30B7Ec1Fa5A` | native ETH | 5 / 0 |
| USDC/eclipsemainnet | USDC | Collateral | `0xe1De9910fe71cC216490AC7FCF019e13a34481D7` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 0 / 0 |
| LITKEY/litchain | LITKEY | Collateral | `0x733BC1F0D76AB8f0AB7C1c8044ECc4720Cd402AD` | `0x4D4eb0E8B160f6EbF63cC6d36060ffec09301B42` | 0 / 0 |
| USDC/paradex | USDC | Collateral | `0x6912088890254E69970baEdB03284fB3D8fBCDA0` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 0 / 2 |
| DIME/paradex | DIME | Collateral | `0x7396b724a43C1d654a89B44996DA84d1E1a9B568` | `0xb32e10022ffbedfe10bc818a1c7e67d9d87e0fa7` | 2 / 3 |
| KROWN/krown | KROWN | Synthetic | `0xD198097db1C372ACbd3907df8A1BEd3c7d1B53CD` | the route is the token | 1 / 1 |
| LUNC/bsc-ethereum-solanamainnet-terraclassic | LUNC | Synthetic | `0xA4bc47a4C5461eB0E59A585a21A1222EF7544Ac6` | the route is the token | 0 / 1 |
| LYX/lukso | LYX | Synthetic | `0xC210B2cB65ed3484892167F5e05F7ab496Ab0598` | the route is the token | 1 / 0 |
| NES/bsc | NES | Synthetic | `0x863F08A3d3B14fbD3D42fFD061D0e290F7dBC538` | the route is the token | 0 / 0 |
| NEX/bsc | NEX | Collateral | `0xb71183f48F7f7789D40551149bE28a51f9A97F9A` | `0xf57D49646621F563b0B905aFc8336923AC569Ec5` | 1 / 0 |
| SEDA/base-ethereum | SEDA | Collateral | `0x8E1C6992621f1f647C79A297035B5484B9fb6864` | `0x14862c03A0cACcC1aB328B062E64e31B2a1afcd7` | 0 / 0 |
| SOLX/nitro | SOLX | Collateral | `0x261a172eB72D8D32837D123E8AcC4d2e44117195` | `0xe0B7AD7F8F26e2b00C8b47b5Df370f15F90fCF48` | 0 / 1 |
| USDC/coti-ethereum | USDC | Collateral | `0x6de5FaBC6B4663BD6BdBc064Bbb183E61aF1daDE` | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` | 0 / 3 |
| USDC/incentiv | USDC | Collateral | `0x8918b0186136130FE8e02bfB221f23cbBbCDDE07` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 0 / 1 |
| USDC/subtensor | USDC | Collateral | `0x3C43C421f08e2a48889eA3F75a747b7a7a366A0b` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 1 / 0 |
| USDT/electroneum | USDT | Collateral | `0x97B80b1d89d10E5d2c9396B0ea0BA2dAf917Dc96` | `0xdac17f958d2ee523a2206206994597c13d831ec7` | 0 / 1 |
| USDT/krown | USDT | Collateral | `0xE78fA49bE021e533cd8f6E10931b796D89cd80DD` | `0xdac17f958d2ee523a2206206994597c13d831ec7` | 1 / 2 |
| VRA/bsc-ethereum | VRA | Collateral | `0xde1bb600f24e9c6E49d51765fB836b070762e45D` | `0xF411903cbC70a74d22900a5DE66A2dda66507255` | 0 / 4 |
| stHYPER/bsc-ethereum | stHYPER | Rebase collateral | `0x9F6E6d150977dabc82d5D4EaaBDB1F1Ab0D25F92` | `0xa860e01Cc4A889BB2917EC97104510A2e1Ae0e53` | 0 / 1 |

**Active routes not in the registry** (`mailbox()` and `token()` read with `eth_call`; "reverts" = the older route version has no `token()`):

| Route | Mailbox | `token()` | Sent / Received |
|-------|---------|-----------|-----------------|
| `0xd11874d565f0b64083433f767f67b15eb110bc8b` | registry Mailbox | reverts; `wrappedToken()` = ARC `0x672fdba7055bddfa8fd6bd45b1455ce5eb97f499` | 2 / 0 |
| `0x01f80bb8e78e79881e8ec7832fb6c2c59f64e353` | independent `0x287cf56e5b1435ae59bf9ce6443f055a0321a063` | `0x9ca8530ca349c966fe9ef903df17a75b8a778927` | 3 / 2 |
| `0x39510fd11b2d9926f94204f35c665d2146e03d03` | independent `0xa9abc828378c9decd6268e6ddf298914ecba59cb` | `0x52076923f24daf4c9da90082b6384edcc4180646` | 1 / 2 |
| `0x6d785ea3102d40a4e094c93c8bb2fe31e292e1b2` | independent `0xa9abc828378c9decd6268e6ddf298914ecba59cb` | USDT `0xdac17f958d2ee523a2206206994597c13d831ec7` | 0 / 2 |
| `0x09ac387ae044f45eeb5d615f7c64dfb40f68c29c` | independent `0xa9abc828378c9decd6268e6ddf298914ecba59cb` | USDC `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` | 0 / 1 |
| `0x81c2813aa88f66bca1e55838045aaceb72febfc1` | independent `0x82a729a4c7b2aebddbfccf533e7b75c61c45c23c` | reverts | 0 / 5 |
| `0x9f1ff33209424841ddcf780158f9ecc37a0099f1` (not a proxy) | registry Mailbox | `0x0` (native) | 1 / 0 |
| `0x4ad2d363bce045a7df7c9069cb517cc803409bea` (not a proxy) | registry Mailbox | reverts | 0 / 1 |
| `0xa0407f73c16776ca60584cca9a4b15d96376e188` (not a proxy) | registry Mailbox | reverts | 0 / 1 |

## 4. Routes — Base (chain ID 8453)

Mailbox `0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D`. Pinned window, any emitter: `SentTransferRemote` 64, `ReceivedTransferRemote` 101. Registry routes: the major routes of §11 plus every registry route active in the window. `Sent / Received` = `SentTransferRemote` / `ReceivedTransferRemote` logs of that route in the pinned window.

| Registry route | Symbol | Type | Route address | Collateral / token | Sent / Received |
|----------------|--------|------|---------------|--------------------|-----------------|
| USDC/mainnet-cctp | USDC | Collateral via CCTP v1 | `0x5C4aFb7e23B1Dc1B409dc1702f89C64527b25975` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 0 / 0 |
| USDC/mainnet-cctp-v2-standard | USDC | Collateral via CCTP v2 | `0x33e94B6D2ae697c16a750dB7c3d9443622C4405a` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 1 / 1 |
| USDC/mainnet-cctp-v2-fast | USDC | Collateral via CCTP v2 fast | `0x31169ee5A8C0D680de74461d7B5394fFc7C3576B` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 0 / 2 |
| CROSS/moonpay, USDC/moonpay | USDC | CrossCollateral | `0x253821543C24623ecD3ceBCEd704359AF16CF38f` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 0 / 3 |
| CROSS/moonpay, USDT/moonpay | USDT | CrossCollateral | `0x7abBb4ea8a5895127500CF0C15830C9Eb9f61F96` | `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` | 0 / 0 |
| EZETH/renzo-prod | ezETH | xERC20 | `0x2552516453368e42705D791F674b312b8b87CD9e` | `0x2416092f143378750bb29b79eD961ab195CcEea5` | 1 / 0 |
| oUSDT/production | oUSDT | xERC20 (VS) | `0x4F0654395d621De4d1101c0F98C1Dba73ca0a61f` | `0x1217BfE6c773EEC6cc4A38b5Dc45B92292B6E189` | 4 / 0 |
| oXAUT/production | oXAUT | xERC20 | `0x0fcf8DAE34efB101e7dF535550370da4e53Ab960` | `0x30974f73A4ac9E606Ed80da928e454977ac486D2` | 0 / 0 |
| USDT/eni | USDT | Collateral | `0x3a669c00F7A041330646AC8AE89d74e104bd1363` | `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` | 0 / 0 |
| USDC/aleo | USDC | Collateral | `0xB46930ca998587A95D9Ee000FA73A071ADD56B64` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 0 / 0 |
| USDC/eclipsemainnet | USDC | Collateral | `0x37e637891A558B5b621723cbf8Fc771525f280C1` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 0 / 0 |
| LITKEY/litchain | LITKEY | Collateral | `0x9D132d5678253FD88f7DB51Ac2AC13FC40a63547` | `0xF732A566121Fa6362E9E0FBdd6D66E5c8C925E49` | 22 / 18 |
| USDC/paradex | USDC | Collateral | `0x0BA30bdd7D3C510De16c47385102c0B7068f4f33` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 3 / 4 |
| GPS/base-bsc | GPS | Collateral | `0x01efc19badCAC4EDaE0d75c5F344AcD0F7311722` | `0x0c1dc73159e30c4b06170f2593d3118968a0dca5` | 3 / 6 |
| KII/kiichain | KII | Synthetic | `0x3EBA6644819546C44Eb3e7c3A92f034f921dcA80` | the route is the token | 1 / 2 |
| MAGIC/abstract | MAGIC | Synthetic | `0xF1572d1Da5c3CcE14eE5a1c9327d17e9ff0E3f43` | the route is the token | 0 / 6 |
| MAT/matchain | MAT | Synthetic | `0xAb5061BebE14630a768D361BB43E7ca714C634E4` | the route is the token | 0 / 1 |
| NES/bsc | NES | Synthetic | `0x2E968fB88998a6303535Ac637C809119ECAd4a4b` | the route is the token | 0 / 0 |
| SEDA/base-ethereum | SEDA | Synthetic | `0x306aCd0c07c430AbBBb2e74Ef7bdE94F32A898c0` | the route is the token | 0 / 0 |
| USDC/appchain-base | USDC | Collateral | `0xF6B933267d0aC9e08c4904FB39fa047eD7b6a814` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 0 / 1 |
| USDC/electroneum | USDC | Collateral | `0xaaDF9558Cf103d394B22b18Ffbaa0D1c0778Ccfa` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 0 / 2 |
| USDC/subtensor | USDC | Collateral | `0x26af973A5b256F9B9bc0B1A3c566de1566568a87` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 1 / 2 |

**Active routes not in the registry** (`mailbox()` and `token()` read with `eth_call`; "reverts" = the older route version has no `token()`):

| Route | Mailbox | `token()` | Sent / Received |
|-------|---------|-----------|-----------------|
| `0xde0f17681123cbe998e7896b74a197937123b3d9` | registry Mailbox | USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | 12 / 13 |
| `0x54716a535c3b5616e3f0d4d5005fc4bb660cdf5f` | independent `0xfdd96df1b2d4354dbb1070815819db47469ca470` | USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | 8 / 14 |
| `0x176383016bb310c9f1c180dc6729d5e28104e602` | registry Mailbox | reverts | 6 / 14 |
| `0xe6522a891702cd2e8cc2a5182638c9da1dd44b22` | registry Mailbox | the route itself (synthetic) | 1 / 9 |
| `0x8a59bb7706317d07325c69521fbe6ecc3d880af0` | registry Mailbox | reverts; `wrappedToken()` = ARC `0x431151f26c48b4d4befc34048a0966bf960a0c50` | 0 / 2 |
| `0x12edac9b50f1014997c1bddad23df58b6d82de3b` | registry Mailbox | `0x1e925de1c68ef83bd98ee3e130ef14a50309c01b` | 0 / 1 |
| `0x7c475c87b8aa7609073e1be3d3ceb62bbbd5276a` | registry Mailbox | `0x6e236176d1b473bdb770cddf4d257b877f2da9db` | 1 / 0 |

## 5. Routes — Arbitrum One (chain ID 42161)

Mailbox `0x979Ca5202784112f4738403dBec5D0F3B9daabB9`. Pinned window, any emitter: `SentTransferRemote` 27, `ReceivedTransferRemote` 49. Registry routes: the major routes of §11 plus every registry route active in the window. `Sent / Received` = `SentTransferRemote` / `ReceivedTransferRemote` logs of that route in the pinned window.

| Registry route | Symbol | Type | Route address | Collateral / token | Sent / Received |
|----------------|--------|------|---------------|--------------------|-----------------|
| USDC/mainnet-cctp | USDC | Collateral via CCTP v1 | `0x8a82186EA618b91D13A2041fb7aC31Bf01C02aD2` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 0 / 0 |
| USDC/mainnet-cctp-v2-standard | USDC | Collateral via CCTP v2 | `0x4c19c653a8419A475d9B6735511cB81C15b8d9b2` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 0 / 2 |
| USDC/mainnet-cctp-v2-fast | USDC | Collateral via CCTP v2 fast | `0xE086378F7f0afd5C3ff95E10B5e7806a0901b33f` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 0 / 0 |
| CROSS/moonpay, USDT/moonpay | USD₮0 | CrossCollateral | `0x75a9297db5F0349fd1d6f4030953Fe17175e06d4` | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | 0 / 5 |
| CROSS/moonpay, USDC/moonpay | USDC | CrossCollateral | `0xeBC079D41C41a0ef7e54aa7Af867df9a621C9bE0` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 13 / 28 |
| EZETH/renzo-prod | ezETH | xERC20 | `0xB26bBfC6d1F469C821Ea25099017862e7368F4E8` | `0x2416092f143378750bb29b79eD961ab195CcEea5` | 2 / 0 |
| oUSDT/production | USDT | Collateral | `0x98d4DD4220Aa0Fe9251ccF7978c9B355D1be276a` | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | 0 / 0 |
| USDT/eni | USDT | Collateral | `0x92637DCE7F34b9e9b5741B9203F33EED7f71E5a4` | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | 0 / 0 |
| USDC/aleo | USDC | Collateral | `0x1FdA66FA15A261F01F1E09228D41bD0A806d7529` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 0 / 0 |
| USDC/eclipsemainnet | USDC | Collateral | `0xAd4350Ee0f9f5b85BaB115425426086Ae8384ebb` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 0 / 1 |
| LITKEY/litchain | LITKEY | Collateral | `0xc656E77E18d378DeED5051b26f750b325D6253C2` | `0xC7603786470F04D33E35f9E9B56bD0Ca8803fB95` | 0 / 0 |
| USDC/paradex | USDC | Collateral | `0xF5f93d26229482adCA3e42F84D08d549cF131658` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 1 / 5 |
| MAGIC/abstract | MAGIC | Collateral | `0x37687d638EA2D25Df5350D37d5BccBF7Fff1F2B3` | `0x539bdE0d7Dbd336b79148AA742883198BBF60342` | 6 / 0 |
| NES/bsc | NES | Synthetic | `0x8cAd676141FeadB6aCA5eF661E835d5957644033` | the route is the token | 0 / 0 |
| RCADE/arbitrum-bsc | RCADE | Collateral | `0x6720350f7e3323418c05645cD5d6bb055f4A7427` | `0x077574441C4F8763a37a2cFeE2ECb444aA60A15e` | 2 / 2 |
| USDC/subtensor | USDC | Collateral | `0x4337e529a4f6429668746db798416961c48F07BE` | `0xaf88d065e77c8cc2239327c5edb3a432268e5831` | 0 / 2 |

**Active routes not in the registry** (`mailbox()` and `token()` read with `eth_call`; "reverts" = the older route version has no `token()`):

| Route | Mailbox | `token()` | Sent / Received |
|-------|---------|-----------|-----------------|
| `0x5b93b4274325493ef91ce75cc98f4e66da2548c4` (the same address and implementation on Optimism) | registry Mailbox | reverts | 3 / 4 |

## 6. Routes — Optimism (chain ID 10)

Mailbox `0xd4C1905BB1D26BC93DAC913e13CaCC278CdCC80D`. Pinned window, any emitter: `SentTransferRemote` 5, `ReceivedTransferRemote` 5. Registry routes: the major routes of §11 plus every registry route active in the window. `Sent / Received` = `SentTransferRemote` / `ReceivedTransferRemote` logs of that route in the pinned window.

| Registry route | Symbol | Type | Route address | Collateral / token | Sent / Received |
|----------------|--------|------|---------------|--------------------|-----------------|
| USDC/mainnet-cctp | USDC | Collateral via CCTP v1 | `0xfB7681ECB05F85c383A5ce4439C7dF5ED12c77DE` | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 0 / 0 |
| USDC/mainnet-cctp-v2-standard | USDC | Collateral via CCTP v2 | `0x33e94B6D2ae697c16a750dB7c3d9443622C4405a` | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 0 / 0 |
| USDC/mainnet-cctp-v2-fast | USDC | Collateral via CCTP v2 fast | `0x4eFaacbf0D3d57b401Cb6B559e84b344448b0C30` | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 0 / 0 |
| EZETH/renzo-prod | ezETH | xERC20 | `0xacEB607CdF59EB8022Cc0699eEF3eCF246d149e2` | `0x2416092f143378750bb29b79eD961ab195CcEea5` | 0 / 0 |
| oUSDT/production | oUSDT | xERC20 (VS) | `0x7bD2676c85cca9Fa2203ebA324fb8792fbd520b8` | `0x1217BfE6c773EEC6cc4A38b5Dc45B92292B6E189` | 3 / 1 |
| USDT/eni | USDT | Collateral | `0x2EbFeC15f3Ff64E52af17c1c9a4aE9B7f6574298` | `0x94b008aA00579c1307B0EF2c499aD98a8ce58e58` | 0 / 0 |
| USDC/aleo | USDC | Collateral | `0x1FdA66FA15A261F01F1E09228D41bD0A806d7529` | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 0 / 0 |
| USDC/eclipsemainnet | USDC | Collateral | `0x02bFd67829317D666dc7dFA030F18eaCC12c2cfb` | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 0 / 1 |
| LITKEY/litchain | LITKEY | Collateral | `0x56aE521E18a7de66b2e3AcE3A0b71e716a61D34d` | `0x0633E91f64C22d4FEa53dbE6e77B7BA4093177B8` | 0 / 0 |

**Active routes not in the registry** (`mailbox()` and `token()` read with `eth_call`; "reverts" = the older route version has no `token()`):

| Route | Mailbox | `token()` | Sent / Received |
|-------|---------|-----------|-----------------|
| `0x5b93b4274325493ef91ce75cc98f4e66da2548c4` | registry Mailbox | reverts | 1 / 3 |
| `0x12edac9b50f1014997c1bddad23df58b6d82de3b` (the same address on Base) | registry Mailbox | `0x1e925de1c68ef83bd98ee3e130ef14a50309c01b` | 1 / 0 |

## 7. Routes — Polygon PoS (chain ID 137)

Mailbox `0x5d934f4e2f797775e53561bB72aca21ba36B96BB`. Pinned window, any emitter: `SentTransferRemote` 12, `ReceivedTransferRemote` 20. Registry routes: the major routes of §11 plus every registry route active in the window. `Sent / Received` = `SentTransferRemote` / `ReceivedTransferRemote` logs of that route in the pinned window.

| Registry route | Symbol | Type | Route address | Collateral / token | Sent / Received |
|----------------|--------|------|---------------|--------------------|-----------------|
| USDC/mainnet-cctp | USDC | Collateral via CCTP v1 | `0xa62F45662809f5F6535b58bae9A572a2EC4A1f84` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 0 / 1 |
| USDC/mainnet-cctp-v2-standard | USDC | Collateral via CCTP v2 | `0x33e94B6D2ae697c16a750dB7c3d9443622C4405a` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 0 / 0 |
| USDC/mainnet-cctp-v2-fast | USDC | Collateral via CCTP v2 fast | `0x07d89DE0F7E18c9bcAAE81F44aee9CA02EBeE872` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 0 / 0 |
| CROSS/moonpay, USDC/moonpay | USDC | CrossCollateral | `0x28a96f9928dB06317356caACd5641C4Fde4424C7` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 3 / 9 |
| CROSS/moonpay, USDT/moonpay | USDT0 | CrossCollateral | `0x766A80a7a6BBA555731DC1726DB5BFa030631270` | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` | 0 / 3 |
| USDT/eni | USDT | Collateral | `0x98e9738DF4A304A97124D3A360A70DeC6efc4f99` | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` | 0 / 0 |
| USDC/aleo | USDC | Collateral | `0x1FdA66FA15A261F01F1E09228D41bD0A806d7529` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 0 / 0 |
| USDC/eclipsemainnet | USDC | Collateral | `0xCb9F833f4d6D9Bb9767CDb25c487DA54D67731D6` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 0 / 0 |
| LITKEY/litchain | LITKEY | Synthetic | `0x5bEd1A06b26853360D9D1a6a27eaCE1b85206867` | the route is the token | 0 / 0 |
| KII/kiichain | KII | Synthetic | `0xEEC6574eAbBa52bac3f0277F2cD5Ac7e67197886` | the route is the token | 0 / 1 |
| USDC/subtensor | USDC | Collateral | `0x52fCcE3778D4Ea883a1F9F697D3710e470D32505` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 0 / 1 |

**Active routes not in the registry** (`mailbox()` and `token()` read with `eth_call`; "reverts" = the older route version has no `token()`):

| Route | Mailbox | `token()` | Sent / Received |
|-------|---------|-----------|-----------------|
| `0x53eef09d9e5ec83917788a182837da48b1c52a15` | registry Mailbox | reverts | 9 / 5 |

## 8. Routes — BNB Smart Chain (chain ID 56)

Mailbox `0x2971b9Aec44bE4eb673DF1B88cDB57b96eefe8a4`. Pinned window, any emitter: `SentTransferRemote` 78, `ReceivedTransferRemote` 227. BNB USDC and USDT have 18 decimals: see §13.4. Registry routes: the major routes of §11 plus every registry route active in the window. `Sent / Received` = `SentTransferRemote` / `ReceivedTransferRemote` logs of that route in the pinned window.

| Registry route | Symbol | Type | Route address | Collateral / token | Sent / Received |
|----------------|--------|------|---------------|--------------------|-----------------|
| CROSS/moonpay, USDT/moonpay | USDT | CrossCollateral | `0x050dcc964BCA53eF1A98A2347995cabC73cE25b9` | `0x55d398326f99059fF775485246999027B3197955` | 4 / 23 |
| CROSS/moonpay, USDC/moonpay | USDC | CrossCollateral | `0x6E66a10Ce72fBdFA45Ab7de3693321246E254123` | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | 9 / 113 |
| EZETH/renzo-prod | ezETH | xERC20 | `0xE00C6185a5c19219F1FFeD213b4406a254968c26` | `0x2416092f143378750bb29b79eD961ab195CcEea5` | 0 / 0 |
| oUSDT/production | USDT | Collateral | `0xc283600F0A84162C0a062f7273ABB1F8F111b40C` | `0x55d398326f99059fF775485246999027B3197955` | 0 / 0 |
| USDT/eni | USDT | Collateral | `0xC05617bc2490CB57a8db163b5551bb7E532695e3` | `0x55d398326f99059fF775485246999027B3197955` | 18 / 42 |
| USDC/aleo | USDC | Collateral | `0x5284D803a4563DC5eE83feA80c688b096d70eb75` | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | 0 / 0 |
| USDC/eclipsemainnet | USDC | Collateral | `0x1eebF9d94a5E707E30f18b9aB3295D963C111fb7` | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | 0 / 0 |
| LITKEY/litchain | LITKEY | Synthetic | `0x0bBeA6812fb3fcBcA126eDb558e551B3f1702026` | the route is the token | 18 / 22 |
| GPS/base-bsc | GPS | Synthetic | `0x9A4a67721573f2c9209DfFf972c52Be4E3F6642e` | the route is the token | 6 / 3 |
| KII/kiichain | KII | Synthetic | `0xEEC6574eAbBa52bac3f0277F2cD5Ac7e67197886` | the route is the token | 1 / 9 |
| LUNC/bsc-ethereum-solanamainnet-terraclassic | LUNC | Synthetic | `0x481095ecEd7A907e7f390b6226F53a66D379e6e2` | the route is the token | 1 / 3 |
| MAT/matchain | MAT | Synthetic | `0xFE2DD2d57a05F89438F3AEC94EaFA4070396bab0` | the route is the token | 0 / 1 |
| MITO/mitosis | MITO | Synthetic | `0x8e1e6BF7E13C400269987B65Ab2b5724b016CaEF` | the route is the token | 0 / 2 |
| NES/bsc | NES | Synthetic | `0x097acf27503753e77bCA940277806156C5925B81` | the route is the token | 0 / 0 |
| NEX/bsc | NEX | Synthetic | `0x365DE036A1F7dcCb621530d517133521debB2013` | the route is the token | 0 / 1 |
| PROM/bsc-polygon-prom | PROM | Collateral | `0x700b9322F6Cce0c8EFF4754bE9AcE88Ce6582821` | `0xaf53d56ff99f1322515e54fdde93ff8b3b7dafd5` | 2 / 0 |
| RCADE/arbitrum-bsc | RCADE | Synthetic | `0x6f0037C79d144d5B8E3E6f04E49FBb5f25fD508f` | the route is the token | 2 / 2 |
| USDT/bsc-prom | USDT | Collateral | `0xCf2D543345728da295CC5d3A3d54B117979643f8` | `0x55d398326f99059fF775485246999027B3197955` | 0 / 2 |
| USTC/bsc-ethereum-solanamainnet-terraclassic | USTC | Synthetic | `0xfC067fd98FD123fC2cAd72d040AF60a523274339` | the route is the token | 0 / 1 |
| VRA/bsc-ethereum | VRA | Collateral | `0xde1bb600f24e9c6E49d51765fB836b070762e45D` | `0x1d58e204ca59328007469A614522903d69dc0A4C` | 4 / 0 |
| WARD/ward-bsc | WARD | Synthetic | `0x6dc200b21894Af4660b549B678ea8df22BF7cfAc` | the route is the token | 5 / 0 |
| stHYPER/bsc-ethereum | stHYPER | Synthetic rebase | `0x6E9804a08092D8ba4E69DaCF422Df12459F2599E` | the route is the token | 1 / 0 |

**Active routes not in the registry** (`mailbox()` and `token()` read with `eth_call`; "reverts" = the older route version has no `token()`):

| Route | Mailbox | `token()` | Sent / Received |
|-------|---------|-----------|-----------------|
| `0x8612ed09749fbe0416bd11d0f37bc391cf8a1eb2` (not a proxy) | registry Mailbox | reverts | 3 / 1 |
| `0xc14babd49b35c4bfff11f669a28e0ba56ebf9024` | registry Mailbox | reverts | 1 / 2 |
| `0xaba2f1a67de552257c409cf6cc1e7ee8b9723023` (not a proxy) | registry Mailbox | `0x2feddd073ab42a334999830c2199d0ec8c19479c` | 2 / 0 |
| `0xd1f5f1613853f5e12ac25ca4b9130d1a71c67807` | registry Mailbox | reverts | 1 / 0 |

## 9. Routes — Avalanche C-Chain (chain ID 43114)

Mailbox `0xFf06aFcaABaDDd1fb08371f9ccA15D73D51FeBD6`. Pinned window, any emitter: `SentTransferRemote` 0, `ReceivedTransferRemote` 0. The routes below have code; none was active in the window. Registry routes: the major routes of §11 plus every registry route active in the window. `Sent / Received` = `SentTransferRemote` / `ReceivedTransferRemote` logs of that route in the pinned window.

| Registry route | Symbol | Type | Route address | Collateral / token | Sent / Received |
|----------------|--------|------|---------------|--------------------|-----------------|
| USDC/mainnet-cctp | USDC | Collateral via CCTP v1 | `0x0E8Bc62865F539889fe7d8537F2ed6db5aa0F677` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | 0 / 0 |
| USDC/mainnet-cctp-v2-standard | USDC | Collateral via CCTP v2 | `0x33e94B6D2ae697c16a750dB7c3d9443622C4405a` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | 0 / 0 |
| USDC/mainnet-cctp-v2-fast | USDC | Collateral via CCTP v2 fast | `0xCB35d7730843F770625bE36A0E4228c17fDcBC09` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | 0 / 0 |
| oXAUT/production | oXAUT | xERC20 | `0x118b30d28e5dB274f2376910038F66b1C33bD00a` | `0x30974f73A4ac9E606Ed80da928e454977ac486D2` | 0 / 0 |
| USDC/aleo | USDC | Collateral | `0x1FdA66FA15A261F01F1E09228D41bD0A806d7529` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | 0 / 0 |
| USDC/eclipsemainnet | USDC | Collateral | `0x252833ad2daa5BCb7C251Aa8E12ce97D6Bd4765E` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | 0 / 0 |
| LITKEY/litchain | LITKEY | Synthetic | `0xa38Fce8bf2fA38a97749332724b9db3FF44F006D` | the route is the token | 0 / 0 |
## 10. Robinhood Chain (chain ID 4663) — core deployed, no registry warp route

The registry lists the full Hyperlane core on Robinhood Chain ([core.md](core.md) §10) but **no warp route**: no `*-config.yaml` under `deployments/warp_routes/` names the chain (registry commit `09aa8356`). The pinned window holds one route transfer, from a route outside the registry:

| Route | Mailbox | Token | Sample |
|-------|---------|-------|--------|
| `0xa880b6e6511daf5a0bdde96ee8b36d8004d9d7ed` (21,225 bytes, not a proxy) | registry Mailbox `0x3a867fCfFeC2B790970eeBDC9023E75B0a172aa7` | `0xe8729dc9dca85167e06b7e9c66a58b22457c5f30` (symbol `AEVA`, 18 decimals) | tx `0x488bfa12b9fd6cb560facc316a64bdb60a91c9619a30a310f3af4621a6d021f9`: `Transfer(user → route)`, `SentTransferRemote` to domain 2383, `Dispatch`, `DispatchId`, `ProtocolFeePaid`, `InsertedIntoTree` |

Domain 2383 is not in the registry; its chain is unverified. Pinned window on Robinhood Chain: `SentTransferRemote` 1, `ReceivedTransferRemote` 0.

**Arc (chain ID 5042):** the registry lists the core on Arc ([core.md](core.md) §10b) but no file in `deployments/warp_routes/` names Arc (registry commit `fe66faf5`, 2026-10-05).

---

## 11. Cross-chain summary (major registry routes; ✅ = route address with code, — = not in the route)

| Route | ETH | Base | Arb | OP | Poly | BNB | Avax | Robin |
|-------|-----|------|-----|----|------|-----|------|-------|
| USDC/mainnet-cctp (CCTP v1) | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| USDC/mainnet-cctp-v2-standard | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| USDC/mainnet-cctp-v2-fast | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| CROSS/moonpay (USDC and USDT) | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | — |
| EZETH/renzo-prod | ✅ lockbox | ✅ | ✅ | ✅ | — | ✅ | — | — |
| oUSDT/production | ✅ lockbox | ✅ | ✅ | ✅ | — | ✅ | — | — |
| USDT/eni | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| USDC/aleo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| USDC/eclipsemainnet | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| LITKEY/litchain | ✅ | ✅ | ✅ | ✅ | ✅ synthetic | ✅ synthetic | ✅ synthetic | — |

Route addresses differ per chain, except a few CREATE2 routes (for example USDC/mainnet-cctp-v2-standard `0x33e94B6D2ae697c16a750dB7c3d9443622C4405a` on Base, Optimism, Polygon and Avalanche, and USDC/aleo `0x1FdA66FA15A261F01F1E09228D41bD0A806d7529` on four chains). The registry holds 526 route entries on the seven chains (Ethereum 172, Base 90, BNB 85, Arbitrum 76, Polygon 50, Optimism 37, Avalanche 16); this file lists the major and the active ones.

---

## 12. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Registry routes (all 116 listed in §3–§9) | EIP-1967 proxies: 113 with a 2,882 or 2,840-byte TransparentUpgradeableProxy runtime, 2 with 855 bytes, 1 with 2,921 bytes | EIP-1967 impl slot set on every one (read on 2026-09-29). Implementations differ per route and per chain. | Each route's own ProxyAdmin and `owner()`, chosen by the route deployer (not read per route). |
| Non-proxy routes | Plain contracts | Full bytecode, no EIP-1967 slot: Ethereum `0x9f1ff33209424841ddcf780158f9ecc37a0099f1`, `0x4ad2d363bce045a7df7c9069cb517cc803409bea`, `0xa0407f73c16776ca60584cca9a4b15d96376e188`; BNB `0x8612ed09749fbe0416bd11d0f37bc391cf8a1eb2`, `0xaba2f1a67de552257c409cf6cc1e7ee8b9723023`; Robinhood Chain `0xa880b6e6511daf5a0bdde96ee8b36d8004d9d7ed`. | `owner()` only. |

Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`, `OwnershipTransferred`, `IsmSet` and calls to `enrollRemoteRouter` on the routes you monitor. A route's security is its own ISM (or the Mailbox default ISM when it sets none): an owner who changes the ISM or enrolls a new remote router can mint or release the route's collateral.

---

## 13. Detection invariants & gotchas

1. **Catch the warp events from any emitter, then classify.** Use `mailbox()` to keep routes on the registry Mailbox, and `token()` / `wrappedToken()` for the asset. A large `ReceivedTransferRemote` on a collateral route is a release of real collateral; on a synthetic route it is a mint.
2. **`SentTransferRemote` has a non-Hyperlane twin.** The rebalancing bridge `TokenBridgeOft` (LayerZero OFT under a Hyperlane interface) declares `SentTransferRemote(uint32 indexed destination, bytes32 indexed recipient, uint256 amount)`: the same topic0, with no Mailbox message. A `SentTransferRemote` without a `DispatchId` in the same transaction is not a Hyperlane transfer.
3. **Link by `messageId`, not by order.** Older routes emit `SentTransferRemote` after `Dispatch`; current source emits it before. Join source and destination with `DispatchId` / `ProcessId` and keep the warp event of the same transaction.
4. **The event amount is in message units.** `SentTransferRemote` emits the scaled outbound amount and `ReceivedTransferRemote` emits the message amount; the token moves `amount × scale`. Example: on BNB the CROSS/moonpay USDC route has 18 decimals and registry `scale` = 1 / 10^12, so the events carry 6-decimal amounts while the BEP-20 transfer carries 18 decimals. Value the transfer from the token movement in the same transaction.
5. **Same-chain CrossCollateral transfers have no message.** `transferRemoteTo` with the local domain calls the target router directly: `ReceivedTransferRemote` (origin = local domain), no `SentTransferRemote`, no `Dispatch`/`Process`.
6. **CCTP routes pay out through CCTP.** On the destination the USDC is minted by CCTP straight to the recipient inside `Mailbox.process` (sample: Base tx `0x5e901a4bb46333cb7885c276b88631eed62e8782c99bd50a8007322311522e44`, `MintAndWithdraw` and USDC `Mint` to the recipient, then `ReceivedTransferRemote`). A CCTP monitor also sees these transfers; do not count them twice. See [../cctp/README.md](../cctp/README.md).
7. **Collateral also leaves without a user transfer.** `CollateralMoved` (rebalance), ERC-4626 `Withdraw` (LP exit) and owner actions move collateral. A drain monitor on a collateral route must cover all three and the plain ERC-20 `Transfer` out of the route.
8. **Admin triggers.** `IsmSet`, `HookSet`, `Upgraded`, `OwnershipTransferred`, `FeeRecipientSet`, `CrossCollateralRouterEnrolled`, and the event-less calls `enrollRemoteRouter` (`0xb49c53a7`), `enrollRemoteRouters` (`0xe9198bf9`), `addRebalancer` (`0x0c979919`), `addBridge` (`0xfbaca44c`).
9. **The recipient is `bytes32`.** Take the low 20 bytes on EVM destinations. Solana recipients (domain 1399811149) are 32-byte public keys; the sample Ethereum send in [core.md](core.md) §16 went to Solana.
10. **The same address can be different routes.** The Polygon route `0x53eef09d9e5ec83917788a182837da48b1c52a15` is also the implementation behind the BNB route `0xc14babd49b35c4bfff11f669a28e0ba56ebf9024`. Key on `(chain, address)`.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Warp route topics (any route, any chain) =====
TOPIC_SENT_TRANSFER_REMOTE       = '\xd229aacb94204188fe8042965fa6b269c62dc5818b21238779ab64bdd17efeec'
TOPIC_RECEIVED_TRANSFER_REMOTE   = '\xba20947a325f450d232530e5f5fce293e7963499d5309a07cee84a269f2f15a6'
TOPIC_COLLATERAL_MOVED           = '\xb1e1b117ddf429b1b8a359fe0e978f0ae191c0f70e0babfea7acaad1b0ee8a2d'
TOPIC_ERC4626_WITHDRAW           = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_ISM_SET                    = '\xc47cbcc588c67679e52261c45cc315e56562f8d0ccaba16facb9093ff9498799'
TOPIC_HOOK_SET                   = '\x4eab7b127c764308788622363ad3e9532de3dfba7845bd4f84c125a22544255a'
TOPIC_FEE_RECIPIENT_SET          = '\xbf9a9534339a9d6b81696e05dcfb614b7dc518a31d48be3cfb757988381fb323'
TOPIC_CROSS_COLLATERAL_ENROLLED  = '\xe2cfaeba7e1fe770315538798648c0aed8b9d4c3e5096bf0a36b8185c1cd2f29'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors =====
SEL_TRANSFER_REMOTE              = '\x81b4e8b4'
SEL_TRANSFER_REMOTE_WITH_HOOK    = '\x51debffc'
SEL_TRANSFER_REMOTE_TO           = '\xd9755d0f'
SEL_HANDLE                       = '\x56d5d475'
SEL_ENROLL_REMOTE_ROUTER         = '\xb49c53a7'
SEL_ENROLL_REMOTE_ROUTERS        = '\xe9198bf9'
SEL_UNENROLL_REMOTE_ROUTER       = '\xefae508a'
SEL_SET_ISM                      = '\x0e72cc06'
SEL_REBALANCE                    = '\x6a99c333'
SEL_ADD_REBALANCER               = '\x0c979919'
SEL_ADD_BRIDGE                   = '\xfbaca44c'
SEL_MAILBOX                      = '\xd5438eae'
SEL_TOKEN                        = '\xfc0c546a'
-- ===== USDC CCTP routes =====
ETH_WARP_USDC_CCTP_V1            = '\xedcbaa585fd0f80f20073f9958246476466205b8'
BASE_WARP_USDC_CCTP_V1           = '\x5c4afb7e23b1dc1b409dc1702f89c64527b25975'
ARB_WARP_USDC_CCTP_V1            = '\x8a82186ea618b91d13a2041fb7ac31bf01c02ad2'
OP_WARP_USDC_CCTP_V1             = '\xfb7681ecb05f85c383a5ce4439c7df5ed12c77de'
POLY_WARP_USDC_CCTP_V1           = '\xa62f45662809f5f6535b58bae9a572a2ec4a1f84'
AVAX_WARP_USDC_CCTP_V1           = '\x0e8bc62865f539889fe7d8537f2ed6db5aa0f677'
ETH_WARP_USDC_CCTP_V2            = '\x8c8d831e1e879604b4b304a2c951b8aee3ab3a23'
BASE_WARP_USDC_CCTP_V2           = '\x33e94b6d2ae697c16a750db7c3d9443622c4405a'
ARB_WARP_USDC_CCTP_V2            = '\x4c19c653a8419a475d9b6735511cb81c15b8d9b2'
OP_WARP_USDC_CCTP_V2             = '\x33e94b6d2ae697c16a750db7c3d9443622c4405a'
POLY_WARP_USDC_CCTP_V2           = '\x33e94b6d2ae697c16a750db7c3d9443622c4405a'
AVAX_WARP_USDC_CCTP_V2           = '\x33e94b6d2ae697c16a750db7c3d9443622c4405a'
ETH_WARP_USDC_CCTP_V2_FAST       = '\x7a576bb5291567cfdbb4585b1911cf7c9891ea07'
BASE_WARP_USDC_CCTP_V2_FAST      = '\x31169ee5a8c0d680de74461d7b5394ffc7c3576b'
ARB_WARP_USDC_CCTP_V2_FAST       = '\xe086378f7f0afd5c3ff95e10b5e7806a0901b33f'
OP_WARP_USDC_CCTP_V2_FAST        = '\x4efaacbf0d3d57b401cb6b559e84b344448b0c30'
POLY_WARP_USDC_CCTP_V2_FAST      = '\x07d89de0f7e18c9bcaae81f44aee9ca02ebee872'
AVAX_WARP_USDC_CCTP_V2_FAST      = '\xcb35d7730843f770625be36a0e4228c17fdcbc09'
-- ===== CROSS/moonpay (CrossCollateralRouter) =====
ETH_WARP_CROSS_USDC              = '\xa9c9a8fb36ce3e5ffbac3757da7141262723541f'
ETH_WARP_CROSS_USDT              = '\xeb1b48b238e15a62e1858a601b6bffdf41163ae3'
BASE_WARP_CROSS_USDC             = '\x253821543c24623ecd3cebced704359af16cf38f'
BASE_WARP_CROSS_USDT             = '\x7abbb4ea8a5895127500cf0c15830c9eb9f61f96'
ARB_WARP_CROSS_USDC              = '\xebc079d41c41a0ef7e54aa7af867df9a621c9be0'
ARB_WARP_CROSS_USDT              = '\x75a9297db5f0349fd1d6f4030953fe17175e06d4'
POLY_WARP_CROSS_USDC             = '\x28a96f9928db06317356caacd5641c4fde4424c7'
POLY_WARP_CROSS_USDT             = '\x766a80a7a6bba555731dc1726db5bfa030631270'
BNB_WARP_CROSS_USDC              = '\x6e66a10ce72fbdfa45ab7de3693321246e254123'
BNB_WARP_CROSS_USDT              = '\x050dcc964bca53ef1a98a2347995cabc73ce25b9'
-- ===== ezETH (Renzo) and oUSDT =====
ETH_WARP_EZETH_LOCKBOX           = '\xc59336d8edda9722b4f1ec104007191ec16f7087'
BASE_WARP_EZETH                  = '\x2552516453368e42705d791f674b312b8b87cd9e'
ARB_WARP_EZETH                   = '\xb26bbfc6d1f469c821ea25099017862e7368f4e8'
OP_WARP_EZETH                    = '\xaceb607cdf59eb8022cc0699eef3ecf246d149e2'
BNB_WARP_EZETH                   = '\xe00c6185a5c19219f1ffed213b4406a254968c26'
ETH_WARP_OUSDT_LOCKBOX           = '\x88ac0fc430130983c0ddeb4c22574056d8340ca8'
BASE_WARP_OUSDT                  = '\x4f0654395d621de4d1101c0f98c1dba73ca0a61f'
ARB_WARP_OUSDT                   = '\x98d4dd4220aa0fe9251ccf7978c9b355d1be276a'
OP_WARP_OUSDT                    = '\x7bd2676c85cca9fa2203eba324fb8792fbd520b8'
BNB_WARP_OUSDT                   = '\xc283600f0a84162c0a062f7273abb1f8f111b40c'
-- ===== Busiest routes outside the registry (pinned window) =====
BASE_WARP_UNLISTED_USDC          = '\xde0f17681123cbe998e7896b74a197937123b3d9'
POLY_WARP_UNLISTED               = '\x53eef09d9e5ec83917788a182837da48b1c52a15'
RH_WARP_UNLISTED_AEVA            = '\xa880b6e6511daf5a0bdde96ee8b36d8004d9d7ed'
```

---

## 15. Verification & sources

How each constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `hyperlane-monorepo/solidity/contracts/token` (`libs/TokenRouter.sol`, `libs/MovableCollateralRouter.sol`, `libs/LpCollateralRouter.sol`, `CrossCollateralRouter.sol`, `TokenBridgeCctpBase.sol`, `TokenBridgeCctpV2.sol`, `TokenBridgeOft.sol`) and `client/Router.sol`, `client/GasRouter.sol`, `client/MailboxClient.sol`. Each event topic and the transfer and admin selectors were found in deployed implementation bytecode on Ethereum (CROSS USDC `0xcaad30a0eed46e8803db01dc84643c4cb6839e9e`, CROSS USDT `0x8adb1f5b190e98f71e15958173a230ab901afc4d`, CCTP v1 `0xfde1c465f63ee79645d2c4c864db995b5883be9b`, CCTP v2 fast `0xba5967deec16d4e806bdf02c52afc55e61ad59c2`, oUSDT lockbox `0x01fc684fb27bbed8ba3c17b62b9299c96edc3d2e`, ezETH lockbox `0x2289b07f486347a5ddd53954c36b87b7ad280261`, HypNative `0x3fbc926e59ea0ec964983139df5f822f13d5311a`).
- **Addresses:** every registry route config parsed for the eight chains; 116 route addresses on the seven chains existence-checked with `eth_getCode` (all have code, all EIP-1967 proxies), and their 39 collateral token addresses checked the same way. Unregistered active routes classified with `mailbox()`, `token()` and `wrappedToken()`.
- **Sample transactions read:** Ethereum send `0xfb299b17db0e06f677d0d7f935821a08738682613d6dac83b684997dba1bc027` (CROSS USDC to Solana); Ethereum receive `0x955037563771deab94c3681051b6c10b771bde2d41d3108848792d28cdf94d5a` (CROSS USDT from domain 747474); Base ezETH send `0xda61f229811f4816410c880b40f2ebe0e418443ca46b47829675f9a6da5e810d` (burn to `0x0`; `SentTransferRemote` after the Mailbox events); Base CCTP v2 fast receive `0x5e901a4bb46333cb7885c276b88631eed62e8782c99bd50a8007322311522e44`; Robinhood Chain send `0x488bfa12b9fd6cb560facc316a64bdb60a91c9619a30a310f3af4621a6d021f9`.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC** (any emitter): `SentTransferRemote` — Ethereum 45, Base 64, Arbitrum 27, Optimism 5, Polygon 12, BNB 78, Avalanche 0, Robinhood Chain 1. `ReceivedTransferRemote` — Ethereum 82, Base 101, Arbitrum 49, Optimism 5, Polygon 20, BNB 227, Avalanche 0, Robinhood Chain 0. Per-route counts are in §3–§10. A 0 is a finding of this window only.

Authoritative sources:
- Canonical repositories — [hyperlane-xyz/hyperlane-registry](https://github.com/hyperlane-xyz/hyperlane-registry) (`deployments/warp_routes/`) · [hyperlane-xyz/hyperlane-monorepo](https://github.com/hyperlane-xyz/hyperlane-monorepo) (`solidity/contracts/token`)
- Explorers — [Etherscan CROSS USDC route](https://etherscan.io/address/0xa9c9a8fb36ce3e5ffbac3757da7141262723541f) · [Basescan ezETH route](https://basescan.org/address/0x2552516453368e42705d791f674b312b8b87cd9e) · [Robinhood Chain Blockscout route](https://robinhoodchain.blockscout.com/address/0xa880b6e6511daf5a0bdde96ee8b36d8004d9d7ed)
