# Frax Ether (frxETH / sfrxETH) — Topics, Selectors, Addresses (Ethereum + 6 L2/alt-L1 bridged)

**Status:** verified against live RPC on every listed chain and the canonical `FraxFinance/frxETH-public` + `frax-solidity` repos and `docs.frax.finance` "frxETH and sfrxETH Token Addresses" on 2026-06-09. Every `topic0`/selector was recomputed locally as `keccak256(sig)`; the core staking topics were confirmed verbatim in live `eth_getLogs`; every address was existence-checked via `eth_getCode` and token identity confirmed via live `name()`/`symbol()`/`asset()` `eth_call`.

**Scope:** **frxETH liquid-staking line ONLY** — the two ERC-20s (`frxETH`, `sfrxETH`) and the `frxETHMinter`. This file does **not** cover the FRAX/frxUSD stablecoin, Fraxlend, or Fraxswap (the latter is a separate reference dir, [`../fraxswap/`](../fraxswap/v2.md)). **frxETH V2** (the validator-lending market) is **not** here either — it lives on **Fraxtal (chain 252, outside the 7 targets)**; see the V2 note at the end. Event `topic0`/function `selector` values are chain-agnostic; addresses are network-specific.

**What frxETH is.** Two-token liquid staking. Deposit ETH into `frxETHMinter` → mint **frxETH** 1:1. **frxETH is a plain, non-yield-bearing ETH-pegged ERC-20** — it does **not** rebase and does **not** accrue staking rewards on its own (holders earn nothing; the staking yield from the ETH backing it is redirected to sfrxETH stakers and AMO LP). To earn, you stake frxETH into **sfrxETH**, an **ERC-4626 vault** (xERC4626 / "Staked Frax Ether"). sfrxETH is **non-rebasing and value-accruing**: its frxETH-per-share exchange rate rises over each rewards cycle. **The monitoring invariant:** frxETH balances never change from yield (only transfers/mint/burn move them); sfrxETH share balances never change from yield either, but `convertToAssets(shares)` / `pricePerShare()` climbs. Index sfrxETH **shares** + read the rate; never infer yield from frxETH `Transfer` deltas.

**Cross-chain shape (read this before keying any L2 alert).** The minter and native frxETH/sfrxETH are **Ethereum-mainnet only**. On every other chain the tokens are **bridged representations** at **chain-specific addresses** — the canonical L1 addresses (`0x5E84…`, `0xac3E…`, `0xbAFA…`) are **NOT reused** elsewhere (where code exists at those addresses on BNB/Arbitrum it is an **unrelated collision contract** — see §Gotchas). Two bridge generations coexist:
- **Fraxferry "Bridged"** mint/burn tokens (the established representation, real multi-thousand-token supply) on **BNB, Arbitrum, Optimism, Polygon** — each a unique per-chain address.
- **LayerZero OFT** tokens (`frax-oft-upgradeable`) — a newer parallel mint/burn path. **OFT family A** (older standalone) is the canonical token on **Base**; on Ethereum the same address is an **OFT *Adapter*/lockbox** wrapping native frxETH. **OFT family B** (TransparentUpgradeableProxy) exists on **BNB, Avalanche, Arbitrum, Optimism, Polygon** as a low-supply second path that shares one address per token across those chains.
- **Avalanche** has **no Fraxferry token** — only the OFT-B representation.

---

## 0. Contract families & versions

| Family | Contracts | Chains | Upgradeable? |
|--------|-----------|--------|--------------|
| **Core (L1)** | `frxETH`, `sfrxETH`, `frxETHMinter` | Ethereum (1) only | **No** — all three are non-proxy immutable logic |
| **Fraxferry bridged** | bridged `frxETH`, bridged `sfrxETH` (mint/burn ERC-20s) | BNB, Arbitrum, Optimism, Polygon | No (non-proxy ERC-20) |
| **LayerZero OFT-A** | frxETH/sfrxETH OFT (+ L1 OFT-Adapter/lockbox) | Ethereum (adapter), Base (token) | No EIP-1967 proxy detected |
| **LayerZero OFT-B** | `frax-oft-upgradeable` frxETH/sfrxETH OFT | BNB, Avalanche, Arbitrum, Optimism, Polygon | **Yes** — TransparentUpgradeableProxy (shared `ProxyAdmin`) |
| **frxETH V2** (out of scope) | `ValidatorPool`, `BeaconOracle`, lending market | **Fraxtal (252)** — outside the 7 targets | n/a |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

`topic0` is unaffected by `indexed`. **✓** = observed verbatim in live mainnet `eth_getLogs`; **abi** = computed locally from the canonical source, not seen in the sampled ranges (rare/admin events).

### 1.1 frxETH — `ERC20PermitPermissionedMint` (non-yield ETH-pegged token)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ✓ |
| `0xe0dcb47e0eb67e20e87f3e34aab31c669ecec7466e8b7fb329d586dadebac6b6` | `TokenMinterMinted(address indexed from, address indexed to, uint256 amount)` | ✓ |
| `0x87e734acb0cbe2481bf904359eb1ae902c1d5d66768b93cab9c914bc89d9ff6d` | `TokenMinterAdded(address minter_address)` | abi |
| `0x9833ab532d36f60d6027dae24e0f397f8b4338ed236df4f47a86fb8b7caa4f6d` | `TokenMinterRemoved(address minter_address)` | abi |
| `0xb532073b38c83145e3e5135377a08bf9aab55bc0fd7c1179cd4fb995d2a5159c` | `OwnerChanged(address oldOwner, address newOwner)` | abi |
| `0x906a1c6bd7e3091ea86693dd029a831c19049ce77f1dce2ce0bab1cacbabce22` | `OwnerNominated(address newOwner)` | abi |
| `0x0b16e94338dda95fa1e5c779ff12c1c00489fca89839afd381c4c5faffd6e2a1` | `TimelockChanged(address previousTimelock, address newTimelock)` | abi |

> **frxETH mint = `TokenMinterMinted`** (the `frxETHMinter` is a registered minter; plain `Transfer` from `0x0` accompanies it). **There is no rebase/reward event on frxETH** — yield never touches a frxETH balance.

### 1.2 sfrxETH — ERC-4626 (xERC4626) "Staked Frax Ether" vault

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed caller, address indexed owner, uint256 assets, uint256 shares)` | ✓ |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed caller, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` | ✓ |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (the sfrxETH share token) | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` | ✓ |
| `0x2fa39aac60d1c94cda4ab0e86ae9c0ffab5b926e5b827a4ccba1d9b5b2ef596e` | `NewRewardsCycle(uint32 indexed cycleEnd, uint256 rewardAmount)` | ✓ |
| `0x1fbeec949a834367cc5fdafe73b350fb3b4ddbfdbf41774350f7d50d059ccbf4` | `SyncRewards(uint32 cycleEnd, uint32 lastSync, uint256 rewardCycleAmount)` | abi |

> **`NewRewardsCycle` is the yield event** (✓, fires when `syncRewards()` starts a new distribution window). `assets` in `Deposit`/`Withdraw` are **frxETH**; `shares` are **sfrxETH**. The exchange rate (`convertToAssets(1e18)`) rises smoothly across the cycle as the locked reward drips in — there is **no per-block rebase event**.

### 1.3 frxETHMinter — submit / ETH2 deposit hub (Ethereum only)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x29b3e86ecfd94a32218997c40b051e650e4fd8c97fc7a4d266be3f7c61c5205b` | `ETHSubmitted(address indexed sender, address indexed recipient, uint256 sent_amount, uint256 withheld_amt)` | ✓ |
| `0x60b677b352dc4c2f8482a85e1557d78515c38e3f3671be950a8357db6f563b9b` | `WithheldETHMoved(address indexed to, uint256 amount)` | ✓ |
| `0x4d312bd9aebc53f5bfad5cc169f41e65030288ef6b769786d43998abfb69a250` | `DepositSent(bytes indexed pubKey, bytes withdrawalCredential)` | abi |
| `0x9d9f4a1fa43ffde666e23300e98e21e37dccd7f33bb238071f5341a53f346f93` | `WithholdRatioSet(uint256 newRatio)` | abi |
| `0xcead0025c428cc6485390ecd2b3213d7a3d44d3f190a3b880ba9025521365706` | `DepositEtherPaused(bool new_status)` | abi |
| `0x4aff1af3f32e78f88c86566e6b50fe05d6ba3d9c7374e042ac17e5191c5fac56` | `SubmitPaused(bool new_status)` | abi |
| `0x040130779a9eeca4469ba7b0c5223a65f424ea2a23f9b9ee336afd7905ef68b4` | `EmergencyEtherRecovered(uint256 amount)` | abi |
| `0x2178cd1256ad9200080414ad733212aa6401e6a74954264b7654e671db074f56` | `EmergencyERC20Recovered(address tokenAddress, uint256 amount)` | abi |

> **`ETHSubmitted` is THE stake event** (✓). `sent_amount` is the ETH staked → 1:1 frxETH minted to `recipient`; `withheld_amt` is the portion kept liquid (per `withholdRatio`). `submitAndDeposit` additionally mints sfrxETH for the caller in the same tx (look for a paired sfrxETH `Deposit`). `DepositSent` fires once per 32-ETH validator funded.

### 1.4 LayerZero OFT (cross-chain bridge tokens — OFT-A and OFT-B)

Standard LayerZero OFT v2 events; same `topic0`s on every OFT instance (disambiguate by emitter):

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` | abi |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` | abi |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (mint from / burn to `0x0` on the OFT token) | ✓ |

> Cross-chain send = `OFTSent` on source + `Transfer` to `0x0` (burn) on a mint/burn OFT, **or** lock on the L1 OFT-Adapter (`approvalRequired()==1`, `token()` = native frxETH/sfrxETH). Receive = `OFTReceived` + `Transfer` from `0x0` (mint). Fraxferry bridged tokens emit only ERC-20 `Transfer` (mint/burn by the ferry operator) — no OFT event.

---

## 2. Function signatures (chain-agnostic — `selector = keccak256(sig)[0:4]`)

**bytecode** = confirmed present in the live deployed contract (PUSH4-dispatcher scan).

### 2.1 frxETHMinter (Ethereum)

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0x5bcb2fc6` | `submit()` | — | **Stake ETH → frxETH 1:1** (payable). Emits `ETHSubmitted`. bytecode ✓ |
| `0x4dcd4547` | `submitAndDeposit(address recipient)` | `uint256` shares | Stake **and** auto-stake into sfrxETH for `recipient`. bytecode ✓ |
| `0xbfda0c8c` | `submitAndGive(address recipient)` | — | Stake, mint frxETH to `recipient`. bytecode ✓ |
| `0x26839f17` | `depositEther(uint256 max_deposits)` | — | Pushes withheld ETH into the ETH2 deposit contract as 32-ETH validators. bytecode ✓ |
| `0xaa6fa83c` | `setWithholdRatio(uint256)` | — | Liquidity-buffer fraction. bytecode ✓ |
| `0x3f8380b6` | `moveWithheldETH(address,uint256)` | — | Emits `WithheldETHMoved`. bytecode ✓ |
| `0x8e69d7ad` | `currentWithheldETH()` | `uint256` | bytecode ✓ |
| `0x57c59b04` | `withholdRatio()` | `uint256` | bytecode ✓ |
| `0x5d593f8d` | `numValidators()` | `uint256` | bytecode ✓ |

### 2.2 frxETH (`ERC20PermitPermissionedMint`)

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0x6a257ebc` | `minter_mint(address m_address, uint256 m_amount)` | — | Mint (minter-gated). Emits `TokenMinterMinted`. bytecode ✓ |
| `0x7941bc89` | `minter_burn_from(address b_address, uint256 b_amount)` | — | Burn (minter-gated). bytecode ✓ |
| `0x983b2d56` | `addMinter(address)` | — | bytecode ✓ |
| `0x3092afd5` | `removeMinter(address)` | — | bytecode ✓ |
| `0xf46eccc4` | `minters(address)` | `bool` | is-minter map. bytecode ✓ |
| `0xd73ced04` | `minters_array(uint256)` | `address` | bytecode ✓ |
| `0xbdacb303` | `setTimelock(address)` | — | bytecode ✓ |
| `0x70a08231` / `0x18160ddd` / `0xa9059cbb` / `0x095ea7b3` / `0x23b872dd` | `balanceOf` / `totalSupply` / `transfer` / `approve` / `transferFrom` | — | ERC-20 (+ EIP-2612 `permit`). |

### 2.3 sfrxETH (ERC-4626 / xERC4626)

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0x6e553f65` | `deposit(uint256 assets, address receiver)` | `uint256` shares | Stake frxETH → sfrxETH. Emits `Deposit`. bytecode ✓ |
| `0x94bf804d` | `mint(uint256 shares, address receiver)` | `uint256` assets | bytecode ✓ |
| `0xb460af94` | `withdraw(uint256 assets, address receiver, address owner)` | `uint256` shares | bytecode ✓ |
| `0xba087652` | `redeem(uint256 shares, address receiver, address owner)` | `uint256` assets | Unstake → frxETH. Emits `Withdraw`. bytecode ✓ |
| `0x75e077c3` | `depositWithSignature(uint256,address,uint256,bool,uint8,bytes32,bytes32)` | `uint256` | EIP-2612-permit deposit. bytecode ✓ |
| `0x07a2d13a` | `convertToAssets(uint256 shares)` | `uint256` frxETH | **THE rate getter** (frxETH per share). bytecode ✓ |
| `0xc6e6f592` | `convertToShares(uint256 assets)` | `uint256` | bytecode ✓ |
| `0x99530b06` | `pricePerShare()` | `uint256` | = `convertToAssets(1e18)`. bytecode ✓ |
| `0x01e1d114` | `totalAssets()` | `uint256` | frxETH backing (excludes undripped reward). bytecode ✓ |
| `0x72c0c211` | `syncRewards()` | — | Starts a new rewards cycle → `NewRewardsCycle`. bytecode ✓ |
| `0xe7ff69f1` | `rewardsCycleEnd()` | `uint256` | bytecode ✓ |
| `0x38d52e0f` | `asset()` | `address` | = frxETH `0x5E84…`. bytecode ✓ |

### 2.4 LayerZero OFT (bridge surface)

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0xc7c7f5b3` | `send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)` | `(...)` | Cross-chain transfer (`SendParam`, `MessagingFee`, refund). |
| `0x3b6f743b` | `quoteSend((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),bool)` | `(uint256,uint256)` | Fee quote. |
| `0xfc0c546a` | `token()` | `address` | Underlying. On the L1 Adapter = native frxETH/sfrxETH; on a mint/burn OFT = self. |
| `0x9f68b964` | `approvalRequired()` | `bool` | `true` ⇒ lock/unlock adapter (L1); `false` ⇒ mint/burn OFT (L2). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

Every address verified: `eth_getCode` non-empty + token identity from live `name()`/`symbol()`/`asset()`. **None of these three core contracts is a proxy** (EIP-1967 impl & admin slots read zero).

| Role | Address | Proxy | One-liner |
|------|---------|-------|-----------|
| **frxETH** | `0x5E8422345238F34275888049021821E8E08CAa1f` | — | Non-yield ETH-pegged ERC-20; `name()="Frax Ether"`, `symbol()="frxETH"`. Mintable by registered minters. |
| **sfrxETH** | `0xac3E018457B222d93114458476f3E3416Abbe38F` | — | ERC-4626 vault, `asset()`=frxETH; value-accruing, non-rebasing. `symbol()="sfrxETH"`. |
| **frxETHMinter** | `0xbAFA44EFE7901E04E39Dad13167D089C559c1138` | — | `submit`/`submitAndDeposit` entry; funds ETH2 validators. Registered minter on frxETH. |
| ETH2 Deposit Contract | `0x00000000219ab540356cBB839Cbe05303d7705Fa` | — | Canonical CL deposit contract (not Frax-owned); minter's deposit target. |
| **frxETH OFT-Adapter (LZ)** | `0xF010a7c8877043681D59AD125EbF575633505942` | — (adapter) | L1 lockbox: `approvalRequired()=1`, `token()`=frxETH. Locks frxETH, mints OFT on remote. |
| **sfrxETH OFT-Adapter (LZ)** | `0x1f55a02A049033E3419a8E2975cF3F572F4e6E9A` | — (adapter) | L1 lockbox: `token()`=sfrxETH. |

## 4. Addresses — Base (chain ID 8453)

**No Fraxferry token on Base** — only the LayerZero OFT-A representation (the canonical Base token).

| Role | Address | Type | One-liner |
|------|---------|------|-----------|
| **frxETH** | `0xF010a7c8877043681D59AD125EbF575633505942` | LZ OFT-A | mint/burn OFT; `name()="Frax Ether"`. (Same address as the L1 Adapter, different role per chain.) |
| **sfrxETH** | `0x1f55a02A049033E3419a8E2975cF3F572F4e6E9A` | LZ OFT-A | mint/burn OFT; `symbol()="sfrxETH"`, `token()`=self. |

> An OFT-B sfrxETH (`0x3ec3849c…`) **has code on Base but is unconfigured** (`token()`/`symbol()` revert, no supply) — **do not use it**; the live Base token is `0x1f55…`.

## 5. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | Type | One-liner |
|------|---------|------|-----------|
| **frxETH** (canonical) | `0x64048A7eEcF3a2F1BA9e144aAc3D7dB6e58F555e` | Fraxferry bridged | mint/burn ERC-20, real supply. `name()="Frax Ether"`. |
| **sfrxETH** (canonical) | `0x3Cd55356433C89E50DC51aB07EE0fa0A95623D53` | Fraxferry bridged | `symbol()="sfrxETH"`. |
| frxETH (LZ) | `0x43eDD7f3831b08FE70B7555ddD373C8bF65a9050` | LZ OFT-B proxy | Parallel low-supply path; impl `0xec74a123…`. |
| sfrxETH (LZ) | `0x3ec3849c33291a9ef4c5db86de593eb4a37fde45` | LZ OFT-B proxy | Parallel low-supply path; impl `0xec74a123…`. |

## 6. Addresses — Avalanche C-Chain (chain ID 43114)

**No Fraxferry token on Avalanche** — only the LayerZero OFT-B representation. (The old Fraxferry addresses `0x94ddd112…` / `0xF380200B…` have **no code**.)

| Role | Address | Type | One-liner |
|------|---------|------|-----------|
| **frxETH** | `0x43eDD7f3831b08FE70B7555ddD373C8bF65a9050` | LZ OFT-B proxy | `name()="Frax Ether"`; impl `0xb47cbaa6…`. |
| **sfrxETH** | `0x3ec3849c33291a9ef4c5db86de593eb4a37fde45` | LZ OFT-B proxy | `symbol()="sfrxETH"`; impl `0xb47cbaa6…`. |

## 7. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | Type | One-liner |
|------|---------|------|-----------|
| **frxETH** (canonical) | `0x178412e79c25968a32e89b11f63B33F733770c2A` | Fraxferry bridged | real supply; `name()="Frax Ether"`. |
| **sfrxETH** (canonical) | `0x95aB45875cFFdba1E5f451B950bC2E42c0053f39` | Fraxferry bridged | `symbol()="sfrxETH"`. |
| frxETH (LZ) | `0x43eDD7f3831b08FE70B7555ddD373C8bF65a9050` | LZ OFT-B proxy | impl `0xc3c747e7…`. |
| sfrxETH (LZ) | `0x3ec3849c33291a9ef4c5db86de593eb4a37fde45` | LZ OFT-B proxy | impl `0xc3c747e7…`. |

> **Collision warning:** the L1 canonical `sfrxETH` (`0xac3E…`) and `frxETHMinter` (`0xbAFA…`) addresses **also hold code on Arbitrum**, but they are **unrelated contracts** (no `name()`/`symbol()`/`asset()`). Do not treat them as frxETH.

## 8. Addresses — Optimism (chain ID 10)

| Role | Address | Type | One-liner |
|------|---------|------|-----------|
| **frxETH** (canonical) | `0x6806411765Af15Bddd26f8f544A34cC40cb9838B` | Fraxferry bridged | real supply. |
| **sfrxETH** (canonical) | `0x484c2D6e3cDd945a8B2DF735e079178C1036578c` | Fraxferry bridged | `symbol()="sfrxETH"`. |
| frxETH (LZ) | `0x43eDD7f3831b08FE70B7555ddD373C8bF65a9050` | LZ OFT-B proxy | impl `0x08f27a09…`. |
| sfrxETH (LZ) | `0x3ec3849c33291a9ef4c5db86de593eb4a37fde45` | LZ OFT-B proxy | impl `0x08f27a09…`. |

## 9. Addresses — Polygon PoS (chain ID 137)

| Role | Address | Type | One-liner |
|------|---------|------|-----------|
| **frxETH** (canonical) | `0xEe327F889d5947c1dc1934Bb208a1E792F953E96` | Fraxferry bridged | real supply. |
| **sfrxETH** (canonical) | `0x6d1FdBB266fCc09A16a22016369210A15bb95761` | Fraxferry bridged | `symbol()="sfrxETH"`. |
| frxETH (LZ) | `0x43eDD7f3831b08FE70B7555ddD373C8bF65a9050` | LZ OFT-B proxy | impl `0x8383edf0…`. |
| sfrxETH (LZ) | `0x3ec3849c33291a9ef4c5db86de593eb4a37fde45` | LZ OFT-B proxy | impl `0x8383edf0…`. |

---

## 10. Cross-chain summary (presence matrix)

| Chain | ID | frxETH (canonical) | sfrxETH (canonical) | Minter | frxETH OFT-B | sfrxETH OFT-B |
|-------|----|--------------------|---------------------|--------|--------------|---------------|
| Ethereum | 1 | `0x5E84…Aa1f` (native) | `0xac3E…be38F` (native) | `0xbAFA…1138` | — (Adapter `0xF010…`) | — (Adapter `0x1f55…`) |
| Base | 8453 | `0xF010…5942` (OFT-A) | `0x1f55…6E9A` (OFT-A) | — | — | — |
| BNB | 56 | `0x6404…55e` (Ferry) | `0x3Cd5…3D53` (Ferry) | — | `0x43eD…9050` | `0x3ec3…fde45` |
| Avalanche | 43114 | `0x43eD…9050` (OFT-B) | `0x3ec3…fde45` (OFT-B) | — | (= canonical) | (= canonical) |
| Arbitrum | 42161 | `0x1784…0c2A` (Ferry) | `0x95aB…3f39` (Ferry) | — | `0x43eD…9050` | `0x3ec3…fde45` |
| Optimism | 10 | `0x6806…838B` (Ferry) | `0x484c…578c` (Ferry) | — | `0x43eD…9050` | `0x3ec3…fde45` |
| Polygon | 137 | `0xEe32…3E96` (Ferry) | `0x6d1F…5761` (Ferry) | — | `0x43eD…9050` | `0x3ec3…fde45` |

**Minter + native mint/burn = Ethereum only.** Everything off-chain-1 is a bridged claim on L1 frxETH/sfrxETH; the on-chain frxETH-per-sfrxETH **rate is only readable on Ethereum** (`sfrxETH.convertToAssets`) — bridged sfrxETH carries no live oracle, so an L2 indexer must source the rate from L1.

---

## 11. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| frxETH, sfrxETH, frxETHMinter (L1) | **immutable** | EIP-1967 impl & admin slots read `0x0` (verified live) | none — not upgradeable |
| Fraxferry bridged frxETH/sfrxETH (BNB/Arb/OP/Polygon) | **non-proxy ERC-20** | impl slot `0x0` (verified BNB/Arb) | Frax comptroller (mint/burn role), no impl swap |
| LZ OFT-A (Base token; L1 Adapter) | **non-proxy** | no EIP-1967 impl slot; `approvalRequired()`/`token()` distinguish adapter-vs-token | n/a |
| **LZ OFT-B** (`frax-oft-upgradeable`, 5 chains) | **TransparentUpgradeableProxy (EIP-1967)** | impl slot `0x360894…2bbc` non-zero (per-chain impl); admin slot `0xb53127…6103` = **`0x223a681fc5c5522c85c96157c0efa18cd6c5405c`** (shared `ProxyAdmin` across all 5 chains). `implementation()`/`admin()` calls **revert** (transparent-proxy: only admin sees them) | `ProxyAdmin` `0x223a681f…` → Frax multisig |

**Upgraded(address) topic to watch** (only on the OFT-B proxies): `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`.

**OFT-B per-chain implementations** (read from EIP-1967 slot, 2026-06-09): BNB `0xec74a123fc45e5d8e36abd09b736010ba8fc0eda` · Avalanche `0xb47cbaa686d0396ca863eca35ff2e9e85b550d43` · Arbitrum `0xc3c747e76a3700d611fb76cae9a8ab3411835ca0` · Optimism `0x08f27a096cc262b9d100f169b5510ffda6596a99` · Polygon `0x8383edf0b101249a632d1d5372baf0d7709d65fe`.

---

## 12. Detection invariants & gotchas

1. **frxETH NEVER yields; sfrxETH yields via exchange rate.** frxETH is a flat ETH-pegged ERC-20 — a frxETH balance only moves on transfer/mint/burn, never from rewards. sfrxETH **share** balances are likewise yield-static; the value accrues in `convertToAssets`/`pricePerShare`, which rises across each `NewRewardsCycle`. **Never infer staking yield from frxETH `Transfer` deltas, and never store a frxETH-denominated sfrxETH value — store shares + the L1 rate.**
2. **The yield event is `NewRewardsCycle` (sfrxETH), not a rebase.** No per-block `TokenRebased`-style event exists. Reward is loaded by `syncRewards()` and drips linearly to `rewardsCycleEnd()`; `totalAssets()` excludes the undripped portion, so the rate is continuous, not stepwise.
3. **The stake event is `ETHSubmitted` on the minter** (`0x29b3e86e…`), not a token event. `submitAndDeposit` additionally emits an sfrxETH `Deposit` in the same tx (one-tx ETH→sfrxETH). The minter + native mint path are **Ethereum-only**.
4. **Canonical L1 addresses are NOT reused cross-chain — and collide with unrelated contracts.** On **BNB** there is code at the L1 `frxETH` address `0x5E84…` and on **Arbitrum** at the L1 `sfrxETH` (`0xac3E…`) and `frxETHMinter` (`0xbAFA…`) addresses — **none of these is frxETH** (they fail `name()`/`symbol()`/`asset()`). Always key bridged tokens on the **chain-specific** address from §4–§9, not the L1 address.
5. **Two bridge generations coexist per chain.** On BNB/Arb/OP/Polygon the **Fraxferry** token is the established representation (multi-thousand-token supply) and the **LZ OFT-B** is a low-supply parallel path — **both are real and both can move supply.** Monitor both; sum supplies if tracking total bridged float. They are distinct addresses with distinct events (Ferry = ERC-20 `Transfer` only; OFT = `OFTSent`/`OFTReceived` + `Transfer` from/to `0x0`).
6. **Base = OFT-A only; Avalanche = OFT-B only.** Base has no Fraxferry token; its canonical is the OFT-A (`0xF010…`/`0x1f55…`). Avalanche has neither Fraxferry nor OFT-A — only OFT-B (`0x43eD…`/`0x3ec3…`). A stale Base OFT-B sfrxETH (`0x3ec3…`) has code but is **unconfigured** (reverts, zero supply) — ignore it.
7. **L1 OFT entries are *adapters*, not tokens.** `0xF010…`/`0x1f55…` on Ethereum lock native frxETH/sfrxETH (`approvalRequired()=1`, `token()`=native) — they do **not** have their own `name()`/`symbol()` and a naive `symbol()` read reverts. On Base the *same addresses* are the actual mint/burn tokens. **Disambiguate by chain + `approvalRequired()`/`token()`**, not by address alone.
8. **OFT-B is the only upgradeable thing here.** All L1 core, all Fraxferry tokens, and OFT-A are non-proxy. Only the five OFT-B proxies are upgradeable (shared `ProxyAdmin` `0x223a681f…`) — watch their `Upgraded(address)` (`0xbc7cd75a…`). The `implementation()`/`admin()` calls revert on them (transparent proxy); read the EIP-1967 impl slot instead.
9. **`Transfer` topic0 is shared** by frxETH, sfrxETH, every bridged token, and every OFT — always disambiguate by emitting contract.
10. **frxETH V2 is a different protocol on a different chain.** The V2 validator-lending market (`ValidatorPool`s borrowing ETH, `BeaconOracle` liquidations) lives on **Fraxtal (252)**, not on any of the 7 targets, and does **not** change the frxETH/sfrxETH token contracts above. Don't conflate V2 lending events with the staking events here.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TRANSFER              = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL             = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- frxETH
TOPIC_TOKEN_MINTER_MINTED  = '\xe0dcb47e0eb67e20e87f3e34aab31c669ecec7466e8b7fb329d586dadebac6b6'
TOPIC_TOKEN_MINTER_ADDED   = '\x87e734acb0cbe2481bf904359eb1ae902c1d5d66768b93cab9c914bc89d9ff6d'
TOPIC_TOKEN_MINTER_REMOVED = '\x9833ab532d36f60d6027dae24e0f397f8b4338ed236df4f47a86fb8b7caa4f6d'
-- sfrxETH (ERC4626 / xERC4626)
TOPIC_DEPOSIT_4626         = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_WITHDRAW_4626        = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_NEW_REWARDS_CYCLE    = '\x2fa39aac60d1c94cda4ab0e86ae9c0ffab5b926e5b827a4ccba1d9b5b2ef596e'
TOPIC_SYNC_REWARDS         = '\x1fbeec949a834367cc5fdafe73b350fb3b4ddbfdbf41774350f7d50d059ccbf4'
-- frxETHMinter
TOPIC_ETH_SUBMITTED        = '\x29b3e86ecfd94a32218997c40b051e650e4fd8c97fc7a4d266be3f7c61c5205b'
TOPIC_WITHHELD_ETH_MOVED   = '\x60b677b352dc4c2f8482a85e1557d78515c38e3f3671be950a8357db6f563b9b'
TOPIC_DEPOSIT_SENT         = '\x4d312bd9aebc53f5bfad5cc169f41e65030288ef6b769786d43998abfb69a250'
-- LayerZero OFT
TOPIC_OFT_SENT             = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED         = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_UPGRADED             = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
SEL_SUBMIT                 = '\x5bcb2fc6'   -- frxETHMinter.submit()
SEL_SUBMIT_AND_DEPOSIT     = '\x4dcd4547'   -- frxETHMinter.submitAndDeposit(address)
SEL_SUBMIT_AND_GIVE        = '\xbfda0c8c'   -- frxETHMinter.submitAndGive(address)
SEL_DEPOSIT_ETHER          = '\x26839f17'   -- frxETHMinter.depositEther(uint256)
SEL_MINTER_MINT            = '\x6a257ebc'   -- frxETH.minter_mint(address,uint256)
SEL_MINTER_BURN_FROM       = '\x7941bc89'   -- frxETH.minter_burn_from(address,uint256)
SEL_4626_DEPOSIT           = '\x6e553f65'   -- sfrxETH.deposit(uint256,address)
SEL_4626_REDEEM            = '\xba087652'   -- sfrxETH.redeem(uint256,address,address)
SEL_4626_WITHDRAW          = '\xb460af94'   -- sfrxETH.withdraw(uint256,address,address)
SEL_CONVERT_TO_ASSETS      = '\x07a2d13a'   -- sfrxETH.convertToAssets(uint256)  [the rate]
SEL_PRICE_PER_SHARE        = '\x99530b06'   -- sfrxETH.pricePerShare()
SEL_SYNC_REWARDS           = '\x72c0c211'   -- sfrxETH.syncRewards()
SEL_OFT_SEND               = '\xc7c7f5b3'   -- OFT.send((...),(...),address)
SEL_OFT_TOKEN              = '\xfc0c546a'   -- OFT.token()  [adapter vs mint/burn]
SEL_OFT_APPROVAL_REQUIRED  = '\x9f68b964'   -- OFT.approvalRequired()

-- ===== Ethereum mainnet (chain ID 1) =====
ETH_FRXETH                 = '\x5e8422345238f34275888049021821e8e08caa1f'
ETH_SFRXETH                = '\xac3e018457b222d93114458476f3e3416abbe38f'
ETH_FRXETH_MINTER          = '\xbafa44efe7901e04e39dad13167d089c559c1138'
ETH_FRXETH_OFT_ADAPTER     = '\xf010a7c8877043681d59ad125ebf575633505942'
ETH_SFRXETH_OFT_ADAPTER    = '\x1f55a02a049033e3419a8e2975cf3f572f4e6e9a'
-- ===== Base (8453) — OFT-A canonical =====
BASE_FRXETH                = '\xf010a7c8877043681d59ad125ebf575633505942'
BASE_SFRXETH               = '\x1f55a02a049033e3419a8e2975cf3f572f4e6e9a'
-- ===== BNB (56) — Fraxferry canonical =====
BNB_FRXETH                 = '\x64048a7eecf3a2f1ba9e144aac3d7db6e58f555e'
BNB_SFRXETH                = '\x3cd55356433c89e50dc51ab07ee0fa0a95623d53'
-- ===== Avalanche (43114) — OFT-B only =====
AVAX_FRXETH                = '\x43edd7f3831b08fe70b7555ddd373c8bf65a9050'
AVAX_SFRXETH               = '\x3ec3849c33291a9ef4c5db86de593eb4a37fde45'
-- ===== Arbitrum (42161) — Fraxferry canonical =====
ARB_FRXETH                 = '\x178412e79c25968a32e89b11f63b33f733770c2a'
ARB_SFRXETH                = '\x95ab45875cffdba1e5f451b950bc2e42c0053f39'
-- ===== Optimism (10) — Fraxferry canonical =====
OP_FRXETH                  = '\x6806411765af15bddd26f8f544a34cc40cb9838b'
OP_SFRXETH                 = '\x484c2d6e3cdd945a8b2df735e079178c1036578c'
-- ===== Polygon (137) — Fraxferry canonical =====
POLY_FRXETH                = '\xee327f889d5947c1dc1934bb208a1e792f953e96'
POLY_SFRXETH               = '\x6d1fdbb266fcc09a16a22016369210a15bb95761'
-- ===== LZ OFT-B (shared addr on BNB/Avax/Arb/OP/Polygon) =====
OFTB_FRXETH                = '\x43edd7f3831b08fe70b7555ddd373c8bf65a9050'
OFTB_SFRXETH               = '\x3ec3849c33291a9ef4c5db86de593eb4a37fde45'
OFTB_PROXY_ADMIN           = '\x223a681fc5c5522c85c96157c0efa18cd6c5405c'
EIP1967_IMPL_SLOT          = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 14. Verification & sources

- **keccak-256:** every `topic0`/selector recomputed locally and cross-checked against the canonical ERC-20 `Transfer`/`Approval` topic0s before use. Two unknown live topic0s (`WithheldETHMoved`, `TokenMinterMinted`) resolved via the openchain signature DB and then **re-derived locally** to confirm.
- **Topics (✓):** observed verbatim in live `eth_getLogs` on `https://ethereum-rpc.publicnode.com` — `ETHSubmitted`+`WithheldETHMoved` on the minter, `Deposit`/`Withdraw`/`NewRewardsCycle`/`Transfer`/`Approval` on sfrxETH, `Transfer`/`Approval`/`TokenMinterMinted` on frxETH. Admin/rare events marked `abi`. OFT topics computed + confirmed via openchain.
- **Selectors (bytecode):** PUSH4-dispatcher scan of the live `frxETHMinter`, `frxETH`, `sfrxETH` deployments — all listed selectors present (minter uses `depositEther(uint256)`, not the no-arg form; sfrxETH is plain xERC4626 without `maxDistributionPerSecondPerAsset`).
- **Addresses:** every entry existence-checked with `eth_getCode` on its chain's RPC; token identity verified live via `name()`/`symbol()`/`asset()`. The native↔OFT-A adapter distinction confirmed via `token()`/`approvalRequired()`. Proxy classification from EIP-1967 impl/admin slot reads (core L1 + Fraxferry = slots zero; OFT-B = impl populated per-chain + shared admin `0x223a681f…`). The L1-address-collision contracts on BNB/Arbitrum were probed and confirmed to be unrelated (no token interface). Avalanche & Base confirmed to have no Fraxferry token; old Fraxferry Avax addresses confirmed code-less.
- **Live rate sanity (2026-06-09):** `sfrxETH.convertToAssets(1e18)` = `pricePerShare()` = `0x101c2653c3169090` ≈ **1.161 frxETH per sfrxETH**, confirming the value-accruing (non-rebasing) ERC-4626 design.

Authoritative sources:
- [`FraxFinance/frxETH-public`](https://github.com/FraxFinance/frxETH-public) — `frxETH`, `sfrxETH`, `frxETHMinter` source.
- [`FraxFinance/frax-solidity`](https://github.com/FraxFinance/frax-solidity) — address constants.
- [`FraxFinance/frax-oft-upgradeable`](https://github.com/FraxFinance/frax-oft-upgradeable) — LayerZero OFT (family B) deployments.
- [docs.frax.finance — frxETH and sfrxETH Token Addresses](https://docs.frax.finance/frax-ether/frxeth-and-sfrxeth-token-addresses) · [frxETH V2 (Fraxtal validator lending, out of scope)](https://docs.frax.finance/frax-ether/frxeth-v2).
- Explorers: [Etherscan sfrxETH](https://etherscan.io/token/0xac3e018457b222d93114458476f3e3416abbe38f), [Arbiscan sfrxETH](https://arbiscan.io/token/0x95ab45875cffdba1e5f451b950bc2e42c0053f39), [OP sfrxETH](https://optimistic.etherscan.io/token/0x484c2d6e3cdd945a8b2df735e079178c1036578c).
