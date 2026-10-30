# Extended — Topics, Selectors, Addresses (Arc settlement; legacy StarkEx on Ethereum)

**Status:** verified on 2026-10-30 against live Arc RPC (`https://rpc.mainnet.arc.io`, `https://arc-rpc.publicnode.com`), live Ethereum RPC, the Sourcify-verified sources on Arc (chain 5042) and the Blockscout-verified sources on Ethereum, the official Extended docs, and the DefiLlama `extended` TVL entry.
**Scope:** the on-chain contracts of the Extended perpetuals exchange (formerly X10). The current settlement system lives on **Arc (5042)** only. A legacy, frozen StarkEx Perpetual instance stays on **Ethereum (1)**. Topics and selectors are chain-agnostic. Addresses are network-specific. No Extended contract exists on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon or Robinhood Chain (§5).

Extended moved its settlement from Starknet to Arc on **2026-10-22**. The official "Technical Architecture" page names the Arc settlement contract `0x4445AACaCC2dE174B77b37Eb27529ce0B36bC580`. The contract is `PerpSettlement`, an SP1 zk-proof settlement for an off-chain matching engine. An operator submits batches with `settle(journal, proof, effects, stateDiffChunks)`. The contract checks a Groth16 SP1 proof. Then it applies a typed effect list in the same transaction: credits deposits, pays withdrawals, mints and burns vault shares, and logs liquidations.

Funds do **not** stay in `PerpSettlement`. A deposit sits in `PerpSettlement` as a pending ticket. When a proof consumes the ticket, the tokens move to a **Circle Modular Smart Contract Account (MSCA)** custody wallet `0x8910…67A2`. The `MscaTreasury` policy plugin `0x8cd3…c660` controls that wallet. A withdrawal pulls tokens from custody back to `PerpSettlement` and hands them to the **Rhino.fi bridge** on Arc in the same `settle`. Rhino.fi then pays the user on the destination chain. Extended has no deposit contract of its own on Ethereum, Arbitrum, Base, BNB, Polygon or Avalanche: those routes go through Rhino.fi (see the `rhinofi` reference). The custody wallet held about **104.4M USDC, 718 WETH and 28.5 cirBTC** on 2026-10-30.

**There is no user escape hatch on Arc.** No forced-withdrawal, freeze or exit function exists in `PerpSettlement`. A user can only reclaim an **unprocessed** deposit with `cancelDeposit` after `cancelDelay` (7 days). Every withdrawal needs the `SETTLER_ROLE` operator and a valid proof.

---

## 0. Contract families & versions

| Contract | Chain | Role | Proxy? |
|----------|-------|------|--------|
| **PerpSettlement** | Arc | State root, deposit tickets, batch settlement, withdrawal payout, vault-share mint/burn. | **UUPS** ERC1967Proxy (130 B); `UPGRADER_ROLE` authorizes |
| **MscaTreasury** (`ProtocolTreasury` policy + Circle MSCA plugin) | Arc | `depositInto` / `withdrawFrom` policy for the custody wallet; 5 %/day withdrawal cap per token. | **UUPS** ERC1967Proxy; only `TreasuryUpgradeGate` can upgrade |
| **Custody account** (Circle MSCA, `UpgradableMSCA`) | Arc | Holds all settled collateral. Created by `MscaTreasury.createAccount()`. | ERC1967Proxy → Circle impl `0xA70F…2B62` (unverified on Sourcify; pinned by codehash in `MscaTreasury`) |
| **TreasuryUpgradeGate** | Arc | `Ownable2Step` timelock for treasury upgrades; 2-day delay; guardian can cancel. | No (1,991 B) |
| **XVS** (`VaultShareToken`, "Extended Vault Share") | Arc | ERC-20 share of the Extended Vault. Only `PerpSettlement` mints/burns. 6 decimals. | No (2,128 B) |
| **SP1Verifier** (Groth16, v6.1.0) | Arc | Proof verifier called by `settle`. | No (5,709 B) |
| **Rhino.fi bridge** (`DVFDepositContract`) | Arc | Withdrawal exit leg; immutable `rhinoBridge` in `PerpSettlement`. Not an Extended contract. | Transparent proxy (Rhino.fi) |
| **StarkExchange (StarkPerpetual)** — legacy | Ethereum | Old X10/Extended StarkEx Perpetual. **Frozen since 2026-02-17**. Users exit with `escape` + `withdraw`. | StarkWare proxy (custom slot) |

Bridge assets on Arc (`bridgeAssets(id)`, read live): **0 = USDC** `0x3600…0000` (quantum 1, deposit type 1), **344 = WETH** `0x128c…4EDB` (quantum 1e12), **346 = XVS** `0x0bce…3fcb` (quantum 1, type 2 = vault share). Asset 345 is configured with a zero token. cirBTC sits in custody but has no token entry in `bridgeAssets` on 2026-10-30.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally from the verified ABIs. "Live" = seen in `eth_getLogs` on Arc blocks 28,646,000–28,666,000 (count in brackets).

### 1.1 PerpSettlement (`0x4445…C580`)

| topic0 | Event | Live |
|--------|-------|------|
| `0xf7987694c649140ede0c33712077c37652df2dea2cfd1fff54751b313d1d919e` | `DepositQueued(bytes32 indexed depositHash,address indexed depositor,uint32 indexed position,uint32 asset,uint32 assetVersion,uint64 quantizedAmount,uint256 rawAmount,bytes32 salt)` | ✅ (54) |
| `0x0c0146bbc54d30a18a6a43531e980131f3cd5ec2b0cd0ccf6b786b07387dd725` | `DepositProcessed(bytes32 indexed depositHash,uint32 indexed position,uint32 indexed asset,uint32 assetVersion,uint64 quantizedAmount,bytes32 salt)` | ✅ (51) |
| `0xfedcf703cd64f014753705fc7938733fae807da28706e8e523d1e60db0ee610a` | `DepositCancelled(bytes32 indexed depositHash,address indexed depositor,uint256 rawAmount,bytes32 salt)` | refund path |
| `0x22064fc128e6deeb077304674fa3e066ee0424d8858be90279228cce94ea199e` | `Withdrawal(uint32 indexed position,bytes32 indexed commitmentId,uint32 indexed asset,uint64 amount)` | ✅ (43) |
| `0x74cd4e944568075ed9b5a8c3db1109c32cced5a5008cc0fd15301fbfb7a98489` | `Liquidation(uint32 indexed liquidatedPosition,uint32 indexed liquidatorPosition,uint32 indexed asset,int64 baseAmount,int64 quoteAmount)` | ✅ (27) |
| `0x60ac5b1ee505d9f300b7566f6d3629cd12cd62dd34469f69e5eef2d1c6d737fe` | `PositionCreated(uint32 indexed position,bytes32 indexed ownerPublicKey)` | ✅ (24) |
| `0x27483f8a752384a9d1ce04a79c9e389bc65c5bd2aed37194d8fab79c7d19f0bd` | `BatchSettled(bytes32 prevRoot,bytes32 newRoot,uint32 applied,bytes32 eventsRoot)` | ✅ (33) |
| `0xfaaca86bc099cda634a771950e2274dcf9b6e76f88ae48cc16fb96b175898c10` | `BridgeAssetRootUpdated(bytes32 indexed previousRoot,bytes32 indexed newRoot)` | ✅ (33, one per batch) |
| `0x33b7d9fc4c4e3429b978557b0747997bee0bff3638f982f9330a743c0601fca7` | `StateDiffChunkPosted(bytes32 indexed chunkHash,uint256 length)` | ✅ (63) |
| `0x3acf177ad277887f85e58e52169881507dd50097e12e3f7aa0726b585787548b` | `VaultSharesMinted(uint32 indexed receiver,uint32 indexed source,uint32 indexed asset,uint64 shares,bytes32 salt,uint32 vaultPosition,uint32 investedAsset,uint64 investedAmount,bytes32 correlationId)` | ✅ (7) |
| `0x0a1ced31cf162d34de6c1ba8e712b6b23b829d16a86b84da235cc81e17d0814f` | `VaultSharesBurned(uint32 indexed position,uint32 indexed asset,uint64 shares)` | ✅ (20) |
| `0xf8ad63feea3ac0f3efd8347f7bcccdb99426b2b1bfc811eafc79d163d7e85fa3` | `VaultSupplyInitialized(uint32 indexed asset,uint64 shares)` | one-time (migration) |
| `0x3058dfc2f461afbd1162821afb43d0eded77fc8c5a8cb1c32abcd69a268a9fb4` | `CustodyActivated()` | **once**: block 27,299,132 (2026-10-22 14:43 UTC) |
| `0x4702d4a842dc1f570feb7894f37e6c46544f80f842da8a87ab9526c1080b64a7` | `BridgeAssetConfigured(uint32 indexed asset,address indexed token,uint64 quantum,uint32 version,uint8 assetType,bool active)` | asset registry change |
| `0x480e808863529746f89169a187f622b1e572ebd6b7a403793955c8f6aff8478c` | `BridgeAssetPaused(uint32 indexed asset,bool paused)` | **deposit pause** |
| `0x1abb27c10d7691fde754b929520c8884218b08dd1a48bfef66ee47a6ab98c717` | `MaxDepositUpdated(uint32 indexed asset,uint256 maxDeposit)` | admin |
| `0x32ab364b44a3388803507a747792aef515bbe3b56a1afcfcde87c4d95a3d46e0` | `CancelDelayUpdated(uint64 cancelDelay)` | admin |
| `0xd2c3a8a49d41ff18659f0d8243687aad2715daa262638b47a8e6b79c1efca74a` | `TreasuryConfigured(address indexed treasury)` | once (block 24,935,223) |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | **impl rotation** |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role,address indexed account,address indexed sender)` | role change |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role,address indexed account,address indexed sender)` | role change |
| `0x3377dc44241e779dd06afab5b788a35ca5f3b778836e2990bdb26a2a4b2e5ed6` | `DefaultAdminTransferScheduled(address indexed newAdmin,uint48 acceptSchedule)` | admin handover |
| `0xf1038c18cf84a56e432fdbfaf746924b7ea511dfe03a6506a0ceba4888788d9b` | `DefaultAdminDelayChangeScheduled(uint48 newDelay,uint48 effectSchedule)` | admin |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | init |

### 1.2 MscaTreasury (`0x8cd3…c660`) and TreasuryUpgradeGate (`0x686b…1a0d`)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xedb91c7cfba21699815cdfbceeeff58063764ec530eb7dfb48aa060443ac0169` | `Deposit(address indexed token,uint256 amount,uint64 timestamp)` | treasury ✅ (51) |
| `0x2f2e6e3734b7f724088fe25c16f6ebd572e77abf7c0aef4bc7b56b5cfc20b276` | `Withdrawal(address indexed token,uint256 amount,uint64 timestamp)` | treasury ✅ (43) |
| `0xbcb6a2b7ca8ddda718dfe9d1c167beb4b43c9d8461da309122491f2161976b07` | `AdminLimitChanged(address indexed token,uint64 percent)` | treasury — **daily cap changed** |
| `0x588a96cb0331a8cf96597662d5b378ca2b32c0ddca45c2ddd6881d227bdc7f0f` | `AdminLimitReset(address indexed token)` | treasury — **cap window reset by governor** |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | treasury — **halts all deposits and withdrawals** |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | treasury |
| `0x2492e15a409c8fc3c0bdcb1a55702d31935d0b34caa6b7bb33a7a3e347165a8d` | `MscaCreated(address indexed account,address indexed implementation,address indexed upgradeGate)` | treasury, once |
| `0x52ca9d3c1c30859d0763c3664a6b7cdbe66172048385fe9b0010533932912b04` | `UpgradeScheduled(bytes32 indexed operation,address indexed implementation,bytes data,uint256 executableAt)` | gate — **treasury upgrade proposed** |
| `0xf6224a998aea3de231cf75375faf8c3711379d54bb84c92ef9d9779dabd383a9` | `UpgradeExecuted(bytes32 indexed operation)` | gate |
| `0x3581f2526e53a276effa5116f0579562b23947cbd75fbabdeb6049aa7f5c50e6` | `UpgradeCancelled(bytes32 indexed operation)` | gate |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner,address indexed newOwner)` | gate |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner,address indexed newOwner)` | gate |

The treasury also emits the OpenZeppelin `RoleGranted`/`RoleRevoked`/`DefaultAdmin*`/`Upgraded` topics of §1.1.

### 1.3 Legacy StarkEx Perpetual (Ethereum `0x1cE5…3C65`)

Counts are from `eth_getLogs` on blocks 21,000,000–latest.

| topic0 | Event | Note |
|--------|-------|------|
| `0x06724742ccc8c330a39a641ef02a0b419bd09248360680bb38159b0a8c2635d6` | `LogDeposit(address depositorEthKey,uint256 starkKey,uint256 vaultId,uint256 assetType,uint256 nonQuantizedAmount,uint256 quantizedAmount)` | 2,057; last at block 23,568,257 |
| `0x03c10a82c955f7bcd0c934147fb39cafca947a4294425b1751d884c8ac954287` | `LogWithdrawalAllowed(uint256 ownerKey,uint256 assetType,uint256 nonQuantizedAmount,uint256 quantizedAmount)` | still live (escape credits) |
| `0xb7477a7b93b2addc5272bbd7ad0986ef1c0d0bd265f26c3dc4bbe42727c2ac0c` | `LogWithdrawalPerformed(uint256 ownerKey,uint256 assetType,uint256 nonQuantizedAmount,uint256 quantizedAmount,address recipient)` | still live (5 in the last 400k blocks) |
| `0xcab1cf17c190e4e2195a7b8f7b362023246fa774390432b4704ab6b29d56b07b` | `LogUserRegistered(address ethKey,uint256 starkKey,address sender)` | live; precedes escapes |
| `0x2672b53d25204094519f7b0fba8d2b5cd0cc1e426f49554c89461cdb9dcec08f` | `LogUpdateState(uint256 sequenceNumber,uint256 batchId)` | 9,486; stopped at 24,125,005 |
| `0x5f3a3d7d7c2b8cc20fa315d7504580e81d5f74ea46e1b3dc2985281df08e204d` | `LogForcedWithdrawalRequest(uint256 starkKey,uint256 vaultId,uint256 quantizedAmount)` | 1 |
| `0xf5b8e6419478ab140eb98026ab5bd607038cb0ac4d4dad5b1fc0848dfd203d1f` | `LogFrozen()` | **1, block 24,477,131 (2026-02-17)** |
| `0x07017fe9180629cfffba412f65a9affcf9a121de02294179f5c058f881dcc9f8` | `LogUnFrozen()` | none |
| `0xff14288d542bc1c1d15a652cb52af735f065c0c9d70b48e454a203c260733544` | `ImplementationUpgraded(address implementation,bytes initializer)` | StarkWare proxy upgrade |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 PerpSettlement

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x94d80a2b` | `deposit(address,uint32,uint256,bytes32)` | `(token, position, amount, salt)` → `bytes32 depositHash`. Permissionless. Pulls tokens, emits `DepositQueued`. |
| `0x31404484` | `cancelDeposit(bytes32)` | Depositor only, after `cancelDelay`. Refund + `DepositCancelled`. |
| `0x90276513` | `rejectDeposit(bytes32)` | `DEPOSIT_ADMIN_ROLE`. Refund + `DepositCancelled`. |
| `0x0a0ba0c1` | `settle(bytes,bytes,bytes,bytes32[])` | `SETTLER_ROLE`. Verifies proof, applies effects, pays withdrawals. |
| `0x40f40ded` | `postStateDiff(bytes)` | `DA_POSTER_ROLE`. Calldata data availability. |
| `0x6c1ff028` | `syncBridgeAsset(uint32,bytes32,(address,uint64,uint32,uint8,bool),bytes32[])` | Permissionless, Merkle-proved asset load. |
| `0x6c4fefed` | `setBridgeAssetPaused(uint32,bool)` | `DEPOSIT_ADMIN_ROLE`. |
| `0xae54c198` | `setMaxDeposit(uint32,uint256)` | `DEPOSIT_ADMIN_ROLE`. Cap counts escrow + custody balance. |
| `0x81f5733c` | `setCancelDelay(uint64)` | `DEPOSIT_ADMIN_ROLE`. |
| `0xf29fad3f` | `configureTreasury(address)` | `DEFAULT_ADMIN_ROLE`, one-time. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | `UPGRADER_ROLE` (self-administered). |
| `0x2f2ff15d` / `0xd547741f` | `grantRole(bytes32,address)` / `revokeRole(bytes32,address)` | role admin. |
| `0x634e93da` / `0xcefc1429` | `beginDefaultAdminTransfer(address)` / `acceptDefaultAdminTransfer()` | 2-day admin handover. |
| `0x9588eca2` | `stateRoot()` | view → `bytes32`. |
| `0x61d027b3` | `treasury()` | view → `0x8cd3…c660`. |
| `0x47c61ea7` | `rhinoBridge()` | view (immutable) → `0x5e02…CaCd1`. |
| `0x2b7ac3f3` | `verifier()` | view (immutable) → `0x6a18…734a`. |
| `0xda2a6286` | `custodyActive()` | view → `true` since 2026-10-22. |
| `0xfd2a5d3d` | `bridgeAssets(uint32)` | view → `(token, quantum, version, assetType, active)`. |
| `0x49d6fd53` | `bridgeAssetByToken(address)` | view. |
| `0x4377de95` | `pendingDeposits(bytes32)` | view (pending ticket). |
| `0x0460574c` | `depositHash(address,address,uint32,bytes32,uint32,uint64,bytes32)` | pure; **sha256**, not keccak. |

### 2.2 MscaTreasury / TreasuryUpgradeGate / XVS

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3fdd49fa` | `depositInto(address,uint256)` | Pulls tokens into custody. Called by `PerpSettlement`. |
| `0x9470b0bd` | `withdrawFrom(address,uint256)` | `perpsContract` only. 5 % of the custody balance per token per day (`DEFAULT_PROTECTION_PERCENT`). |
| `0x56bc3952` | `changeProtectionLimitPercent(address,uint64)` | `APP_GOVERNOR_ROLE`. |
| `0x37c9168a` | `resetProtectionLimit(address)` | `APP_GOVERNOR_ROLE`. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | `SECURITY_AGENT_ROLE` / `SECURITY_ADMIN_ROLE`. |
| `0xfb6318a8` | `custodyAccount()` | view → `0x8910…67A2`. |
| `0x9b741529` | `perpsContract()` | view → `0x4445…C580`. |
| `0xe7264f2a` | `upgradeGate()` | view → `0x686b…1a0d`. |
| `0x1c4c963a` | `scheduleUpgrade(address,bytes)` | gate owner. |
| `0xdce0c9ac` | `executeUpgrade(address,bytes)` | anyone, after `delay` (172,800 s). |
| `0x55f29166` | `cancelUpgrade()` | gate owner or guardian. |
| `0xa0712d68` / `0x79cc6790` | `mint(uint256)` / `burnFrom(address,uint256)` | XVS; settlement only. |

### 2.3 Legacy StarkEx Perpetual (Ethereum)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x366a2670` | `escape(uint256,uint256,uint256)` | `(starkKey, vaultId, quantizedAmount)`; frozen-mode exit, credits `LogWithdrawalAllowed`. |
| `0x441a3e70` | `withdraw(uint256,uint256)` | `(ownerKey, assetType)`; emits `LogWithdrawalPerformed`. |
| `0xbea84187` | `registerEthAddress(address,uint256,bytes)` | Links an ETH key to a Stark key. |
| `0xaf1437a3` | `forcedWithdrawalRequest(uint256,uint256,uint256,bool)` | Pre-freeze censorship escape. |
| `0x75d4eefd` | `freezeRequest(uint256,uint256,uint256)` | Called once; froze the exchange. |
| `0x2505c3d9` | `deposit(uint256,uint256,uint256,uint256)` | Closed. |
| `0x33eeb147` | `isFrozen()` | view → `true`. |

---

## 3. Addresses — Arc (chain ID 5042)

All existence-checked with `eth_getCode` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **PerpSettlement** (proxy) | `0x4445AACaCC2dE174B77b37Eb27529ce0B36bC580` | Main contract. Deployed at block 24,929,472 (2026-10-08). Named in the official docs. |
| PerpSettlement impl (current) | `0x93Dfdeb3dEc38c52c1635b8F288a1455710781D4` | 22,575 B, `PerpSettlement`, solc 0.8.36, Sourcify exact match. Live since block 27,680,321 (2026-10-24). |
| PerpSettlement impl (old) | `0xf08DF2F9b0341Aa972712AC20534585Ea123283C` | 22,125 B; impl at deployment. |
| **MscaTreasury** (proxy) | `0x8Cd3267dE1177D1Dfd940f502a5Ce682420cc660` | Custody policy. `treasury()` of the settlement. |
| MscaTreasury impl | `0xF640B59a993F7dBeCc939d6a12257C14ea4F448a` | 17,251 B, `MscaTreasury`, Sourcify exact match. |
| **Custody account** (Circle MSCA) | `0x89103959Eef431bEa308027b8A5073c5ddc867A2` | **Holds the funds**: 104.4M USDC, 718 WETH, 28.5 cirBTC, 52.27M XVS. |
| Circle MSCA impl | `0xA70F1296869DA9D7CB69578123F21888E6dB2B62` | 16,412 B; constant `CIRCLE_IMPLEMENTATION` in `MscaTreasury`. |
| **TreasuryUpgradeGate** | `0x686B940FD1D2943B3b8FE90027Ef014fE2751A0d` | Owner `0xB87D…CB87`, guardian `0x703D…E3aF`, delay 172,800 s. |
| **XVS** (Extended Vault Share) | `0x0BCEdC69A801eBf2B9cD3da5Dc64ba03f01a3Fcb` | `VaultShareToken`, 6 dp, supply 52.28M; `settlement()` = `0x4445…C580`. |
| SP1Verifier (Groth16 v6.1.0) | `0x6A1866bc78275C3dCd4d6ea087Ad2204D3cb734A` | Proof verifier. |
| Treasury factory | `0x09FC901DfA00ef5bD86470B6b132D39837eF66F1` | 1,381 B; granted the first treasury roles at deployment. |
| Rhino.fi bridge (external) | `0x5e023c31E1d3dCd08a1B3e8c96f6EF8Aa8FcaCd1` | Withdrawal exit leg (`rhinoBridge()`). |
| USDC (Arc native, ERC-20 view) | `0x3600000000000000000000000000000000000000` | Bridge asset 0. |
| WETH | `0x128cC466B61f542da60c70e3aA11c10e19B84EDB` | Bridge asset 344. |
| cirBTC | `0x171A4217b86A807A64eB94757Db6849fb4bDbAA0` | 8 dp; held in custody. |

**Role holders (read live with `hasRole` on 2026-10-30):**

| Contract | Role | Holder |
|----------|------|--------|
| PerpSettlement | `DEFAULT_ADMIN_ROLE`, `UPGRADER_ROLE`, `DEPOSIT_ADMIN_ROLE` (= `owner()`) | `0xc3323F7803149a5A055723b41bf670EF8920317e` (EOA) |
| PerpSettlement | `SETTLER_ROLE`, `DA_POSTER_ROLE` | `0x05193432BcC9e2BAd28B7C6355B8f3C9F52D4dc6` (EOA, sends every `settle`) |
| MscaTreasury | `DEFAULT_ADMIN_ROLE`, `APP_GOVERNOR_ROLE`, `APP_ROLE_ADMIN_ROLE`, `SECURITY_ADMIN_ROLE` | `0xB87d482d9E84D07c1D6A26BB89d504dE2912Cb87` (EOA) |
| MscaTreasury | `UPGRADER_ROLE` | `0x686B…1a0d` (TreasuryUpgradeGate) |
| TreasuryUpgradeGate | `owner()` / `guardian()` | `0xB87D…CB87` / `0x703d415af7BB94B189eF4De7D8D190bfbBA1E3af` (EOA) |

`defaultAdminDelay()` is 172,800 s (2 days) on both role contracts.

## 4. Addresses — Ethereum mainnet (chain ID 1) — legacy only

| Role | Address | One-liner |
|------|---------|-----------|
| **StarkExchange proxy** (legacy X10/Extended StarkEx Perpetual) | `0x1cE5D7f52A8aBd23551e91248151CA5A13353C65` | 6,984 B StarkWare `Proxy`. Frozen. Held about 155k USDC on 2026-10-30. Listed in DefiLlama's `extended` entry. |
| StarkPerpetual dispatcher impl | `0x8C43C9bec15d82D153C52518030e0a9590ABD35d` | 5,365 B, `StarkPerpetual`, solc 0.6.12. |

No `PerpSettlement`, treasury or XVS code exists on Ethereum.

## 5. Other target chains

Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137) and Robinhood Chain (4663): `eth_getCode` returns `0x` for all 12 addresses of §3–§4. Deposits and withdrawals on these chains go through the Rhino.fi bridge. Extended does not deploy a contract there.

## 6. Cross-chain summary

| Chain (ID) | PerpSettlement | Treasury + custody | XVS | Legacy StarkEx |
|------------|----------------|--------------------|-----|----------------|
| Arc (5042) | `0x4445…C580` | `0x8cd3…c660` / `0x8910…67A2` | `0x0bce…3fcb` | — |
| Ethereum (1) | — | — | — | `0x1cE5…3C65` (frozen) |
| Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood | — | — | — | — |

## 7. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **PerpSettlement** `0x4445…C580` | UUPS (OZ `ERC1967Proxy`, 130 B) | EIP-1967 impl slot = `0x93df…81d4`; admin slot empty | `UPGRADER_ROLE` (EOA `0xC332…317E`); the role admins itself, so `DEFAULT_ADMIN_ROLE` cannot override it. **No timelock.** Watch `Upgraded` (`0xbc7cd75a…`). One upgrade so far: `0xf08d…283c` → `0x93df…81d4` at block 27,680,321. |
| **MscaTreasury** `0x8cd3…c660` | UUPS (`ERC1967Proxy`) | impl slot = `0xf640…448a` | Only `TreasuryUpgradeGate` (`_authorizeUpgrade` checks `msg.sender`). Watch `UpgradeScheduled` on the gate (2-day warning) and `Upgraded` on the treasury. |
| **Custody account** `0x8910…67A2` | `ERC1967Proxy` → Circle `UpgradableMSCA` | impl slot = `0xa70f…2b62` | The plugin manifest exposes no execution function. MSCA self-upgrade and ERC-4337 operations fail closed. Watch `Upgraded` on the account. |
| **StarkExchange** (Ethereum) `0x1cE5…3C65` | StarkWare proxy | impl at slot `keccak256("StarkWare2019.implemntation-slot")` = `0x177667…761b24` → `0x8c43…d35d` | StarkWare upgrade governors with an activation delay. Watch `ImplementationUpgraded` (`0xff14288d…`). |
| TreasuryUpgradeGate, XVS, SP1Verifier, factory | not proxies | impl slot empty | immutable |

## 8. Detection invariants & gotchas

1. **The funds are in the custody account, not in `PerpSettlement`.** `PerpSettlement` holds only pending deposits (about 3.2 USDC on 2026-10-30). A balance or drain monitor must watch `0x8910…67A2`.
2. **One `settle` is many events.** Each settlement transaction emits `BatchSettled` + `BridgeAssetRootUpdated` and then one event per effect (`DepositProcessed`, `Withdrawal`, `Liquidation`, `PositionCreated`, `VaultShares*`). Key a user flow on the effect events, not on `BatchSettled`.
3. **Join a withdrawal to its payout by `commitmentId`.** In the same transaction the Rhino.fi bridge emits `BridgedDepositWithId` (`0x1655dc42…`) with `sender = 0x4445…C580` and `commitmentId = Withdrawal.commitmentId`. The destination chain and recipient are only in the Rhino.fi quote. The contract cannot check them, so the operator is trusted.
4. **Amounts are quantized.** `Withdrawal.amount` and `DepositQueued.quantizedAmount` are in units of the asset quantum. USDC quantum = 1 (6 dp). WETH quantum = 1e12, so the event value is in micro-ETH. Multiply by `bridgeAssets(asset).quantum` before you price it. `DepositQueued.rawAmount` is the token amount.
5. **Positions are `uint32` ids, not addresses.** `position` in every user event is an off-chain account id. Only `DepositQueued.depositor` and `DepositCancelled.depositor` carry an EVM address. `PositionCreated.ownerPublicKey` links a position to a key (Stark keys carried over from Starknet).
6. **`depositHash` is sha256.** `depositHash(...)` and `bridgeAssetLeaf(...)` use `sha256(abi.encodePacked("perp.deposit.v1", …))`. Do not recompute them with keccak.
7. **Treasury daily cap.** `withdrawFrom` reverts when the day's withdrawals pass 5 % of the custody balance at the last reset. Then the whole `settle` reverts and every withdrawal stalls. `AdminLimitReset` and `AdminLimitChanged` are the operator levers. Alert on both.
8. **Centralized keys.** The settlement admin/upgrader and the treasury admin are plain EOAs on 2026-10-30. A `RoleGranted`, `Upgraded` or `DefaultAdminTransferScheduled` on either contract is high severity.
9. **No escape hatch on Arc.** No forced withdrawal or freeze exists. The only user-side exit is `cancelDeposit` for a deposit that was never processed. Treasury `Paused` stops all settlement payouts.
10. **Arc native USDC emits two `Transfer` logs.** Each USDC move logs an 18-decimal `Transfer` from the system address `0xffff…fffe` and a 6-decimal `Transfer` from `0x3600…0000`. Count only one, or you double the volume.
11. **Migration artefacts.** Before `CustodyActivated` (block 27,299,132), `DepositProcessed.salt` = 0 and `Withdrawal` paid nothing on Arc, because the funds were still on Starknet. `VaultSupplyInitialized` fired once to import the XVS supply.
12. **Legacy Ethereum StarkEx is frozen, not empty.** `isFrozen()` = true since block 24,477,131. Exits still run (`LogUserRegistered` → `escape` → `LogWithdrawalAllowed` → `withdraw` → `LogWithdrawalPerformed`). New `LogDeposit` or `LogUpdateState` events would be anomalous.

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_EXT_DEPOSIT_QUEUED          = '\xf7987694c649140ede0c33712077c37652df2dea2cfd1fff54751b313d1d919e'
TOPIC_EXT_DEPOSIT_PROCESSED       = '\x0c0146bbc54d30a18a6a43531e980131f3cd5ec2b0cd0ccf6b786b07387dd725'
TOPIC_EXT_DEPOSIT_CANCELLED       = '\xfedcf703cd64f014753705fc7938733fae807da28706e8e523d1e60db0ee610a'
TOPIC_EXT_WITHDRAWAL              = '\x22064fc128e6deeb077304674fa3e066ee0424d8858be90279228cce94ea199e'
TOPIC_EXT_LIQUIDATION             = '\x74cd4e944568075ed9b5a8c3db1109c32cced5a5008cc0fd15301fbfb7a98489'
TOPIC_EXT_POSITION_CREATED        = '\x60ac5b1ee505d9f300b7566f6d3629cd12cd62dd34469f69e5eef2d1c6d737fe'
TOPIC_EXT_BATCH_SETTLED           = '\x27483f8a752384a9d1ce04a79c9e389bc65c5bd2aed37194d8fab79c7d19f0bd'
TOPIC_EXT_BRIDGE_ASSET_ROOT       = '\xfaaca86bc099cda634a771950e2274dcf9b6e76f88ae48cc16fb96b175898c10'
TOPIC_EXT_STATE_DIFF_POSTED       = '\x33b7d9fc4c4e3429b978557b0747997bee0bff3638f982f9330a743c0601fca7'
TOPIC_EXT_VAULT_SHARES_MINTED     = '\x3acf177ad277887f85e58e52169881507dd50097e12e3f7aa0726b585787548b'
TOPIC_EXT_VAULT_SHARES_BURNED     = '\x0a1ced31cf162d34de6c1ba8e712b6b23b829d16a86b84da235cc81e17d0814f'
TOPIC_EXT_CUSTODY_ACTIVATED       = '\x3058dfc2f461afbd1162821afb43d0eded77fc8c5a8cb1c32abcd69a268a9fb4'
TOPIC_EXT_BRIDGE_ASSET_CONFIGURED = '\x4702d4a842dc1f570feb7894f37e6c46544f80f842da8a87ab9526c1080b64a7'
TOPIC_EXT_BRIDGE_ASSET_PAUSED     = '\x480e808863529746f89169a187f622b1e572ebd6b7a403793955c8f6aff8478c'
TOPIC_EXT_MAX_DEPOSIT_UPDATED     = '\x1abb27c10d7691fde754b929520c8884218b08dd1a48bfef66ee47a6ab98c717'
TOPIC_EXT_TREASURY_DEPOSIT        = '\xedb91c7cfba21699815cdfbceeeff58063764ec530eb7dfb48aa060443ac0169'
TOPIC_EXT_TREASURY_WITHDRAWAL     = '\x2f2e6e3734b7f724088fe25c16f6ebd572e77abf7c0aef4bc7b56b5cfc20b276'
TOPIC_EXT_ADMIN_LIMIT_CHANGED     = '\xbcb6a2b7ca8ddda718dfe9d1c167beb4b43c9d8461da309122491f2161976b07'
TOPIC_EXT_ADMIN_LIMIT_RESET       = '\x588a96cb0331a8cf96597662d5b378ca2b32c0ddca45c2ddd6881d227bdc7f0f'
TOPIC_EXT_GATE_UPGRADE_SCHEDULED  = '\x52ca9d3c1c30859d0763c3664a6b7cdbe66172048385fe9b0010533932912b04'
TOPIC_EXT_GATE_UPGRADE_EXECUTED   = '\xf6224a998aea3de231cf75375faf8c3711379d54bb84c92ef9d9779dabd383a9'
TOPIC_PAUSED                      = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED                = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_DEFAULT_ADMIN_XFER_SCHED    = '\x3377dc44241e779dd06afab5b788a35ca5f3b778836e2990bdb26a2a4b2e5ed6'
TOPIC_RHINO_BRIDGED_DEPOSIT_ID    = '\x1655dc426ee0145d9436d28cfb463fb0e0717ae145566e5e534da64b735e49f3'
TOPIC_STARKEX_LOG_DEPOSIT         = '\x06724742ccc8c330a39a641ef02a0b419bd09248360680bb38159b0a8c2635d6'
TOPIC_STARKEX_WITHDRAWAL_ALLOWED  = '\x03c10a82c955f7bcd0c934147fb39cafca947a4294425b1751d884c8ac954287'
TOPIC_STARKEX_WITHDRAWAL_PERFORMED= '\xb7477a7b93b2addc5272bbd7ad0986ef1c0d0bd265f26c3dc4bbe42727c2ac0c'
TOPIC_STARKEX_USER_REGISTERED     = '\xcab1cf17c190e4e2195a7b8f7b362023246fa774390432b4704ab6b29d56b07b'
TOPIC_STARKEX_UPDATE_STATE        = '\x2672b53d25204094519f7b0fba8d2b5cd0cc1e426f49554c89461cdb9dcec08f'
TOPIC_STARKEX_FROZEN              = '\xf5b8e6419478ab140eb98026ab5bd607038cb0ac4d4dad5b1fc0848dfd203d1f'
TOPIC_STARKEX_IMPL_UPGRADED       = '\xff14288d542bc1c1d15a652cb52af735f065c0c9d70b48e454a203c260733544'
-- ===== Selectors (chain-agnostic) =====
SEL_EXT_DEPOSIT                   = '\x94d80a2b'
SEL_EXT_CANCEL_DEPOSIT            = '\x31404484'
SEL_EXT_REJECT_DEPOSIT            = '\x90276513'
SEL_EXT_SETTLE                    = '\x0a0ba0c1'
SEL_EXT_POST_STATE_DIFF           = '\x40f40ded'
SEL_EXT_SET_ASSET_PAUSED          = '\x6c4fefed'
SEL_EXT_SET_MAX_DEPOSIT           = '\xae54c198'
SEL_EXT_TREASURY_WITHDRAW_FROM    = '\x9470b0bd'
SEL_EXT_TREASURY_DEPOSIT_INTO     = '\x3fdd49fa'
SEL_EXT_CHANGE_PROTECTION_LIMIT   = '\x56bc3952'
SEL_EXT_RESET_PROTECTION_LIMIT    = '\x37c9168a'
SEL_UPGRADE_TO_AND_CALL           = '\x4f1ef286'
SEL_GRANT_ROLE                    = '\x2f2ff15d'
SEL_STARKEX_ESCAPE                = '\x366a2670'
SEL_STARKEX_WITHDRAW              = '\x441a3e70'
SEL_STARKEX_REGISTER_ETH_ADDRESS  = '\xbea84187'
-- ===== Addresses (network-specific) =====
ARC_EXT_PERP_SETTLEMENT           = '\x4445aacacc2de174b77b37eb27529ce0b36bc580'
ARC_EXT_PERP_SETTLEMENT_IMPL      = '\x93dfdeb3dec38c52c1635b8f288a1455710781d4'
ARC_EXT_MSCA_TREASURY             = '\x8cd3267de1177d1dfd940f502a5ce682420cc660'
ARC_EXT_CUSTODY_ACCOUNT           = '\x89103959eef431bea308027b8a5073c5ddc867a2'
ARC_EXT_TREASURY_UPGRADE_GATE     = '\x686b940fd1d2943b3b8fe90027ef014fe2751a0d'
ARC_EXT_XVS                       = '\x0bcedc69a801ebf2b9cd3da5dc64ba03f01a3fcb'
ARC_EXT_SP1_VERIFIER              = '\x6a1866bc78275c3dcd4d6ea087ad2204d3cb734a'
ARC_EXT_SETTLER_EOA               = '\x05193432bcc9e2bad28b7c6355b8f3c9f52d4dc6'
ARC_EXT_ADMIN_EOA                 = '\xc3323f7803149a5a055723b41bf670ef8920317e'
ARC_EXT_TREASURY_ADMIN_EOA        = '\xb87d482d9e84d07c1d6a26bb89d504de2912cb87'
ARC_RHINO_BRIDGE                  = '\x5e023c31e1d3dcd08a1b3e8c96f6ef8aa8fcacd1'
ETH_EXT_STARKEX_LEGACY            = '\x1ce5d7f52a8abd23551e91248151ca5a13353c65'
```

## 10. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify ABIs of `PerpSettlement` (`0x93df…81d4`), `MscaTreasury` (`0xf640…448a`, incl. `TreasuryUpgradeGate` source) and `VaultShareToken`. Twelve settlement/treasury topics were seen in live Arc logs (counts in §1). StarkEx topics were matched against live Ethereum logs. `LogUserRegistered`, `escape(uint256,uint256,uint256)` and `freezeRequest(uint256,uint256,uint256)` were matched to live transactions and to the openchain.xyz signature database.
- **Addresses:** the settlement address is from the official docs and DefiLlama. Treasury, custody, gate, verifier, Rhino.fi bridge and XVS were read from on-chain getters (`treasury()`, `custodyAccount()`, `upgradeGate()`, `verifier()`, `rhinoBridge()`, `bridgeAssets(346)`). Role holders came from the deployment `RoleGranted` logs and `hasRole` calls. Deployment and upgrade blocks came from binary search on `eth_getCode`, the impl slot and `custodyActive()` over archive state.
- **Payout path:** one `settle` receipt shows custody → settlement → Rhino.fi `BridgedDepositWithId` with the same `commitmentId` as `Withdrawal`.
- **Chain coverage:** batched `eth_getCode` on all nine target chains for every address in §3–§4.

Authoritative sources:
- [Extended docs — Technical Architecture](https://docs.extended.exchange/about-extended/technical-architecture) · [Migration from Starknet to Arc](https://docs.extended.exchange/about-extended/migration-from-starknet-to-arc) · [Deposits and Withdrawals](https://docs.extended.exchange/extended-resources/account-operations/deposits-and-withdrawals) · [Vault](https://docs.extended.exchange/extended-resources/vault)
- [Sourcify — Arc (5042) verified sources](https://sourcify.dev/) · [Blockscout Ethereum — StarkPerpetual](https://eth.blockscout.com/address/0x1cE5D7f52A8aBd23551e91248151CA5A13353C65)
- [DefiLlama-Adapters `registries/sumTokens/data1.js` (`extended`)](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/registries/sumTokens/data1.js)
- [Crypto Briefing — Extended migrates settlement to Arc](https://cryptobriefing.com/extended-migrates-settlement-starknet-to-arc/)
- Explorers: [explorer.arc.io](https://explorer.arc.io/address/0x4445AACaCC2dE174B77b37Eb27529ce0B36bC580) · [Etherscan](https://etherscan.io/address/0x1cE5D7f52A8aBd23551e91248151CA5A13353C65)
