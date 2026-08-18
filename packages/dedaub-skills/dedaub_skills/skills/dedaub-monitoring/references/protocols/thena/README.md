# THENA Finance — Protocol Reference Index

Monitoring-grade references for THENA, the ve(3,3) + concentrated-liquidity DEX on **BNB Smart Chain (56)**. The original protocol that Blackhole (Avalanche) and Ramses (Arbitrum) forked from. Verified on-chain 2026-06.

**THENA is BNB Smart Chain only** — `eth_getCode = 0x` on all other six target chains.

| File | Component | What it covers | Key contracts |
|------|-----------|----------------|---------------|
| [classic.md](classic.md) | **Classic AMM + Governance** | Solidly volatile+stable pairs + ve(3,3) governance (THE/veTHE, VoterV3, MinterUpgradeable, Gauges, Bribes, RewardsDistributor) | `PairFactory` `0xAFD89d21…`, `VoterV3` `0x8FBB1ECE…`, `VotingEscrow` `0xfBBF371C…`, `THE` `0xF4C8E32E…` |
| [cl.md](cl.md) | **CL AMM (Algebra V1)** | Concentrated liquidity — Algebra V1 (NOT Integral). AlgebraFactory, NFPM, SwapRouter | `AlgebraFactory` `0x306F06C1…`, `NFPM` `0xa51adb08…` |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** → **Proxies** → **Detection invariants** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **⚠️ VoterV3 address**: The VoterV3 is `0x8FBB1ECEbb9E9839bC0dE00b9c4C585CabDD0462`. The address `0x3005b0d3…` is the **EpochDistributorBSC** (a separate rewards distributor), not the Voter — don't confuse them.
- **Classic AMM PairCreated includes `bool stable`** — 5-arg `PairCreated(address,address,bool,address,uint256)` = `0xc4805696…`. Call `pair.stable()` to determine pool type.
- **Classic AMM Swap = Uniswap V2** (`0xd78ad95f…`). Disambiguate by pair address.
- **CL is Algebra V1** (NOT Algebra Integral as used in Blackhole/Pharaoh). Key differences: no `plugin()`, no `communityVault()`, no `SwapFee`/`BurnFee` events. NFPM is "Algebra Positions NFT-**V1**" / `"ALGB-POS"`.
- **No SwapFee/BurnFee events** — these are Blackhole-specific additions not present in THENA original. CL pools emit `Fee(uint16)` = `0x598b9f04…` before each swap (dynamic fee update).
- **MinterUpgradeable and PairFactory are EIP-1967 proxies**; VoterV3, VotingEscrow, AlgebraFactory are immutable.
- **CL NFPM IncreaseLiquidity is 6-arg** (`0x8a82de7f…`) — Algebra V1 adds `actualLiquidity` + `pool`. Differs from UniV3 4-arg form.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(sig)` from `ThenafiBNB/THENA-Contracts` GitHub source; classic `PairCreated`/`Fees`/`Sync`/`Vote`/VE `Deposit` and CL `Swap`/`Mint` confirmed live via `eth_getLogs` on BNB Smart Chain.
- **Addresses:** every contract `eth_getCode`-verified on BNB; confirmed `0x` on all 6 other target chains.
- **Coverage caveats:** some low-frequency governance/admin events computed from source but not all live-matched. CL `Fee` event `0x598b9f04…` is well-established Algebra V1 signature.
