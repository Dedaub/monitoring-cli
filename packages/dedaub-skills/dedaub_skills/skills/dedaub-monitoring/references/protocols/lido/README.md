# Lido — Protocol Reference Index

Monitoring-grade references for Lido liquid staking (stETH / wstETH). The staking protocol runs on **Ethereum (1) only**. Other chains carry only bridged wstETH. The live Ethereum deployment is **Lido protocol v4.1.0** (`docs.lido.fi/deployed-contracts`, checked 2026-10-30).

Lido upgrades **in place**. The stETH, StakingRouter, AccountingOracle and WithdrawalVault proxies keep their addresses across V1 → V2 → V3 → V4. Each file documents what its generation adds. Read the newer files together with the older ones.

| File | Generation | Components | Status |
|------|-----------|------------|--------|
| [v1.md](v1.md) | **V1 — pre-Shapella** (Dec 2020 → May 2023) | stETH, LidoOracle push model, NodeOperatorsRegistry | **Legacy.** Historic indexing only. Ethereum. |
| [v2.md](v2.md) | **V2 — post-Shapella** (May 2023) | stETH base ABI, wstETH, WithdrawalQueueERC721, StakingRouter, AccountingOracle + HashConsensus, VEBO, NodeOperatorsRegistry, SimpleDVT, DAO / Dual Governance | **Live core ABI.** Ethereum. |
| [v3.md](v3.md) | **V3 — stVaults** | VaultHub, Accounting, LazyOracle, OperatorGrid, PredepositGuarantee, StakingVault beacon/factory, external shares, CSM (module 3) | **Live.** Ethereum. |
| [v4.md](v4.md) | **V4 — Staking Router v3** (v4.0.0, 2026-07-24) **+ EDF** (v4.1.0, 2026-10-07) | 0x02 withdrawal credentials, CuratedModule v2 (module 4), CSM 0x02 (module 5), consolidation stack, TopUpGateway, CircuitBreaker, DelegationFactory, v4 `ReportData` | **Live.** Ethereum. |
| [l2.md](l2.md) | **Bridged tokens** | wstETH (± rebasable L2 stETH) on Base, Arbitrum, Optimism, BNB; Polygon canonical-bridge wstETH and sunset stMATIC; Avalanche third-party OFT | **Live.** No staking on these chains. |

Each file follows the same layout: **Topics** → **Function signatures** → **Addresses** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts

- **Ethereum-only protocol.** No Lido v2/v3/v4 contract has code on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon PoS, Robinhood Chain or Arc. Those chains have bridged wstETH at most ([l2.md](l2.md)).
- **The live ABI is v4.** The deployed stETH impl is `0x0282…cDb0` and the AccountingOracle impl is `0xe4f0…9136`. Decode oracle reports with `submitReportData` `0x11a78d23` ([v4.md](v4.md) §2.1). The V2 (`0xfc7377cd`) and V3 (`0x1001587f`) selectors no longer exist.
- **Use shares, not balances.** stETH rebases every oracle report. Track `TransferShares` and `sharesOf`, not raw `Transfer` amounts ([v2.md](v2.md)).
- **Five staking modules.** IDs 1 NodeOperatorsRegistry, 2 SimpleDVT, 3 CSM, 4 CuratedModule v2, 5 CSM 0x02. Modules share many topic0s (`SigningKeyAdded`, `NodeOperatorAdded`, bond events). Always filter by the emitter address.
- **Redeployed contracts.** The DepositSecurityModule, Burner and OracleReportSanityChecker get new addresses on upgrades. Resolve the current ones from LidoLocator `0xC1d0…d2Eb`.
- **Proxy model.** Core and module contracts use EIP-1967 `OssifiableProxy`. stETH uses an Aragon app proxy. Every proxy admin is the Aragon Agent `0x3e40…9C8c` (Dual Governance). Watch `Upgraded(address)` `0xbc7cd75a…2d3b`.
- **Bots act through DelegationContracts (v4.1.0).** Oracle reports and top-ups go through EDF instances (`execute(address,bytes)` `0x1cff79cd`). The top-level `tx.to` is not the Lido contract.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` from canonical source or verified ABIs, then confirmed in live `eth_getLogs` and in deployed bytecode (`PUSH4` scan).
- **Addresses:** from `docs.lido.fi/deployed-contracts` and LidoLocator getters, existence-checked with `eth_getCode`. Proxy impls are read from the EIP-1967 slot.
- **Chain coverage:** `eth_getCode` on all nine target chains. Absence is recorded in each file.
