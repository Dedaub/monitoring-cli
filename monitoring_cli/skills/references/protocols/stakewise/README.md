# StakeWise — Protocol Reference Index

Monitoring-grade references for StakeWise across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137)**. Verified against live RPC + the canonical `stakewise/contracts` (V2) and `stakewise/v3-core` repos + `@stakewise/v3-sdk` `4.2.5` address files on 2026-06-09.

**Headline: of the 7 target chains, StakeWise is deployed on Ethereum mainnet ONLY.** Every V2 token (sETH2/rETH2/SWISE) and every V3 contract (VaultsRegistry/Keeper/OsToken/factories/vaults) returns **`0x` (no code) on Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon** — verified via `eth_getCode`. StakeWise V2 and V3 *also* run on **Gnosis Chain (100)** (osGNO, outside the 7 — mentioned as context, addresses listed but not deep-verified) and on the **Hoodi testnet (560048)**. There is **no StakeWise on Arbitrum** despite occasional speculation — the `v3-core` repo ships no Arbitrum deployment file and the canonical mainnet addresses have no code there.

StakeWise is **two generations** of liquid staking, not a linear `v2→v3`. One file per generation:

| File | Generation | Model | Status |
|------|-----------|-------|--------|
| [v2.md](v2.md) | **V2 — pooled** | Single shared **Pool** → mints rebasing **sETH2** (`StakedEthToken`, 1:1 with deposited ETH) + separate rebasing reward token **rETH2** (`RewardEthToken`); a 4-of-N **Oracles** quorum votes the daily reward Merkle root. | **Legacy, frozen for new deposits.** Migrated into the V3 GenesisVault (Apr 2024). Contracts still live; oracle still emits `RewardsUpdated`. Ethereum + Gnosis. Upgradeable proxies. |
| [v3.md](v3.md) | **V3 — vaults / osETH** | Per-vault **ERC-1967-proxy clones** deployed by an **EthVaultFactory** (+ priv / erc20 / blocklist / meta variants); each vault holds staked ETH and can mint the **overcollateralized, non-rebasing osETH** (`OsToken`) against its position. A single **Keeper** harvests every vault from one signed oracle Merkle root. | **Live, dominant.** Ethereum + Gnosis. Core singletons are **immutable** (no proxy); **vaults are upgradeable** ERC-1967 proxies. |

Each file follows the same layout: **Contract families** → **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function signatures** (chain-agnostic 4-byte selectors) → **Addresses** (Ethereum) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **sETH2 vs osETH — two completely different tokens, two generations.** **sETH2** (V2, `0xFe2e…043A`) is *rebasing* and *1:1 with deposited ETH* (rewards accrue in the **separate** rETH2 token). **osETH** (V3, `0xf1C9…0E38`) is a *non-rebasing*, *overcollateralized debt-style* token minted against a vault position (value accrues via `convertToAssets`). Do not treat them as the same asset.
- **Correct sETH2 address is `0xFe2e637202056d30016725477c5da089Ab0A043A`.** A frequently-circulated typo (`…20Ae81B5d52`) has **no code on-chain** — do not key on it. (rETH2 `0x20BC832ca081b91433ff6c17f85701B6e92486c5`, SWISE `0x48C3399719B582dD63eB5AADf12A40B4C3f52FA2`, osETH `0xf1C9acDc66974dFB6dEcB12aA385b9cD01190E38` all verified with code.)
- **V3 vaults are discovered, not enumerated.** Every vault is a per-vault ERC-1967 proxy minted by `EthVaultFactory.createVault` → indexed via the `VaultCreated(address indexed admin, address indexed vault, address ownMevEscrow, bytes params)` event (`0x0d606510…`) and the registry's `VaultAdded` (`0x2f069741…`). The vault *implementation* is shared per factory version; the factory's `implementation()` is immutable, but each vault can self-upgrade (`upgradeToAndCall`). Key all vault activity on `(chainId, vaultAddress)`.
- **The GenesisVault (`0xAC0F906E433d58FA868F936E8A43230473652885`) is the V2→V3 bridge.** It is the on-chain successor to the V2 Pool: V2 sETH2/rETH2 holders migrate in, and it inherits the V2 pool-escrow ETH. It is a normal V3 ETH vault (same event/selector set) but predeployed (not factory-minted), behind its own ERC-1967 proxy (impl `0xf113bfd6…`).
- **Topics + selectors are 100% chain-agnostic** — identical on Ethereum and Gnosis; only the emitting address changes. (Moot for the 7 targets since only Ethereum has code.)
- **`Harvested`, `MevReceived`, `ExitedAssetsClaimed`, `ExitQueueEntered` collide across emitters.** Keeper vs SharedMevEscrow vs OwnMevEscrow vs OsTokenVaultEscrow all reuse names — always disambiguate by emitting contract. See each file's §1 collision notes.
- **Immutability split is the opposite of V2.** V3 **core singletons** (VaultsRegistry, Keeper, OsToken, OsTokenVaultController, OsTokenConfig, all factories, DepositDataRegistry, SharedMevEscrow, PriceFeed) read EIP-1967 impl slot `0x0` → **immutable, no proxy**. V3 **vaults** are ERC-1967 proxies. V2 is the inverse: **all V2 tokens/pool are upgradeable** TransparentUpgradeableProxies behind one shared ProxyAdmin (`0x3EB0175d…`); SWISE itself is a proxy.

## Coverage caveats (read these)

- **Per-vault addresses are not enumerated** — StakeWise V3 is permissionless; vaults number in the hundreds. The docs list singletons + factories; discover instances via `VaultCreated` / `VaultAdded`.
- **Gnosis (chain 100) addresses are listed for context** (from the SDK + `v3-core/deployments/gnosis.json`) but were not each re-verified on-chain this pass — only the osGNO token presence was spot-checked. Gnosis is outside the 7 targets.
- **Hoodi (560048)** is the V3 testnet and is omitted from the per-chain address sections (testnet, outside scope) — noted only so its addresses are not mistaken for mainnet.
- **V2 deposit selectors** (`stake*` on the Pool) are not in the trimmed canonical V2 ABI snapshot (the deployed Pool impl is the v3.0.0 "migration" build whose public surface is reduced); V2 staking is closed, so [v2.md](v2.md) documents the still-live monitoring surface (rebases, rewards-Merkle votes, escrow) and marks the historical deposit path as such.
