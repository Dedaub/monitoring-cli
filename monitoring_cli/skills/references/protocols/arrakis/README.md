# Arrakis Finance — Protocol Reference Index

Monitoring-grade references for Arrakis (the Uniswap-liquidity-management protocol, originally "G-UNI" by Gelato) across the target chains **Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137)**. Verified on-chain 2026-06.

Arrakis is **not** an AMM itself — it deploys *vaults* that manage liquidity on an underlying DEX (Uniswap V3, and in the Modular generation also Uniswap V4 / Valantis). Three generations, each its own codebase:

| File | Generation | What a vault is | Chains (of 7) | Key contracts |
|------|-----------|-----------------|---------------|---------------|
| [v1.md](v1.md) | **V1 (G-UNI)** | one ERC-20 token wrapping a **single** managed Uniswap-V3 position | Ethereum, Polygon, Optimism, Arbitrum | `GUniFactory` (ETH `0xea1aff9d…2db7d9`), GUniRouter, GUniResolver |
| [v2.md](v2.md) | **V2** | multi-range Uniswap-V3 vault (per-instance), manager-driven | Ethereum, Polygon, Arbitrum, Base, Optimism, BNB | `ArrakisV2Factory`, `ArrakisV2Beacon`, Resolver, RouterV2, SimpleManager |
| [modular.md](modular.md) | **Modular** (current) | **Meta-vault** with pluggable **modules** (UniV4, Valantis HOT); public ERC-20 or private NFT | ETH, Base, Arbitrum, Optimism, Polygon, BNB | `ArrakisMetaVaultFactory` `0x820FB8127a689327C863de8433278d6181123982`, ArrakisStandardManager, Guardian, TimeLock |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** (per-chain, absence recorded) → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Arrakis is not on Avalanche.** V2 and Modular core contracts return `0x` on Avalanche; V1 is only on ETH/Polygon/Optimism/Arbitrum. Every absence is `eth_getCode`-recorded in the per-file tables.
- **Three vault models, three proxy patterns** — disambiguate by generation:
  - **V1 (G-UNI):** vaults are **full EIP-1967 transparent proxies** (the `GUniFactory` is the proxy admin, upgrades via `upgradePools()`); they emit a **non-standard `ProxyImplementationUpdated`**, not `Upgraded`. Events: `Minted`/`Burned`/`Rebalance`/`FeesEarned`; factory `PoolCreated(address,address,address)` (all three params indexed).
  - **V2:** vaults are OpenZeppelin **BeaconProxy** by default (beacon slot `0xa3f0ad74…133d50`; emit `BeaconUpgraded` at construction). Events: `LogMint`/`LogBurn`/`LogRebalance`/`LogCollectedFees`; factory `VaultCreated(address indexed manager, address indexed vault)` = `0x5d9c31ff…`. **V2 core addresses are deterministic — same address on every deployed chain.**
  - **Modular:** meta-vaults are full CREATE3 instances; **modules** are BeaconProxy clones (TimeLock-owned beacons). Public vaults are ERC-20, private vaults are owned by an NFT. Factory `LogPrivateVaultCreation` = `0x15509c43…` (live-confirmed).
- **⚠️ Modular: the real swap/LP events come from the *module*, not the vault.** A Modular meta-vault delegates to a module (Uniswap V4 module → events from the V4 `PoolManager`; Valantis HOT module → events from the Valantis pool). To monitor actual liquidity/swap activity you must follow `vault → module → underlying venue`, not just the meta-vault address.
- **Modular uses CREATE3 → same factory address on every chain** (`0x820FB8127a689327C863de8433278d6181123982`, verified code-present and ~21.8KB on ETH/Base/Arbitrum/Optimism/Polygon/BNB). **Nuance:** CREATE3 guarantees *address* determinism, **not bytecode equality** — ETH/Base/Arbitrum share one build, Optimism/Polygon another, BNB a third. Key by `(chain_id, address)`.
- **Managers are often a Gnosis Safe.** V2 vaults' `manager()` is frequently a `GnosisSafeProxy` (not the shipped `SimpleManager`); resolve the real manager via `vault.manager()` rather than assuming. The Modular `ArrakisStandardManager` is itself an ERC-1967 proxy (admin = TimeLock → upgradeable by timelock).

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` (`cast keccak`) from the Arrakis source generations; key events cross-checked against live `eth_getLogs` (V2 `VaultCreated` on a mainnet vault; Modular `LogPrivateVaultCreation` byte-for-byte against a live factory log).
- **Addresses:** every contract `eth_getCode`-verified present on its chain and confirmed `0x` (absent) where not deployed; factories confirmed via view calls (V1 `numPools()`, V2 `numVaults()`, Modular factory `manager()`/registry wiring + 2 public / 112 private vaults). Proxy/beacon slots read live.
- **Coverage caveats:** several low-frequency topic0s are computed-from-source not yet live-matched — `Modular LogPublicVaultCreation` (no public-vault creation in the sampled window), and assorted V1/V2 admin/manager events — flagged per file. V1 `GUniResolver` addresses on Polygon/Optimism/Arbitrum and the Arbitrum `GUniRouter` left as explicit UNVERIFIED placeholders. `ArrakisRoles` has no published address (`arrakis-modular` repo is private).

### Independent fact-check (2026-06)
All three files passed an adversarial multi-source cross-check (Arrakis docs/deployments page, GitHub, explorers, live RPC). Corrections folded in: **(1)** V1's "current gov token is ARR on Arbitrum" was refuted — that address has no code; **SPICE** (`0xe498c57f…`) is the verified token. **(2)** V2's "PALM has no canonical address" was corrected — **PALMTerms `0xB041f628…`** (in `v2-palm`) is the canonical manager. Additions: the **Gauge/staking** system (`GaugeRegistry` + `LiquidityGaugeV4`, shared V2/Modular), the broader **Modular module set** (UniV3, PancakeSwap, Aerodrome beyond UniV4/Valantis), and the Modular **Withdraw Helper**. All addresses, chain coverage, and proxy claims were otherwise confirmed.
