# Paxos — Protocol Reference Index

Monitoring-grade references for the Paxos-issued tokens across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663), Arc (5042)**. Verified against live RPC, the `paxosglobal/*` repos and the Paxos developer docs on 2026-10-30.

Paxos issues centrally minted ERC-20 tokens. Each token has a supply-control contract, a pause switch, and an asset-protection (freeze and wipe) role. Two code builds are live:

| File | Tokens | Build | Chains (of the 9) |
|------|--------|-------|-------------------|
| [usdg.md](usdg.md) | **USDG** (Global Dollar, 6 dec) | `PaxosTokenClaimableRewards` (V3): UUPS proxy + selector facets + opt-in rewards + SupplyControl + LayerZero OFTWrapper. Admin is a 1-day TimelockController. | Ethereum, Arbitrum One, Robinhood Chain |
| [pyusd_usdp_paxg.md](pyusd_usdp_paxg.md) | **PYUSD** (6 dec), **USDP** (18 dec), **PAXG** (18 dec), legacy **BUSD** (18 dec) | `PaxosTokenV2` (no facets) + SupplyControl. BUSD stays on the V1 build. Zeppelin `AdminUpgradeabilityProxy` on ETH/ARB. | PYUSD: Ethereum, Arbitrum One, Polygon PoS. USDP, PAXG, BUSD: Ethereum only |

No Paxos token is deployed on **Base, BNB, Avalanche, Optimism or Arc** (`eth_getCode` = `0x` for every address). Robinhood Chain has USDG only.

## Cross-cutting facts worth knowing before you start

- **Supply events are Paxos-specific.** A mint emits `SupplyIncreased(address indexed to, uint256)` `0xf5c174d5…8797` and then `Transfer(0x0 → to)`. A burn emits `SupplyDecreased(address indexed from, uint256)` `0x1b7e1824…8a63` and then `Transfer(from → 0x0)`. These two topics are the same in every build.
- **Pause events are `Pause()` `0x6985a022…f625` / `Unpause()` `0x7805862f…5b33`,** not the OpenZeppelin `Paused(address)`.
- **Freeze topics changed between builds.** V2 and V3 emit `FreezeAddress` `0x1aa66049…c392`. V1 (BUSD, and pre-upgrade history of the others) emits `AddressFrozen` `0x90811a8e…3690`. `FrozenAddressWiped` `0xfc5960f1…aede` is the same in all builds and is followed by `SupplyDecreased`.
- **Minting is gated by `SupplyControl`.** `SupplyControllerAdded` `0xcf08d9c6…3c26` adds a minter with a rate limit. The same three supply-controller EOAs (`0xf845a0a0…`, `0x2fb074fa…`, `0x835e20da…`) serve USDG, PYUSD, USDP and PAXG.
- **Bridging is burn-and-mint.** The Paxos `OFTWrapper` (LayerZero v2) is a supply controller on every chain, Ethereum included. There is no lockbox. Join `OFTSent` / `OFTReceived` on `guid`.
- **USDG facets.** USDG routes pause, freeze, permit and rewards selectors to facet contracts. A `FacetUpdate(bytes4,address)` `0x59277b34…914a` changes behavior without an `Upgraded` event. All events still come from the token proxy.
- **Proxy slots differ.** USDG and all SupplyControls use EIP-1967. PYUSD (ETH, ARB), USDP, PAXG and BUSD use the ZeppelinOS slots `0x7050c9e0…f8c3` (impl) and `0x10d6a54a…390b` (admin).
- **Decoys.** The Ethereum USDG literal `0xe343…491D` holds "Flux USD" on Arbitrum and a PYUSD-related contract on Polygon. Always key on `(chainId, address)`.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `paxosglobal/paxos-token-contracts`. Live `eth_getLogs` confirmed the supply, freeze, EIP-3009 and rewards topics on Ethereum and Arbitrum.
- **Addresses:** from the Paxos docs mainnet pages, existence-checked with `eth_getCode` on all nine chains. Wiring (`supplyControl()`, `getAllSupplyControllerAddresses()`, `getFacet`, `defaultAdmin()`, `token()`) was read live.
- **Proxies:** EIP-1967 and ZeppelinOS slots read live.

## Coverage caveats

- PYUSD, USDG and USDP on non-target chains (Solana, Stellar, Ink, Mantle, X Layer, Stable) are not covered. "PYUSD0" / "USDG0" OFT representations issued through LayerZero on other chains are not Paxos `PaxosTokenV2` contracts.
- The LayerZero OApp configuration of each OFTWrapper (peers, DVNs) is in the LayerZero v2 reference, not here.
- Admin-event history was back-filled in full on Robinhood Chain only. On Ethereum, Arbitrum and Polygon the public RPC serves recent blocks only, so those chains were checked with recent windows and live `eth_call` state.
