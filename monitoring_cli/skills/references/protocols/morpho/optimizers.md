# Morpho Optimizers (legacy, deprecated) — Topics, Selectors, Addresses (Ethereum only)

**Status:** verified against live Ethereum RPC on 2026-05-29 and the `morpho-org/morpho-optimizers` (Compound + Aave-V2) and `morpho-org/morpho-aave-v3` (Aave-V3 ETH Optimizer) repos. **Deprecated** — wind-down governed by [MIP-120](https://forum.morpho.org/t/mip-120-compound-v2-and-aave-v2-optimizers-deprecation-final-phase/2038) (Compound V2 + Aave V2 final-phase deprecation). The successor is Morpho Blue ([v1.md](v1.md)); index in [README.md](README.md).
**Scope:** the **first generation** of Morpho — a peer-to-peer matching *overlay* on top of Aave V2, Aave V3, and Compound V2. Deposits/borrows are matched P2P at an improved rate when possible, otherwise fall back to the underlying pool. **Ethereum mainnet only** (these were never multi-chain). Three independent instances. Kept here for historical position/event detection; do not build new integrations against them.

Unlike Morpho Blue, the Optimizers are **upgradeable** — each is a `TransparentUpgradeableProxy` (EIP-1967) behind a shared `ProxyAdmin`. Read the impl slot, don't assume the logic address.

---

## 1. Addresses — Ethereum mainnet (chain ID 1)

| Role | Address | Code | One-liner |
|------|---------|------|-----------|
| **Morpho-AaveV3 (ETH Optimizer)** proxy | `0x33333aea097c193e66081E930c33020272b33333` | 1901 B | P2P overlay on Aave V3 (ETH-correlated market). Vanity `0x33333…33333`. |
| Morpho-AaveV3 implementation | `0xf835456cb1de3e39ab50a8a9fbb07ebec3a8ff67` | — | Logic behind the `0x33333…` proxy (read from EIP-1967 slot). |
| **Morpho-Compound** proxy | `0x8888882f8f843896699869179fB6E4f7e3B58888` | 2091 B | P2P overlay on Compound V2. Vanity `0x8888…8888`. Deprecated (MIP-120). |
| Morpho-Compound implementation | `0xe3d7a242614174ccf9f96bd479c42795d666fc81` | — | Logic behind `0x8888…`. |
| Morpho-Compound Lens | `0x930f1b46e1D081Ec1524efD95752bE3eCe51EF67` | 2091 B | Read-only position/rate views (also a proxy). |
| **Morpho-AaveV2** proxy | `0x777777c9898D384F785Ee44Acfe945efDFf5f3E0` | 2091 B | P2P overlay on Aave V2. Vanity `0x7777…`. Deprecated (MIP-120). |
| Morpho-AaveV2 implementation | `0xfbc7693f114273739c74a3ff028c13769c49f2d0` | — | Logic behind `0x7777…`. |
| Morpho-AaveV2 Lens | `0x507fA343d0A90786d86C7cd885f5C49263A91FF4` | 2091 B | Read-only views (proxy). |
| **Optimizer ProxyAdmin** | `0x99917ca0426fbc677e84f873fb0b726bb4799cd8` | 1827 B | Admin of all three optimizer proxies (+ Lenses). |
| RewardsDistributor (MORPHO) | `0x3B14E5C73e0A56D607A8688098326fD4b4292135` | 2219 B | Merkle distributor for optimizer MORPHO rewards. |

The Aave-V3 optimizer (`0x33333…`) is the only one with meaningful residual life; Compound (`0x8888…`) and Aave-V2 (`0x7777…`) are fully deprecated. All three are Ethereum-only.

---

## 2. Topics (chain-agnostic by signature; emitted on Ethereum only)

### 2.1 Compound + Aave-V2 Optimizers (shared signatures — `poolToken`-indexed scheme)

| topic0 | Event |
|--------|-------|
| `0x11adb3570ba55fd255b1f04252ca0071ae6639c86d4fd69e7c1bf1688afb493f` | `Supplied(address indexed supplier, address indexed onBehalf, address indexed poolToken, uint256 amount, uint256 balanceOnPool, uint256 balanceInP2P)` |
| `0xc1cba78646fef030830d099fc25cb498953709c9d47d883848f81fd207174c9f` | `Borrowed(address indexed borrower, address indexed poolToken, uint256 amount, uint256 balanceOnPool, uint256 balanceInP2P)` |
| `0x378f9d375cd79e36c19c26a9e57791fe7cd5953b61986c01ebf980c0efb92801` | `Withdrawn(address indexed supplier, address indexed receiver, address indexed poolToken, uint256 amount, uint256 balanceOnPool, uint256 balanceInP2P)` |
| `0x7b417e520d2b905fc5a1689d29d329358dd55efc60ed115aa165b0a2b64232c6` | `Repaid(address indexed repayer, address indexed onBehalf, address indexed poolToken, uint256 amount, uint256 balanceOnPool, uint256 balanceInP2P)` |
| `0xc2c75a73164c2efcbb9f74bfa511cd0866489d90687831a7217b3dbeeb697088` | `Liquidated(address liquidator, address indexed liquidated, address indexed poolTokenBorrowed, uint256 amountRepaid, address indexed poolTokenCollateral, uint256 amountSeized)` |
| `0x1cf8705a784a46d32023f3694b5e8149137d563085a870fde2f54a6cc5c59df7` | `P2PSupplyDeltaUpdated(address indexed poolToken, uint256 p2pSupplyDelta)` |
| `0x8113f59ef078158acce9021327489b70d6ab15d0c107c36455c3505248648df6` | `P2PBorrowDeltaUpdated(address indexed poolToken, uint256 p2pBorrowDelta)` |
| `0xaa997145358327b99ccedf396e9b7719eb7999623af1a7b38605739996c2ccfa` | `P2PAmountsUpdated(address indexed poolToken, uint256 p2pSupplyAmount, uint256 p2pBorrowAmount)` *(Compound)* |
| `0x919308a0c65e4238b9e7c930b218a0ba8c75d0bce06fc2ffb36e95e1fa12a8f1` | `P2PDeltasIncreased(address indexed poolToken, uint256 amount)` |

> These two optimizers index by **`poolToken`** (the cToken / aToken), not the underlying. To get the underlying, map the poolToken. `Borrowed`/`Withdrawn` here have a **different arity** than the Aave-V3 optimizer below (`Borrowed` is 5-field, no `receiver`).

### 2.2 Aave-V3 ETH Optimizer (`0x33333…`) — `underlying`-indexed, scaled-balance scheme

| topic0 | Event |
|--------|-------|
| `0x11adb3570ba55fd255b1f04252ca0071ae6639c86d4fd69e7c1bf1688afb493f` | `Supplied(address indexed from, address indexed onBehalf, address indexed underlying, uint256 amount, uint256 scaledOnPool, uint256 scaledInP2P)` *(same topic0 as §2.1 Supplied)* |
| `0x4d1fc6dc36972a1eeab2351fae829d06c827d7ee429880dbf762ec00b805fb2f` | `CollateralSupplied(address indexed from, address indexed onBehalf, address indexed underlying, uint256 amount, uint256 scaledBalance)` |
| `0xf99275e3db7a3400181f0bd088002bba02b833be9187bccc88fbbc79fb52f2f1` | `Borrowed(address caller, address indexed onBehalf, address indexed receiver, address indexed underlying, uint256 amount, uint256 scaledOnPool, uint256 scaledInP2P)` |
| `0x7b417e520d2b905fc5a1689d29d329358dd55efc60ed115aa165b0a2b64232c6` | `Repaid(address indexed repayer, address indexed onBehalf, address indexed underlying, uint256 amount, uint256 scaledOnPool, uint256 scaledInP2P)` *(same topic0 as §2.1 Repaid)* |
| `0x6a9c828ef646db99cc7a20bbfb02fdf8f7dcc183400a28daab4968e47b9a21e0` | `Withdrawn(address caller, address indexed onBehalf, address indexed receiver, address indexed underlying, uint256 amount, uint256 scaledOnPool, uint256 scaledInP2P)` |
| `0xb49f4cffa4b6674963440a1fb6cb419c233a9341280f44d8543571eca1306577` | `CollateralWithdrawn(address caller, address indexed onBehalf, address indexed receiver, address indexed underlying, uint256 amount, uint256 scaledBalance)` |
| `0xc2c75a73164c2efcbb9f74bfa511cd0866489d90687831a7217b3dbeeb697088` | `Liquidated(address indexed liquidator, address indexed borrower, address indexed underlyingBorrowed, uint256 amountLiquidated, address underlyingCollateral, uint256 amountSeized)` *(same topic0 as §2.1 Liquidated)* |
| `0xb7f1c1a7c27b63c53c9c4700bfc54d905ec2ef2b451c24e6426a7cc86fed7ed7` | `IndexesUpdated(address indexed underlying, uint256 poolSupplyIndex, uint256 p2pSupplyIndex, uint256 poolBorrowIndex, uint256 p2pBorrowIndex)` |
| `0xe41625c4c3305c982f69719ce2edfc7f372d126b5bfdd5029cea4619cb5a1023` | `ManagerApproval(address indexed delegator, address indexed manager, bool isAllowed)` |
| `0x1cf8705a784a46d32023f3694b5e8149137d563085a870fde2f54a6cc5c59df7` | `P2PSupplyDeltaUpdated(address indexed underlying, uint256 scaledDelta)` *(same topic0 as §2.1)* |
| `0x8113f59ef078158acce9021327489b70d6ab15d0c107c36455c3505248648df6` | `P2PBorrowDeltaUpdated(address indexed underlying, uint256 scaledDelta)` *(same topic0 as §2.1)* |
| `0x29c7258ad2a828aee0fb295826bf2a731d38a5ae377f284addeb97838d657c2d` | `P2PTotalsUpdated(address indexed underlying, uint256 scaledTotalSupplyP2P, uint256 scaledTotalBorrowP2P)` |
| `0xb27af04ab132a0b6bba5de2a84bbbadcc31c20c33932936a992ae6ff951259c3` | `MarketCreated(address indexed underlying)` |
| `0xd37f8c5b1028a8745d109e601653cbf41563b7e941e8affa1a9c4a7a38abd971` | `IdleSupplyUpdated(address indexed underlying, uint256 idleSupply)` |

> **`Supplied`/`Repaid`/`Liquidated` topic0 are shared across all three optimizers** (identical signatures). Disambiguate by the emitting optimizer address (`0x33333…` / `0x8888…` / `0x7777…`). The Aave-V3 optimizer adds `CollateralSupplied`/`CollateralWithdrawn` (Aave V3 separates collateral from supply) and reports **scaled** balances.

---

## 3. Function signatures — Aave-V3 ETH Optimizer (`0x33333…`)

Selectors = `keccak256(sig)[0:4]`. The Optimizer ABI is **completely different from Morpho Blue** — it is underlying-asset + maxIterations based, not market-id based.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe9c7359c` | `supply(address underlying, uint256 amount, address onBehalf, uint256 maxIterations)` | `(uint256 supplied)`. P2P-match up to `maxIterations`, rest to Aave. |
| `0xd910fa66` | `supplyCollateral(address underlying, uint256 amount, address onBehalf)` | Collateral only (no P2P). |
| `0x99920806` | `borrow(address underlying, uint256 amount, address onBehalf, address receiver, uint256 maxIterations)` | `(uint256 borrowed)`. |
| `0x5ceae9c4` | `repay(address underlying, uint256 amount, address onBehalf)` | `(uint256 repaid)`. |
| `0x5501f1c6` | `withdraw(address underlying, uint256 amount, address onBehalf, address receiver, uint256 maxIterations)` | `(uint256)`. |
| `0x2bbccf01` | `withdrawCollateral(address underlying, uint256 amount, address onBehalf, address receiver)` | `(uint256)`. |
| `0xaab3f868` | `liquidate(address underlyingBorrowed, address underlyingCollateral, address user, uint256 amount)` | `(uint256 repaid, uint256 seized)`. |
| `0x9ab2d0c7` | `approveManager(address manager, bool isAllowed)` | Delegation (emits `ManagerApproval`). |
| `0x0e42c363` | `setAssetIsCollateral(address underlying, bool isCollateral)` | |
| `0x77d5d857` | `claimRewards(address[] assets, address onBehalf)` | Aave incentives passthrough. |

> The Compound/Aave-V2 optimizers use a different (older) ABI keyed by `poolToken` (cToken/aToken) rather than the underlying. For deprecated-product monitoring, prefer detection by **event topics** (§2), which are validated and stable.

---

## 4. Proxies

| Contract | Pattern | Admin |
|----------|---------|-------|
| Morpho-AaveV3 `0x33333…` | TransparentUpgradeableProxy (EIP-1967) → impl `0xf835456cb1de3e39ab50a8a9fbb07ebec3a8ff67` | ProxyAdmin `0x99917ca0…9cd8` |
| Morpho-Compound `0x8888…` | TransparentUpgradeableProxy → impl `0xe3d7a242614174ccf9f96bd479c42795d666fc81` | ProxyAdmin `0x99917ca0…9cd8` |
| Morpho-AaveV2 `0x7777…` | TransparentUpgradeableProxy → impl `0xfbc7693f114273739c74a3ff028c13769c49f2d0` | ProxyAdmin `0x99917ca0…9cd8` |

EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. **This is the opposite of Morpho Blue** (immutable). All three proxies + both Lenses share the one ProxyAdmin `0x99917ca0426fbc677e84f873fb0b726bb4799cd8`.

---

## 5. Detection invariants & gotchas

1. **Ethereum only.** Optimizers were never deployed multi-chain. If you see "Morpho" activity on Base/Arb/etc., it is Morpho Blue ([v1.md](v1.md)), not an Optimizer.
2. **Shared `Supplied`/`Repaid`/`Liquidated` topic0** across all three optimizers — key on `(chainId=1, optimizer address)`.
3. **Aave-V3 optimizer indexes `underlying`; Compound/Aave-V2 index `poolToken`** (cToken/aToken). Different join keys.
4. **Scaled vs raw balances.** Aave-V3 optimizer emits **scaled** on-pool/in-P2P balances (reconstruct with the pool index); the older two emit a mix — read the field names.
5. **Upgradeable.** Read the EIP-1967 impl slot; do not hardcode the logic address.
6. **Deprecated — expect ~zero new activity.** Live-log scans near the chain head return nothing; activity clustered 2022–2024. (Validated: Aave-V3-opt `Supplied` 5 logs at block 18.00M; none in recent windows.)
7. **MORPHO rewards** for optimizer users came via the RewardsDistributor `0x3B14E5C7…` (Merkle), not the URD used by Morpho Blue.

---

## 6. Quick-copy constants (bytea-ready for PG)

```
-- Optimizer event topics (Ethereum only)
TOPIC_OPT_SUPPLIED            = '\x11adb3570ba55fd255b1f04252ca0071ae6639c86d4fd69e7c1bf1688afb493f'  -- all 3 optimizers
TOPIC_OPT_REPAID             = '\x7b417e520d2b905fc5a1689d29d329358dd55efc60ed115aa165b0a2b64232c6'  -- all 3
TOPIC_OPT_LIQUIDATED         = '\xc2c75a73164c2efcbb9f74bfa511cd0866489d90687831a7217b3dbeeb697088'  -- all 3
TOPIC_OPT_BORROWED_CADV2     = '\xc1cba78646fef030830d099fc25cb498953709c9d47d883848f81fd207174c9f'  -- Compound + AaveV2
TOPIC_OPT_WITHDRAWN_CADV2    = '\x378f9d375cd79e36c19c26a9e57791fe7cd5953b61986c01ebf980c0efb92801'  -- Compound + AaveV2
TOPIC_OPT_BORROWED_AV3       = '\xf99275e3db7a3400181f0bd088002bba02b833be9187bccc88fbbc79fb52f2f1'  -- AaveV3-opt
TOPIC_OPT_WITHDRAWN_AV3      = '\x6a9c828ef646db99cc7a20bbfb02fdf8f7dcc183400a28daab4968e47b9a21e0'  -- AaveV3-opt
TOPIC_OPT_COLLATSUPPLIED_AV3 = '\x4d1fc6dc36972a1eeab2351fae829d06c827d7ee429880dbf762ec00b805fb2f'
TOPIC_OPT_COLLATWITHDRAWN_AV3= '\xb49f4cffa4b6674963440a1fb6cb419c233a9341280f44d8543571eca1306577'
TOPIC_OPT_INDEXESUPDATED_AV3 = '\xb7f1c1a7c27b63c53c9c4700bfc54d905ec2ef2b451c24e6426a7cc86fed7ed7'

-- Optimizer addresses (Ethereum, chain 1)
OPT_AAVEV3   = '\x33333aea097c193e66081e930c33020272b33333'
OPT_AAVEV3_IMPL = '\xf835456cb1de3e39ab50a8a9fbb07ebec3a8ff67'
OPT_COMPOUND = '\x8888882f8f843896699869179fb6e4f7e3b58888'
OPT_AAVEV2   = '\x777777c9898d384f785ee44acfe945efdff5f3e0'
OPT_PROXY_ADMIN = '\x99917ca0426fbc677e84f873fb0b726bb4799cd8'
OPT_REWARDS_DISTRIBUTOR = '\x3b14e5c73e0a56d607a8688098326fd4b4292135'
```

---

## 7. Verification & sources

- Event topics computed locally (`keccak256(sig)`) from `morpho-org/morpho-optimizers` (`compound/PositionsManager.sol`, `aave-v2/Entry/ExitPositionsManager.sol`) and `morpho-org/morpho-aave-v3` (`src/libraries/Events.sol`); `Supplied` topic validated against live Aave-V3-optimizer logs (5 hits at block 18,000,000–18,040,000).
- Proxy impls read live from EIP-1967 slot on 2026-05-29; all three share ProxyAdmin `0x99917ca0…9cd8`. Addresses existence-checked via `eth_getCode`.
- [`morpho-org/morpho-optimizers`](https://github.com/morpho-org/morpho-optimizers) · [`morpho-org/morpho-aave-v3`](https://github.com/morpho-org/morpho-aave-v3) · [MIP-120 deprecation](https://forum.morpho.org/t/mip-120-compound-v2-and-aave-v2-optimizers-deprecation-final-phase/2038) · [optimizers.morpho.org](https://optimizers.morpho.org/).
