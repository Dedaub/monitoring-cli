# Meridian Perps — Topics, Selectors, Addresses (Robinhood Chain)

**Status:** verified against live RPC on Robinhood Chain (4663) and the Sourcify-verified sources of `ExchangeGateway` and `MeridianUSD` (solc 0.8.28, exact match) on 2026-10-30.
**Scope:** the Meridian perpetuals exchange (the successor of Ethereal): the `ExchangeGateway` proxy, its eight delegatecall modules, the `merUSD` collateral token and the third-party LP vault. **Robinhood Chain (4663) only.** Topics and selectors are chain-agnostic. Addresses are network-specific. The prediction-market product is in [predict.md](predict.md).

Meridian runs an off-chain order book with an on-chain settlement contract. Users deposit to the `ExchangeGateway`. Sequencers submit signed off-chain actions in batches with `processActions(bytes[])`: deposit finalization, order matches, funding, withdrawals, liquidations. Every action result is an event on the gateway, so **trades, funding and liquidations are visible on-chain** (unlike a pure rollup).

The gateway is a UUPS proxy. Its implementation holds only dispatch code. It `delegatecall`s eight module contracts that it finds in its own address registry (`RegistryRecordUpdated`). **All events, including the module events, are emitted by the gateway address.** Collateral is **merUSD** (18 dec), a 1:1 wrapper of USDe (`0x5d3a1Ff2…ef34`, Ethena's OFT). Exchange balances use 9 decimals ("D9"). Prices come from **Pyth Lazer** (`PythLazerUpdated`; verifier `0xACeA761c…F481`, see [pyth/pro.md](../pyth/pro.md)).

---

## 0. Contract families

| Contract | Role | Proxy? |
|----------|------|--------|
| **ExchangeGateway** | Single entry and event emitter. Deposits, withdrawals, `processActions`, admin. EIP-712 domain `Meridian` v1. | UUPS (Solady), EIP-1967 |
| ActionHandler module | `processActions`, signer link/revoke, withdraw initiation. | delegatecall target (21,627 B) |
| CollateralManager module | `deposit*`, `finalizeWithdraw`, `rescueFunds`, fee claims. | delegatecall target (10,742 B) |
| ExchangeConfig module | Tokens, sequencers, fee schedules, pauses, Pyth config. | delegatecall target (10,284 B) |
| PerpEngine module | Order matching, funding, PnL, delisting. | delegatecall target (21,517 B) |
| PerpEngineAdmin module | Product registration and updates. | delegatecall target (6,004 B) |
| Liquidation module | Liquidations. | delegatecall target (20,343 B) |
| Deleverage / DeleverageWithCompensation modules | Auto-deleveraging. | delegatecall targets (17,922 B / 20,308 B) |
| **merUSD** (`MeridianUSD`) | ERC-20 "Meridian USD". `wrap`/`unwrap` 1:1 against the default wrapped token (USDe). | UUPS (Solady), EIP-1967 |
| Meridian LP vault | "Meridian Liquidity Provider", `AccountableAsyncRedeemVault` (ERC-4626 + async redeem), asset USDe. Third-party curated; trades from exchange account `0x2f46…56B2`. | Not a proxy (18,511 B) |

---

## 1. Topics (chain-agnostic — all emitted by the ExchangeGateway address)

### 1.1 Collateral and account flow

| topic0 | Event |
|--------|-------|
| `0x46da1b0e33ef2092122ede41f24c033eef76439dfa22b2301f1efec6d6b94405` | `DepositInitiated(address indexed sender, bytes32 indexed subaccount, address token, uint256 amount, uint128 fee)` |
| `0x390706e9b004ebbb7dd99fba03d4f95a51dd699ca825b015aff3d84c0a052c0e` | `DepositFinalized(address indexed sender, bytes32 indexed subaccount, address token, uint256 amount, uint128 fee, uint256 balance, bytes32 initiatedTxHash, uint32 initiatedLogIdx, uint64 messageIdx)` |
| `0x3df896d1329a3df70d706a667a750a3bb2baca5fb930f07279319c5df7296d5b` | `AccountReferred(address indexed account, bytes32 referralCode)` |
| `0x22705f0084db947c6291da7786d8fbdf84a8703b9a5d764e81948f06bba6bd86` | `WithdrawInitiated(address indexed account, bytes32 indexed subaccount, bytes32 indexed withdrawDigest, address token, uint256 amount, uint128 fee, uint64 initiatedTimestamp, uint64 messageIdx)` |
| `0xbd9ea22eb88ecf5b83475cf3b3e65bb8922d917b0f28c0eb98a28be67179d38a` | `WithdrawFinalized(address indexed account, bytes32 indexed withdrawDigest, address token, uint256 amount, uint128 fee, uint64 finalizedTimestamp, bytes32 destinationAddress, uint32 destinationEndpointId)` |
| `0x6401e8b3df9aa8a33e16ea55cd86575e78b276bb08761817150a3329caec1731` | `FundsRescued(address indexed account, bytes32 withdrawDigest)` — owner-only rescue of a stuck withdrawal |
| `0x73b9739b6cdc68367a5e7238f0da61e4fda735932f2ca57647ebf176ea407508` | `ConvertFinalized(address indexed account, bytes32 indexed subaccount, bytes32 indexed convertDigest, address fromToken, address toToken, uint128 fromAmount, uint128 toAmount, uint128 fee, uint64 finalizedTimestamp, uint64 messageIdx)` |
| `0xa474c89bbc344a369396cf6d8a1eedb5c35beb7dc7e00c2e69d663b1c5bdee36` | `FeeAccrued(address indexed account, bytes32 indexed subaccount, address token, uint256 feeAmount, uint256 balance, uint64 messageIdx)` |
| `0xa6270cf6d6bf39ce9b0414e9e74f84287604b2c4b4cc651cffbc6c617f84cc72` | `FeesClaimed(address indexed account, bytes32 indexed subaccount, address token, uint256 amount)` |
| `0x00ac044a939772289ba100a72299cb8ecb48bc0ce87b4ea568075bb50b688590` | `FeesConverted(address indexed account, bytes32 indexed subaccount, address fromToken, address toToken, uint256 amount)` |
| `0x8de079c195ccd26194a88bc98ac30e46ba1e908374730547cb9e8afe3b70c084` | `SignerLinked(address indexed sender, bytes32 indexed subaccount, address indexed signer, uint64 linkedTimestamp, uint64 messageIdx)` |
| `0x8223037ee45f2c2d5dc3be42fdf569ee53f163c0c46669e5d82b2f7461783bd9` | `SignerLinkRejected(address indexed sender, bytes32 indexed subaccount, address indexed signer, uint64 rejectedTimestamp, uint64 messageIdx)` |
| `0x0540b694696af56b0f69f7113313c89b532e9cbe4082ced479d1d236fe629d1b` | `SignerRevoked(address indexed sender, bytes32 indexed subaccount, address indexed signer, uint64 revokedTimestamp, uint64 messageIdx)` |
| `0xc61a34b02f64f9b75e136664946eb6a4204cdbd383064b33ac427757e00f3331` | `SignerRevokeRejected(address indexed sender, bytes32 indexed subaccount, address indexed signer, uint64 rejectedTimestamp, uint64 messageIdx)` |
| `0xbf212ba11b203b26ee32795ed0bb76ebfc8f4a95b343bc839d879639a8ed3e4c` | `ActionsProcessed(uint64 firstActionId, uint64 lastActionId, uint256 length)` — one per sequencer batch |
| `0xa2036101b620b7c7f6766c56944afd2838999ad2284e249d2c828a822b845003` | `Ping(address indexed sender, uint64 timestamp)` — permissionless heartbeat |

### 1.2 Trading (PerpEngine, Liquidation, Deleverage modules)

| topic0 | Event |
|--------|-------|
| `0x230b0c22b351760fe01c981ccc8e374df9e9a789d6776116551a9180b499f73a` | `PerpOrderMatched(uint32 indexed productId, address indexed maker, address indexed taker, bytes32 makerSubaccount, bytes32 takerSubaccount, uint8 makerSide, uint8 takerSide, uint128 fillQuantity, uint128 price, uint128 makerFee, uint128 takerFee, uint64 messageIdx)` |
| `0x55ec828ad85b3d89e094ae1d99a4388c0ab77cafa463e1b4f6016223d2ed64fd` | `PerpProductFundingUpdated(uint32 indexed productId, int256 fundingUsd, int256 cumulativeFundingUsd, uint64 messageIdx)` |
| `0x868a91625e681fd3cc477fc3046c572a0c1002ead916f22389c719a3283bf16b` | `PerpFundingRealized(address indexed account, bytes32 indexed subaccount, uint32[] productIds, int256 realizedFundingUsd, uint64 messageIdx)` |
| `0x641d32db578133881f8e9d969fec55b805e3e73cc0b29f2802ba93ce00bc01d5` | `PerpPnlRealized(address indexed account, bytes32 indexed subaccount, uint32 indexed productId, int128 costDelta, uint64 messageIdx)` |
| `0x1677064c2b5706482c9d20bf7570ed0c22b170d98889611218c9f63485eb81d4` | `PositionLiquidated(uint32 indexed productId, address indexed account, bytes32 indexed subaccount, uint8, int128, uint128, uint64)` — 63 logs since deployment |
| `0x68223d04c5143d156bbd2d83a11b7a575daf5368d52570cda2c013cb2769fe9d` | `PositionDeleveraged(uint32 indexed productId, address indexed account, bytes32 indexed subaccount, int128, int128, uint128, uint64)` — not yet emitted |
| `0x0dcf0555ad14e7b5a10599a3850a4cd6e3704ba9910fac09d5b39730c85ee5c1` | `PositionTransferred(uint32 indexed productId, uint8 indexed engineType, address accountFrom, bytes32 subaccountFrom, address accountTo, bytes32 subaccountTo, int128 amount)` |
| `0x89683c580b9f9cab86d54f96c7f2dbcedd1a05e074e9b130bf7868ca7b6291f3` | `PerpFillNotionalMismatch(uint64 id, uint128 externalValue, uint128 internalValue, uint128 tolerance)` |
| `0x5c9ce697fe371dfb87874a70bcbe455a3793ceccc57835bedc1a3a7105c1869d` | `PerpProductPositionFeeUpdated(uint32 indexed productId, uint128 positionFeeDeltaUsd, uint128 cumulativePositionFeeUsd, uint256 liquidatorCreditAmount, uint64 messageIdx)` |
| `0xa4e7c6dbd6b80dbdd5ac96841e2662410cf112f5b3b3883a539066f2a63894a5` | `PerpProductRegistered(uint32 indexed productId, bytes32 baseTokenName, bytes32 quoteTokenName)` |
| `0x8bf0f76cefb6d5a14dd48e997b3d40c0d198864d60405a84b3bf1c5178d7438c` | `PerpProductStatusUpdated(uint32 indexed productId, uint8 status)` |
| `0x9a033e4b410fedca37112ef716c88f363be46d11de6016a1f0625e35cc761b66` | `PerpProductUpdated(uint32 indexed productId)` |
| `0xfd7d00bf7dced3b5461c8b6b0a218f98069c941f96cf523da5c38b9f983c3e7b` | `PerpProductUpdateInitiated(uint32 indexed productId)` |
| `0x6f075df11503cd74643c492909a6f56bf7225f6d53af0921842c6466caaf2f89` | `PerpProductUpdateFinalized(uint32 indexed productId, uint64 messageIdx)` |
| `0x7d0eea6a464ea372aae016221c83be72149ab8922d0a53d9098d96f88daf84bf` | `PerpProductPythFeedIdUpdated(uint32 indexed productId, uint32 pythFeedId)` — **oracle feed change** |
| `0xf8665c3b6f683a0806d1f577fe43855a5ff930f692ecbfcd2a7959d07dfd3fdb` | `PerpProductDelistInvoked(uint32 indexed productId)` |
| `0x3822699498411c1b1e329cb26ddc47287432c55ed60a49893418e5f59214ac3f` | `PerpProductDelistInitiated(uint32 indexed productId, uint256 expiryPrice, uint64 messageIdx)` |
| `0x0cad00c6a24e4ca7701bcc25f171e90b88a60ac7832f9528403c0894de1e6304` | `PerpProductDelistFinalized(uint32 indexed productId, uint256 expiryPrice, uint64 messageIdx)` |
| `0x471d341cd5b21d53213bc30c67ef8c734620cb4637ce478a9796b77adcfc7bb7` | `PerpProductDelistPositionSettlement(address indexed account, bytes32 indexed subaccount, uint32 indexed productId, int128 size, int128 realizedPnl, uint64 messageIdx)` |

Live sample (blocks 101,800,000–101,824,352): `FeeAccrued` 163, `PerpOrderMatched` 162, `ActionsProcessed` 137, `PerpProductFundingUpdated` 13, `ConvertFinalized` 2, `WithdrawInitiated` 1, `WithdrawFinalized` 1.

### 1.3 Admin and configuration

| topic0 | Event |
|--------|-------|
| `0xf593f886229ed3e6aa72c1f0b6bfb9d2688ec6c7654ddb84ffd86f2e91ff0813` | `RegistryRecordUpdated(bytes32 indexed name, address indexed record)` — **module swap = code change** |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed oldOwner, address indexed newOwner)` |
| `0xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d` / `0xfa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92` | `OwnershipHandoverRequested(address indexed)` / `OwnershipHandoverCanceled(address indexed)` (Solady) |
| `0x3db650cbaed68f5d5708fee569e4e3c7493f1fdebba21d1025924940336f593c` | `ExchangePauseUpdated(address indexed account, bool isPaused)` — **emergency pause** |
| `0x071f159924c97723131f06154a022b0aae952620b188fd5c08d1e3cd78d5f896` | `EmergencyPauserUpdated(address indexed pauser, bool enabled)` |
| `0xf1eaebc06e30ebf137e6ceb4e30da3b559889b36af843bac9311db9c36f68d0b` | `SequencerAdded(address indexed sequencer)` |
| `0x65cc197fd699db876319e374dc4b8117a40f5a65a313e0c87dc388c423e01c20` | `SequencerRemoved(address indexed sequencer)` |
| `0xc3fa2c62af2e1997e7e46b34cf2b52805a5b446a9b09b26c4bbc2fd46433043b` | `SequencerPausedUpdated(address indexed sequencer, bool paused)` |
| `0x662cc3305b9b4ea3a5fd06717cdaece79b6ac0a7734fd44eabe0f37951dc587c` | `TokenAdded(bytes32 indexed tokenName, address tokenAddress)` |
| `0x2aada7c835843a942d6bae43540591b084921c87edbb049c55d49d1144242794` | `TokenUpdated(bytes32 indexed tokenName, address tokenAddress)` |
| `0xe63fed861569a9d11223064361de84eb5a42b48b3091ae4cafb299f5fa8c69c1` | `TokenPromoted(bytes32 indexed tokenName, address tokenAddress)` |
| `0x3afbc119e23990903d2ef3fdf9210a7b06b5f6f85438b0edfcfbf630ad594fcc` | `TokenRemoved(bytes32 indexed tokenName, address tokenAddress)` |
| `0xd961ad62ec74636d9f47bf4922a7cb96381d598cdb7eb0a9557513944fdaa400` | `PythLazerUpdated(address pythLazer, uint64 maxAge)` — **oracle source change** |
| `0x42d094e542cf1d223ec5f17025b58f295bff1c685129e584ec012a05167479f9` | `RescueDelayUpdated(uint64 rescueDelay)` |
| `0x0d4de5cd7f05b154b7f42e4f1dd68f5c27ea0edaf9bd084309201cfa52e85926` | `ClaimerUpdated(address indexed claimer, bool granted)` |
| `0xee1f6015d865c5c41fe8842cd4ae122e6bba3d346a5caf0ad05c9a5e671a8874` | `DelegateDepositorUpdated(address indexed account, bool granted)` |
| `0x71b7c9097252c5f0f2bf761fc78da5e8aa8da529691a320b8b447a2affde68e3` | `DelegateDepositMaxBatchSizeUpdated(uint16 delegateDepositMaxBatchSize)` |
| `0xd57939805d33a784c01e4503ab4bdd9e2d3a8623c3b862e326ef3be3c0b98518` | `FeeCollectorUpdated(address indexed account, bytes32 indexed subaccount)` |
| `0x23285086efbf0ed6e7442eed352c09065c2e786de0d4b0b9d4d90c4c245add30` | `LiquidatorUpdated(address indexed account, bytes32 indexed subaccount)` |
| `0x7bf80d62633d84c37d5e338ba88ba6407baa926905ab5f0fd574210f80868517` / `0xf5a56d2b3c8806064b5531636b083c2453cf936f80e52b19b9b9f4c181d7f499` | `FeeScheduleAdded(uint32 indexed id)` / `FeeScheduleUpdated(uint32 indexed id)` |
| `0x5aa9313d41000bc617881b3e15a7e519969f0307bacd0ac2d1e119f8da447002` | `ActionExpiryBufferUpdated(uint8 indexed action, uint64 buffer)` |
| `0x96f51efb13cba47a6fcb8a0acf2d02e41f542d644373186a701815a4f2e4dd78` | `LzEndpointIdUpdated(uint32 indexed lzEndpointId)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` (Solady) |

### 1.4 merUSD (`0xad22…f009`)

| topic0 | Event |
|--------|-------|
| `0x29b3b451f9779df34ec8a67ec6c96fa910b17a579a66b7428d94f481be6900d9` | `Wrapped(address indexed account, address indexed token, uint256 amount)` — **merUSD minted** 1:1 for USDe |
| `0x742cbb4a6bddd5e23aa0c14356065c236bdbc921cddb7f1f763161eb2030f3ef` | `Unwrapped(address indexed account, address indexed token, uint256 amount)` — **merUSD burned**, USDe out |
| `0x5702ed4ef40441acd729b1bd1976931e64e99d9a5ce6eb544a1cbba8141fb407` | `WrappedTokenUpdated(address indexed token, bool oldEnabled, bool newEnabled)` — **backing asset allow-list** |
| `0x2b58d3dcc21eafeda2e7b9f75fdb13371b995a7de0861a5309dadcd35ed7aa33` | `DefaultWrappedTokenUpdated(address indexed oldToken, address indexed newToken)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` / `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Transfer` / `Approval` (ERC-20) |
| `0xbc7cd75a…d38a` / `0x8be0079c…57e0` | `Upgraded` / `OwnershipTransferred` |

### 1.5 Meridian LP vault (`0x24b8…F9d`, `AccountableAsyncRedeemVault`)

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` |
| `0x1fdc681a13d8c5da54e301c7ce6542dcde4581e4725043fdab2db12ddc574506` | `RedeemRequest(address indexed controller, address indexed owner, uint256 indexed requestId, address sender, uint256 assets)` |
| `0x4dd5187225a2ae5f5ea35ca7b1732180f848cc4b6f7dce34b4c5e9f384d77dec` | `RedeemClaimable(address indexed controller, uint256 indexed requestId, uint256 assets, uint256 shares)` |
| `0x91f628e8c7a6f75792ac4b71145861594f59fa4439e803548a394011b6c6bc2b` | `CancelRedeemRequest(address indexed controller, address indexed receiver, uint256 requestId, address sender)` |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` |
| `0x8dd4664ff532261941b00d8312d1764002e0de40af594821e7a4c08e4f0b8c70` / `0x48e891cea1a36b8bc4f1fb9fb7ae5508bf0edfee67aaeb354f1cfb8f62d68c82` | `LockAssets(address indexed caller, uint256 assets)` / `ReleaseAssets(address indexed caller, uint256 assets)` |
| `0xc5217903bd71390e046be1c1ee589f3af533c8fe5b67ee0a7dade2f8a853badd` | `AllowedSet(address indexed account, bool allowed)` |

---

## 2. Function signatures (chain-agnostic)

### 2.1 ExchangeGateway — user and sequencer

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x60f06a44` | `deposit(bytes32,address,uint256,bytes32)` | `(subaccount, token, amount, referralCode)`. Native units. |
| `0x05d625d3` | `depositUsd(bytes32,uint256,bytes32)` | Deposit the default wrapped USD (USDe); the gateway wraps it to merUSD. |
| `0xd9a3b28f` | `depositOnBehalf((address,bytes32,bytes32,uint256)[],bytes32)` | Delegate depositors only. |
| `0xf7bfc18b` | `finalizeWithdraw(address,bytes32)` | payable. `(account, withdrawDigest)`. Caller = the account, a claimer or the owner. Pays out after the sequencer initiated it; can route cross-chain via LayerZero OFT. |
| `0x7bc8a752` | `processActions(bytes[])` | payable. Sequencer batch. |
| `0x7dfaf882` | `processActionsDryRun(bytes[],uint256)` | payable. Simulation. |
| `0xe943587e` | `finalizeRevokeLinkedSigner((address,address,bytes32,uint64,uint64))` | Owner. |
| `0x5c46ff99` / `0xadb46a51` | `claimFees(address,uint256)` / `convertFees(address,address,uint256)` | Fee collector account or owner. |
| `0x5c36b186` | `ping()` | Permissionless. |
| `0x12815776` | `getAccountBalance(address,bytes32,address)` | view. D9. |
| `0x378756a9` | `getPerpPosition(address,bytes32,uint32)` | view. `(int128,uint128,int128,uint128)`. |
| `0x1ae10bc5` | `getPerpProduct(uint32)` | view. |
| `0x155bf4e2` | `getToken(bytes32)` | view. `(name, tokenAddress, depositEnabled, withdrawEnabled, removeProtected, depositCapacity, minDeposit, withdrawFee, depositFee, oftAddress, backingToken)`. |
| `0xe34940db` | `getExchangeTokens()` | view. 18 token names. |
| `0x6c07748a` | `getExchangePythLazer()` | view. `(address, uint64 maxAge)`. |
| `0xe5c0070c` / `0x85c1dce6` | `getAccountPendingWithdraw(address,bytes32)` / `getAccountPendingDeposit(address,bytes32)` | view. |

### 2.2 ExchangeGateway — admin (owner = Safe unless noted)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | Owner. |
| `0xed70c641` | `updateRegistryRecord(bytes32,address)` | Owner. Swaps a module. |
| `0xac9650d8` | `multicall(bytes[])` | Owner. Self-delegatecall batch. |
| `0x51858e27` / `0x4a4e3bd5` | `emergencyPause()` / `emergencyUnpause()` | Pause: owner or emergency pauser. Unpause: owner. |
| `0xcf6b00cf` | `rescueFunds(address,bytes32)` | Owner. After `rescueDelay`. |
| `0x2d6fa5da` / `0xf705ef1d` / `0xbdfa5d20` / `0x224e7462` | `addToken(bytes32,address,address,address)` / `updateToken((bytes32,uint256,uint256,uint128,uint128,bool,bool))` / `promoteToken(bytes32,address,address)` / `removeToken(bytes32)` | Owner. |
| `0x8a336231` / `0x6989ca7c` / `0x01070a55` | `addSequencer(address)` / `removeSequencer(address)` / `updateSequencerPaused(address,bool)` | Owner. |
| `0xf21366e6` | `updatePythLazer(address,uint64)` | Owner. Oracle source. |
| `0x83159974` | `updatePerpProductPythFeedId(uint32,uint32)` | Owner. Oracle feed per product. |
| `0xeb5e326e` / `0x4cff0dec` / `0x5be3f47a` / `0x5f267d46` | `registerPerpProduct(…)` / `updatePerpProduct(…)` / `activatePerpProduct(uint32)` / `delistPerpProduct(uint32)` | Owner. |
| `0x9cf306c6` / `0x5043eaea` | `addEmergencyPauser(address)` / `removeEmergencyPauser(address)` | Owner. |
| `0xf9882152` / `0xe4873aca` | `updateLiquidator(address,bytes32)` / `updateFeeCollector(address,bytes32)` | Owner. |
| `0x1b308685` | `updateRescueDelay(uint64)` | Owner. |
| `0xf2fde38b` / `0x25692962` / `0xf04e283e` | `transferOwnership(address)` / `requestOwnershipHandover()` / `completeOwnershipHandover(address)` | Solady Ownable. |

### 2.3 merUSD

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xbf376c7a` | `wrap(address,uint256)` | Pull USDe, mint merUSD 1:1. Only the default wrapped token. |
| `0x39f47693` | `unwrap(address,uint256)` | Burn merUSD, send USDe 1:1. |
| `0xdc18dde7` / `0xcc6c3c6a` | `setWrappedToken(address,bool)` / `setDefaultWrappedToken(address)` | Owner. |
| `0xbcc79d57` / `0x64fb065b` | `defaultWrappedToken()` / `isWrappedToken(address)` | view. |

---

## 3. Addresses — Robinhood Chain (chain ID 4663)

All verified with `eth_getCode` on 2026-10-30. Gateway and merUSD deployed by `0x39C647fdd8524c69be3E05A754bD63E02b019D75` at blocks 48,038,093 / 48,037,972 (implementations).

| Role | Address | One-liner |
|------|---------|-----------|
| **ExchangeGateway** | `0xD540F47F214dC7D6D244E62A6aE7e06B586Ef44A` | Proxy, entry point and event emitter. Holds the merUSD collateral. |
| **merUSD** | `0xad221259d4a1f2d7376dc1012c561bc86640f009` | "Meridian USD", 18 dec. Supply 1,509,974.88 on 2026-10-30. |
| ACTION_HANDLER module | `0xeb9a61e37a28828e84d97e1487d66b444800a280` | Registry record. |
| COLLATERAL_MANAGER module | `0x719256070f9ec31dfa8df58791fdb80602e431a4` | Registry record. |
| EXCHANGE_CONFIG module | `0xc334010fdd465e5d7b758ec27f90094574de4183` | Registry record. |
| PERP_ENGINE module | `0x94e37b0a9e16e6efff842a9e373f0aa2edca0fc8` | Registry record. |
| PERP_ENGINE_ADMIN module | `0x14c899f08c26af5db8b33cbb4a01fce7898b2a20` | Registry record. |
| LIQUIDATION module | `0x03fff44b0d7192be942098bf69017cbb293121b0` | Registry record. |
| DELEVERAGE module | `0x4cd414a3c1d17d8d9ecea6b7628da790dc733966` | Registry record. |
| DELEVERAGE_WITH_COMPENSATION module | `0x5842d29f7266cb0eb327258a3b4fb03c2f8c7bf1` | Registry record. |
| Owner Safe | `0xf8067d8ca90b8510ce8ade1eec24b7260eafa5f7` | Safe 1.4.1, 2-of-5. Owns gateway and merUSD. |
| Fee collector Safe | `0xff68fda91b0e785b4aee674d3b428c4ab6d8eaa7` | Safe 1.4.1, 1-of-1; subaccount `primary`. |
| Liquidator account | `0x15982b91cfbcb0ef69d8d4c4c98c0003881917f7` | EOA; subaccount `primary`. |
| Sequencer | `0x39f7e2936316f99e578489509c2db036f384e574` | `SequencerAdded`. |
| Delegate depositors | `0x721f512fe6fbf2c4a814e8d25055ea3071abecb1`, `0xc15ddebe99b8edf14e6b79f44db0c026114ac6b7` | `DelegateDepositorUpdated(true)`. |
| Withdraw claimer | `0x673c47b6ed2b34276e521a163998485f22875f1c` | `ClaimerUpdated(true)`. May call `finalizeWithdraw` for any account. |
| Meridian LP vault | `0x24b84023c8e4Da635be228C380C09bfE5271BF9d` | Sourcify-verified `AccountableAsyncRedeemVault`, asset USDe. |
| LP vault exchange account | `0x2f46C3FCe6BdA596c2771BCA618C4f69aE3E56B2` | Trades the vault's liquidity on the gateway. |
| USDe (backing) | `0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34` | Ethena USDe OFT. Not a Meridian contract. |
| Pyth Lazer verifier | `0xACeA761c27A909d4D3895128EBe6370FDE2dF481` | `getExchangePythLazer()`; Pyth contract. |

Exchange tokens (`getExchangeTokens()`): USD, BTC, ETH, SOL, HYPE, XAUUSD, XAU, XAGUSD, XAG, SPYUSD, SPY, QQQUSD, QQQ, NEAR, ZEC, VVV, ENA, LIT. Only `USD` maps to an on-chain token (merUSD, backing USDe). The others are book entries. `getNextPerpProductId()` = 14.

## 4. Cross-chain summary

| Chain (ID) | ExchangeGateway | merUSD | Modules | LP vault |
|------------|-----------------|--------|---------|----------|
| Robinhood Chain (4663) | `0xD540…F44A` | `0xad22…f009` | 8 | `0x24b8…F9d` |
| Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Arc | — | — | — | — |

`eth_getCode` returns `0x` for the gateway, merUSD, the ActionHandler and PerpEngine modules and the LP vault on all eight other chains (2026-10-30). Ethereal (chain 5064014), the predecessor venue, is not a target chain.

## 5. Proxies

| Contract | Pattern | Current implementation | History | Upgrade auth |
|----------|---------|------------------------|---------|--------------|
| **ExchangeGateway** | UUPS (Solady), ERC1967Proxy (163 B) | `0x0f17d8468c49d6c80e4ee10cc87a767085a4b9a8` (`ExchangeGateway`) | one `Upgraded` at block 48,038,123 | `onlyOwner` (Safe 2-of-5) |
| **merUSD** | UUPS (Solady), ERC1967Proxy (163 B) | `0x9a5c0ca8138923bf3788579fb48dabb0339bbbde` (`MeridianUSD`) | one `Upgraded` at block 48,038,002 | `onlyOwner` (Safe 2-of-5) |
| Modules (8) | plain contracts (impl slot 0) | — | swapped through `updateRegistryRecord` | `onlyOwner` |
| LP vault | not a proxy | — | — | — |

Both proxies have the same 163-byte code. Admin and beacon slots are zero. **The gateway can change logic in two ways:** `Upgraded` (implementation) and `RegistryRecordUpdated` (module). Only the eight initial `RegistryRecordUpdated` logs exist (blocks 48,038,396–48,038,606).

## 6. Detection invariants & gotchas

1. **One emitter for everything.** All perp, collateral, liquidation and admin events come from `0xD540…F44A`, even though eight module contracts hold the code. Do not watch the module addresses for logs.
2. **Deposits are two-phase.** `DepositInitiated` (on-chain transfer in) → `DepositFinalized` (sequencer credit, carries `initiatedTxHash` + `initiatedLogIdx`). Withdrawals too: `WithdrawInitiated` (sequencer, keyed by `withdrawDigest`) → `WithdrawFinalized` (`finalizeWithdraw` by the account, a claimer or the owner).
3. **Units.** `deposit*` amounts are native token units. Exchange balances, fees and `claimFees` amounts are D9. merUSD and USDe are 18 dec. `PerpOrderMatched.price` and `fillQuantity` are fixed-point exchange units.
4. **Collateral = merUSD at the gateway.** USDe sits in the merUSD contract, merUSD sits in the gateway. A drain shows as merUSD leaving the gateway or USDe leaving merUSD. `Unwrapped` with no matching `WithdrawFinalized` is suspicious.
5. **Cross-chain withdrawals.** `WithdrawFinalized.destinationEndpointId` ≠ 0 means a LayerZero OFT send; `destinationAddress` is `bytes32`.
6. **Liquidations are on-chain.** `PositionLiquidated` (63 logs to date) shares its emitter with `PerpOrderMatched`. `PositionLiquidated` and `PositionDeleveraged` signatures were recovered by `keccak256` matching (module source is not published); parameter names are unknown.
7. **Oracle changes.** `PythLazerUpdated` and `PerpProductPythFeedIdUpdated` change the price source. The current `maxAge` raw value is 605,100.
8. **Weak Safes.** The fee-collector Safe is 1-of-1. The prediction-market owner Safe is also 1-of-2 (see [predict.md](predict.md)).
9. **`Ping` is spam-able.** Anyone can call `ping()`. Do not treat `Ping` as sequencer liveness.
10. **Topic collisions.** `Deposit`/`Withdraw`/`RedeemRequest` on the LP vault are standard ERC-4626/7540 topics. `DepositInitiated` here (`0x46da…`) differs from Arcus `DepositInitiated` (`0x4127…`). `Initialized(uint64)` is shared with every OZ-v5/Solady contract.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MER_DEPOSIT_INITIATED       = '\x46da1b0e33ef2092122ede41f24c033eef76439dfa22b2301f1efec6d6b94405'
TOPIC_MER_DEPOSIT_FINALIZED       = '\x390706e9b004ebbb7dd99fba03d4f95a51dd699ca825b015aff3d84c0a052c0e'
TOPIC_MER_WITHDRAW_INITIATED      = '\x22705f0084db947c6291da7786d8fbdf84a8703b9a5d764e81948f06bba6bd86'
TOPIC_MER_WITHDRAW_FINALIZED      = '\xbd9ea22eb88ecf5b83475cf3b3e65bb8922d917b0f28c0eb98a28be67179d38a'
TOPIC_MER_FUNDS_RESCUED           = '\x6401e8b3df9aa8a33e16ea55cd86575e78b276bb08761817150a3329caec1731'
TOPIC_MER_CONVERT_FINALIZED       = '\x73b9739b6cdc68367a5e7238f0da61e4fda735932f2ca57647ebf176ea407508'
TOPIC_MER_FEE_ACCRUED             = '\xa474c89bbc344a369396cf6d8a1eedb5c35beb7dc7e00c2e69d663b1c5bdee36'
TOPIC_MER_FEES_CLAIMED            = '\xa6270cf6d6bf39ce9b0414e9e74f84287604b2c4b4cc651cffbc6c617f84cc72'
TOPIC_MER_ACTIONS_PROCESSED       = '\xbf212ba11b203b26ee32795ed0bb76ebfc8f4a95b343bc839d879639a8ed3e4c'
TOPIC_MER_PERP_ORDER_MATCHED      = '\x230b0c22b351760fe01c981ccc8e374df9e9a789d6776116551a9180b499f73a'
TOPIC_MER_FUNDING_UPDATED         = '\x55ec828ad85b3d89e094ae1d99a4388c0ab77cafa463e1b4f6016223d2ed64fd'
TOPIC_MER_FUNDING_REALIZED        = '\x868a91625e681fd3cc477fc3046c572a0c1002ead916f22389c719a3283bf16b'
TOPIC_MER_PNL_REALIZED            = '\x641d32db578133881f8e9d969fec55b805e3e73cc0b29f2802ba93ce00bc01d5'
TOPIC_MER_POSITION_LIQUIDATED     = '\x1677064c2b5706482c9d20bf7570ed0c22b170d98889611218c9f63485eb81d4'
TOPIC_MER_POSITION_DELEVERAGED    = '\x68223d04c5143d156bbd2d83a11b7a575daf5368d52570cda2c013cb2769fe9d'
TOPIC_MER_POSITION_TRANSFERRED    = '\x0dcf0555ad14e7b5a10599a3850a4cd6e3704ba9910fac09d5b39730c85ee5c1'
TOPIC_MER_REGISTRY_RECORD_UPDATED = '\xf593f886229ed3e6aa72c1f0b6bfb9d2688ec6c7654ddb84ffd86f2e91ff0813'
TOPIC_MER_EXCHANGE_PAUSE_UPDATED  = '\x3db650cbaed68f5d5708fee569e4e3c7493f1fdebba21d1025924940336f593c'
TOPIC_MER_SEQUENCER_ADDED         = '\xf1eaebc06e30ebf137e6ceb4e30da3b559889b36af843bac9311db9c36f68d0b'
TOPIC_MER_PYTH_LAZER_UPDATED      = '\xd961ad62ec74636d9f47bf4922a7cb96381d598cdb7eb0a9557513944fdaa400'
TOPIC_MER_PYTH_FEED_ID_UPDATED    = '\x7d0eea6a464ea372aae016221c83be72149ab8922d0a53d9098d96f88daf84bf'
TOPIC_MER_TOKEN_ADDED             = '\x662cc3305b9b4ea3a5fd06717cdaece79b6ac0a7734fd44eabe0f37951dc587c'
TOPIC_MERUSD_WRAPPED              = '\x29b3b451f9779df34ec8a67ec6c96fa910b17a579a66b7428d94f481be6900d9'
TOPIC_MERUSD_UNWRAPPED            = '\x742cbb4a6bddd5e23aa0c14356065c236bdbc921cddb7f1f763161eb2030f3ef'
TOPIC_MERUSD_WRAPPED_TOKEN_UPDATED= '\x5702ed4ef40441acd729b1bd1976931e64e99d9a5ce6eb544a1cbba8141fb407'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- ===== Selectors (chain-agnostic) =====
SEL_MER_DEPOSIT                   = '\x60f06a44'
SEL_MER_DEPOSIT_USD               = '\x05d625d3'
SEL_MER_DEPOSIT_ON_BEHALF         = '\xd9a3b28f'
SEL_MER_FINALIZE_WITHDRAW         = '\xf7bfc18b'
SEL_MER_PROCESS_ACTIONS           = '\x7bc8a752'
SEL_MER_RESCUE_FUNDS              = '\xcf6b00cf'
SEL_MER_EMERGENCY_PAUSE           = '\x51858e27'
SEL_MER_UPDATE_REGISTRY_RECORD    = '\xed70c641'
SEL_MER_UPDATE_PYTH_LAZER         = '\xf21366e6'
SEL_MERUSD_WRAP                   = '\xbf376c7a'
SEL_MERUSD_UNWRAP                 = '\x39f47693'
SEL_UPGRADE_TO_AND_CALL           = '\x4f1ef286'
-- ===== Addresses (Robinhood Chain 4663) =====
RH_MER_EXCHANGE_GATEWAY           = '\xd540f47f214dc7d6d244e62a6ae7e06b586ef44a'
RH_MER_MERUSD                     = '\xad221259d4a1f2d7376dc1012c561bc86640f009'
RH_MER_OWNER_SAFE                 = '\xf8067d8ca90b8510ce8ade1eec24b7260eafa5f7'
RH_MER_FEE_COLLECTOR_SAFE         = '\xff68fda91b0e785b4aee674d3b428c4ab6d8eaa7'
RH_MER_SEQUENCER                  = '\x39f7e2936316f99e578489509c2db036f384e574'
RH_MER_LP_VAULT                   = '\x24b84023c8e4da635be228c380c09bfe5271bf9d'
RH_USDE                           = '\x5d3a1ff2b6bab83b63cd9ad0787074081a52ef34'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed as `keccak256(signature)` from the Sourcify-verified ABIs of `ExchangeGateway` and `MeridianUSD` and from the verified interface sources (`IPerpEngine`, `IActionHandler`, `ICollateralManager`). `PositionLiquidated` and `PositionDeleveraged` (module source not published) were found by matching candidate signatures against `PUSH32` constants in the Liquidation and Deleverage module bytecode; `PositionLiquidated` also against 63 live logs. Live counts come from `eth_getLogs` on `https://rpc.mainnet.chain.robinhood.com`.
- **Addresses:** gateway and merUSD from the DefiLlama adapter; modules from the gateway's `RegistryRecordUpdated` logs; owners, tokens, Pyth Lazer, fee collector and liquidator from live views; sequencer, depositors and claimer from config event logs. All existence-checked with `eth_getCode`.
- **Proxies:** EIP-1967 slots read live; `Upgraded` logs over the full history.
- **Chain coverage:** `eth_getCode` on the other seven target chains and Arc returned `0x`.

Sources:
- Sourcify: [ExchangeGateway impl](https://sourcify.dev/server/v2/contract/4663/0x0f17d8468c49d6c80e4ee10cc87a767085a4b9a8) · [MeridianUSD impl](https://sourcify.dev/server/v2/contract/4663/0x9a5c0ca8138923bf3788579fb48dabb0339bbbde) · [LP vault](https://sourcify.dev/server/v2/contract/4663/0x24b84023c8e4Da635be228C380C09bfE5271BF9d)
- [DefiLlama-Adapters `projects/meridian-perps/index.js`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/meridian-perps/index.js) · [DefiLlama — Meridian Perps](https://defillama.com/protocol/meridian-perps)
- [Meridian docs](https://docs.meridian.xyz) · [app.meridian.xyz](https://app.meridian.xyz/)
- Explorer: [Robinhood Chain Blockscout — ExchangeGateway](https://robinhoodchain.blockscout.com/address/0xD540F47F214dC7D6D244E62A6aE7e06B586Ef44A)
