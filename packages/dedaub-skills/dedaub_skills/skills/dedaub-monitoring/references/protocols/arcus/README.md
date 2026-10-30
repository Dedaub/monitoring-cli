# Arcus — Protocol Reference Index

Monitoring-grade references for Arcus, the Robinhood Chain perpetuals and Stock Token exchange built by the dYdX team. Verified against live RPC and the official `arcus-xyz/*-contracts-abis` repos on 2026-10-30.

Arcus is deployed on **Robinhood Chain (4663) only**. Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon and Arc have no Arcus contract (`eth_getCode` = `0x` for every address in these files).

| File | Product line | Components | Status |
|------|--------------|------------|--------|
| [perps.md](perps.md) | **Perps rootchain** | BridgeVault (custody, 64.5 M arcUSDG), CheckpointManager, ValidatorConsensus, BlockExecutor, ValidatorBeacon, EmergencySettlement, PaxosDepositProxy, PaxosWithdrawalUnwrapper, TimelockController | Live. UUPS proxies. Official ABIs. |
| [ptokens.md](ptokens.md) | **pTokens** | PTokenFactory, pToken beacon, 17 pToken vaults (ERC-4626 + ERC-7540) | Live since 2026-08. Beacon proxies. No public ABI; signatures recovered from bytecode and logs. |
| [spot.md](spot.md) | **Spot router** | SwapShell, ArcusSettlement, RFQ/AMM executors, WrappedTokenFactory/Escrow/beacon | Live. UUPS proxies. The official ABI repo lags the chain. |

## Cross-cutting facts

- **Funds sit in one contract.** The BridgeVault `0x14b107cf534239c59571b066cb6497a321da897c` holds the perps margin as **arcUSDG** (`0x4fdbdaf4…15a4`, a Paxos vault share of USDG), not as USDG. pToken collateral also ends up there (pTokens are Arcus accounts).
- **No on-chain price oracle.** Perps prices, funding and liquidations live on the permissioned appchain. pToken NAV is signed off-chain by a `NAV_SIGNER_ROLE` key. On-chain monitoring sees deposits, withdrawals, batch finalization, governance and upgrades.
- **Two admin domains.** The perps rootchain is administered by the validator set (ValidatorConsensus and CheckpointManager hold `DEFAULT_ADMIN_ROLE`) plus a 1-day OpenZeppelin timelock and two 2-of-5 guardian Safes. The pToken and spot contracts are owned by one Safe 2-of-5, `0x81b80499c396a9931b9e44953425a82c1b2541bd`, with no timelock.
- **USDG flow.** User USDG → `PaxosDepositProxy` → Paxos Teller (mint arcUSDG) → `BridgeVault.DepositInitiated` → `DepositConfirmed` after a validator batch. Withdrawal: validator batch → `WithdrawalInitiated` → keeper `executeWithdrawal` → `WithdrawalUnwrapped` (USDG out).
- **Robinhood Chain block numbers run fast** (core contracts at block ~159 k; head ~101.8 M on 2026-10-30). The public log RPC `https://rpc.mainnet.chain.robinhood.com` caps a query at 10 M blocks and 10,000 logs.

## Verification methodology

- **Topic0 / selectors:** recomputed locally with `keccak256`. Official ABIs were matched against the live implementation bytecode. pToken signatures were matched against live topic0s and dispatcher selectors.
- **Addresses:** official `deployments.json`, DefiLlama adapter (pToken factory), docs (BridgeVault `verifyingContract`), and on-chain reads (`pTokenAt`, `marginAsset`, `wrappedToken`, EIP-1967 slots, roles). Every address was existence-checked with `eth_getCode` on all nine target chains.
