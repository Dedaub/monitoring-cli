# Lista DAO — Protocol Reference Index

Monitoring-grade references for Lista DAO across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663), Arc (5042)**. Verified against live RPC, the official docs (`docs.bsc.lista.org`) and the canonical `lista-dao/*` repos on 2026-10-30.

Lista DAO is a BNB-Chain-first DeFi suite with several independent product lines. One file per product line. Each file follows the same section layout: Topics → Function signatures → Addresses per chain → Cross-chain summary → Proxies → Detection invariants & gotchas → Quick-copy bytea constants → Verification & sources.

| File | Product line | Components | Chains |
|------|--------------|------------|--------|
| [lending.md](lending.md) | **Lista Lending (Moolah)** — largest TVL | Moolah (Morpho Blue fork) singleton, MoolahVault (MetaMorpho fork), factories, IRMs, providers, LendingBroker fixed-rate markets, liquidators, Smart Lending StableSwap LP collateral, Credit Loans | BNB, Ethereum |
| [staking.md](staking.md) | **Liquid staking (slisBNB)** | ListaStakeManager, slisBNB, slisBNB LayerZero OFT (BSC adapter + Ethereum OFT), slisBNBx / clisBNB Launchpool certificate | BNB (+ Ethereum OFT) |
| [cdp.md](cdp.md) | **CDP (lisUSD)** | Interaction, MakerDAO-style Vat/Spot/Jug/Dog/Clipper/Vow, GemJoin/HayJoin, lisUSD, Jar, HelioProvider/SlisBNBProvider, USDT PSM, flash minter | BNB |
| [governance.md](governance.md) | **LISTA token & veLISTA** | LISTA (immutable, 1e9), VeLista (retired by LIP-024 on 2026-04-07), ListaVault emissions, distributors, EmissionVoting | BNB |
| [dex.md](dex.md) | **Lista DEX** | ListaV3 (Uniswap V3 fork) and ListaV2 (Uniswap V2 fork) | BNB, Ethereum (V3) |

## Cross-cutting facts worth knowing before you start

- **Chain footprint.** Every product is on BNB Chain. Ethereum has Moolah lending, the slisBNB OFT, the ListaV3 DEX and the slisXAUE RWA product. **Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc have no Lista deployment** (`eth_getCode` = `0x` at Moolah, LISTA, slisBNB, StakeManager, Interaction, lisUSD, the OFTs and both ListaV3 factories).
- **Moolah = Morpho Blue topic0s.** Moolah `Supply`/`Borrow`/`Repay`/`Withdraw`/`SupplyCollateral`/`WithdrawCollateral`/`Liquidate`/`FlashLoan`/`AccrueInterest`/`CreateMarket` share topic0 **and** selectors with Morpho Blue ([../morpho/v1.md](../morpho/v1.md)). MoolahVault shares MetaMorpho topic0s. Disambiguate by emitter: BNB Moolah `0x8F73b65B4caAf64FBA2aF91cC5D4a2A1318E5D8C` vs Morpho Blue BNB `0x01b0Bd…7a83a`. Ethereum Moolah `0xf820fB4680712CD7263a0D3D024D5b5aEA82Fd70` vs Morpho Blue `0xBBBBBbbB…EFFCb`.
- **Other topic0 collisions.** CDP `Interaction.Deposit` = ERC-4626 `Deposit` (`0xdcbc1c05…`). StakeManager and HelioProvider `Deposit(address,uint256)` = WBNB `Deposit` (`0xe1fffcc4…`). ListaV3/V2 = Uniswap V3/V2. Always filter by emitter.
- **Everything is upgradeable** except LISTA, the OFTs, the DEX core and the airdrop. Three proxy styles: UUPS ERC-1967 (130–170 B; Moolah stack), OZ v4 Transparent (2112/2141 B; StakeManager, slisBNB, CDP core), OZ v5 Transparent (1159 B; newer CDP joins, governance). On BNB the upgrade root for every product checked is the 1-day TimelockController **`0x07d274a68393e8b8a2ccf19a2ce4ba3518735253`** (sole `DEFAULT_ADMIN_ROLE` on Moolah; owner of the CDP, staking, governance and DEX ProxyAdmins). It is not listed in the docs. On Ethereum the Moolah admin is `0xa18ae79AEDA3e711E0CD64cfe1Cd06402d400D61`.
- **Address literals are reused across chains with different meaning.** Lista deploys from the same EOAs on BNB and Ethereum. `0xf820fB…Fd70` is Moolah on Ethereum and a VeListaRevenueDistributor implementation on BNB. `0xf9B24C…eBAa` is the slisBNB OFT on Ethereum and an unrelated contract on BNB. `0x8b7d33…F990` is the Moolah IRM on Ethereum and a Launchpool distributor on BNB. Always key on `(chainId, address)`.
- **slisBNB flows into lending and CDP.** slisBNB is the main collateral in Moolah and the CDP. Both use a "provider" that holds the slisBNB and mints the non-transferable slisBNBx certificate. Provider contracts appear as `caller` in Moolah events; the user is `onBehalf`.
- **Historical logs.** The public BSC RPC serves only recent logs. Rare events in these docs were confirmed by finding the topic0 constant in live implementation bytecode, not by historical logs.

## Not covered (smaller product lines)

These are listed on the docs site but have no dedicated file: **RWA** (RWAEarnPool/RWAAdapter on BNB; **slisXAUE** on Ethereum at `0x97b0A9c6A4d9fD51Bf8beBf04015F74C2e36A624`, an ERC-1967 proxy, with XAUTStaking `0x86c92fF74fa55b08b4fA0d59E41e26b14ed1150b` and XAUEAdapter `0x7509661232741c6912E278193404b912FC342F30`), **lisAster** (LisAster `0xa17A497D20cC143508FE3b63578b13ba6b9c9f06` and staking/reward contracts on BNB), **Lista Rights** holder emissions, and the multi-oracle (ResilientOracle, BoundValidator, PT linear-discount oracles). See the docs pages under "For Developer" for their addresses.

## Sources

- [Lista docs — For Developer](https://docs.bsc.lista.org/for-developer/overview) (smart-contract address pages per product).
- GitHub: [lista-dao/moolah](https://github.com/lista-dao/moolah) · [lista-dao/synclub-contracts](https://github.com/lista-dao/synclub-contracts) · [lista-dao/lista-dao-contracts](https://github.com/lista-dao/lista-dao-contracts) · [lista-dao/lista-token](https://github.com/lista-dao/lista-token) · [lista-dao/lista-v3](https://github.com/lista-dao/lista-v3)
- Explorers: [BscScan](https://bscscan.com) · [Etherscan](https://etherscan.io)
