# Sui Bridge — Topics, Selectors, Addresses (Ethereum only)

**Status:** verified on 2026-09-29 against Ethereum mainnet RPC (`eth_getCode`, `eth_call`, EIP-1967 slots, `eth_getLogs`), `eth_getCode` on the seven other target chains, the `MystenLabs/sui` repository (`bridge/evm/contracts`, `bridge/evm/deploy_configs/mainnet.json`), the Sui documentation, and Sourcify.
**Scope:** the Ethereum-side contracts of the Sui native bridge: `SuiBridge` (the entry point), `BridgeVault` (the escrow), `BridgeCommittee` (signature checks), `BridgeLimiter` (the USD rate limit) and `BridgeConfig` (tokens and prices). Sui is not an EVM chain, so the Sui side is not EVM-queryable. Of the eight target chains, only Ethereum (chain ID 1) has a deployment. Topics and selectors are chain-agnostic; addresses are network-specific.

The Sui Bridge is a **committee bridge**: the Sui validators hold ECDSA bridge keys, and a message is valid on Ethereum when the signers' stake reaches the threshold for its type (token transfer 3,334 of 10,000; freeze 450; unfreeze, upgrade, limit, price, blocklist and token add 5,001). A deposit (`bridgeERC20` / `bridgeETH`) moves the tokens into the `BridgeVault` and emits `TokensDeposited`; a withdrawal is a committee-signed message that anyone submits with `transferBridgedTokensWithSignatures`, which pays out of the vault and emits `TokensClaimed`.

`SuiBridge`, `BridgeCommittee`, `BridgeLimiter` and `BridgeConfig` are UUPS proxies (ERC-1967) that **only the committee can upgrade** (`upgradeWithSignatures`, stake 5,001). `BridgeVault` is an immutable `Ownable` contract owned by the `SuiBridge` proxy. The bridge uses its **own chain ids**: Ethereum mainnet is **10** and Sui mainnet is **0** (read live).

---

## 0. Contract families & versions

| Contract | Address (Ethereum) | Live implementation | Role |
|----------|--------------------|---------------------|------|
| **SuiBridge** (proxy) | `0xda3bD1fE1973470312db04551B65f401Bc8a92fD` | `0xa60f29201aeae592d9ab95747ae1cf425dbb036c` (`SuiBridge`) | Deposits, claims, emergency pause. |
| **BridgeVault** | `0x312e67b47A2A29AE200184949093D92369F80B53` | — (immutable) | **Escrow** of WBTC, WETH, USDT and LBTC; unwraps WETH for ETH payouts. `owner()` = SuiBridge. |
| **BridgeCommittee** (proxy) | `0xee2d52477a7c1a7be0b0347dbe7e3b15185b416f` | `0xa470ca92126bd6b6f6e98f3010c7e384f223b63b` | Stake-weighted signature checks; member blocklist. |
| **BridgeLimiter** (proxy) | `0x12183b0796bbc4678999100e8c6c5715d5736767` | `0xd754e54261e300ff9653567f03f74bfdef887340` | Rolling 24-hour USD limit on payouts. `owner()` = SuiBridge. |
| **BridgeConfig** (proxy) | `0x72d34fe82c71bf8120647518e5128e53106a1540` | `0xb083c462fa5b04899d87204a4566b3db90fec50c` | Chain id, token ids, token addresses, Sui decimals, USD prices. |

All five were created at block 20,811,249. The repository also holds `SuiBridgeV2.sol` (`bridgeERC20V2`, `TokensDepositedV2` with a timestamp); the live implementation is the first version, and `TokensDepositedV2` had 0 logs in the pinned window.

Token map (read live from `BridgeConfig`): id 0 SUI (no Ethereum address), id 1 BTC → WBTC `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` (8 Sui decimals), id 2 ETH → WETH `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` (8), id 3 USDC (no Ethereum address), id 4 USDT → `0xdAC17F958D2ee523a2206206994597C13D831ec7` (6), id 6 LBTC → `0x8236a87084f8B84306f72007F36F2618A5634494` (8). Ids 5 and 7–12 are empty.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 SuiBridge — transfer flow (emitter `0xda3bD1fE1973470312db04551B65f401Bc8a92fD`)

| topic0 | Event |
|--------|-------|
| `0xa0f1d54820817ede8517e70a3d0a9197c015471c5360d2119b759f0359858ce6` | `TokensDeposited(uint8 indexed sourceChainID, uint64 indexed nonce, uint8 indexed destinationChainID, uint8 tokenID, uint64 suiAdjustedAmount, address senderAddress, bytes recipientAddress)` — **source leg**; `sourceChainID` = 10, `destinationChainID` = 0; `suiAdjustedAmount` in Sui decimals; `recipientAddress` is a 32-byte Sui address |
| `0x933e8377dca7a8cf67d2bf865c4d8c1c45347815760900f9d2eb5655a06943af` | `TokensClaimed(uint8 indexed sourceChainID, uint64 indexed nonce, uint8 indexed destinationChainID, uint8 tokenID, uint256 erc20AdjustedAmount, bytes senderAddress, address recipientAddress)` — **destination leg**; `sourceChainID` = 0, `nonce` = the Sui-side deposit nonce; amount in token decimals |
| `0x0838fecaac9057733ed7f9bb6e8ecfacf0d9c68d2f9b06e84f8c7f6098814bfb` | `EmergencyOperation(uint64 nonce, bool paused)` — **committee freeze (`true`) or unfreeze (`false`)** |
| `0xdc69b57038334451ee12fd1742228917cea7f40dbd33cda5162e7e5754acee1c` | `ContractUpgraded(uint256 nonce, address proxy, address implementation)` — committee-signed upgrade; also on the committee, limiter and config proxies |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — ERC-1967, in the same transaction as `ContractUpgraded` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` — OpenZeppelin, with `EmergencyOperation(true)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` |
| `0x70ef4a8b6f5065985fc424842df9fc218ad4c4015e85bb4158770e34abbcd82c` | `TokensDepositedV2(uint8 indexed sourceChainID, uint64 indexed nonce, uint8 indexed destinationChainID, uint8 tokenID, uint64 suiAdjustedAmount, address senderAddress, bytes recipientAddress, uint256 timestampSeconds)` — **repository V2 only; not in the live implementation** |

### 1.2 BridgeCommittee, BridgeLimiter, BridgeConfig, BridgeVault (admin and configuration)

| topic0 | Event |
|--------|-------|
| `0x22a2e525910eeb1577657a78bc70deeffc0d24e756d63718b502b1a9b99769de` | `BlocklistUpdated(address[] updatedMembers, bool isBlocklisted)` — committee |
| `0x1a1b35eeb36118431e57f7a5ff9c4718f99197beb1f65fada60b6e46af6656ba` | `BlocklistUpdatedV2(uint64 nonce, address[] updatedMembers, bool isBlocklisted)` — committee (current form) |
| `0x2266d5ea4551f9e8a7c1ffe1c87131985d16d31b1ca809656328b4e19ec2b0f8` | `LimitUpdated(uint8 sourceChainID, uint64 newLimit)` — limiter |
| `0x253425292723148e4239ef77c5a481d0351c3440eaee94112b541e71a3754599` | `LimitUpdatedV2(uint64 nonce, uint8 sourceChainID, uint64 newLimit)` — limiter (current form); `newLimit` is USD with 8 decimals |
| `0x1c67469b467f869771dcc2fb28419e0225fff93861a184775e7af2fd916eef55` | `HourlyTransferAmountUpdated(uint32 hourUpdated, uint256 amount)` — declared in the limiter ABI; 0 logs in the pinned window despite 8 claims, and the repository source emits only `LimitUpdatedV2` |
| `0xa7e991a720243e0c1b8072c6972f6102e2609ab05652b7f7201eda2fe2319a5c` | `TokenAdded(uint8 tokenID, address tokenAddress, uint8 suiDecimal, uint64 tokenPrice)` — config |
| `0xa8c9f6401ba814ab2ccd92aaaf0ee583418ce404d9b20a70188e76fd74e59c70` | `TokensAddedV2(uint64 nonce, uint8[] tokenIDs, address[] tokenAddresses, uint8[] suiDecimals, uint64[] tokenPrices)` — config (current form) |
| `0x63c7b0537430440067accde2f4ff8d60cfb1ff84ad16fd272394102f9cd052d0` | `TokenPriceUpdated(uint8 tokenID, uint64 tokenPrice)` — config |
| `0xe89f01f7a3c23e3a6667361b69793ec8e62800df987fae26a83313f61730ad87` | `TokenPriceUpdatedV2(uint64 nonce, uint8 tokenID, uint64 tokenPrice)` — config (current form) |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` — vault and limiter; **the vault owner can move every escrowed token** |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

`Message` is the tuple `(uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload)`; message types: 0 token transfer, 1 blocklist, 2 emergency op, 3 bridge limit, 4 token price, 5 upgrade, 7 add EVM tokens.

### 2.1 SuiBridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x212afaff` | `bridgeERC20(uint8 tokenID, uint256 amount, bytes recipientAddress, uint8 destinationChainID)` | Pulls `amount` from the caller **straight into the vault**; emits `TokensDeposited`. |
| `0x9449ebd2` | `bridgeETH(bytes recipientAddress, uint8 destinationChainID)` | `payable`; ETH goes to the vault, which wraps it to WETH; emits `TokensDeposited` with token id 2. |
| `0xbeb0d55c` | `transferBridgedTokensWithSignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | Anyone may submit; checks stake, the limiter and `isTransferProcessed`; pays from the vault; emits `TokensClaimed`. |
| `0xa6f740f6` | `executeEmergencyOpWithSignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | Pause or unpause; emits `EmergencyOperation`. |
| `0xfa72a6d0` | `upgradeWithSignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | The only upgrade path (all four proxies); emits `ContractUpgraded`. |
| `0x5458ea9e` | `isTransferProcessed(uint64 nonce)` | View; replay guard for claims. |
| `0x5035bda2` | `nonces(uint8 messageType)` | View; `nonces(0)` = next deposit nonce (33,417 on 2026-09-29). |
| `0xd864e740` | `committee()` | View. |
| `0xfbfa77cf` | `vault()` | View. |
| `0x74b87f67` | `limiter()` | View. |
| `0x5c975abb` | `paused()` | View. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | Reverts unless called from `upgradeWithSignatures`. |

### 2.2 BridgeCommittee, BridgeLimiter, BridgeConfig, BridgeVault

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf188949c` | `verifySignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | Committee view; reverts below the stake threshold. |
| `0xf6f66e98` | `updateBlocklistWithSignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | Committee; blocks or unblocks members. |
| `0x5b1adbef` | `committeeStake(address committeeMember)` | View; stake in basis points of 10,000. |
| `0xe5c7160b` | `blocklist(address committeeMember)` | View. |
| `0x97c39b13` | `updateLimitWithSignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | Limiter; emits `LimitUpdatedV2`. |
| `0x2c4535af` | `chainLimits(uint8 chainID)` | Limiter view; `chainLimits(0)` = 5,000,000,000,000,000 (USD 50,000,000, 8 decimals). |
| `0xc6b478dd` | `calculateWindowAmount(uint8 chainID)` | Limiter view; USD paid out in the last 24 hours. |
| `0x9373d391` | `recordBridgeTransfers(uint8 chainID, uint8 tokenID, uint256 amount)` | Limiter; owner (SuiBridge) only. |
| `0xbfb5d846` | `updateTokenPriceWithSignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | Config; price feeds the limiter. |
| `0x43025664` | `addTokensWithSignatures(bytes[] signatures, (uint8 messageType, uint8 version, uint64 nonce, uint8 chainID, bytes payload) message)` | Config; adds token ids. |
| `0xe5324889` | `tokenAddressOf(uint8 tokenID)` | Config view. |
| `0x71ceee4f` | `tokenSuiDecimalOf(uint8 tokenID)` | Config view. |
| `0xdfc3db3d` | `tokenPriceOf(uint8 tokenID)` | Config view; USD with 8 decimals. |
| `0xadc879e9` | `chainID()` | Config view; 10. |
| `0x73209533` | `isChainSupported(uint8 chainId)` | Config view; true only for 0. |
| `0x9db5dbe4` | `transferERC20(address tokenAddress, address recipientAddress, uint256 amount)` | Vault; owner only. |
| `0x7b1a4909` | `transferETH(address recipientAddress, uint256 amount)` | Vault; owner only; unwraps WETH. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Vault and limiter; owner only. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on 2026-09-29. Wiring read live: SuiBridge `committee()`, `vault()`, `limiter()` → the addresses below; committee `config()` → the config proxy; vault and limiter `owner()` → SuiBridge; vault `wETH()` → WETH.

| Role | Address | One-liner |
|------|---------|-----------|
| **SuiBridge** (proxy) | `0xda3bD1fE1973470312db04551B65f401Bc8a92fD` | Entry point: deposits, claims, emergency ops. 170-byte proxy. |
| **BridgeVault** | `0x312e67b47A2A29AE200184949093D92369F80B53` | The escrow. 1,866 bytes, not a proxy. |
| BridgeCommittee (proxy) | `0xee2d52477a7c1a7be0b0347dbe7e3b15185b416f` | Committee keys and stake. |
| BridgeLimiter (proxy) | `0x12183b0796bbc4678999100e8c6c5715d5736767` | 24-hour USD limit. |
| BridgeConfig (proxy) | `0x72d34fe82c71bf8120647518e5128e53106a1540` | Tokens, prices, chain ids. |
| SuiBridge implementation | `0xa60f29201aeae592d9ab95747ae1cf425dbb036c` | 15,050 bytes. |
| BridgeCommittee implementation | `0xa470ca92126bd6b6f6e98f3010c7e384f223b63b` | 9,811 bytes. |
| BridgeLimiter implementation | `0xd754e54261e300ff9653567f03f74bfdef887340` | 9,892 bytes. |
| BridgeConfig implementation | `0xb083c462fa5b04899d87204a4566b3db90fec50c` | 10,702 bytes. |

The committee is the Sui validator set's bridge keys (96 members in `deploy_configs/mainnet.json`); the contract has no member-list getter, so read `committeeStake(address)` per member.

---

## 4. Cross-chain summary

| Chain | ID | SuiBridge | BridgeVault | Committee / Limiter / Config | Note |
|-------|----|-----------|-------------|------------------------------|------|
| **Ethereum** | 1 | ✅ `0xda3bD1fE1973470312db04551B65f401Bc8a92fD` | ✅ `0x312e67b47A2A29AE200184949093D92369F80B53` | ✅ | Bridge chain id 10. |
| Base | 8453 | — | — | — | no deployment: `eth_getCode` = `0x` at all five Ethereum addresses; `BridgeConfig` supports only chain id 0 |
| Arbitrum One | 42161 | — | — | — | same |
| Optimism | 10 | — | — | — | same |
| Polygon PoS | 137 | — | — | — | same |
| BNB Smart Chain | 56 | — | — | — | same |
| Avalanche C-Chain | 43114 | — | — | — | same |
| Robinhood Chain | 4663 | — | — | — | same |

The counterparty is **Sui mainnet** (bridge chain id 0), outside the eight chains. Other bridge chain ids in the deploy configs: Sui testnet 1, Sui custom 2, Ethereum Sepolia 11 (from `11155111.json`).

---

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| SuiBridge, BridgeCommittee, BridgeLimiter, BridgeConfig | UUPS (ERC-1967) | 170-byte proxies with one runtime hash (`0xfc3c26f696152e6e4e4b7ffc2f483b259be216f7253f4847a4acef3d9b54563f`); impl slot → §3. | **Committee only:** `upgradeWithSignatures` sets a one-shot flag that `_authorizeUpgrade` requires (stake 5,001 of 10,000). No admin key and no timelock. |
| BridgeVault | Immutable `Ownable` | 1,866-byte runtime, no proxy slot. | None. Its owner (SuiBridge) moves funds; an ownership change would emit `OwnershipTransferred`. |

EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. An upgrade emits both `ContractUpgraded` (with the message nonce) and `Upgraded`.

---

## 6. Detection invariants & gotchas

1. **Source leg:** `bridgeERC20` → ERC-20 `Transfer(user → BridgeVault)` + `TokensDeposited`. `bridgeETH` → ETH `msg.value` to the vault (the vault wraps it: a WETH `Deposit` with the vault as `dst`) + `TokensDeposited(tokenID = 2)`. The tokens go to the vault, not to the SuiBridge proxy.
2. **Destination leg:** `transferBridgedTokensWithSignatures` → ERC-20 `Transfer(BridgeVault → recipient)` (or, for token id 2, a WETH `Withdrawal` by the vault and an internal ETH transfer) + `TokensClaimed`. `tx.from` is whoever submitted the signatures, often the recipient.
3. **Link key:** `(sourceChainID, nonce)`, topics 1 and 2 of both events. Ethereum→Sui: `(10, nonce)` from `TokensDeposited`; the Sui-side claim is not EVM-queryable. Sui→Ethereum: `(0, nonce)` in `TokensClaimed`; `isTransferProcessed(nonce)` is the replay guard.
4. **Decimals differ by leg.** `TokensDeposited.suiAdjustedAmount` uses the Sui decimals (8 for WBTC, WETH and LBTC; 6 for USDT); `TokensClaimed.erc20AdjustedAmount` uses the token's own decimals (18 for WETH). Convert before you compare.
5. **No refund or cancel path on Ethereum.** A deposit is final once `TokensDeposited` is emitted. A payout above the limiter window reverts (`limitNotExceeded`) and can be resubmitted later.
6. **Drain and admin triggers.** `ContractUpgraded` / `Upgraded` on any proxy; `EmergencyOperation` (a freeze needs only 450 stake; watch `paused = false` too); `LimitUpdatedV2` (a higher limit weakens the brake); `TokenPriceUpdatedV2` (a lower price lets more value through the USD limit); `TokensAddedV2`; `BlocklistUpdatedV2`; `OwnershipTransferred` on the vault. Large `TokensClaimed` amounts, or a burst of claims near the $50,000,000 window, are the drain signal.
7. **The limiter caps only payouts on Ethereum.** `chainLimits(0)` bounds the USD value leaving the vault in 24 hours; deposits into the vault are not limited on Ethereum. The Sui docs quote a $7 million Sui→Ethereum limit; the live value is $50,000,000 (`chainLimits(0)`, read 2026-09-29).
8. **`HourlyTransferAmountUpdated` does not fire.** It is in the limiter ABI, but it had 0 logs in the window with 8 claims. Measure throughput from `TokensClaimed`, or read `calculateWindowAmount(0)`.
9. **Two deposit functions, one event.** Filter `TokensDeposited` by `tokenID` to split ETH from ERC-20 deposits. SUI (id 0) and USDC (id 3) have no Ethereum address, so they cannot leave the vault on Ethereum.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== SuiBridge topics (chain-agnostic) =====
TOPIC_TOKENS_DEPOSITED           = '\xa0f1d54820817ede8517e70a3d0a9197c015471c5360d2119b759f0359858ce6'
TOPIC_TOKENS_CLAIMED             = '\x933e8377dca7a8cf67d2bf865c4d8c1c45347815760900f9d2eb5655a06943af'
TOPIC_EMERGENCY_OPERATION        = '\x0838fecaac9057733ed7f9bb6e8ecfacf0d9c68d2f9b06e84f8c7f6098814bfb'
TOPIC_CONTRACT_UPGRADED          = '\xdc69b57038334451ee12fd1742228917cea7f40dbd33cda5162e7e5754acee1c'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_TOKENS_DEPOSITED_V2_REPO   = '\x70ef4a8b6f5065985fc424842df9fc218ad4c4015e85bb4158770e34abbcd82c'
-- ===== Committee / limiter / config / vault topics =====
TOPIC_BLOCKLIST_UPDATED_V2       = '\x1a1b35eeb36118431e57f7a5ff9c4718f99197beb1f65fada60b6e46af6656ba'
TOPIC_LIMIT_UPDATED_V2           = '\x253425292723148e4239ef77c5a481d0351c3440eaee94112b541e71a3754599'
TOPIC_TOKEN_PRICE_UPDATED_V2     = '\xe89f01f7a3c23e3a6667361b69793ec8e62800df987fae26a83313f61730ad87'
TOPIC_TOKENS_ADDED_V2            = '\xa8c9f6401ba814ab2ccd92aaaf0ee583418ce404d9b20a70188e76fd74e59c70'
TOPIC_OWNERSHIP_TRANSFERRED      = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== Selectors =====
SEL_BRIDGE_ERC20                 = '\x212afaff'
SEL_BRIDGE_ETH                   = '\x9449ebd2'
SEL_TRANSFER_WITH_SIGNATURES     = '\xbeb0d55c'
SEL_EMERGENCY_OP_WITH_SIGNATURES = '\xa6f740f6'
SEL_UPGRADE_WITH_SIGNATURES      = '\xfa72a6d0'
SEL_UPDATE_LIMIT_WITH_SIGNATURES = '\x97c39b13'
SEL_UPDATE_PRICE_WITH_SIGNATURES = '\xbfb5d846'
SEL_ADD_TOKENS_WITH_SIGNATURES   = '\x43025664'
SEL_UPDATE_BLOCKLIST_WITH_SIGS   = '\xf6f66e98'
SEL_VAULT_TRANSFER_ERC20         = '\x9db5dbe4'
SEL_VAULT_TRANSFER_ETH           = '\x7b1a4909'

-- ===== Addresses — Ethereum (chain ID 1), the only chain with a deployment =====
ETH_SUI_BRIDGE                   = '\xda3bd1fe1973470312db04551b65f401bc8a92fd'
ETH_SUI_BRIDGE_VAULT             = '\x312e67b47a2a29ae200184949093d92369f80b53'
ETH_SUI_BRIDGE_COMMITTEE         = '\xee2d52477a7c1a7be0b0347dbe7e3b15185b416f'
ETH_SUI_BRIDGE_LIMITER           = '\x12183b0796bbc4678999100e8c6c5715d5736767'
ETH_SUI_BRIDGE_CONFIG            = '\x72d34fe82c71bf8120647518e5128e53106a1540'
ETH_SUI_BRIDGE_IMPL              = '\xa60f29201aeae592d9ab95747ae1cf425dbb036c'
ETH_WBTC                         = '\x2260fac5e5542a773aa44fbcfedf7c193bc2c599'
ETH_WETH                         = '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
ETH_USDT                         = '\xdac17f958d2ee523a2206206994597c13d831ec7'
ETH_LBTC                         = '\x8236a87084f8b84306f72007f36f2618a5634494'
-- Bridge chain ids: Ethereum 10, Sui 0. Token ids: 1 WBTC, 2 WETH, 4 USDT, 6 LBTC.
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood: no deployment
```

---

## 8. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` (and `[0:4]`) from the verified ABIs of the five live implementations on Sourcify; `TokensDepositedV2` from `SuiBridgeV2.sol` in the repository. Stake thresholds and message types from `BridgeUtils.sol`; the upgrade gate from `CommitteeUpgradeable.sol`; the vault behavior from `BridgeVault.sol`.
- **Addresses:** the SuiBridge proxy from the Sui docs; the other four from live getters (`committee()`, `vault()`, `limiter()`, `config()`); implementations from the EIP-1967 slot and named by Sourcify. Each existence-checked with `eth_getCode` on Ethereum; `eth_getCode` = `0x` at all five addresses on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain.
- **State:** `paused()` = false; `chainID()` = 10; `isChainSupported(0)` = true and false for 1–8; the token map, Sui decimals and USD prices (WBTC 101,000, WETH 3,300, USDT 1, LBTC 90,000) from `BridgeConfig`; `chainLimits(0)` and `calculateWindowAmount(0)` (USD 1,087,280.85 at read time) from the limiter; `nonces(0)` = 33,417.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26,072,222–26,075,812):** `TokensDeposited` 4, `TokensClaimed` 8, `EmergencyOperation` 0, `TokensDepositedV2` 0 (any emitter), `HourlyTransferAmountUpdated` 0 (limiter). The seven other chains: 0 `TokensDeposited` and 0 `TokensClaimed` logs from any emitter.
- **Sample transactions (receipts read):** deposit `0x1abaff3e06705c753d3728251e2216816b94c7760e4ab787880f073f6afccc1b` (`bridgeERC20`: USDT `Transfer` user → vault, `TokensDeposited(10, 33,391, 0)`); claim `0x75fbd883f6bec182ba46e36c0f198eb45de195c2f03c1ca416942bfc80609dfa` (`transferBridgedTokensWithSignatures`: USDT `Transfer` vault → user, `TokensClaimed(0, 24,159, 10)`).

Authoritative sources (opened):
- [MystenLabs/sui — `bridge/evm`](https://github.com/MystenLabs/sui/tree/main/bridge/evm) (`contracts/SuiBridge.sol`, `SuiBridgeV2.sol`, `BridgeVault.sol`, `BridgeCommittee.sol`, `BridgeLimiter.sol`, `BridgeConfig.sol`, `utils/BridgeUtils.sol`, `utils/CommitteeUpgradeable.sol`, `deploy_configs/mainnet.json`, `deploy_configs/11155111.json`)
- Sui docs — [Sui Bridge](https://docs.sui.io/concepts/tokenomics/sui-bridging)
- Sourcify — [SuiBridge impl](https://sourcify.dev/server/v2/contract/1/0xa60f29201aeae592d9ab95747ae1cf425dbb036c) · [BridgeCommittee impl](https://sourcify.dev/server/v2/contract/1/0xa470ca92126bd6b6f6e98f3010c7e384f223b63b) · [BridgeLimiter impl](https://sourcify.dev/server/v2/contract/1/0xd754e54261e300ff9653567f03f74bfdef887340) · [BridgeConfig impl](https://sourcify.dev/server/v2/contract/1/0xb083c462fa5b04899d87204a4566b3db90fec50c) · [BridgeVault](https://sourcify.dev/server/v2/contract/1/0x312e67b47a2a29ae200184949093d92369f80b53)
