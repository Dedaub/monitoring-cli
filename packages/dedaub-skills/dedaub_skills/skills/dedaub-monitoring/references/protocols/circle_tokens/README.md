# Circle tokens — reference index

Circle's issued tokens on the nine target chains: the **FiatToken** family (USDC, EURC, cirBTC) and **USYC**. These files cover supply control (mint, burn, minter allowances), blacklist, pause, rescue, roles and upgrades. Cross-chain movement of these tokens is in [../cctp/README.md](../cctp/README.md) (USDC burn-and-mint, CrossChainTokenService for EURC and cirBTC) and [../circle_gateway/core.md](../circle_gateway/core.md). StableFX (USDC ⇄ EURC on Arc) is in [../circle_stablefx/core.md](../circle_stablefx/core.md).

**Status:** verified on 2026-10-30 against live RPC on all nine target chains, Circle's USDC, EURC, cirBTC and USYC address pages, Arc's contract-address page, `circlefin/stablecoin-evm` and the verified implementation sources.

| File | Tokens | Contracts | Proxy pattern | Chains |
|------|--------|-----------|---------------|--------|
| [fiattoken.md](fiattoken.md) | USDC (6 dec), EURC (6 dec), cirBTC (8 dec) | FiatTokenProxy, FiatTokenV2_2 / NativeFiatTokenV2_2, MasterMinter | Legacy zos `AdminUpgradeabilityProxy` (not EIP-1967); MasterMinter immutable | USDC: ETH, Base, Avax, Arb, OP, Poly, Robinhood, Arc · EURC: ETH, Base, Avax, Arc · cirBTC: ETH, Arc · **none on BNB** |
| [usyc.md](usyc.md) | USYC (6 dec) | USYC token, Teller, Cross Chain Teller, Entitlements, Oracle, PriceReporter | UUPS (EIP-1967); Cross Chain Teller immutable | ETH, BNB, Arc |

## Presence matrix

| Chain | ID | USDC | EURC | cirBTC | USYC |
|-------|----|------|------|--------|------|
| Ethereum | 1 | ✅ | ✅ | ✅ | ✅ (+ Teller, Cross Chain Teller) |
| Base | 8453 | ✅ | ✅ | — | — |
| BNB Smart Chain | 56 | — | — | — | ✅ (Cross Chain Teller only) |
| Avalanche C-Chain | 43114 | ✅ | ✅ | — | — |
| Arbitrum One | 42161 | ✅ | — | — | — |
| Optimism | 10 | ✅ | — | — | — |
| Polygon PoS | 137 | ✅ | — | — | — |
| Robinhood Chain | 4663 | ✅ (not on Circle's list) | — | — | — |
| Arc | 5042 | ✅ native gas token | ✅ | ✅ | ✅ (supply 0) |

## Cross-cutting facts

1. **Every token address is per chain.** No token address is reused on a second chain (each literal has code only on its own chain). Key every rule on `(chainId, address)`.
2. **Two code bases, one colliding topic.** FiatToken `MinterConfigured(address indexed,uint256)` and USYC `MinterConfigured(address,uint256)` have the same topic0 `0x46980fca…0d20` and different indexing.
3. **Supply signals differ.** FiatToken emits `Mint` / `Burn` plus `Transfer` to or from `0x0`. USYC emits only `Transfer` to or from `0x0`.
4. **Two upgrade-event layouts.** FiatTokenProxy `Upgraded(address)` is not indexed (impl in `data`). USYC and its contracts use EIP-1967 `Upgraded(address indexed)`. Same topic0 `0xbc7cd75a…2d3b`.
5. **Arc USDC is the native coin.** The system emitter `0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE` logs every native move at 18 decimals; the token `0x3600…0000` logs ERC-20 calls at 6 decimals. Pick one stream.
6. **Not Circle tokens.** Binance-Peg USDC on BNB and the bridged `USDC.e` / "USD Coin (PoS)" / "USD Coin (Arb1)" tokens are out of scope (addresses in fiattoken.md §7).
7. **Role holders are per token and per chain.** Owner, pauser, blacklister, MasterMinter and proxy admin differ on every deployment (tables in fiattoken.md §3–§6; usyc.md §3–§5).
