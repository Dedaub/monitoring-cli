# Lista LISTA Token & veLISTA Governance — Topics, Selectors, Addresses (BNB Chain)

**Status:** verified against live RPC on BNB Chain (56) and the canonical `lista-dao/lista-token` repo on 2026-10-30.
**Scope:** the LISTA token, the retired veLISTA vote-escrow lock and its distributors, `ListaVault` (weekly LISTA emissions to per-pool distributors), `EmissionVoting`, the airdrop contract and the LP-staking plumbing. Topics and selectors are chain-agnostic. Addresses are network-specific.

**LISTA** is a plain, immutable ERC-20 on BNB Chain (3603 B, no proxy). `totalSupply()` = 1,000,000,000 LISTA (fixed). There is no mint function.

**veLISTA is retired under LIP-024.** On-chain `freePenaltyStartTime` = `0x69d4be30` = 2026-04-07 08:20 UTC. From then `lock`, `relockUnclaimed`, `increaseAmount` and `extendWeek` revert, and `earlyClaim` pays no penalty while the window is open. Governance moved to plain LISTA on Snapshot (off-chain). Revenue that went to veLISTA holders now funds LISTA buybacks. The veLISTA contracts stay readable and existing locks can still exit.

LISTA governance exists on **BNB Chain only**. The LISTA address returns `0x` on Ethereum, Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc. The `lista-token` repo has a LayerZero OFT v2 configuration for an Ethereum LISTA route (`scripts/foundry/oft/v2/OFTConfig.sol`), but neither the docs nor the repo publish a deployed Ethereum LISTA address. It is recorded here as **not found**.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 LISTA token

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

### 1.2 VeLista (retired lock)

| topic0 | Event |
|--------|-------|
| `0x2d689ede4be2a1bfc6f6d44b0a67326a70ae12c3d8b518827219654c2d45624c` | `LockCreated(address indexed account, uint256 amount, uint16 week, bool autoLock)` |
| `0xea61c3b66d1b521d412995113fb2d02e1f83da97103751ff25a4e0689f3e937e` | `LockAmountIncreased(address indexed account, uint256 amount)` |
| `0xa1b4a8b1f89db552deb25d3e9dd2cd3fc4dbb4937616c0a34819d63e663c7945` | `LockWeekExtended(address indexed account, uint16 week)` |
| `0xd8138f8a3f377c5259ca548e70e4c2de94f129f5a11036a15b69513cba2b426a` | `Claimed(address indexed account, uint256 amount)` — exit after term |
| `0x2f65626b865fc7e12d949d7de5ca5798f444dcae0edb082e59697aeedc2a8413` | `EarlyClaimed(address indexed account, uint256 amount, uint256 penalty)` — exit before term; `penalty` is 0 in the LIP-024 window |
| `0x2342a6b6f5171412bfdc7bb0b6490a228f521951cf3deee4313397daf84627ed` | `DisableAutoLock(address indexed account)` |
| `0x7e5b85f0febc27eb4e17c8c290d2937360015bfad3960de9d6ea7436ddce1f04` | `EnableAutoLock(address indexed account)` |
| `0x82e08ce611570015d86c2aa9279daf6cdad840f9fe1b2efd5cd2a2963e8eef71` | `PenaltyClaimed(address indexed account, uint256 amount)` |
| `0x445051e9b727e426602ab47f381789fffbe0c06d619d0ae4295a21d4290e53ef` | `FreePenaltyPeriodSet(uint256 start, uint256 end)` — admin; moves the LIP-024 window |
| `0x0c71e606018d4105dbcd41f23657831cd2bc2c87c60ee60f2fd8e3ce9970b175` | `EarlyClaimBlacklistUpdated(address account, bool isBlacklisted)` |

### 1.3 ListaVault (emissions) and distributors

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x2c00706df3fbb4a8ead830d4c0a7f278823843af15ad7e680c4f7db763dd779c` | `Deposit(address indexed account, uint16 indexed week, uint256 amount)` — weekly LISTA funding | ListaVault |
| `0xda1c4f2d69a45f565043251bb71522280543796bb865d00e12065191714d4707` | `IncreasedAllocation(address indexed distributor, uint256 increasedAmount)` | ListaVault |
| `0x9c278963f6956e398db88886d09da9df0878b9f801496617864af8247100e36f` | `NewDistributorRegistered(address distributor, uint256 id)` | ListaVault |
| `0x69b6d7b78570479eeee9d43408a5754ddbc6a3cb4046d3360b39c783fac98947` | `WeeklyDistributorPercentSet(uint16 indexed week, uint16[] ids, uint256[] percents)` | ListaVault |
| `0x8d43238b88f39ed11711051fa226e2c11ef3e2ca7441a406218d4c69d996dac7` | `DistributorBlacklistUpdated(uint16 indexed distributorId, bool blacklisted)` | ListaVault |
| `0x5fafa99d0643513820be26656b45130b01e1c03062e1266bf36f88cbd3bd9695` | `EmergencyWithdraw(address token, uint256 amount)` | ListaVault |
| `0x26372de6decc0ca1770f6d75300a8df13c11cf3a9b592071a221f546f201810d` | `LPTokenDeposited(address indexed lpToken, address indexed receiver, uint256 amount)` | distributors |
| `0x2d7689b3add04b23136b575399b9bb324f6705d949a2cf734850634803751dd3` | `LPTokenWithdrawn(address indexed lpToken, address indexed receiver, uint256 amount)` | distributors |
| `0x106f923f993c2149d49b4255ff723acafa1f2d94393f561d3eda32ae348f7241` | `RewardClaimed(address indexed receiver, uint256 listaAmount)` | distributors |

---

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa9059cbb` / `0x23b872dd` | `transfer(address,uint256)` / `transferFrom(address,address,uint256)` | LISTA. |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | LISTA (EIP-2612). |
| `0xe480aa84` | `lock(uint256,uint16,bool)` | VeLista. Reverts in the LIP-024 window. |
| `0x15456eba` | `increaseAmount(uint256)` | VeLista. Reverts in the window. |
| `0xb43bb2bb` | `extendWeek(uint16)` | VeLista. Reverts in the window. |
| `0x4e71d92d` | `claim()` | VeLista exit after term. |
| `0x06044632` | `earlyClaim()` | VeLista exit before term. |
| `0xe867b94e` / `0x375e2b47` | `disableAutoLock()` / `enableAutoLock()` | VeLista. |
| `0x1c87fb17` | `setFreePenaltyPeriod(uint256,uint256)` | VeLista admin. |
| `0x995eac13` | `setEarlyClaimBlacklist(address,bool)` | VeLista admin. |
| `0xc0258ac0` / `0x7d6561ba` | `freePenaltyStartTime()` / `freePenaltyEndTime()` | VeLista views. |
| `0x50cc6cd6` | `depositRewards(uint256,uint16)` | ListaVault. Emits `Deposit`. |
| `0x31ab0518` | `registerDistributor(address)` | ListaVault admin. |
| `0x5d73e66e` | `setWeeklyDistributorPercent(uint16,uint16[],uint256[])` | ListaVault. |
| `0xd894f99c` | `batchClaimRewards(address[])` | ListaVault. |
| `0x3a43eed3` / `0xc04dda0c` | `distributorId()` / `idToDistributor(uint16)` | ListaVault views. Enumerate distributors `1..distributorId()`. |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)

All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **LISTA** | `0xFceB31A79F71AC9CBDCF853519c1b12D379EdC46` | Governance token. Immutable. Supply 1e9. |
| VeLista (retired) | `0xd0C380D31DB43CD291E2bbE2Da2fD6dc877b87b3` | Vote-escrow lock. OZ v5 TP, impl `0x765d17e43be4fa44b1cf75a01dc10ab95470274e`. |
| VeListaDistributor (retired) | `0x45aAc046Bc656991c52cf25E783c6942425ce40C` | veLISTA reward distributor. OZ v5 TP. |
| VeListaRevenueDistributor (retired) | `0xE4153Eb04417bE05b8d6B2222E4Cdd8AE674ee76` | Revenue split. ERC-1967 (170 B). |
| VeListaInterestRebater (retired) | `0xda1E93d58CCCC9683f9Cb051cAEC5CF2F01B3253` | ERC-1967 (170 B). |
| EmissionVoting (retired) | `0xfc136f286805a7922d9bf04317068964b231336c` | Gauge voting. OZ v5 TP. |
| **ListaVault** | `0x307d13267f360f78005f476Fa913F8848F30292A` | Weekly LISTA emissions. OZ v5 TP. `distributorId()` = 68 on 2026-10-30. |
| OracleCenter | `0x946a68b29149f819FBcE866cED3632e0C9F7C53b` | Price source for emissions. OZ v5 TP. |
| BorrowLisUSDListaDistributor | `0x0AED860cA496600F6976219Cb1acEc435d7F4f3B` | CDP borrower emissions. OZ v5 TP. |
| StakeLisUSDListaDistributor | `0xFeB28443692216f66D14C7be4a449a765E2BDbAc` | lisUSD staker emissions. OZ v5 TP. |
| LpProxy | `0x5A0E3291514F5F1797A0C7eFefdac81eeC70ec01` | LP staking router. OZ v5 TP. |
| Lista Airdrop (closed) | `0x2ed866Ca9C33bf695C78af222d61Bd4D9cB558d3` | Merkle airdrop. Immutable (2795 B). |

Staking vaults (all OZ v5 Transparent proxies, 1159 B): PancakeStaking `0xE31f0BcE1F825A8e27f2Cc30B54af19DA2978f10`, ThenaStaking `0xFA5B482882F9e025facCcE558c2F72c6c50AC719`, PancakeVault `0x62DfeC5C9518fE2e0ba483833d1BAD94ecF68153`, ThenaVault `0xF40D0d497966fe198765877484FFf08c2D2004ad`.

## 4. Cross-chain summary

| Chain (ID) | LISTA | VeLista | ListaVault |
|------------|-------|---------|------------|
| BNB (56) | `0xFceB31…EdC46` | `0xd0C380…87b3` | `0x307d13…292A` |
| Ethereum (1) | not found (OFT v2 route configured in repo, no published address) | — | — |
| Base · Avalanche · Arbitrum · Optimism · Polygon · Robinhood · Arc | — | — | — |

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| LISTA, Lista Airdrop | immutable | impl slot `0x0` | — |
| VeLista, VeListaDistributor, ListaVault, OracleCenter, EmissionVoting, distributors, LpProxy | OZ v5 TransparentUpgradeableProxy | 1159 B; one ProxyAdmin per proxy | ProxyAdmin owner. VeLista and ListaVault ProxyAdmins are owned by TimelockController `0x07d274…5253`. |
| VeListaRevenueDistributor, VeListaInterestRebater | ERC-1967 (UUPS) | 170 B | `DEFAULT_ADMIN_ROLE` |

## 6. Detection invariants & gotchas

1. **veLISTA is wind-down only.** After 2026-04-07 08:20 UTC, expect only `Claimed`, `EarlyClaimed` (penalty 0), `DisableAutoLock` and `EnableAutoLock`. A new `LockCreated` or a `FreePenaltyPeriodSet` is an anomaly worth an alert.
2. **`earlyClaim` vs blacklist.** `earlyClaim` checks `earlyClaimBlacklist` first. A blacklisted auto-locked account must `disableAutoLock` and wait up to 52 weeks to `claim`.
3. **ListaVault `Deposit` is not ERC-4626.** `Deposit(address,uint16,uint256)` has its own topic0 `0x2c00706d…`.
4. **Distributor registry is on-chain.** Use `idToDistributor(i)` for `i` in `1..distributorId()`. A registered distributor is not necessarily funded; read `getDistributorWeeklyEmissions(id, week)`.
5. **Address reuse.** VeListaRevenueDistributor's implementation on BNB (`0xf820fB…Fd70`) is the Moolah proxy address on Ethereum. Key on `(chainId, address)`.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_ERC20_TRANSFER              = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_VELISTA_LOCK_CREATED        = '\x2d689ede4be2a1bfc6f6d44b0a67326a70ae12c3d8b518827219654c2d45624c'
TOPIC_VELISTA_CLAIMED             = '\xd8138f8a3f377c5259ca548e70e4c2de94f129f5a11036a15b69513cba2b426a'
TOPIC_VELISTA_EARLY_CLAIMED       = '\x2f65626b865fc7e12d949d7de5ca5798f444dcae0edb082e59697aeedc2a8413'
TOPIC_VELISTA_FREE_PENALTY_SET    = '\x445051e9b727e426602ab47f381789fffbe0c06d619d0ae4295a21d4290e53ef'
TOPIC_LISTAVAULT_DEPOSIT          = '\x2c00706df3fbb4a8ead830d4c0a7f278823843af15ad7e680c4f7db763dd779c'
TOPIC_LISTAVAULT_NEW_DISTRIBUTOR  = '\x9c278963f6956e398db88886d09da9df0878b9f801496617864af8247100e36f'
TOPIC_DISTRIBUTOR_REWARD_CLAIMED  = '\x106f923f993c2149d49b4255ff723acafa1f2d94393f561d3eda32ae348f7241'
-- ===== Selectors (chain-agnostic) =====
SEL_VELISTA_CLAIM                 = '\x4e71d92d'
SEL_VELISTA_EARLY_CLAIM           = '\x06044632'
SEL_VELISTA_LOCK                  = '\xe480aa84'
SEL_LISTAVAULT_DEPOSIT_REWARDS    = '\x50cc6cd6'
-- ===== Addresses (network-specific) =====
BSC_LISTA                         = '\xfceb31a79f71ac9cbdcf853519c1b12d379edc46'
BSC_VELISTA                       = '\xd0c380d31db43cd291e2bbe2da2fd6dc877b87b3'
BSC_VELISTA_DISTRIBUTOR           = '\x45aac046bc656991c52cf25e783c6942425ce40c'
BSC_LISTA_VAULT                   = '\x307d13267f360f78005f476fa913f8848f30292a'
BSC_EMISSION_VOTING               = '\xfc136f286805a7922d9bf04317068964b231336c'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `lista-token/contracts` (`ListaToken.sol`, `VeLista.sol`, `interfaces/IVeLista.sol`, `dao/ListaVault.sol`, `dao/CommonListaDistributor.sol`). Every listed VeLista and ListaVault topic was found as a constant in the live implementation bytecode.
- **Addresses:** parsed from the docs page "Lista Governance — Smart Contract", then existence-checked with `eth_getCode`. Proxy slots, `totalSupply()`, `symbol()`, `distributorId()`, `freePenaltyStartTime()` and `freePenaltyEndTime()` were read live.
- **Chain coverage:** the LISTA address returns `0x` on the eight other target chains. No Ethereum LISTA deployment is published in the docs or the repo.

Authoritative sources:
- [lista-dao/lista-token](https://github.com/lista-dao/lista-token) — source of truth for signatures.
- [Lista docs — Lista Governance smart contracts](https://docs.bsc.lista.org/for-developer/lista-governance/smart-contract)
- Explorer: [BscScan LISTA](https://bscscan.com/token/0xFceB31A79F71AC9CBDCF853519c1b12D379EdC46)
