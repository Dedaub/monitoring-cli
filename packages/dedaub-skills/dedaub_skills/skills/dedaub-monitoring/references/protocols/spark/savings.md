# Spark Savings — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Avalanche, Robinhood Chain)

**Status:** verified against live RPC on every listed chain and the canonical `sparkdotfi/spark-vaults-v2`, `sparkdotfi/spark-vaults`, `sparkdotfi/spark-psm`, `sparkdotfi/xchain-ssr-oracle`, `sparkdotfi/spark-savings-intents` and `sparkdotfi/spark-address-registry` repos on 2026-10-30.
**Scope:** the user-facing Spark Savings products. These are the **Spark Vaults V2** (spUSDC, spUSDT, spETH, spPYUSD, spUSDG — ERC-4626 with a governance-set Vault Savings Rate), the **sUSDC** wrapper vault (USDC in, sUSDS exposure), **PSM3** (the L2 USDC/USDS/sUSDS swap pool), the cross-chain **SSR/DSR oracles**, and **Savings Intents**. Chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Avalanche C-Chain (43114), Robinhood Chain (4663). BNB (56), Polygon PoS (137) and Arc (5042) have none. Topics and selectors are chain-agnostic. Addresses are network-specific.

A **Spark Vault V2** is a UUPS proxy (163 B OZ `ERC1967Proxy` v5.4) over a `SparkVault` implementation (14678 B). The vault holds a single asset. It pays a rate `vsr` (ray, per second) that the `SETTER_ROLE` sets inside `[minVsr, maxVsr]`. The accumulator `chi` grows with `drip()`. The **ALMProxy of the Spark Liquidity Layer holds `TAKER_ROLE`**. It calls `take(value)` to move deposited assets out of the vault and deploy them ([liquidity-layer.md](liquidity-layer.md)). So `totalAssets()` is a liability figure, not the vault's token balance. `assetsOutstanding()` shows the gap.

**sUSDS** and **USDS** themselves are Sky tokens. See [../sky/](../sky/). The SparkLend money market is in [sparklend.md](sparklend.md).

---

## 0. Contract families & versions

| Component | Role | Pattern | Chains |
|-----------|------|---------|--------|
| **SparkVault (V2)** | ERC-4626 savings vault, VSR yield, `take` by the ALMProxy | UUPS proxy (ERC1967Proxy 163 B) | ETH, Arb, Avax, Robinhood |
| **sUSDC** (`UsdcVault` / `UsdcVaultL2`) | ERC-4626, asset USDC (6 dec), shares 18 dec. Routes USDC→USDS→sUSDS (ETH via LitePSM, L2 via PSM3) | UUPS proxy (163 B) | ETH, Base, Arb, OP |
| **PSM3** | Three-asset pool (USDC, USDS, sUSDS) with LP shares. sUSDS priced by the SSR oracle | Immutable | Base, Arb, OP |
| **SSRAuthOracle / DSRAuthOracle** | L2 copy of the Sky Savings Rate (`ssr`, `chi`, `rho`) pushed from Ethereum forwarders | Immutable | Base, Arb, OP |
| **SavingsVaultIntents** | Queue for large redemption requests that a relayer fulfills | Immutable | ETH |

---

## 1. Topics (chain-agnostic)

### 1.1 SparkVault (V2) — emitter = each vault proxy

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` (ERC-4626) |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` (ERC-4626) |
| `0xb30a03a0e2a407f18ae0e83491331dc069d1521e292feffb071e61c8f7f40636` | `Referral(uint16 indexed referral, address indexed owner, uint256 assets, uint256 shares)` |
| `0xd69eabfc802f58b2a23d16767d1fcab6551f30a60ab43a24f147d3823d7d0368` | `Take(address indexed to, uint256 value)` — **assets leave the vault to the ALMProxy** |
| `0xad1e8a53178522eb68a9d94d862bf30c841f709d2115f743eb6b34528751c79f` | `Drip(uint256 chi, uint256 diff)` |
| `0xdd4573165d2d2b3ad7be79cfb35bd79c5d5e90e9a51ca373b975e89591b1e513` | `VsrSet(address indexed sender, uint256 oldVsr, uint256 newVsr)` |
| `0x6074f38f2f0894d37e6c6842e522ed5a263a62e38db11377b063d485b0b30220` | `VsrBoundsSet(uint256 oldMinVsr, uint256 oldMaxVsr, uint256 newMinVsr, uint256 newMaxVsr)` |
| `0x296bce538ac6d09f30846d670defb82b44ccc28a772613d99904be3f6ed7a167` | `DepositCapSet(uint256 oldCap, uint256 newCap)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` (share token) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (UUPS) |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |

### 1.2 sUSDC (`UsdcVault`, `UsdcVaultL2`)

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05…f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` — same topic as §1.1 |
| `0xfbde797d…9c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` — same topic as §1.1 |
| `0x5d37b5fd4fa55aef7719d4c71278238e6561b98a34f1402c6813e91fbda607a7` | `Exit(address indexed sender, address indexed receiver, address indexed owner, uint256 shares)` — redeem to sUSDS, not USDC |
| `0xb30a03a0…6f40636` (same as §1.1) | `Referral(uint16 indexed referral, address indexed owner, uint256 assets, uint256 shares)` |
| `0xdd0e34038ac38b2a1ce960229778ac48a8719bc900b6c4f8d0475c6e8b385a60` | `Rely(address indexed usr)` |
| `0x184450df2e323acec0ed3b5c7531b81f9b4cdef7914dfd4c0a4317416bb5251b` | `Deny(address indexed usr)` |

### 1.3 PSM3 (L2 only)

| topic0 | Event |
|--------|-------|
| `0xdba43ee9916cb156cc32a5d3406e87341e568126a46815294073ba25c9400246` | `Swap(address indexed assetIn, address indexed assetOut, address sender, address indexed receiver, uint256 amountIn, uint256 amountOut, uint256 referralCode)` |
| `0x5fe47ed6d4225326d3303476197d782ded5a4e9c14f479dc9ec4992af4e85d59` | `Deposit(address indexed asset, address indexed user, address indexed receiver, uint256 assetsDeposited, uint256 sharesMinted)` |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed asset, address indexed user, address indexed receiver, uint256 assetsWithdrawn, uint256 sharesBurned)` — **same topic0 as ERC-4626 `Withdraw`** |
| `0x3fc246ba2ebf4dedf8b9de3cc4b46795e44b56db70960136b44fccbe99daa478` | `PocketSet(address indexed oldPocket, address indexed newPocket, uint256 amountTransferred)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

### 1.4 SSR / DSR oracles and Savings Intents

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xc234856e2a0c5b406365714ced016892e7d98f7b1d49982cdd8db416a586d811` | `SetSUSDSData((uint96 ssr, uint120 chi, uint40 rho) nextData)` | SSRAuthOracle (L2) |
| `0xc3bbb2150e1e8742715cfdb05bbe56476860c1d3abeef394f17f5d53d9cd9d2f` | `SetMaxSSR(uint256 maxSSR)` | SSRAuthOracle |
| `0x5e30fdd2979e332af16cdeae2862b38bc5fc87150ebdf5d8b9690a2616251d76` | `RequestCreated(address indexed account, address indexed vault, uint256 indexed requestId, uint256 shares, address recipient, uint256 deadline)` | SavingsVaultIntents |
| `0x84ec25b59940488f00ce0dea9ef60d1d8192093ef1e1f3acbd54bdd0f8f385f2` | `RequestFulfilled(address indexed account, address indexed vault, uint256 indexed requestId)` | SavingsVaultIntents |
| `0x42518a4b22fcff722865232fd08e44bc48a8c1851d85a49865aad209f8af5563` | `RequestCancelled(address indexed account, address indexed vault, uint256 indexed requestId)` | SavingsVaultIntents |
| `0xe8ad04668f651168ebea2da983b38ca63562058eee010b47b178eca948cf9722` | `VaultConfigUpdated(address indexed vault, bool indexed whitelisted, uint256 minIntentAssets, uint256 maxIntentAssets)` | SavingsVaultIntents |
| `0xd8324e0857d5c4b9ba6cd0beaae197bd83f97787307c8d991a6dfe7e5703f5d2` | `MaxDeadlineDurationUpdated(uint256 indexed maxDeadlineDuration)` | SavingsVaultIntents |

---

## 2. Function signatures (chain-agnostic)

### 2.1 SparkVault (V2) — all checked in the live implementation bytecode

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256,address)` | ERC-4626. |
| `0x9b8d6d38` | `deposit(uint256,address,uint16)` | With referral. Emits `Referral`. |
| `0x94bf804d` / `0x216740a0` | `mint(uint256,address)` / `mint(uint256,address,uint16)` | |
| `0xb460af94` | `withdraw(uint256,address,address)` | |
| `0xba087652` | `redeem(uint256,address,address)` | |
| `0x4fd9efc4` | `take(uint256)` | `TAKER_ROLE` (ALMProxy). Emits `Take`. |
| `0x9f678cca` | `drip()` | Anyone. Emits `Drip`. |
| `0x7497d46c` | `setVsr(uint256)` | `SETTER_ROLE`. Emits `VsrSet`. |
| `0x78d3e538` | `setVsrBounds(uint256,uint256)` | `DEFAULT_ADMIN_ROLE`. |
| `0x86651203` | `setDepositCap(uint256)` | `DEFAULT_ADMIN_ROLE`. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | `DEFAULT_ADMIN_ROLE` (UUPS). |
| `0x01e1d114` | `totalAssets()` | View. Liabilities at `nowChi()`. |
| `0x925455ca` | `assetsOutstanding()` | View. `totalAssets − vault balance` (amount taken). |
| `0x4ab65039` / `0xc92aecc4` / `0x1e7b14d3` | `nowChi()` / `chi()` / `vsr()` | Views (ray). |
| `0x38d52e0f` / `0x07a2d13a` | `asset()` / `convertToAssets(uint256)` | Views. |

### 2.2 sUSDC

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` / `0x0c71b121` | `deposit(uint256,address)` / `deposit(uint256,address,uint256,uint16)` | 4-arg form has `minShares` + referral. |
| `0x94bf804d` / `0x418b4bdb` | `mint(uint256,address)` / `mint(uint256,address,uint256,uint16)` | |
| `0xb460af94` / `0xa318c1a4` | `withdraw(uint256,address,address)` / `withdraw(uint256,address,address,uint256)` | |
| `0xba087652` / `0x9f40a7b3` | `redeem(uint256,address,address)` / `redeem(uint256,address,address,uint256)` | |
| `0x120175ca` | `exit(uint256,address,address)` | Burn shares, receive sUSDS. |

### 2.3 PSM3 / SSR oracle / Intents

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1a019e37` | `swapExactIn(address,address,uint256,uint256,address,uint256)` | PSM3. Emits `Swap`. |
| `0x051f86b5` | `swapExactOut(address,address,uint256,uint256,address,uint256)` | PSM3. |
| `0x8340f549` | `deposit(address,address,uint256)` | PSM3 LP deposit (asset, receiver, amount). The SLL ALMProxy is the main LP. |
| `0xd9caed12` | `withdraw(address,address,uint256)` | PSM3 LP withdraw. |
| `0x03fa0d0b` / `0xcccef9e2` | `setPocket(address)` / `pocket()` | PSM3 owner / view. USDC sits in the pocket. |
| `0x3a98ef39` / `0xce7c2ac2` | `totalShares()` / `shares(address)` | PSM3 views. |
| `0x044089a7` | `setSUSDSData((uint96,uint120,uint40))` | SSRAuthOracle, `DATA_PROVIDER_ROLE` (receiver). |
| `0xf36089ec` / `0x5e37e811` | `getConversionRate()` / `getSSR()` | SSR oracle views. |
| `0xac5651a6` | `request(address,uint256,address,uint256)` | Intents: vault, shares, recipient, deadline. |
| `0x886365e3` | `fulfill(address,address,uint256)` | Intents, `RELAYER` role. |
| `0x4c33fe94` | `cancel(address)` | Intents. |

---

## 3. Addresses

All addresses come from `spark-address-registry`. Each one returned non-empty code from `eth_getCode` on 2026-10-30. Vault metadata (`symbol`, `asset`, `totalAssets`, `depositCap`) was read live.

### 3.1 Spark Vaults V2

| Chain | Vault | Proxy | Asset | Implementation | `totalAssets` (2026-10-30) |
|-------|-------|-------|-------|----------------|----------------------------|
| Ethereum | **spUSDC** | `0x28B3a8fb53B741A8Fd78c0fb9A6B2393d896a43d` | USDC | `0x1b992302652A92611DCd5090D1Cb388C6377f455` | ≈ 272.3M USDC (cap 2B) |
| Ethereum | **spUSDT** | `0xe2e7a17dFf93280dec073C995595155283e3C372` | USDT | " | ≈ 425.0M USDT (cap 4B) |
| Ethereum | **spETH** | `0xfE6eb3b609a7C8352A241f7F3A21CEA4e9209B8f` | WETH | " | ≈ 24,485 WETH (cap 500k) |
| Ethereum | **spPYUSD** | `0x80128DbB9f07b93DDE62A6daeadb69ED14a7D354` | PYUSD | " | ≈ 23,897 PYUSD |
| Avalanche | **spUSDC** | `0x28B3a8fb53B741A8Fd78c0fb9A6B2393d896a43d` (same address as ETH) | USDC `0xB97E…8a6E` | `0xC2C0582D1cCe30449cF561C7b9C4D6d527547F12` | ≈ 988K USDC |
| Arbitrum | **spUSDT** | `0x45d91340B3B7B96985A72b5c678F7D9e8D664b62` | USDT `0xFd08…Cbb9` | `0x282dAfE8B97e2Db5053761a4601ab2E1CB976318` | ≈ 103.6K USDT |
| Robinhood | **spUSDG** | `0xde770c84FE66E063336b31737cFE9790f18c4087` | USDG `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` | `0x797c58C9779D46a437D8f57908D6d56371A55F02` | ≈ 13.30M USDG (cap 500M) |

Roles on spUSDG (Robinhood), read with `getRoleMember`: admin = `SPARK_EXECUTOR` `0x826AEaeee9233fA8Ba199518dd8621A5962b1D02`; `TAKER_ROLE` = SLL ALMProxy `0xfD2fD4B046136B540A56C11c75ac679AE7d1dB24`; `SETTER_ROLE` = ALMProxyFreezable `0xAEa9f5dE56e6C20383a1fcC2C3629Dca0A92cE41`. On Ethereum spUSDC: admin = `SPARK_PROXY` `0x3300f198…f8c4`, taker = ALMProxy `0x1601843c…347E`, setter = ALMProxyFreezable `0xe5c63184…f699`.

### 3.2 sUSDC

| Chain | Proxy | Implementation | Asset |
|-------|-------|----------------|-------|
| Ethereum | `0xBc65ad17c5C0a2A4D159fa5a503f4992c7B545FE` | `0xf943Cb8D5f06f2bBF352878ebEF3Ec5C537A20bA` (`UsdcVault`) | USDC |
| Base | `0x3128a0F7f0ea68E7B7c9B00AFa7E41045828e858` | `0x6ACC02ddd82206a44ff4EC13977E63d1a29C7723` (`UsdcVaultL2`) | USDC `0x8335…2913` |
| Arbitrum | `0x940098b108fB7D0a7E374f6eDED7760787464609` | `0xdC8DF20bE448E41FdE88E2478d6Bc4d3C9A092d6` | USDC `0xaf88…5831` |
| Optimism | `0xCF9326e24EBfFBEF22ce1050007A43A3c0B6DB55` | `0x3a1d3A9B0eD182d7B17aa61393D46a4f4EE0CEA5` | USDC `0x0b2C…Ff85` |

### 3.3 PSM3 and rate oracles (L2)

| Chain | PSM3 | SSRAuthOracle | SSR receiver | DSRAuthOracle | sUSDS (Sky) |
|-------|------|---------------|--------------|---------------|-------------|
| Base | `0x1601843c5E9bC251A3272907010AFa41Fa18347E` | `0x65d946e533748A998B1f0E430803e39A6388f7a1` | `0x212871A1C235892F86cAB30E937e18c94AEd8474` | `0x2Dd2a2Fe346B5704380EfbF6Bd522042eC3E8FAe` | `0x5875eEE11Cf8398102FdAd704C9E96607675467a` |
| Arbitrum | `0x2B05F8e1cACC6974fD79A673a341Fe1f58d27266` | `0xEE2816c1E1eed14d444552654Ed3027abC033A36` | `0x567214Dc57a2385Abc4a756f523ddF0275305Cbc` | `0xE206AEbca7B28e3E8d6787df00B010D4a77c32F3` | `0xdDb46999F8891663a8F2828d25298f70416d7610` |
| Optimism | `0xe0F9978b907853F354d79188A3dEfbD41978af62` | `0x6E53585449142A5E6D5fC918AE6BEa341dC81C68` | `0xE2868095814c2714039b3A9eBEE035B9E2c411E5` | `0x33a3aB524A43E69f30bFd9Ae97d1Ec679FF00B64` | `0xb5B2dc7fd34C249F4be7fB1fCea07950784229e0` |

Ethereum forwarders (they push SSR to L2): `BASE_SSR_FORWARDER` `0xB2833392527f41262eB0E3C7b47AFbe030ef188E`, `ARBITRUM_SSR_FORWARDER` `0x1A229AdbAC83A948226783F2A3257B52006247D5`, `OPTIMISM_SSR_FORWARDER` `0x6Ac25B8638767a3c27a65597A74792d599038724`.

### 3.4 Other

| Chain | Contract | Address |
|-------|----------|---------|
| Ethereum | SavingsVaultIntents | `0x592B7DB9906E6f8924C4D74c2A0aB86CE44fDDDf` |
| Ethereum | PSM Variant1 user actions (USDC→sUSDS helper) | `0xd0A61F2963622e992e6534bde4D52fd0a89F39E0` |
| Ethereum / OP / Avax | SparkRewards (Merkle claims) | `0xbaf21A27622Db71041Bd336a573DDEdC8eB65122` / `0xf94473Bf6EF648638A7b1eEef354fE440721ef41` / `0xAf76856f788519704a9411839614e144FEd52d8a` |

**No Spark Savings contract on:** BNB (56), Polygon PoS (137), Arc (5042). Base and Optimism have no Spark Vault V2. Avalanche and Robinhood have no PSM3 or sUSDC.

---

## 4. Cross-chain summary

| Chain | spUSDC | spUSDT | spETH | spPYUSD | spUSDG | sUSDC | PSM3 |
|-------|--------|--------|-------|---------|--------|-------|------|
| Ethereum (1) | `0x28B3…a43d` | `0xe2e7…C372` | `0xfE6e…9B8f` | `0x8012…D354` | — | `0xBc65…45FE` | — |
| Base (8453) | — | — | — | — | — | `0x3128…e858` | `0x1601…347E` |
| Arbitrum (42161) | — | `0x45d9…4b62` | — | — | — | `0x9400…4609` | `0x2B05…7266` |
| Optimism (10) | — | — | — | — | — | `0xCF93…DB55` | `0xe0F9…af62` |
| Avalanche (43114) | `0x28B3…a43d` | — | — | — | — | — | — |
| Robinhood (4663) | — | — | — | — | `0xde77…4087` | — | — |
| BNB / Polygon / Arc | — | — | — | — | — | — | — |

---

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Spark Vaults V2 | **UUPS** (OZ ERC1967Proxy v5.4, 163 B) | impl slot = implementation in §3.1. Admin slot = `0x0` (UUPS). | `DEFAULT_ADMIN_ROLE` (Spark governance) via `upgradeToAndCall`. Watch `Upgraded`. |
| sUSDC | **UUPS** (163 B) | impl slot = §3.2 | `wards` (`Rely`/`Deny`) = Spark governance. |
| PSM3 | **Immutable** | impl slot `0x0` | Owner can change `pocket` only. |
| SSR/DSR oracles, Intents | **Immutable** | impl slot `0x0` | Admin roles only. |

Each chain has its own Spark Vault implementation address (ETH `0x1b992302…f455`, Avax `0xC2C0582D…7F12`, Arb `0x282dAfE8…6318`, Robinhood `0x797c58C9…5F02`). All four are 14678 B.

---

## 6. Detection invariants & gotchas

1. **`Take` is the outflow, not `Withdraw`.** User exits emit ERC-4626 `Withdraw`. The ALMProxy removes assets with `take` (`Take(to, value)`, `to` = ALMProxy). A large `Take` is normal SLL deployment. A `Take` to any address that is not the chain's ALMProxy is an anomaly.
2. **`totalAssets()` is not the token balance.** Most assets are deployed by the SLL. A vault can hold only a small buffer. Redemptions larger than the buffer revert until the SLL returns funds. Watch `assetsOutstanding()` against `totalAssets()`.
3. **`Withdraw` topic0 collision.** `0xfbde797d…` is the ERC-4626 `Withdraw` **and** the PSM3 `Withdraw(asset, user, receiver, assets, shares)`. Disambiguate by emitter.
4. **Same vault address on two chains.** spUSDC is `0x28B3a8fb…a43d` on both Ethereum and Avalanche, with different assets and implementations. `0x45d91340…4b62` is spUSDT on Arbitrum but the `UNICHAIN_SSR_FORWARDER` on Ethereum. Key on `(chainId, address)`.
5. **sUSDC decimals mismatch.** Asset USDC has 6 decimals. Shares have 18. `Deposit.assets` is in 6-decimal units and `Deposit.shares` in 18-decimal units.
6. **`Exit` is a third outflow path** on sUSDC. It returns sUSDS, so no USDC `Transfer` follows.
7. **Rate change signal.** `VsrSet` changes the user yield of a Spark Vault. The new value must stay in `[minVsr, maxVsr]`. A `VsrBoundsSet` with a wide new max is a governance-level change.
8. **Robinhood spUSDG** (lead address `0xde770c84…4087`, 163 B proxy) held ≈ 13.30M USDG and had 13.14M shares on 2026-10-30. Live `eth_getLogs` shows `Deposit`/`Withdraw`/`Referral`/`Drip` on it. It is the only Spark Savings contract on Robinhood Chain.
9. **L2 sUSDS price comes from the SSR oracle.** PSM3 and sUSDC on L2 use `getConversionRate()`. A stale or wrong `SetSUSDSData` on an L2 oracle mis-prices every PSM3 swap. Alert on `SetSUSDSData` where `ssr` exceeds `maxSSR` or `chi` drops.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_ERC4626_DEPOSIT          = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_ERC4626_WITHDRAW         = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_SPARK_VAULT_REFERRAL     = '\xb30a03a0e2a407f18ae0e83491331dc069d1521e292feffb071e61c8f7f40636'
TOPIC_SPARK_VAULT_TAKE         = '\xd69eabfc802f58b2a23d16767d1fcab6551f30a60ab43a24f147d3823d7d0368'
TOPIC_SPARK_VAULT_DRIP         = '\xad1e8a53178522eb68a9d94d862bf30c841f709d2115f743eb6b34528751c79f'
TOPIC_SPARK_VAULT_VSR_SET      = '\xdd4573165d2d2b3ad7be79cfb35bd79c5d5e90e9a51ca373b975e89591b1e513'
TOPIC_SPARK_VAULT_VSR_BOUNDS   = '\x6074f38f2f0894d37e6c6842e522ed5a263a62e38db11377b063d485b0b30220'
TOPIC_SPARK_VAULT_CAP_SET      = '\x296bce538ac6d09f30846d670defb82b44ccc28a772613d99904be3f6ed7a167'
TOPIC_UPGRADED                 = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_SUSDC_EXIT               = '\x5d37b5fd4fa55aef7719d4c71278238e6561b98a34f1402c6813e91fbda607a7'
TOPIC_PSM3_SWAP                = '\xdba43ee9916cb156cc32a5d3406e87341e568126a46815294073ba25c9400246'
TOPIC_PSM3_DEPOSIT             = '\x5fe47ed6d4225326d3303476197d782ded5a4e9c14f479dc9ec4992af4e85d59'
TOPIC_PSM3_WITHDRAW            = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_PSM3_POCKET_SET          = '\x3fc246ba2ebf4dedf8b9de3cc4b46795e44b56db70960136b44fccbe99daa478'
TOPIC_SSR_SET_SUSDS_DATA       = '\xc234856e2a0c5b406365714ced016892e7d98f7b1d49982cdd8db416a586d811'
TOPIC_INTENT_REQUEST_CREATED   = '\x5e30fdd2979e332af16cdeae2862b38bc5fc87150ebdf5d8b9690a2616251d76'
TOPIC_INTENT_REQUEST_FULFILLED = '\x84ec25b59940488f00ce0dea9ef60d1d8192093ef1e1f3acbd54bdd0f8f385f2'
-- ===== Roles =====
ROLE_TAKER                     = '\x508ee82d0bdf04e000303ab4f02b172e60c5f2d35b2e559b05bed2cf403bb58b'
ROLE_SETTER                    = '\x61c92169ef077349011ff0b1383c894d86c5f0b41d986366b58a6cf31e93beda'
-- ===== Selectors (chain-agnostic) =====
SEL_ERC4626_DEPOSIT            = '\x6e553f65'
SEL_SPARK_VAULT_DEPOSIT_REF    = '\x9b8d6d38'
SEL_ERC4626_WITHDRAW           = '\xb460af94'
SEL_ERC4626_REDEEM             = '\xba087652'
SEL_SPARK_VAULT_TAKE           = '\x4fd9efc4'
SEL_SPARK_VAULT_SET_VSR        = '\x7497d46c'
SEL_SPARK_VAULT_DRIP           = '\x9f678cca'
SEL_UPGRADE_TO_AND_CALL        = '\x4f1ef286'
SEL_SUSDC_EXIT                 = '\x120175ca'
SEL_PSM3_SWAP_EXACT_IN         = '\x1a019e37'
SEL_PSM3_SWAP_EXACT_OUT        = '\x051f86b5'
SEL_PSM3_DEPOSIT               = '\x8340f549'
SEL_PSM3_WITHDRAW              = '\xd9caed12'
-- ===== Addresses (network-specific) =====
ETH_SPARK_SPUSDC               = '\x28b3a8fb53b741a8fd78c0fb9a6b2393d896a43d'
ETH_SPARK_SPUSDT               = '\xe2e7a17dff93280dec073c995595155283e3c372'
ETH_SPARK_SPETH                = '\xfe6eb3b609a7c8352a241f7f3a21cea4e9209b8f'
ETH_SPARK_SPPYUSD              = '\x80128dbb9f07b93dde62a6daeadb69ed14a7d354'
ETH_SPARK_SUSDC                = '\xbc65ad17c5c0a2a4d159fa5a503f4992c7b545fe'
ETH_SPARK_SAVINGS_INTENTS      = '\x592b7db9906e6f8924c4d74c2a0ab86ce44fdddf'
AVAX_SPARK_SPUSDC              = '\x28b3a8fb53b741a8fd78c0fb9a6b2393d896a43d'
ARB_SPARK_SPUSDT               = '\x45d91340b3b7b96985a72b5c678f7d9e8d664b62'
ROBIN_SPARK_SPUSDG             = '\xde770c84fe66e063336b31737cfe9790f18c4087'
ROBIN_USDG                     = '\x5fc5360d0400a0fd4f2af552add042d716f1d168'
BASE_SPARK_SUSDC               = '\x3128a0f7f0ea68e7b7c9b00afa7e41045828e858'
ARB_SPARK_SUSDC                = '\x940098b108fb7d0a7e374f6eded7760787464609'
OP_SPARK_SUSDC                 = '\xcf9326e24ebffbef22ce1050007a43a3c0b6db55'
BASE_SPARK_PSM3                = '\x1601843c5e9bc251a3272907010afa41fa18347e'
ARB_SPARK_PSM3                 = '\x2b05f8e1cacc6974fd79a673a341fe1f58d27266'
OP_SPARK_PSM3                  = '\xe0f9978b907853f354d79188a3defbd41978af62'
BASE_SPARK_SSR_AUTH_ORACLE     = '\x65d946e533748a998b1f0e430803e39a6388f7a1'
ARB_SPARK_SSR_AUTH_ORACLE      = '\xee2816c1e1eed14d444552654ed3027abc033a36'
OP_SPARK_SSR_AUTH_ORACLE       = '\x6e53585449142a5e6d5fc918ae6bea341dc81c68'
```

---

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `spark-vaults-v2` (`51c6d7a`), `spark-vaults` (`78d37c8`), `spark-psm` (`2b1a72a`), `xchain-ssr-oracle` (`4a23d1f`) and `spark-savings-intents` (`20d9a5b`). Live `eth_getLogs` confirmed `Deposit`/`Withdraw`/`Referral`/`Take`/`Drip` on ETH spUSDC, `VsrSet` on ETH spETH, `Drip`/`Deposit`/`Withdraw` on Avalanche spUSDC and Robinhood spUSDG, `Exit` on ETH sUSDC, `Swap`/`Deposit`/`Withdraw` on Base PSM3 and `SetSUSDSData` on the Base SSRAuthOracle. Selectors were confirmed by a PUSH4 scan of the live SparkVault, PSM3, sUSDC and Intents bytecode.
- **Addresses:** parsed from `spark-address-registry` and checked with `eth_getCode`. Implementations were read from the EIP-1967 slot. Vault roles were read with `getRoleMember`.
- **Chain coverage:** BNB, Polygon and Arc have no registry entry for any Savings contract. `eth_getCode` on Arc returned `0x` for all of them.
- **Not verified:** Savings Intents produced no log in the last 10k Ethereum blocks. Its topics are from source only.

Authoritative sources:
- [sparkdotfi/spark-vaults-v2](https://github.com/sparkdotfi/spark-vaults-v2) · [sparkdotfi/spark-vaults](https://github.com/sparkdotfi/spark-vaults) · [sparkdotfi/spark-psm](https://github.com/sparkdotfi/spark-psm) · [sparkdotfi/xchain-ssr-oracle](https://github.com/sparkdotfi/xchain-ssr-oracle) · [sparkdotfi/spark-savings-intents](https://github.com/sparkdotfi/spark-savings-intents)
- [sparkdotfi/spark-address-registry](https://github.com/sparkdotfi/spark-address-registry)
- [Spark docs — Savings](https://docs.spark.fi/)
- Explorers: [Etherscan](https://etherscan.io/address/0x28B3a8fb53B741A8Fd78c0fb9A6B2393d896a43d) · [Basescan](https://basescan.org/address/0x1601843c5E9bC251A3272907010AFa41Fa18347E) · [Arbiscan](https://arbiscan.io) · [Optimistic Etherscan](https://optimistic.etherscan.io) · [Snowtrace](https://snowtrace.io) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com/address/0xde770c84FE66E063336b31737cFE9790f18c4087)
