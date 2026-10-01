# Circle Gateway — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + Avalanche; NOT BNB, NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, Circle's Gateway contract-address and supported-blockchain pages, and the canonical `circlefin/evm-gateway-contracts` repository (commit `fd51093c`, 2026-09-02, release 1.3.0). Topics and selectors recomputed as `keccak256(signature)` and matched against the deployed implementation bytecode. Addresses existence-checked with `eth_getCode`; proxy implementations read from the EIP-1967 slot; roles read with `eth_call`.
**Scope:** Circle Gateway, the unified USDC balance: **GatewayWallet** (deposits, burns, withdrawals, batches) and **GatewayMinter** (attested mints). One vanity address per contract, the same on the six deployed target chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137) and Avalanche C-Chain (43114). **BNB Smart Chain (56) and Robinhood Chain (4663) have no deployment.** Topics and selectors are chain-agnostic; addresses and roles are network-specific. Circle CCTP is a different product: see [../cctp/README.md](../cctp/README.md).

Gateway is not a message bridge. A user first deposits USDC into the GatewayWallet of a chain. Circle's off-chain Gateway system adds the deposits of all chains into one unified balance. To move value, the depositor (or its delegate) signs a burn intent and sends it to Circle's Gateway API (`/v1/transfer`). The API returns an attestation signed by a Circle attestation signer. The user (or a relayer) calls `gatewayMint` on the destination GatewayMinter, which mints new USDC to the recipient. After that mint is final, Circle submits `gatewayBurn` on the source GatewayWallet: the Wallet deducts the depositor's balance, pays the fee and burns the rest.

Three facts to know before indexing:

1. **The payout comes before the burn.** `AttestationUsed` (destination) is emitted first; `GatewayBurned` (source) follows minutes later, in a transaction that Circle sends. The deposit that funds the transfer can be days older. Attribute a mint to the depositor's balance, not to the burn transaction.
2. **`transferSpecHash` is the link key, on chain on both sides.** It is topic3 of `GatewayBurned` and topic3 of `AttestationUsed`. A source domain can equal the destination domain (a same-chain transfer, Circle's "instant withdrawal").
3. **Value moves without token transfers.** `submitBatch` (event `BatchProcessed`) moves balance between depositors inside the Wallet, and the unified balance lets a deposit on chain A pay a mint on chain B. The ERC-20 trail alone cannot follow Gateway value.

---

## 0. Contract families & the flow

| Contract | Role | Proxy | Chains |
|----------|------|-------|--------|
| **GatewayWallet** | Holds deposited USDC. Keeps per-depositor `available` and `withdrawing` balances. Burns on attested transfers, runs batches and trustless withdrawals. | **UUPS** (ERC1967Proxy, 163-byte runtime) | ETH, Base, Arb, OP, Poly, Avax |
| **GatewayMinter** | Verifies Circle attestations and mints USDC to the recipient. | **UUPS** (ERC1967Proxy, 163-byte runtime) | ETH, Base, Arb, OP, Poly, Avax |
| USDC (FiatToken) | The token. The GatewayMinter is a USDC minter (`tokenMintAuthority(USDC)` = `0x0` on every chain, so the Minter calls `USDC.mint` directly). | FiatToken proxy | per chain (§3–§8) |
| Circle off-chain system | Gateway API, attestation signer, burn signer, batch signer. | not on chain | — |
| xReserve (related Circle product) | Calls `depositFor` into the GatewayWallet. Seen on Ethereum at `0x8888888199b2df864bf678259607d6d5ebb4e3ce` (verified name `xReserve`; Circle's xReserve repository gives the mainnet prefix `0x8888888`). Not in Circle's Gateway list. | EIP-1967 | ETH (observed) |

| Leg | Chain | Call (contract) | Event | Value movement in the same transaction |
|-----|-------|-----------------|-------|------------------------------------------|
| Fund (source leg, part 1) | any deployed chain | `deposit*` / `depositFor` (Wallet) | `Deposited` | USDC `Transfer(sender → Wallet)` |
| Request | off chain | burn intent to the Gateway API | — | — |
| **Payout (destination leg)** | destination | `gatewayMint` (Minter) | `AttestationUsed` | USDC `Mint(minter = GatewayMinter)` + `Transfer(0x0 → recipient)` |
| **Settlement (source leg, part 2)** | source | `gatewayBurn` (Wallet), Circle-submitted | `GatewayBurned` (+ `InsufficientBalance` on a shortfall) | USDC `Transfer(Wallet → feeRecipient)` (fee) + `Transfer(Wallet → 0x0)` + `Burn(burner = Wallet)` |
| Ledger batch | any | `submitBatch` (Wallet), Circle-submitted | `BatchProcessed` | **none** (internal balances only) |
| Exit start | source | `initiateWithdrawal` (Wallet) | `WithdrawalInitiated` | none (status only) |
| **Refund / exit** | source | `withdraw` (Wallet), after the delay | `WithdrawalCompleted` | USDC `Transfer(Wallet → depositor)` |
| Expiry | — | intent `maxBlockHeight` / attestation `maxBlockHeight` | none | An expired attestation reverts in `gatewayMint`; the balance stays in the Wallet. |

**Gateway domains = CCTP domains** (read live with `domain()` on both contracts): Ethereum `0`, Avalanche `1`, Optimism `2`, Arbitrum `3`, Base `6`, Polygon PoS `7`. BNB (CCTP domain 17) and Robinhood Chain (CCTP domain 35) have no Gateway contracts. Off-target Gateway domains per Circle: Solana 5, Unichain 10, Sonic 13, World Chain 14, Sei 16, HyperEVM 19, Arc 26.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 GatewayWallet — value and status events (emitter `0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x4174a9435a04d04d274c76779cad136a41fde6937c56241c09ab9d3c7064a1a9` | `Deposited(address indexed token, address indexed depositor, address indexed sender, uint256 value)` | **Source leg, funding.** The Wallet pulls `value` from `sender` and credits `depositor`'s available balance. |
| `0x12ee2719e7e2dec9f2a0041286b66669153dff0d36719f692b8bbaa4dfe0aa87` | `GatewayBurned(address indexed token, address indexed depositor, bytes32 indexed transferSpecHash, uint32 destinationDomain, bytes32 destinationRecipient, address signer, uint256 value, uint256 fee, uint256 fromAvailable, uint256 fromWithdrawing)` | **Source leg, settlement.** The Wallet burns `value` and pays `fee` to the fee recipient. It comes after the destination mint. |
| `0x5fab62745de032ad35a05146c51710fd80871be06cb193722c40f011df352f0c` | `InsufficientBalance(address indexed token, address indexed depositor, uint256 value, uint256 availableBalance, uint256 withdrawingBalance)` | **Shortfall.** A burn or a batch asked for more than the depositor's balance. The mint was already paid. Also declared on the Minter base contract; only the Wallet emits it. |
| `0x5f9a559874d8abe05a98d167b78d2012697505ea3e7bcdba906e7b6084014c65` | `WithdrawalInitiated(address indexed token, address indexed depositor, uint256 value, uint256 remainingAvailable, uint256 totalWithdrawing, uint256 withdrawalBlock)` | **Status only.** No token moves. The balance moves to "withdrawing" until `withdrawalBlock`. |
| `0xb00382203b46c3b6ad0a2d7af0268e334bd9406256a7c7ba8f7fc8bc47f8cde9` | `WithdrawalCompleted(address indexed token, address indexed depositor, uint256 value)` | **Refund path (trustless exit).** The Wallet transfers `value` USDC to `depositor`. |
| `0x8e9878875610f80a970e0cea1889a4c7de3012c1a52ae169d9d5d3ab2c08b670` | `BatchProcessed(bytes32 indexed batchId, address indexed signer, address indexed tokenAddress)` | **Ledger only.** Balances move between depositors inside the Wallet. No token moves. |

`GatewayBurned` data layout: `destinationDomain`, `destinationRecipient` (bytes32; low 20 bytes on EVM), `signer` (the depositor or its delegate), `value` (burned), `fee` (to the fee recipient), `fromAvailable` + `fromWithdrawing` (the two balance buckets that paid `value + fee`).

### 1.2 GatewayWallet — delegation and admin events

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xe91cba149cb264c22b997b1a69e785ad1562a07f83318cd0c985ba1be6e66099` | `DelegateAdded(address indexed token, address indexed depositor, address delegate)` | A depositor lets `delegate` sign burn intents for its balance. |
| `0xf706b3b70da5d5dada9b3c7d9f14e4f6c280183742a82ea2f951653070b0f195` | `DelegateRemoved(address indexed token, address indexed depositor, address delegate)` | Status only. |
| `0x895cdec14fd06461967f67fd12f3dc81c22b59fe80d1caf6f07b1902a8eaa35e` | `BurnSignerAdded(address indexed signer)` | Admin. A new key can authorize `gatewayBurn` calldata. |
| `0x61bf1e503074577bd48a3a903d7b74860236be7560e7324f6614d093a166ff45` | `BurnSignerRemoved(address indexed signer)` | Admin. |
| `0xceb230c3aed7aaaf620d28e444845b73c1083c4011d91d07e0cf321ef07b8016` | `BatchSignerAdded(address indexed signer)` | Admin. A new key can authorize `submitBatch` calldata. **High severity** (it can move balances between depositors). |
| `0x0d46aa3c36e0d3ca3d9255a77e39f993dc0513a8aecf73b2f4d14f995ec05e46` | `BatchSignerRemoved(address indexed signer)` | Admin. |
| `0x0bc21fe5c3ab742ff1d15b5c4477ffbacf1167e618228078fa625edebe7f331d` | `FeeRecipientChanged(address indexed oldFeeRecipient, address indexed newFeeRecipient)` | Admin. Destination of every burn fee. |
| `0xab3f1d5eaee409b7067167f77f1fa3f8a863366d6fb2b88559cd4f9b8e03e182` | `WithdrawalDelayChanged(uint256 indexed oldDelay, uint256 indexed newDelay)` | Admin. The trustless-exit delay, in blocks. |
| `0xe7fb698e5322fe65a384378258ac9736675fefb632b12521d6bc01b7a40e3d3d` | `ContractSignatureSignerAdded(address indexed signer)` | Admin (1.3.0). A key that re-signs ERC-1271 burn intents. |
| `0x95547dda5ebb10c9cc4b71db26ccd049c0c0149f1ab489e20e763760f70b4d83` | `ContractSignatureSignerRemoved(address indexed signer)` | Admin (1.3.0). |
| `0x616cc662cea3b5dff33daa1a10848b026312cbaa9ecde0c72b4c7ef52e73ba2c` | `ContractSignerAllowlisted(address indexed contractAddr)` | Admin (1.1.0). A contract that may sign burn intents with ERC-1271. |
| `0xc2656aabcb7557615392742b8b6916a8e7dfccfe39d6c1ac969b403de4768403` | `ContractSignerDisallowed(address indexed contractAddr)` | Admin. |
| `0xacb19fad966932f7cf955011d7df0b4791e53516cea6ea15b5093c45aa1a8dde` | `ContractSignersAllowlisterChanged(address indexed oldAllowlister, address indexed newAllowlister)` | Admin role change. |
| `0x6fc40ada044f92e006fcc2a0459f95ce12dfafee15ffe7f09ece2f08ef4c7d08` | `ContractSignersDisallowlisterChanged(address indexed oldDisallowlister, address indexed newDisallowlister)` | Admin role change. |

### 1.3 GatewayMinter (emitter `0x2222222d7164433c4C09B0b0D809a9b52C04C205`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbb312ce0cc311b2cb0746e09ccd2f91fdb9e2ac755d2f11c65300eb0d0fffd63` | `AttestationUsed(address indexed token, address indexed recipient, bytes32 indexed transferSpecHash, uint32 sourceDomain, bytes32 sourceDepositor, bytes32 sourceSigner, uint256 value)` | **Destination leg (payout).** USDC is minted to `recipient` in the same transaction. |
| `0x09b9e0aeb0d8dd390c8ab392ed51b6cbc0e6f3a2ddae0149cec4dd4acf13d7a9` | `AttestationSignerAdded(address indexed signer)` | Admin. A new key can sign mint attestations. **High severity.** |
| `0xfdf1ac7bfb61a45532dcc5b24ecc2b3373a97f45b89df6489ac493f873dd6548` | `AttestationSignerRemoved(address indexed signer)` | Admin. |
| `0x5c3cb1b340c7f4e8dfc2058a7e8992362e063c9ded5e14aa21e23e8856ee1831` | `MintAuthorityChanged(address indexed token, address indexed oldMintAuthority, address indexed newMintAuthority)` | Admin. The contract that the Minter calls to mint. |

### 1.4 Both contracts — pause, denylist, token support, upgrade, ownership

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | OpenZeppelin `PausableUpgradeable`. Deposits, burns, mints, batches and withdrawals stop. |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |
| `0x95bb211a5a393c4d30c3edc9a745825fba4e6ad3e3bb949e6bf8ccdfe431a811` | `PauserChanged(address indexed oldPauser, address indexed newPauser)` | Admin role change. |
| `0xfa4507bc1f9c730e6e95897024f1fe7d576cf2deb53579d55c14f1ac3439e114` | `Denylisted(address indexed addr)` | The address can no longer deposit, add or remove a delegate, call `gatewayMint` or receive a mint. Burns and withdrawals do not check the denylist. |
| `0xc904e1b03de0c20d7fcf9dbd056daf1bd3815e93f251199de815fd0f0b96e166` | `UnDenylisted(address indexed addr)` | |
| `0xe144e84038182cefebda68c192c222085b2c12a85d135d3c938498c0165c01d3` | `DenylisterChanged(address indexed oldDenylister, address indexed newDenylister)` | Admin role change. |
| `0xea3145306a87baeba6bb1a8b5c8d3744f840a81cb436b3509f64fc978600cdfb` | `TokenSupported(address token)` | Admin. A new token is accepted (USDC today). |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | ERC-1967. **UUPS implementation change.** |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | `Ownable2Step`, first step. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | `Ownable2Step`, final step. |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | OpenZeppelin v5 initializer (reinitializer 2 on the Wallet). |

### 1.5 USDC events in the same transaction (the value trail)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | USDC. `to` = `0x0` on a burn, `from` = `0x0` on a mint. |
| `0xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8` | `Mint(address indexed minter, address indexed to, uint256 amount)` | USDC (FiatToken). `minter` = the GatewayMinter. |
| `0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5` | `Burn(address indexed burner, uint256 amount)` | USDC (FiatToken). `burner` = the GatewayWallet. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 GatewayWallet — user functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x47e7ef24` | `deposit(address token, uint256 value)` | User. Pulls `value` from `msg.sender`; credits `msg.sender`. Emits `Deposited`. |
| `0xb3db428b` | `depositFor(address token, address depositor, uint256 value)` | User or integrator. Pulls from `msg.sender`; credits `depositor`. |
| `0x8ef59739` | `depositWithPermit(address token, address owner, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)` | EIP-2612 permit, then pull from `owner`. |
| `0x26a3fb30` | `depositWithPermit(address token, address owner, uint256 value, uint256 deadline, bytes signature)` | Same, packed signature. |
| `0x8a94d4fc` | `depositWithAuthorization(address token, address from, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s)` | ERC-3009 `receiveWithAuthorization`. USDC's own `AuthorizationUsed` also fires. |
| `0x438d4835` | `depositWithAuthorization(address token, address from, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, bytes signature)` | Same, packed signature. |
| `0xc8393ba9` | `initiateWithdrawal(address token, uint256 value)` | User. Starts the delay. Emits `WithdrawalInitiated`. |
| `0x51cff8d9` | `withdraw(address token)` | User, after `withdrawalBlock`. Emits `WithdrawalCompleted`. |
| `0xe909ebfa` | `addDelegate(address token, address delegate)` | User. Emits `DelegateAdded`. |
| `0x020d308d` | `removeDelegate(address token, address delegate)` | User. Emits `DelegateRemoved`. |

### 2.2 Circle-submitted and attested calls

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8ec3dbb9` | `gatewayBurn(bytes calldataBytes, bytes signature)` | Wallet. `calldataBytes` = encoded intents and fees, signed by a burn signer. Emits `GatewayBurned` per intent. |
| `0xc9486c8b` | `submitBatch(bytes calldataBytes, bytes signature)` | Wallet. `calldataBytes` = `abi.encode((address,int256)[] deltas, bytes32 batchId, uint32 domain, address token, address wallet)`; each delta is `(depositor, value)` and the values must sum to zero. Emits `BatchProcessed`. |
| `0x9fb01cc5` | `gatewayMint(bytes attestationPayload, bytes signature)` | Minter. Called by the user or its relayer with Circle's attestation. Emits `AttestationUsed` per attestation. |

### 2.3 Admin functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8456cb59` | `pause()` | Pauser. |
| `0x3f4ba83a` | `unpause()` | Pauser. |
| `0x3371bfff` | `denylist(address addr)` | Denylister. |
| `0x9cab0c1c` | `unDenylist(address addr)` | Denylister. |
| `0x6d69fcaf` | `addSupportedToken(address token)` | Owner. |
| `0x52cd67e9` | `updateWithdrawalDelay(uint256 newDelay)` | Owner (Wallet). |
| `0xf160d369` | `updateFeeRecipient(address newFeeRecipient)` | Owner (Wallet). |
| `0xb3f69f8d` | `addBurnSigner(address signer)` | Owner (Wallet). |
| `0x7e2acfa3` | `removeBurnSigner(address signer)` | Owner (Wallet). |
| `0x78c8ef23` | `addBatchSigner(address signer)` | Owner (Wallet). |
| `0xd2b85a0f` | `removeBatchSigner(address signer)` | Owner (Wallet). |
| `0x35a570e4` | `addContractSignatureSigner(address signer)` | Owner (Wallet). |
| `0x28a4b97f` | `allowlistContractSigner(address contractAddr)` | Allowlister role (Wallet). |
| `0xf15be2e0` | `disallowContractSigner(address contractAddr)` | Disallowlister role (Wallet). |
| `0x08307b78` | `addAttestationSigner(address signer)` | Owner (Minter). **High severity.** |
| `0x3a57609e` | `removeAttestationSigner(address signer)` | Owner (Minter). |
| `0x1ad20c51` | `updateMintAuthority(address token, address newMintAuthority)` | Owner (Minter). |
| `0x554bab3c` | `updatePauser(address newPauser)` | Owner. |
| `0xa946de04` | `updateDenylister(address newDenylister)` | Owner. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | Owner. UUPS upgrade; emits `Upgraded`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner. Emits `OwnershipTransferStarted`. |
| `0x79ba5097` | `acceptOwnership()` | Pending owner. Emits `OwnershipTransferred`. |

### 2.4 Views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3ccb64ae` | `availableBalance(address token, address depositor)` | `uint256`. Spendable balance on this chain. |
| `0xdf0c6690` | `withdrawingBalance(address token, address depositor)` | `uint256`. Balance in the withdrawal delay. |
| `0x1453b987` | `totalBalance(address token, address depositor)` | `uint256`. Available plus withdrawing. |
| `0x3bbe1ecd` | `withdrawableBalance(address token, address depositor)` | `uint256`. Withdrawing balance past its block. |
| `0xfefeec13` | `withdrawalBlock(address token, address depositor)` | `uint256`. |
| `0xa7ab6961` | `withdrawalDelay()` | `uint256`, in blocks. |
| `0x17580158` | `isTransferSpecHashUsed(bytes32 transferSpecHash)` | `bool`. True once a mint (Minter) or a burn (Wallet) used the hash on that contract. |
| `0xc2fb26a6` | `domain()` | `uint32`. The CCTP domain of this chain. |
| `0x46904840` | `feeRecipient()` | `address` (Wallet). |
| `0x75151b63` | `isTokenSupported(address token)` | `bool`. |
| `0x3e5de4df` | `tokenMintAuthority(address token)` | `address` (Minter). `0x0` = mint on the token itself. |
| `0xc418fac3` | `isAttestationSigner(address signer)` | `bool` (Minter). |
| `0x3660dbd0` | `isBurnSigner(address signer)` | `bool` (Wallet). |
| `0xa77eb2a4` | `isBatchSigner(address signer)` | `bool` (Wallet). |
| `0x9fd0506d` | `pauser()` | `address`. |
| `0xbcc76c60` | `denylister()` | `address`. |
| `0x8da5cb5b` | `owner()` | `address`. |
| `0xe30c3978` | `pendingOwner()` | `address`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

The two contract addresses are identical on all six deployed chains (CREATE2 vanity); §4–§8 list only the per-chain values. Every address below was existence-checked with `eth_getCode` on 2026-09-29; every role was read with `eth_call`.

| Role | Address | One-liner |
|------|---------|-----------|
| **GatewayWallet** (proxy) | `0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE` | Deposits, burns, batches, withdrawals. Impl `0xf7a6d9d7df917c072ac8987a820c58aa27a0e798`. |
| **GatewayMinter** (proxy) | `0x2222222d7164433c4C09B0b0D809a9b52C04C205` | Attested mints. Impl `0xc2ff68068362aea1ca22a3896d05b2b812ce51b1` (the same implementation on all six chains). |
| Wallet `owner()` — EOA | `0x2a6a86466f181721ec8ff946967b56f1aa4758c5` | Upgrade and signer authority (nonce 11). |
| Minter `owner()` — EOA | `0x3c54ffa14d01ef3a555106007a4fed6e8964aab6` | Upgrade and attestation-signer authority (nonce 1). |
| Wallet `feeRecipient()` — EOA | `0xfbaf3a19b1c02b8bef52a7e9fa855c86c69ab95c` | Receives every burn fee (nonce 0). |
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | The supported token. |
| `domain()` / `withdrawalDelay()` | `0` / 50,400 blocks | About 7 days. |

## 4. Addresses — Base (chain ID 8453)

| Role | Address / value |
|------|-----------------|
| GatewayWallet / GatewayMinter | shared addresses (§3) |
| Wallet implementation | `0x85558ae0c8234d4b1b36b2ca6ca9d5380688242b` (the same as Optimism) |
| Wallet `owner()` — EOA | `0x3a66e6486e8dd044fc8d194e9ec19b0f80bf5018` |
| Minter `owner()` — EOA | `0xf1237f985d146d8aec106c742ec6d8c4a98bb788` |
| Wallet `feeRecipient()` — EOA | `0x01bfd8ece1309a11adad54f62c644173a7039da0` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| `domain()` / `withdrawalDelay()` | `6` / 302,400 blocks (7 days at 2 s) |

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address / value |
|------|-----------------|
| GatewayWallet / GatewayMinter | shared addresses (§3) |
| Wallet implementation | `0xd87210dfc0804fc5d8b4defb59491621b016c0f3` |
| Wallet `owner()` — EOA | `0x213cd84bb7c31977c12f17c41bb159988c446e8f` |
| Minter `owner()` — EOA | `0xca01392083523df0629208d15ac8719237fd9add` |
| Wallet `feeRecipient()` — EOA | `0x7af122dd42bbf1f0c8f28169c152da27780dfb7f` |
| USDC | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| `domain()` / `withdrawalDelay()` | `3` / 50,400 blocks (Arbitrum's `block.number` follows the Ethereum block number, so this is also about 7 days) |

## 6. Addresses — Optimism (chain ID 10)

| Role | Address / value |
|------|-----------------|
| GatewayWallet / GatewayMinter | shared addresses (§3) |
| Wallet implementation | `0x85558ae0c8234d4b1b36b2ca6ca9d5380688242b` (the same as Base) |
| Wallet `owner()` — EOA | `0xf861c3e8900737baad8cb3559dc859d878fae311` |
| Minter `owner()` — EOA | `0x177c5bab57597a5baa3a58a18d1adc839bc4e5ca` |
| Wallet `feeRecipient()` — EOA | `0x1a17c995f532de51580ffdc4862d3b1c3dfe082b` |
| USDC | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| `domain()` / `withdrawalDelay()` | `2` / 302,400 blocks |

## 7. Addresses — Polygon PoS (chain ID 137)

| Role | Address / value |
|------|-----------------|
| GatewayWallet / GatewayMinter | shared addresses (§3) |
| Wallet implementation | `0xeb4ea4637f38c37b8fca6f7857957772eafa71a9` (the same as Avalanche) |
| Wallet `owner()` — EOA | `0x488805c75f57d4f29e578bf66b0f0d320196126c` |
| Minter `owner()` — EOA | `0xef1efc49d4df1a9f2b1bea0ffa169640336d9bd2` |
| Wallet `feeRecipient()` — EOA | `0x8b49a7dccf2328c633b7b3aede098f19e50e511a` |
| USDC | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| `domain()` / `withdrawalDelay()` | `7` / 403,200 blocks (7 days at 1.5 s) |

## 8. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address / value |
|------|-----------------|
| GatewayWallet / GatewayMinter | shared addresses (§3) |
| Wallet implementation | `0xeb4ea4637f38c37b8fca6f7857957772eafa71a9` (the same as Polygon) |
| Wallet `owner()` — EOA | `0x0286eab5e62785ad04de13934d011a69f19c2608` |
| Minter `owner()` — EOA | `0xe636a3e1acf976c98dc1652a52ecfb9583a66799` |
| Wallet `feeRecipient()` — EOA | `0x96c790d3b06ae69e2f5be0b782e1bdad2825c917` |
| USDC | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| `domain()` / `withdrawalDelay()` | `1` / 545,000 blocks |

### 8.1 Pause and denylist role holders (all EOAs with nonce 0: none has ever sent a transaction)

| Chain | Wallet `pauser()` | Wallet `denylister()` | Minter `pauser()` |
|-------|-------------------|-----------------------|-------------------|
| Ethereum | `0x9812d5f0a0832d9a0a78a1ba728facd87bc35b19` | `0x7359fd9aa258992eb4b6d9572c6f6c74cf719a94` | `0x6fa314d4dce1d49233c329a60fdbd96a6bcbe6fb` |
| Base | `0x6c754cab415deeb2aa85962d8b6dea2f6fc5a0d6` | `0x5316c167d25595e29ff0ea562dcb12c8db0a52ea` | `0xe8e9a69cac43785438f181f64763fbee83866bf2` |
| Arbitrum | `0x872a84980caf229adec4292964d6717698cc32b4` | `0x2ab0851b480aefa81222679e8cd89abc1707ec5f` | `0xb15812b865203d3ecb0a2f2b9332b32b493f8bc3` |
| Optimism | `0x686d129a7a78c2b83b51d67abbd94c9a99cab1fa` | `0x281b36386962ece4db95d499b305d944447c3280` | `0x89aa3ff7484ce48a030febb471f796095abbff5b` |
| Avalanche | `0x4c1167fc1b133b382a172de89aab691f0834255d` | `0x053075ab5271b121fd897488aee57a119c9f5546` | `0x12ea8487edae9cec60dec6bfae82d41b8116e5ff` |
| Polygon | `0xf999330e9f1e853bd69dfd2706cdbc3ee120d13b` | `0x2d884aebb34cd83efb6d3c72e7f4e1569f4d0853` | `0x8367b237a120ae6ee4be9bcb41b502f7e24cd756` |

### 8.2 BNB Smart Chain (56) and Robinhood Chain (4663) — no deployment

`eth_getCode` returns `0x` at `0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE` and `0x2222222d7164433c4C09B0b0D809a9b52C04C205` on both chains (nonce 0: the deployer never used the vanity addresses there). Circle's contract-address and supported-blockchain pages list neither chain. The pinned window holds zero Gateway events on both. Both chains do run CCTP v2 (BNB domain 17, Robinhood Chain domain 35; see [../cctp/README.md](../cctp/README.md)).

---

## 9. Cross-chain summary

| Chain | ID | Gateway domain | GatewayWallet | GatewayMinter | Wallet implementation | Withdrawal delay (blocks) |
|-------|----|----------------|--------------------------|--------------------------|-----------------------|---------------------------|
| Ethereum | 1 | 0 | ✅ | ✅ | `0xf7a6d9d7df917c072ac8987a820c58aa27a0e798` | 50,400 |
| Base | 8453 | 6 | ✅ | ✅ | `0x85558ae0c8234d4b1b36b2ca6ca9d5380688242b` | 302,400 |
| Arbitrum One | 42161 | 3 | ✅ | ✅ | `0xd87210dfc0804fc5d8b4defb59491621b016c0f3` | 50,400 |
| Optimism | 10 | 2 | ✅ | ✅ | `0x85558ae0c8234d4b1b36b2ca6ca9d5380688242b` | 302,400 |
| Polygon PoS | 137 | 7 | ✅ | ✅ | `0xeb4ea4637f38c37b8fca6f7857957772eafa71a9` | 403,200 |
| BNB Smart Chain | 56 | — (CCTP 17) | ❌ `0x` | ❌ `0x` | — | — |
| Avalanche C-Chain | 43114 | 1 | ✅ | ✅ | `0xeb4ea4637f38c37b8fca6f7857957772eafa71a9` | 545,000 |
| Robinhood Chain | 4663 | — (CCTP 35) | ❌ `0x` | ❌ `0x` | — | — |

The four Wallet implementations have the same size (22,818 bytes) and the same event and selector surface (the 1.3.0 set, with batches and ERC-1271 signer support); their code hashes differ. The Minter implementation is one contract on all six chains.

---

## 10. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **GatewayWallet** | **UUPS** (ERC1967Proxy) | 163-byte runtime; EIP-1967 impl slot set (§9); admin slot `0x0`; `upgradeToAndCall` `0x4f1ef286` in the implementation. | `owner()` via `_authorizeUpgrade onlyOwner`. A different **EOA** per chain (§3–§8), `Ownable2Step`; `renounceOwnership` is disabled. |
| **GatewayMinter** | **UUPS** (ERC1967Proxy) | Same proxy runtime; impl `0xc2ff68068362aea1ca22a3896d05b2b812ce51b1` everywhere; admin slot `0x0`. | `owner()`, a different EOA per chain. |

Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` and `OwnershipTransferStarted` on both addresses on all six chains. The Wallet owners have nonces 7–11 (they have run upgrades); the Minter owners have nonce 1. The implementations listed are point-in-time: read the EIP-1967 slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` for the current one.

---

## 11. Detection invariants & gotchas

1. **The mint comes first.** Measured on Ethereum: `AttestationUsed` at block 26,072,217 (tx `0xce83cdaf0da2cac024f7603e331c85c5661aa2f85defe280e8151f64d00369e8`) and the matching `GatewayBurned` at block 26,072,304 (tx `0x2f25fc39bf447929c8413cd85c588a1af70aa4405e2d448df8af7709b433ec38`), 87 blocks later, with the same `transferSpecHash` `0x6391bd04c86ae82a15ba9f163709bac4afa6427c7e0f16b67b8f0bc2dc36e9ef` and the same value (4,991.502 USDC; fee 2 USDC). This pair is a same-chain transfer (source and destination domain 0).
2. **Join on `transferSpecHash` (topic3 on both sides).** Take the source domain from `AttestationUsed.sourceDomain` and the destination from `GatewayBurned.destinationDomain`; both are CCTP domain numbers, not chain ids. `sourceDepositor` and `destinationRecipient` are `bytes32` (low 20 bytes on EVM chains; full 32 bytes for Solana).
3. **Burns cluster where the balances are.** In the pinned window, 535 of 559 `GatewayBurned` logs were on Polygon, while the 561 `AttestationUsed` logs spread over six chains. A burn chain is where the depositor funded the balance, not where the user acted.
4. **`gatewayBurn` is a batch.** One transaction burns many intents of one token: one `GatewayBurned` per intent, then **one** fee `Transfer` for the total fee and **one** burn `Transfer(Wallet → 0x0)` for the total burned. Match value per intent from the events, not from the transfers.
5. **`BatchProcessed` moves value with no transfer.** `submitBatch` changes `available` balances of many depositors (positive and negative deltas that sum to zero). The deltas are in calldata only. This is the nanopayment settlement path (Base 45 batches in the window).
6. **A plain USDC transfer to the Wallet is lost.** It credits no balance and emits no `Deposited` (Circle's docs say so). Do not treat a `Transfer` into the Wallet without `Deposited` as a deposit.
7. **`Deposited.sender` is not always the user.** Integrators call `depositFor`; for example Circle's xReserve (`0x8888888199b2df864bf678259607d6d5ebb4e3ce` on Ethereum) pulls USDC from the user and deposits for another `depositor`. Credit `depositor`, not `sender`.
8. **`Deposited(address,address,address,uint256)` is a common signature.** Other contracts emit the same topic0 (in the pinned window: two contracts on Arbitrum with 51 logs, one on Base with 7). Always filter by the Wallet address.
9. **`InsufficientBalance` is the loss signal.** It means a burn or a batch could not collect the full amount after Circle had already minted. 0 logs in the pinned window on all six deployed chains. Alert on any.
10. **Withdrawal is a two-step trustless exit.** `WithdrawalInitiated` (status only) and, after `withdrawalDelay()` blocks, `WithdrawalCompleted` (USDC leaves). The withdrawing balance still pays burns (`fromWithdrawing` in `GatewayBurned`), so a pending withdrawal can shrink.
11. **Admin triggers.** `Upgraded`, `OwnershipTransferStarted`, `AttestationSignerAdded`, `BurnSignerAdded`, `BatchSignerAdded`, `MintAuthorityChanged`, `FeeRecipientChanged`, `WithdrawalDelayChanged`, `PauserChanged`, `Paused`. Every owner is a single EOA per chain and per contract.
12. **Gateway is not CCTP.** No `DepositForBurn`, `MessageSent` or `MintAndWithdraw` fires on a Gateway transfer, and CCTP nonces do not apply. Gateway reuses only the domain numbering. A CCTP monitor sees nothing of Gateway flow, and the reverse.
13. **Absent chains.** BNB and Robinhood Chain have no code at either vanity address. Do not infer a Gateway leg there from a CCTP domain number.

---

## 12. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== GatewayWallet topics =====
TOPIC_DEPOSITED                  = '\x4174a9435a04d04d274c76779cad136a41fde6937c56241c09ab9d3c7064a1a9'
TOPIC_GATEWAY_BURNED             = '\x12ee2719e7e2dec9f2a0041286b66669153dff0d36719f692b8bbaa4dfe0aa87'
TOPIC_INSUFFICIENT_BALANCE       = '\x5fab62745de032ad35a05146c51710fd80871be06cb193722c40f011df352f0c'
TOPIC_WITHDRAWAL_INITIATED       = '\x5f9a559874d8abe05a98d167b78d2012697505ea3e7bcdba906e7b6084014c65'
TOPIC_WITHDRAWAL_COMPLETED       = '\xb00382203b46c3b6ad0a2d7af0268e334bd9406256a7c7ba8f7fc8bc47f8cde9'
TOPIC_BATCH_PROCESSED            = '\x8e9878875610f80a970e0cea1889a4c7de3012c1a52ae169d9d5d3ab2c08b670'
TOPIC_DELEGATE_ADDED             = '\xe91cba149cb264c22b997b1a69e785ad1562a07f83318cd0c985ba1be6e66099'
TOPIC_BURN_SIGNER_ADDED          = '\x895cdec14fd06461967f67fd12f3dc81c22b59fe80d1caf6f07b1902a8eaa35e'
TOPIC_BATCH_SIGNER_ADDED         = '\xceb230c3aed7aaaf620d28e444845b73c1083c4011d91d07e0cf321ef07b8016'
TOPIC_FEE_RECIPIENT_CHANGED      = '\x0bc21fe5c3ab742ff1d15b5c4477ffbacf1167e618228078fa625edebe7f331d'
TOPIC_WITHDRAWAL_DELAY_CHANGED   = '\xab3f1d5eaee409b7067167f77f1fa3f8a863366d6fb2b88559cd4f9b8e03e182'
-- ===== GatewayMinter topics =====
TOPIC_ATTESTATION_USED           = '\xbb312ce0cc311b2cb0746e09ccd2f91fdb9e2ac755d2f11c65300eb0d0fffd63'
TOPIC_ATTESTATION_SIGNER_ADDED   = '\x09b9e0aeb0d8dd390c8ab392ed51b6cbc0e6f3a2ddae0149cec4dd4acf13d7a9'
TOPIC_MINT_AUTHORITY_CHANGED     = '\x5c3cb1b340c7f4e8dfc2058a7e8992362e063c9ded5e14aa21e23e8856ee1831'
-- ===== Both contracts =====
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                   = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_DENYLISTED                 = '\xfa4507bc1f9c730e6e95897024f1fe7d576cf2deb53579d55c14f1ac3439e114'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFER_STARTED = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
TOPIC_OWNERSHIP_TRANSFERRED      = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- ===== USDC value trail =====
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_USDC_MINT                  = '\xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8'
TOPIC_USDC_BURN                  = '\xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'

-- ===== Selectors =====
SEL_DEPOSIT                      = '\x47e7ef24'
SEL_DEPOSIT_FOR                  = '\xb3db428b'
SEL_DEPOSIT_WITH_PERMIT          = '\x8ef59739'
SEL_DEPOSIT_WITH_PERMIT_BYTES    = '\x26a3fb30'
SEL_DEPOSIT_WITH_AUTH            = '\x8a94d4fc'
SEL_DEPOSIT_WITH_AUTH_BYTES      = '\x438d4835'
SEL_INITIATE_WITHDRAWAL          = '\xc8393ba9'
SEL_WITHDRAW                     = '\x51cff8d9'
SEL_ADD_DELEGATE                 = '\xe909ebfa'
SEL_GATEWAY_BURN                 = '\x8ec3dbb9'
SEL_SUBMIT_BATCH                 = '\xc9486c8b'
SEL_GATEWAY_MINT                 = '\x9fb01cc5'
SEL_PAUSE                        = '\x8456cb59'
SEL_ADD_ATTESTATION_SIGNER       = '\x08307b78'
SEL_ADD_BURN_SIGNER              = '\xb3f69f8d'
SEL_ADD_BATCH_SIGNER             = '\x78c8ef23'
SEL_UPDATE_MINT_AUTHORITY        = '\x1ad20c51'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'
SEL_AVAILABLE_BALANCE            = '\x3ccb64ae'
SEL_TOTAL_BALANCE                = '\x1453b987'
SEL_DOMAIN                       = '\xc2fb26a6'

-- ===== Addresses (the same on ETH, BASE, ARB, OP, POLY, AVAX; no code on BNB or RH) =====
ETH_GATEWAY_WALLET               = '\x77777777dcc4d5a8b6e418fd04d8997ef11000ee'
ETH_GATEWAY_MINTER               = '\x2222222d7164433c4c09b0b0d809a9b52c04c205'
BASE_GATEWAY_WALLET              = '\x77777777dcc4d5a8b6e418fd04d8997ef11000ee'
BASE_GATEWAY_MINTER              = '\x2222222d7164433c4c09b0b0d809a9b52c04c205'
ARB_GATEWAY_WALLET               = '\x77777777dcc4d5a8b6e418fd04d8997ef11000ee'
ARB_GATEWAY_MINTER               = '\x2222222d7164433c4c09b0b0d809a9b52c04c205'
OP_GATEWAY_WALLET                = '\x77777777dcc4d5a8b6e418fd04d8997ef11000ee'
OP_GATEWAY_MINTER                = '\x2222222d7164433c4c09b0b0d809a9b52c04c205'
POLY_GATEWAY_WALLET              = '\x77777777dcc4d5a8b6e418fd04d8997ef11000ee'
POLY_GATEWAY_MINTER              = '\x2222222d7164433c4c09b0b0d809a9b52c04c205'
AVAX_GATEWAY_WALLET              = '\x77777777dcc4d5a8b6e418fd04d8997ef11000ee'
AVAX_GATEWAY_MINTER              = '\x2222222d7164433c4c09b0b0d809a9b52c04c205'
-- implementations (point-in-time)
ETH_GATEWAY_WALLET_IMPL          = '\xf7a6d9d7df917c072ac8987a820c58aa27a0e798'
BASE_GATEWAY_WALLET_IMPL         = '\x85558ae0c8234d4b1b36b2ca6ca9d5380688242b'
ARB_GATEWAY_WALLET_IMPL          = '\xd87210dfc0804fc5d8b4defb59491621b016c0f3'
OP_GATEWAY_WALLET_IMPL           = '\x85558ae0c8234d4b1b36b2ca6ca9d5380688242b'
POLY_GATEWAY_WALLET_IMPL         = '\xeb4ea4637f38c37b8fca6f7857957772eafa71a9'
AVAX_GATEWAY_WALLET_IMPL         = '\xeb4ea4637f38c37b8fca6f7857957772eafa71a9'
ETH_GATEWAY_MINTER_IMPL          = '\xc2ff68068362aea1ca22a3896d05b2b812ce51b1'
-- owners and fee recipients (EOAs)
ETH_GATEWAY_WALLET_OWNER_EOA     = '\x2a6a86466f181721ec8ff946967b56f1aa4758c5'
ETH_GATEWAY_MINTER_OWNER_EOA     = '\x3c54ffa14d01ef3a555106007a4fed6e8964aab6'
ETH_GATEWAY_FEE_RECIPIENT_EOA    = '\xfbaf3a19b1c02b8bef52a7e9fa855c86c69ab95c'
BASE_GATEWAY_WALLET_OWNER_EOA    = '\x3a66e6486e8dd044fc8d194e9ec19b0f80bf5018'
BASE_GATEWAY_MINTER_OWNER_EOA    = '\xf1237f985d146d8aec106c742ec6d8c4a98bb788'
BASE_GATEWAY_FEE_RECIPIENT_EOA   = '\x01bfd8ece1309a11adad54f62c644173a7039da0'
ARB_GATEWAY_WALLET_OWNER_EOA     = '\x213cd84bb7c31977c12f17c41bb159988c446e8f'
ARB_GATEWAY_MINTER_OWNER_EOA     = '\xca01392083523df0629208d15ac8719237fd9add'
ARB_GATEWAY_FEE_RECIPIENT_EOA    = '\x7af122dd42bbf1f0c8f28169c152da27780dfb7f'
OP_GATEWAY_WALLET_OWNER_EOA      = '\xf861c3e8900737baad8cb3559dc859d878fae311'
OP_GATEWAY_MINTER_OWNER_EOA      = '\x177c5bab57597a5baa3a58a18d1adc839bc4e5ca'
OP_GATEWAY_FEE_RECIPIENT_EOA     = '\x1a17c995f532de51580ffdc4862d3b1c3dfe082b'
AVAX_GATEWAY_WALLET_OWNER_EOA    = '\x0286eab5e62785ad04de13934d011a69f19c2608'
AVAX_GATEWAY_MINTER_OWNER_EOA    = '\xe636a3e1acf976c98dc1652a52ecfb9583a66799'
AVAX_GATEWAY_FEE_RECIPIENT_EOA   = '\x96c790d3b06ae69e2f5be0b782e1bdad2825c917'
POLY_GATEWAY_WALLET_OWNER_EOA    = '\x488805c75f57d4f29e578bf66b0f0d320196126c'
POLY_GATEWAY_MINTER_OWNER_EOA    = '\xef1efc49d4df1a9f2b1bea0ffa169640336d9bd2'
POLY_GATEWAY_FEE_RECIPIENT_EOA   = '\x8b49a7dccf2328c633b7b3aede098f19e50e511a'
-- related Circle contract that deposits into the Wallet
ETH_XRESERVE                     = '\x8888888199b2df864bf678259607d6d5ebb4e3ce'
-- BNB (56) and RH (4663): no Gateway code at either address
```

---

## 13. Verification & sources

How each constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the Solidity in `circlefin/evm-gateway-contracts` (`src/modules/wallet/*.sol`, `src/modules/minter/Mints.sol`, `src/modules/common/*.sol`, `src/GatewayCommon.sol`). Each event topic and each listed selector was found in the deployed implementation bytecode (the four Wallet implementations and the one Minter implementation, read with `eth_getCode`). Live logs confirm `Deposited`, `GatewayBurned`, `AttestationUsed`, `BatchProcessed` and `WithdrawalInitiated`, and the USDC `Mint`/`Burn` topics in the sample transactions below.
- **Addresses:** from Circle's contract-address page; existence-checked with `eth_getCode` on all eight chains. BNB and Robinhood Chain return `0x` (nonce 0) at both addresses. Implementations from the EIP-1967 slot; admin slot `0x0` on every proxy. `owner()`, `pauser()`, `denylister()`, `feeRecipient()`, `domain()`, `withdrawalDelay()`, `isTokenSupported(USDC)` and `tokenMintAuthority(USDC)` read with `eth_call`; every owner, role holder and fee recipient returned no code (EOA).
- **Sample transactions read (`eth_getTransactionReceipt`):** Ethereum burn `0x2f25fc39bf447929c8413cd85c588a1af70aa4405e2d448df8af7709b433ec38` (`GatewayBurned`, fee `Transfer`, USDC `Burn`, `Transfer` to `0x0`); Ethereum mint `0x1c83f78ca15bf2d9c2c91da4f86313e9fb13b029856c0836f6c6fa75b3edd18b` (USDC `Mint`, `Transfer` from `0x0`, `AttestationUsed`); Ethereum deposit `0x84d67c4dcc371be4323df84dc727a5df1d74b101a90fed4326e84f76153be4b0` (via xReserve `depositFor`); Base batch `0xf5d97bec66592cfaa4579496cdb9bcef3624e188a298485ec71b6497894c23eb` (one `BatchProcessed`, no transfer); Base withdrawal start `0x8ab5295ee067cf4b7c48c45f19aae7cd0ec9f68951a34234c4be6ebace1a6e74` (one `WithdrawalInitiated`, no transfer). The burn-to-mint join in §11.1 was found with `eth_getLogs` filtered on topic3.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC** (logs at the Gateway addresses; BNB and Robinhood Chain have no deployment and 0 logs):

| Event | Ethereum | Base | Arbitrum | Optimism | Polygon | Avalanche |
|-------|---------:|-----:|---------:|---------:|--------:|----------:|
| `Deposited` (Wallet) | 19 | 6 | 0 | 0 | 247 | 0 |
| `GatewayBurned` (Wallet) | 16 | 2 | 2 | 2 | 535 | 2 |
| `AttestationUsed` (Minter) | 90 | 165 | 153 | 44 | 97 | 12 |
| `BatchProcessed` (Wallet) | 0 | 45 | 0 | 0 | 3 | 0 |
| `WithdrawalInitiated` / `WithdrawalCompleted` | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `InsufficientBalance` | 0 | 0 | 0 | 0 | 0 | 0 |

A 0 is a measurement of this window only, not a statement that the path is unused.

Authoritative sources:
- Canonical repository — [circlefin/evm-gateway-contracts](https://github.com/circlefin/evm-gateway-contracts) (`src/GatewayWallet.sol`, `src/GatewayMinter.sol`, `src/modules/`, `CHANGELOG.md`)
- Docs — [Gateway contract addresses](https://developers.circle.com/gateway/references/contract-addresses) · [Supported blockchains and domains](https://developers.circle.com/gateway/references/supported-blockchains) · [Technical guide](https://developers.circle.com/gateway/concepts/technical-guide) · [Nanopayments](https://developers.circle.com/gateway/nanopayments) · [Batched settlement](https://developers.circle.com/gateway/nanopayments/concepts/batched-settlement)
- Related — [circlefin/evm-xreserve-contracts](https://github.com/circlefin/evm-xreserve-contracts) (xReserve proxy prefix `0x8888888`) · [Circle CCTP reference](../cctp/README.md)
- Explorers — [Etherscan GatewayWallet](https://etherscan.io/address/0x77777777dcc4d5a8b6e418fd04d8997ef11000ee) · [Etherscan GatewayMinter](https://etherscan.io/address/0x2222222d7164433c4c09b0b0d809a9b52c04c205) · [Blockscout xReserve](https://eth.blockscout.com/address/0x8888888199b2df864bf678259607d6d5ebb4e3ce)
