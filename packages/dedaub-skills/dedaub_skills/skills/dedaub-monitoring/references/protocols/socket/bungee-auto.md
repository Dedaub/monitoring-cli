# Bungee Auto — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche; not Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the `SocketDotTech/bungee-contracts-public` deployment files (`deployments/<network>.json`) and the explorer-verified sources of BungeeInbox, BungeeGateway and the request routers. Topics and selectors recomputed as `keccak256(signature)` from the verified ABIs; addresses existence-checked with `eth_getCode`.
**Scope:** the Bungee Auto contracts (the solver-auction generation of Bungee, before the OpenRouter of [openrouter.md](openrouter.md)): the BungeeInbox for on-chain requests, the per-chain BungeeGateway where solvers extract, fulfil and settle requests, the request implementations and routers, and the Switchboard messaging that settles across chains. Topics and selectors are chain-agnostic; addresses are network-specific.

A Bungee Auto transfer is a **request** identified by `requestHash`. The user signs a request (Permit2 witness) or submits it on chain to the **BungeeInbox** (`createRequest`, emits `SingleOutputRequestCreated`). A transmitter (solver) calls the source **BungeeGateway**: `extractRequests` pulls the user's funds from the wallet with Permit2 into the router of the request and emits `RequestExtracted`. On the destination the transmitter calls `fulfilRequests` and pays the receiver (`RequestFulfilled`). Then `settleRequests` on the destination sends a Switchboard message (`RequestsSettledOnDestination`), and the source gateway credits the solver (`RequestSettled`). A user whose request was not filled calls `cancelRequest` on the destination (`RequestCancelledOnDestination`); the message back to the origin releases the funds to the user (`RequestCancelled`). Inbox requests can also be withdrawn before extraction (`SingleOutputRequestWithdrawn`), and some routers allow `WithdrawOnDestination`.

Three facts to know before indexing:

1. **No logs in the pinned window.** In the 12-hour window of 2026-09-28 the BungeeInbox and the BungeeGateway of every chain emitted 0 logs (§15). On Ethereum the last BungeeGateway log is at block 25845552 (2026-08-27 09:06:35 UTC, `RequestExtracted`) and the last BungeeInbox log at block 25832093 (2026-08-25 12:04:11 UTC, `SingleOutputRequestWithdrawn`). The current Socket API routes use the OpenRouter. Keep the monitor: the contracts are live and can be used again.
2. **`requestHash` is the link key on both chains** (topic1 of the inbox and gateway request events).
3. **The BungeeGateway address differs per chain, and addresses are reused across roles.** The same address is, for example, the BungeeGateway on Base and the SwapExecutor on Optimism. Always key on `(chain, address)`.

---

## 0. Contract families & versions

| Contract | Address | Chains | Role |
|----------|---------|--------|------|
| **BungeeInbox** | `0x5e0f8e7337c8955d2124b8e85ca74af884b3e124` | 7 | On-chain request submission (`createRequest`) and withdrawal of unfilled requests (`withdrawFunds`). |
| **BungeeGateway** | per chain (§3–§9) | 7 | Solver entry point: `executeImpl(implId, data)` runs the request implementation; receives Switchboard messages; emits every request lifecycle event. |
| SingleOutputRequestImpl / SwapRequestImpl | per chain | 7 | Implementations that the gateway runs for single-output and swap requests. |
| Request routers (RFQ, CCTP, CCTP V2, staked) | RFQ `0xc4088d6e5a2027e784efc0491c322a3e2621bd9e` on 7 chains; others per §3–§9 | 7 | Deliver the output on the destination; emit `WithdrawOnDestination` for a refund on the destination. |
| SwitchboardRouter / SwitchboardPlug | per chain | 7 | Cross-chain settlement messaging. |
| Entrypoint, SwapExecutor, CalldataExecutor, FeeCollector, Solver | per chain / shared | 7 | Support contracts of the gateway (`ENTRYPOINT()`, `SWAP_EXECUTOR()`, `CALLDATA_EXECUTOR()`, `FEE_COLLECTOR()`). |
| BungeeInboxOld | per chain | 7 | The previous inbox; same events. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Request lifecycle

| topic0 | Event |
|--------|-------|
| `0xaafaed86f175a2b5a9812043ba82df1a5d0ab905b78d0f4bea5ca66a05b12183` | `SingleOutputRequestCreated(bytes32 indexed requestHash, address refundAddress, bytes request)` |
| `0xf434768883a3ab10e133a3543933614318754252dae7fba45ecb5190b2850a0a` | `SingleOutputRequestWithdrawn(bytes32 indexed requestHash)` |
| `0x5f35e6c87802b75b33eba5733b4ded8a8b8d406d93e2227ed7d74f134b390d67` | `SwapRequestCreated(bytes32 indexed requestHash, address refundAddress, bytes request)` |
| `0xa60380b825a601e4b8fc7abe6ef2b41879098292cfd96335954f819ba271f09f` | `SwapRequestWithdrawn(bytes32 indexed requestHash)` |
| `0x14a241d5b404d2061ceb9a847972acfd690983f1d8a0fef9779b8191aa1b7ef2` | `RequestExtracted(bytes32 indexed requestHash, uint8 implId, address transmitter, bytes execution)` |
| `0xd83e4fbd120e768f3bb813ecfa1a2b16c323fa7dfa07db1cd6434b3cbc97bc75` | `RequestFulfilled(bytes32 indexed requestHash, uint8 implId, address fulfiller, bytes execution)` |
| `0x7eea86cc10df3b8a859a99d48d6858b1128a479f035d0223cf9dd929f37c6079` | `RequestSettled(bytes32 indexed requestHash)` |
| `0x07349f83fa11ddca53ca675ac3efd87202dffc9178afef9b223b3976e1949a47` | `RequestSettlementFailed(bytes32 indexed requestHash, bytes4 _error)` |
| `0xc74d65bbb9e63c78e05140eda2a63c9011b58af244ec5c5e596d4842fe84d329` | `RequestCancelled(bytes32 indexed requestHash, address token, uint256 amount, address to)` |
| `0x315b5b12b5749bb31d7d3c18cee689619f441a29bbf35a2f958394e3fd309762` | `RequestCancelledOnDestination(bytes32 requestHash, uint8 implId, address transmitter, uint256 outboundFees)` |
| `0x3e09b55b6efb54718ae4486c6229eaf5afca42c1aed76e189d9cfaeb3b539f4e` | `RequestsSettledOnDestination(bytes32[] requestHashes, uint8 implId, address transmitter, uint256 outboundFees)` |
| `0xcaf6a92baaa2579fa4947b96c59846b5f1e64162dce1b89d3e524b34c6820ca6` | `CalldataExecutionFailed(bytes32 requestHash, address to, bytes encodedData, uint256 minDestGasLimit)` |
| `0xe6cea8072222bb5dd02862b1f55e8609a98566d603d56964af44c187c81536ed` | `WithdrawOnDestination(bytes32 indexed requestHash, address token, uint256 amount, address to)` |
| `0x3754b0090c75d1f0866f0d41983f3eadd3b0de510c67e67e0ad24a94b756d9f1` | `RequestRefunded(bytes32 requestHash, address token, uint256 amount, address refundTo)` |

- Emitters: `SingleOutputRequestCreated` / `SwapRequestCreated` / `*Withdrawn` → BungeeInbox (and BungeeInboxOld); `Request*` and `CalldataExecutionFailed` → BungeeGateway; `WithdrawOnDestination` → the request routers; `RequestRefunded` → StakedRouterReceiver.
- Source leg: `SingleOutputRequestCreated` (the user's funds enter the inbox) or a Permit2 request, then `RequestExtracted` (funds pulled into the router). Destination leg: `RequestFulfilled`. Settlement to the solver: `RequestsSettledOnDestination` (destination), then `RequestSettled` (source). Refund: `SingleOutputRequestWithdrawn` (inbox), `RequestCancelledOnDestination` then `RequestCancelled` (origin), `WithdrawOnDestination` (router), `RequestRefunded` (staked router).
- `execution` in `RequestExtracted` / `RequestFulfilled` is the ABI-encoded execution data (amounts, receiver, token) of the implementation `implId`.

### 1.2 Admin events

| topic0 | Event |
|--------|-------|
| `0x891e2f61914a277b540f6cbff39daf187f334f204a2576ff5e72303d1cf2ce8b` | `ImplAdded(uint32 indexed implId, address implAddress)` |
| `0x21f97cc4493d15a39bb3e09017843c80cc31e5f6d3e35769cbde2d51caf993ab` | `ImplRemoved(uint32 indexed implId, address prevImplAddress)` |
| `0x2ae6a113c0ed5b78a53413ffbb7679881f11145ccfba4fb92e863dfcd5a1d2f3` | `RoleGranted(bytes32 indexed role, address indexed grantee)` |
| `0x155aaafb6329a2098580462df33ec4b7441b19729b9601c5fc17ae1cf99a8a52` | `RoleRevoked(bytes32 indexed role, address indexed revokee)` |
| `0x906a1c6bd7e3091ea86693dd029a831c19049ce77f1dce2ce0bab1cacbabce22` | `OwnerNominated(address indexed nominee)` |
| `0xfbe19c9b601f5ee90b44c7390f3fa2319eba01762d34ee372aeafd59b25c7f87` | `OwnerClaimed(address indexed claimer)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 BungeeInbox

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4cdfec6e` | `createRequest(((uint256 originChainId, uint256 destinationChainId, uint256 deadline, uint256 nonce, address sender, address receiver, address delegate, address bungeeGateway, uint32 switchboardId, address inputToken, uint256 inputAmount, address outputToken, uint256 minOutputAmount, uint256 refuelAmount) basicReq, address swapOutputToken, uint256 minSwapOutput, bytes32 metadata, bytes affiliateFees, uint256 minDestGas, bytes destinationPayload, address exclusiveTransmitter) singleOutputRequest, address refundAddress)` | Swap request (with `destinationChainId`, `switchboardId`). Emits `SwapRequestCreated`. |
| `0x7d9ead2b` | `createRequest(((uint256 chainId, uint256 deadline, uint256 nonce, address sender, address receiver, address bungeeGateway, address inputToken, uint256 inputAmount, address outputToken, uint256 minOutputAmount) basicReq, bytes32 metadata, bytes affiliateFees, uint256 minDestGas, bytes destinationPayload, address exclusiveTransmitter) swapRequest, address refundAddress)` | Single-output request. Emits `SingleOutputRequestCreated`. |
| `0x9da29c8e` | `withdrawFunds(((uint256 chainId, uint256 deadline, uint256 nonce, address sender, address receiver, address bungeeGateway, address inputToken, uint256 inputAmount, address outputToken, uint256 minOutputAmount) basicReq, bytes32 metadata, bytes affiliateFees, uint256 minDestGas, bytes destinationPayload, address exclusiveTransmitter) swapRequest)` | Withdraw an unfilled single-output request. Emits `SingleOutputRequestWithdrawn`. |
| `0xad776116` | `withdrawFunds(((uint256 originChainId, uint256 destinationChainId, uint256 deadline, uint256 nonce, address sender, address receiver, address delegate, address bungeeGateway, uint32 switchboardId, address inputToken, uint256 inputAmount, address outputToken, uint256 minOutputAmount, uint256 refuelAmount) basicReq, address swapOutputToken, uint256 minSwapOutput, bytes32 metadata, bytes affiliateFees, uint256 minDestGas, bytes destinationPayload, address exclusiveTransmitter) singleOutputRequest)` | Withdraw an unfilled swap request. Emits `SwapRequestWithdrawn`. |

### 2.2 BungeeGateway

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0341ac35` | `addImpl(uint8 _implId, address _newImplAddress)` | Owner. Emits `ImplAdded`. |
| `0x3bd1adec` | `claimOwner()` | Nominee. Emits `OwnerClaimed`. |
| `0x276a2ced` | `executeImpl(uint8 implId, bytes data)` | Transmitter (solver) entry: runs implementation `implId` (extract, fulfil, settle, cancel). |
| `0x2f2ff15d` | `grantRole(bytes32 role_, address grantee_)` | Owner. Emits `RoleGranted`. |
| `0xc66eaeb6` | `inboundMsgFromSwitchboard(uint8 implId, uint32, bytes payload)` | Switchboard message in (settlement / cancellation). |
| `0x5b94db27` | `nominateOwner(address nominee_)` | Owner. Emits `OwnerNominated`. |
| `0xb746078a` | `receiveMsg(bytes payload)` | Message in. |
| `0xc7bfb9ce` | `removeImpl(uint8 _implId)` | Owner. Emits `ImplRemoved`. |
| `0x20ff430b` | `rescue(address token, address to, uint256 amount)` | Owner rescue. |
| `0xd547741f` | `revokeRole(bytes32 role_, address revokee_)` | Owner. Emits `RoleRevoked`. |
| `0x9ed0cb13` | `setWhitelistedReceiver(address receiver, uint256 destinationChainId, address router)` | Owner. |
| `0x31feeadd` | `withdrawBeneficiarySettlement(address beneficiary, address router, address token)` | Solver withdraws settled funds. |

---

## 3. Addresses — Ethereum (chain ID 1)

From `deployments/ethereum.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| BungeeInbox | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | 12,375 |
| BungeeGateway | `0xe772551F88E2c14aEcC880dF6b7CBd574561bf82` | 6,324 |
| Entrypoint | `0x2837593949F6c5f7abB66dd848ed4E5b774D4ef5` | 9,914 |
| SwapExecutor | `0x11918f1cb6db5e008A692F47c5320216fba6054B` | 658 |
| CalldataExecutor | `0xa873AaB6A98Cb764Ad6D52820d129D0e3667d9F9` | 740 |
| FeeCollector | `0xd718CDD6f19BEb30b50AF96659C309eB85B79535` | 3,730 |
| Solver | `0xAe68b7117BE0026Cbd4366303f74EEcbB19e4042` | 8,474 |
| SingleOutputRequestImpl | `0x407BE335f94C30Ee2876c4cF86ce08A46f518cF3` | 18,498 |
| SwapRequestImpl | `0x6379442Fb03F78060e8746AeA425eF6420e19F41` | 11,673 |
| RFQRouterSingleOutput | `0xc4088D6E5A2027E784EfC0491C322A3E2621bd9E` | 5,420 |
| CCTPRouterSingleOutput | `0x3b4817827d06600f92296C5d1491818D69Fc955F` | 13,518 |
| CCTPV2RouterSingleOutput | `0x6faEc2944071B2A5EbFD1b08f43f29597aAd8cA1` | 12,985 |
| StakedRouterExecutor | `0x12EFda5e4D410C5Da723ceb7E43942779E3FE49b` | 2,932 |
| StakedRouterSingleOutput | `0x167d49f106BBeA59587Ef3c63B33e6a421Af1b8d` | 6,067 |
| StakedRouterReceiver | `0x5D84f33b7c9214Df23FD86a0861AC923aF99954d` | 10,165 |
| GenericStakedRoute | `0x5013C0b3DefD8F832d1B6DEC750382946De5c13B` | 3,030 |
| SwitchboardRouter | `0x6026369CcA399352ba68AEDdb89aC65442D1907b` | 4,511 |
| SwitchboardPlug | `0x9ED094fDe2a31BEd0278a4cfdb5528473baFe5a8` | 1,942 |
| SwapRequestCallback | `0xEFB37Bd3a9ed2f768bf6f79d0379fe7f9BE50F49` | 4,183 |
| BungeeInboxOld | `0x92612711D4d07dEbe4964D4d1401D7d7B5a11737` | 12,190 |
| UnwrapAndForward | `0xD31367da48D3f9D6Dd0D59DE4aa1EF6023A88FAD` | 1,831 |

## 4. Addresses — Base (chain ID 8453)

From `deployments/base.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| BungeeInbox | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | 12,375 |
| BungeeGateway | `0x84F06fBaCc4b64CA2f72a4B26191DAD97f2b52BA` | 6,324 |
| Entrypoint | `0x574A7fF7758c18e7985cda39b0Ae6a0B82fCFf87` | 9,914 |
| SwapExecutor | `0x056d246A858B3b53cE5A446868FA4abeAb66B1aA` | 658 |
| CalldataExecutor | `0xa873AaB6A98Cb764Ad6D52820d129D0e3667d9F9` | 740 |
| FeeCollector | `0x1337B8Af481f3d7d245De35dFfCF30B825C20836` | 3,730 |
| Solver | `0xAe68b7117BE0026Cbd4366303f74EEcbB19e4042` | 8,474 |
| SingleOutputRequestImpl | `0xbEB2Ef8B61Ae41611e6656d21551303e4a1E11ba` | 18,498 |
| SwapRequestImpl | `0xF4DB5105aF0A71542a5650Ef017876C38cc0CFeB` | 11,673 |
| RFQRouterSingleOutput | `0xc4088D6E5A2027E784EfC0491C322A3E2621bd9E` | 5,420 |
| CCTPRouterSingleOutput | `0x3b4817827d06600f92296C5d1491818D69Fc955F` | 13,518 |
| CCTPV2RouterSingleOutput | `0x6faEc2944071B2A5EbFD1b08f43f29597aAd8cA1` | 12,985 |
| StakedRouterExecutor | `0x12EFda5e4D410C5Da723ceb7E43942779E3FE49b` | 2,932 |
| StakedRouterSingleOutput | `0x167d49f106BBeA59587Ef3c63B33e6a421Af1b8d` | 6,067 |
| StakedRouterReceiver | `0x5D84f33b7c9214Df23FD86a0861AC923aF99954d` | 10,165 |
| GenericStakedRoute | `0x5013C0b3DefD8F832d1B6DEC750382946De5c13B` | 3,030 |
| SwitchboardRouter | `0x1b243044d1d78E027C4c5ceF8624C7bcAF90CE4a` | 4,511 |
| SwitchboardPlug | `0x464A517d77183051211235641d9304D4BE3f36E1` | 1,942 |
| SwapRequestCallback | `0xd0389e84178f809903cbFE7D1EfAE3EFa9c1769c` | 4,183 |
| BungeeInboxOld | `0x3C54883Ce0d86b3abB26A63744bEb853Ea99a403` | 12,190 |
| UnwrapAndForward | `0xD31367da48D3f9D6Dd0D59DE4aa1EF6023A88FAD` | 1,831 |
| BungeeDepository | `0xA6Cd293BA20873b3CBBBf78F156A1D56D8Ab9347` | 9,630 |

## 5. Addresses — Arbitrum One (chain ID 42161)

From `deployments/arbitrum.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| BungeeInbox | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | 12,375 |
| BungeeGateway | `0xCdEa28Ee7BD5bf7710B294d9391e1b6A318d809a` | 6,324 |
| Entrypoint | `0xdF5F746C18D367Ff9641656b355d54903DE1B2A9` | 9,914 |
| SwapExecutor | `0x0DF289D53fC45f20044b793cEDBB228928953F4B` | 658 |
| CalldataExecutor | `0xa873AaB6A98Cb764Ad6D52820d129D0e3667d9F9` | 740 |
| FeeCollector | `0xf791765B58270Eb6DabFf00D9E3bcD8c0C0567a3` | 3,730 |
| Solver | `0xAe68b7117BE0026Cbd4366303f74EEcbB19e4042` | 8,474 |
| SingleOutputRequestImpl | `0xac7615255677f28B09DA637714E45Ffb5fE76B58` | 18,498 |
| SwapRequestImpl | `0x5f2295051cC021e8DE247DC052B8CE4429D73E7F` | 11,673 |
| RFQRouterSingleOutput | `0xc4088D6E5A2027E784EfC0491C322A3E2621bd9E` | 5,420 |
| CCTPRouterSingleOutput | `0x3b4817827d06600f92296C5d1491818D69Fc955F` | 13,518 |
| CCTPV2RouterSingleOutput | `0x6faEc2944071B2A5EbFD1b08f43f29597aAd8cA1` | 12,985 |
| StakedRouterExecutor | `0x12EFda5e4D410C5Da723ceb7E43942779E3FE49b` | 2,932 |
| StakedRouterSingleOutput | `0x167d49f106BBeA59587Ef3c63B33e6a421Af1b8d` | 6,067 |
| StakedRouterReceiver | `0x5D84f33b7c9214Df23FD86a0861AC923aF99954d` | 10,165 |
| GenericStakedRoute | `0x5013C0b3DefD8F832d1B6DEC750382946De5c13B` | 3,030 |
| SwitchboardRouter | `0x3C54883Ce0d86b3abB26A63744bEb853Ea99a403` | 4,511 |
| SwitchboardPlug | `0x8EAeE07f8FFF38695708be900c1F9aacFB8b3C09` | 1,942 |
| SwapRequestCallback | `0x4682e8315B80cF757e2077280E0471729c992Ed3` | 4,183 |
| BungeeInboxOld | `0xA3BF43451CdEb6DEC588B8833838fC419CE4F54c` | 12,190 |
| UnwrapAndForward | `0xD31367da48D3f9D6Dd0D59DE4aa1EF6023A88FAD` | 1,831 |
| BungeeDepository | `0xA6Cd293BA20873b3CBBBf78F156A1D56D8Ab9347` | 9,630 |

## 6. Addresses — Optimism (chain ID 10)

From `deployments/optimism.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| BungeeInbox | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | 12,375 |
| BungeeGateway | `0x09DAbdD517Ff1e155DeDEF64EC629Ca0285a31af` | 6,324 |
| Entrypoint | `0x73096A2cD977941d0D423fA08F8C14DC5100DCef` | 9,914 |
| SwapExecutor | `0x84F06fBaCc4b64CA2f72a4B26191DAD97f2b52BA` | 658 |
| CalldataExecutor | `0xa873AaB6A98Cb764Ad6D52820d129D0e3667d9F9` | 740 |
| FeeCollector | `0xdb629B83681Db277273808A15be68688CE75a94A` | 3,730 |
| Solver | `0xAe68b7117BE0026Cbd4366303f74EEcbB19e4042` | 8,474 |
| SingleOutputRequestImpl | `0x9c5fbD790A4D7921DBc66b09830F2D485a21f307` | 18,498 |
| SwapRequestImpl | `0x3c819aAEeD5063F4A613032386Be29035E2F043d` | 11,673 |
| RFQRouterSingleOutput | `0xc4088D6E5A2027E784EfC0491C322A3E2621bd9E` | 5,420 |
| CCTPRouterSingleOutput | `0x3b4817827d06600f92296C5d1491818D69Fc955F` | 13,518 |
| CCTPV2RouterSingleOutput | `0x6faEc2944071B2A5EbFD1b08f43f29597aAd8cA1` | 12,985 |
| StakedRouterExecutor | `0x12EFda5e4D410C5Da723ceb7E43942779E3FE49b` | 2,932 |
| StakedRouterSingleOutput | `0x167d49f106BBeA59587Ef3c63B33e6a421Af1b8d` | 6,067 |
| StakedRouterReceiver | `0x5D84f33b7c9214Df23FD86a0861AC923aF99954d` | 10,165 |
| GenericStakedRoute | `0x5013C0b3DefD8F832d1B6DEC750382946De5c13B` | 3,030 |
| SwitchboardRouter | `0xBd5a1D22e83c53Bdd403bb50D5465472D8F05FAD` | 4,511 |
| SwitchboardPlug | `0x0D1A6Fef68F81A407f4d66a7e0229eC198107ECa` | 1,942 |
| SwapRequestCallback | `0xC8E67b4D14A84D3408932a7ED01789d20864B624` | 4,183 |
| BungeeInboxOld | `0x78255f1DeE074fb7084Ee124058A058dE0B1C251` | 12,190 |
| UnwrapAndForward | `0xD31367da48D3f9D6Dd0D59DE4aa1EF6023A88FAD` | 1,831 |
| BungeeDepository | `0xA6Cd293BA20873b3CBBBf78F156A1D56D8Ab9347` | 9,630 |

## 7. Addresses — Polygon PoS (chain ID 137)

From `deployments/polygon.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| BungeeInbox | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | 12,375 |
| BungeeGateway | `0x6DDe7CF4e6A6f53F058Bf5d2B4a54aFBba11EE54` | 6,324 |
| Entrypoint | `0xF0FaB952E363eAa34edCA4d05e330B1dC475f010` | 9,914 |
| SwapExecutor | `0x31D27CeB1A388556F28AaF6BF7B45eFA437B35b8` | 658 |
| CalldataExecutor | `0xa873AaB6A98Cb764Ad6D52820d129D0e3667d9F9` | 740 |
| FeeCollector | `0xecD3D10919a77Ef3352A88816Aea379091a0084B` | 3,730 |
| Solver | `0xAe68b7117BE0026Cbd4366303f74EEcbB19e4042` | 8,474 |
| SingleOutputRequestImpl | `0x4bA60a120b12d070c26393Db76779DeB323e5aA4` | 18,498 |
| SwapRequestImpl | `0xd589562E76a826a01aCcd4Cb31928656c940b769` | 11,673 |
| RFQRouterSingleOutput | `0xc4088D6E5A2027E784EfC0491C322A3E2621bd9E` | 5,420 |
| CCTPRouterSingleOutput | `0x3b4817827d06600f92296C5d1491818D69Fc955F` | 13,518 |
| CCTPV2RouterSingleOutput | `0x6faEc2944071B2A5EbFD1b08f43f29597aAd8cA1` | 12,985 |
| StakedRouterExecutor | `0x12EFda5e4D410C5Da723ceb7E43942779E3FE49b` | 2,932 |
| StakedRouterSingleOutput | `0x167d49f106BBeA59587Ef3c63B33e6a421Af1b8d` | 6,067 |
| StakedRouterReceiver | `0x5D84f33b7c9214Df23FD86a0861AC923aF99954d` | 10,165 |
| GenericStakedRoute | `0x5013C0b3DefD8F832d1B6DEC750382946De5c13B` | 3,030 |
| SwitchboardRouter | `0x69c6702EFC57f3Bb29E9896120246D91B33Bbc44` | 4,511 |
| SwitchboardPlug | `0xFD4AdfA24c351C485D4b05f268c75216DBDCE088` | 1,942 |
| SwapRequestCallback | `0x4682e8315B80cF757e2077280E0471729c992Ed3` | 4,183 |
| BungeeInboxOld | `0x8d2d9F75346DB3c3bF54CCEED25E3D63d1E963F5` | 12,190 |
| UnwrapAndForward | `0xD31367da48D3f9D6Dd0D59DE4aa1EF6023A88FAD` | 1,831 |
| BungeeDepository | `0xA6Cd293BA20873b3CBBBf78F156A1D56D8Ab9347` | 9,630 |

## 8. Addresses — BNB Smart Chain (chain ID 56)

From `deployments/bsc.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| BungeeInbox | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | 12,375 |
| BungeeGateway | `0x9aF2b913679049c966b77934af4CbE7Bb36Cf9D3` | 6,324 |
| Entrypoint | `0xF070dae0a1eae99A27aE2496093F913a2d26E3b3` | 9,914 |
| SwapExecutor | `0x6b1a31Af8A9DC9E8e489035859ca98D6335a0bcB` | 658 |
| CalldataExecutor | `0xa873AaB6A98Cb764Ad6D52820d129D0e3667d9F9` | 740 |
| FeeCollector | `0xE8746d664059067FD9337eb81CEdD632Ffa4325e` | 3,730 |
| Solver | `0xAe68b7117BE0026Cbd4366303f74EEcbB19e4042` | 8,474 |
| SingleOutputRequestImpl | `0x5e01dbBBe59F8987673FAdD1469DdD2Be71e00af` | 18,498 |
| SwapRequestImpl | `0xdcf83CC9CCDfa57aE757021f9457567F67BABeA9` | 11,673 |
| RFQRouterSingleOutput | `0xc4088D6E5A2027E784EfC0491C322A3E2621bd9E` | 5,420 |
| StakedRouterExecutor | `0x12EFda5e4D410C5Da723ceb7E43942779E3FE49b` | 2,932 |
| StakedRouterSingleOutput | `0x167d49f106BBeA59587Ef3c63B33e6a421Af1b8d` | 6,067 |
| StakedRouterReceiver | `0x5D84f33b7c9214Df23FD86a0861AC923aF99954d` | 10,165 |
| GenericStakedRoute | `0x5013C0b3DefD8F832d1B6DEC750382946De5c13B` | 3,030 |
| SwitchboardRouter | `0xD22ef0dEA27049484bF9b4B748eC715dB8c9d646` | 4,511 |
| SwitchboardPlug | `0x4743a14Dd1B32Bf7c89dBB905A83fC513455d2C7` | 1,942 |
| SwapRequestCallback | `0xEFB37Bd3a9ed2f768bf6f79d0379fe7f9BE50F49` | 4,183 |
| BungeeInboxOld | `0x002cd45978F556D817e5FBB4020f7Dd82Bb10941` | 12,190 |
| UnwrapAndForward | `0xD31367da48D3f9D6Dd0D59DE4aa1EF6023A88FAD` | 1,831 |
| BungeeDepository | `0xA6Cd293BA20873b3CBBBf78F156A1D56D8Ab9347` | 9,630 |

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

From `deployments/avalanche.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| BungeeInbox | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | 12,375 |
| BungeeGateway | `0xfe191a43dc4F3d57d7D942717D259005967e4e0D` | 6,324 |
| Entrypoint | `0x64e36517BaCc2b634944658F8bE124C043054F3e` | 9,914 |
| SwapExecutor | `0xbc481539Be2e6990900D34F0Ab54873a177ba019` | 658 |
| CalldataExecutor | `0xa873AaB6A98Cb764Ad6D52820d129D0e3667d9F9` | 740 |
| FeeCollector | `0x717bC2FeCad574ec68Cc1eb074abFD93AdaAb754` | 3,730 |
| Solver | `0xAe68b7117BE0026Cbd4366303f74EEcbB19e4042` | 8,474 |
| SingleOutputRequestImpl | `0x92612711D4d07dEbe4964D4d1401D7d7B5a11737` | 18,498 |
| SwapRequestImpl | `0xb701aB56ACB5897eEc7905afF72b52706638a2ec` | 11,673 |
| RFQRouterSingleOutput | `0xc4088D6E5A2027E784EfC0491C322A3E2621bd9E` | 5,420 |
| CCTPRouterSingleOutput | `0x3b4817827d06600f92296C5d1491818D69Fc955F` | 13,518 |
| CCTPV2RouterSingleOutput | `0x6faEc2944071B2A5EbFD1b08f43f29597aAd8cA1` | 12,985 |
| StakedRouterExecutor | `0x12EFda5e4D410C5Da723ceb7E43942779E3FE49b` | 2,932 |
| StakedRouterSingleOutput | `0x167d49f106BBeA59587Ef3c63B33e6a421Af1b8d` | 6,067 |
| StakedRouterReceiver | `0x5D84f33b7c9214Df23FD86a0861AC923aF99954d` | 10,165 |
| GenericStakedRoute | `0x5013C0b3DefD8F832d1B6DEC750382946De5c13B` | 3,030 |
| SwitchboardRouter | `0x8d00Ad02DF0C7B0C379bc1cb49fD74aA10698bFc` | 4,511 |
| SwitchboardPlug | `0x2261Fe33C0858a4Bb5178e429bF90C3652da961E` | 1,942 |
| SwapRequestCallback | `0x4682e8315B80cF757e2077280E0471729c992Ed3` | 4,183 |
| BungeeInboxOld | `0xEd69eD4Bcdf4cd5E590f383853d73e93Cc383681` | 12,190 |
| UnwrapAndForward | `0xD31367da48D3f9D6Dd0D59DE4aa1EF6023A88FAD` | 1,831 |
| BungeeDepository | `0xA6Cd293BA20873b3CBBBf78F156A1D56D8Ab9347` | 9,630 |

---

## 10. Cross-chain summary

| Chain | ID | BungeeInbox | BungeeGateway | Logs in the pinned window (inbox / gateway) |
|-------|----|-------------|---------------|---------------------------------------------|
| Ethereum | 1 | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | `0xe772551F88E2c14aEcC880dF6b7CBd574561bf82` | 0 / 0 |
| Base | 8453 | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | `0x84F06fBaCc4b64CA2f72a4B26191DAD97f2b52BA` | 0 / 0 |
| Arbitrum One | 42161 | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | `0xCdEa28Ee7BD5bf7710B294d9391e1b6A318d809a` | 0 / 0 |
| Optimism | 10 | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | `0x09DAbdD517Ff1e155DeDEF64EC629Ca0285a31af` | 0 / 0 |
| Polygon PoS | 137 | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | `0x6DDe7CF4e6A6f53F058Bf5d2B4a54aFBba11EE54` | 0 / 0 |
| BNB Smart Chain | 56 | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | `0x9aF2b913679049c966b77934af4CbE7Bb36Cf9D3` | 0 / 0 |
| Avalanche C-Chain | 43114 | `0x5E0f8E7337C8955D2124b8e85Ca74aF884b3E124` | `0xfe191a43dc4F3d57d7D942717D259005967e4e0D` | 0 / 0 |
| Robinhood Chain | 4663 | — (no code) | — | not deployed |

**Robinhood Chain (4663): no Bungee Auto deployment.** No `deployments/robinhood.json` exists, and `eth_getCode` returns `0x` at the addresses that the other chains share (BungeeInbox, RFQ router, SocketDeployFactory, staked routers, CalldataExecutor).

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| BungeeGateway | Not a proxy; implementation table | EIP-1967 implementation slot empty. `addImpl` / `removeImpl` change the implementation of an `implId` (`ImplAdded`, `ImplRemoved`). | Owner (two-step) and roles. |
| BungeeInbox, routers, Switchboard, executors | Plain contracts | EIP-1967 implementation slot empty. | Owner and roles. |

---

## 12. Detection invariants & gotchas

1. **Join source and destination by `requestHash`.** `RequestExtracted` (source gateway) and `RequestFulfilled` (destination gateway) carry it as topic1.
2. **Extraction is not a payout.** `RequestExtracted` moves the user's funds from the wallet into the request's router on the source chain; the user is paid by `RequestFulfilled` on the destination.
3. **Settlement lags the fill.** `RequestSettled` on the source arrives after the Switchboard message (`RequestsSettledOnDestination` on the destination); it credits the solver, not the user. A refund to the user is `RequestCancelled` on the origin, after `RequestCancelledOnDestination`.
4. **Admin triggers.** `ImplAdded`, `ImplRemoved`, `RoleGranted`, `RoleRevoked`, `OwnerNominated`, `OwnerClaimed` at the gateway and the inbox.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_BUNGEE_SINGLE_OUTPUT_REQUEST_CREATED       = '\xaafaed86f175a2b5a9812043ba82df1a5d0ab905b78d0f4bea5ca66a05b12183'
TOPIC_BUNGEE_SINGLE_OUTPUT_REQUEST_WITHDRAWN     = '\xf434768883a3ab10e133a3543933614318754252dae7fba45ecb5190b2850a0a'
TOPIC_BUNGEE_SWAP_REQUEST_CREATED                = '\x5f35e6c87802b75b33eba5733b4ded8a8b8d406d93e2227ed7d74f134b390d67'
TOPIC_BUNGEE_SWAP_REQUEST_WITHDRAWN              = '\xa60380b825a601e4b8fc7abe6ef2b41879098292cfd96335954f819ba271f09f'
TOPIC_BUNGEE_REQUEST_EXTRACTED                   = '\x14a241d5b404d2061ceb9a847972acfd690983f1d8a0fef9779b8191aa1b7ef2'
TOPIC_BUNGEE_REQUEST_FULFILLED                   = '\xd83e4fbd120e768f3bb813ecfa1a2b16c323fa7dfa07db1cd6434b3cbc97bc75'
TOPIC_BUNGEE_REQUEST_SETTLED                     = '\x7eea86cc10df3b8a859a99d48d6858b1128a479f035d0223cf9dd929f37c6079'
TOPIC_BUNGEE_REQUEST_SETTLEMENT_FAILED           = '\x07349f83fa11ddca53ca675ac3efd87202dffc9178afef9b223b3976e1949a47'
TOPIC_BUNGEE_REQUEST_CANCELLED                   = '\xc74d65bbb9e63c78e05140eda2a63c9011b58af244ec5c5e596d4842fe84d329'
TOPIC_BUNGEE_REQUEST_CANCELLED_ON_DESTINATION    = '\x315b5b12b5749bb31d7d3c18cee689619f441a29bbf35a2f958394e3fd309762'
TOPIC_BUNGEE_REQUESTS_SETTLED_ON_DESTINATION     = '\x3e09b55b6efb54718ae4486c6229eaf5afca42c1aed76e189d9cfaeb3b539f4e'
TOPIC_BUNGEE_WITHDRAW_ON_DESTINATION             = '\xe6cea8072222bb5dd02862b1f55e8609a98566d603d56964af44c187c81536ed'
TOPIC_BUNGEE_REQUEST_REFUNDED                    = '\x3754b0090c75d1f0866f0d41983f3eadd3b0de510c67e67e0ad24a94b756d9f1'
TOPIC_BUNGEE_IMPL_ADDED                          = '\x891e2f61914a277b540f6cbff39daf187f334f204a2576ff5e72303d1cf2ce8b'
TOPIC_BUNGEE_IMPL_REMOVED                        = '\x21f97cc4493d15a39bb3e09017843c80cc31e5f6d3e35769cbde2d51caf993ab'

-- ===== Selectors (chain-agnostic) =====
SEL_BUNGEE_INBOX_CREATE_SINGLE_OUTPUT_REQUEST   = '\x7d9ead2b'
SEL_BUNGEE_INBOX_CREATE_SWAP_REQUEST            = '\x4cdfec6e'
SEL_BUNGEE_GATEWAY_EXECUTE_IMPL                 = '\x276a2ced'
SEL_BUNGEE_GATEWAY_INBOUND_MSG                  = '\xc66eaeb6'

-- ===== Addresses (network-specific) =====
ETH_BUNGEE_INBOX                                 = '\x5e0f8e7337c8955d2124b8e85ca74af884b3e124'
ETH_BUNGEE_GATEWAY                               = '\xe772551f88e2c14aecc880df6b7cbd574561bf82'
ETH_BUNGEE_RFQ_ROUTER                            = '\xc4088d6e5a2027e784efc0491c322a3e2621bd9e'
ETH_BUNGEE_SWITCHBOARD_ROUTER                    = '\x6026369cca399352ba68aeddb89ac65442d1907b'
BASE_BUNGEE_INBOX                                = '\x5e0f8e7337c8955d2124b8e85ca74af884b3e124'
BASE_BUNGEE_GATEWAY                              = '\x84f06fbacc4b64ca2f72a4b26191dad97f2b52ba'
BASE_BUNGEE_RFQ_ROUTER                           = '\xc4088d6e5a2027e784efc0491c322a3e2621bd9e'
BASE_BUNGEE_SWITCHBOARD_ROUTER                   = '\x1b243044d1d78e027c4c5cef8624c7bcaf90ce4a'
ARB_BUNGEE_INBOX                                 = '\x5e0f8e7337c8955d2124b8e85ca74af884b3e124'
ARB_BUNGEE_GATEWAY                               = '\xcdea28ee7bd5bf7710b294d9391e1b6a318d809a'
ARB_BUNGEE_RFQ_ROUTER                            = '\xc4088d6e5a2027e784efc0491c322a3e2621bd9e'
ARB_BUNGEE_SWITCHBOARD_ROUTER                    = '\x3c54883ce0d86b3abb26a63744beb853ea99a403'
OP_BUNGEE_INBOX                                  = '\x5e0f8e7337c8955d2124b8e85ca74af884b3e124'
OP_BUNGEE_GATEWAY                                = '\x09dabdd517ff1e155dedef64ec629ca0285a31af'
OP_BUNGEE_RFQ_ROUTER                             = '\xc4088d6e5a2027e784efc0491c322a3e2621bd9e'
OP_BUNGEE_SWITCHBOARD_ROUTER                     = '\xbd5a1d22e83c53bdd403bb50d5465472d8f05fad'
POLY_BUNGEE_INBOX                                = '\x5e0f8e7337c8955d2124b8e85ca74af884b3e124'
POLY_BUNGEE_GATEWAY                              = '\x6dde7cf4e6a6f53f058bf5d2b4a54afbba11ee54'
POLY_BUNGEE_RFQ_ROUTER                           = '\xc4088d6e5a2027e784efc0491c322a3e2621bd9e'
POLY_BUNGEE_SWITCHBOARD_ROUTER                   = '\x69c6702efc57f3bb29e9896120246d91b33bbc44'
BNB_BUNGEE_INBOX                                 = '\x5e0f8e7337c8955d2124b8e85ca74af884b3e124'
BNB_BUNGEE_GATEWAY                               = '\x9af2b913679049c966b77934af4cbe7bb36cf9d3'
BNB_BUNGEE_RFQ_ROUTER                            = '\xc4088d6e5a2027e784efc0491c322a3e2621bd9e'
BNB_BUNGEE_SWITCHBOARD_ROUTER                    = '\xd22ef0dea27049484bf9b4b748ec715db8c9d646'
AVAX_BUNGEE_INBOX                                = '\x5e0f8e7337c8955d2124b8e85ca74af884b3e124'
AVAX_BUNGEE_GATEWAY                              = '\xfe191a43dc4f3d57d7d942717d259005967e4e0d'
AVAX_BUNGEE_RFQ_ROUTER                           = '\xc4088d6e5a2027e784efc0491c322a3e2621bd9e'
AVAX_BUNGEE_SWITCHBOARD_ROUTER                   = '\x8d00ad02df0c7b0c379bc1cb49fd74aa10698bfc'
```

---

## 14. Verification & sources

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the explorer-verified ABIs of BungeeInbox, BungeeGateway, RFQRouter and StakedRouterReceiver on Ethereum.
- **Addresses:** from `deployments/<network>.json` of `SocketDotTech/bungee-contracts-public`, existence-checked with `eth_getCode`.
- **Activity:**

  | Contract (address-wide scan, pinned window) | ETH | Base | Arb | OP | Poly | BNB | Avax |
  |---|---|---|---|---|---|---|---|
  | BungeeInbox, all topics | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | BungeeGateway, all topics | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

  - Last activity on Ethereum (explorer log listing of the address, read on 2026-09-29): BungeeGateway `0xe772551F88E2c14aEcC880dF6b7CBd574561bf82` block 25845552 (2026-08-27 09:06:35 UTC, `RequestExtracted`, transaction `0xa9457497b367534bd2cb193cea7cb26c11ab85623bb2c63d765c6c0ea413dbfe`); BungeeInbox block 25832093 (2026-08-25 12:04:11 UTC, `SingleOutputRequestWithdrawn`, transaction `0x7e077dd468f4896d52755891ffe198810f88459d1eb7bc6346a5770dc5847f09`). Block times read from the chain.

Authoritative sources:
- [SocketDotTech/bungee-contracts-public](https://github.com/SocketDotTech/bungee-contracts-public) (`deployments/`)
- Explorers (verified sources) — [BungeeGateway on Blockscout](https://eth.blockscout.com/address/0xe772551F88E2c14aEcC880dF6b7CBd574561bf82) · [BungeeInbox on Blockscout](https://eth.blockscout.com/address/0x5e0f8e7337c8955d2124b8e85ca74af884b3e124) · [BungeeGateway on Etherscan](https://etherscan.io/address/0xe772551F88E2c14aEcC880dF6b7CBd574561bf82)
