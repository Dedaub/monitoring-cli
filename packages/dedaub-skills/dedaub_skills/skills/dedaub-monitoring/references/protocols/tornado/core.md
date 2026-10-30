# Tornado Cash (Classic) — Topics, Selectors, Addresses (Ethereum, BNB, Polygon, Arbitrum, Optimism, Avalanche, Base)

**Status:** verified against live RPC on every listed chain and the canonical `tornadocash/tornado-core`, `tornado-anonymity-mining`, `tornado-governance` and `tornado-classic-ui` repos on 2026-10-30.
**Scope:** Tornado Cash Classic: the fixed-denomination mixer instances, the routers (TornadoRouter on Ethereum, TornadoProxyLight elsewhere), the Instance Registry, the Relayer Registry, governance (TORN, Governance, staking) and the note Echoer.
Chains: Ethereum (1), BNB (56), Polygon (137), Arbitrum (42161), Optimism (10), Avalanche (43114), Base (8453, unused copy).
Topics and selectors are chain-agnostic. Addresses are network-specific.

A Tornado instance is a fixed-denomination pool. A deposit stores a Poseidon/MiMC commitment in a Merkle tree. A withdrawal proves membership with a zk-SNARK and spends a nullifier. The link between deposit and withdrawal is hidden on purpose.
The instances are immutable. They have no proxy and no admin (`operator()` is `0x0` on Ethereum; the non-Ethereum instances have no `operator` function).
On Ethereum, the router, the registries, the fee manager, staking and governance are upgradeable proxies that TORN governance controls.

**Sanctions:** OFAC added Tornado Cash to the SDN list on 2022-08-08. OFAC removed Tornado Cash and its Ethereum addresses from the SDN list on 2025-03-21, after the Fifth Circuit ruling in *Van Loon v. Department of the Treasury*.

The non-obvious facts for an indexer:
- The `Deposit` event has **no depositor address**. Use `tx.from`, the router `EncryptedNote.sender`, or the ERC-20 `Transfer` into the instance.
- The `Withdrawal` event has the **recipient in data** (`to`, not indexed) and the **relayer indexed**.
- Third-party clones emit the same `Deposit`/`Withdrawal` topic0 values. Always filter by the instance addresses in this file.

---

## 0. Contract families

| Component | Role | Upgradeable |
|-----------|------|-------------|
| **Instance** (ETH or ERC-20) | Holds funds of one denomination. Emits `Deposit` and `Withdrawal` | No |
| **TornadoRouter** (Ethereum) | Entry point for UI deposits and relayed withdrawals. Emits `EncryptedNote`. Calls RelayerRegistry `burn` on relayed withdrawals | No (plain contract) |
| **TornadoProxyLight** (other chains) | Router without registries. Emits `EncryptedNote` | No |
| **InstanceRegistry** (Ethereum) | List of allowed instances and their state and protocol fee | EIP-1967, admin = Governance |
| **RelayerRegistry** (Ethereum) | Relayer registration, TORN stake, stake burn per relayed withdrawal | EIP-1967, admin = Governance |
| **FeeManager** (Ethereum) | Computes per-instance relayer fee (stake burn) from Uniswap TWAPs | EIP-1967, admin = Governance |
| **TornadoStakingRewards** (Ethereum) | Distributes burned relayer stake to locked-TORN holders | EIP-1967, admin = Governance |
| **Governance** (Ethereum) | TORN lock, proposals, votes; admin of all Tornado proxies | Self-administered proxy |
| **TORN** | Governance token | No |
| **Echoer** | Stores encrypted note-account backups (`Echo` events) | No |
| Anonymity mining (Miner, TornadoTrees, RewardSwap) | Ended AP/TORN mining program | Mixed; inactive |

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Instance (every chain)

| topic0 | Event |
|--------|-------|
| `0xa945e51eec50ab98c161376f0db4cf2aeba3ec92755fe2fcd388bdbbb80ff196` | `Deposit(bytes32 indexed commitment, uint32 leafIndex, uint256 timestamp)` |
| `0xe9e508bad6d4c3227e881ca19068f099da81b5164dd6d62b2eaf1e8bc6c34931` | `Withdrawal(address to, bytes32 nullifierHash, address indexed relayer, uint256 fee)` |

### 1.2 Routers, registries, Echoer

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xfa28df43db3553771f7209dcef046f3bdfea15870ab625dcda30ac58b82b4008` | `EncryptedNote(address indexed sender, bytes encryptedNote)` | TornadoRouter, TornadoProxyLight, old TornadoProxy v1/v2 |
| `0x02826f62d88a4d9f1978eb9c06f8663f642d032908e65a915d5898f3585421c0` | `InstanceStateUpdated(address indexed instance, uint8 state)` | InstanceRegistry; old TornadoProxy v2. State: 0 DISABLED, 1 ENABLED, 2 MINEABLE |
| `0x94df8c3a8087dce110e5fbc5acf380c83c94bbd31b2c8ed4c08e1396a696e1a8` | `RouterRegistered(address tornadoRouter)` | InstanceRegistry, RelayerRegistry |
| `0x6f0eaf2c2f89fb4cfe96a1dee5e764d60b52c7f48aaa590f0850e308aa1b953a` | `FeeUpdated(address indexed instance, uint256 newFee)` | FeeManager |
| `0x50d6f3fc915efd1695d8a4cb50da185984f50d256834b9cb308295eb3c872c9c` | `Echo(address indexed who, bytes data)` | Echoer |

### 1.3 RelayerRegistry (Ethereum; no indexed fields)

| topic0 | Event |
|--------|-------|
| `0x9ca7c9c762eff27b021608f232b4c4b8f9b8bf9a3d322297e47cc4209a67d5e2` | `RelayerRegistered(bytes32 relayer, string ensName, address relayerAddress, uint256 stakedAmount)` |
| `0x659f33fc6677bebf3a9bf3101092792e31f35766d0358e54577bdd91a655f6a0` | `StakeBurned(address relayer, uint256 amountBurned)` — one per relayed withdrawal through the router |
| `0x1275dbe2a271b2b822e60f1d44894fa5fb337e7e2dc6a200205b1a5b17c07d64` | `StakeAddedToRelayer(address relayer, uint256 amountStakeAdded)` |
| `0xcde75bd02c5f739608c891bcd9aa6809e6c4a7035ac7b9f3fd5fea756db74724` | `WorkerRegistered(address relayer, address worker)` |
| `0xb2a8e18b9e887f502d65c1683e60b723fa582a6903ea4e8eb23907a19c1ce8a0` | `WorkerUnregistered(address relayer, address worker)` |
| `0xafa759fb3c68e89eaaba359f0930ab40c24875b73cc9e2f6a38b0180019eb8f3` | `RelayerBalanceNullified(address relayer)` |
| `0x404663163d528ec45288abc4389b81bd96fabf858ff57577ebd4ee7f15d7b0a6` | `MinimumStakeAmount(uint256 minStakeAmount)` |

### 1.4 Governance, staking, TORN (Ethereum)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x90ec05050aa23d54ba425e926fe646c318e85825bc400b13a46010abe86eb2f0` | `ProposalCreated(uint256 indexed id, address indexed proposer, address target, uint256 startTime, uint256 endTime, string description)` | Governance |
| `0x7c2de587c00d75474a0c6c6fa96fd3b45dc974cd4e8a75f712bb84c950dce1b5` | `Voted(uint256 indexed proposalId, address indexed voter, bool indexed support, uint256 votes)` | Governance |
| `0x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f` | `ProposalExecuted(uint256 indexed proposalId)` | Governance — **watch: executes arbitrary code as admin of every proxy** |
| `0x4bc154dd35d6a5cb9206482ecb473cdbf2473006d6bce728b9cc0741bcc59ea2` | `Delegated(address indexed account, address indexed to)` | Governance |
| `0x1af5b1c85495b3618ea659a1ba256c8b8974b437297d3b914e321e086a28da72` | `Undelegated(address indexed account, address indexed from)` | Governance |
| `0x9b227b0c1ae308b34f72d4fdf9a1943fa769ff4814933595e7bc5230a117698b` | `RewardUpdateSuccessful(address indexed account)` | Governance |
| `0x5a6216e80d86159dc87dcebfe519205477a94005b7d9d6bd313606450a5344f6` | `RewardUpdateFailed(address indexed account, bytes indexed errorData)` | Governance |
| `0x39fe62076cf7adf3c60e355a2da5a4f17a958ca319e8eba385a6c09a8b649016` | `RewardsUpdated(address indexed account, uint256 rewards)` | TornadoStakingRewards |
| `0xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe` | `RewardsClaimed(address indexed account, uint256 rewardsClaimed)` | TornadoStakingRewards |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every EIP-1967 proxy above |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | TORN; ERC-20 deposits/withdrawals |

### 1.5 Anonymity mining (ended)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xbd4a5ca11c6f082fd6d00dc9d1dced6ab22490039bc36154bfa748bf2bf74355` | `NewAccount(bytes32 commitment, bytes32 nullifier, bytes encryptedAccount, uint256 index)` | Miner |
| `0x77f92a1b6a1a11de8ca49515ad4c1fad45632dd3442167d74b90b304a3c7a758` | `Swap(address indexed recipient, uint256 pTORN, uint256 TORN)` | RewardSwap (collides with other `Swap(address,uint256,uint256)` emitters) |
| `0xd5ef75672982cb39cc849450302ce426d1655271003cae8a66cb533c12f86ecc` | `TornadoTreesUpdated(address addr)` | old TornadoProxy v2 |

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Instance

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb214faa5` | `deposit(bytes32)` | payable for ETH instances. `_commitment` |
| `0x21a0adb6` | `withdraw(bytes,bytes32,bytes32,address,address,uint256,uint256)` | `(_proof, _root, _nullifierHash, _recipient, _relayer, _fee, _refund)` |
| `0x8bca6d16` | `denomination()` | view. Use it to identify the pool size |
| `0xfc0c546a` | `token()` | view. ERC-20 instances only |
| `0xe5285dcc` | `isSpent(bytes32)` | view. Nullifier check |
| `0x17cc915c` | `nullifierHashes(bytes32)` | view |
| `0x839df945` | `commitments(bytes32)` | view |
| `0xfc7e9c6f` | `nextIndex()` | view. Total deposits to date |
| `0xba70f757` / `0x6d9833e3` | `getLastRoot()` / `isKnownRoot(bytes32)` | view |

### 2.2 TornadoRouter / TornadoProxyLight

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x13d98d13` | `deposit(address,bytes32,bytes)` | payable. `(_tornado, _commitment, _encryptedNote)`. Emits `EncryptedNote` |
| `0xb438689f` | `withdraw(address,bytes,bytes32,bytes32,address,address,uint256,uint256)` | payable. `(_tornado, _proof, _root, _nullifierHash, _recipient, _relayer, _fee, _refund)` |
| `0x6485ba2a` | `backupNotes(bytes[])` | Emits `EncryptedNote` |

### 2.3 RelayerRegistry

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe43fdb3c` | `register(string,uint256,address[])` | `(ensName, stake, workers)` |
| `0xe37e8bcc` | `registerPermit(string,uint256,address[],address,uint256,uint8,bytes32,bytes32)` | |
| `0x2e650649` / `0x3523dc85` | `registerWorker(address,address)` / `unregisterWorker(address)` | |
| `0xd990231d` | `stakeToRelayer(address,uint256)` | |
| `0x85a29683` | `stakeToRelayerPermit(address,uint256,address,uint256,uint8,bytes32,bytes32)` | |
| `0x45a11cec` | `burn(address,address,address)` | Router-only. `(sender, relayer, pool)` |
| `0x4d4efd04` | `nullifyBalance(address)` | Governance-only |
| `0xeb4af045` | `setMinStakeAmount(uint256)` | Governance-only |
| `0xb971a6bf` / `0x541d5548` / `0xb69fd4ab` | `getRelayerBalance(address)` / `isRelayer(address)` / `isRelayerRegistered(address,address)` | view |

### 2.4 Governance, staking, registries

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd6f0948c` | `propose(address,string)` | `target` is a proposal contract run by `delegatecall` on execute |
| `0x15373e3d` | `castVote(uint256,bool)` | |
| `0xb859f11b` | `castDelegatedVote(address[],uint256,bool)` | |
| `0xfe0d94c1` | `execute(uint256)` | |
| `0xf0b76892` / `0xb54426c8` | `lock(address,uint256,uint256,uint8,bytes32,bytes32)` / `lockWithApproval(uint256)` | Lock TORN for votes |
| `0x6198e339` | `unlock(uint256)` | |
| `0x5c19a95c` / `0x92ab89bb` | `delegate(address)` / `undelegate()` | |
| `0xda35c664` / `0x3e4f49e6` / `0x9ae697bf` | `proposalCount()` / `state(uint256)` / `lockedBalance(address)` | view |
| `0x3d18b912` | `getReward()` | TornadoStakingRewards |
| `0x10c13ac3` | `getAllInstanceAddresses()` | InstanceRegistry view |
| `0x032bb443` | `instances(address)` | InstanceRegistry view → `(isERC20, token, state, uniswapPoolSwappingFee, protocolFeePercentage)` |
| `0x9e0505fc` / `0xcf552c89` | `updateInstance((bool,address,uint8,uint32,uint32,address))` / `removeInstance(uint256)` | InstanceRegistry, Governance-only. Selector derived from the struct layout; not seen in bytecode |
| `0xf522d6d6` / `0x80eb7bf0` | `updateAllFees()` / `updateFee(address)` | FeeManager. Permissionless |
| `0x624fbfdc` | `echo(bytes)` | Echoer |

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `ethereum-rpc.publicnode.com` on 2026-10-30.

### 3.1 Instances in the InstanceRegistry (state ENABLED)

The list comes from `InstanceRegistry.getAllInstanceAddresses()` (19 instances). `nextIndex` = deposits to date on 2026-10-30.

| Token | Denomination | Address | nextIndex |
|-------|-------------|---------|-----------|
| ETH | 0.1 | `0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc` | 75,643 |
| ETH | 1 | `0x47CE0C6eD5B0Ce3d3A51fdb1C52DC66a7c3c2936` | 96,793 |
| ETH | 10 | `0x910Cbd523D972eb0a6f4cAe4618aD62622b39DbF` | 79,056 |
| ETH | 100 | `0xA160cdAB225685dA1d56aa342Ad8841c3b53f291` | 49,783 |
| DAI | 100 | `0xD4B88Df4D29F5CedD6857912842cff3b20C8Cfa3` | 477 |
| DAI | 1,000 | `0xFD8610d20aA15b7B2E3Be39B396a1bC3516c7144` | 1,379 |
| DAI | 10,000 | `0x07687e702b410Fa43f4cB4Af7FA097918ffD2730` | 3,446 |
| DAI | 100,000 | `0x23773E65ed146A459791799d01336DB287f25334` | 4,402 |
| cDAI | 5,000 | `0x22aaA7720ddd5388A3c0A3333430953C68f1849b` | 5 |
| cDAI | 50,000 | `0x03893a7c7463AE47D46bc7f091665f1893656003` | 118 |
| cDAI | 500,000 | `0x2717c5e28cf931547B621a5dddb772Ab6A35B701` | 87 |
| cDAI | 5,000,000 | `0xD21be7248e0197Ee08E0c20D4a96DEBdaC3D20Af` | 114 |
| USDC | 100 | `0xd96f2B1c14Db8458374d9Aca76E26c3D18364307` | 397 |
| USDC | 1,000 | `0x4736dCf1b7A3d580672CcE6E7c65cd5cc9cFBa9D` | 934 |
| USDT | 100 | `0x169AD27A470D064DEDE56a2D3ff727986b15D52B` | 991 |
| USDT | 1,000 | `0x0836222F2B2B24A3F36f98668Ed8F0B38D1a872f` | 2,134 |
| WBTC | 0.1 | `0x178169B423a011fff22B9e3F3abeA13414dDD0F1` | 156 |
| WBTC | 1 | `0x610B717796ad172B316836AC95a2ffad065CeaB4` | 1,042 |
| WBTC | 10 | `0xbB93e510BbCD0B7beb5A853875f9eC60275CF498` | 1,202 |

Tokens: DAI `0x6B175474E89094C44Da98b954EedeAC495271d0F`, cDAI `0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643`, USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`, USDT `0xdAC17F958D2ee523a2206206994597C13D831ec7`, WBTC `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599`.

### 3.2 Legacy ERC-20 instances (not in the registry)

Same instance code (5,999 B), same events. `denomination()` and `token()` read live. Use is near zero (0–6 deposits each).

| Token | Denomination | Address |
|-------|-------------|---------|
| USDC | 10,000 | `0xD691F27f38B395864Ea86CfC7253969B409c362d` |
| USDT | 10,000 | `0xF67721A2D8F736E75a49FdD7FAd2e31D8676542a` |
| USDT | 100,000 | `0x9AD122c22B14202B4490eDAf288FDb3C7cb3ff5E` |
| cUSDC | 5,000 | `0xaEaaC358560e11f52454D997AAFF2c5731B6f8a6` |
| cUSDC | 50,000 | `0x1356c899D8C9467C7f71C195612F8A395aBf2f0a` |
| cUSDC | 500,000 | `0xA60C772958a3eD56c1F15dD055bA37AC8e523a0D` |
| cDAI | 50,000 | `0xBA214C1c1928a32Bffe790263E38B4Af9bFCD659` |
| cDAI | 500,000 | `0xb1C8094B234DcE6e03f10a5b673c1d8C69739A00` |

### 3.3 Router, registries, governance

| Role | Address | One-liner |
|------|---------|-----------|
| **TornadoRouter** | `0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b` | Current router. `instanceRegistry()` and `relayerRegistry()` read live |
| **InstanceRegistry** | `0xB20c66C4DE72433F3cE747b58B86830c459CA911` | Proxy, impl `0x2573bac39ebe2901b4389cd468f2872cf7767faf` |
| **RelayerRegistry** | `0x58E8dCC13BE9780fC42E8723D8EaD4CF46943dF2` | Proxy, impl `0x84b0c75c1f6211450fec7289c32d717adadd702a` |
| **FeeManager** | `0x5f6c97C6AD7bdd0AE7E0Dd4ca33A4ED3fDabD4D7` | Proxy, impl `0xf4b067dd14e95bab89be928c07cb22e3c94e0daa` |
| **TornadoStakingRewards (live)** | `0x5B3f656C80E8ddb9ec01Dd9018815576E9238c29` | Proxy, impl `0x9c97be37840f0e754bb7adb1b16fd0954a2ba248`. Returned by `Governance.Staking()`. Emits `RewardsUpdated`/`RewardsClaimed` |
| TornadoStakingRewards (old) | `0x2FC93484614a34f26F7970CBB94615bA109BB4bf` | Proxy, impl `0x26903a5a198d571422b2b4ea08b56a37cbd68c89`. No events in the last 300k blocks |
| **Governance** | `0x5efda50f22d34F262c29268506C5Fa42cB56A1Ce` | Self-administered proxy, impl `0xbf46f2222c0712caf2f13b8590732dbd964ce395`. 72 proposals on 2026-10-30 |
| Governance user vault | `0x2F50508a8a3D323B91336FA3eA6ae50E55f32185` | Holds locked TORN (`Governance.userVault()`) |
| Governance gas-compensation vault | `0xFA4C1f3f7D5dd7c12a9Adb82Cd7dDA542E3d59ef` | `Governance.gasCompensationVault()` |
| **TORN** | `0x77777FeDdddFfC19Ff86DB637967013e6C6A116C` | Governance token |
| Echoer | `0x9B27DD5Bb15d42DC224FCD0B7caEbBe16161Df42` | Note-account backups |
| Aggregator | `0xE8F47A78A6D52D317D0D2FFFac56739fE14D1b49` | UI read helper (relayer data) |
| TornadoProxyLight copy | `0x0D5550d52428E7e3175bfc9550207e4ad3859b17` | Same code as on other chains; not used by the Ethereum UI |
| Old TornadoProxy v2 | `0x722122dF12D4e14e13Ac3b6895a86e84145b6967` | Router before TornadoRouter (emits `EncryptedNote`, `InstanceStateUpdated`) |
| Old TornadoProxy v1 | `0x905b63Fff465B9fFBF41DeA908CEb12478ec7601` | First router |
| Miner / TornadoTrees / RewardSwap | `0x746Aebc06D2aE31B71ac51429A19D54E797878E9` / `0x527653eA119F3E6a1F5BD18fbF4714081D7B31ce` / `0x5cab7692D4E94096462119ab7bF57319726Eed2A` | Anonymity mining (ended). TornadoTrees is a proxy (impl `0x200a79068d8141924b511bc78cb55dca89cf5c2e`) |

## 4. Addresses — other chains

On BNB, Polygon, Arbitrum, Optimism, Avalanche and Base the instances share addresses (same deployer and nonces). The code is the same 5,072 B on every chain. Native coin only (no ERC-20 instances).
Each chain uses **TornadoProxyLight** `0x0D5550d52428E7e3175bfc9550207e4ad3859b17` (1,270 B) and the Echoer `0xa75BF2815618872f155b7C4B0C81bF990f5245E4` (326 B). There is no registry, relayer registry or governance outside Ethereum.

| Address | BNB (56) | Polygon (137) | Arbitrum (42161) | Optimism (10) | Avalanche (43114) | Base (8453) |
|---------|----------|---------------|------------------|---------------|-------------------|-------------|
| `0x84443CFd09A48AF6eF360C6976C5392aC5023a1F` | 0.1 BNB | — | 0.1 ETH | 0.1 ETH | — | 0.1 ETH (code only) |
| `0xd47438C816c9E7f2E2888E060936a499Af9582b3` | 1 BNB | — | 1 ETH | 1 ETH | — | 1 ETH (code only) |
| `0x330bdFADE01eE9bF63C209Ee33102DD334618e0a` | 10 BNB | — | 10 ETH | 10 ETH | 10 AVAX | 10 ETH (code only) |
| `0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD` | 100 BNB | 100 POL | 100 ETH | 100 ETH | 100 AVAX | 100 ETH (code only) |
| `0xdf231d99Ff8b6c6CBF4E9B9a945CBAcEF9339178` | — | 1,000 POL | — | — | — | — |
| `0xaf4c0B70B2Ea9FB7487C7CbB37aDa259579fe040` | — | 10,000 POL | — | — | — | — |
| `0xa5C2254e4253490C54cef0a4347fddb8f75A4998` | — | 100,000 POL | — | — | — | — |
| `0xaf8d1839c3c67cf571aa74B5c12398d4901147B3` | — | — | — | — | 500 AVAX | — |

Use on 2026-10-30 (`nextIndex` / balance):
- BNB: 88,633 / 105,785 / 68,248 / 19,700 deposits; balances 502.5 / 2,098 / 6,930 / 68,200 BNB. Active (deposits and withdrawals in the last 100k blocks).
- Polygon: 12,237 / 6,951 / 1,247 / 32 deposits.
- Arbitrum: 3,184 / 2,716 / 729 / 183 deposits.
- Optimism: 801 / 280 / 2 / 0 deposits.
- Avalanche: 4,675 / 2,084 / 366 deposits.
- **Base:** the code exists, but the official UI config lists no Base network. The 0.1 ETH pool has 1 deposit and all four pools hold 0 ETH. No logs in the last 500k blocks.

The `denomination()` value is in the native coin's 18 decimals.

## 5. Cross-chain summary

| Chain (ID) | Instances | Router | Registries / governance |
|------------|-----------|--------|-------------------------|
| Ethereum (1) | 19 ENABLED + 8 legacy | TornadoRouter `0xd90e…F31b` | ✓ |
| BNB (56) | 4 (BNB) | ProxyLight `0x0D55…9b17` | — |
| Polygon (137) | 4 (POL) | ProxyLight | — |
| Arbitrum (42161) | 4 (ETH) | ProxyLight | — |
| Optimism (10) | 4 (ETH) | ProxyLight | — |
| Avalanche (43114) | 3 (AVAX) | ProxyLight | — |
| Base (8453) | 4 (ETH), unused | ProxyLight (code only) | — |
| Robinhood (4663) | — | — | — (instance, router, registry and TORN addresses return `0x`) |
| Arc (5042) | — | — | — (same check) |

Non-target: Gnosis (100) has xDAI instances at the Polygon addresses. Tornado Nova (variable-amount pool) lives on Gnosis only.

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Instances (all chains) | immutable | impl slot 0; ETH `operator()` = 0 | none |
| TornadoRouter, TornadoProxyLight, Echoer, TORN | immutable | impl slot 0 | none (a new router needs governance to re-register it) |
| InstanceRegistry, RelayerRegistry, FeeManager, TornadoStakingRewards (both), TornadoTrees | EIP-1967 transparent | impl slot non-zero (§3.3) | admin slot = Governance `0x5efda50f…A1Ce` |
| Governance | self-administered EIP-1967 proxy | admin slot = its own address | a passed proposal |

Watch `Upgraded(address)` (`0xbc7cd75a…2d3b`) on every proxy and `ProposalExecuted` on Governance. A proposal runs with `delegatecall` in Governance context, so it can change any proxy.

## 7. Detection invariants & gotchas

1. **Depositor is not in the log.** `Deposit` has only `commitment`, `leafIndex`, `timestamp`. Take the depositor from `tx.from`, from the router `EncryptedNote.sender` in the same transaction, or from the ERC-20 `Transfer(from → instance)`.
2. **Withdrawal recipient is not indexed.** `to` is in data word 0. `relayer` is topic1. `fee` goes to the relayer. A self-withdrawal has `relayer = 0x0` and `fee = 0`.
3. **Amount comes from the pool, not the event.** Neither event carries the amount. Map the emitter to its denomination (§3–§4) or call `denomination()`.
4. **Exploit-fund tracing:** a burst of `Deposit` logs on the 100 ETH / 10 ETH (or 100 BNB) pools whose `tx.from` is a flagged address is the classic signal. Query by emitter in §3.1 and §4, then join `tx.from`.
5. **Clones share topic0.** Non-official contracts with the same `Deposit` topic0 are active on Ethereum (for example 0.01 ETH and 0.03 ETH pools at `0x199112eb…b41c` and `0x398971a7…8fd4`, 10,384 B code, not in the registry). Filter by the addresses here.
6. **Router vs direct.** Deposits and withdrawals can call the instance directly. The router adds `EncryptedNote` (deposit) and `StakeBurned` (relayed withdrawal on Ethereum). Do not require router events.
7. **Same address, different chains.** `0x1E34A778…95DD` is 100 BNB on BNB, 100 ETH on Arbitrum/Optimism/Base, 100 POL on Polygon and 100 AVAX on Avalanche. Always key on (chain, address).
8. **Base copies are not in the official UI.** They hold no funds. Treat any Base activity as unusual.
9. **Governance risk.** Governance can replace the registries, fee logic and staking. In May 2023 an attacker passed a malicious proposal and took over Governance for a time. Alert on `ProposalCreated`, `ProposalExecuted` and `Upgraded`.
10. **Two staking contracts.** The live TornadoStakingRewards is `0x5B3f…8c29` (from `Governance.Staking()`). The UI config still names the older `0x2FC9…B4bf`.
11. **`Swap(address,uint256,uint256)`** of RewardSwap collides with many unrelated contracts. Filter by emitter.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TC_DEPOSIT                 = '\xa945e51eec50ab98c161376f0db4cf2aeba3ec92755fe2fcd388bdbbb80ff196'
TOPIC_TC_WITHDRAWAL              = '\xe9e508bad6d4c3227e881ca19068f099da81b5164dd6d62b2eaf1e8bc6c34931'
TOPIC_TC_ENCRYPTED_NOTE          = '\xfa28df43db3553771f7209dcef046f3bdfea15870ab625dcda30ac58b82b4008'
TOPIC_TC_INSTANCE_STATE_UPDATED  = '\x02826f62d88a4d9f1978eb9c06f8663f642d032908e65a915d5898f3585421c0'
TOPIC_TC_ROUTER_REGISTERED       = '\x94df8c3a8087dce110e5fbc5acf380c83c94bbd31b2c8ed4c08e1396a696e1a8'
TOPIC_TC_FEE_UPDATED             = '\x6f0eaf2c2f89fb4cfe96a1dee5e764d60b52c7f48aaa590f0850e308aa1b953a'
TOPIC_TC_ECHO                    = '\x50d6f3fc915efd1695d8a4cb50da185984f50d256834b9cb308295eb3c872c9c'
TOPIC_TC_RELAYER_REGISTERED      = '\x9ca7c9c762eff27b021608f232b4c4b8f9b8bf9a3d322297e47cc4209a67d5e2'
TOPIC_TC_STAKE_BURNED            = '\x659f33fc6677bebf3a9bf3101092792e31f35766d0358e54577bdd91a655f6a0'
TOPIC_TC_STAKE_ADDED             = '\x1275dbe2a271b2b822e60f1d44894fa5fb337e7e2dc6a200205b1a5b17c07d64'
TOPIC_TC_WORKER_REGISTERED       = '\xcde75bd02c5f739608c891bcd9aa6809e6c4a7035ac7b9f3fd5fea756db74724'
TOPIC_TC_RELAYER_NULLIFIED       = '\xafa759fb3c68e89eaaba359f0930ab40c24875b73cc9e2f6a38b0180019eb8f3'
TOPIC_TC_PROPOSAL_CREATED        = '\x90ec05050aa23d54ba425e926fe646c318e85825bc400b13a46010abe86eb2f0'
TOPIC_TC_VOTED                   = '\x7c2de587c00d75474a0c6c6fa96fd3b45dc974cd4e8a75f712bb84c950dce1b5'
TOPIC_TC_PROPOSAL_EXECUTED       = '\x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f'
TOPIC_TC_REWARDS_CLAIMED         = '\xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_TRANSFER                   = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- ===== Selectors (chain-agnostic) =====
SEL_TC_INSTANCE_DEPOSIT          = '\xb214faa5'
SEL_TC_INSTANCE_WITHDRAW         = '\x21a0adb6'
SEL_TC_ROUTER_DEPOSIT            = '\x13d98d13'
SEL_TC_ROUTER_WITHDRAW           = '\xb438689f'
SEL_TC_BACKUP_NOTES              = '\x6485ba2a'
SEL_TC_DENOMINATION              = '\x8bca6d16'
SEL_TC_RELAYER_REGISTER          = '\xe43fdb3c'
SEL_TC_RELAYER_BURN              = '\x45a11cec'
SEL_TC_GOV_PROPOSE               = '\xd6f0948c'
SEL_TC_GOV_EXECUTE               = '\xfe0d94c1'
SEL_TC_GOV_CAST_VOTE             = '\x15373e3d'
-- ===== Addresses: Ethereum =====
ETH_TC_ETH_0_1                   = '\x12d66f87a04a9e220743712ce6d9bb1b5616b8fc'
ETH_TC_ETH_1                     = '\x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936'
ETH_TC_ETH_10                    = '\x910cbd523d972eb0a6f4cae4618ad62622b39dbf'
ETH_TC_ETH_100                   = '\xa160cdab225685da1d56aa342ad8841c3b53f291'
ETH_TC_DAI_100                   = '\xd4b88df4d29f5cedd6857912842cff3b20c8cfa3'
ETH_TC_DAI_1000                  = '\xfd8610d20aa15b7b2e3be39b396a1bc3516c7144'
ETH_TC_DAI_10000                 = '\x07687e702b410fa43f4cb4af7fa097918ffd2730'
ETH_TC_DAI_100000                = '\x23773e65ed146a459791799d01336db287f25334'
ETH_TC_CDAI_5000                 = '\x22aaa7720ddd5388a3c0a3333430953c68f1849b'
ETH_TC_CDAI_50000                = '\x03893a7c7463ae47d46bc7f091665f1893656003'
ETH_TC_CDAI_500000               = '\x2717c5e28cf931547b621a5dddb772ab6a35b701'
ETH_TC_CDAI_5000000              = '\xd21be7248e0197ee08e0c20d4a96debdac3d20af'
ETH_TC_USDC_100                  = '\xd96f2b1c14db8458374d9aca76e26c3d18364307'
ETH_TC_USDC_1000                 = '\x4736dcf1b7a3d580672cce6e7c65cd5cc9cfba9d'
ETH_TC_USDT_100                  = '\x169ad27a470d064dede56a2d3ff727986b15d52b'
ETH_TC_USDT_1000                 = '\x0836222f2b2b24a3f36f98668ed8f0b38d1a872f'
ETH_TC_WBTC_0_1                  = '\x178169b423a011fff22b9e3f3abea13414ddd0f1'
ETH_TC_WBTC_1                    = '\x610b717796ad172b316836ac95a2ffad065ceab4'
ETH_TC_WBTC_10                   = '\xbb93e510bbcd0b7beb5a853875f9ec60275cf498'
ETH_TC_LEGACY_USDC_10000         = '\xd691f27f38b395864ea86cfc7253969b409c362d'
ETH_TC_LEGACY_USDT_10000         = '\xf67721a2d8f736e75a49fdd7fad2e31d8676542a'
ETH_TC_LEGACY_USDT_100000        = '\x9ad122c22b14202b4490edaf288fdb3c7cb3ff5e'
ETH_TC_LEGACY_CUSDC_5000         = '\xaeaac358560e11f52454d997aaff2c5731b6f8a6'
ETH_TC_LEGACY_CUSDC_50000        = '\x1356c899d8c9467c7f71c195612f8a395abf2f0a'
ETH_TC_LEGACY_CUSDC_500000       = '\xa60c772958a3ed56c1f15dd055ba37ac8e523a0d'
ETH_TC_LEGACY_CDAI_50000         = '\xba214c1c1928a32bffe790263e38b4af9bfcd659'
ETH_TC_LEGACY_CDAI_500000        = '\xb1c8094b234dce6e03f10a5b673c1d8c69739a00'
ETH_TC_ROUTER                    = '\xd90e2f925da726b50c4ed8d0fb90ad053324f31b'
ETH_TC_PROXY_V2_OLD              = '\x722122df12d4e14e13ac3b6895a86e84145b6967'
ETH_TC_PROXY_V1_OLD              = '\x905b63fff465b9ffbf41dea908ceb12478ec7601'
ETH_TC_INSTANCE_REGISTRY         = '\xb20c66c4de72433f3ce747b58b86830c459ca911'
ETH_TC_RELAYER_REGISTRY          = '\x58e8dcc13be9780fc42e8723d8ead4cf46943df2'
ETH_TC_FEE_MANAGER               = '\x5f6c97c6ad7bdd0ae7e0dd4ca33a4ed3fdabd4d7'
ETH_TC_STAKING_REWARDS           = '\x5b3f656c80e8ddb9ec01dd9018815576e9238c29'
ETH_TC_GOVERNANCE                = '\x5efda50f22d34f262c29268506c5fa42cb56a1ce'
ETH_TC_GOV_VAULT                 = '\x2f50508a8a3d323b91336fa3ea6ae50e55f32185'
ETH_TORN                         = '\x77777feddddffc19ff86db637967013e6c6a116c'
ETH_TC_ECHOER                    = '\x9b27dd5bb15d42dc224fcd0b7caebbe16161df42'
-- ===== Addresses: BNB / Polygon / Arbitrum / Optimism / Avalanche / Base (shared) =====
L2_TC_PROXY_LIGHT                = '\x0d5550d52428e7e3175bfc9550207e4ad3859b17'
L2_TC_ECHOER                     = '\xa75bf2815618872f155b7c4b0c81bf990f5245e4'
-- 0.1 native: BNB, Arbitrum, Optimism (Base copy unused)
L2_TC_SLOT_0_1                   = '\x84443cfd09a48af6ef360c6976c5392ac5023a1f'
-- 1 native: BNB, Arbitrum, Optimism (Base copy unused)
L2_TC_SLOT_1                     = '\xd47438c816c9e7f2e2888e060936a499af9582b3'
-- 10 native: BNB, Arbitrum, Optimism, Avalanche (Base copy unused)
L2_TC_SLOT_10                    = '\x330bdfade01ee9bf63c209ee33102dd334618e0a'
-- 100 native: BNB, Arbitrum, Optimism, Avalanche, Polygon (Base copy unused)
L2_TC_SLOT_100                   = '\x1e34a77868e19a6647b1f2f47b51ed72dede95dd'
POLY_TC_1000                     = '\xdf231d99ff8b6c6cbf4e9b9a945cbacef9339178'
POLY_TC_10000                    = '\xaf4c0b70b2ea9fb7487c7cbb37ada259579fe040'
POLY_TC_100000                   = '\xa5c2254e4253490c54cef0a4347fddb8f75a4998'
AVAX_TC_500                      = '\xaf8d1839c3c67cf571aa74b5c12398d4901147b3'
```

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `tornado-core` (`Tornado.sol`), `tornado-anonymity-mining` (`TornadoProxy.sol`, `TornadoProxyLight.sol`, `Echoer.sol`, `Miner.sol`, `RewardSwap.sol`), `tornado-governance` and the ABIs in `tornado-classic-ui/abis`.
  Each topic0 and selector was found as a constant in the deployed bytecode of its emitter or its current implementation (instance, router, ProxyLight, InstanceRegistry, RelayerRegistry, FeeManager, staking, Governance, Echoer, TORN, Miner, RewardSwap).
  Live `eth_getLogs` (Ethereum blocks 26.01M–26.31M) returned `Deposit`, `Withdrawal`, `EncryptedNote`, `StakeBurned`, `StakeAddedToRelayer`, `RelayerRegistered`, `WorkerRegistered`, `ProposalCreated`, `Voted`, `ProposalExecuted`, `RewardUpdateSuccessful`, `FeeUpdated`, `Echo`, `RewardsUpdated` and `RewardsClaimed`. On BNB, `Deposit`, `Withdrawal` and `EncryptedNote` occur in the last 100k blocks.
- **Addresses:** the Ethereum instance list was read live from `InstanceRegistry.getAllInstanceAddresses()` and matches `tornado-classic-ui/networkConfig.js`. Non-Ethereum instances come from the same config. Every address was existence-checked via `eth_getCode`, and every instance answered `denomination()`.
  Legacy instances were confirmed by `denomination()` + `token()` and the presence of the instance event constants in the bytecode. Registry state was read with `instances(address)`.
  Router wiring was read with `instanceRegistry()`, `relayerRegistry()` and `RelayerRegistry.tornadoRouter()`. Staking and vault addresses were read from `Governance.Staking()`, `userVault()` and `gasCompensationVault()`.
- **Proxies:** EIP-1967 implementation and admin slots read live.
- **Chain coverage:** the instance, ProxyLight and Echoer addresses were checked on all seven publicnode chains; code hashes are identical across chains. Base use was checked with `nextIndex()`, balances and 500k blocks of logs. Instance, router, registry, Governance and TORN addresses return `0x` on Robinhood Chain and Arc.
  Discovery of instances outside the known address list was possible only on Ethereum (topic-only `eth_getLogs`). The other public endpoints require an address filter, so unknown clones there were not searched.
- **Sanctions:** OFAC delisting on 2025-03-21 confirmed by multiple news reports and the Federal Register.

Authoritative sources:
- [tornadocash/tornado-core](https://github.com/tornadocash/tornado-core) — instance contract.
- [tornadocash/tornado-anonymity-mining](https://github.com/tornadocash/tornado-anonymity-mining) — TornadoProxy, ProxyLight, Echoer, Miner.
- [tornadocash/tornado-governance](https://github.com/tornadocash/tornado-governance)
- [tornadocash/tornado-classic-ui `networkConfig.js` and `abis/`](https://github.com/tornadocash/tornado-classic-ui)
- [Federal Register notice 2025-05096](https://public-inspection.federalregister.gov/2025-05096.pdf) · [The Block: Treasury removes Tornado Cash sanctions](https://www.theblock.co/post/347519/treasury-department-removes-economic-sanctions-against-crypto-mixer-tornado-cash)
- Explorers: [Etherscan](https://etherscan.io/address/0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b) · [BscScan](https://bscscan.com/address/0x0D5550d52428E7e3175bfc9550207e4ad3859b17) · [Polygonscan](https://polygonscan.com/address/0x0D5550d52428E7e3175bfc9550207e4ad3859b17) · [Arbiscan](https://arbiscan.io/address/0x0D5550d52428E7e3175bfc9550207e4ad3859b17) · [Optimistic Etherscan](https://optimistic.etherscan.io/address/0x0D5550d52428E7e3175bfc9550207e4ad3859b17) · [Snowtrace](https://snowtrace.io/address/0x0D5550d52428E7e3175bfc9550207e4ad3859b17)
