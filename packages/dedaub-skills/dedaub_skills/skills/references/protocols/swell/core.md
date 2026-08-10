# Swell Network — Topics, Selectors, Addresses (Ethereum mainnet; Swellchain L2 noted)

**Status:** verified 2026-06-09 against Ethereum mainnet via `eth_getLogs` / `eth_getCode` / `eth_getStorageAt` / `eth_call` on `https://ethereum-rpc.publicnode.com`, the canonical `SwellNetwork/v3-core-public` source, `build.swellnetwork.io` deployment docs, and keccak-256 computed locally + cross-checked against live logs. Cross-chain presence (`0x` = absent) existence-checked on all 6 other target chains.
**Scope:** Both Swell product lines — **liquid staking** (swETH) and **liquid restaking** (rswETH, EigenLayer) — plus the **Earn vaults** (earnETH/earnBTC/rswBTC, Nucleus BoringVault) and the **SWELL/rSWELL** governance tokens. Event `topic0` and function `selector` values are **chain-agnostic**; addresses are Ethereum-specific. The two staking lines (`lst/` and `lrt/` in the repo) are **near-identical codebases** — the same event/selector signatures with `swETH`↔`rswETH` renamed — so a single file covers both; **disambiguate by emitting contract address**, never by topic0.

**What Swell is.** Deposit ETH → mint **swETH** (LST, non-rebasing, value-accruing) or **rswETH** (LRT, restaked via EigenLayer). Both are ERC-20 upgradeable proxies whose exchange rate moves only on a daily **`Reprice`** driven by an off-chain bot through a **`RepricingOracle`** (which emits `SnapshotSubmittedV2` / `ReservesRecordedV2` / `RewardsCalculatedV2`, then calls `reprice()` on the token). Withdrawals are async + NFT-based via **swEXIT / rswEXIT** (ERC-721 request tokens). The **Earn vaults** (earnETH/earnBTC/rswBTC) are a *separate* system built on **Nucleus BoringVault** (ERC-4626-like, emit `Enter`/`Exit`, immutable). **Swellchain** is Swell's own OP-Stack L2 (chain **1923**) — outside the 7 targets; its L1 bridge contracts live on Ethereum and are listed in §6.

---

## 0. Contract families & versions

| Family | Contracts | Upgradeable? | Notes |
|--------|-----------|--------------|-------|
| **LST (swETH)** | swETH, swEXIT, DepositManager, RepricingOracle, NodeOperatorRegistry, AccessControlManager | EIP-1967 Transparent proxies | LST ProxyAdmin `0x25eaf579…b8846` |
| **LRT (rswETH)** | rswETH, rswEXIT, DepositManager, RepricingOracle, NodeOperatorRegistry, AccessControlManager, EigenLayerManager | EIP-1967 Transparent proxies | LRT ProxyAdmin `0xd750b848…bfd14`; adds EigenLayer integration |
| **Earn vaults** | earnETH, earnBTC, rswBTC, swBTC (Nucleus BoringVault + Teller + Accountant) | **immutable** (BoringVault) / EIP-1167 clones | `Enter`/`Exit` accounting; rate via Accountant `ExchangeRateUpdated` |
| **Governance** | SWELL, rSWELL | **non-proxy** ERC-20 / EIP-1167 clone | SWELL = plain `ERC20Votes`; rSWELL = clone of `0x1ab62413…14467` |
| **Swellchain L1 bridge** | OptimismPortal, L1StandardBridge, L1CrossDomainMessenger, SystemConfig, AddressManager | OP-Stack proxies | bridges ETH/tokens to chain 1923 |

> The repo's `lst/` and `lrt/` trees are sibling copies. **`Reprice`, `ETHDepositReceived`, `ETHWithdrawn`, `WithdrawRequestCreated`, `WithdrawalClaimed`, `WithdrawalsProcessed`, `SnapshotSubmittedV2`, `ReservesRecordedV2` have identical canonical signatures on both lines** (the params are `uint256` either way; only the doc/param names differ). One topic0 each, two emitter addresses.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

**✓** = observed verbatim in live mainnet `eth_getLogs`; **abi** = computed from canonical source, not seen in sampled ranges (rare/admin events).

### 1.1 swETH / rswETH (LST & LRT staking token — same sigs, two addresses)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ✓ |
| `0xe28a9e1df63912c0c77b586c53595df741cbbc554d6831e40f1b5453199a9630` | `ETHDepositReceived(address indexed from, uint256 amount, uint256 swETHMinted, uint256 newTotalETHDeposited, address indexed referral)` (`rswETHMinted` on LRT) | ✓ |
| `0xf0e4379b3fd6b436bf73f47761c746a33d02bbd47835cbd8050b130fb2c6db2e` | `Reprice(uint256 newEthReserves, uint256 newSwETHToETHRate, uint256 nodeOperatorRewards, uint256 swellTreasuryRewards, uint256 totalETHDeposited)` | ✓ |
| `0xd3605746397fcbe273096353855da8c40c332aa45d2d97a5e19130a238e9e3bc` | `ETHWithdrawn(address indexed to, uint256 swETHBurned, uint256 ethReturned)` | abi |
| `0x71fa34c234c299cc82b901827ef18e0c50a6a37215b6d7fd3a326b1b2cd78fc3` | `DepoistManagerDeposit(address _receiver, uint256 _ethSpent, uint256 _rswETHReceived)` (**rswETH only**; typo is in the source) | abi |
| `0x27e4f2f352935a2ca3e0ce8449fe7cb9d5a6ff6bf77dd8b3a15b7fe8e6c70b17` | `SwellTreasuryRewardPercentageUpdate(uint256 oldPercentage, uint256 newPercentage)` | abi |
| `0xc6a0a21af7e95fb21f7a2393b2004d6a61318bede114a5d92a3d2b7949a714d5` | `NodeOperatorRewardPercentageUpdate(uint256 oldPercentage, uint256 newPercentage)` | abi |
| `0x08dde51d1eb863f6f778ed692f211d8fbe9842b2f1a688face1a896aedb0fa45` | `MinimumRepriceTimeUpdated(uint256,uint256)` | abi |
| `0xf19926eb41216b26f9bf7015eeae6dd236e8868a8da2b442909f20b9a5ba7193` | `MaximumRepriceswETHDifferencePercentageUpdated(uint256,uint256)` (LST) | abi |
| `0x230483171950cae34ad1b1c4ed0d79293f1c90062b6588c92388cc62c587be7d` | `MaximumRepriceRswETHDifferencePercentageUpdated(uint256,uint256)` (LRT) | abi |
| `0x789d9f061bf0f3168343be4f3221ced5600fc12b01682b64edf925abd8dc64de` | `MaximumRepriceDifferencePercentageUpdated(uint256,uint256)` | abi |

> **The rate moves only on `Reprice`.** Index it (one emitter for swETH, one for rswETH). `newSwETHToETHRate` is 1e18-scaled ETH per token. **swETH/rswETH do NOT rebase** — `Transfer.value` is the real token amount; balances are stable, the *rate* changes. `ETHDepositReceived` is the mint/stake event (mint also shows as `Transfer` from `0x0`). Burns go through swEXIT, not a direct user burn — `ETHWithdrawn` is rarely emitted directly.

### 1.2 swEXIT / rswEXIT (withdrawal queue — ERC-721 request NFTs; same sigs, two addresses)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xd48f8b52902b367c4dc78fa10a8bd215a48d630181be5432700f09b680517f50` | `WithdrawRequestCreated(uint256 tokenId, uint256 amount, uint256 timestamp, uint256 indexed lastTokenIdProcessed, uint256 rateWhenCreated, address indexed owner)` | ✓ |
| `0x2d43eb174787155132b52ddb6b346e2dca99302eac3df4466dbeff953d3c84d1` | `WithdrawalClaimed(address indexed owner, uint256 tokenId, uint256 exitClaimedETH)` | ✓ |
| `0xb2196843288728fda0c54b9d3c1ee5d1b41f935cdbd1e46ef0dadbcae4e746ec` | `WithdrawalsProcessed(uint256 fromTokenId, uint256 toTokenId, uint256 processedRate, uint256 processedExitingETH, uint256 processedExitedETH)` | ✓ |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (ERC-721 NFT; `tokenId` = withdrawal request id) | ✓ |
| `0xbfe611b001dfcd411432f7bf0d79b82b4b2ee81511edac123a3403c357fb972a` | `ETHReceived(address indexed sender, uint256 amount)` | abi |
| `0x81874a0642912a1bb935b844d374323408b144e6689eb2f74e61e2e438cc9ed9` | `WithdrawalRequestMaximumUpdated(uint256 oldLimit, uint256 newLimit)` | abi |
| `0xcbb988b1110581179ab9947482ee29fb15c094ced67aa98fed03ae19cfc8d9da` | `WithdrawalRequestMinimumUpdated(uint256 oldMinimum, uint256 newMinimum)` | abi |
| `0x309b29ded109b9e28fb9885757b3e0096eb75c51d23aa4635d68bcd569f6adc1` | `BaseURIUpdated(string,string)` | abi |

> Withdrawals are async: **`WithdrawRequestCreated`** (mints an ERC-721 to the owner) → bot **`WithdrawalsProcessed`** (a token-id range, locks the processed rate) → owner **`WithdrawalClaimed`** (burns NFT, sends ETH). The ERC-721 `Transfer` shares topic0 with the ERC-20 — **disambiguate by emitter** (swEXIT/rswEXIT address vs swETH/rswETH address). Transferring the NFT transfers claim rights.

### 1.3 RepricingOracle (LST & LRT — same sigs, two addresses)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x117ef17ee1efd4615c6c3cdc3d846b3e3c721357f3f9bdae2cac7c125b15b9ea` | `SnapshotSubmittedV2(uint256 indexed blockNumber, uint256 slot, uint256 reportTimestamp, uint256 totalETHDeposited, uint256 swETHTotalSupply, uint256 totalETHExited)` (**live form**) | ✓ |
| `0x065c2d0865d0a176d73094316d4809db64290ccf790ed5f2c25edc3e19ef56b6` | `ReservesRecordedV2(uint256 indexed blockAtSnapshot, uint256 elBalance, uint256 clV3Balance, uint256 clV2Balance, uint256 transitioningBalance, uint256 newETHReserves, uint256 reserveAssets, uint256 exitingETH)` (**live form**) | ✓ |
| `0x03f848ac9bef13b51657bd5a8a209708dab4dd1e70a8c63fb3a0f44e8e2d7987` | `RewardsCalculatedV2(uint256 indexed blockAtSnapshot, uint256 blockOfLastSnapshot, int256 reserveAssetsChange, uint256 ethDepositsChange, uint256 rewardsPayableForFees, uint256 ethExitedChange)` | abi |
| `0xa3a0ac4b7d33d5d49f9fd1c3129f28c805428898548b5ff1fe58d90ca367cb58` | `SnapshotSubmitted(uint256 indexed blockNumber, uint256 slot, uint256 reportTimestamp, uint256 totalETHDeposited, uint256 swETHTotalSupply)` (**V1 — superseded**) | abi |
| `0xf43c8650b32b66ea8c511adf3ad70bf0ac136ac736d2a0226a18619c75fa8607` | `ReservesRecorded(uint256 indexed blockAtSnapshot, uint256 elBalance, uint256 clV3Balance, uint256 clV2Balance, uint256 transitioningBalance, uint256 newETHReserves)` (**V1**) | abi |
| `0x131f8256d8e5a19d55928aaa3b51e76324ca6a7af5974179f7444742da8c9db6` | `RewardsCalculated(uint256 indexed blockAtSnapshot, uint256 blockOfLastSnapshot, int256 reservesChange, uint256 ethDepositsChange, uint256 rewardsPayableForFees)` (**V1**) | abi |
| `0xfa8d209167610f942a538ba5f5270247506741005c83629661c2479908888597` | `ExternalV3ReservesPoROracleAddressUpdated(address oldAddress, address newAddress)` | abi |

> **Use the V2 events** (`…V2`, live-confirmed). The non-V2 forms are the original signatures, still in the ABI but superseded once `totalETHExited` / `reserveAssets` were added. The reprice flow per period: oracle emits `SnapshotSubmittedV2` → `ReservesRecordedV2` → `RewardsCalculatedV2`, all in the snapshot tx, then calls `swETH.reprice()` which emits the token's `Reprice`. **`reservesChange` / `reserveAssetsChange` are `int256`** (can be negative = slashing/loss — the key risk signal).

### 1.4 DepositManager (LST & LRT — validator funding; same sigs, two addresses)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xffb1367626264d9733e4dcd7f14cd59fc3a2c15d50d1a41f1ee60c96f77a01dd` | `ValidatorsSetup(bytes[] pubKeys)` | abi |
| `0xbfe611b001dfcd411432f7bf0d79b82b4b2ee81511edac123a3403c357fb972a` | `ETHReceived(address indexed from, uint256 amount)` | abi |
| `0x78f5cdad99320ec2ba57132d7dffb1d125775c823239e60ff5e9300fd4ac898c` | `EthSent(address indexed to, uint256 amount)` | abi |

### 1.5 NodeOperatorRegistry (LST & LRT — same sigs, two addresses)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x0780dc183feb0e4f9714cd802b3c0a21894b7ccb4172c992569d2acb5d45f91c` | `OperatorAdded(address operatorAddress, address rewardAddress)` | abi |
| `0x9e532d260bd7dde07708a6b1f7c64042546243d79bac23514cd74fcfc1a01fe4` | `OperatorEnabled(address indexed operator)` | abi |
| `0x23cd406c7cafe6d88c3f1c1cc16e438745a4236aec25906be2046ca16c36bd1e` | `OperatorDisabled(address indexed operator)` | abi |
| `0x9f11a997d566f42b07cef240eb15dd049a6a0be7a3f642656786fc1938a73976` | `OperatorAddedValidatorDetails(address indexed operator, (bytes,bytes,bytes32)[] pubKeys)` | abi |
| `0x790d3361478ddb811f265789ce5dddc293527ee2bc8951304a9de1d849600bb9` | `ActivePubKeysDeleted(bytes[] pubKeys)` | abi |
| `0x9b3c43de1c4440da470f4b2b750fb6ebae2d6684dac752e4ee4d7fb7ac1b654d` | `PendingPubKeysDeleted(bytes[] pubKeys)` | abi |
| `0x0f4e549c79372febae129e43b9a8b39280d5fab140fdf26f839ae647f857d3e6` | `PubKeysUsedForValidatorSetup(bytes[] pubKeys)` | abi |
| `0x58842ff85e13a74a6e41fbc7797c19619df9a311c26df97a2dd3c723671de8df` | `OperatorControllingAddressUpdated(address indexed oldControllingAddress, address indexed newControllingAddress)` | abi |
| `0xb40208293c58e442b2302dc32a7fe189c2682484d6459d934d33f9580e8c6fc9` | `OperatorRewardAddressUpdated(address indexed operator, address indexed newRewardAddress, address indexed oldRewardAddress)` | abi |

### 1.6 EigenLayerManager (**LRT only** — restaking bridge to EigenLayer)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x02573264a31062071e6fe875ef91be3f022dfce12d2560f8411f8e1eaea9017b` | `StakerCreated(address stakerProxyAddress)` | abi |
| `0xf975a40e54653d58fd233016e025c986dcafad672f3ed5dd2a6c5a30528acd7d` | `DepositedIntoStrategy(uint256 amount, address token, address currentStrategy)` | abi |
| `0xd81827406c6888c79665ca758c4fd9c4f4c6f2861725af946799a12783c3d7a7` | `ValidatorsSetupOnEigenLayer(uint256[] stakerIds, bytes[] pubKeys)` | abi |
| `0x966456cce068b3ce98c139dffc506255100836c161fce1c9cd68d4ce09f37905` | `StakerAssignedToOperator(uint256 stakerId, address operator)` | abi |
| `0x02f407e3319e5f215ed4a90c586172be9d2d0a4a729deba9bfa6b2d91f124c55` | `StakerUnassignedFromOperator(uint256 stakerId, address operator)` | abi |

### 1.7 AccessControlManager + OZ proxy events (all core proxies)

The LST/LRT contracts use OpenZeppelin `AccessControl`; pausing/role changes surface here.

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | abi |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | abi |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | abi |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | abi |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (**watch — every core proxy can upgrade**) | abi |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | abi |

> Role byte32s (keccak of the string): `PLATFORM_ADMIN` `0x4ff52032…2691b` · `BOT` `0x902cbe3a…4e2b` · `REPRICER` `0x2d75377d…74e4` (gates `reprice`) · `PAUSER` `0x53944082…5c14c` · `UNPAUSER` `0x82b32d9a…e9448` · `DELETE_ACTIVE_VALIDATORS` `0xf9684f08…1994` · `PROCESS_WITHDRAWALS` `0x549433fa…dddb` · `DEFAULT_ADMIN_ROLE` = `0x00…00`. The **AccessControlManager is a separate proxy per line** — `swETH.AccessControlManager()` → `0x6250…5EAC` (LST), `rswETH.AccessControlManager()` → `0x7965…333f` (LRT). It also exposes `pauseCoreMethods` / `lockdown` (protocol-wide kill switch).

### 1.8 Earn vaults — Nucleus BoringVault / Teller / Accountant (earnETH, earnBTC, rswBTC, swBTC)

Separate ERC-4626-style system (built by Nucleus, same team as Ion). The vault token itself custodies assets and emits `Enter`/`Exit`; the **Accountant** (a different address per vault) emits `ExchangeRateUpdated`.

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xea00f88768a86184a6e515238a549c171769fe7460a011d6fd0bcd48ca078ea4` | `Enter(address from, address asset, uint256 amount, address to, uint256 shares)` (deposit) | abi |
| `0xe0c82280a1164680e0cf43be7db4c4c9f985423623ad7a544fb76c772bdc6043` | `Exit(address to, address asset, uint256 amount, address from, uint256 shares)` (redeem) | ✓ |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (vault share token) | ✓ |
| `0xa95bc6aba40bbc4d95fc35f118c4cd8b53fc5d5b89ed264002af03503a7a9439` | `ExchangeRateUpdated(uint96 oldRate, uint96 newRate, uint64 currentTime)` (**on the Accountant, not the vault**) | abi |

> The earn vaults' rate updates are emitted by the **Accountant** contract (a distinct address from the BoringVault token). To monitor the earn rate, find each vault's Accountant (`BoringVault` → `Teller`/`Accountant` wiring) rather than keying `ExchangeRateUpdated` on the vault token address. The earn share token is **immutable** (no proxy slot).

---

## 2. Function signatures (chain-agnostic — `selector = keccak256(signature)[0:4]`)

**bytecode** = confirmed in the live deployed implementation (PUSH4 dispatcher scan; proxies resolved to impl first).

### 2.1 swETH / rswETH

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0xd0e30db0` | `deposit()` | — | **Stake ETH** (payable). Emits `ETHDepositReceived`. bytecode✓ |
| `0xc18d7cb7` | `depositWithReferral(address referral)` | — | payable. bytecode✓ |
| `0x42966c68` | `burn(uint256 amount)` | — | burns caller's tokens (no ETH back; used by swEXIT). bytecode✓ |
| `0x7342bbd4` | `reprice(uint256 _preRewardETHReserves, uint256 _newETHRewards, uint256 _swETHTotalSupply)` | — | **REPRICER-only**, called by RepricingOracle. Emits `Reprice`. bytecode✓ |
| `0xd68b2cb6` | `swETHToETHRate()` | `uint256` | **swETH rate (1e18).** bytecode✓ (live ≈ 1.124) |
| `0x0de3ff57` | `ethToSwETHRate()` | `uint256` | inverse. bytecode✓ |
| `0xa7b9544e` | `rswETHToETHRate()` | `uint256` | **rswETH rate (1e18).** bytecode✓ (live ≈ 1.073) |
| `0x780a47e0` | `ethToRswETHRate()` | `uint256` | inverse (rswETH). bytecode✓ |
| `0x70a08231` / `0x18160ddd` / `0x95d89b41` | `balanceOf` / `totalSupply` / `symbol` | | standard ERC-20 (**non-rebasing**). |
| `0x902340a1` | `AccessControlManager()` | `address` | resolves the per-line ACM. |

### 2.2 swEXIT / rswEXIT

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0x74dc9d1a` | `createWithdrawRequest(uint256 amount)` | — | burns swETH, mints request NFT. bytecode✓ |
| `0x5e15c749` | `finalizeWithdrawal(uint256 tokenId)` | — | claim ETH, burn NFT → `WithdrawalClaimed`. bytecode✓ |
| `0x152fcb0c` | `processWithdrawals(uint256 _lastTokenIdToProcess)` | — | **PROCESS_WITHDRAWALS-only** (bot) → `WithdrawalsProcessed`. bytecode✓ |

### 2.3 RepricingOracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x64370336` | `submitSnapshotV2(...)` | **the live snapshot entry-point** (LST reprice tx selector). Emits §1.3 V2 events then calls `swETH.reprice`. |
| `0x79aaafcf` | `submitSnapshotV2(...)` | the live LRT snapshot entry-point selector (rswETH path). |

> The two RepricingOracle lines expose different snapshot-submit selectors (`0x64370336` LST, `0x79aaafcf` LRT) because the calldata struct differs slightly; both are the off-chain bot's reprice trigger. Decode the live ABI before parsing calldata.

### 2.4 Nucleus BoringVault (earn vaults)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0efe6a8b` | `deposit(address depositAsset, uint256 depositAmount, uint256 minimumMint)` | called on the **Teller**, mints vault shares → `Enter`. |
| `0x2e1a7d4d` | `withdraw(uint256)` / queue-based redeem | redeem path; `Exit` on the vault. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

Every address verified to hold code (`eth_getCode`). Proxy type confirmed by EIP-1967 impl-slot read. **Proxy legend:** `T-proxy` = OZ TransparentUpgradeableProxy (EIP-1967 impl + admin slots populated); `clone` = EIP-1167 minimal proxy; `—` = non-proxy / immutable.

### 3.1 LST (swETH) — liquid staking

| Role | Address | Proxy | One-liner |
|------|---------|-------|-----------|
| **swETH** | `0xf951E335afb289353dc249e82926178EaC7DEd78` | T-proxy → impl `0xce95ba824ae9a4df9b303c0bbf4d605ba2affbfc` | LST token; emits §1.1. |
| **swEXIT** | `0x48C11b86807627AF70a34662D4865cF854251663` | T-proxy → impl `0x02454d649054276e3ed8b9f17f8d5f49ac6c8f78` | Withdrawal queue (ERC-721); emits §1.2. |
| **DepositManager** | `0xb3D9cf8E163bbc840195a97E81F8A34E295B8f39` | T-proxy → impl `0xeee6207d514c2845394b5f4b9f12b6d155f4524b` | Holds ETH, funds validators; emits §1.4. |
| **RepricingOracle** | `0x289d600447a74B952Ad16f0BD53b8eaAAc2D2d71` | T-proxy → impl `0x3334c0d1fdcd972a6dd1cc0d79e9a602805a25f7` | Snapshot + reprice driver; emits §1.3. |
| **NodeOperatorRegistry** | `0x46ddC39E780088B1B146aBA8cBbe15dc321a1A1d` | T-proxy → impl `0xea6c9a14b96777a448687272bf0e6f6d9ce0e68a` | Operator/validator key registry; emits §1.5. |
| **AccessControlManager** | `0x625087d72c762254a72CB22cC2ECa40da6b95EAC` | T-proxy → impl `0xbb7b99c2be525c0a6b719344f89a4255ef593e64` | Roles + pausing + lockdown; emits §1.7. |
| LST **ProxyAdmin** | `0x25eaF579Ca2255faa5463c635eEC28697b5b8846` | — | Upgrade authority for all LST proxies above. |

### 3.2 LRT (rswETH) — liquid restaking

| Role | Address | Proxy | One-liner |
|------|---------|-------|-----------|
| **rswETH** | `0xFAe103DC9cf190eD75350761e95403b7b8aFa6c0` | T-proxy → impl `0x4796d939b22027c2876d5ce9fde52da9ec4e2362` | LRT token; emits §1.1. |
| **rswEXIT** | `0x58749C46FFE97e4d79508a2C781C440f4756f064` | T-proxy → impl `0xbd6a5ec8a78b57871ae17d22cd686a72ebe06479` | Restaking withdrawal queue (ERC-721); emits §1.2. |
| **DepositManager** | `0x5e6342D8090665BE14EeB8154c8A87B7249a4889` | T-proxy → impl `0xee33c44a30e6e8a79e33c45fe0deeaf069d33181` | LRT validator funding; emits §1.4. |
| **RepricingOracle** | `0xd5A73C748449a45cc7d9F21c7ed3Ab9eb3D2e959` | T-proxy → impl `0x73e26f707a0dca4b22e32379259dda021ba6ddc7` | LRT snapshot + reprice; emits §1.3. |
| **NodeOperatorRegistry** | `0xaae0B305B3F1edDe7b11B680d4FA9252f7A1c524` | T-proxy → impl `0xf3deaee3b6775fd33a25f728012c0ae01c38c7b8` | LRT operator registry; emits §1.5. |
| **AccessControlManager** | `0x796592b2092F7E150C48643DA19dD2F28bE3333f` | T-proxy → impl `0x4195ed6e112cbddc1adf7271047dba4e6bb6bc56` | LRT roles + pausing; emits §1.7. |
| **EigenLayerManager** | `0xc94cFFd5249dF4008A043Ee61E13F19af16d0936` | T-proxy → impl `0x487aa7c2d3246447f955cb6e349b0519d2c1d1b9` | EigenLayer restaking integration; emits §1.6. |
| LRT **ProxyAdmin** | `0xd750B84845f1cADFEAc63F96Ec74635e949BFD14` | — | Upgrade authority for all LRT proxies above. |

### 3.3 Earn vaults (Nucleus BoringVault) — separate system

| Role | Address | Proxy | One-liner |
|------|---------|-------|-----------|
| **earnETH** | `0x9Ed15383940CC380fAEF0a75edacE507cC775f22` | — (immutable BoringVault) | ETH-denominated yield vault; emits §1.8. |
| **earnBTC** | `0x66E47E6957B85Cf62564610B76dD206BB04d831a` | — (immutable BoringVault) | BTC-denominated yield vault. |
| **rswBTC** | `0x215DC1Cc32D9D08a0081e55E55895C8cf006839A` | — (immutable BoringVault) | restaked BTC vault. |
| **swBTC** | `0x8DB2350D78aBc13f5673A411D4700BCF87864dDE` | EIP-1167 clone → impl `0x2826d136f5630ada89c1678b64a61620aab77aea` | Swell wrapped-BTC LST; clone (not a BoringVault). |

> The earn vaults reuse the **same address on Swellchain** (`earnETH` = `0x9Ed1…f22` on both ETH and chain 1923) — a deterministic deploy. Each vault has a separate **Teller** and **Accountant** (resolve from the vault); the rate event lives on the Accountant.

### 3.4 Governance tokens

| Role | Address | Proxy | One-liner |
|------|---------|-------|-----------|
| **SWELL** | `0x0a6E7Ba5042B38349e437ec6Db6214AEC7B35676` | — (**non-proxy** `ERC20Votes`) | Governance token; 10,000,000,000 supply; emits ERC-20 `Transfer`/`Approval` + `DelegateChanged`/`DelegateVotesChanged`. |
| **rSWELL** | `0x358d94b5b2F147D741088803d932Acb566acB7B6` | EIP-1167 clone → impl `0x1ab62413e0cf2eBEb73da7d40c70E7202ae14467` | Locked/restaked SWELL governance token. |

---

## 4. Cross-chain summary (presence matrix)

`✓addr` = native deployment at that exact address; `—` = `0x` (no code at the canonical Ethereum address). All four canonical addresses were existence-checked on every chain below; **none are present on the 6 L2/alt targets** at the Ethereum address.

| Chain (ID) | swETH | rswETH | SWELL | earnETH | Notes |
|------------|-------|--------|-------|---------|-------|
| **Ethereum (1)** | ✓ `0xf951…Ded78` | ✓ `0xFAe1…a6c0` | ✓ `0x0a6E…5676` | ✓ `0x9Ed1…5f22` | canonical home of all core contracts |
| Base (8453) | — | — | — | — | absent at ETH address |
| BNB (56) | — | — | — | — | absent (a `swETH`-symbol decoy `0x2189…1063` exists on BscScan — **not** Swell's token) |
| Avalanche (43114) | — | — | — | — | absent |
| Arbitrum (42161) | — | — | — | — | absent (historic LayerZero-OFT swETH existed earlier; not at this address) |
| Optimism (10) | — | — | — | — | absent |
| Polygon (137) | — | — | — | — | absent |
| **Swellchain (1923)** | `0x0934…85B7` | `0x18d3…5258` | `0x2826…7Aea` | `0x9Ed1…5f22` | **outside the 7 targets**; Swell's own OP-Stack L2. rSWELL `0x939f…bf8c`, swBTC `0x1cf7…BF7B`, uBTC `0xb566…0b0A`, stBTC `0xf671…b8A3`, WETH `0x4200…0006` |

> **Swell is Ethereum-canonical.** Native swETH/rswETH/SWELL/earn deployments exist only on Ethereum (mint/burn) and **Swellchain** (the protocol's home L2). They are **not** natively deployed on any of the 6 other target chains. Earlier swETH used a LayerZero OFT for L2 liquidity (since deprecated in favor of Chainlink CCIP / Swellchain native bridging) — any L2 swETH today is a bridged representation at a *different* address, not the Ethereum token. **A BNB token with `swETH` symbol (`0x2189…1063`) is a look-alike decoy** — verify by source, not symbol.

---

## 5. Proxies (old & new)

| Contract group | Pattern | Detection | Upgrade authority |
|----------------|---------|-----------|-------------------|
| **All 6 LST core** (swETH, swEXIT, DepositManager, RepricingOracle, NOR, ACM) | OZ **TransparentUpgradeableProxy** (EIP-1967) | impl slot `0x3608…2bbc` populated; admin slot = LST ProxyAdmin `0x25eaf579…b8846` | LST ProxyAdmin → PLATFORM_ADMIN multisig |
| **All 7 LRT core** (rswETH, rswEXIT, DepositManager, RepricingOracle, NOR, ACM, EigenLayerManager) | OZ **TransparentUpgradeableProxy** (EIP-1967) | impl slot populated; admin slot = LRT ProxyAdmin `0xd750b848…bfd14` | LRT ProxyAdmin → PLATFORM_ADMIN multisig |
| **Earn vaults** (earnETH, earnBTC, rswBTC) | **immutable** Nucleus BoringVault | EIP-1967 impl slot = **zero**; logic is the contract itself | not upgradeable (BoringVault is fixed; only Teller/Accountant/manager wiring changes) |
| **swBTC, rSWELL** | **EIP-1167 minimal-proxy clone** | 45-byte runtime `363d3d373d3d3d363d73<impl>5af43d82803e903d91602b57fd5bf3`; impl slot is zero (clone targets are hard-coded in bytecode — swBTC → `0x2826d136…77aea`, rSWELL → `0x1ab62413…14467`) | clone target fixed at deploy |
| **SWELL** | **non-proxy** ERC20Votes | impl/admin/beacon slots all zero; 2,200-byte token | none (immutable token) |

**Two separate ProxyAdmins** gate the two staking lines — LST `0x25eaf579…b8846`, LRT `0xd750b848…bfd14`. Watch **`Upgraded(address)`** (`0xbc7cd75a…2d3b`) on every core proxy; an upgrade silently changes decode behaviour. **Read the live impl slot** before decoding — Swell upgrades in place.

---

## 6. Swellchain L1 bridge (Ethereum-side, OP-Stack) — context, not a target

Swellchain (chain 1923) is an OP-Stack L2; these are its **Ethereum mainnet** bridge/system contracts (lock-and-mint to L2):

| Role | Address |
|------|---------|
| OptimismPortalProxy | `0x758E0EE66102816F5C3Ec9ECc1188860fbb87812` |
| L1StandardBridgeProxy | `0x7aA4960908B13D104bf056B23E2C76B43c5AACc8` |
| L1CrossDomainMessengerProxy | `0xe6a99Ef12995DeFC5ff47EC0e13252f0E6903759` |
| SystemConfigProxy | `0xD3d4c6B703978a5d24FecF3a70a51127667Ff1A4` |
| AddressManager | `0xa54a84f17c2180148c762D79bC57BdfF7FdAFC8A` |

---

## 7. Detection invariants & gotchas

1. **swETH/rswETH do NOT rebase.** Unlike stETH, balances are stable and the **rate** changes only on `Reprice` (`0xf0e4379b…`). Track `swETHToETHRate()` / `rswETHToETHRate()` or the `Reprice.newSwETHToETHRate` field — not balance deltas. wstETH-style "shares" don't exist here.
2. **LST and LRT share every topic0 and selector** — `Reprice`, `ETHDepositReceived`, `WithdrawRequestCreated`, `SnapshotSubmittedV2`, etc. are byte-identical across the two lines. **Disambiguate purely by emitting address** (swETH `0xf951…` vs rswETH `0xFAe1…`; swEXIT `0x48C1…` vs rswEXIT `0x5874…`; LST oracle `0x289d…` vs LRT oracle `0xd5A7…`).
3. **Withdrawals are async + NFT-based.** `WithdrawRequestCreated` (mint ERC-721) → bot `WithdrawalsProcessed` (token-id range) → owner `WithdrawalClaimed` (burn + ETH). The ERC-721 `Transfer` collides with the ERC-20 `Transfer` topic0 — key on the swEXIT/rswEXIT address. The NFT carries claim rights; transferring it reassigns the payout.
4. **The rate-change risk signal is `int256 reserveAssetsChange` in `RewardsCalculatedV2`** (and `reservesChange` in V1) — a **negative** value means the protocol's CL reserves fell (slashing / penalty). Also watch a `Reprice` where `newSwETHToETHRate` drops vs prior.
5. **Use the V2 oracle events.** `SnapshotSubmittedV2` / `ReservesRecordedV2` / `RewardsCalculatedV2` are the live forms; the non-V2 originals are superseded (still in the ABI). The full reprice happens in one tx: 3 oracle V2 events on the RepricingOracle address, then `Reprice` on the token address.
6. **`reprice` is REPRICER-gated and only the RepricingOracle calls it.** A `Reprice` not preceded by a `SnapshotSubmittedV2` in the same tx is anomalous. Snapshot-submit selectors differ per line (`0x64370336` LST, `0x79aaafcf` LRT).
7. **Earn vaults are a different protocol surface (Nucleus).** They emit `Enter`/`Exit` (not `ETHDepositReceived`), are **immutable BoringVaults**, and their rate event `ExchangeRateUpdated` lives on a **separate Accountant** address, not the vault token. Don't conflate earn TVL flows with swETH/rswETH staking flows.
8. **SWELL is a plain non-proxy ERC20Votes** (supply 10B, no `owner()`) — governance/voting power moves via `DelegateChanged`/`DelegateVotesChanged`, not the LST AccessControl. **rSWELL** and **swBTC** are EIP-1167 clones (zero impl slot — don't mistake "no impl slot" for "not upgradeable infra").
9. **Cross-chain decoys.** The BNB `swETH`-symbol token `0x2189…1063` is **not** Swell's swETH. Verify any non-Ethereum token by source/issuer, never by symbol. Native Swell deployments exist only on Ethereum + Swellchain (1923).
10. **Two ProxyAdmins, two ACMs, two of every core contract.** Build your address book keyed on **(line, role)** — every LST contract has an LRT twin. The `AccessControlManager.lockdown()` / `pauseCoreMethods()` is the protocol-wide kill switch; an admin `Paused`/`RoleGranted` on either ACM is alert-worthy.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; same for swETH & rswETH lines) =====
TOPIC_TRANSFER                  = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  -- ERC20+ERC721
TOPIC_APPROVAL                  = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_ETH_DEPOSIT_RECEIVED      = '\xe28a9e1df63912c0c77b586c53595df741cbbc554d6831e40f1b5453199a9630'
TOPIC_REPRICE                   = '\xf0e4379b3fd6b436bf73f47761c746a33d02bbd47835cbd8050b130fb2c6db2e'
TOPIC_ETH_WITHDRAWN             = '\xd3605746397fcbe273096353855da8c40c332aa45d2d97a5e19130a238e9e3bc'
-- swEXIT / rswEXIT (withdrawal queue)
TOPIC_WITHDRAW_REQUEST_CREATED  = '\xd48f8b52902b367c4dc78fa10a8bd215a48d630181be5432700f09b680517f50'
TOPIC_WITHDRAWAL_CLAIMED        = '\x2d43eb174787155132b52ddb6b346e2dca99302eac3df4466dbeff953d3c84d1'
TOPIC_WITHDRAWALS_PROCESSED     = '\xb2196843288728fda0c54b9d3c1ee5d1b41f935cdbd1e46ef0dadbcae4e746ec'
-- RepricingOracle (use V2)
TOPIC_SNAPSHOT_SUBMITTED_V2     = '\x117ef17ee1efd4615c6c3cdc3d846b3e3c721357f3f9bdae2cac7c125b15b9ea'
TOPIC_RESERVES_RECORDED_V2      = '\x065c2d0865d0a176d73094316d4809db64290ccf790ed5f2c25edc3e19ef56b6'
TOPIC_REWARDS_CALCULATED_V2     = '\x03f848ac9bef13b51657bd5a8a209708dab4dd1e70a8c63fb3a0f44e8e2d7987'
-- NodeOperatorRegistry / EigenLayer / proxy admin
TOPIC_OPERATOR_ADDED            = '\x0780dc183feb0e4f9714cd802b3c0a21894b7ccb4172c992569d2acb5d45f91c'
TOPIC_DEPOSITED_INTO_STRATEGY   = '\xf975a40e54653d58fd233016e025c986dcafad672f3ed5dd2a6c5a30528acd7d'
TOPIC_ROLE_GRANTED              = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_UPGRADED                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- Earn vaults (Nucleus)
TOPIC_VAULT_ENTER               = '\xea00f88768a86184a6e515238a549c171769fe7460a011d6fd0bcd48ca078ea4'
TOPIC_VAULT_EXIT                = '\xe0c82280a1164680e0cf43be7db4c4c9f985423623ad7a544fb76c772bdc6043'
TOPIC_EXCHANGE_RATE_UPDATED     = '\xa95bc6aba40bbc4d95fc35f118c4cd8b53fc5d5b89ed264002af03503a7a9439'

-- ===== Selectors =====
SEL_DEPOSIT                     = '\xd0e30db0'   -- deposit()
SEL_DEPOSIT_WITH_REFERRAL       = '\xc18d7cb7'   -- depositWithReferral(address)
SEL_BURN                        = '\x42966c68'   -- burn(uint256)
SEL_REPRICE                     = '\x7342bbd4'   -- reprice(uint256,uint256,uint256)
SEL_SWETH_RATE                  = '\xd68b2cb6'   -- swETHToETHRate()
SEL_RSWETH_RATE                 = '\xa7b9544e'   -- rswETHToETHRate()
SEL_CREATE_WITHDRAW_REQUEST     = '\x74dc9d1a'   -- createWithdrawRequest(uint256)
SEL_FINALIZE_WITHDRAWAL         = '\x5e15c749'   -- finalizeWithdrawal(uint256)
SEL_PROCESS_WITHDRAWALS         = '\x152fcb0c'   -- processWithdrawals(uint256)

-- ===== Ethereum mainnet (chain ID 1) — LST =====
SWETH                           = '\xf951e335afb289353dc249e82926178eac7ded78'
SWEXIT                          = '\x48c11b86807627af70a34662d4865cf854251663'
LST_DEPOSIT_MANAGER             = '\xb3d9cf8e163bbc840195a97e81f8a34e295b8f39'
LST_REPRICING_ORACLE            = '\x289d600447a74b952ad16f0bd53b8eaaac2d2d71'
LST_NODE_OPERATOR_REGISTRY      = '\x46ddc39e780088b1b146aba8cbbe15dc321a1a1d'
LST_ACCESS_CONTROL_MANAGER      = '\x625087d72c762254a72cb22cc2eca40da6b95eac'
LST_PROXY_ADMIN                 = '\x25eaf579ca2255faa5463c635eec28697b5b8846'
-- ===== Ethereum mainnet (chain ID 1) — LRT =====
RSWETH                          = '\xfae103dc9cf190ed75350761e95403b7b8afa6c0'
RSWEXIT                         = '\x58749c46ffe97e4d79508a2c781c440f4756f064'
LRT_DEPOSIT_MANAGER             = '\x5e6342d8090665be14eeb8154c8a87b7249a4889'
LRT_REPRICING_ORACLE            = '\xd5a73c748449a45cc7d9f21c7ed3ab9eb3d2e959'
LRT_NODE_OPERATOR_REGISTRY      = '\xaae0b305b3f1edde7b11b680d4fa9252f7a1c524'
LRT_ACCESS_CONTROL_MANAGER      = '\x796592b2092f7e150c48643da19dd2f28be3333f'
LRT_EIGENLAYER_MANAGER          = '\xc94cffd5249df4008a043ee61e13f19af16d0936'
LRT_PROXY_ADMIN                 = '\xd750b84845f1cadfeac63f96ec74635e949bfd14'
-- ===== Earn vaults + governance =====
EARN_ETH                        = '\x9ed15383940cc380faef0a75edace507cc775f22'
EARN_BTC                        = '\x66e47e6957b85cf62564610b76dd206bb04d831a'
RSW_BTC                         = '\x215dc1cc32d9d08a0081e55e55895c8cf006839a'
SW_BTC                          = '\x8db2350d78abc13f5673a411d4700bcf87864dde'
SWELL_TOKEN                     = '\x0a6e7ba5042b38349e437ec6db6214aec7b35676'
RSWELL_TOKEN                    = '\x358d94b5b2f147d741088803d932acb566acb7b6'
EIP1967_IMPL_SLOT               = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 9. Verification & sources

- **keccak-256:** every topic0/selector recomputed locally from the verbatim canonical signature and cross-checked against known ERC-20 `Transfer`/`Approval` + `deposit`/`burn` values.
- **Topics (✓):** observed verbatim in live `eth_getLogs` (40k-block windows) on `https://ethereum-rpc.publicnode.com` — `ETHDepositReceived` (swETH 18, rswETH 1), `Reprice` (swETH 18, rswETH 8), `WithdrawRequestCreated` (swEXIT 416, rswEXIT 17), `WithdrawalClaimed` (38), `WithdrawalsProcessed` (2), `SnapshotSubmittedV2`/`ReservesRecordedV2` (18 each LST, 8 LRT), vault `Exit` (1), SWELL `Transfer` (3182). Admin/rare events marked `abi`.
- **Selectors (bytecode):** PUSH4-dispatcher scan of the live impls (proxies resolved via EIP-1967 slot). `deposit`/`depositWithReferral`/`burn`/`reprice`/rate getters confirmed in swETH `0xce95…` and rswETH `0x4796…`; withdraw selectors in swEXIT `0x0245…`. Live `swETHToETHRate` ≈ 1.124, `rswETHToETHRate` ≈ 1.073.
- **Addresses:** resolved on-chain — core LST/LRT addresses from `AccessControlManager.swETH()/swEXIT()/DepositManager()/NodeOperatorRegistry()` and `<token>.AccessControlManager()`; RepricingOracle addresses from the `to` of live reprice txs (LST `0x804ec5…`, LRT `0xe6b95b…`); EigenLayerManager from `DepositManager.eigenLayerManager()`. All confirmed via `eth_getCode` + EIP-1967 slot reads. Swellchain + L1-bridge addresses from `build.swellnetwork.io` deploy docs.
- **Cross-chain:** swETH/rswETH/SWELL/earnETH existence-checked via `eth_getCode` on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon — all `0x` (absent). BNB `swETH`-symbol decoy noted.

Authoritative sources:

- [`SwellNetwork/v3-core-public`](https://github.com/SwellNetwork/v3-core-public) — `contracts/lst/**` and `contracts/lrt/**`: swETH, RswETH, swEXIT, RswEXIT, DepositManager, RepricingOracle, NodeOperatorRegistry, AccessControlManager, EigenLayerManager, SwellLib (roles).
- [Swell developer docs — contract addresses](https://build.swellnetwork.io/docs/developer-resources/contract-addresses) · [bridges](https://build.swellnetwork.io/docs/developer-resources/bridges).
- [Nucleus vault framework](https://docs.nucleusearn.io/nucleus-architecture/vault-framework) — BoringVault/Teller/Accountant (earn vaults).
- Explorers: [Etherscan swETH](https://etherscan.io/address/0xf951E335afb289353dc249e82926178EaC7DEd78) · [rswETH](https://etherscan.io/address/0xFAe103DC9cf190eD75350761e95403b7b8aFa6c0) · [SWELL](https://etherscan.io/address/0x0a6E7Ba5042B38349e437ec6Db6214AEC7B35676) · [Swellchain explorer](https://explorer.swellnetwork.io/).
