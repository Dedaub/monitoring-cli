# Maple — Protocol Reference Index

Monitoring-grade references for Maple Finance. The lending protocol is on **Ethereum (1)** and **Base (8453)**. Bridged Syrup tokens are on BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10) and Polygon PoS (137). Robinhood Chain (4663) and Arc (5042) have no code at the modular-release addresses; the token survey in syrup-cross-chain.md does not cover them. Verified against live RPC, the canonical `maple-labs/*` repos and the `maple-labs/address-registry` on 2026-05-29. Re-checked on 2026-10-30 for the modular release.

| File | Generation | Components | Status |
|------|-----------|------------|--------|
| [v1.md](v1.md) | **Maple 1.0** (`maple-core`, 2021) | Pools, Loans, StakeLocker, MapleGlobals V1, MPL/xMPL | **Deprecated.** Ethereum only. |
| [v2.md](v2.md) | **Maple 2.0 / Syrup** (`maple-core-v2`, Dec 2022) | Pool (ERC-4626), PoolManager, FixedTerm/OpenTerm Loans and LoanManagers, WithdrawalManager (Cyclical/Queue), MapleGlobals, PoolPermissionManager, SyrupRouter | **Live.** Ethereum + Base. Proxied. |
| [modular.md](modular.md) | **Modular release** (2026-10) | StrategyManager, Allocation / ModularAave / ModularSky strategy factories, legacy Aave / Sky / Basic strategies, LiquidityRouterV100, StrategyDeployerV100, PoolDeployerV5, PoolManager V500 and Globals V500 changes, Secured Lending 2 and 3 USDC pools | **Live on Ethereum only.** Factories registered. No StrategyManager instance yet (2026-10-30). |
| [syrup-cross-chain.md](syrup-cross-chain.md) | **Tokens** | SYRUP (LayerZero OFT), syrupUSDC / syrupUSDT / syrupUSDG (Chainlink CCIP) | **Live.** 7 chains. |

Each file has the same section order: Topics → Function signatures → Addresses (per chain) → Cross-chain summary → Proxies → Detection invariants → Quick-copy bytea constants → Verification & sources.

## Cross-cutting facts

- **Almost everything in Maple 2.0 is a `maple-proxy-factory` proxy.** The implementation is at the standard EIP-1967 slot. Upgrades emit Maple `Upgraded(uint256 toVersion, bytes arguments)` `0xaaaa7ee6…`, not OpenZeppelin `Upgraded(address)`. Pools (ERC-4626) and factories are not proxies.
- **Ethereum PoolManagers run V500 since 2026-10-27 (block 26,284,267).** V500 removes first-loss cover events and functions and adds StrategyManagers. The Base PoolManager still runs V301.
- **MapleGlobals (`0x804a…390C`) is the registry for every role.** `ValidInstanceSet(bytes32,address,bool)` with keys such as `POOL_MANAGER_FACTORY`, `STRATEGY_MANAGER_FACTORY`, `LIQUIDITY_BOT` and `MAPLE_MANAGED_WALLET` controls which contracts and bots can move funds.
- **Same event names, different topics.** FixedTerm vs OpenTerm loans, legacy vs modular strategies, and Pool vs StrategyManager `RedemptionRequested` all differ. Key on `(emitter, topic0)`, never on the event name.
- **V1 and 2.0 are separate.** Different repos, different Globals, different events. MPL and xMPL are shared and are migrating to SYRUP.
- **Same address on Ethereum and Base** for some singletons (PoolPermissionManager, withdrawalManagerQueueFactory, fixedTermLoanFactoryV2, poolDeployerV3, SYRUP OFT). Key on `(chainId, address)`.

## Sources

- [maple-labs/address-registry](https://github.com/maple-labs/address-registry) — auto-generated per-chain address files.
- [maple-labs](https://github.com/maple-labs) repos: `maple-core`, `pool-v2`, `globals-v2`, `fixed-term-loan`, `open-term-loan`, `withdrawal-manager-queue`, `strategy-manager`, `allocation-strategy`, `defi-strategies`, `maple-strategies`, `syrup-utils`.
- [Maple docs](https://docs.maple.finance/).
