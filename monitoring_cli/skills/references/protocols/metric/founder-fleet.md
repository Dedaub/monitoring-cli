# Metric founder fleet — Wild Credit, UpDown.finance, Basis Gold fork & co. (Ethereum-only)

**Status:** exhaustively reverse-engineered from deployed bytecode + live logs on Ethereum mainnet (`https://ethereum-rpc.publicnode.com` + Blockscout) on 2026-06-05. **None of these contracts are source-verified** (only the METRIC token in [`core.md`](core.md) is). Every event topic0 below was **observed in live logs** and the signature **recomputed locally with keccak** (pycryptodome) to confirm; every function selector was extracted from runtime bytecode (PUSH4 scan) and resolved via 4byte + openchain (648 / 750 resolved). Treat signatures as *high-confidence-but-unverified*.

**What this file is.** The METRIC token's deployer EOA `0x2Cb037BD…58172` and a paired operator/owner EOA `0xd7b3b509…8e97` — publicly attributed to **0xdev0** (the Wild Credit / Metric founder) — together deployed **306 contracts on Ethereum** (143 + 163). These are **NOT the Metric.exchange product** (that's just the token + 0x/KeeperDAO — see [`core.md`](core.md)). They are a serial DeFi builder's body of work across several **distinct protocols**, all sharing one deploy wallet, one ownership scaffold, and one set of "fingerprint" functions. The user asked to *exhaust the fleet*; this is that catalog.

> **Linkage evidence (why these are grouped):** the METRIC token deployer `0x2Cb0…` directly created the two earliest Wild Credit lending contracts, whose `owner()` is `0xd7b3…`; `0xd7b3…` in turn deployed the WILD token, veWILD, the LendingPairs, the Basis Gold treasury, and UpDown markets. The two EOAs interlock as deployer/owner across the whole set. This is an **on-chain** linkage; the "0xdev0" name is the publicly-reported attribution.

**Decomposition (306 contracts → distinct protocols, by emitted events + selectors):**

| Sub-protocol | What it is | ~contracts | Anchor token(s) |
|--------------|-----------|-----------:|-----------------|
| **Wild Credit** | Permissionless **isolated-pair lending**; collateral incl. **Uniswap V3 positions**. Factory → minimal-proxy LendingPair clones, a LendingController, a UniV3/Chainlink PriceOracle, veWILD vote-escrow, xWILD staking. | ~110 | WILD, veWILD, xWILD, WILD-LP, wBOND, bCRED |
| **Basis Gold (fork)** | **Seigniorage algo-stablecoin** (Basis Cash–style): a "gold" peg token + bond + share, boardroom, treasury (`allocateSeigniorage`). | ~8 | BSG, BSGB, BSGS |
| **UpDown.finance** | **Binary up/down options** keyed to a TWAP oracle (`buyUp`/`buyDown`/`resolve`, per-epoch shares). | ~6 | UPDOWN |
| Vaults / index ("X") | Index/rebalancer vaults (`VaultCreated`, `Rebalance`), share token symbol `X`. | ~14 | X |
| Test / misc tokens | One-off ERC-20s & experiments. | ~rest | HYPE×5, BUILD, CPOOL, DPOOL(DSD coupon), Hype |
| Cross-cutting | Timelocks, ProxyAdmins/TransparentProxies, MasterChef farms, helpers, and many bespoke unverified contracts. | — | — |

**Ethereum-only.** As with the token, nothing here exists on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event sig)`) — the full fleet set (60 distinct, observed live)

All 60 distinct event topic0s emitted anywhere in the fleet. Each keccak-recomputed locally; the 7 that no DB decoded were resolved via openchain and **keccak-confirmed**. **Many names collide across DeFi** (`Transfer`, `Deposit`, `Withdraw`, `Claim`, `OwnershipTransferred`, `QueueTransaction`, `Upgraded`) — always key on `(chainId=1, emitter address, topic0)`.

| topic0 | Event signature |
|--------|-----------------|
| `0x6a75ebadc337734596edf1289381bebea46d6708a4c05ed096a5ac94d3a20d75` | AddLinkOracle(address indexed token, address oracle) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | Approval(address indexed owner, address indexed spender, uint256 value) |
| `0x03ca7276ab7799bf73fb79d27ff0610cd7049574f2508ef8445162833d439aea` | BoardroomFunded(uint256 timestamp, uint256 seigniorage) |
| `0xbb614ecd1ed5d1454c15f856743fff55fa975d6257e7262b092a86067ceda764` | BorrowingEnabled(bool value) |
| `0xdbf5270c3cf4729fec4fdac76fda864aa4f3d14d657ad21772ac28f627141ed9` | BoughtBonds(address indexed from, uint256 amount) |
| `0xccd3723763bfaa32adaf7f802373aec077dc37e45054e6b2f6007dea24df5c53` | CancelTransaction(bytes32 indexed txHash, address indexed target, bytes data, uint256 eta) |
| `0x2fffc091a501fd91bfbff27141450d3acb40fb8e6d8382b243ec7a812a3aaf87` | CancelTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta) |
| `0x34fcbac0073d7c3d388e51312faf357774904998eeb8fca628b9e6f65ee1cbf7` | Claim(address indexed account, uint256 veBalance, uint256 claimAmount) |
| `0x4caa64211297e9263667fef70732dc65ca7a8e8c60dc72539ed94518628212d0` | ContributionPoolFunded(uint256 timestamp, uint256 seigniorage) |
| `0x25ba333c9a98f8f18bb40ff507a4a1fb423614f442759c754d038a9de3f81cf3` | ContributionPoolRateChanged(address indexed operator, uint256 newRate) |
| `0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15` | Deposit(address indexed user, uint256 indexed pid, uint256 amount) *(MasterChef)* |
| `0xa3af609bf46297028ce551832669030f9effef2b02606d02cbbcc40fe6b47c55` | Deposit(uint256 user, uint256 amount) |
| `0x643e927b32d5bfd08eccd2fcbd97057ad413850f857a2359639114e8e8dd3d7b` | Deposit(address,uint256,string) *(openchain+keccak-confirmed)* |
| `0x7b014ed3854e7f5cb0218d58b3c6ae7d53a68bb0af2f67bfb029ea42c38a7e85` | DepositsEnabled(bool newValue) |
| `0xb649c98f58055c520df0dcb5709eff2e931217ff2fb1e21376130d31bbb1c0af` | Distributed(address account, uint256 amount) |
| `0xc96beb48c3f09a2506ca826988a1c28f731e1e1b91826bd50ed9c0889347e425` | ExecuteTransaction(bytes32 indexed txHash, address indexed target, bytes data, uint256 eta) |
| `0xa560e3198060a2f10670c1ec5b403077ea6ae93ca8de1c32b451dc1a943cd6e7` | ExecuteTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta) |
| `0xd5b1679906751c92e8e1b459d1043b618d4828583b2d75bccaa1b8a63e45ae95` | FeeDistribution(uint256 amount) |
| `0x25ff68dd81b34665b5ba7e553ee5511bf6812e12adb4a7e2c0d9e26b3099ce79` | Initialized(address indexed executor, uint256 at) |
| `0x0e31f07bae79135368ff475cf6c7f6abb31e0fd731e03c18ad425bd9406cf0c0` | Lock(address indexed account, uint256 lockedBalance, uint256 veBalance, uint256 lockedUntil) *(veWILD)* |
| `0x0caca70b66aed56b0630989a049110023c5a3f37e0ea4b6ce96fc747663f3ebc` | Migration(address indexed target) |
| `0x93f89a4ade64affae107c642c1a64962fbccf628af01c63a6fbd0928697a5acf` | NewColFactor(address indexed token, uint256 value) *(Wild lending ctrl)* |
| `0x4b78fab1094794ffd6fdb46f2d48f13d20be4df4af14f9b5f42bd97483f2ce03` | NewDepositLimit(address indexed pair, address indexed token, uint256 value) |
| `0x1011e87ba3050b2d8e1056215c975f86fd3b4bb0fd318474f313eb4c052f87bd` | NewDepositLimit(address indexed vault, uint256 amount) |
| `0x412871529f3cedd6ca6f10784258f4965a5d6e254127593fe354e7a62f6d0a23` | NewFeeRecipient(address feeRecipient) |
| `0x367a05e702f64fce9d390ac847a7609b6fd6e7c1e387ff65a90102dde6f85c4c` | NewIncome(uint256 addAmount, uint256 remainingAmount, uint256 rewardRate) |
| `0x784ec2eb964e8fb9a1b293a1dc19b1bf33e48c9a6e63a2894b3ab6f800add2ca` | NewMinBorrow(address indexed token, uint256 value) |
| `0x73a78e4c5a3b1768f847a4681bbd31a79b940ebb8cabf042275eabbce120bb2b` | NewMinBorrowUSD(uint256) *(openchain+keccak-confirmed)* |
| `0x8e2feba176220d60396be54887d00e4d945ce2f0f1c85b818e818cf5c0b0a2ab` | NewMinObservations(uint16) *(openchain+keccak-confirmed)* |
| `0x83cb4005d15c169dad68dec1455521fb46565b8522cb670db69104e6cc1bd773` | NewLowRate(uint256) *(openchain+keccak-confirmed)* |
| `0xf261845a790fe29bbd6631e2ca4a5bdc83e6eed7c3271d9590d97287e00e9123` | NewPriceOracle(address indexed priceOracle) |
| `0x81221bfed06bcaa6afd963740e5f89e5e5feabcfe9fea03798467eafd0094bdb` | NewRates(uint256 minRate, uint256 lowRate, uint256 highRate) |
| `0xf82e12abcc9d9ad0deb2ba4299126479da600b31cc4085d7f75778922e829bf5` | NewRebalancer(address indexed rebalancer) |
| `0xf399bc60edd477d205779b7a0741a3fe0f0fad805bff5d92d7f6cb941c743506` | NewTargetUtilization(uint256 value) |
| `0xfa1f92b31b731f678a69ee528dc71a2dcf379376ccd7e3d2c118e2a15c4a28dd` | NewTwapPeriod(uint32) *(openchain+keccak-confirmed)* |
| `0x0c1be0b2d0e453076b8bb6ce5a43299a77c60998b2471f24daaf7d886dd9f95c` | NewUniPriceConverter(address) *(openchain+keccak-confirmed)* |
| `0x74da04524d50c64947f5dd5381ef1a4dca5cba8ed1d816243f9e48aa0b5617ed` | OperatorTransferred(address indexed previousOperator, address indexed newOperator) |
| `0x646fe5eeb20d96ea45a9caafcb508854a2fb5660885ced7772e12a633c974571` | OwnershipTransferConfirmed(address indexed previousOwner, address indexed newOwner) *(2-step)* |
| `0xb150023a879fd806e3599b6ca8ee3b60f0e360ab3846d128d67ebce1a391639a` | OwnershipTransferInitiated(address indexed previousOwner, address indexed newOwner) *(2-step)* |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | OwnershipTransferred(address indexed previousOwner, address indexed newOwner) *(OZ)* |
| `0xa92a2b95c8d8436f6ac4c673c61487364f877efb9534d4296fad8ef904546c94` | PairCreated(address indexed pair, address indexed tokenA, address indexed tokenB) *(Wild PairFactory)* |
| `0x73cca62ab1b520c9715bf4e6c71e3e518c754e7148f65102f43289a7df0efea6` | PoolAdded(address indexed pool) |
| `0x64e6e7bd72b853c4e62fd6ceaca05a104700c70a4cb567c75c7f2242ba7f037c` | PriceUpdate(address indexed owner, uint256 newPrice) |
| `0x934d569426d283fac73ada3c014b2a891b0d69f541eb3efc761d9b29377a90f9` | QueueTransaction(bytes32 indexed txHash, address indexed target, bytes data, uint256 eta) |
| `0x76e2796dc3a81d57b0e8504b647febcbeeb5f4af818e164f11eef8131a6a763f` | QueueTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta) |
| `0xb0850b8e0f9e8315dde3c9f9f31138283e6bbe16cd29e8552eb1dcdf9fac9e3b` | Rebalance(address indexed oldAsset, address indexed newAsset, uint256 assets) |
| `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | RewardAdded(uint256 reward) |
| `0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486` | RewardPaid(address indexed user, uint256 reward) |
| `0xb7261e9c33aa7c56209c3bf60b424a8f9551ce28876c0ab3d0c487695e943487` | SetOracle(address indexed oldAddr, address indexed newAddr) |
| `0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d` | Staked(address indexed user, uint256 amount) |
| `0x7c6a000d6581009ece38db2bf0a802db87c25d55bdf668f06a962b9c71884773` | Received(address) *(openchain+keccak-confirmed)* |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | Transfer(address indexed from, address indexed to, uint256 value) |
| `0xd78a0cb8bb633d06981248b816e7bd33c2a35a6089241d099fa519e361cab902` | Updated(uint256 price0CumulativeLast, uint256 price1CumulativeLast) *(UniV2 TWAP oracle)* |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | Upgraded(address indexed implementation) *(EIP-1967 proxy)* |
| `0x5d9c31ffa0fecffd7cf379989a3c7af252f0335e0d2a1320b55245912c781f53` | VaultCreated(address indexed vault, address indexed token) |
| `0x2bdc5c4e10b58c4ee8c2641a6c2d28a9555ff641bec6dd0e8151756e152b4f01` | Verification(uint256 _uid) |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | Withdraw(address indexed account, uint256 amount) |
| `0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568` | Withdraw(address indexed user, uint256 indexed pid, uint256 amount) *(MasterChef)* |
| `0xcbc7c7858f9ab8ce22517d4b910042540172c3d579222cf6716e222f341ca371` | WithdrawRequest(address indexed account, uint256 amount, uint256 withdrawAt) |
| `0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5` | Withdrawn(address indexed user, uint256 amount) |

---

## 2. Wild Credit — the largest sub-protocol

Isolated-pair lending: each **LendingPair** holds exactly two tokens (`tokenA`/`tokenB`), and can additionally take a **Uniswap V3 LP position** (`depositUniPosition`/`uniPosition`) as collateral — the feature Wild Credit was known for. A **PairFactory** clones pairs from a `lendingPairMaster` template; a single **LendingController** holds global risk params (collateral factors, min-borrow, deposit/borrow limits, the price-oracle pointer); a **PriceOracle** maps tokens to Chainlink feeds (`addLinkOracle`) and converts values; **veWILD** is the vote-escrow (lock WILD → veWILD, claim income); **xWILD** is a staking wrapper.

### 2.1 LendingPair (per-pair; minimal-proxy clones of `lendingPairMaster`) — selectors

The workhorse contract. Several versions exist (plain, `wildCall`-flash variant, integrated-swap variant); selectors below cover them. Verified present in bytecode of e.g. `0xef543229…` (G114), `0xe5b09744…` (G36), `0xe5862651…` (G108), `0xae135a1b…` (G123).

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x47e7ef24`* | `deposit(address account, address token, uint256 amount)` | supply collateral/lend. (`deposit(address,address,uint256)`) |
| — | `withdraw(address token, uint256 amount)` / `withdraw(address,address,uint256)` / `withdrawAll(address)` | redeem supply |
| — | `borrow(address token, uint256 amount)` *or* `borrow(address,address,uint256)` | take debt |
| — | `repay(address account, address token, uint256 amount)` / `repayAll(address,address,uint256)` | repay debt |
| — | `depositRepay(address,address,uint256)` / `depositRepayETH(address)` / `withdrawBorrow(address,uint256)` / `withdrawBorrowETH(uint256)` | combined supply+repay / borrow+withdraw helpers (ETH variants wrap WETH) |
| — | `depositUniPosition(address account, uint256 tokenId)` / `withdrawUniPosition()` / `uniPosition(address)` | **Uniswap V3 NFT position as collateral** (the signature Wild Credit feature) |
| — | `liquidateAccount(address account, address token, uint256 maxRepay[, uint256])` | liquidation |
| — | `accountHealth(address)` / `checkAccountHealth(address)` / `LIQ_MIN_HEALTH()` | solvency views (health < `LIQ_MIN_HEALTH` ⇒ liquidatable) |
| — | `accrue(address)` / `lastBlockAccrued(address)` / `supplyRatePerBlock(address)` / `borrowRatePerBlock(address)` | **per-block** interest accrual |
| — | `colFactor(address)` / `minBorrow(address)` / `borrowLimit(address,address)` / `depositLimit(address,address)` | risk params (read from controller) |
| — | `supplyOf(address,address)` / `debtOf(address,address)` / `supplySharesOf(address,address)` / `debtSharesOf(address,address)` / `totalSupplyAmount(address)` / `totalDebtAmount(address)` | balances (share-based accounting) |
| — | `lpToken(address)` / `transferLp(address,address,address,uint256)` | the pair's per-token LP share token |
| — | `tokenA()` / `tokenB()` / `lendingController()` / `interestRateModel()` / `feeRecipient()` | wiring |
| — | `wildCall(bytes)` | **flash-loan callback** (the `*flash` pair variant) |
| — | `operate(uint256[] actions, bytes[] data)` | batched multi-action entrypoint (newer variant) |
| — | `liqFeeSystem(address)` / `liqFeeCaller(address)` / `pendingSystemFees(address)` / `collectSystemFee(address,uint256)` | liquidation-fee split |
| `0x150b7a02` | `onERC721Received(address,address,uint256,bytes)` | accepts the UniV3 NFT |

\* `deposit(address,address,uint256)` = selector `0x8340f549` (resolved); the per-version selector set differs — read the live pair bytecode.

### 2.2 LendingController — selectors & events

Global risk engine. Flagships: **`0x2ca9b2cd3b50a4B11bc2aC73bC617aa5Be9A6ca1`** (G119) and **`0x45ee906e9cFae0aaBdb194d6180A3a119d4376C4`** (G164, a later "origin-fee + minBorrowUSD" version).

| Selector / Event | Signature |
|------------------|-----------|
| fn | `setColFactor(address,uint256)` / `setMinBorrow(address,uint256)` / `setMinBorrowUSD(uint256)` / `setBorrowLimit(address,address,uint256)` / `setDepositLimit(address,address,uint256)` |
| fn | `setPriceOracle(address)` / `setInterestRateModel(address)` / `setLiqParamsToken(address,uint256,uint256)` / `setOriginFee(address,uint256)` / `setFeeRecipient(address)` |
| fn | `enableBorrowing()` / `disableBorrowing()` / `enableDeposits()` / `disableDeposits()` / `setBorrowingEnabled(bool)` / `setDepositsEnabled(bool)` / `allowGuardian(address,bool)` / `isGuardian(address)` |
| fn (views) | `colFactor(address)` / `minBorrow(address)` / `borrowLimit(address,address)` / `depositLimit(address,address)` / `tokenPrice(address)` / `tokenPrices(address,address)` / `priceOracle()` / `interestRateModel()` |
| event | `NewColFactor(address,uint256)`, `NewMinBorrow(address,uint256)`, `NewMinBorrowUSD(uint256)`, `NewPriceOracle(address)`, `NewDepositLimit(address,address,uint256)`, `NewFeeRecipient(address)`, `BorrowingEnabled(bool)`, `DepositsEnabled(bool)`, `OwnershipTransferInitiated/Confirmed` |

### 2.3 PairFactory — selectors & events

Clones LendingPairs. Flagships: **`0x0fC7E80090BBc1740595B1fCcD33E0e82547212f`** (G116, with `uniV3Helper`/`implementation()`), plus earlier variants `0x23b74796…` (G163), `0x28af489c…` (G179), `0x56108645…` (G182).

| Selector / Event | Signature |
|------------------|-----------|
| fn | `createPair(address tokenA, address tokenB)` → deploys a clone, emits `PairCreated` |
| fn | `pairByTokens(address,address)` (pair lookup) / `lendingPairMaster()` (clone template) / `lpTokenMaster()` (LP-token template) / `lendingController()` / `uniV3Helper()` / `feeRecipient()` / `implementation()` |
| event | `PairCreated(address indexed pair, address indexed tokenA, address indexed tokenB)` — **the pair-discovery anchor** |

> **Discover all Wild Credit pairs from `PairCreated` (topic0 `0xa92a2b95…`) on the factory**, then watch each pair's deposit/borrow/`liquidateAccount`. Pairs are minimal-proxy clones of `lendingPairMaster` — their own EIP-1967 impl slot is empty; the impl is baked into the clone bytecode.

### 2.4 PriceOracle — selectors & events

Flagships: **`0x65e2cf21e7D3A0c9aaB02DB2577a1e827C899436`** (G124), `0x24391869…` (G165), `0xb40462f8…` (G178, with `setTokenPrice`); a UniV2-TWAP oracle at `0xffdf8499…` (G94, `consult`/`update`/`getReserves`); a UniV3 position helper at `0x0dca1a3f…` (G117, `decreaseLiquidity`/`onERC721Received`).

| Selector / Event | Signature |
|------------------|-----------|
| fn | `addLinkOracle(address token, address chainlinkFeed)` / `removeLinkOracle(address)` / `setTokenPrice(address,uint256)` / `convertTokenValues(address,address,uint256)` / `tokenSupported(address)` |
| fn (TWAP) | `consult(address)` / `update(address)` / `getReserves()` / `token0()` / `lastUpdateAt(address)` |
| event | `AddLinkOracle(address,address)`, `SetOracle(address,address)`, `PriceUpdate(address,uint256)`, `Updated(uint256,uint256)`, `NewTwapPeriod(uint32)`, `NewMinObservations(uint16)`, `NewUniPriceConverter(address)` |

### 2.5 veWILD (vote-escrow) & xWILD (staking)

veWILD: lock WILD for time → veWILD; accrues protocol income. Selectors: `lock(uint256 amount, uint256 duration)`, `lockedBalanceOf(address)`, `lockedUntil(address)`, `claim()`, `pendingAccountReward(address)`, `requestWithdraw()`, `withdraw()`, `withdrawAt(address)`, `addIncome(uint256)`, `rewardRate()`, `rewardPerToken()`, `distributionPeriod()`. Events: `Lock`, `Claim`, `NewIncome`, `WithdrawRequest`, `Withdraw`, `Transfer`. **veWILD is fronted by a TransparentUpgradeableProxy** (e.g. `0xc4347dbd…` is the proxy: `upgradeTo`/`upgradeToAndCall`/`changeAdmin`/`admin`; the `Lock`/`Claim` events fire through it).

### 2.6 Wild Credit — flagship addresses

| Role | Address | Notes |
|------|---------|-------|
| **WILD** (governance token, 100M) | `0x08a75dbc7167714ceac1a8e43a8d643a4edd625a` | "Wild Credit" — the canonical WILD. |
| WILD (earlier/test instances) | `0x403d512aB96103562DCaFe4635545E8Ee2753f6e`, `0xacfe71002347d635c05ee8D1cC1Ab93b548eD0a6`, `0xad997Ca6497173C1831bd39200Db13c410B0Ff3C` | older deployments — distinguish by address. |
| veWILD (vote-escrow) | `0x5cCAFE74b0271aC80573044d1450E2b836f839FD`, `0x879f2aD840e3F920b16982E55455D0905DDf164E`, `0x1d74408fc603B9b130535d7CF2009B6809E042Ff`, `0x1Ae3C2651ae6Fe7463B0C1B73a2b5855d34caFA2`, proxy `0xc4347dbDa0078d18073584602cF0c1572541bb15` | multiple iterations; read live. |
| xWILD (staking) | `0xb0f466CC45DC73d0A6Ea889C63390aeEa7B6dcc5` *(live, ~357k supply)*, plus `0xc7631366…`, `0xdfAD0502…`, `0xc12ce0c8…`, `0x55fbc2e2…`, `0xc452aec6…`, `0x5fffb329…` | |
| WILD-LP | `0xe0FaDA235382Ff2e63c021f2974f6C51Ab8cE368`, `0x8014481101D931C74FfcF96Ef839f344b0bE26b8`, `0x277AA659750AB673B550d842c9e8AA1592Ea5925` | per-pair LP share tokens. |
| wBOND / bCRED | `0xdB8a9e26bF319D1bbD04A8e13B02652C0B14b400` / `0xb7412e57767ec30A76a4461D408d78B36688409c` | bond / credit tokens. |
| LendingController | `0x2ca9b2cd3b50a4B11bc2aC73bC617aa5Be9A6ca1`, `0x45ee906e9cFae0aaBdb194d6180A3a119d4376C4` | global risk engine (read live for the active one). |
| PairFactory | `0x0fC7E80090BBc1740595B1fCcD33E0e82547212f` (+ `0x23b74796…`, `0x28af489c…`, `0x56108645…`) | emits `PairCreated`. |
| PriceOracle | `0x65e2cf21e7D3A0c9aaB02DB2577a1e827C899436` (+ `0x24391869…`, `0xb40462f8…`, TWAP `0xffdf8499…`, UniV3 helper `0x0dca1a3f…`) | |
| LendingPair (sample clones) | `0xef543229bE38C10F4D705E51b1F95D5077bcBe73`, `0xe5B0974a457698b171e5541378Dbec55E0e2EE62`, `0xe5862651A033CdDcB8f3b4Af9c063DB2bAEC39d0`, `0xae135A1b33C0d3682390762ea2bE6c7419Cf425a`, early `0xfAD877d50022D955b17242B560A8638Fc258173E` / `0xD9dC00f04064b42f0B051f006DF545efe771041d` | enumerate the full set from `PairCreated`. |

---

## 3. Basis Gold (seigniorage fork)

A Basis-Cash–style 3-token seigniorage system pegged to "gold" (XAU): a peg token + **bond** (`buyBonds`/`redeemBonds`) + **share**, a **Boardroom** (stake share → earn seigniorage), and a **Treasury** that runs `allocateSeigniorage()` once per epoch when the peg token trades above ceiling. Tokens: **BSG** (peg), **BSGB** (bond), **BSGS** (share).

**Selectors** (treasury/token, e.g. `0xb471e50c…` G67 22.5 KB, `0xba0c5019…` G79): `allocateSeigniorage()` / `allocateSeigniorage(uint256)`, `buyBonds(uint256,uint256)`, `redeemBonds(uint256,uint256)`, `boardroom()`, `bond()`, `share()`, `gold()`, `goldOracle()`, `getGoldPrice()`, `goldPriceOne()`, `goldPriceCeiling()`, `getReserve()`, `getCurrentEpoch()`, `nextEpochPoint()`, `setFund(address)`, `setFundAllocationRate(uint256)`, `setPeriod(uint256)`, `migrate(address)`, `transferOperator(address)`, plus ERC-20 `mint`/`burn`.

**Events:** `BoardroomFunded(uint256,uint256)`, `ContributionPoolFunded(uint256,uint256)`, `ContributionPoolRateChanged(address,uint256)`, `BoughtBonds(address,uint256)`, `Initialized(address,uint256)`, `OperatorTransferred`, `Migration(address)`, `OwnershipTransferred`.

**Addresses:** BSG `0xb34Ab2f65c6e4F764fFe740ab83F982021FaeD6d`, BSGB `0x7259354a43DF5f405f4Becce4468C25d48b2B00C` & `0x940C7CCD1456B29A6F209b641Fb0eDaa96A15C2D`, BSGS `0xA9d232cc381715aE791417B624D7C4509D2c28DB`; treasury/boardroom `0xb471e50c75DEd7405B136a7ab684f4BAB09B4b3D`, `0xba0C5019eD0215e156Df4f266FC062Bb3716ED20`, `0xcab78d79c0eB514822d5cfd74bE0707BF3FB8c9a`, `0xeeEEFf73060e9F36a270Ad8a843F7D719cE2f79F`.

---

## 4. UpDown.finance

**Binary up/down options** keyed to a TWAP oracle. Per epoch, users `buyUp`/`buyDown`; at expiry `resolve()` settles to a winning side (`resolvedTo`), and winners `claim`. Token **UPDOWN** `0xfBFaF8d8E5d82e87b80578fd348f60fb664E9390`.

**Selectors** (market, e.g. `0x86e61309…` G85, `0x8cbfc74f…` G87, 11 KB): `buyUp(uint256)`, `buyDown(uint256)`, `claim(uint256 epoch)`, `resolve()`, `resolvedTo(uint256)`, `winAmount(uint256,address)`, `sharesOfUp(uint256,address)`, `sharesOfDown(uint256,address)`, `totalSharesUp(uint256)`, `totalSharesDown(uint256)`, `purchasedOfUp/Down(uint256,address)`, `currentEpoch()`, `isTimeOpen(uint256)`, `latestBidTime()`, `MIN_BID_TIME()`, `oracle()`, `oraclePair()`, `lastTWAP()`, `update(address)`, `nextUpdateAt(address)`, `setFeeBps(uint256)`, `setMaxSupply(uint256)`, `setFeeRecipent(address)`, `resolve()`. **Addresses:** markets `0x86e61309cA10b2f40fd9d738e62caCAB2fE8111a`, `0x8cbFc74f3F21ec3DD488e2F6B0FB16fD0A7Bf7e2`, factories/aux `0x26f939e4…`, `0x284a68d7…`, `0x535d31de…`.

---

## 5. Cross-cutting infrastructure

- **Vault / index ("X")** — `VaultCreated(vault,token)`, `Rebalance(oldAsset,newAsset,assets)`, `NewRebalancer`, `NewDepositLimit(vault,amount)`. Share-token symbol **`X`**: `0xaf130719…`, `0x257d36b9…`, `0x3fd288e4…`, `0xb3a4b3ce…`, `0x674c298f…`. Vault factories: `0x30795cf4…`, `0xa1561494…`, `0x5fd31de5…`.
- **Timelocks** — Compound-style (`QueueTransaction`/`ExecuteTransaction`/`CancelTransaction`, both the v2 `(…,string signature,…)` and a compact `(…,bytes data,…)` form). Instances: `0x8b164cef…`, `0xa94695e9…`, `0x38bce4b4…`, `0xa941381f…`, `0x481b81c5…`, `0xfd66fb51…`.
- **MasterChef farms** — `Deposit/Withdraw(address indexed user, uint256 indexed pid, uint256 amount)` (same topic0s as DODO V1 mining): `0x06831e89…`, `0x3220269e…`, `0x4de3ba29…`.
- **Proxies (EIP-1967 / Transparent)** — `Upgraded(address indexed implementation)` (`0xbc7cd75a…`), ProxyAdmin/TransparentUpgradeableProxy stubs (`upgradeTo`/`changeAdmin`/`admin`): `0x134e553e…`, `0x17a4d75c…`, `0x3c8f118f…`, `0x8ddae4f3…`, veWILD proxy `0xc4347dbd…`. Read the EIP-1967 impl slot `0x360894…bbc` on these (the rest of the fleet is non-proxy: plain contracts or minimal-proxy clones).

---

## 6. Deployer "fingerprints" (how to recognize a fleet contract)

These appear across multiple sub-protocols and identify 0xdev0's code:

1. **`LOCK8605463013()`** — a no-arg marker function present in the bytecode of *most* substantive fleet contracts (LendingPairs, factories, treasuries, oracles, veWILD). A near-unique tell of this deployer's contracts.
2. **Two-step + timeout ownership** — `OwnershipTransferInitiated`/`OwnershipTransferConfirmed` (a custom 2-step Ownable, **not** OZ's `OwnershipTransferred`), plus a **renounce-with-timeout** scaffold: `initiateRenounceOwnership()` / `acceptRenounceOwnership()` / `cancelRenounceOwnership()` / `RENOUNCE_TIMEOUT()` / `renouncedAt()`, and `acceptOwnership()`/`pendingOwner()`/`isOwner()`. Also `returnOwnership()` and `rescueToken(address,uint256)` on early pairs.
3. **`Panic(uint256)`** in many ABIs — solc-0.8 panic re-export surfaced by the selector scan (not a real event to monitor; ignore `0x4e487b71`).
4. **`3bb732b9`** — an unresolved selector recurring across Wild Credit contracts (likely an internal/guard function); useful as a same-codebase marker.
5. **`convertTokenValues(address,address,uint256)`** — the oracle value-conversion primitive shared by controller + oracle.

---

## 7. Detection invariants & gotchas

1. **None of this is "Metric."** Metric.exchange = the token + 0x/KeeperDAO ([`core.md`](core.md)). This file is the founder's *other* protocols (Wild Credit, UpDown, Basis Gold). Do not label Wild Credit lending events as "Metric lending."
2. **All unverified.** No source on Etherscan/Blockscout/Sourcify for any of the 306. Signatures here are reverse-engineered (bytecode + live logs + keccak), not source-confirmed. Re-derive against the live contract before relying on any single arg layout.
3. **Name collisions everywhere.** `Deposit`/`Withdraw` exist in ≥3 distinct shapes (Wild pair vs MasterChef `(user,pid,amount)` vs `(address,uint256,string)`); `CancelTransaction`/`QueueTransaction`/`ExecuteTransaction` each have a v2 `(string signature)` and a compact `(bytes data)` form; `OwnershipTransferred` (OZ) vs `OwnershipTransferInitiated/Confirmed` (custom). **Key on `(chainId=1, address, topic0)`** — the exact topic0 disambiguates the variant.
4. **Pairs/vaults are minimal-proxy clones** of a master template — their EIP-1967 impl slot is empty; discover them from `PairCreated`/`VaultCreated`, not a static list. The ~110 "WildCredit"-tagged addresses in the appendix are a *snapshot*; enumerate live.
5. **Many contracts are dead/dust.** Most hold ~0 balance (the `0xdev0` operation ran on testnet-grade liquidity); treat the fleet as low-TVL experiments, not high-value monitoring targets — *except* WILD/veWILD if Wild Credit is still being used.
6. **Interest is per-block** (`supplyRatePerBlock`/`borrowRatePerBlock`/`lastBlockAccrued`), not per-timestamp — unlike e.g. Moonwell.
7. **Ethereum-only.** Nothing on the other six chains.

---

## 8. Quick-copy detection constants (bytea-ready for Postgres)

```
-- ===== EOAs =====
ADDR_DEPLOYER_EOA      = '\x2cb037bd6b7fbd78f04756c99b7996f430c58172'  -- METRIC + 142 more
ADDR_OPERATOR_EOA      = '\xd7b3b50977a5947774bfc46b760c0871e4018e97'  -- 0xdev0; 163 contracts; owner() of most

-- ===== Wild Credit flagships =====
ADDR_WILD_TOKEN        = '\x08a75dbc7167714ceac1a8e43a8d643a4edd625a'
ADDR_WILD_CONTROLLER   = '\x2ca9b2cd3b50a4b11bc2ac73bc617aa5be9a6ca1'
ADDR_WILD_CONTROLLER2  = '\x45ee906e9cfae0aabdb194d6180a3a119d4376c4'
ADDR_WILD_PAIRFACTORY  = '\x0fc7e80090bbc1740595b1fccd33e0e82547212f'
ADDR_WILD_ORACLE       = '\x65e2cf21e7d3a0c9aab02db2577a1e827c899436'
ADDR_VEWILD_PROXY      = '\xc4347dbda0078d18073584602cf0c1572541bb15'
ADDR_XWILD_LIVE        = '\xb0f466cc45dc73d0a6ea889c63390aeea7b6dcc5'

-- ===== UpDown / Basis Gold tokens =====
ADDR_UPDOWN_TOKEN      = '\xfbfaf8d8e5d82e87b80578fd348f60fb664e9390'
ADDR_BSG               = '\xb34ab2f65c6e4f764ffe740ab83f982021faed6d'
ADDR_BSGS              = '\xa9d232cc381715ae791417b624d7c4509d2c28db'

-- ===== Wild Credit discovery / lending events =====
TOPIC_PAIR_CREATED     = '\xa92a2b95c8d8436f6ac4c673c61487364f877efb9534d4296fad8ef904546c94'
TOPIC_NEW_COL_FACTOR   = '\x93f89a4ade64affae107c642c1a64962fbccf628af01c63a6fbd0928697a5acf'
TOPIC_NEW_MIN_BORROW   = '\x784ec2eb964e8fb9a1b293a1dc19b1bf33e48c9a6e63a2894b3ab6f800add2ca'
TOPIC_ADD_LINK_ORACLE  = '\x6a75ebadc337734596edf1289381bebea46d6708a4c05ed096a5ac94d3a20d75'
TOPIC_NEW_PRICE_ORACLE = '\xf261845a790fe29bbd6631e2ca4a5bdc83e6eed7c3271d9590d97287e00e9123'
TOPIC_BORROWING_ENABLED= '\xbb614ecd1ed5d1454c15f856743fff55fa975d6257e7262b092a86067ceda764'
TOPIC_VEWILD_LOCK      = '\x0e31f07bae79135368ff475cf6c7f6abb31e0fd731e03c18ad425bd9406cf0c0'
TOPIC_VAULT_CREATED    = '\x5d9c31ffa0fecffd7cf379989a3c7af252f0335e0d2a1320b55245912c781f53'
-- ===== Basis Gold / UpDown =====
TOPIC_BOARDROOM_FUNDED = '\x03ca7276ab7799bf73fb79d27ff0610cd7049574f2508ef8445162833d439aea'
TOPIC_BOUGHT_BONDS     = '\xdbf5270c3cf4729fec4fdac76fda864aa4f3d14d657ad21772ac28f627141ed9'
-- ===== proxy / timelock =====
TOPIC_UPGRADED         = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_QUEUE_TX_V2      = '\x76e2796dc3a81d57b0e8504b647febcbeeb5f4af818e164f11eef8131a6a763f'
```

---

## 9. Full address appendix (all 306 fleet contracts, grouped by deployer EOA)

Tags are role/sub-protocol inferred from bytecode+events; `[SYM]` = on-chain `symbol()`. This is a 2026-06-05 snapshot — clones (pairs/vaults) keep being created, so enumerate live from `PairCreated`/`VaultCreated` for the current set.

**Deployer EOA `0x2Cb0…8172` — 142 contracts (also deployed the METRIC token, listed in core.md):**

```
0x04818034947951151b5b6094d9eb87b47c039eec  Token/ERC20
0x0611891580b8aad2d67d21d42cf051e3255542ec  Unknown/Helper
0x06514f4e3d2362b498fb07d24e2455d408a97170  AMM/DEX
0x0b5be054145a4f4a90374b2c6220c15943ff5398  Unknown/Helper
0x110c76650ff5ad825ea708c1903cf8ccda888799  Unknown/Helper
0x13252c8bf26647ceccd70a7dd49cf64e70ad3bf0  AMM/DEX
0x1457dd7eee6457b727840e985750aeb7c065ae0b  veToken/Staking
0x1a96fa58e2499111eee3d54db65daef3ea6e74c9  Unknown/Helper
0x1b7db08d5497c1f6c03af5e4b7250a30a78b60dd  Unknown/Helper
0x1eb9c74186b504b4d679c07b2203cae1f0b7e268  Unknown/Helper
0x2111c5e977b13d1a3b94603c0cabf5a591adc25c  Unknown/Helper
0x21ab213d86aaac5e6c2dbae5bfa2fd1247dda356  veToken/Staking
0x243a16c59e07033199addb38c03ac4a17da820e3  Unknown/Helper
0x25c0d3c4606dcfe73b9bfe8263f20fdf6c49406e  Unknown/Helper
0x26f939e499794e111d0d52c5a4f09e65fbb730e5  UpDown
0x284a68d7ebf6441376aee7dd1419e24ae5d87e47  UpDown
0x2c5133a7149fa00084329b6fd052f70b716113da  Unknown/Helper
0x2cf861957c7932e80eb171cb698a17bbcc28730e  veToken/Staking
0x3157439c84260541003001129c42fb6aba57e758  Token/ERC20
0x35343813769c146e900afbf6106ff1b1e7c10905  veToken/Staking
0x3628faf211c1d1060226783113f051733766777e  Token/ERC20
0x38bce4b45f3d0d138927ab221560dac926999ba6  Timelock/Gov
0x3b871056e9f13aa3ba5b4dc3f71f00f7dc652199  veToken/Staking
0x3e823bdd69b7e2e48df96e6701ef049c9e24aaec  Unknown/Helper
0x3ea5527f862d88781845c81e48724b1ce1317566  AMM/DEX
0x417361fb006ca34d87535c02c9d710e1dbd639aa  AMM/DEX
0x431505a812373eb1b9c9dda80d52691acea59108  Unknown/Helper
0x4330e43f5b1e7d3ea7b0a177af50c6b2489ca406  veToken/Staking
0x4573dffca2fd899793ab2f50b5e4d86cc7dc28a3  veToken/Staking
0x46a71f71c059d96591e1cefcee46defbae529d3b  WildCredit
0x48b5bcdb2cb7444b197d73b9ddb83e490cc8b695  Unknown/Helper
0x49c3846da57465638703eaeaa0b8cc2e3376008d  Token/ERC20  [HYPE]
0x4be857b93d5075aba72ccf2461906ffde1e145e9  Unknown/Helper
0x4e1f166cb1bfb34cb0e361abdc402acf586a8932  Unknown/Helper
0x4ee08a94279a3ad241f8f785a1abdec775809a62  veToken/Staking
0x535d31de3850ecae0161a586664d4ca5d437b48b  UpDown
0x5379ef07eed84da062241788c43a0709759d2917  Token/ERC20
0x54844fa5dd5da093f727c229b97d95e336938fc2  veToken/Staking
0x5988bd402f1efcdbb3e2ab8537093e6484650046  Unknown/Helper
0x5a6ebeb61a80b2a2a5e0b4d893d731358d888583  Token/ERC20
0x5aaaf38e6c4a6ee5848bb68e3087139f0ddbebf2  Unknown/Helper
0x5b85877d33ca6b86f0f82329f24ca82bdedd09ac  veToken/Staking
0x5e3a9e69401088fb4bfcb8488b84d9cec70134e1  Token/ERC20  [HYPE]
0x5f69d96dd0b72493f7df05ad81f272f6fdb7d483  Unknown/Helper
0x62986352f86eddebb2eb82347b274507c0698316  Unknown/Helper
0x62b5ebd2ac15c378a56c217ed18de7b352229cb1  Unknown/Helper
0x64eaa9e62d532a91952e018d46bc8ccf93997b34  Minimal/Stub
0x6696e1812c42a27e2b3c3604998ca1ab97456d3c  AMM/DEX
0x6d9438cd0df10a78de373f5d9b5b5e7227e3822d  veToken/Staking
0x6e36556b3ee5aa28def2a8ec3dae30ec2b208739  Token/ERC20  [BUILD]
0x6e58d0beac040f56d396ddb9d7f6110bcc7722ff  veToken/Staking
0x6ffa986352cd35618df468e0291d1e7688241a8f  Unknown/Helper
0x7259354a43df5f405f4becce4468c25d48b2b00c  Token/ERC20  [BSGB]
0x7497dd9ddfc8aeecd8f368f8cf8e754e81fb869f  AMM/DEX
0x79dee3049c3211ff9f412352a10e1989fae80847  AMM/DEX
0x7c21f00b0086ce78b60780d55a05bb1b1f65214f  AMM/DEX
0x7fb1c1f093a95b5efbc16973590936fc9a3fb812  Token/ERC20
0x82802e0972a535f343cf634e1902f04efdca0bdc  Minimal/Stub
0x8316f11b85dcd50ccbaa029be65b9a4018a6f344  Token/ERC20
0x84a7559dbe02256d6d6f1b184517d65780c83b9b  Token/ERC20
0x859a9d0d8bbf57c390a0bd8fb4f5de617e1de535  veToken/Staking
0x86e61309ca10b2f40fd9d738e62cacab2fe8111a  UpDown
0x88169f9a271c11bdbbe0161d2db4d4ffa6f27f8e  Unknown/Helper
0x886e3a3d3c81335cfacddc695f870d0d379ec0c4  Unknown/Helper
0x8956b7b7a94d3ec5065db0de3999e57e9e0e0716  Token/ERC20
0x8aa177e9f38e76d161b8a09f12bc0112104d7ffe  veToken/Staking
0x8b164ceffb591b10514d41e8beef623139d69b05  Timelock/Gov
0x8c55a6c3ca5b14dc44cbc428aab91280f7cac527  Unknown/Helper
0x8cbfc74f3f21ec3dd488e2f6b0fb16fd0a7bf7e2  UpDown
0x8d4507e16efcd02f4434b2498cfface9a05c9955  Token/ERC20  [DPOOL]
0x8f793199304bcb82c4d1edae2612fcf590441f3b  veToken/Staking
0x911b32927ff1bead42fc8d1e4581ed516c4ef917  Minimal/Stub
0x940c7ccd1456b29a6f209b641fb0edaa96a15c2d  Token/ERC20  [BSGB]
0x944d7a25e481cc2912e30cfd0b186c06bb15d648  Unknown/Helper
0x96dd8183f1c5f9d8d6617f72cd11bb82ecbdfeb7  Unknown/Helper
0x96e343a080da853c168afe6e5b6d8cb98386de35  veToken/Staking
0x97da5d4b52d2596cfff78372ecb7084088140779  veToken/Staking
0x989a1b51681110fe01548c83b37258fc9e5dfd0e  Token/ERC20  [CPOOL]
0x9e3e903f75baf410525278404ae2a8ada9336f67  Token/ERC20  [Hype]
0x9e8fa6ab0528578eaf9d1bb022aac22831770c26  AMM/DEX
0x9f7a46850d9ca08db2175bb5e28fcc0298689c22  Unknown/Helper
0xa0e56853e947f071964264a1e46651faa37ab177  Unknown/Helper
0xa250c1d07fc0049de5e2a3a8a916517914846b40  veToken/Staking
0xa451c734f29711ada1cfc3b4d71ea803737bc7e7  veToken/Staking
0xa4fc2439267b4ee63600e175aa4655b81668ff8a  Unknown/Helper
0xa67d1fee145587372bb6f94378f9d178fcaa1365  AMM/DEX
0xa7657e2058ff43d0b9eb9d6114f59dc32a5ec944  Minimal/Stub
0xa8621477645f76b06a41c9393ddaf79ddee63daf  Token/ERC20
0xa94695e9074176099653524c450f283e6ce1f149  Timelock/Gov
0xa9d232cc381715ae791417b624d7c4509d2c28db  Token/ERC20  [BSGS]
0xae38d486af40a402a4aa1e4d5f4a7e07791ec04f  veToken/Staking
0xae49f34331f31e1c1ada91213b47b4065a04516b  veToken/Staking
0xb0a7f9552ce8b16c59a1696d577ec327a803b6fe  Token/ERC20
0xb254da7c8e6e65a6976c6cb6ac4cf49186bbaaf6  Unknown/Helper
0xb34ab2f65c6e4f764ffe740ab83f982021faed6d  Token/ERC20  [BSG]
0xb453fc3fe4173a0de51c799d42a4c58f6b7f0ff2  Unknown/Helper
0xb471e50c75ded7405b136a7ab684f4bab09b4b3d  BasisGold
0xb4d78f3a0fa97d42bff0f7f9cedfe2fe23eeca05  veToken/Staking
0xb7412e57767ec30a76a4461d408d78b36688409c  Token/ERC20  [bCRED]
0xb7b7e0a038f3112fe01bd220bc076a1974f039a5  AMM/DEX
0xb83cb1f9cd7ff5e748d4798d1198e783083204b3  Unknown/Helper
0xb8dc5e54211191689715b8edb8a31b65f022e493  Unknown/Helper
0xba0c5019ed0215e156df4f266fc062bb3716ed20  BasisGold
0xbbecd4fc3c04769837dca2305eef53dc3cf4e620  veToken/Staking
0xbfb333b07a7209cb4323b4148ff1640ea29c1874  AMM/DEX
0xc0baeacc6ed67aff27ec55b238fc2fc2b5fa50d0  veToken/Staking
0xcab78d79c0eb514822d5cfd74be0707bf3fb8c9a  BasisGold
0xcae422363d45d7d6e876afac4af06127b74b11bb  Unknown/Helper
0xcb0eaf940ef7cf5ed2f526400d473f36f598935d  Unknown/Helper
0xcf5ff79a453788914d9aac49d0c80f5e564e4892  Unknown/Helper
0xcf7209fd19a29267ece09ff99831ae44635c6db4  veToken/Staking
0xd1b013cd7386e6eba235104e1aa492a2b2a5d081  veToken/Staking
0xd22df8a977f616731f31864335bf31bd0b38f2b6  veToken/Staking
0xd6def84ab0c520434e95d3849f01a85143da9be4  Token/ERC20  [CPOOL]
0xd9dc00f04064b42f0b051f006df545efe771041d  WildCredit
0xdd54781d7c2bc600c3abbfaeb862dc9d07b452eb  Minimal/Stub
0xde916597e6d66fbbae4580c80479bfd63e584934  Token/ERC20  [Hype]
0xdea45e6b792c59f51d9b4eac84d16762edcde3d1  Token/ERC20
0xdf3f6daa51a2d67d3304495c7a804a4f2f733a59  Unknown/Helper
0xdf9a17a73308416f555783239573913afb77fa8a  Unknown/Helper
0xe1212f852c0ca3491ca6b96081ac3cf40e989094  Token/ERC20  [HYPE]
0xe46a588e68aa30cd4d59b97b87dcdd0c1546a39f  WildCredit
0xe69daa5e01fa1a17bbb1547c45b836fd7cd59a8e  Token/ERC20
0xe6dc7dafcc467a5a0142b44585b4a5223472b689  AMM/DEX
0xe7c169edc44e0e5ee7f27b6af46d9f372769397f  Token/ERC20
0xe8924d460ab7af34d970fb65b39eb1fc246c5a7d  Unknown/Helper
0xe8c05d7fa032964c113a9844027ffce4e2a90122  Unknown/Helper
0xe9c2c3b47a82a2bdf22fd84b06981635cbfb0677  Unknown/Helper
0xea322a8ab474c2c27581b8aeaa5c594141aa5dfb  veToken/Staking
0xeb5850729bcf5b0b3535dc7bdd073e4f7b178861  Token/ERC20
0xee9247b47b31499bdb4e817059a0a6f0bfe46803  Token/ERC20
0xeeeeff73060e9f36a270ad8a843f7d719ce2f79f  BasisGold
0xf03caee35367e55648d8058f8465875009247620  Token/ERC20
0xf08c44a2b2c53c3b86fc03c2675dcb6f02dc0e94  Unknown/Helper
0xf0c23ec77079c2343d9819bccd5e9f568490c2e0  Unknown/Helper
0xf1b9e5ce536593b2f1ee812795fbbb2107ef2210  Unknown/Helper
0xf22cbaaab5c38e624cad7afdb1902d94069f18eb  Unknown/Helper
0xfad877d50022d955b17242b560a8638fc258173e  WildCredit (early LendingPair; holds WILD-LP)
0xfbfaf8d8e5d82e87b80578fd348f60fb664e9390  Token/ERC20  [UPDOWN]
0xfc23e2e15f22d638749194e3ff72c0a12fc4e36d  Unknown/Helper
0xfd15657341492d1918e3a8b7421e9627d52056e9  veToken/Staking
0xffdf8499be85fd50445a201ef3388461f918c9fb  AMM/DEX (Wild UniV2 TWAP oracle)
```

**Operator/owner EOA `0xd7b3…8e97` (0xdev0) — 163 contracts:**

```
0x01eaea91d453a2a1fa02115ad763e54ccd3ea5f1  Unknown/Helper
0x0473910ff52580b0e85a1d333d3b7a1d81063e32  WildCredit
0x04b9d0c1f041bb6820247bb23d1b817e12fb8d60  Unknown/Helper
0x06075cfe2df83ba39faadceba0173447b1f857a5  WildCredit
0x06831e896731afc290c53ab5261b2fddc5cf57bd  Farming/MasterChef
0x08a75dbc7167714ceac1a8e43a8d643a4edd625a  Token/ERC20  [WILD]
0x0dca1a3f48407686da05f50ca6a59a16931aa81d  Oracle (Wild UniV3 helper)
0x0fc7e80090bbc1740595b1fccd33e0e82547212f  WildCredit (PairFactory)
0x0fd91a3f5f3d79afc95bf756fea351b1f51a668c  WildCredit
0x1252ea2bb824557429e83e5bd89a29907ea18643  WildCredit
0x134e553eac5ee8a61521cdd8ac641e688ff13f7d  Proxy
0x141da177d219b44673170b7c7a9bc587f7a9fa60  WildCredit
0x143ba97efee7edd6c3f300216fd2541a96b0c598  Unknown/Helper
0x17a4d75c4964704f3a27b7ae5b94c39770c23a30  Proxy
0x1890ca3b4e2e21d020350cad7a01cf18d8e0a744  Unknown/Helper
0x19157d76bc76c0f727555723cb56deb9db7ca8df  Token/ERC20
0x1ae3c2651ae6fe7463b0c1b73a2b5855d34cafa2  Token/ERC20  [veWILD]
0x1d74408fc603b9b130535d7cf2009b6809e042ff  Token/ERC20  [veWILD]
0x1ffd9e1c038773d1c61dfeb0cdb5afd2d8f28c97  WildCredit
0x21e717a282f88e9a2b129408848fe6d506748735  WildCredit
0x23b74796b72f995e14a5e3ff2156dad9653256cf  WildCredit (PairFactory)
0x24391869e7d7ae4a410d613c17396b6ece227f54  WildCredit (PriceOracle)
0x257d36b97d0067d3033644fb747aa911e42584ec  Vault/Rebalancer  [X]
0x26a6b022edecb9bbe5f37b504d6434d840280cfd  Token/ERC20
0x26fac81478879b7dc10fb5008e392b9dfa213165  Unknown/Helper
0x277aa659750ab673b550d842c9e8aa1592ea5925  WildCredit  [WILD-LP]
0x28af489c8a868337057723b21ceb50134f0154f5  WildCredit (PairFactory)
0x28e3904b2a12f68086d13accca283f978a1ad666  WildCredit
0x2b073198a710bc70e350fdd5b240733339b7b9a3  Unknown/Helper
0x2ca9b2cd3b50a4b11bc2ac73bc617aa5be9a6ca1  WildCredit (LendingController)
0x2d2a0e94619393b4b9ff4255ddf77ae68306e840  WildCredit
0x2ebb8bf07b27bd49a5e9cf1e3383ca787fd9ce1f  Unknown/Helper
0x2fa8bb9bcad729272e3f8728b012513e88b0e019  WildCredit
0x30795cf4613c35efef114c88a0bf2986e3fcb232  Vault/Rebalancer
0x31138ba1ed1db7aa5f17f12422cead6b06f54f56  Vault/Rebalancer
0x31fd80bf06453ace58bea89727e88003f0e691bb  WildCredit
0x3220269e3cfa62270f4d0e5c4245d7b6a0079777  Farming/MasterChef
0x3493791a5d1ef068347d7e1d831670d8ad06bac4  WildCredit
0x34f0c78f0e9cd6cde477088a24f29bb72188c70f  WildCredit
0x386f2874b1366d925f91e8b416b330ebd003d75e  Unknown/Helper
0x3c8f118f21e8d49a633d970a6eedc4e09409b2b5  Proxy
0x3d619bc03014917d3b27b3b86452346af36e58de  Oracle
0x3e8eed7ea2ff2f7eab34eb3047b21fa2b173439d  Unknown/Helper
0x3fcf5ad35d268164170abd94d738563c57dd0939  Unknown/Helper
0x3fd288e4e6c845d26c37102aed1463a238a43c59  Vault/Rebalancer  [X]
0x403d512ab96103562dcafe4635545e8ee2753f6e  Token/ERC20  [WILD]
0x406dbaf03a73fcedb9cb5bc74723e0b584d7cb94  WildCredit
0x41844a657a3c037820ed1c36a529ec179e88d089  Unknown/Helper
0x4294df09d16331c62655607c4ea2d8aec5a8335f  Token/ERC20
0x43e50c57616ab3be66d37755b8dcfe1327293fef  WildCredit
0x45ee906e9cfae0aabdb194d6180a3a119d4376c4  WildCredit (LendingController v2)
0x47dd9fff5e36a4944a759720b396a81588f6fe4d  Oracle
0x481b81c5c0a9a7b2c1c9e92eec9e61dcbd6cb5d6  Timelock/Gov
0x487502f921ba3dadacf63dbf7a57a978c241b72c  Unknown/Helper
0x4c650926416cb7438876aee88481f29f7e9e9450  Unknown/Helper
0x4de3ba2932aa07542dca74b01fb143b6e806a658  Farming/MasterChef
0x5185d866d6b2eb0f9bae995db6f6daf3e5a0f1d0  Token/ERC20
0x530c7287a61fd88201ed9f8691a633bbca896def  WildCredit
0x55fbc2e2131a596c126286ac6bfedf8d1a42c507  Token/ERC20  [xWILD]
0x56108645c4557e672391339776728cc53a28823a  WildCredit (PairFactory)
0x59386094413df798678f45b67345f71113c3c60b  Lending
0x59c88e46a0cc337cee7ce9c453e5e518f944ca05  WildCredit
0x5c89a02076e22e4ee1c011d351304066e8aa94c6  Unknown/Helper
0x5c9a6f148741b297b85110a641200a1617fe6c71  WildCredit (LendingPair, swap variant)
0x5cb095958bdee2aeab18bba0877876c2b73a4e69  WildCredit
0x5ccafe74b0271ac80573044d1450e2b836f839fd  Token/ERC20  [veWILD]
0x5de7832f38923b14d28632c77077532751c6bbe7  Vault/Rebalancer
0x5f71a58bb98e74590479d9b8616116636d320c3b  Unknown/Helper
0x5fd31de528fb1cc17e895a9214ea6d2df17e2463  Vault/Rebalancer
0x5fffb3296c0d9c3cb7cc736c39adc57376d8201a  Token/ERC20  [xWILD]
0x609443abf0f4f97366701529213dc219950d4080  WildCredit
0x610ace4e7bfb9d501dbba714fa3a6a0fcd7783b2  WildCredit
0x65e2cf21e7d3a0c9aab02db2577a1e827c899436  WildCredit (PriceOracle)
0x674c298f3820d200922bbdcb126a76d5a6db10d6  Vault/Rebalancer  [X]
0x682525e2aa0b4a07ed98ab9ea847556004b6914f  Unknown/Helper
0x68dd4e294713ab2ec3b373a8dba5fe00f0fe175a  Unknown/Helper
0x69f2f43e591cb4df6dee11824c75b81e964a7f6c  Unknown/Helper
0x6a0bed085e2a06aea54267108c9eb51293ee7f51  Vault/Rebalancer
0x6de00c7b2c9dfe8e065e1ca8be3be089d6e50ee9  Unknown/Helper
0x6fd599e812f1bc8dc225535db5ca66fda957c7af  Unknown/Helper
0x701a069e8aeaadc1570d0f817d250611a69c3d1c  Unknown/Helper
0x724777c454c5af1ca6231e57429c812726ac84ae  WildCredit
0x7e966846d9db70b0935adf2b7eeefdfbfce0adbc  Unknown/Helper
0x7f8757006809e55cabbb4a97870680d4c2eb4bd5  Token/ERC20
0x8014481101d931c74ffcf96ef839f344b0be26b8  WildCredit  [WILD-LP]
0x81453d099c6c23124d6fb67e183487a8589f38e9  Lending
0x82a55d65307fa6e095b1d3dbe67ef0dc6e69e2fc  Unknown/Helper
0x83b352228d6f88386071a03115c0a5bab011670b  WildCredit
0x845768b704269172e55b7858c5b7406f5e99ffa1  WildCredit
0x879f2ad840e3f920b16982e55455d0905ddf164e  Token/ERC20  [veWILD]
0x88a073d09c9f2041092a72ed288c19ae5da3f098  Unknown/Helper
0x8a8385ca5f3bf51e34826566e7838b1332bfedfc  Token/ERC20
0x8ddae4f348bfc48158ad5c244011b836649128e8  Proxy
0x8e6ab0b7233f19c1cb3a9ba2bfbfa2f6784115a7  Unknown/Helper
0x8f9c6d24603d827d19f5862763ba280c11db7e49  Unknown/Helper
0x8fa5c869a2f17793660e191ee850ce994acb760e  WildCredit
0x929fb65cb8cc1ae04355e7d8be71a522450179ff  WildCredit (LendingPair, swap variant)
0x9417566b9cb7aa6231265d200d2e9440e3278d10  WildCredit
0x94934ef2e630da601489345fbff787362badd6ba  Lending
0x979c49484ed6abfb8f0fc02bec8fcb92844cc789  Token/ERC20
0x993726b3fef1fa124a8fa198d047c36827d2dd20  Oracle
0x9a7b59de763ababd77b3f8089550431ca646c52e  Unknown/Helper
0x9baeaf77f404db8c08e47a153196f0c4b05acff3  Unknown/Helper
0xa1561494dcd9f1c3ede6a965302a851d2a7e1a74  Vault/Rebalancer
0xa474868accc4757ff4f1e680ddad3eec3fedfc67  Unknown/Helper
0xa658b50a1ed384d457244cd16c3af11a9efc40e8  Unknown/Helper
0xa69690e1b4990f0ba537cfcd38b810a978ead732  Token/ERC20
0xa75cecd91f3af322609119e6f8f4eb879abee45d  Unknown/Helper
0xa941381f83fd4c5fd7f5451b7f517aaf16ee8c2a  Timelock/Gov
0xacfe71002347d635c05ee8d1cc1ab93b548ed0a6  Token/ERC20  [WILD]
0xad40f763ebecdae5ca3d178f94537e913182b6eb  Unknown/Helper
0xad997ca6497173c1831bd39200db13c410b0ff3c  Token/ERC20  [WILD]
0xae135a1b33c0d3682390762ea2be6c7419cf425a  WildCredit (LendingPair)
0xaec0e203eb8545a701171b7889903b0c3c1cd33d  Unknown/Helper
0xaf13071963441f3554bf0c8ab9911b860d4f02d7  Vault/Rebalancer  [X]
0xb0f466cc45dc73d0a6ea889c63390aeea7b6dcc5  Token/ERC20  [xWILD]
0xb3a4b3ceb32c8bf18ea9503154511398b20b154a  Vault/Rebalancer  [X]
0xb40462f839a2b5195c4aa02cfcc9afd24a71751e  WildCredit (PriceOracle)
0xb8406709dbea4adbc26f5965bd97ab753c68162c  WildCredit
0xbb6e5e47d95d05474a153ec767c8e5d0a13a3d62  Unknown/Helper
0xbc51c25f202308930fa7df67bc4b654106c95f37  Vault/Rebalancer
0xbee6be01514dc12f22275153aad1a6f61a256bc6  Unknown/Helper
0xc12ce0c877ce1c5c3314bfdf1d9e9dc4cdde0c70  Token/ERC20  [xWILD]
0xc150bd3356c59aad1c8e7989340658c9d23c14aa  Unknown/Helper
0xc2fa359da98c02686e9e2584a0f97159e95cfac0  Unknown/Helper
0xc4347dbda0078d18073584602cf0c1572541bb15  veToken/Staking  [veWILD] (proxy)
0xc452aec60ce901a7ef28ef2de5ebc41e65e00731  Token/ERC20  [xWILD]
0xc607bc54edd8642efe9eb3c6f0cee1b6e30763c8  WildCredit
0xc7631366e6785976a52cf4bdeacf1e5d90f7b476  Token/ERC20  [xWILD]
0xc891516bdda876b6b0b3991cc361c38c32a4cf9f  Unknown/Helper
0xc95718babe4c0c6f74fabed006866c1cfa2edd74  WildCredit (LendingPair)
0xcad102287ef073d68c029234ffb38d3ac2f74123  Unknown/Helper
0xccc75cd3d90c4ee3461aff7cfc29ac78784a0313  Unknown/Helper
0xd2e692b6b7bd845d45e14e6ddd14a6fecf647e26  Unknown/Helper
0xd30c920bf76f45fca585b29a62804bd369bdaae5  Unknown/Helper
0xd613af7d674a22a86a472eaedeaa3c02df46ec03  WildCredit
0xd6231f50b53250b10fdd7cae7a3e54002cc66d78  Unknown/Helper
0xd734723a6bf480254a3de30be6b22eb4fcf6b128  Unknown/Helper
0xd7f87400a9e36a27e1176a9e3f1c5f3ddd394df5  Vault/Rebalancer
0xd9cf5eb9adaceda91d8ebf793883f42edf9f9aea  WildCredit
0xdb8a9e26bf319d1bbd04a8e13b02652c0b14b400  Token/ERC20  [wBOND]
0xdfad05020c8c56862d7d08682a8ba6ca4db580b4  Token/ERC20  [xWILD]
0xdfb3d03e060a374a83c71c6bef51f7d93329f422  Token/ERC20
0xe0fada235382ff2e63c021f2974f6c51ab8ce368  WildCredit  [WILD-LP]
0xe2edb3789e405f4ac9c4f659d6f7fbbddcd112c8  WildCredit
0xe5862651a033cddcb8f3b4af9c063db2baec39d0  WildCredit (LendingPair)
0xe58fabc3a2aa7d181d9c28d0c2c9bdb245303d59  Unknown/Helper
0xe5b0974a457698b171e5541378dbec55e0e2ee62  WildCredit (LendingPair)
0xe609e880b60ebe510bef3bdbec834955f08bce34  WildCredit
0xe81f5fafbd5102be67864cc0e2e928ffb3ec323e  WildCredit
0xe863f40483c4c41cde74208222dffd03c5399361  WildCredit
0xea4bd92a0dec125a875d2a294d653be64145c747  Unknown/Helper
0xec738877f8a0deac03cd7c2176f1275ab18a7f9c  Unknown/Helper
0xec79d05808059cb1ea52d396cefff8ac54d8817d  Unknown/Helper
0xeefbcf72ed88a675988882ddd6e4a0e9209f9815  Unknown/Helper
0xef543229be38c10f4d705e51b1f95d5077bcbe73  WildCredit (LendingPair)
0xef5606010407c5835e7a9253448b256fa8d4d3de  Unknown/Helper
0xf24f35e5ed0338175ded0d972dafd0e6b56e6f2b  Unknown/Helper
0xf5d3684b34a4105a055092c41b526a3efee089df  Unknown/Helper
0xfa16e4d8378c579a2bd15308f98e5e338d82810e  Unknown/Helper
0xfd66fb512dbc2dfa49377cfe1168eafc4ea6aa5d  Timelock/Gov
0xfe4f052f80745c681b476a95b45f730b34b23707  Vault/Rebalancer
0xffd5d4b5a6df94f6b8d481f5f402a810713dd44e  Unknown/Helper
```

---

## 10. Verification & sources

- **Method:** enumerated all CREATEs by both EOAs (Blockscout `/transactions?filter=from`, full pagination → 306 contracts); fetched runtime bytecode for each (`eth_getCode`), extracted PUSH4 selector sets, grouped by ABI (194 distinct), resolved 648/750 selectors (4byte + openchain), mined 60 distinct event topic0s from live logs (Blockscout `/addresses/{a}/logs`), recomputed every quoted topic0 locally with keccak (pycryptodome) — all match; the 7 DB-undecoded topics were resolved via openchain and keccak-confirmed.
- **Sub-protocol identification:** by on-chain `symbol()` of the 70 token contracts (WILD/veWILD/xWILD/WILD-LP/wBOND/bCRED, BSG/BSGB/BSGS, UPDOWN, X, HYPE, BUILD, CPOOL, DPOOL) cross-referenced with each group's emitted events + selectors.
- **Wild Credit external confirmation:** Wild Credit is a real protocol (founder **0xdev0**; WILD `0x08a75dbc…625a`; veWILD ≈ veCRV/veFXS; first to accept Uniswap V3 positions as collateral; docs at `wild-credit.gitbook.io`). The Metric↔Wild↔UpDown↔Basis-fork grouping here is established **on-chain** via the shared deployer/owner EOAs.
- **Caveat:** all 306 are **unverified** (no published source). Argument layouts are reverse-engineered; confirm against the live contract before building precise decoders. Most contracts hold ~0 balance (low-TVL experiments).
- Paired with [`core.md`](core.md) (the METRIC token + Metric's 0x/KeeperDAO product surface) and [`README.md`](README.md) (index).
