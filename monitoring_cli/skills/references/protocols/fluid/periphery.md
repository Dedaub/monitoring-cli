# Fluid — Periphery: FLUID token, Staking, Merkle Distributors, Resolvers — Topics, Selectors, Addresses

**Status:** addresses from `Instadapp/fluid-contracts-public` `deployments/deployments.md` (`main`, fetched 2026-06-05) + on-chain `eth_getCode`/`symbol()` confirmation; event topic0/selectors computed locally via keccak.
**Scope:** everything around the four core Fluid modules — the **FLUID** governance token (per chain), the **reward mechanisms** (3 distinct families — do not conflate), and the **resolver** read-helpers. Core modules: [`liquidity-layer.md`](liquidity-layer.md), [`lending.md`](lending.md), [`vaults.md`](vaults.md), [`dex.md`](dex.md). Index: [`README.md`](README.md).
**Key fact:** Fluid has **three** separate reward systems: (1) `LendingRewardsRateModel` — feeds an fToken's supply APY, **no claim event** (yield accrues into exchange price); (2) `StakingRewards` — Synthetix-style, users *stake fTokens* to earn FLUID, emits `Staked`/`Withdrawn`/`RewardPaid`; (3) `MerkleDistributor` — off-chain-computed campaign claims, emits `LogClaimed`. Best monitoring targets: **`LogClaimed`, `RewardPaid`, `Staked`/`Withdrawn`**, and `LogRootProposed`/`LogRootUpdated` for distributor-root governance.

---

## 1. FLUID governance token (per chain — verified `symbol()`/`name()` 2026-06-05)

| Chain | Address | symbol/name | Notes |
|-------|---------|-------------|-------|
| Ethereum (1) | `0x6f40d4A6237C257fff2dB00FA0510DeEECd303eb` | FLUID / Fluid | **Canonical / native.** |
| Arbitrum (42161) | `0x61e030a56d33e8260fdd81f03b162a79fe3449cd` | FLUID / Fluid | Bridged (LayerZero OFT). |
| Base (8453) | `0x61e030a56d33e8260fdd81f03b162a79fe3449cd` | FLUID / Fluid | Bridged — **same address as Arb/BNB.** |
| BNB (56) | `0x61e030a56d33e8260fdd81f03b162a79fe3449cd` | FLUID / Fluid | Bridged — same address. |
| Polygon (137) | — | — | **No FLUID token** (neither `0x6f40d4…` nor `0x61e030…` has code). Polygon "FLUID rewards" were historically paid in **$POL** via a dedicated MerkleDistributor. |

> The bridged FLUID OFT lives at the **single shared address `0x61e030a56d33e8260fdd81f03b162a79fe3449cd` on Arb, Base, and BNB**. ETH mainnet uses the distinct native `0x6f40d4…`. The legacy mainnet INST-on-Polygon bridge (`0xf50d05a1…`, `symbol()`="INST") is **NOT** FLUID. (`0x6f40d4…` also returns code on BNB but is not an ERC-20 there — disregard.)

**FLUID buyback:** `FluidBuybackProxy` ETH `0x9Afb8C1798B93a8E04a18553eE65bAFa41a012F1` (impl `0xC27293043EF9B6c911AEf47e4A563baE8a91654f`).

---

## 2. Reward mechanism A — LendingRewardsRateModel (rate, not claimable)
Drives an fToken's supply-side reward **rate** (accrues into the fToken→underlying exchange price; **no per-user claim event**). Full events/selectors documented in [`lending.md`](lending.md) §1.3/§2.4 (`LogStartRewards`/`LogStopRewards`/…, `getRate`/`getConfig`). The per-fToken model addresses are the `*_Rewards` deployments (e.g. ETH fUSDC_fUSDT `0x724d0c9497Fa89B2C6A4585e08380c91a92ab9b6`, ARB `0x65913Cf72695bA29f51fD23D9FCa208e1cB94974`, Base fUSDC `0xe6c7AfB08108c3257048b346718DEA1F3dF3E86C`, Base fEURC `0x8c762C38351D9b2E206D30B8f5c285dcC200EF6D`, BNB fUSDC `0x149747813e1A5b04B5F17869b9d6603022B591fd`, BNB fUSDT `0xBE02b3DA446BF1B5CB271553F162A0f7C92E90bD`, BNB fU `0xbaFe938aEE7b0E1efe7D488905710F3C99eCb36A`). See [`lending.md`](lending.md) for the per-fToken table.

---

## 3. Reward mechanism B — StakingRewards (Synthetix-style; stake fTokens → earn FLUID)
Source: `contracts/protocols/lending/stakingRewards/main.sol`. Users stake an fToken to earn a reward token. **No `Recovered`/`recoverERC20`** (unlike vanilla Synthetix — don't add a Recovered alert; it won't fire).

### 3.1 Topics
| topic0 | Event |
|--------|-------|
| `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | `RewardAdded(uint256 reward)` |
| `0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d` | `Staked(address indexed user, uint256 amount)` |
| `0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5` | `Withdrawn(address indexed user, uint256 amount)` |
| `0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486` | `RewardPaid(address indexed user, uint256 reward)` |
| `0x1f6864585aff6172b9e61fd517190576e478963013921dff17824a9b8ff101d8` | `NextRewardQueued(uint256 reward, uint256 periodFinish)` |

### 3.2 Selectors
`stake(uint256) 0xa694fc3a` · `withdraw(uint256) 0x2e1a7d4d` · `getReward() 0x3d18b912` · `exit() 0xe9fad8ee` · `notifyRewardAmount(uint256) 0x3c6b16ab` (onlyOwner) · `stakeWithPermit(...)` · `notifyRewardAmountWithDuration(...)`.

### 3.3 Addresses (per fToken, per chain)
| Instance | Address |
|----------|---------|
| ETH fUSDC StakingRewards | `0x2fA6c95B69c10f9F52b8990b6C03171F13C46225` |
| ETH fUSDT StakingRewards | `0x490681095ed277B45377d28cA15Ac41d64583048` |
| ARB fUSDC StakingRewards | `0x48f89d731C5e3b5BeE8235162FC2C639Ba62DB7d` |
| ARB fUSDT StakingRewards | `0x65241f6cacde58c03400Cb84542a2c197d6dE9C3` |

(Enumerate the full set via `StakingRewardsResolver` — §5.)

---

## 4. Reward mechanism C — MerkleDistributor (campaign claims)
Source: `contracts/protocols/lending/merkleDistributor/{main,events}.sol`. Off-chain-computed Merkle roots, claimed on-chain in cycles. **`LogClaimed` is the per-user claim event.**

### 4.1 Topics
| topic0 | Event |
|--------|-------|
| `0x309cb1c0dc6ce0f02c0c35cc1f46bbe61ec9deb311d101b87e7d25bd0b647fd7` | `LogClaimed(address user, uint256 amount, uint256 cycle, uint8 positionType, bytes32 positionId, uint256 timestamp, uint256 blockNumber)` |
| `0xb38026cc978f6c2642a5108ee558571a1b01a939b056abcc065b7eabacaf2d9d` | `LogRootProposed(uint256 cycle, bytes32 root, bytes32 contentHash, uint256 timestamp, uint256 blockNumber)` |
| `0xcc3c3071340d91a4fd687f9ad48d1ee5689f8083136feb3594807d0f7481f7cf` | `LogRootUpdated(uint256 cycle, bytes32 root, bytes32 contentHash, uint256 timestamp, uint256 blockNumber)` |
| `0x9d1578529527d7ca977e6e95da5e7302299dfa7894fea3a1992ce68741ff5a0a` | `LogRewardCycle(uint256,uint256,uint256,uint256,uint256)` |
| `0xd3aec04e72c75d4a42792ce6fe015d1ec10b07a8a621c9df2a89bd3644cf7ca8` | `LogDistribution(uint256,address,uint256,uint256,uint256,uint256,uint256)` |

Other admin events (non-indexed toggles, not hashed here): `LogUpdateProposer`, `LogUpdateApprover`, `LogDistributionConfigUpdated`, `LogRewardsDistributorToggled`, `LogStartBlockOfNextCycleUpdated`. Key funcs: `claim(...)`, `claimOnBehalfOf(...)`, `proposeRoot(...)`, `approveRoot(...)`.

### 4.2 Addresses — sprawling (one canonical-per-chain + ~15 per-campaign one-offs)
**Canonical 2026 (GHO rewards):** ETH `0xF398E66B1273a34558AeBbEC550DccaF4AcC7714`, ARB `0xfA1bD6fb7014D1AF41D9aE7Fa4844B2944811215`, Base `0x77B2eD3653f10AB269396FaE6CF7Cb196B2D486a`.

Notable per-campaign instances (reward token in parens; `deployments.md` §MerkleDistributors lines ~7220–7317):
| Address | Chain(s) | Campaign |
|---------|----------|----------|
| `0x9d694b7f2AB2C1f328Ca3E334AB74aFC2814240E` (ETH), `0x6ebFeb4372e64d6C63A292a14ce6c9F2bB427203` (ARB/Base) | ETH/ARB/Base | delegateCall claimOnBehalfOf (FLUID) |
| `0x7060FE0Dd3E31be01EFAc6B28C8D38018fD163B0` | ETH | Fluid Rewards Dec 2024 (FLUID) |
| `0xbAbB3f87424d900aBd83C807C1E01a22a54E726F` | ETH | cbBTC-wBTC (FLUID) |
| `0xD833484b198D3d05707832cc1C2D62b520D95B8A` | ETH | GHO Vaults Apr 2025 (FLUID) |
| `0xB48BbE313eDB7fAAa28C03684D48F58dD7dEA239` | ETH | deUSD-USDC (FLUID) |
| `0xF90D6eA5d0B4CAD69530543CA00eE6cab94B09f4` | POL | fTokens Mar 2025 ($POL) |
| `0x252452ccf245a59A6d1Afab11cF16750029b4620` (ETH), `0xB044433fdDCE4DabA3b24aC7Af464fd3f67aa154` (ARB) | ETH/ARB | ETH-USDC LP Jul 2025 (FLUID, 1yr vest) |
| `0x94312a608246Cecfce6811Db84B3Ef4B2619054E` | ARB/Base | FLUID Jul 2025 |
| `0xF36029358A684CdDD5103A4b84dC8a832c6e5b40` | ARB/Base | GHO Jul 2025 (FLUID) |
| `0x47bbA4cb84cC3227BF6FAB50464856E11D2FD41A` (ARB), `0x5986f3d7dd089d53784f72F8c4dE1BF49E4e851d` (ETH) | ARB/ETH | SyrupUSDC ($USDC) |

> For monitoring, `LogClaimed` (topic0 above) is the same across **all** instances — match by topic0 across the address set, or scope to the canonical per-chain instances.

---

## 5. Resolvers & other periphery (read-helpers; same address multichain unless noted)
| Name | Address | Chains | One-liner |
|------|---------|--------|-----------|
| LendingResolver | `0x48D32f49aFeAEC7AE66ad7B9264f446fc11a1569` | all 5 | fToken/lending state |
| LiquidityResolver | `0xca13A15de31235A37134B4717021C35A3CF25C60` | all 5 | Liquidity Layer state |
| RevenueResolver | `0x0A84741D50B4190B424f57425b09FAe60C330F32` | all 5 | protocol revenue |
| VaultResolver | `0xA5C3E16523eeeDDcC34706b0E6bE88b4c6EA95cC` | all 5 | vault state |
| VaultT1Resolver | `0xB21C67DD518F6d31257d3A4F12B0A6344885b268` | all 5 | T1 vault state |
| VaultPositionsResolver | `0xaA21a86030EAa16546A759d2d10fd3bF9D053Bc7` | all 5 | vault positions |
| VaultLiquidationResolver | `0xd8d1a39b1Fe519113b6D8e1E82Dc92aedaD40948` | all 5 | liquidation data |
| VaultTicksBranchesResolver | per-chain (ETH `0x8F31451Afa539cAfB92CBd5cdA41DC026f9CDc62`) | all 5 | vault ticks/branches |
| DexResolver | `0x11D80CfF056Cef4F9E6d23da8672fE9873e5cC07` (BNB `0xAf572EfC84d905926F7b05C1B7bE04e4E89542B0`) | all 5 | DEX V1 state |
| DexReservesResolver | `0x05Bd8269A20C472b148246De20E6852091BF16Ff` | all 5 | DEX reserves |
| FluidDexLiteResolver | `0x12a47cEB96A952E8D4A6eA9FE3b40b79bbaeb4e9` | ETH only | DEX Lite state |
| SmartLendingResolver | `0x3E69A3Af4305b65598b228d3da70786Bd9cfeB0e` (BNB `0x1446dEc487B4411DE222547ADbC3b3e01933787f`) | all 5 | smart lending (`fSL*` tokens) |
| StakingRewardsResolver | ETH `0x122E12eB5F235adAC8DC78292CB1838f065D9b9f`, ARB `0x53EB5A17D93b536d82521414EA00047De8DB7438`, Base `0x5d30B123aa5DD834bCB50490E150dE065E4Ee7f7`, POL `0x83fB87c8E85AD854f1B2D030f925211C6ae71D6d`, BNB `0x9c88eaF9f83fF3c796E71dd6888410645cEbf049` | all 5 | reads StakingRewards instances |
| StakingMerkleResolver | ETH `0xE3DcB2183fe0aBBa897F7880C6E8c58d9c5A3Ce9`, ARB `0x9A69715215eB352cf23e5407E5e6769648638512` | **ETH, ARB only** | reads MerkleDistributor state |
| StETHResolver | ETH `0xf0b280cCa857E0580a0aE13fbd8e7c7Ec71bfc38` | ETH | stETH integration |

---

## 6. Detection invariants & gotchas
1. **Three reward systems, do not conflate.** Rate model (no claim event) vs StakingRewards (`Staked`/`Withdrawn`/`RewardPaid`) vs MerkleDistributor (`LogClaimed`). Pick targets by which mechanism you're watching.
2. **FLUID is bridged at one shared address** (`0x61e030…`) on Arb/Base/BNB; native `0x6f40d4…` on ETH; **none on Polygon**.
3. **MerkleDistributor is a sprawl** — one canonical-per-chain plus ~15 per-campaign instances; `LogClaimed` topic0 is identical across all, so match by topic0 over the address set.
4. **StakingRewards has no `Recovered`** — Fluid's variant omits `recoverERC20`.
5. **StakingMerkleResolver is ETH+ARB only** — staking-merkle reads aren't available on Base/Polygon/BNB.

---

## 7. Quick-copy detection constants (bytea-ready for PG)
```
-- ===== FLUID token =====
FLUID_TOKEN_ETH                  = '\x6f40d4a6237c257fff2db00fa0510deeecd303eb'  -- native, symbol FLUID
FLUID_TOKEN_OFT                  = '\x61e030a56d33e8260fdd81f03b162a79fe3449cd'  -- bridged: Arb + Base + BNB (same addr)
FLUID_BUYBACK_PROXY              = '\x9afb8c1798b93a8e04a18553ee65bafa41a012f1'  -- ETH

-- ===== StakingRewards (Synthetix-style) =====
TOPIC_SR_REWARD_ADDED            = '\xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d'
TOPIC_SR_STAKED                  = '\x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'
TOPIC_SR_WITHDRAWN               = '\x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'
TOPIC_SR_REWARD_PAID             = '\xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'
TOPIC_SR_NEXT_REWARD_QUEUED      = '\x1f6864585aff6172b9e61fd517190576e478963013921dff17824a9b8ff101d8'

-- ===== MerkleDistributor =====
TOPIC_MD_CLAIMED                 = '\x309cb1c0dc6ce0f02c0c35cc1f46bbe61ec9deb311d101b87e7d25bd0b647fd7'
TOPIC_MD_ROOT_PROPOSED           = '\xb38026cc978f6c2642a5108ee558571a1b01a939b056abcc065b7eabacaf2d9d'
TOPIC_MD_ROOT_UPDATED            = '\xcc3c3071340d91a4fd687f9ad48d1ee5689f8083136feb3594807d0f7481f7cf'

-- ===== Canonical 2026 MerkleDistributors (GHO) =====
MD_CANON_ETH                     = '\xf398e66b1273a34558aebbec550dccaf4acc7714'
MD_CANON_ARB                     = '\xfa1bd6fb7014d1af41d9ae7fa4844b2944811215'
MD_CANON_BASE                    = '\x77b2ed3653f10ab269396fae6cf7cb196b2d486a'
```

---

## 8. Verification & sources
- **topic0/selector:** computed locally via keccak from `Instadapp/fluid-contracts-public` (`main`) `contracts/protocols/lending/{stakingRewards,merkleDistributor}/...`. `Staked`/`LogClaimed` spot-checked locally.
- **Addresses:** from `deployments/deployments.md` (fetched 2026-06-05) + `eth_getCode`/`symbol()`/`name()` confirmation. FLUID `symbol()`="FLUID" verified on ETH/Arb/Base/BNB; absent on Polygon.
- **Source:** [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) · `deployments/deployments.md`.
