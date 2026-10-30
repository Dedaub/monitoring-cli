# Circle USYC (US Yield Coin) — Topics, Selectors, Addresses (Ethereum, BNB, Arc; NOT the other six targets)

**Status:** verified on 2026-10-30 against live RPC on all nine target chains, Circle's USYC smart-contract page, Arc's contract-address page and the verified sources of the deployed implementations (Sourcify full matches). Topics and selectors were recomputed as `keccak256(signature)` and checked against the bytecode of each live implementation. Addresses were existence-checked with `eth_getCode`; proxies were read from the EIP-1967 slot.
**Scope:** USYC, Circle's tokenized money-market fund share (ex-Hashnote), and its contracts: the **USYC token**, the **Teller** (USDC ⇄ USYC subscribe and redeem), the **Cross Chain Teller** (Ethereum ⇄ BNB over CCTP v2), **Entitlements** (the role authority) and the **Oracle** (NAV price) with its **PriceReporter**. Chains: Ethereum (1), BNB Smart Chain (56) and Arc (5042). Base (8453), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137) and Robinhood Chain (4663) have no USYC deployment. Topics and selectors are chain-agnostic; addresses are network-specific.

USYC is a permissioned, non-rebasing share token (6 decimals). Its price rises; supply moves only on subscribe and redeem. The Teller is an ERC-4626-style vault: it takes USDC and mints USYC at the Oracle price, and burns USYC to pay out USDC. Every call is gated by **Entitlements**, a Solmate `RolesAuthority`: only allow-listed addresses can hold or move USYC. On BNB there is no Teller: the Cross Chain Teller on Ethereum subscribes and sends the shares to BNB through CCTP v2, and the BNB Cross Chain Teller mints them there.

---

## 0. Contract families & versions

| Contract | Role | Pattern | Ethereum | BNB | Arc |
|----------|------|---------|----------|-----|-----|
| **USYC** | Share token. Mint/burn by minters with an allowance; `sweep`; `authority()` gate. | UUPS (EIP-1967) | ✅ | ✅ (older build) | ✅ (supply 0) |
| **Teller** | Subscribe (USDC → USYC) and redeem (USYC → USDC) at the Oracle price, with fees and per-account limits. | UUPS | ✅ | — | ✅ |
| **Cross Chain Teller** | Subscribe on Ethereum and deliver to BNB, or redeem from BNB, through CCTP v2 (`cctpToken()` = TokenMessengerV2, `cctpMessage()` = MessageTransmitterV2, `CCTP_VERSION()` = 1). | immutable | ✅ | ✅ | — |
| **Entitlements** | `RolesAuthority`: user roles and per-function capabilities. `authority()` of the token, Tellers and Oracle. | UUPS | ✅ | ✅ | ✅ |
| **Oracle** | USYC NAV price feed (`latestRoundData`, 18 dec). | UUPS | ✅ | — | ✅ |
| **PriceReporter** | Oracle `reporter()` on Ethereum. One `transmit` posts the price and mints the management fee in USYC to the fee recipient. On Arc the Oracle reporter is an EOA instead. | UUPS | ✅ | — | — (EOA) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 USYC token

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` | Mint = from `0x0`; burn = to `0x0`. No separate `Mint`/`Burn` event. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` | |
| `0x46980fca912ef9bcdbd36877427b6b90e860769f604e89c0e67720cece530d20` | `MinterConfigured(address minter, uint256 amount)` | **Not indexed.** Same topic0 as FiatToken `MinterConfigured`, other layout. |
| `0xed679328aebf74ede77ae09efcf36e90244f83643dadac1c2d9f0b21a46f6ab7` | `Sweep(address indexed recipient, address token, uint256 amount)` | Ethereum and Arc builds only. |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | Ethereum and Arc builds only. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` | |

The verified ABI also lists Hashnote-era events (`Deposit`, `Withdrawal`, `FeeProcessed`, `TradeToFiat`, `OracleSet`, `TellerSet`, `ManagementFeeSet`, `FeeRecipientSet`, `UnderlyingSet`). None of them is in any of the three live token implementations. Do not index them on the token.

### 1.2 Teller (Ethereum, Arc)

| topic0 | Event |
|--------|-------|
| `0x3672435a0cb047a194a35f62a596f99687620b27db9f6690553d4f7e5e3b98e4` | `Subscribe(address indexed from, address indexed receiver, uint256 assets, uint256 shares, uint256 price, uint256 fee)` |
| `0x8caf04742286d017f9ac3924388e188c73e6e5094311c5e59a61a7ef86dda8bf` | `Redeem(address indexed from, address indexed receiver, uint256 assets, uint256 shares, uint256 price, uint256 fee)` |
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed caller, address indexed owner, uint256 assets, uint256 shares)` (ERC-4626) |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed caller, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` (ERC-4626) |
| `0x8ddebf084bbd4e0dc80392d607eff26dddf8e449d62295574d55c484336264b5` | `LimitsSet(address indexed owner, uint256 subscribe, uint256 newSubscribe, uint256 redeem, uint256 newRedeem)` |
| `0xc1854e2f1655cc3b6b2494ac281ef36e0982a88e1cf28e448c1561fef413bbd9` | `AfterHourTradingSet(uint256 afterHourTrading, uint256 newAfterHourTrading)` |
| `0x04628abcaa6b1674651352125cb94b65b289145bc2bc4d67720bb7d966372f03` | `FeeManagerSet(address indexed feeManager, address indexed newFeeManager)` |
| `0x15d80a013f22151bc7246e3bc132e12828cde19de98870475e3fa70840152721` | `FeeRecipientSet(address indexed feeRecipient, address indexed newFeeRecipient)` |
| `0xc1d3048301c0d23629a2532c8defa6d68f8e1a0e4157918769e9fb1b2eeb888e` | `OracleSet(address indexed oracle, address indexed newOracle)` |
| `0xdaeb4cc3125e2ffb3c047d15e86dbcaac1e656b8d615dcbe28767cd8aac289ad` | `TreasurySet(address indexed owner, address treasury, address newTreasury)` |
| `0xa3645bbce20198b58ea94a91363b751fc1b741352849f1ae53c7ef9d97bb40ae` | `Sweep(address indexed token, address indexed treasury, uint256 amount, address indexed recipient)` |
| `0x38d16b8c…2700` / `0x8be0079c…57e0` / `0xbc7cd75a…2d3b` / `0x7f26b83f…2498` | `OwnershipTransferStarted` / `OwnershipTransferred` / `Upgraded` / `Initialized(uint8)` |

A subscribe emits `Deposit` + `Subscribe` in one transaction; a redeem emits `Withdraw` + `Redeem` (seen together in Ethereum tx `0x9e1a79da460b8e1d1b4405c09c9c21c616f982a2b6b7014c86cc2054ce035a8c`). The `Teller.Sweep` topic differs from the token `Sweep` topic.

### 1.3 Cross Chain Teller (Ethereum, BNB)

| topic0 | Event |
|--------|-------|
| `0xd7e4ea769da878204296b09c76ef6942a276da7e6e97d6141f20c5205f800666` | `Deposit(address indexed from, bytes32 indexed receiver, uint256 indexed destinationDomain, uint256 assets, uint256 shares)` |
| `0x3f693fff038bb8a046aa76d9516190ac7444f7d69cf952c4cbdc086fdef2d6fc` | `Redeem(address indexed from, address indexed receiver, uint256 indexed destinationDomain, uint256 shares)` |
| `0xdfc7365875beca2b9a99786151e35a53b3df048c22e4052a28ffa5ee1bd6c159` | `RedeemComplete(address indexed receiver, uint256 indexed sourceDomain, uint256 assets, uint256 shares)` |
| `0x19b7557ac82d0b4effc2b45d565820ea77693cea9f2f5803d4c77f1bb17099e7` | `Transfer(address indexed from, bytes32 indexed receiver, uint256 indexed destinationDomain, uint256 shares)` — **4 topics, not ERC-20 `Transfer`** |
| `0xcc76a3b6b5231655cc089a80564b180574f1c00b03491a9291de6dc9c92e08fa` | `DomainSet(uint256 indexed domain, bool status, bool newStatus, bytes32 caller, bytes32 newCaller)` |
| `0x3aabed068d9b747be27c5c3b73518a2dccf40bee9768178cba0eb6534a495a09` | `MaxFeeSet(uint256 maxFee, uint256 newMaxFee)` |
| `0x5d143c402fd7e71450bf0383aba407131bb8e2377c52a23268afdf9393f42564` | `MinFinalityThresholdSet(uint256 minFinalityThreshold, uint256 newMinFinalityThreshold)` |

### 1.4 Entitlements (RolesAuthority)

| topic0 | Event |
|--------|-------|
| `0x4c9bdd0c8e073eb5eda2250b18d8e5121ff27b62064fbeeeed4869bb99bc5bf2` | `UserRoleUpdated(address indexed user, uint8 indexed role, bool enabled)` — allow-list change |
| `0xa52ea92e6e955aa8ac66420b86350f7139959adfcc7e6a14eee1bd116d09860e` | `RoleCapabilityUpdated(uint8 indexed role, address indexed target, bytes4 indexed functionSig, bool enabled)` |
| `0x950a343f5d10445e82a71036d3f4fb3016180a25805141932543b83e2078a93e` | `PublicCapabilityUpdated(address indexed target, bytes4 indexed functionSig, bool enabled)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` / `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Paused(address)` / `Unpaused(address)` |
| `0x8be0079c…57e0` / `0xbc7cd75a…2d3b` | `OwnershipTransferred` / `Upgraded` |

### 1.5 Oracle (Ethereum, Arc)

| topic0 | Event |
|--------|-------|
| `0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f` | `AnswerUpdated(int256 indexed current, uint256 indexed roundId, uint256 updatedAt)` — new NAV price |
| `0x9eb97636dd72f6900ac13af43ef8f121ec7f80d9d5d65ec478a0c2750b203075` | `NextPriceReported(uint256 roundId, uint256 nextPrice)` |
| `0x8be0079c…57e0` / `0xbc7cd75a…2d3b` | `OwnershipTransferred` / `Upgraded` |

`BalanceReported(uint80,uint256,uint256)` is in the verified ABI but not in either live implementation.

### 1.6 PriceReporter (Ethereum)

| topic0 | Event |
|--------|-------|
| `0x4aa002eeef409b39c0a68c1e9974c8e847463e35e0032ec6d251786a3eb2bc2d` | `Transmitted(address indexed token, uint256 indexed roundId, uint256, uint256, uint256, uint256, uint256, uint256, uint256)` — price post + fee mint |
| `0x179ecbce9cdfa83dda282bee880489b3e7c644e7d2482d5cc5e6acbc0908ab8a` | `FeeScheduleSet(address indexed token, uint256, uint256)` |
| `0xed2bc9e951253aa4798e736092ab986269d0a97efe8c1df2be4fa19ffebbe4a0` | `TokenDetailsSet(address indexed token, address)` |
| `0x38d16b8c…2700` / `0x8be0079c…57e0` / `0xbc7cd75a…2d3b` | `OwnershipTransferStarted` / `OwnershipTransferred` / `Upgraded` |

Selectors: `transmit(address,uint256,uint256,uint256,uint256,uint256,bytes[])` `0x217fd7c3`, `transmitCall(address,bytes)` `0x46d2755e`, `transmitCallBatch(address[],bytes[])` `0x23b59384`, `setFeeSchedule(address,uint256,uint256)` `0xc9fe4554`, `setTokenDetails(address,address,bool,address)` `0x522de920`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 USYC token

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | Minter only (Teller / Cross Chain Teller), within allowance. |
| `0x42966c68` / `0x9dc29fac` | `burn(uint256)` / `burn(address,uint256)` | |
| `0x1dd319cb` | `burnFor(address,uint256)` | Ethereum and Arc builds only. |
| `0xc5c0db62` | `setMinterAllowance(address,uint256)` | Admin; emits `MinterConfigured`. |
| `0xa327039a` / `0x782ec779` | `incrementMinterAllowance(address,uint256)` / `decrementMinterAllowance(address,uint256)` | Ethereum and Arc builds only. |
| `0x8a6db9c3` | `minterAllowance(address)` | view |
| `0xdc2c256f` | `sweep(address,uint256,address)` | Ethereum and Arc builds only. |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | EIP-2612. |
| `0xbf7e214f` | `authority()` | Entitlements address. |
| `0x3659cfe6` / `0x4f1ef286` | `upgradeTo(address)` / `upgradeToAndCall(address,bytes)` | UUPS. |
| `0xf2fde38b` / `0x79ba5097` | `transferOwnership(address)` / `acceptOwnership()` | |

### 2.2 Teller

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256,address)` | Subscribe by USDC amount → `Deposit` + `Subscribe`. |
| `0x50921b23` / `0x54047f16` | `depositWithPermit(uint256,address,uint256,uint8,bytes32,bytes32)` / `depositWithPermit(uint256,address,uint256,bytes)` | Same, with a USDC permit. |
| `0x94bf804d` | `mint(uint256,address)` | Subscribe by share amount. |
| `0xba087652` | `redeem(uint256,address,address)` | Redeem by shares → `Withdraw` + `Redeem`. |
| `0xb460af94` | `withdraw(uint256,address,address)` | Redeem by USDC amount. |
| `0x037549cf` | `setLimits(address,uint56,uint56)` | Per-account limits. |
| `0x7adbf973` / `0x472d35b9` / `0xe74b981b` / `0xadfe0870` | `setOracle(address)` / `setFeeManager(address)` / `setFeeRecipient(address)` / `setTreasury(address,address)` | Admin. |
| `0x9c99ae58` | `setAfterHourTrading(uint256)` | Admin. |
| `0x07f35901` | `sweep(address,address,uint256,address)` | Admin. |
| `0x38d52e0f` / `0xa8d5fd65` / `0x7dc0d1d0` | `asset()` / `share()` / `oracle()` | Wiring views. |
| `0x6817c76c` / `0x01e1d114` | `mintPrice()` / `totalAssets()` | |

### 2.3 Cross Chain Teller

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5da5575b` | `deposit(uint256,bytes32,uint32)` | Ethereum: USDC in, shares sent to `destinationDomain` → `Deposit`. |
| `0x1acadfeb` | `transfer(uint256,bytes32,uint32)` | Send existing USYC to another domain → 4-topic `Transfer`. |
| `0xd63ee428` | `redeem(uint256,address,uint32)` | Redeem from the remote domain → `Redeem`. |
| `0x977a8ea5` | `redeemComplete(bytes,bytes)` | Takes a CCTP message + attestation → `RedeemComplete`. |
| `0xc3d14e7d` / `0x710e5d2f` / `0x3c6cffc9` / `0x9e3593b3` | `setDomain(uint32,bool,bytes32)` / `setMaxFee(uint256)` / `setMinFinalityThreshold(uint32)` / `setAllowances(uint256,uint256)` | Admin. |

### 2.4 Entitlements and Oracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x67aff484` / `0x44324b47` | `setUserRole(address,uint8,bool)` / `setUserRoleBatch(address[],uint8[],bool[])` | Allow-list writes → `UserRoleUpdated`. |
| `0x7d40583d` / `0xc6b0263e` | `setRoleCapability(uint8,address,bytes4,bool)` / `setPublicCapability(address,bytes4,bool)` | Capability writes. |
| `0xb7009613` / `0xea7ca276` / `0x06a36aee` | `canCall(address,address,bytes4)` / `doesUserHaveRole(address,uint8)` / `getUserRoles(address)` | Views. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | |
| `0xe588a2c3` / `0xa8f3ba1d` | `setUserRoleBroadcast(address,uint8,bool)` / `setUserRoleBatchBroadcast(address[],uint8[],bool[])` | **BNB build only** (not in the Ethereum or Arc implementations). |
| `0xbb024568` | `transmit(uint256,uint256)` | Oracle reporter posts a price → `AnswerUpdated`. |
| `0x23037a85` | `setNextPrice(uint256)` | → `NextPriceReported`. |
| `0xfeaf968c` / `0x668a0f02` / `0x010ec441` | `latestRoundData()` / `latestRound()` / `reporter()` | Views. |

---

## 3. Addresses — Ethereum (chain ID 1)

| Role | Address | Implementation | Owner |
|------|---------|----------------|-------|
| **USYC** | `0x136471a34f6ef19fE571EFFC1CA711fdb8E49f2b` (833 B) | `0xbf0f2f3aad6b99893d80c550fbacec915545eb92` | `0x13ff8cabb86edf94a2df4f98773bda4005182dd6` |
| **Teller** (USDC) | `0xeE35F963BFC71b51eC95147f26c030D674ea30e6` (183 B) | `0xb69ecb156dc0028198028c501340d5367845ca72` | `0x8b1a2015758578669e1ddbd98242648130a3a55b` |
| **Cross Chain Teller** (USDC) | `0x5dbeCcECEbCdC2ce3258f6E638373d2923560c7d` (7,920 B) | immutable | — (role-gated) |
| **Entitlements** | `0x902D906b8d988092213bE799B18Bd2cbd64F808C` (183 B) | `0xb59b15683710822c40df789a8e67ecfe30460c76` | `0x8fb098d65b38f8425de8f80ad54ee990fb5d2fc0` |
| **Oracle** | `0x74f2199AEb743f68f05943e5715A33EaF2b61f53` (833 B) | `0x6deaa761bc131ac5f1d562ee71819e846ef11624` | `0x1de107dc268f4be3ee688cf24c7742f6ebb19e98` |
| **PriceReporter** | `0x9fde717a21c5b272b8956d3aa0c3551e1ffd23d7` (833 B) | `0x88bd154df6ab08f71443e845841727162d88f65b` | `0x0a18ae6fc841226d611931d38ecec8893ac89f5a` |

Teller wiring (read live): `asset()` = USDC `0xA0b8…eB48`; `share()` = USYC; `oracle()` = the Oracle; `authority()` = Entitlements; `feeRecipient()` = `0xed96e247655361031aee6514cd1b89c7141b59d5`; `feeManager()` = `0x41ecf227a4ce2564e8fd1a01082cb56bb8e1344f`. Cross Chain Teller: `usdc()` = USDC, `usyc()` = USYC, `teller()` = the Teller, `cctpToken()` = TokenMessengerV2 `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d`, `cctpMessage()` = MessageTransmitterV2 `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64`, `minFinalityThreshold()` = 2,000, `maxFee()` = 0. USYC supply 34.77 M on 2026-10-30. Oracle price 1.141975 (round 544). `minterAllowance()` on USYC is unlimited (`2^256-1`) for the Teller, the PriceReporter and the reporter EOA `0xdbe01f447040f78ccbc8dfd101bec1a2c21f800d`; 0 for the Cross Chain Teller. The EOA calls `PriceReporter.transmit` (tx `0x6231372c5da230e922bfe40cc2b633e1ca77114ee1c1f2c80ad18572d94aa05e`: `AnswerUpdated`, USYC `Transfer(0x0 → 0xed96…59d5)`, `NextPriceReported`, `Transmitted`).

## 4. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | Implementation | Owner |
|------|---------|----------------|-------|
| **USYC** | `0x8D0fA28f221eB5735BC71d3a0Da67EE5bC821311` (833 B) | `0x191fb6f3ba332f1b8789caf67abbaba56147445b` (older build, §1.1) | `0xcd636d955a95385ec5e2776b167b92e89ef6f70e` |
| **Cross Chain Teller** (USDC) | `0xf38979E05650be7926EA07BB59C48Fb9b1DB3D08` (7,756 B) | immutable | — |
| **Entitlements** | `0x6B7d54003f73bE979cf92BF369432aC534853692` (176 B) | `0x8cadc832040bc66a0aeef9bf6b6d1bd7bcc5acdb` | `0x2d833ef0b55a7578e6f0f86fbf29674e4a250782` |

BNB Cross Chain Teller: `usdc()` = `0x0`, `teller()` = `0x0`, `usyc()` = BNB USYC; same CCTP v2 addresses as Ethereum. There is no Teller and no Oracle on BNB. USYC supply 2.03 B on 2026-10-30 (larger than Ethereum).

## 5. Addresses — Arc (chain ID 5042)

| Role | Address | Implementation | Owner |
|------|---------|----------------|-------|
| **USYC** | `0x8a5D989Bbb96929F689B0200f435f53dA42bF490` (183 B) | `0x7eb324c2b505fc778fa3480a587ebda70aa5f948` | `0x6a010e562eb99f2aea4a98e8d3d33556d4475c4b` |
| **Teller** (USDC) | `0x51A8CE47dC08ba5CD19c7aa84EA6fD6664f60f9b` (183 B) | `0x7ff36d935f598c23c75c3db6536133654beab1e6` | `0x0fc8d5671fd0778494600871c7f3dd8b74c55485` |
| **Entitlements** | `0xb69ecb156Dc0028198028c501340d5367845ca72` (183 B) | `0x6b765d649968358cb38ade91816b575207c38324` | `0x46a3b46d806c632e4c7b3e7fe4d677dabac9bc17` |
| **Oracle** | `0x4BC8d5aCD3d040d2903dD9C5B7048520c6ff537A` (183 B) | `0x88bd154df6ab08f71443e845841727162d88f65b` | `0x2d5c2d5d803d3953fb984d32d04f373ddc2c2927` |

Arc Teller wiring: `asset()` = USDC `0x3600…0000`; `share()` = USYC; `oracle()` = the Arc Oracle; `authority()` = Arc Entitlements; `feeRecipient()` = `0xdc2ff6e3b8afd22e360b2cd641ad705de61a8ac1`; `feeManager()` = `0x5f7fc0d52774dcefbf6a6a862b0a6de3abcac9bb`. **Arc USYC `totalSupply()` = 0** on 2026-10-30 and the Teller emitted no log in 40,000 blocks. The Arc Oracle posts the same price as Ethereum (1.141975, its own round counter 89). Arc Oracle `reporter()` = the EOA `0xdbe01f447040f78ccbc8dfd101bec1a2c21f800d` (no PriceReporter on Arc). Arc USYC `minterAllowance()` is unlimited for the Teller and for that EOA.

## 6. Cross-chain summary

| Chain | ID | USYC | Teller | Cross Chain Teller | Entitlements | Oracle |
|-------|----|------|--------|--------------------|--------------|--------|
| Ethereum | 1 | ✅ `0x1364…9f2b` | ✅ `0xeE35…30e6` | ✅ `0x5dbe…0c7d` | ✅ `0x902D…808C` | ✅ `0x74f2…1f53` (+ PriceReporter `0x9fde…23d7`) |
| BNB | 56 | ✅ `0x8D0f…1311` | — | ✅ `0xf389…3D08` | ✅ `0x6B7d…3692` | — |
| Arc | 5042 | ✅ `0x8a5D…F490` | ✅ `0x51A8…9f9b` | — | ✅ `0xb69e…ca72` | ✅ `0x4BC8…537A` |
| Base, Avalanche, Arbitrum, Optimism, Polygon PoS, Robinhood Chain | 8453, 43114, 42161, 10, 137, 4663 | — | — | — | — | — |

**Address collisions (same deployer nonce on other chains; not USYC):**
- `0x8D0f…1311` (BNB USYC literal) has 7,420 B of other code on Ethereum.
- `0xf389…3D08` (BNB Cross Chain Teller literal) is a Hashnote `AxelarMessengerSatellite` on Base (Sourcify).
- `0x6B7d…3692` (BNB Entitlements literal) is an `OptionTokenDescriptor` on Ethereum and a `RolesAuthorityProxy` on Base with the BNB Entitlements implementation. No USYC token sits on Base; Circle's page does not list Base.
- `0xb69e…ca72` (Arc Entitlements literal) is the **Ethereum Teller implementation**.
- `0x88bd…f65b` (Arc Oracle implementation) is the Ethereum PriceReporter implementation literal, with other code.

## 7. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| USYC, Teller, Entitlements, Oracle | **UUPS** (ERC1967Proxy; 833 B older proxy on Ethereum USYC/Oracle and BNB USYC, 183 B / 176 B elsewhere) | EIP-1967 impl slot set; admin slot `0x0`; `upgradeTo`/`upgradeToAndCall` in the implementation. | `owner()` (§3–§5), with `authority()` checks in some builds. |
| Cross Chain Teller | immutable | EIP-1967 slots `0x0`; no upgrade selector. | — |

Arc history (EIP-1967 slot read at sampled blocks and bisected): Entitlements set at block 4,656,757 (2026-06-11); USYC at 4,785,877, Oracle at 4,791,586 and Teller at 4,799,729 (all 2026-06-12). No upgrade since. Ethereum and BNB histories were not enumerated.

## 8. Detection invariants & gotchas

1. **Supply moves through the Tellers and the fee mint at each price post.** On Ethereum and Arc, a USYC `Transfer` from `0x0` pairs with Teller `Deposit` + `Subscribe`, or (fee) with Oracle `AnswerUpdated` + PriceReporter `Transmitted` and the Teller fee recipient as `to`. On BNB, a mint is expected in the same transaction as a CCTP v2 `MessageReceived` consumed by the BNB Cross Chain Teller (`redeemComplete` calls `receiveMessage`; no live BNB mint was seen in the sample). A USYC mint with none of these events in the transaction is an anomaly. The reporter EOA has an unlimited mint allowance on Ethereum and Arc: a mint sent directly by it, outside `transmit`, is top severity.
2. **`MinterConfigured` collides with FiatToken.** Same topic0 `0x46980fca…0d20`; USYC has no indexed fields (minter is in `data`). Key by emitter.
3. **The Cross Chain Teller `Transfer` is not an ERC-20 `Transfer`.** Its topic0 is `0x19b7557a…99e7` and it has 4 topics (`receiver` is `bytes32`, `destinationDomain` is a CCTP domain: Ethereum 0, BNB 17).
4. **Entitlements is the allow-list.** `UserRoleUpdated(user, role, enabled)` adds or removes a holder. A transfer to an address with no role reverts; no event fires. Watch `RoleCapabilityUpdated` and `PublicCapabilityUpdated`: they change who may call `mint`, `burn` and the Teller.
5. **Price comes from the Oracle.** `AnswerUpdated.current` (topic1, 18 decimals) is the new NAV. The sample had one update in 9,000 Ethereum blocks (about 30 hours). A large change, or a stale `updatedAt`, is a risk signal.
6. **Same price, separate oracles.** Ethereum and Arc Oracles posted the same answer (1,141,975,457,429,334,727) with different round ids.
7. **BNB holds most of the supply.** 2.03 B USYC on BNB against 34.8 M on Ethereum and 0 on Arc (2026-10-30). Watch the BNB Cross Chain Teller for large `RedeemComplete` and the Ethereum one for `Deposit` to domain 17.
8. **Teller limits and fees.** `LimitsSet`, `FeeManagerSet`, `FeeRecipientSet`, `OracleSet`, `TreasurySet` and `AfterHourTradingSet` are admin changes. `Sweep` on the Teller moves the USDC out to the treasury.
9. **Builds differ by chain.** BNB USYC lacks `Sweep`, `OwnershipTransferStarted`, `burnFor` and the allowance increment and decrement functions. BNB Entitlements has the broadcast role functions that Ethereum and Arc lack.
10. **Arc is staged.** Every Arc contract exists, but supply is 0 and the Teller has no traffic.

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== USYC token topics =====
TOPIC_TRANSFER                  = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_USYC_MINTER_CONFIGURED    = '\x46980fca912ef9bcdbd36877427b6b90e860769f604e89c0e67720cece530d20'
TOPIC_USYC_SWEEP                = '\xed679328aebf74ede77ae09efcf36e90244f83643dadac1c2d9f0b21a46f6ab7'
TOPIC_UPGRADED                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFER_STARTED= '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
TOPIC_OWNERSHIP_TRANSFERRED     = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- ===== Teller topics =====
TOPIC_TELLER_SUBSCRIBE          = '\x3672435a0cb047a194a35f62a596f99687620b27db9f6690553d4f7e5e3b98e4'
TOPIC_TELLER_REDEEM             = '\x8caf04742286d017f9ac3924388e188c73e6e5094311c5e59a61a7ef86dda8bf'
TOPIC_TELLER_DEPOSIT_4626       = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_TELLER_WITHDRAW_4626      = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_TELLER_LIMITS_SET         = '\x8ddebf084bbd4e0dc80392d607eff26dddf8e449d62295574d55c484336264b5'
TOPIC_TELLER_AFTER_HOUR_SET     = '\xc1854e2f1655cc3b6b2494ac281ef36e0982a88e1cf28e448c1561fef413bbd9'
TOPIC_TELLER_FEE_MANAGER_SET    = '\x04628abcaa6b1674651352125cb94b65b289145bc2bc4d67720bb7d966372f03'
TOPIC_TELLER_FEE_RECIPIENT_SET  = '\x15d80a013f22151bc7246e3bc132e12828cde19de98870475e3fa70840152721'
TOPIC_TELLER_ORACLE_SET         = '\xc1d3048301c0d23629a2532c8defa6d68f8e1a0e4157918769e9fb1b2eeb888e'
TOPIC_TELLER_TREASURY_SET       = '\xdaeb4cc3125e2ffb3c047d15e86dbcaac1e656b8d615dcbe28767cd8aac289ad'
TOPIC_TELLER_SWEEP              = '\xa3645bbce20198b58ea94a91363b751fc1b741352849f1ae53c7ef9d97bb40ae'
-- ===== Cross Chain Teller topics =====
TOPIC_CCT_DEPOSIT               = '\xd7e4ea769da878204296b09c76ef6942a276da7e6e97d6141f20c5205f800666'
TOPIC_CCT_REDEEM                = '\x3f693fff038bb8a046aa76d9516190ac7444f7d69cf952c4cbdc086fdef2d6fc'
TOPIC_CCT_REDEEM_COMPLETE       = '\xdfc7365875beca2b9a99786151e35a53b3df048c22e4052a28ffa5ee1bd6c159'
TOPIC_CCT_TRANSFER              = '\x19b7557ac82d0b4effc2b45d565820ea77693cea9f2f5803d4c77f1bb17099e7'
TOPIC_CCT_DOMAIN_SET            = '\xcc76a3b6b5231655cc089a80564b180574f1c00b03491a9291de6dc9c92e08fa'
TOPIC_CCT_MAX_FEE_SET           = '\x3aabed068d9b747be27c5c3b73518a2dccf40bee9768178cba0eb6534a495a09'
TOPIC_CCT_MIN_FINALITY_SET      = '\x5d143c402fd7e71450bf0383aba407131bb8e2377c52a23268afdf9393f42564'
-- ===== Entitlements topics =====
TOPIC_ENT_USER_ROLE_UPDATED     = '\x4c9bdd0c8e073eb5eda2250b18d8e5121ff27b62064fbeeeed4869bb99bc5bf2'
TOPIC_ENT_ROLE_CAPABILITY       = '\xa52ea92e6e955aa8ac66420b86350f7139959adfcc7e6a14eee1bd116d09860e'
TOPIC_ENT_PUBLIC_CAPABILITY     = '\x950a343f5d10445e82a71036d3f4fb3016180a25805141932543b83e2078a93e'
TOPIC_PAUSED                    = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                  = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
-- ===== Oracle topics =====
TOPIC_ORACLE_ANSWER_UPDATED     = '\x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'
TOPIC_ORACLE_NEXT_PRICE         = '\x9eb97636dd72f6900ac13af43ef8f121ec7f80d9d5d65ec478a0c2750b203075'
TOPIC_REPORTER_TRANSMITTED      = '\x4aa002eeef409b39c0a68c1e9974c8e847463e35e0032ec6d251786a3eb2bc2d'
TOPIC_REPORTER_FEE_SCHEDULE_SET = '\x179ecbce9cdfa83dda282bee880489b3e7c644e7d2482d5cc5e6acbc0908ab8a'
-- ===== Selectors =====
SEL_USYC_MINT                   = '\x40c10f19'
SEL_USYC_BURN                   = '\x42966c68'
SEL_USYC_BURN_FROM              = '\x9dc29fac'
SEL_USYC_BURN_FOR               = '\x1dd319cb'
SEL_USYC_SET_MINTER_ALLOWANCE   = '\xc5c0db62'
SEL_TELLER_DEPOSIT              = '\x6e553f65'
SEL_TELLER_DEPOSIT_PERMIT_VRS   = '\x50921b23'
SEL_TELLER_DEPOSIT_PERMIT_BYTES = '\x54047f16'
SEL_TELLER_MINT                 = '\x94bf804d'
SEL_TELLER_REDEEM               = '\xba087652'
SEL_TELLER_WITHDRAW             = '\xb460af94'
SEL_CCT_DEPOSIT                 = '\x5da5575b'
SEL_CCT_TRANSFER                = '\x1acadfeb'
SEL_CCT_REDEEM                  = '\xd63ee428'
SEL_CCT_REDEEM_COMPLETE         = '\x977a8ea5'
SEL_ENT_SET_USER_ROLE           = '\x67aff484'
SEL_ENT_SET_USER_ROLE_BATCH     = '\x44324b47'
SEL_ENT_SET_ROLE_CAPABILITY     = '\x7d40583d'
SEL_ENT_SET_PUBLIC_CAPABILITY   = '\xc6b0263e'
SEL_ORACLE_TRANSMIT             = '\xbb024568'
SEL_ORACLE_SET_NEXT_PRICE       = '\x23037a85'
SEL_REPORTER_TRANSMIT           = '\x217fd7c3'
SEL_UPGRADE_TO                  = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL         = '\x4f1ef286'
-- ===== Addresses =====
ETH_USYC                        = '\x136471a34f6ef19fe571effc1ca711fdb8e49f2b'
ETH_USYC_TELLER                 = '\xee35f963bfc71b51ec95147f26c030d674ea30e6'
ETH_USYC_CC_TELLER              = '\x5dbeccecebcdc2ce3258f6e638373d2923560c7d'
ETH_USYC_ENTITLEMENTS           = '\x902d906b8d988092213be799b18bd2cbd64f808c'
ETH_USYC_ORACLE                 = '\x74f2199aeb743f68f05943e5715a33eaf2b61f53'
ETH_USYC_PRICE_REPORTER         = '\x9fde717a21c5b272b8956d3aa0c3551e1ffd23d7'
USYC_REPORTER_EOA               = '\xdbe01f447040f78ccbc8dfd101bec1a2c21f800d'   -- Ethereum and Arc
BNB_USYC                        = '\x8d0fa28f221eb5735bc71d3a0da67ee5bc821311'
BNB_USYC_CC_TELLER              = '\xf38979e05650be7926ea07bb59c48fb9b1db3d08'
BNB_USYC_ENTITLEMENTS           = '\x6b7d54003f73be979cf92bf369432ac534853692'
ARC_USYC                        = '\x8a5d989bbb96929f689b0200f435f53da42bf490'
ARC_USYC_TELLER                 = '\x51a8ce47dc08ba5cd19c7aa84ea6fd6664f60f9b'
ARC_USYC_ENTITLEMENTS           = '\xb69ecb156dc0028198028c501340d5367845ca72'
ARC_USYC_ORACLE                 = '\x4bc8d5acd3d040d2903dd9c5b7048520c6ff537a'
```

## 10. Verification & sources

How constants were verified (2026-10-30):

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify-verified ABIs of the Ethereum implementations (USYC `0xbf0f…eb92`, Teller `0xb69e…ca72`, Oracle `0x6dea…1624`, Cross Chain Teller `0x5dbe…0c7d`, PriceReporter `0x88bd…f65b`) and the BNB Entitlements implementation `0x8cad…cdb`. Each listed topic and selector was then searched in the bytecode of every live implementation on Ethereum, BNB and Arc; build differences are stated in the tables. Events in the verified ABIs that no live implementation contains are named and excluded.
- **Live logs:** Ethereum (blocks 26,297,296–26,306,296): USYC `Transfer` 4; Teller `Withdraw` + `Redeem` (tx `0x9e1a…5a8c`); Oracle `AnswerUpdated` (3 topics) and `NextPriceReported`. Arc (40,000 blocks to 28,664,061): Oracle `AnswerUpdated` and `NextPriceReported`; 0 Teller logs. BNB (40,000 blocks to 130,684,847): 0 logs on USYC and on the Cross Chain Teller.
- **Addresses:** from Circle's USYC smart-contract page and Arc's contract-address page; `eth_getCode` for all twelve literals on all nine chains (collisions in §6). EIP-1967 slots, `owner()`, `authority()`, Teller and Cross Chain Teller wiring, `totalSupply()` and `latestRoundData()` read with `eth_call`.

Authoritative sources:
- [USYC smart contracts](https://developers.circle.com/tokenized/usyc/smart-contracts) — address list
- [Arc contract addresses](https://docs.arc.io/arc/references/contract-addresses) (Stablecoins → USYC, Entitlements, Teller)
- [Sourcify](https://sourcify.dev) verified sources for the implementations above
- Explorers — [Etherscan USYC](https://etherscan.io/token/0x136471a34f6ef19fe571effc1ca711fdb8e49f2b) · [BscScan USYC](https://bscscan.com/token/0x8d0fa28f221eb5735bc71d3a0da67ee5bc821311) · [Arc explorer USYC](https://explorer.arc.io/address/0x8a5D989Bbb96929F689B0200f435f53dA42bF490)
