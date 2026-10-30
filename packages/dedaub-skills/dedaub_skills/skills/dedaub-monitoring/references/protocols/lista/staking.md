# Lista Liquid Staking (slisBNB, slisBNBx) — Topics, Selectors, Addresses (BNB Chain, Ethereum)

**Status:** verified against live RPC on BNB Chain (56) and Ethereum (1) and the canonical `lista-dao/synclub-contracts`, `lista-dao/lista-token` and `lista-dao/lista-dao-contracts` repos on 2026-10-30.
**Scope:** BNB liquid staking — `ListaStakeManager` (stake, withdraw queue, validator delegation through the BSC StakeHub), the `slisBNB` token, the LayerZero OFT bridge of slisBNB to Ethereum, and the `slisBNBx` certificate (formerly clisBNB) that lets a collateral position earn Binance Launchpool rewards. Topics and selectors are chain-agnostic. Addresses are network-specific.

`ListaStakeManager` takes BNB, delegates it to whitelisted BSC validators through the native StakeHub system contract (`0x…2002`) and mints slisBNB at the current exchange rate. Unstaking is a two-step queue: `requestWithdraw` burns slisBNB, `claimWithdraw` pays BNB after the unbonding period. An `instantWithdraw` path pays from a buffer for a fee. The product descends from Synclub (snBNB), so the repo is still named `synclub-contracts`.

Both `ListaStakeManager` and `slisBNB` are OZ v4 TransparentUpgradeableProxies (2112 B). Their ProxyAdmin `0x8ce30a8d13d6d729708232aa415d7da46a4fa07b` is owned by the 1-day TimelockController `0x07d274a68393e8b8a2ccf19a2ce4ba3518735253`.

Staking exists on **BNB Chain only**. Ethereum has only the bridged slisBNB OFT. Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc have nothing (`eth_getCode` = `0x` at the slisBNB, StakeManager and OFT addresses).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 ListaStakeManager

| topic0 | Event |
|--------|-------|
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address _src, uint256 _amount)` — stake BNB. **No indexed args; same topic0 as WBNB/WETH `Deposit(address indexed,uint256)`** |
| `0x0afd74a2a0a78f6c15e41029f44995ee023fe49276f44a4b2b2cf674829362e6` | `RequestWithdraw(address indexed _account, uint256 _amountInSlisBnb)` |
| `0x63bfb3a58e0713d68e49dda62c223fab04fb534eeef8ac6356cec78e691c092a` | `ClaimWithdrawal(address indexed _account, uint256 _idx, uint256 _amount)` |
| `0x672004d35ad2124f90299371ade95cf5594500e40705a7cf6eaf7c00b55a07ac` | `InstantWithdraw(address indexed _user, uint256 _slisBnbAmount, uint256 _bnbAmountAfterFee, uint256 _fee)` |
| `0x5e71c05bb10b927aa8842ebdca9a130a7f3333b640f0c3cb1380fbef84c34749` | `DelegateTo(address _validator, uint256 _amount, bool _delegateVotePower)` |
| `0x0f23ce3b62792113baf786ff98a77f4309d51920fcb7d88bab3f7e6f53d2287a` | `ReDelegate(address _src, address _dest, uint256 _amount)` |
| `0x0190f399b2c3dcb444d981796081189b4b1f466824f5a82f2bf53713ac5b427b` | `UndelegateFrom(address indexed _operator, uint256 _bnbAmount, uint256 _shares)` |
| `0x1031206b6983c708045c4fe17ec7933f2dc7c3e600724e00fe15a9fe383d9ddd` | `ClaimUndelegatedFrom(address indexed _validator, uint256 _uuid, uint256 _amount)` |
| `0x33222d90f0305cdd84f37927a34b36077e5328c8318dc017be0eed3e0305fa2e` | `RewardsCompounded(uint256 _amount)` — exchange-rate step |
| `0xd586d49d4f659031867ca21e9a1c82179f2ab7946a8f75670218d8e494b5e5d5` | `RefundCommission(uint256 _bnbAmount, uint256 _dailySlisBnb, uint256 _days, uint256 _remainingSlisBnb)` |
| `0x0e54007134950d3919a149802063b8771a6f9aa0e04673316971e72e7c8c7024` | `ClaimWithdrawFee(address indexed _recipient, uint256 _amount)` |
| `0x5ce1ed13ab7bf8de942f6a4d7ef859be025626a486b20a66ea2e20d771a5d0ee` | `WhitelistValidator(address indexed _address)` |
| `0x36a773811aa40c53a642b0596c94174b588d0d1b2b9b6fa6e31c3c30d686163f` | `DisableValidator(address indexed _address)` |
| `0x1af60f72d206709ac9c5fd393b54381507af4df1feb01708422ef8498c57aa57` | `RemoveValidator(address indexed _address)` |
| `0xc42638714e4dadf46d57ed62b1ef9805f061d57fc97d4d5bed85d6d420363545` | `SetSynFee(uint256 _synFee)` — protocol fee on rewards |
| `0xe85ff8a2cb1dcb286d18a041670a3e95d5093a45a77f06120748d920678f0b55` | `SetInstantWithdrawFeeRate(uint256 _feeRate)` |
| `0xf980d53d1bddd28d9ae609f333a2a294fa8f486a11bb8ddb03b71f5f17429011` | `SetRevenuePool(address indexed _address)` |
| `0x54a6385aa0292b04e1ef8513253c17d1863f7cdfc87029d77fd55cc4c2e717e2` | `SetManager(address indexed _address)` |
| `0x83652aadba7c476ee2342c6633f26530701848fafd5ea726f804efef2007898d` | `SetSubStaker(address indexed _subStaker)` |

`Redelegate(uint256,uint256)` (`0x18112e7e…`) is declared in the interface but is absent from the live implementation bytecode.

### 1.2 slisBNB token, slisBNBx certificate, OFT bridge

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — mint = from `0x0` (by StakeManager), burn = to `0x0` | slisBNB, slisBNBx, ListaOFT (ETH) |
| `0x7dfdd82c117acb6fc9c4b79890e8556f46493a5da48f6e0ac5eca08276ac7c92` | `SetStakeManager(address indexed _address)` — who can mint | slisBNB |
| `0x04bca3656717d14c20f88f2a0122832cb0d2807bfc66ed9e932a2202cc59f495` | `MinterChanged(address minter, bool isAdd)` | slisBNBx |
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` | ListaOFTAdapter (BSC), ListaOFT (ETH) |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` | ListaOFTAdapter, ListaOFT |
| `0xc936000a38158a6358900260524fb98fda54e21b1fb66f53d6eae161af6a8e1a` | `TransferLimitChanged(uint32 dstEid, uint256 maxDailyTransferAmount, uint256 singleTransferUpperLimit, uint256 singleTransferLowerLimit, uint256 dailyTransferAmountPerAddress, uint256 dailyTransferAttemptPerAddress)` | ListaOFTAdapter, ListaOFT |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` | ListaOFTAdapter, ListaOFT |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` / `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Paused(address)` / `Unpaused(address)` | ListaOFTAdapter, ListaOFT |

slisBNBx balances are minted and burned by the providers (`SlisBNBxMinter`, the Moolah and CDP slisBNB providers). Those providers emit `UserLpRebalanced` / `SyncUserLp` (see [lending.md](lending.md) §1.5 and [cdp.md](cdp.md) §1.4).

---

## 2. Function signatures (chain-agnostic)

### 2.1 ListaStakeManager

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd0e30db0` | `deposit()` | payable. Stake BNB, mint slisBNB. Emits `Deposit`. |
| `0x745400c9` | `requestWithdraw(uint256)` | Amount in slisBNB. Burns slisBNB. Emits `RequestWithdraw`. |
| `0xb13acedd` | `claimWithdraw(uint256)` | Request index. Pays BNB. Emits `ClaimWithdrawal`. |
| `0x916082e5` | `claimWithdrawByUUID(uint256)` | |
| `0x9a53d5af` | `claimWithdrawFor(address,uint256)` | Bot claim for a user. |
| `0xfd92bff2` | `instantWithdraw(uint256)` | Buffer exit with fee. Emits `InstantWithdraw`. |
| `0xc00c9f7f` | `compoundRewards()` | Bot. Emits `RewardsCompounded`. |
| `0x8bcd4620` | `delegateTo(address,uint256)` | Manager. |
| `0x6bd8f804` | `redelegate(address,address,uint256)` | Manager. |
| `0x252b7edc` | `undelegateFrom(address,uint256)` | Bot. |
| `0x1b3133fb` | `claimUndelegated(address)` | Bot. |
| `0x85c48a0b` / `0x1fe97684` / `0x40a141ff` | `whitelistValidator(address)` / `disableValidator(address)` / `removeValidator(address)` | Manager. |
| `0x6dda1f38` | `setSynFee(uint256)` | Admin. |
| `0x3bfb5c14` | `setInstantWithdrawFeeRate(uint256)` | Admin. |
| `0x8456cb59` / `0x3f4ba83a` / `0xc4ae3168` | `pause()` / `unpause()` / `togglePause()` | |
| `0xce6298e1` | `convertSnBnbToBnb(uint256)` | view. Exchange rate slisBNB → BNB. |
| `0x29d8a2eb` | `convertBnbToSnBnb(uint256)` | view. |
| `0x2be7fef5` | `getTotalPooledBnb()` | view. |
| `0x6c930228` | `getUserWithdrawalRequests(address)` | view. |

### 2.2 slisBNB, slisBNBx, OFT

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | slisBNB: StakeManager only. slisBNBx: minters only. |
| `0x9dc29fac` | `burn(address,uint256)` | Same gates. |
| `0x0e7c67fc` | `setStakeManager(address)` | slisBNB admin. |
| `0x983b2d56` / `0x3092afd5` | `addMinter(address)` / `removeMinter(address)` | slisBNBx admin. |
| `0xc7c7f5b3` | `send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)` | LayerZero OFT send (adapter or OFT). |
| `0x5d504c80` | `setTransferLimitConfigs((uint32,uint256,uint256,uint256,uint256,uint256)[])` | Owner. |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)

All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **ListaStakeManager** | `0x1adB950d8bB3dA4bE104211D5AB038628e477fE6` | Stake/unstake BNB. Transparent proxy, impl `0xafe120d0d912495366253c51fe1f2f6f71f6a085`. |
| **slisBNB** | `0xB0b84D294e0C75A6abe60171b70edEb2EFd14A1B` | "Staked Lista BNB". Transparent proxy, impl `0xd9edeba7f3580f5e22821a52fc1ba8508f4e34d0`. |
| ListaOFTAdapter (slisBNB) | `0x837CB07f6B8a98731856092457524FF37b25E7B3` | Lock/unlock adapter, LayerZero EID 30102. Immutable (14510 B). Owner `0x8d388136d578dCD791D081c6042284CED6d9B0c6`. |
| SubStaker | `0x571a25497A28A3424ad652f665e63219070195E1` | Sub-staking helper (708 B proxy). |
| **slisBNBx** | `0x4b30fcAA7945fE9fDEFD2895aae539ba102Ed6F6` | Non-transferable Launchpool certificate (symbol `slisBNBx`). Transparent proxy, ProxyAdmin `0x1fa3e4718168077975ff4039304cc2e19ae58c4c`. |
| SlisBNBxMinter | `0x2959c423bfe5Cc6E41516599D982A29C0773F11a` | Mints slisBNBx for Moolah collateral. |
| ClisBNBLaunchPoolDistributor | `0x81a62B329CC8939494d8613F614171a9955A46e8` | Launchpool reward distributor. OZ v5 Transparent proxy. |
| ClisBNBLaunchPoolDistributor (Pendle) | `0x8b7d334d243b74D63C4b963893267A0F5240F990` | Same impl `0x231ddb18…f116a`. |
| ERC20TokenProvider | `0x2725d7336027773d7a958e10819a923dcd65aa57` | ERC-20 provider for slisBNBx minting. |
| StakeHub (BSC system) | `0x0000000000000000000000000000000000002002` | Native validator staking. Not a Lista contract. |

## 4. Addresses — Ethereum (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **ListaOFT (slisBNB)** | `0xf9B24C9364457Ea85792179D285855753549eBAa` | Mint/burn OFT, symbol `slisBNB`, LayerZero EID 30101. Immutable (18767 B, no proxy). `token()` returns itself. |

No StakeManager on Ethereum. The OFT supply is backed by slisBNB locked in the BSC adapter.

## 5. Cross-chain summary

| Chain (ID) | ListaStakeManager | slisBNB | OFT | slisBNBx |
|------------|-------------------|---------|-----|----------|
| BNB (56) | `0x1adB95…7fE6` | `0xB0b84D…4A1B` (canonical) | adapter `0x837CB0…B7E3` | `0x4b30fc…F6` |
| Ethereum (1) | — | via OFT | `0xf9B24C…eBAa` | — |
| Base · Avalanche · Arbitrum · Optimism · Polygon · Robinhood · Arc | — | — | — | — |

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| ListaStakeManager, slisBNB | OZ v4 TransparentUpgradeableProxy | 2112 B; admin slot = ProxyAdmin `0x8ce30a8d…a07b` | ProxyAdmin owner = TimelockController `0x07d274…5253` (1 day) |
| slisBNBx | OZ v4 TransparentUpgradeableProxy | 2141 B; admin slot = ProxyAdmin `0x1fa3e471…8c4c` | same timelock |
| ClisBNBLaunchPoolDistributor (×2) | OZ v5 TransparentUpgradeableProxy | 1159 B; one ProxyAdmin per proxy | ProxyAdmin owner |
| ListaOFTAdapter (BSC), ListaOFT (ETH) | immutable | impl slot `0x0` | — (owner can pause and set limits) |

Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` and `AdminChanged(address,address)` `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` on the proxies.

## 7. Detection invariants & gotchas

1. **`Deposit` topic0 collision with WBNB.** StakeManager `Deposit(address,uint256)` has the same topic0 as WBNB/WETH `Deposit`. The StakeManager version has **no indexed argument** (1 topic; the staker is in `data`). WBNB indexes `dst` (2 topics). Always filter by emitter `0x1adB95…7fE6`.
2. **Staker attribution.** `_src` in `Deposit` is `msg.sender`. Deposits through a router or provider show the router, not the end user.
3. **Unstake is two events.** `RequestWithdraw` (slisBNB amount) and later `ClaimWithdrawal` (BNB amount, request index). Match them by `_account` and `_idx`. `InstantWithdraw` is a separate one-step path with a fee.
4. **Exchange rate.** slisBNB is not rebasing. Value grows through `RewardsCompounded`. A sudden drop in pooled BNB (validator slashing) shows as a smaller `RewardsCompounded` or an `UndelegateFrom` without a matching claim.
5. **slisBNBx is non-transferable.** Its `Transfer` logs are mints and burns only. Supply follows collateral deposited in Moolah and CDP slisBNB providers.
6. **OFT dust.** `sharedDecimals = 6`. Bridged amounts are truncated to a multiple of `1e12` wei. `amountSentLD` can be less than the requested amount.
7. **Address reuse.** `0xf9B24C…eBAa` is the slisBNB OFT on Ethereum, but the same literal on BNB is an unrelated 9560 B contract. `0x8b7d33…F990` is a Launchpool distributor on BNB but the Moolah IRM on Ethereum. Key on `(chainId, address)`.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_STAKE_DEPOSIT               = '\xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'
TOPIC_STAKE_REQUEST_WITHDRAW      = '\x0afd74a2a0a78f6c15e41029f44995ee023fe49276f44a4b2b2cf674829362e6'
TOPIC_STAKE_CLAIM_WITHDRAWAL      = '\x63bfb3a58e0713d68e49dda62c223fab04fb534eeef8ac6356cec78e691c092a'
TOPIC_STAKE_INSTANT_WITHDRAW      = '\x672004d35ad2124f90299371ade95cf5594500e40705a7cf6eaf7c00b55a07ac'
TOPIC_STAKE_REWARDS_COMPOUNDED    = '\x33222d90f0305cdd84f37927a34b36077e5328c8318dc017be0eed3e0305fa2e'
TOPIC_STAKE_DELEGATE_TO           = '\x5e71c05bb10b927aa8842ebdca9a130a7f3333b640f0c3cb1380fbef84c34749'
TOPIC_STAKE_UNDELEGATE_FROM       = '\x0190f399b2c3dcb444d981796081189b4b1f466824f5a82f2bf53713ac5b427b'
TOPIC_STAKE_SET_SYN_FEE           = '\xc42638714e4dadf46d57ed62b1ef9805f061d57fc97d4d5bed85d6d420363545'
TOPIC_SLISBNB_SET_STAKE_MANAGER   = '\x7dfdd82c117acb6fc9c4b79890e8556f46493a5da48f6e0ac5eca08276ac7c92'
TOPIC_ERC20_TRANSFER              = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_OFT_SENT                    = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED                = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_STAKE_DEPOSIT                 = '\xd0e30db0'
SEL_STAKE_REQUEST_WITHDRAW        = '\x745400c9'
SEL_STAKE_CLAIM_WITHDRAW          = '\xb13acedd'
SEL_STAKE_INSTANT_WITHDRAW        = '\xfd92bff2'
SEL_STAKE_COMPOUND_REWARDS        = '\xc00c9f7f'
SEL_OFT_SEND                      = '\xc7c7f5b3'
-- ===== Addresses (network-specific) =====
BSC_LISTA_STAKE_MANAGER           = '\x1adb950d8bb3da4be104211d5ab038628e477fe6'
BSC_SLISBNB                       = '\xb0b84d294e0c75a6abe60171b70edeb2efd14a1b'
BSC_SLISBNB_OFT_ADAPTER           = '\x837cb07f6b8a98731856092457524ff37b25e7b3'
BSC_SLISBNBX                      = '\x4b30fcaa7945fe9fdefd2895aae539ba102ed6f6'
BSC_SLISBNBX_MINTER               = '\x2959c423bfe5cc6e41516599d982a29c0773f11a'
BSC_CLISBNB_LAUNCHPOOL_DIST       = '\x81a62b329cc8939494d8613f614171a9955a46e8'
ETH_SLISBNB_OFT                   = '\xf9b24c9364457ea85792179d285855753549ebaa'
```

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `synclub-contracts` (`ListaStakeManager.sol`, `IStakeManager.sol`, `SLisBNB.sol`), `lista-token/contracts/oft` and `lista-dao-contracts/contracts/ceros/slisBNBx.sol`. All listed topics and selectors were found as constants in the live BSC implementation bytecode (StakeManager impl `0xafe120d0…`, slisBNB impl `0xd9edeba7…`, OFT adapter). Live `eth_getLogs` on the StakeManager returned `Deposit` 19 and `RequestWithdraw` 13 in a 40k-block window.
- **Addresses:** parsed from the docs pages "Liquid Staking (slisBNB) — Smart Contract" and "clisBNB — Smart Contract" and from `lista-token/scripts/oft/slisBNBOftChains.json`, then existence-checked with `eth_getCode`. Proxy slots and ProxyAdmin `owner()` were read live. `symbol()` was read on slisBNB, slisBNBx and the Ethereum OFT.
- **Chain coverage:** the slisBNB, StakeManager and OFT addresses return `0x` on Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc.

Authoritative sources:
- [lista-dao/synclub-contracts](https://github.com/lista-dao/synclub-contracts) · [lista-dao/lista-token](https://github.com/lista-dao/lista-token) · [lista-dao/lista-dao-contracts](https://github.com/lista-dao/lista-dao-contracts)
- [Lista docs — Liquid Staking smart contracts](https://docs.bsc.lista.org/for-developer/liquid-staking-slisbnb/smart-contract) · [Cross-chain bridge](https://docs.bsc.lista.org/for-developer/liquid-staking-slisbnb/cross-chain-bridge) · [clisBNB smart contract](https://docs.bsc.lista.org/for-developer/clisbnb/smart-contract)
- Explorers: [BscScan](https://bscscan.com/address/0x1adB950d8bB3dA4bE104211D5AB038628e477fE6) · [Etherscan](https://etherscan.io/address/0xf9B24C9364457Ea85792179D285855753549eBAa)
