# Rootstock Token Bridge — Topics, Selectors, Addresses (Ethereum only; counterpart Rootstock)

**Status:** verified on 2026-09-29 against Ethereum mainnet RPC (`eth_getCode`, `eth_call`, EIP-1967 slots, `eth_getLogs`), `eth_getCode` on the seven other target chains, two `eth_getCode` calls to the public Rootstock node, the `rsksmart/tokenbridge` repository (`bridge/deployed/ethmainnet.json`, `bridge/deployed/rskmainnet.json`, contract sources), the Rootstock developer portal sources (`rsksmart/devportal`), and Sourcify.
**Scope:** the Ethereum side of the Rootstock (RSK) Token Bridge, a federated lock-and-mint bridge between Ethereum and Rootstock (chain 30): the `Bridge` proxy (escrow and entry point), the `Federation` (the signers' vote), `AllowTokens` (token list and limits), `SideTokenFactory`, the `ProxyAdmin` and the owner `MultiSigWallet`. Of the eight target chains, only Ethereum (chain ID 1) has a deployment. Topics and selectors are chain-agnostic; addresses are network-specific.

**Deprecated but live.** The Rootstock developer portal states: "The Token Bridge will no longer support moving assets between Ethereum and Rootstock." On 2026-09-29 the Ethereum bridge still reads `paused()=false`, and blocks 25,600,000–26,075,812 (about 66 days) hold one transfer in each direction. Monitor it for residual withdrawals and admin actions.

The flow is a **two-step claim**. Ethereum → Rootstock: the user calls `receiveTokensTo` (ERC-20) or `depositTo` (ETH, wrapped to WETH); the bridge escrows the token (or burns a side token) and emits `Cross`. Rootstock → Ethereum: each Federation member calls `voteTransaction`; at the threshold (2 of 5, read live) the Federation calls `Bridge.acceptTransfer`, which records the transfer (`AcceptedCrossTransfer`, no value moves); then the user, or a relayer with the user's signature, calls `claim` / `claimGasless`, which releases the tokens (`Claimed`). The key on both sides is the source-chain transaction hash, block hash and log index of the `Cross` event.

---

## 0. Contract families & versions

| Contract | Address (Ethereum) | Live implementation | Role |
|----------|--------------------|---------------------|------|
| **Bridge** (`AdminUpgradeabilityProxy`) | `0x12eD69359919Fc775bC2674860E8Fe2d2b6a7B5D` | `0x9F29F9BDA2052884D39F0f032b68aAa14FC363d8` (`Bridge`, `version()` = `"v3"`) | Entry point and **escrow** of Ethereum-native tokens; mints and burns side tokens. Proxy created at block 9,172,486. |
| **Federation** (proxy) | `0x5e29C223d99648C88610519f96E85E627b3ABe17` | `0x5631a6Ac95B6BDE690807085aAa70E3b2D9d76C5` (`Federation`, `"v2"`) | 5 members, `required()` = 2; calls `acceptTransfer`. |
| **AllowTokens** (proxy) | `0xA3FC98e0a7a979677BC14d541Be770b2cb0A15F3` | `0x118522603dc0B8490feC2b8DB92e6F1c66CD697c` (`AllowTokens`) | Token whitelist, per-type min / max / daily limits, confirmation counts. |
| SideTokenFactory | `0xF73C60863BF2930Bde2c69dF4CB8fE700Ae713fB` | — | Creates side tokens (prefix `"e"`, read from `symbolPrefix()`) for Rootstock-native tokens. |
| ProxyAdmin | `0xe4D351911A6d599F91A3DB1843e2ECb0f851E7e6` | — | EIP-1967 admin of the Bridge and Federation proxies; `owner()` = the MultiSig. |
| MultiSigWallet | `0x040007b1804ad78a97f541bebed377dcb60e4138` | — | Gnosis `MultiSigWallet` (legacy, not a Safe), 2 of 3; `owner()` of the Bridge, Federation and ProxyAdmin; receives the bridge fee. |
| Utils | `0x5f989f2f323a1732a565c9a3f694f2Fa8f0b6120` | — | Library contract from `ethmainnet.json`. |

The repository's `master` branch also holds a multi-chain Bridge (`IBridge.sol`) whose `Cross`, `AcceptedCrossTransfer`, `Claimed` and `NewSideToken` carry chain ids and have other topic0 values (§1.4). It is not the Ethereum implementation: 0 logs of those topics on Ethereum and BNB in the pinned window.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Bridge — transfer flow (emitter `0x12eD69359919Fc775bC2674860E8Fe2d2b6a7B5D`)

| topic0 | Event |
|--------|-------|
| `0x1e90de9ae4d02420648a650f45f089a1be18fbca324092544ea626f9833212b0` | `Cross(address indexed _tokenAddress, address indexed _from, address indexed _to, uint256 _amount, bytes _userData)` — **source leg** (Ethereum → Rootstock); `_amount` is after the fee; `_to` is the Rootstock recipient |
| `0x2858b8803acb87882fd2de49ce7572ae3e741fb8073cbe772fa50ce00bdfba22` | `AcceptedCrossTransfer(bytes32 indexed _transactionHash, address indexed _originalTokenAddress, address indexed _to, address _from, uint256 _amount, bytes32 _blockHash, uint256 _logIndex)` — **status only**: the Federation accepted a Rootstock → Ethereum transfer; no value moves |
| `0x42b1cb6263e8da47edf0583516eda1de16f729d26282f5791dc5b7af1010e925` | `Claimed(bytes32 indexed _transactionHash, address indexed _originalTokenAddress, address indexed _to, address _sender, uint256 _amount, bytes32 _blockHash, uint256 _logIndex, address _reciever, address _relayer, uint256 _fee)` — **destination leg**: tokens released to `_reciever` (the parameter name is misspelled in source); `_relayer` and `_fee` are set for `claimGasless` |
| `0x2ef93c4e96a4ef0b19497ff60c9e7360a8734f3d2cd27ae5318e43851734d17f` | `NewSideToken(address indexed _newSideTokenAddress, address indexed _originalTokenAddress, string _newSymbol, uint256 _granularity)` — a side token was created for a Rootstock-native token |

### 1.2 Bridge — admin

| topic0 | Event |
|--------|-------|
| `0x4a41a4d11aaf0c0c9e4311ac1d68b2b0134556da594779a2a35b0ddf7cd1eafb` | `FederationChanged(address _newFederation)` — **the account that can accept transfers changed** |
| `0x5f2c1fe803fd576d8af05ea156011cc9cc8c025bda24c1e85772fc05a0b3f1e3` | `AllowTokensChanged(address _newAllowTokens)` |
| `0x619936bc6e3618d0b8dc69bcc70134fe9d88f9967f3a8b8304e3183692521625` | `SideTokenFactoryChanged(address _newSideTokenFactory)` |
| `0x97e97c577f03bda90e2c9739011ec065ed5fbfb36ae217d20bb0d9be95e160cd` | `FeePercentageChanged(uint256 _amount)` — fee in units of 1/10,000 (live value 20 = 0.2%) |
| `0x0966c958966f6fac9ff807af074f8117eb2e9ce2b76390db7a158e9bdeb2485c` | `WrappedCurrencyChanged(address _wrappedCurrency)` |
| `0x983e436223c000a441c2443b394ca5fb4669a513fe86dc1dd44494047b514ad9` | `Upgrading(bool _isUpgrading)` — the owner froze (`true`) or unfroze transfers for an upgrade |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x6719d08c1888103bea251a4ed56406bd0c3e69723c8a1686e017e7bbe159b6f8` | `PauserAdded(address indexed account)` |
| `0xcd265ebaf09df2871cc7bd4133404a235ba12eff2041bb89d9c714a2621c7c7e` | `PauserRemoved(address indexed account)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` — Bridge, Federation, AllowTokens and ProxyAdmin |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — proxy implementation changed |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` — proxy admin changed |

### 1.3 Federation (emitter `0x5e29C223d99648C88610519f96E85E627b3ABe17`) and AllowTokens (emitter `0xA3FC98e0a7a979677BC14d541Be770b2cb0A15F3`)

| topic0 | Event |
|--------|-------|
| `0xd22894491aaa5bb67855bcff4b9730bdf7768be1e25f66ced9a7d7ad623bf291` | `Voted(address indexed federator, bytes32 indexed transactionHash, bytes32 indexed transactionId, address originalTokenAddress, address sender, address receiver, uint256 amount, bytes32 blockHash, uint32 logIndex)` — status only; one per member vote |
| `0xe21e4d3d66ef78424137270e65cfafe938736bb770702ab4fd630383e7820b73` | `Executed(address indexed federator, bytes32 indexed transactionHash, bytes32 indexed transactionId, address originalTokenAddress, address sender, address receiver, uint256 amount, bytes32 blockHash, uint32 logIndex)` — the vote reached `required`; the Federation called `acceptTransfer` in the same transaction |
| `0xbb00e6cbdccbb5b7549e189335249187223d88583604555326aa1d7ccbcad442` | `HeartBeat(address indexed sender, uint256 fedRskBlock, uint256 fedEthBlock, string federatorVersion, string nodeRskInfo, string nodeEthInfo)` — federator liveness |
| `0x72114e270de66b9d2710ecf140403e5e99b1574767d6a8197bdc8d807a46e7c7` | `MemberAddition(address indexed member)` — **a new signer** |
| `0x270bfc616dd36d5cb6b35aac93e6ef22b089c34e6f6ad6f0892797424840897b` | `MemberRemoval(address indexed member)` |
| `0xa3f1ee9126a074d9326c682f561767f710e927faa811f7a99829d49dc421797a` | `RequirementChange(uint256 required)` — **the vote threshold changed** |
| `0x9775531310b2880b61484ed85cbb0b491c8fde3a07f289c63b92551782794497` | `BridgeChanged(address bridge)` |
| `0x84480cc6a063ffd72c3eddf21e3ffd30db3e2b8e386ec3abf09c98ee9e0e8d34` | `UpdateTokensTransfered(address indexed _tokenAddress, uint256 _lastDay, uint256 _spentToday)` — AllowTokens; fires with every `Cross` (daily-limit bookkeeping) |
| `0x720764556647dd167f4229d6a4255ac86018e302a50fc29dd67a70edb7b314d0` | `SetToken(address indexed _tokenAddress, uint256 _typeId)` — AllowTokens; token whitelisted |
| `0xbf996b4fd74f0c7159bb017b1db415b0d9a6f13129f46d0b93309d170b78df31` | `AllowedTokenRemoved(address indexed _tokenAddress)` — AllowTokens |
| `0x1d2b256bb06ebc298b1980410a5e3b1e9bc4be642e8f26a58dc8a97d7fe2bbbb` | `TypeLimitsChanged(uint256 indexed _typeId, (uint256 min, uint256 max, uint256 daily, uint256 mediumAmount, uint256 largeAmount) limits)` — AllowTokens |
| `0xfcc55d4aea72e6d2d439843942c59b3141c952375a217e381f6a40e0b5ac4219` | `ConfirmationsChanged(uint256 _smallAmountConfirmations, uint256 _mediumAmountConfirmations, uint256 _largeAmountConfirmations)` — AllowTokens |

### 1.4 Repository multi-chain version (not deployed on Ethereum)

| topic0 | Event |
|--------|-------|
| `0xb2320a1ad388e1e16b142f7d2e822f31d8a2bbdd7d4f29260e7c203c5f45e849` | `Cross(address indexed _tokenAddress, address indexed _to, uint256 indexed _destinationChainId, address _from, uint256 _originChainId, uint256 _amount, bytes _userData)` |
| `0xddae5e892ad96ac0e35e9018a1a3e32ecd7f3dfe55ea34d9ab1e8faecd6ccb5a` | `AcceptedCrossTransfer(bytes32 indexed _transactionHash, address indexed _originalTokenAddress, address indexed _to, address _from, uint256 _amount, bytes32 _blockHash, uint256 _logIndex, uint256 _originChainId, uint256 _destinationChainId)` |
| `0xa7a84dcc6757cdf9b9122d3bbc42d58358c28dc4b09cc24349599a63c56c62fd` | `Claimed(bytes32 indexed _transactionHash, address indexed _originalTokenAddress, address indexed _to, address _sender, uint256 _amount, bytes32 _blockHash, uint256 _logIndex, address _reciever, address _relayer, uint256 _fee, uint256 _destinationChainId, uint256 _originChainId)` |
| `0x88dcf8b72e53287db29df3fee9a0f2cb07d1f986cee153aa7d7554405d5db017` | `NewSideToken(address indexed _newSideTokenAddress, address indexed _originalTokenAddress, string _newSymbol, uint256 _granularity, uint256 _chainId)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Bridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7813bea2` | `receiveTokensTo(address tokenToUse, address to, uint256 amount)` | **ERC-20 deposit**: `transferFrom` user → bridge, fee → owner, emits `Cross`. |
| `0xb760faf9` | `depositTo(address to)` | `payable`; ETH deposit, wrapped to WETH (`wrappedCurrency()`); emits `Cross` with the WETH address. |
| `0x0023de29` | `tokensReceived(address operator, address from, address to, uint256 amount, bytes userData, bytes)` | ERC-777 hook deposit; emits `Cross`. |
| `0x6a863191` | `acceptTransfer(address _originalTokenAddress, address _from, address _to, uint256 _amount, bytes32 _blockHash, bytes32 _transactionHash, uint32 _logIndex)` | Federation only; emits `AcceptedCrossTransfer`. |
| `0xb50277bb` | `claim((address to, uint256 amount, bytes32 blockHash, bytes32 transactionHash, uint32 logIndex) _claimData)` | **Payout**; emits `Claimed`. |
| `0xadc5fb64` | `claimFallback((address to, uint256 amount, bytes32 blockHash, bytes32 transactionHash, uint32 logIndex) _claimData)` | Payout to the original sender when `to` cannot receive. |
| `0x4beea506` | `claimGasless((address to, uint256 amount, bytes32 blockHash, bytes32 transactionHash, uint32 logIndex) _claimData, address _relayer, uint256 _fee, uint256 _deadline, uint8 _v, bytes32 _r, bytes32 _s)` | Relayer-submitted payout (EIP-712 signature of the recipient). |
| `0x37e76109` | `hasBeenClaimed(bytes32 transactionHash)` | View. |
| `0xda677037` | `hasCrossed(bytes32 transactionHash)` | View; accepted and waiting for a claim. |
| `0xafad80ac` | `getTransactionDataHash(address _to, uint256 _amount, bytes32 _blockHash, bytes32 _transactionHash, uint32 _logIndex)` | Pure; the stored claim hash. |
| `0x20e3bb00` | `createSideToken(uint256 _typeId, address _originalTokenAddress, uint8 _originalTokenDecimals, string _originalTokenSymbol, string _originalTokenName)` | Owner; emits `NewSideToken`. |
| `0xfa0caa16` | `changeFederation(address newFederation)` | Owner; emits `FederationChanged`. |
| `0x916dc59d` | `changeAllowTokens(address newAllowTokens)` | Owner. |
| `0x42cdb2c6` | `changeSideTokenFactory(address newSideTokenFactory)` | Owner. |
| `0xae06c1b7` | `setFeePercentage(uint256 amount)` | Owner. |
| `0x07c8f7b0` | `setUpgrading(bool _isUpgrading)` | Owner; emits `Upgrading`. |
| `0x8456cb59` | `pause()` | Pauser role. |
| `0x3f4ba83a` | `unpause()` | Pauser role. |
| `0x82dc1ec4` | `addPauser(address account)` | Pauser role; emits `PauserAdded`. |
| `0x11efbf61` | `getFeePercentage()` | View; 20. |
| `0xea217091` | `getFederation()` | View; the Federation proxy. |
| `0x54fd4d50` | `version()` | View; `"v3"`. |

### 2.2 Federation and AllowTokens

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x35d4aa9e` | `voteTransaction(address originalTokenAddress, address sender, address receiver, uint256 amount, bytes32 blockHash, bytes32 transactionHash, uint32 logIndex)` | Member only; emits `Voted` (and `Executed` at the threshold). |
| `0xfa6297ba` | `getTransactionId(address originalTokenAddress, address sender, address receiver, uint256 amount, bytes32 blockHash, bytes32 transactionHash, uint32 logIndex)` | Pure; the vote key. |
| `0xca6d56dc` | `addMember(address _newMember)` | Owner; emits `MemberAddition`. |
| `0x0b1ca49a` | `removeMember(address _oldMember)` | Owner; emits `MemberRemoval`. |
| `0xba51a6df` | `changeRequirement(uint256 _required)` | Owner; emits `RequirementChange`. |
| `0x8dd14802` | `setBridge(address _bridge)` | Owner; emits `BridgeChanged`. |
| `0x9eab5253` | `getMembers()` | View. |
| `0xdc8452cd` | `required()` | View; 2. |
| `0xb9a3b9dc` | `emitHeartbeat(uint256 fedRskBlock, uint256 fedEthBlock, string federatorVersion, string nodeRskInfo, string nodeEthInfo)` | Member liveness. |
| `0x78bf2b53` | `setToken(address token, uint256 typeId)` | AllowTokens owner; emits `SetToken`. |
| `0xbb698dad` | `addTokenType(string description, (uint256 min, uint256 max, uint256 daily, uint256 mediumAmount, uint256 largeAmount) limits)` | AllowTokens owner. |
| `0x601ad4c9` | `setConfirmations(uint256 _smallAmountConfirmations, uint256 _mediumAmountConfirmations, uint256 _largeAmountConfirmations)` | AllowTokens owner. |
| `0x9d27d226` | `getInfoAndLimits(address token)` | AllowTokens view. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on 2026-09-29. Wiring read live: Bridge `getFederation()`, `allowTokens()`, `sideTokenFactory()`, `wrappedCurrency()` → the Federation proxy, the AllowTokens proxy, the SideTokenFactory and WETH; Federation `bridge()` → the Bridge proxy; Bridge and Federation EIP-1967 admin slot → the ProxyAdmin; `owner()` of the Bridge, Federation and ProxyAdmin → the MultiSig.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (proxy) | `0x12eD69359919Fc775bC2674860E8Fe2d2b6a7B5D` | Entry point and escrow. 2,240-byte proxy. |
| Bridge implementation | `0x9F29F9BDA2052884D39F0f032b68aAa14FC363d8` | `Bridge` v3, 16,894 bytes, created at block 12,871,770. |
| **Federation** (proxy) | `0x5e29C223d99648C88610519f96E85E627b3ABe17` | Members vote here. |
| Federation implementation | `0x5631a6Ac95B6BDE690807085aAa70E3b2D9d76C5` | `Federation` v2. |
| AllowTokens (proxy) | `0xA3FC98e0a7a979677BC14d541Be770b2cb0A15F3` | Implementation `0x118522603dc0B8490feC2b8DB92e6F1c66CD697c`. |
| SideTokenFactory | `0xF73C60863BF2930Bde2c69dF4CB8fE700Ae713fB` | Side-token deployer. |
| ProxyAdmin | `0xe4D351911A6d599F91A3DB1843e2ECb0f851E7e6` | Upgrades the proxies. |
| MultiSigWallet (2 of 3) | `0x040007b1804ad78a97f541bebed377dcb60e4138` | Owner of everything above; fee receiver. |
| Federation members | `0x5eb6cECA6BdD82f4a38AAc0b957E6A4B5b1cCEba`, `0x8a9Ec366C1b359FeD1A7372Cf8607ec52963B550`, `0xA4398c6fF62E9b93B32b28Dd29BD27c6B106245f`, `0x358550C63F02cc16AdE1190DFc05dA50F079B2Cf`, `0x58b03353688E0a58473BC0E4f53f9c51F87B9A79` | The five signers (`getMembers()`); 2 votes accept a transfer. |

Rootstock-side counterparts (chain 30, outside the eight; from `rskmainnet.json` and the developer portal): Bridge proxy `0x9d11937e2179dc5270aa86a3f8143232d6da0e69` (2,240 bytes on the public Rootstock node), Bridge implementation `0x4e159f565555fc4eb27d864ff0bd308f1cefa0ac`, Federation proxy `0x7ecfda6072942577d36f939ad528b366b020004b` (2,165 bytes), AllowTokens proxy `0xcb789036894a83a008a2aa5b3c2dde41d0605a9a`, MultiSigWallet `0x040007b1804ad78a97f541bebed377dcb60e4138` (the same address as on Ethereum).

---

## 4. Cross-chain summary

| Chain | ID | Bridge | Federation / AllowTokens / ProxyAdmin / MultiSig | Note |
|-------|----|--------|---------------------------------------------------|------|
| **Ethereum** | 1 | ✅ `0x12eD69359919Fc775bC2674860E8Fe2d2b6a7B5D` | ✅ | The only EVM side among the eight. |
| Base | 8453 | — | — | no deployment: `eth_getCode` = `0x` at the five Ethereum addresses; the repository has no Base deployment |
| Arbitrum One | 42161 | — | — | same |
| Optimism | 10 | — | — | same |
| Polygon PoS | 137 | — | — | same |
| BNB Smart Chain | 56 | — | — | same for the Bridge, Federation, AllowTokens and ProxyAdmin; the MultiSig address holds an unrelated verified `Payroll` contract (8,764 bytes, another deployer): a decoy |
| Avalanche C-Chain | 43114 | — | — | same |
| Robinhood Chain | 4663 | — | — | same |

**No BNB side.** The repository holds BSC deployments only for testnets (`bridge/deployments/bsctestnet`, `bridge/deployments/rsktestnetbsc`), and the multi-chain `Cross` topic (§1.4) had 0 logs on BNB in the pinned window. For other routes, the Rootstock portal points to third-party cross-chain bridges; they are not part of this doc.

The counterparty is **Rootstock mainnet** (chain 30), outside the eight chains. The bridge uses EVM chain ids only in the undeployed multi-chain version; the deployed v3 has one route, Ethereum ↔ Rootstock.

---

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Bridge | EIP-1967 transparent (`AdminUpgradeabilityProxy`) | impl slot → `0x9F29F9BDA2052884D39F0f032b68aAa14FC363d8`; admin slot → the ProxyAdmin. | ProxyAdmin `owner()` = MultiSig (2 of 3); no timelock. |
| Federation | EIP-1967 transparent | impl slot → `0x5631a6Ac95B6BDE690807085aAa70E3b2D9d76C5`; admin slot → the ProxyAdmin. | Same. |
| AllowTokens | EIP-1967 proxy | impl → `0x118522603dc0B8490feC2b8DB92e6F1c66CD697c`. | Same. |
| SideTokenFactory, MultiSigWallet, ProxyAdmin | Not proxies | Full runtimes (11,672 / 11,209 / 2,844 bytes). | — |

EIP-1967 slots: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`.

---

## 6. Detection invariants & gotchas

1. **Source leg:** `receiveTokensTo` → ERC-20 `Transfer(user → Bridge)`, AllowTokens `UpdateTokensTransfered`, `Cross(token, from, to, amount after fee)`, then ERC-20 `Transfer(Bridge → MultiSig)` for the 0.2% fee. For a side token (a Rootstock-native asset), the bridge burns instead of escrowing. ETH arrives by `depositTo` as `msg.value` and is wrapped to WETH.
2. **Destination leg, two transactions.** (a) Federation: `Voted` per member, then `Executed` + Bridge `AcceptedCrossTransfer` in the vote that reaches 2. No tokens move. (b) `claim`: ERC-20 `Transfer(Bridge → recipient)` (or a side-token mint) + `Claimed`. Count value on `Claimed`, not on `AcceptedCrossTransfer`.
3. **Link key.** Rootstock → Ethereum: `_transactionHash` (topic 1 of `AcceptedCrossTransfer` and `Claimed`, topic 2 of `Voted` / `Executed`) is the Rootstock transaction hash of the source `Cross`; with `_blockHash` and `_logIndex` it identifies the log. Ethereum → Rootstock: the key is the Ethereum `Cross` log itself (transaction hash, block hash, log index); `Cross` carries no nonce. The Federation's `transactionId` (topic 3) is `getTransactionId` (selector `0xfa6297ba`, §2.2) over all seven fields.
4. **Pending claims.** An accepted transfer that nobody claimed stays in `hasCrossed` / not `hasBeenClaimed`. With the bridge deprecated, expect old claims to arrive long after acceptance.
5. **Drain and admin triggers.** `MemberAddition`, `MemberRemoval`, `RequirementChange` (2 of 5 is already low), `FederationChanged`, `AllowTokensChanged`, `SideTokenFactoryChanged`, `Upgraded` / `AdminChanged` on the proxies, `OwnershipTransferred`, `Upgrading(true)`, `Paused`. A large `Claimed`, or an `AcceptedCrossTransfer` with no matching Rootstock `Cross`, is the drain signal.
6. **Address reuse across chains.** `0x12eD69359919Fc775bC2674860E8Fe2d2b6a7B5D` is the Bridge on Ethereum but the **ProxyAdmin** on Rootstock (`rskmainnet.json`), and the MultiSig has the same address on both chains. Always key on `(chain id, address)`.
7. **`_reciever` vs `_to`.** In `Claimed`, `_to` (topic 3) is the recipient stated on the source chain; `_reciever` is where the tokens went (it differs after `claimFallback`). Use `_reciever` for the value flow.
8. **Topic reuse by other deployments.** The same open-source code runs on the testnets listed in `bridge/deployments/`, and a fork that keeps these event signatures emits the same topic0 values. Always filter by emitter and chain.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Bridge topics (deployed v3, chain-agnostic) =====
TOPIC_CROSS                      = '\x1e90de9ae4d02420648a650f45f089a1be18fbca324092544ea626f9833212b0'
TOPIC_ACCEPTED_CROSS_TRANSFER    = '\x2858b8803acb87882fd2de49ce7572ae3e741fb8073cbe772fa50ce00bdfba22'
TOPIC_CLAIMED                    = '\x42b1cb6263e8da47edf0583516eda1de16f729d26282f5791dc5b7af1010e925'
TOPIC_NEW_SIDE_TOKEN             = '\x2ef93c4e96a4ef0b19497ff60c9e7360a8734f3d2cd27ae5318e43851734d17f'
TOPIC_FEDERATION_CHANGED         = '\x4a41a4d11aaf0c0c9e4311ac1d68b2b0134556da594779a2a35b0ddf7cd1eafb'
TOPIC_ALLOW_TOKENS_CHANGED       = '\x5f2c1fe803fd576d8af05ea156011cc9cc8c025bda24c1e85772fc05a0b3f1e3'
TOPIC_FEE_PERCENTAGE_CHANGED     = '\x97e97c577f03bda90e2c9739011ec065ed5fbfb36ae217d20bb0d9be95e160cd'
TOPIC_UPGRADING                  = '\x983e436223c000a441c2443b394ca5fb4669a513fe86dc1dd44494047b514ad9'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFERRED      = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- ===== Federation / AllowTokens topics =====
TOPIC_FED_VOTED                  = '\xd22894491aaa5bb67855bcff4b9730bdf7768be1e25f66ced9a7d7ad623bf291'
TOPIC_FED_EXECUTED               = '\xe21e4d3d66ef78424137270e65cfafe938736bb770702ab4fd630383e7820b73'
TOPIC_FED_MEMBER_ADDITION        = '\x72114e270de66b9d2710ecf140403e5e99b1574767d6a8197bdc8d807a46e7c7'
TOPIC_FED_MEMBER_REMOVAL         = '\x270bfc616dd36d5cb6b35aac93e6ef22b089c34e6f6ad6f0892797424840897b'
TOPIC_FED_REQUIREMENT_CHANGE     = '\xa3f1ee9126a074d9326c682f561767f710e927faa811f7a99829d49dc421797a'
TOPIC_ALLOW_UPDATE_TRANSFERED    = '\x84480cc6a063ffd72c3eddf21e3ffd30db3e2b8e386ec3abf09c98ee9e0e8d34'

-- ===== Selectors =====
SEL_RECEIVE_TOKENS_TO            = '\x7813bea2'
SEL_DEPOSIT_TO                   = '\xb760faf9'
SEL_ACCEPT_TRANSFER              = '\x6a863191'
SEL_CLAIM                        = '\xb50277bb'
SEL_CLAIM_FALLBACK               = '\xadc5fb64'
SEL_CLAIM_GASLESS                = '\x4beea506'
SEL_VOTE_TRANSACTION             = '\x35d4aa9e'
SEL_CHANGE_FEDERATION            = '\xfa0caa16'
SEL_ADD_MEMBER                   = '\xca6d56dc'
SEL_CHANGE_REQUIREMENT           = '\xba51a6df'

-- ===== Addresses — Ethereum (chain ID 1), the only target chain with a deployment =====
ETH_RSK_BRIDGE                   = '\x12ed69359919fc775bc2674860e8fe2d2b6a7b5d'
ETH_RSK_BRIDGE_IMPL              = '\x9f29f9bda2052884d39f0f032b68aaa14fc363d8'
ETH_RSK_FEDERATION               = '\x5e29c223d99648c88610519f96e85e627b3abe17'
ETH_RSK_ALLOW_TOKENS             = '\xa3fc98e0a7a979677bc14d541be770b2cb0a15f3'
ETH_RSK_SIDE_TOKEN_FACTORY       = '\xf73c60863bf2930bde2c69df4cb8fe700ae713fb'
ETH_RSK_PROXY_ADMIN              = '\xe4d351911a6d599f91a3db1843e2ecb0f851e7e6'
ETH_RSK_MULTISIG                 = '\x040007b1804ad78a97f541bebed377dcb60e4138'
-- Rootstock (chain 30, outside the eight): Bridge 0x9d11937e2179dc5270aa86a3f8143232d6da0e69
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood: no deployment
```

---

## 8. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` (and `[0:4]`) from the verified ABIs of the live Bridge, Federation and AllowTokens implementations on Sourcify; §1.4 from `bridge/contracts/interface/IBridge.sol`, the v3 events cross-checked against `bridge/contracts/Bridge/IBridgeV3.sol`.
- **Addresses:** from `bridge/deployed/ethmainnet.json` and the developer portal's address page, each existence-checked with `eth_getCode`; implementations and the admin from the EIP-1967 slots; the members from `getMembers()`; the MultiSig owners (3) and `required()` (2) read live. Rootstock-side proxies checked with two `eth_getCode` calls to `public-node.rsk.co`.
- **State:** Bridge `version()` = `"v3"`, `paused()` = false, `isUpgrading()` = false, `getFeePercentage()` = 20 of `feePercentageDivider()` = 10,000, `symbolPrefix()` = `"e"`; Federation `version()` = `"v2"`, `required()` = 2 of 5 members.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26,072,222–26,075,812):** `Cross` 0, `Claimed` 0 (and 0 on the seven other chains from any emitter). Over blocks 25,600,000–26,075,812: Bridge 1 `Cross`, 1 `AcceptedCrossTransfer`, 1 `Claimed`; Federation 3 `Voted`, 1 `Executed`. The multi-chain topics (§1.4): 0 on Ethereum and BNB in the pinned window.
- **Sample transactions (receipts read):** deposit `0x6bfc0860aa18e2b4e57348c67567bae0c29e4d20400d6c453c03d18c48927e67` (`receiveTokensTo` DAI: `Transfer` user → Bridge, `UpdateTokensTransfered`, `Cross`, fee `Transfer` Bridge → MultiSig); acceptance `0xcbdb7d9085f85000edcc001a34f28addf268e5b6b50c38542e6203550a1ccc82` (member `voteTransaction` → `Voted`, `AcceptedCrossTransfer`, `Executed`); claim `0xf934f96ab27ac9bce0c4d1e242fed7f3b528fc2597bfd15b4e8b8424cb919a60` (`claim` → DAI `Transfer` Bridge → user, `Claimed`).

Authoritative sources (opened):
- [rsksmart/tokenbridge](https://github.com/rsksmart/tokenbridge) — `bridge/deployed/ethmainnet.json`, `bridge/deployed/rskmainnet.json`, `bridge/deployments/` (testnet folders only for BSC), `bridge/contracts/Bridge/IBridgeV3.sol`, `bridge/contracts/interface/IBridge.sol`
- Rootstock developer portal sources — [`rsksmart/devportal` token bridge addresses page](https://github.com/rsksmart/devportal/blob/main/docs/04-resources/06-guides/_tokenbridge/contractaddresses.md) (addresses and the deprecation notice)
- Sourcify — [Bridge impl](https://sourcify.dev/server/v2/contract/1/0x9f29f9bda2052884d39f0f032b68aaa14fc363d8) · [Federation impl](https://sourcify.dev/server/v2/contract/1/0x5631a6ac95b6bde690807085aaa70e3b2d9d76c5) · [AllowTokens impl](https://sourcify.dev/server/v2/contract/1/0x118522603dc0b8490fec2b8db92e6f1c66cd697c)
