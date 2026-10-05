# Synthetix — Protocol Reference Index

Monitoring-grade references for Synthetix across the target chains **Ethereum (1), Optimism (10), Base (8453), Arbitrum One (42161)**. Verified on-chain 2026-06; status re-checked 2026-10-05.

**Status (2026-10-05): the L2 deployments are wound down.** Synthetix deprecated Arbitrum and Base before 2025-08-16 and shut down Optimism in August 2025 (perps close-only 2025-08-18, positions force-closed 2025-08-25, all other Optimism functionality deprecated 2025-08-31), to focus on "Synthetix Mainnet", an Ethereum perps exchange with off-chain order matching (CLOB) and on-chain settlement (blog.synthetix.io, "Mainnet is where the heart is", 2025-08-16). That newer Ethereum perps system is **not covered** by these files. Observed last logs (indexed chain data): Optimism PerpsV2 BTC/ETH markets 2025-08-25; Arbitrum PerpsMarketProxy 2026-03-23; Base PerpsMarketProxy 2026-08-17 and Base CoreProxy 2026-09-01 (residual activity only); the V3 CoreProxy on Optimism and Ethereum got a new Router on 2026-06-25 and emitted no log after that day. Treat any new V3/PerpsV2 activity as an anomaly, not normal flow.

**Not deployed on BNB (56), Avalanche (43114), Polygon (137), Robinhood Chain (4663) or Arc (5042)** — `eth_getCode = 0x` confirmed for both V2 and V3 core contracts (Robinhood Chain and Arc checked 2026-10-05).

| File | Generation | What it covers | Chains (of 7) |
|------|-----------|----------------|---------------|
| [v2.md](v2.md) | **V2** (legacy; Optimism shut down 2025-08) | Proxyable-pattern synths/staking on Ethereum; PerpsV2 perpetuals + bridged SNX on Optimism | Ethereum (1), Optimism (10) |
| [v3.md](v3.md) | **V3** (L2s deprecated 2025; Ethereum CoreProxy dormant since 2026-06-25) | Diamond/Router proxy — CoreProxy, AccountProxy, USDProxy (snxUSD/USDx), SpotMarketProxy, PerpsMarketProxy | Optimism (10), Base (8453), Arbitrum (42161), Ethereum (1) |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** (per-chain, absence recorded) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Two completely different proxy patterns — never confuse them:**
  - **V2 "Proxyable":** `Proxy` → `target()` (stored at storage slot 2, NOT EIP-1967). Events emitted from proxy address, impl fetched via `proxy.target()`. Upgrading replaces the target.
  - **V3 Diamond/Router:** `CoreProxy` → `Router` → module implementations. No EIP-1967 impl slot. Router maps selectors to modules. `getImplementation()` on the CoreProxy returns the Router. Upgrades fire `Upgraded(address indexed self, address implementation)` from the proxy.
- **V3 Base CoreProxy is NOT the vanity address.** The canonical V3 CoreProxy vanity `0xffffffaEff0B96Ea8e4f94b2253f31abdD875847` (344B on Optimism/Arbitrum/Ethereum) is **different on Base**: `0x32C222A9A159782aFD7529c87FA34b96CA72C696`. Always specify both when filtering across chains.
- **V2 PerpsV2 is shut down.** Positions on the Optimism PerpsV2 markets were force-closed on 2025-08-25; the last `PositionModified` on the BTC and ETH markets is from that day. The key PerpsV2 monitoring event is `PositionModified(uint256,address,uint256,int256,int256,uint256,uint256,uint256,int256)` = `0xc0d933ba…`.
- **V3 perps are deprecated on Arbitrum and Base (2025).** The contracts keep their code, but there is no normal flow: Arbitrum PerpsMarketProxy last log 2026-03-23, Base PerpsMarketProxy last log 2026-08-17. No target chain has an active V3 perps market.
- **V3 Arbitrum USDProxy token is branded "USDx"**, not "snxUSD" (as on Optimism/Base). Confirm per-chain with `symbol()` before attributing.
- **V3 PerpsMarketProxy events emit from the PerpsMarketProxy address, not CoreProxy.** Key monitoring: `OrderSettled` (position executed) and `PositionLiquidated`. Both have large tuple params — verify exact signatures against source before decoding.
- **V2 FuturesMarketManager.allMarkets() returns empty array** after V3 migration moved collateral. Individual PerpsV2 market proxies remain deployed and functional for existing positions.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` (`cast keccak`) from `Synthetixio/synthetix` (V2) and `Synthetixio/synthetix-v3` (V3) canonical sources; key events cross-checked against live `eth_getLogs` (V2 `PositionModified` on Optimism PerpsV2 BTC market; V3 events on Base/Optimism CoreProxy).
- **Addresses:** every contract `eth_getCode`-verified present on its chain(s); V3 CoreProxy Router resolved via `getImplementation()`; V2 proxy targets read via `target()`.
- **Coverage caveats:** V3 `OrderSettled` / `OrderCommitted` tuple topic0s computed from source but not all live-matched (large struct params vary by version); V3 `OracleManagerProxy` and some collateral token addresses taken from meta.json (not individually code-verified per chain); V2 individual synth (sETH, sBTC…) contract addresses not enumerated (discover via `AddressResolver.getAddress(bytes32)`).
