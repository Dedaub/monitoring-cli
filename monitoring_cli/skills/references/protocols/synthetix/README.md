# Synthetix — Protocol Reference Index

Monitoring-grade references for Synthetix across the target chains **Ethereum (1), Optimism (10), Base (8453), Arbitrum One (42161)**. Verified on-chain 2026-06.

**Not deployed on BNB (56), Avalanche (43114), or Polygon (137)** — `eth_getCode = 0x` confirmed on all three for both V2 and V3 core contracts.

| File | Generation | What it covers | Chains (of 7) |
|------|-----------|----------------|---------------|
| [v2.md](v2.md) | **V2** (legacy, maintenance mode) | Proxyable-pattern synths/staking on Ethereum; PerpsV2 perpetuals + bridged SNX on Optimism | Ethereum (1), Optimism (10) |
| [v3.md](v3.md) | **V3** (current) | Diamond/Router proxy — CoreProxy, AccountProxy, USDProxy (snxUSD/USDx), SpotMarketProxy, PerpsMarketProxy | Optimism (10), Base (8453), Arbitrum (42161), Ethereum (1) |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** (per-chain, absence recorded) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Two completely different proxy patterns — never confuse them:**
  - **V2 "Proxyable":** `Proxy` → `target()` (stored at storage slot 2, NOT EIP-1967). Events emitted from proxy address, impl fetched via `proxy.target()`. Upgrading replaces the target.
  - **V3 Diamond/Router:** `CoreProxy` → `Router` → module implementations. No EIP-1967 impl slot. Router maps selectors to modules. `getImplementation()` on the CoreProxy returns the Router. Upgrades fire `Upgraded(address indexed self, address implementation)` from the proxy.
- **V3 Base CoreProxy is NOT the vanity address.** The canonical V3 CoreProxy vanity `0xffffffaEff0B96Ea8e4f94b2253f31abdD875847` (344B on Optimism/Arbitrum/Ethereum) is **different on Base**: `0x32C222A9A159782aFD7529c87FA34b96CA72C696`. Always specify both when filtering across chains.
- **V2 PerpsV2 is in maintenance mode.** All V2 PerpsV2 markets (Optimism) are close-only; `PositionModified` events still fire as existing positions close. The key PerpsV2 monitoring event is `PositionModified(uint256,address,uint256,int256,int256,uint256,uint256,uint256,int256)` = `0xc0d933ba…`.
- **V3 Arbitrum perps were sunseted in 2025.** The Arbitrum CoreProxy (`0xffff…`) remains live but PerpsMarketProxy is set to close-only. Base is the primary active V3 perps chain.
- **V3 Arbitrum USDProxy token is branded "USDx"**, not "snxUSD" (as on Optimism/Base). Confirm per-chain with `symbol()` before attributing.
- **V3 PerpsMarketProxy events emit from the PerpsMarketProxy address, not CoreProxy.** Key monitoring: `OrderSettled` (position executed) and `PositionLiquidated`. Both have large tuple params — verify exact signatures against source before decoding.
- **V2 FuturesMarketManager.allMarkets() returns empty array** after V3 migration moved collateral. Individual PerpsV2 market proxies remain deployed and functional for existing positions.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` (`cast keccak`) from `Synthetixio/synthetix` (V2) and `Synthetixio/synthetix-v3` (V3) canonical sources; key events cross-checked against live `eth_getLogs` (V2 `PositionModified` on Optimism PerpsV2 BTC market; V3 events on Base/Optimism CoreProxy).
- **Addresses:** every contract `eth_getCode`-verified present on its chain(s); V3 CoreProxy Router resolved via `getImplementation()`; V2 proxy targets read via `target()`.
- **Coverage caveats:** V3 `OrderSettled` / `OrderCommitted` tuple topic0s computed from source but not all live-matched (large struct params vary by version); V3 `OracleManagerProxy` and some collateral token addresses taken from meta.json (not individually code-verified per chain); V2 individual synth (sETH, sBTC…) contract addresses not enumerated (discover via `AddressResolver.getAddress(bytes32)`).
