# Blackhole DEX — Protocol Reference Index

Monitoring-grade references for Blackhole, the ve(3,3) + concentrated-liquidity DEX on **Avalanche C-Chain (43114)**. A ThenaFi fork. Verified on-chain 2026-06.

**Blackhole is Avalanche-only** — `eth_getCode = 0x` on all other six target chains (Ethereum, Base, BNB, Arbitrum, Optimism, Polygon) for every contract.

| File | Component | What it covers | Key contracts |
|------|-----------|----------------|---------------|
| [classic.md](classic.md) | **Classic AMM + Governance** | Solidly-style volatile/stable pairs + full ve(3,3) stack (BLACK/veBLACK, Voter, GaugeManager, Minter, Bribes, RewardDistributor) | `PairFactory` `0xfE926062…`, `RouterV2` `0xe946A9f3…`, `VoterV3` `0xE30D0C85…`, `VotingEscrow` `0xEac56281…`, `BLACK` `0xcd94a876…` |
| [cl.md](cl.md) | **CL AMM + Genesis Pools** | Algebra-based concentrated liquidity + CL gauge farming + Genesis Pools (pre-TGE seeding) | `AlgebraFactory` `0x512eb749…`, `SwapRouter` `0xaBfc48e8…`, `NFPM` `0x3fED017E…`, `GenesisPoolFactory` `0xdeB50ac7…` |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **`PairCreated` includes `bool stable` in 3rd position** — `PairCreated(address,address,bool,address,uint256)` = `0xc4805696…`. This differs from standard Uniswap V2 `PairCreated` (`0x0d3648bd…`). The `stable` flag identifies pool type directly from the event.
- **CL pool Swap topic0 = Uniswap V3** (`0xc42079f9…`, standard 7-param). Despite the codebase using Algebra Integral imports, the deployed pools emit the same Swap signature as Algebra V1 / Uniswap V3. Confirmed live on Avalanche. Use the AlgebraFactory `Pool` event or NFPM `symbol()="ALGB-POS"` to distinguish Blackhole CL from UniV3.
- **Two Blackhole-specific CL pool events** not in upstream Algebra source:
  - `SwapFee(address,uint24,uint24)` = `0x9443903d…` — fires on every swap with current fee rates
  - `BurnFee(address,uint24)` = `0x1a25098b…` — fires on every burn
- **Key proxies**: VoterV3, GaugeManager, MinterUpgradeable, and GaugeFactoryCL are upgradeable (EIP-1967 transparent proxy via shared ProxyAdmin `0xd763061c…`). VotingEscrow, PairFactory, AlgebraFactory, and NFPM are immutable.
- **VotingEscrow** `name()="veBlack"`, `symbol()="veBLACK"`. BLACK `name()="BLACKHOLE"`, `symbol()="BLACK"`.
- **Genesis Pools** are Blackhole-specific pre-TGE liquidity seeding — not present in upstream Thena/Algebra. Watch `GenesisPoolFactory` and `GenesisPoolManager` for project launches.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(sig)` from the `code-423n4/2025-05-blackhole` audit repo source; classic AMM `PairCreated`/`Swap`/`GaugeCreated`/`Voted` and CL `Swap`/`Burn`/`SwapFee`/`BurnFee` confirmed live via `eth_getLogs` on Avalanche.
- **Addresses:** every contract `eth_getCode`-verified on Avalanche; confirmed `0x` on all other 6 target chains; factory views and proxy slot reads performed on-chain.
- **Coverage caveats:** GenesisPool individual instance events and rare admin events computed from source but not all live-matched. The VotingEscrow lock-operation event has an unresolved second indexed param (always `0x0` in all observed logs) — flagged in [classic.md](classic.md).
