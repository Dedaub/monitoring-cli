# ether.fi — Protocol Reference Index

Monitoring-grade references for ether.fi across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663), Arc (5042)**. Verified against live RPC, verified implementation ABIs, the official ether.fi "Deployed Contracts" page and the `etherfi-protocol/*` repos on 2026-10-30.

ether.fi is four product lines, not linear versions. One file per line:

| File | Product line | Components | Chains |
|------|--------------|------------|--------|
| [core.md](core.md) | **Staking core (LST/LRT)** | LiquidityPool, eETH, weETH, WithdrawRequestNFT, RedemptionManager, PriorityWithdrawalQueue, StakingManager, EtherFiNodesManager, EtherFiOracle, EtherFiAdmin, Membership, Liquifier, DepositAdapter, Restaker, rewards, RoleRegistry, timelocks, ETHFI, sETHFI | Ethereum only. UUPS proxies, upgraded by a 10-day timelock. |
| [weeth-crosschain.md](weeth-crosschain.md) | **weETH & ETHFI bridging** | weETH LayerZero OFT mesh (Ethereum lockbox adapter + L2 OFTs), native-minting sync pools (Base, OP) + L1SyncPool, Arbitrum canonical weETH, ETHFI OFT mesh | Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Robinhood Chain, Arc. **Not Polygon.** |
| [liquid.md](liquid.md) | **ether.fi Liquid vaults** | Veda BoringVault stacks (Liquid ETH/USD/BTC: Vault, Teller, Accountant, Manager, RolesAuthority, Queue), eBTC, sETHFI, Midas vaults (Liquid Reserve / USD RWAs / EUR) | Ethereum + Optimism (full); Base/Arbitrum (eBTC, sETHFI, dust liquidETH); Robinhood Chain (empty liquidUSD stack). |
| [cash.md](cash.md) | **ether.fi Cash (v3)** | CashModule, CashEventEmitter, EtherFiSafe + factory, DataProvider, legacy DebtManager, SettlementDispatchers, TopUpDest, top-up factories + bridge adapters | Core on Optimism; top-up factories on Ethereum, Base, BNB, Arbitrum. Lending = Aave V4 white-label, see [../aave/v4.md](../aave/v4.md). |

## Cross-cutting facts worth knowing before you start

- **The staking core is Ethereum-only.** No LiquidityPool, eETH or oracle exists on another chain. Two core literals have unrelated code elsewhere (Optimism `0x3088…F216` = 145 B stub; Base `0x3d32…3000` = uninitialised OFT-style token). See [core.md](core.md) §6.
- **weETH has three bridge shapes.** LayerZero OFT (Base, BNB, Avalanche, Optimism, Robinhood Chain, Arc), Arbitrum canonical gateway (Arbitrum), and native minting on Base/Optimism (L2 mint first, L1 backing later). Polygon has none.
- **Same literal, different role.** `0xe0080d2F…fD3f` = ETHFI OFT adapter (Ethereum), ETHFI mint/burn adapter (Base, Arbitrum), ETHFI token (Optimism). `0xF4e147Db…d8CF` = EtherFiSafeFactory (Optimism), TopUpSourceFactory (Ethereum/Base/BNB/Arbitrum), placeholder (Avalanche). Always key on `(chainId, address)`.
- **Same address, different code.** The Liquid Tellers share an address on Ethereum and Optimism but have different builds. The Teller `Deposit` topic0 and `deposit` selector differ by chain ([liquid.md](liquid.md) §1.2).
- **Topic collisions inside ether.fi.** Two `WithdrawRequestCreated`/`WithdrawRequestClaimed` (WithdrawRequestNFT vs PriorityWithdrawalQueue). Many `Deposit` events (LiquidityPool, L2 sync pool, Teller, TopUpDest). One pause family (`PausedUntil`/`UnpausedUntil`) on every core proxy. `BeaconProxyDeployed` on both Cash factories. Key on the emitter.
- **Selector collisions.** `0x0efe6a8b` `deposit(address,uint256,uint256)` = L2 sync pool and Ethereum Teller. `0x1da649cf` `repay(address,address,uint256)` = CashModule and DebtManager. `0x0bf5d35e` `bridge(address,uint256,uint256)` = SettlementDispatcher and TopUpSourceFactory.
- **Governance delays.** Ethereum Upgrade Timelock 10 days (holds `UPGRADE_TIMELOCK_ROLE`), Operating Timelock 2 days, L2 Timelock `0x851D…F5C6` 3 days (owns every weETH OFT), Cash Timelock 2 days.
- **Related docs.** LayerZero transport and the weETH OFT rows: [../layerzero/v2.md](../layerzero/v2.md). Arbitrum gateway: [../arbitrum_native/core.md](../arbitrum_native/core.md). Aave V3 EtherFi market (Ethereum) and V4 EtherFi Cash stack: [../aave/v3.md](../aave/v3.md), [../aave/v4.md](../aave/v4.md).

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the verified implementation ABI behind each proxy (impl read from the EIP-1967 slot). Cross-checked against live logs (explorer log pages and `eth_getLogs`). Every observed topic0 on the sampled emitters decoded with no unknown values.
- **Addresses:** official ether.fi pages and repo deployment files, existence-checked with `eth_getCode` on all nine chains. Proxy pattern from the EIP-1967 impl/admin/beacon slots. Roles, owners, peers, supplies and timelock delays read with `eth_call`.

## Coverage caveats

- **Per-user contracts are not listed.** EtherFiNode instances, EtherFiSafe and TopUp contracts are beacon proxies. Discover them with `EtherFiNodeDeployed` (StakingManager) and `BeaconProxyDeployed` (Cash factories).
- **Midas vault internals** (DataFeed, CustomFeed) are listed by address. Their oracle events were not decoded.
- **Three whitelisted Cash modules** are UUPS proxies whose names the repo does not give ([cash.md](cash.md) §3).
- **Polygon `0xF4e147Db…d8CF`** has a 21,601 B implementation that is not verified on an explorer.
- Chains outside the nine (Scroll, Blast, Linea, zkSync, Swell, Sonic, HyperEVM, Plasma, Monad, Berachain, Unichain …) are named only where they affect a target chain.
