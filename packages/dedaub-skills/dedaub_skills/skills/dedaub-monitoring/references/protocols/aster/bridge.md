# Aster Deposit Bridge — Topics, Selectors, Addresses (BNB, Ethereum, Arbitrum; legacy ApolloX treasuries)

**Status:** verified on 2026-10-30 against live RPC on BNB (56), Ethereum (1) and Arbitrum (42161), `eth_getCode` on all nine target chains, the Sourcify-verified sources of every contract listed here, the official Aster "Smart Contracts" page, and the DefiLlama `astherus` and `apollox` TVL adapters.
**Scope:** the custody contracts that take user deposits for the off-chain Aster Pro order book and pay withdrawals: the current **`AstherusVault`** ("Aster Deposit Bridge") on BNB, Ethereum and Arbitrum, its timelocks and withdrawal-signature validators, and the legacy **`ApolloxExchangeTreasury`** contracts that still hold and pay out funds. Topics and selectors are chain-agnostic. Addresses are network-specific. Aster also lists Solana and Sui vaults; those are not EVM and are out of scope.

Aster (the merged ApolloX + Astherus) runs its perpetuals order book off chain. On chain there is no trade or position event. A user deposits into a per-chain **vault** (`Deposit`). An operator later pays a withdrawal from the same vault (`Withdraw`). Each payout carries three signatures (user, business and ledger) that a separate `AsterWithdrawValidator` checks. A rolling **hourly USD limit** auto-pauses the vault when it is crossed.

The vaults are UUPS proxies. Only the immutable `TIMELOCK_ADDRESS` (an `AstherusTimelock`, 6-hour minimum delay) can upgrade them. The BNB vault is the largest. On 2026-10-30 it held about 102.5M USDF, 67.5M USD1, 60.9M USDT, 8.7M USDC, 2,878 BNB, 23.8k asBNB and 278 BTCB. The Ethereum vault held 100.7M USDT, 13.9M USDC and 1,185 ETH. The Arbitrum vault held 22.9M USDT, 21.5M USDC and 1,153 ETH.

---

## 0. Contract families & versions

| Contract | Chains | Role | Proxy? |
|----------|--------|------|--------|
| **AstherusVault** (current) | BNB, Ethereum, Arbitrum | User deposits; operator withdrawals with 3-signature check; hourly limit; fee sweep. BNB build adds `depositUSDF` and `depositAsBNB` zaps. | **UUPS** `ERC1967Proxy` (855 B) |
| **AstherusTimelock** | BNB, Ethereum, Arbitrum | OpenZeppelin `TimelockController` + `scheduleTask`/`executeTask`. Sole upgrader of the vault. `getMinDelay()` = 21,600 s. | No |
| **AsterWithdrawValidator** | BNB, Ethereum, Arbitrum | `withdrawCheck` verifies user (EIP-712), business and ledger signatures. Immutable `WITHDRAW_VALIDATOR` in the vault. | No |
| **ApolloxExchangeTreasury v2** | BNB | Legacy ApolloX deposit/claim treasury. Still pays `Claim`. | No |
| **ApolloxExchangeTreasury** (v1-style) | Ethereum | Legacy; claim-only (no `deposit`). Still pays `Claimed`. | No |
| **ApolloxExchangeTreasury** (v2-style) | Arbitrum | Legacy; same ABI as BNB v2. | No |
| **ApolloxExchangeTreasury v1** | BNB | Legacy, solc 0.5.16. Nearly empty. `counterParty()` = the BNB v2 treasury. | No |

The Arbitrum and Ethereum vault implementations are an older build. They still expose the validator-set withdrawal `withdraw(uint256,(address,uint256)[],(address,uint256,uint256,address),bytes[])` and the old 5-field `Withdraw` event. Live payouts on all three chains use the new `Withdraw(id,to,currency,amount,fee)` event.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

"Live" counts: BNB vault blocks head−5,000…head; Ethereum vault head−20,000…head; Arbitrum vault head−200,000…head (2026-10-30).

### 1.1 AstherusVault

| topic0 | Event | Live (BNB / ETH / ARB) |
|--------|-------|------------------------|
| `0x18081cde2fa64894914e1080b98cca17bb6d1acf633e57f6e26ebdb945ad830b` | `Deposit(address indexed account,address indexed currency,bool isNative,uint256 amount,uint256 broker)` | 51 / 657 / 299 |
| `0xfe7813e2866053d5c3938554e517b554fce6666a6561bed9eaa7419b29fa9b68` | `Withdraw(uint256 indexed id,address indexed to,address indexed currency,uint256 amount,uint256 fee)` | 43 / 484 / 166 |
| `0x81b8021db23057eb1dfd88796511e506e0a736c5d4758e29c39aa74b8509bcee` | `Withdraw(uint256 indexed id,address indexed to,address indexed currency,bool isNative,uint256 amount)` | old ETH/ARB build and legacy treasuries only |
| `0x869baec015e2c7c07b86bc04511ae11388341001134b9f28df8e96bc6b33d26b` | `WithdrawCanceled(uint256 indexed id,bytes32 userDigest)` | operator cancel |
| `0x88655d4ce709d20f0d4615ecbb09d91c03964e7c93cf29be9912b6467d8449d1` | `WithdrawPaused(address indexed trigger,address indexed currency,uint256 amount,uint256 amountUsd)` | **hourly limit hit → vault paused** |
| `0xe25b4595fcf79866f7cbb640445a5235d8b71d78ebf254ac1d69619028a05722` | `DepositFailed(address indexed account,address indexed currency,bool isNative,uint256 amount)` | |
| `0x1a5f279a9c22a4ad34f4070b85334882f8a945656329d87746c0f2c8806ba00e` | `ReceiveETH(address indexed from,address indexed to,uint256 amount)` | plain native transfer (ETH: 4) |
| `0x768860cd8341946923182b97157e5aab4ca296b545a5055fbdce5e55bc1ab578` | `WithdrawFee(address indexed currency,uint256 amount,address receiver)` | **admin fee sweep** |
| `0xa71f31d4b603b19554862f19f43a8800f15ae23017b823ebe92eab7c3b20bf92` | `UpdateHourlyLimit(uint256 oldHourlyLimit,uint256 newHourlyLimit)` | admin |
| `0x9a8c7cf8e1b2219d5ec46a06b8dd00ae4e22d22f7392999d4bb4000aa8cfde5e` | `UpdateProofHourlyLimit(uint256 oldHourlyLimit,uint256 newHourlyLimit)` | admin |
| `0x5e44b8d769cde64991e4725cd0276d385af04c64b64cba70267e0ed4d42350a0` | `AddToken(address indexed currency,address indexed priceFeed,bool fixedPrice)` | token listing |
| `0x4eb129c82dcd3eedb52df2b0e6fb4cfa41ac64ee9d63ff081acbb1877e85d79b` | `RemoveToken(address indexed currency)` | |
| `0x3cb07f1fe3c4f446f6d78f36fb133221584a679f2f3165aa763950d06f91ad9e` | `TokenHashChanged(address indexed tokenAddress,bytes32 tokenHash)` | |
| `0x8dab9a2a283c7b6ba069309ca8068fffe547519cf6029bad20d31ce4ac81d210` | `ValidatorAdd(bytes32 indexed hash,uint256 validatorNum,uint256 totalPower)` | ETH/ARB build |
| `0x0c8edcc44f2d00a6f32a5133026661f75c80a03eba7393a03f76e369c7716f12` | `ValidatorRemove(bytes32 indexed hash,uint256 validatorNum)` | ETH/ARB build |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | **withdrawals halted** |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | **impl rotation** |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role,address indexed account,address indexed sender)` | |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role,address indexed account,address indexed sender)` | |

### 1.2 AstherusTimelock (watch for vault upgrades)

| topic0 | Event |
|--------|-------|
| `0x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca` | `CallScheduled(bytes32 indexed id,uint256 indexed index,address target,uint256 value,bytes data,bytes32 predecessor,uint256 delay)` |
| `0xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58` | `CallExecuted(bytes32 indexed id,uint256 indexed index,address target,uint256 value,bytes data)` |
| `0xbaa1eb22f2a492ba1a5fea61b8df4d27c6c8b5f3971e63bb58fa14ff72eedb70` | `Cancelled(bytes32 indexed id)` |
| `0x11c24f4ead16507c69ac467fbd5e4eed5fb5c699626d2cc6d66421df253886d5` | `MinDelayChange(uint256 oldDuration,uint256 newDuration)` |
| `0x8494f77d4a61d84f47d72ac087b427d85a3c3783e2b970f0a142019b5d5e1b7e` | `MaxDelayChanged(uint256 oldValue,uint256 newValue)` |

### 1.3 Legacy ApolloxExchangeTreasury

| topic0 | Event | Emitter / live |
|--------|-------|----------------|
| `0xc977beb5adf839e24d3d75d83f7781f425347b483f62742ad0d5f08c9390648d` | `Claim(uint256 indexed id,address indexed to,address indexed currency,bool isETH,uint256 amount)` | BNB v2 (13 in 400k blocks), ARB (5 in 3M blocks) |
| `0xbdf2c3f6edfac9e3d933ce8519d4cafffb974eb01531df50efe58090b4b1fd90` | `Claimed(uint256 indexed id,address indexed to,bool isETH,address currency,uint256 amount,uint256 deadline)` | ETH (170 in 200k blocks), BNB v1 |
| `0x18081cde…d830b` | `Deposit(address indexed account,address indexed currency,bool isETH,uint256 amount,uint256 broker)` | BNB v2, ARB — **same topic0 as the vault** |
| `0x81b8021d…9bcee` | `Withdraw(uint256 indexed id,address indexed to,address indexed currency,bool isETH,uint256 amount)` | BNB v2, ARB |
| `0x5a438a2092d27293a83dccc949b06566503615797dcb9afab851a64763fa33f0` | `ClaimPaused(address indexed trigger,address indexed currency,uint256 amount,uint256 amountUsd)` | BNB v2, ARB — hourly limit |
| `0xfa77df1ea6d4af3788b21e52a0a92d6894cd2c8ffccce06ea7fb736542153861` | `TransferToCounterParty(address indexed currency,bool isETH,uint256 amount)` | BNB v2, ARB — **bulk move out** |
| `0x33278ebf7b841e996e09580bfa7a0279c875902fe042c3d102a8d051c30dc733` | `TransferToCounterParty(bool isETH,address currency,uint256 amount)` | ETH, BNB v1 — **bulk move out** |
| `0xf32a9f77675fd5917534c7746608fd3e309eac68fbdcbf5925e24ca97a704396` | `ReceiveEther(address sender,uint256 amount)` | ETH (54) |
| `0x100ee7bc9f90ed0d187ec16b9532449ca9eee13c1d00463b5759a771c1b49fb4` | `NewCounterParty(address oldCounterParty,address newCounterParty)` | all |
| `0x81b88ce749f5ea02a8cec52c72adf48d4bae4bb5c855faaae1a248b327ff00ca` | `NewTruthHolder(address oldTruthHolder,address newTruthHolder)` | all — **claim signer rotated** |
| `0xf1e04d73c4304b5ff164f9d10c7473e2a1593b740674a6107975e2a7001c1e5c` | `NewOperator(address oldOperator,address newOperator)` | all |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner,address indexed newOwner)` | all |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` | ETH, BNB v1 |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 AstherusVault

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0efe6a8b` | `deposit(address,uint256,uint256)` | `(currency, amount, broker)`. |
| `0x608fc37a` | `depositNative(uint256)` | payable; `currency` logged as the `NATIVE` sentinel. |
| `0xcf4a0c5e` | `depositFor(address,address,uint256,uint256)` | `DEPOSIT_ROLE` only; credits `forAddress`. |
| `0x29a9228c` | `depositUSDF(uint256,uint256,uint256)` | BNB only. Mints USDF from USDT via `USDF_EARN`, then deposits. |
| `0x2a6c263f` | `depositAsBNB(address,uint256,uint256,uint256)` | BNB only. Mints asBNB via `ASBNB_MINTER`, then deposits. |
| `0x67212e3b` | `batchedDepositWithPermit((address,address,uint256,uint256,uint256,bytes)[])` | Arbitrum build only. |
| `0x224a5fdd` | `withdraw(address,uint256,(address,uint256,uint256,uint256),(uint256,address,bytes32,uint8,uint8,uint8,uint256),(bytes,bytes,bytes))` | BNB build; `OPERATE_ROLE`; raw-amount (EIP-8056) variant. |
| `0x0cd4b1fe` | `withdraw(address,uint256,(address,uint256,uint256,uint256),(uint256,address,bytes32,uint8,uint8,uint8),(bytes,bytes,bytes))` | all builds; `OPERATE_ROLE`; 3-signature check. |
| `0xe79158b1` | `withdraw(uint256,(address,uint256)[],(address,uint256,uint256,address),bytes[])` | ETH/ARB build; validator-set path. |
| `0x13874d37` | `cancelWithdraw(uint256,bytes32)` | `OPERATE_ROLE`. |
| `0x9cb7bd2b` | `withdrawFee(address[],uint256[],address)` | `ADMIN_ROLE`; sweeps accrued fees. |
| `0x413bcb44` | `updateHourlyLimit(uint256)` | `ADMIN_ROLE`; 8-decimal USD. |
| `0x69959ca0` / `0xf6e20adc` | `addToken(address,address,uint256,bool,uint8,uint8)` / `addToken(...,string)` | `TOKEN_ROLE`. |
| `0x5fa7b584` | `removeToken(address)` | `ADMIN_ROLE`. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | `PAUSE_ROLE` / `PAUSE_ROLE` or `UNPAUSE_ROLE`. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | `TIMELOCK_ADDRESS` only. |
| views | `TIMELOCK_ADDRESS()` `0x431c1830`, `WITHDRAW_VALIDATOR()` `0x92eda24b`, `USDF_EARN()` `0x08bfa087`, `ASBNB_MINTER()` `0xec66a6fd`, `hourlyLimit()` `0x79a3c6ed` | |

### 2.2 AsterWithdrawValidator / AstherusTimelock

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2ff70030` | `withdrawCheck((address,uint256,uint256,uint256),(uint256,address,bytes32,uint8,uint8,uint8),(bytes,bytes,bytes))` | view → user digest. |
| `0x2ad92c5a` | `withdrawCheck(...,(uint256,address,bytes32,uint8,uint8,uint8,uint256),(bytes,bytes,bytes))` | BNB raw-amount variant. |
| `0x4405fda8` / `0x5181bb25` | `BUSINESS_SIGNER()` / `LEDGER_SIGNER()` | immutable signer addresses. |
| `0x01d5062a` | `schedule(address,uint256,bytes,bytes32,bytes32,uint256)` | timelock. |
| `0x134008d3` | `execute(address,uint256,bytes,bytes32,bytes32)` | timelock. |
| `0xf1eccc4c` / `0xf4b6fc13` | `scheduleTask(address,string,bytes)` / `executeTask(address,string,bytes)` | timelock helpers. |
| `0xf27a0c92` | `getMinDelay()` | view → 21,600. |

### 2.3 Legacy ApolloxExchangeTreasury

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xbe27b22c` | `claim(bytes,bytes)` | `(message, signature)` signed by `truthHolder`. |
| `0x50fbe2d9` | `withdraw(bytes,bytes)` | BNB v2 / ARB. |
| `0x0efe6a8b` / `0x5358fbda` | `deposit(address,uint256,uint256)` / `depositETH(uint256)` | BNB v2 / ARB. |
| `0x89c9e1ac` | `transferToCounterParty(bool,address,uint256)` | owner/operator; moves funds to `counterParty`. |
| `0xbfbd7f30` / `0xf6dd2353` | `changeTruthHolder(address)` / `_changeTruthHolder(address)` | v2 / v1 naming. |
| `0xa720969f` / `0x2c453bdf` / `0x570ca735` | `truthHolder()` / `counterParty()` / `operator()` | views. |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| **AstherusVault** (proxy) | `0x128463A60784c4D3f46c23Af3f65Ed859Ba87974` | Aster Deposit Bridge (official list). |
| AstherusVault impl | `0x9a183b1e8939d7a7bd49c47ab0ad540f8aa07360` | `AstherusVault`, solc 0.8.25. |
| AstherusTimelock | `0xdd95d454ea23de750aa46d093c7b04e3f5b8b6b5` | `TIMELOCK_ADDRESS()`; proposer/executor = Safe `0xa8c0…1c3f` and itself. |
| AsterWithdrawValidator | `0xea1f2292b8c741db0d82286edadfb0d2436b19f1` | `WITHDRAW_VALIDATOR()`. |
| Admin Safe (4-of-7) | `0xa8c0c6ee62f5ad95730fe23ccf37d1c1ffaa1c3f` | `DEFAULT_ADMIN_ROLE` + `ADMIN_ROLE` + `TOKEN_ROLE` on the vault. |
| **ApolloxExchangeTreasury v2** | `0xcEF2dD45Da08b37fB1c2f441d33c2eBb424866A4` | Legacy. Held 38.0M USDT, 912k USDC, 259k BUSD, 2,997 BNB, 499 ETH on 2026-10-30. Hourly limit $5M. |
| ApolloxExchangeTreasury v1 | `0xe2e912f0b1b5961be7cb0d6dbb4a920ace06cd99` | Legacy, ~empty. |
| ApolloX owner Safe (4-of-7) | `0x60ede4402a34762d608ad9ba7bd3797f5bfe544c` | `owner()` = `operator()` = `counterParty()` of BNB v2 and Arbitrum treasuries. |

Vault roles (BNB, `getRoleMember`): `PAUSE_ROLE` 4 EOAs (`0xf517…3777`, `0x168d…c114`, `0x77bd…752e`, `0x39a5…156a`); `UNPAUSE_ROLE` `0xb453…6512`; `OPERATE_ROLE` 5 EOAs (`0xef9c…77ab`, `0x1cbb…8c22`, `0x6348…8a93`, `0xe60b…c8c0`, `0x0744…7b89`); `DEPOSIT_ROLE` `0x0008…369c`, `0x9886…d090`. `hourlyLimit` = $30M.

## 4. Addresses — Ethereum mainnet (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **AstherusVault** (proxy) | `0x604DD02d620633Ae427888d41bfd15e38483736E` | Official list. `hourlyLimit` = $30M. |
| AstherusVault impl | `0x2cc878ac49c3bf8b0f2b053af7845ba6590eec4f` | `AstherusVault` (older build). |
| AstherusTimelock | `0x20f4e8cbf7c0062464e1496164b6847112ec41bf` | 21,600 s. |
| AsterWithdrawValidator | `0x1006511304aada32ea80a259dcf140a6ecbd30dc` | |
| Admin Safe (4-of-7) | `0x1fe3fe2ddd19ab58b0c56054a5af217afb27ecea` | `DEFAULT_ADMIN_ROLE` + `ADMIN_ROLE` on the vault. |
| **ApolloxExchangeTreasury** | `0xb40EEd68d7d6B3b6d6f4E93DE6239B7C53EFc786` | Legacy, claim-only. Held 20.6M USDT, 1.85M USDC, 1,000 ETH. Owner Safe `0x9b7c…bbec` (3-of-6). |

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **AstherusVault** (proxy) | `0x9E36CB86a159d479cEd94Fa05036f235Ac40E1d5` | Official list. `hourlyLimit` = $20M. |
| AstherusVault impl | `0x896a363007ba67f677eb2d1e8cc00f8b61697d1a` | `AstherusVault` (older build + permit batch). |
| AstherusTimelock | `0xf2edc8b3b6a16e3de962027c7bb80192e807b44d` | Also holds `DEFAULT_ADMIN_ROLE` on the vault. |
| AsterWithdrawValidator | `0x3d2068e2e0d505876c57a236bb65dfd42cbf8937` | |
| Admin Safe (4-of-7) | `0xa8c0c6ee62f5ad95730fe23ccf37d1c1ffaa1c3f` | Same address and threshold as on BNB. |
| **ApolloxExchangeTreasury** | `0xbad4ccc91ef0dfffbcab1402c519601fbaf244ef` | Legacy. Held 596k USDT, 505k USDC, 51 ETH. Hourly limit $1M. |

## 6. Other target chains

Base (8453), Avalanche (43114), Optimism (10), Polygon (137), Robinhood Chain (4663) and Arc (5042) have no Aster vault. **Same-address traps:** the deployer reused nonces, so several of these addresses hold **different** code on other chains (§9.6). The Polygon copies of `0xe2e9…cd99` and `0xb40E…c786` (6,427 B) are not Aster vaults with funds.

## 7. Cross-chain summary

| Chain (ID) | AstherusVault | Timelock | Validator | Legacy treasury |
|------------|---------------|----------|-----------|-----------------|
| BNB (56) | `0x1284…7974` | `0xdd95…b6b5` | `0xea1f…19f1` | `0xcEF2…66A4` (v2), `0xe2e9…cd99` (v1) |
| Ethereum (1) | `0x604D…736E` | `0x20f4…41bf` | `0x1006…30dc` | `0xb40E…c786` |
| Arbitrum (42161) | `0x9E36…40E1d5` | `0xf2ed…b44d` | `0x3d20…8937` | `0xbad4…44ef` |
| Base, Avalanche, Optimism, Polygon, Robinhood, Arc | — | — | — | — |

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **AstherusVault** (all three) | UUPS, OZ `ERC1967Proxy` 855 B | EIP-1967 impl slot = impl in §3–§5; admin slot empty | `_authorizeUpgrade` is `onlyTimeLock` → `TIMELOCK_ADDRESS` (immutable). Watch `CallScheduled` on the timelock (6 h warning) and `Upgraded` on the vault. |
| AstherusTimelock, AsterWithdrawValidator, ApolloxExchangeTreasury (all) | not proxies | impl slot empty | Validator signers and `TIMELOCK_ADDRESS` are immutable; a change needs a new vault impl. Treasuries are `Ownable` (Safe owners). |

## 9. Detection invariants & gotchas

1. **`Deposit` topic0 `0x18081cde…` is shared** by every `AstherusVault` and by the BNB v2 and Arbitrum ApolloX treasuries. `Withdraw` `0x81b8021d…` is shared by the old vault build and those treasuries. Always filter by emitter.
2. **Native deposits use a sentinel, not `0x0`.** `currency` = `NATIVE` = `address(bytes20(keccak256("NATIVE")))` = `0xfdae1ba7c826abdc4c99903c8056f82a1a04a615` on all three chains. Price it as BNB on BNB and as ETH on Ethereum/Arbitrum.
3. **`Deposit.account` is the credited user.** With `depositFor`, `msg.sender` is a `DEPOSIT_ROLE` relayer and `account` is the beneficiary. `broker` is a referral id, not an address.
4. **Withdrawals are operator-sent.** `Withdraw.to` is the user. `tx.from` is an `OPERATE_ROLE` EOA. `amount` is gross: the user receives `amount − fee`. The vault keeps `fee` and an admin sweeps it later with `withdrawFee` (`WithdrawFee` event).
5. **Auto-pause.** When an hourly USD total would pass `hourlyLimit`, the vault calls `_pause()` and emits `WithdrawPaused` instead of paying. Pair `WithdrawPaused` with `Paused` as the high-severity signal. The legacy treasuries do the same with `ClaimPaused`.
6. **Same address, different contract.** `0x604D…736E` is the Ethereum vault but a 11–13 kB unrelated contract on Base and BNB. `0x9E36…E1d5` is the Arbitrum vault but different code on Ethereum and BNB. `0xb40E…c786` and `0xbad4…44ef` repeat on other chains with other code. Key every monitor on `(chain, address)`.
7. **Legacy treasuries still move money.** The Ethereum ApolloX treasury paid 170 `Claimed` in the last 200k blocks. `TransferToCounterParty` moves funds to the owner Safe in bulk; alert on it.
8. **BNB zaps mint first.** `depositUSDF` and `depositAsBNB` mint USDF/asBNB in the same transaction (see `earn.md`). The vault `Deposit` then logs the minted token and amount, not the USDT/BNB that the user paid.

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_ASTER_VAULT_DEPOSIT          = '\x18081cde2fa64894914e1080b98cca17bb6d1acf633e57f6e26ebdb945ad830b'
TOPIC_ASTER_VAULT_WITHDRAW         = '\xfe7813e2866053d5c3938554e517b554fce6666a6561bed9eaa7419b29fa9b68'
TOPIC_ASTER_VAULT_WITHDRAW_OLD     = '\x81b8021db23057eb1dfd88796511e506e0a736c5d4758e29c39aa74b8509bcee'
TOPIC_ASTER_WITHDRAW_CANCELED      = '\x869baec015e2c7c07b86bc04511ae11388341001134b9f28df8e96bc6b33d26b'
TOPIC_ASTER_WITHDRAW_PAUSED        = '\x88655d4ce709d20f0d4615ecbb09d91c03964e7c93cf29be9912b6467d8449d1'
TOPIC_ASTER_WITHDRAW_FEE           = '\x768860cd8341946923182b97157e5aab4ca296b545a5055fbdce5e55bc1ab578'
TOPIC_ASTER_UPDATE_HOURLY_LIMIT    = '\xa71f31d4b603b19554862f19f43a8800f15ae23017b823ebe92eab7c3b20bf92'
TOPIC_ASTER_ADD_TOKEN              = '\x5e44b8d769cde64991e4725cd0276d385af04c64b64cba70267e0ed4d42350a0'
TOPIC_TIMELOCK_CALL_SCHEDULED      = '\x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca'
TOPIC_TIMELOCK_CALL_EXECUTED       = '\xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58'
TOPIC_APOLLOX_CLAIM                = '\xc977beb5adf839e24d3d75d83f7781f425347b483f62742ad0d5f08c9390648d'
TOPIC_APOLLOX_CLAIMED              = '\xbdf2c3f6edfac9e3d933ce8519d4cafffb974eb01531df50efe58090b4b1fd90'
TOPIC_APOLLOX_CLAIM_PAUSED         = '\x5a438a2092d27293a83dccc949b06566503615797dcb9afab851a64763fa33f0'
TOPIC_APOLLOX_XFER_COUNTERPARTY_V2 = '\xfa77df1ea6d4af3788b21e52a0a92d6894cd2c8ffccce06ea7fb736542153861'
TOPIC_APOLLOX_XFER_COUNTERPARTY_V1 = '\x33278ebf7b841e996e09580bfa7a0279c875902fe042c3d102a8d051c30dc733'
TOPIC_APOLLOX_NEW_TRUTH_HOLDER     = '\x81b88ce749f5ea02a8cec52c72adf48d4bae4bb5c855faaae1a248b327ff00ca'
TOPIC_PAUSED                       = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UPGRADED                     = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED                 = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
-- ===== Selectors (chain-agnostic) =====
SEL_ASTER_DEPOSIT                  = '\x0efe6a8b'
SEL_ASTER_DEPOSIT_NATIVE           = '\x608fc37a'
SEL_ASTER_DEPOSIT_FOR              = '\xcf4a0c5e'
SEL_ASTER_DEPOSIT_USDF             = '\x29a9228c'
SEL_ASTER_DEPOSIT_ASBNB            = '\x2a6c263f'
SEL_ASTER_WITHDRAW_3SIG            = '\x0cd4b1fe'
SEL_ASTER_WITHDRAW_3SIG_RAW        = '\x224a5fdd'
SEL_ASTER_WITHDRAW_VALIDATORS      = '\xe79158b1'
SEL_ASTER_WITHDRAW_FEE             = '\x9cb7bd2b'
SEL_ASTER_UPDATE_HOURLY_LIMIT      = '\x413bcb44'
SEL_APOLLOX_CLAIM                  = '\xbe27b22c'
SEL_APOLLOX_XFER_COUNTERPARTY      = '\x89c9e1ac'
SEL_UPGRADE_TO_AND_CALL            = '\x4f1ef286'
-- ===== Addresses (network-specific) =====
ASTER_NATIVE_SENTINEL              = '\xfdae1ba7c826abdc4c99903c8056f82a1a04a615'
BNB_ASTER_VAULT                    = '\x128463a60784c4d3f46c23af3f65ed859ba87974'
BNB_ASTER_TIMELOCK                 = '\xdd95d454ea23de750aa46d093c7b04e3f5b8b6b5'
BNB_ASTER_WITHDRAW_VALIDATOR       = '\xea1f2292b8c741db0d82286edadfb0d2436b19f1'
BNB_ASTER_ADMIN_SAFE               = '\xa8c0c6ee62f5ad95730fe23ccf37d1c1ffaa1c3f'
BNB_APOLLOX_TREASURY_V2            = '\xcef2dd45da08b37fb1c2f441d33c2ebb424866a4'
BNB_APOLLOX_TREASURY_V1            = '\xe2e912f0b1b5961be7cb0d6dbb4a920ace06cd99'
ETH_ASTER_VAULT                    = '\x604dd02d620633ae427888d41bfd15e38483736e'
ETH_ASTER_TIMELOCK                 = '\x20f4e8cbf7c0062464e1496164b6847112ec41bf'
ETH_ASTER_WITHDRAW_VALIDATOR       = '\x1006511304aada32ea80a259dcf140a6ecbd30dc'
ETH_APOLLOX_TREASURY               = '\xb40eed68d7d6b3b6d6f4e93de6239b7c53efc786'
ARB_ASTER_VAULT                    = '\x9e36cb86a159d479ced94fa05036f235ac40e1d5'
ARB_ASTER_TIMELOCK                 = '\xf2edc8b3b6a16e3de962027c7bb80192e807b44d'
ARB_ASTER_WITHDRAW_VALIDATOR       = '\x3d2068e2e0d505876c57a236bb65dfd42cbf8937'
ARB_APOLLOX_TREASURY               = '\xbad4ccc91ef0dfffbcab1402c519601fbaf244ef'
```

## 11. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify ABIs of the three vault impls, the timelocks, the validators and the four ApolloX treasuries. `Deposit`, new `Withdraw`, `ReceiveETH`, `Claim`, `Claimed` and `ReceiveEther` were seen in live logs (counts in §1).
- **Addresses:** vault addresses are from the official "Smart Contracts" page and the DefiLlama `astherus` adapter. Legacy treasuries are from the DefiLlama `apollox` adapter. Timelock and validator addresses were read from the vault getters. Role members came from `getRoleMember`. Safe thresholds came from `getThreshold()`/`getOwners()`.
- **Balances:** `balanceOf` / `eth_getBalance` at the latest block.
- **Chain coverage:** batched `eth_getCode` on all nine target chains, with code-size and code-hash comparison to detect same-address traps.

Authoritative sources:
- [Aster docs — Smart Contracts](https://docs.asterdex.com/overview/smart-contracts) · [Deposit & Withdrawal Guide](https://docs.asterdex.com/getting-started/deposit-and-withdrawal-guide)
- [DefiLlama-Adapters `projects/astherus`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/astherus/index.js) · [`projects/apollox`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/apollox/index.js)
- [Sourcify](https://sourcify.dev/) (BNB, Ethereum and Arbitrum verified sources)
- Explorers: [BscScan](https://bscscan.com/address/0x128463A60784c4D3f46c23Af3f65Ed859Ba87974) · [Etherscan](https://etherscan.io/address/0x604DD02d620633Ae427888d41bfd15e38483736E) · [Arbiscan](https://arbiscan.io/address/0x9E36CB86a159d479cEd94Fa05036f235Ac40E1d5)
