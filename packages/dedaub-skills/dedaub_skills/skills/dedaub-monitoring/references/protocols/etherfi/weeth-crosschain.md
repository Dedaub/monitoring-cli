# ether.fi weETH & ETHFI Cross-Chain — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Robinhood Chain, Arc)

**Status:** verified against live RPC on every listed chain on 2026-10-30. Addresses come from the official ether.fi "Deployed Contracts" page and the `etherfi-protocol/weETH-cross-chain` registry (`registry/chains.json`, `utils/L2Constants.sol`). Topics and selectors come from the verified implementation ABIs.
**Scope:** how weETH and ETHFI leave Ethereum: the weETH **LayerZero V2 OFT mesh** (Ethereum lockbox adapter + burn/mint OFTs), the **native-minting** L2 sync pools on Base and Optimism, the **Arbitrum canonical-bridge** weETH, and the **ETHFI OFT mesh**. Topics and selectors are chain-agnostic. Addresses are per chain. Polygon PoS has **no** ether.fi token deployment.

**Two bridge models.** (1) **OFT mesh.** On Ethereum, weETH is locked in the adapter `0xcd2e…CA63`. On each other chain an `EtherfiOFTUpgradeable` token burns and mints. `OFTSent`/`OFTReceived` fire on both sides. (2) **Arbitrum is different.** Arbitrum weETH `0x3575…4dbe` is an Arbitrum `StandardArbERC20` minted by the Arbitrum L2 ERC20 gateway `0x09e9…1eEE`. The Ethereum adapter has **no** Arbitrum peer (`peers(30110)` = 0). The generic layerzero/v2.md and arbitrum_native docs cover the transport layer.

**Native minting.** On Base and Optimism a user can deposit ETH into an L2 sync pool and get weETH minted on the L2 at once (`L2SyncPool.deposit` → OFT `mint`). The pool later calls `sync()`. That sends a LayerZero message plus the ETH by the canonical bridge to `L1SyncPool` `0xD789…A146` on Ethereum. The L1 pool deposits the ETH into `LiquidityPool` and backs the L2 supply. The L2 price comes from `EtherfiL2ExchangeRateProvider`, which reads a Chainlink `weETH / ETH` feed.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 weETH OFT (`EtherfiOFTUpgradeable`) and Ethereum OFT adapter (`EtherfiOFTAdapterUpgradeable`)
| topic0 | Event |
|--------|-------|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` |
| `0xbe4864a8e820971c0247f5992e2da559595f7bf076a21cb5928d443d2a13b674` | `EnforcedOptionSet((uint32,uint16,bytes)[] _enforcedOptions)` |
| `0x983af742b0b5ca79aa5c0be76cea126e1baf3139ecd04624deac13853c4bebde` | `InboundRateLimitsChanged((uint32,uint256,uint256)[] rateLimitConfigs)` |
| `0x55254e344b7fc8e2e038c1f7f20a1c7afe659c1a3bbfc4e35dd1ca9bba0ca0a0` | `OutboundRateLimitsChanged((uint32,uint256,uint256)[] rateLimitConfigs)` |
| `0xf0be4f1e87349231d80c36b33f9e8639658eeaf474014dee15a3e6a4d4414197` | `MsgInspectorSet(address inspector)` |
| `0xd48d879cef83a1c0bdda516f27b13ddb1b3f8bbac1c9e1511bb2a659c2427760` | `PreCrimeSet(address preCrimeAddress)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |

> The same impl ABI is deployed on Base (`0xde8a…43d1`), OP/BNB (`0x70d7…aA9`) and Avalanche/Robinhood/Arc (`0x08db…A748`). The topic set is identical on all three. `OFTSent`/`OFTReceived` are the generic LayerZero OFT topics: every OFT token emits them. Key on the emitter.

### 1.2 Native minting — L2 sync pool (Base `EtherfiL2ModeSyncPoolETH`, OP `L2OPStackSyncPoolETHUpgradeable`)
| topic0 | Event |
|--------|-------|
| `0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15` | `Deposit(address indexed tokenIn, uint256 amountIn, uint256 amountOut)` |
| `0x66bfea63a3d589c5d7bbe344440ccf4b219832ab3266091fbf2d8875fbf065b8` | `DepositWithReferral(address indexed sender, uint256 amount, address referral)` |
| `0xdb49c955bbc09ebed0b7337419bcbc9ce581910150a5b1f91159e653a0a4978e` | `Sync(uint32 dstEid, address indexed tokenIn, uint256 amountIn, uint256 amountOut)` |
| `0x4a0f73c7c1971268d36d35f4aa566bc6bf4d11a95048a36db084492132ab6f74` | `L2ExchangeRateProviderSet(address l2ExchangeRateProvider)` |
| `0x3881bcae1b79d28312da310a8d211e93a9d6ea5a30e04f43bca54b0768e5b3e7` | `RateLimiterSet(address rateLimiter)` |
| `0x94ba8d5f7922370aad18b707619f668a8fd07cbdf364eeaa6a048e737c9f2a82` | `MinSyncAmountSet(address tokenIn, uint256 minSyncAmount)` |
| `0xb68fd1a788a85f8f18de7976d851969ff9ff2216de81169c17a6f4ac94c23def` | `ReceiverSet(address receiver)` |
| `0xe6d4148fa8480ba4cb586ab5df8951ddaeddaab62b2a0dc1ad370bc198cb4ce4` | `DstEidSet(uint32 dstEid)` |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` |
| `0xe32dd0e1ba6b23ac15f09a0c455561d7dbc2ad9b22f20259edfd397ae8ca8516` | `RateParametersSet(address token, address rateOracle, uint64 depositFee, uint32 freshPeriod)` |
| `0x75734bff051d085f94244c3b739b0dab1e47933c9afdb3566f2e39ece31aeeaa` | `UpdatedAdmin(address indexed admin, bool status)` |
| `0x85cd1b4925ff24a817c00622085a8e26f7f6d76012b93f751375a4ce2b8be6f9` | `UpdatedPauser(address indexed pauser, bool status)` |

### 1.3 Native minting — `L1SyncPool` (Ethereum `0xD789…A146`, `EtherfiL1SyncPoolETH`)
| topic0 | Event |
|--------|-------|
| `0xa089f492661ec30f616b1832904023bf44486a5bc56e729fc89bcd0b804cb526` | `InsufficientDeposit(uint32 indexed originEid, bytes32 guid, uint256 actualAmountOut, uint256 expectedAmountOut, uint256 unbackedTokens)` |
| `0xfb0c5352582a29d48fc4633bcde5055e28e653e2332400344eb55a3c5337af87` | `Fee(uint32 indexed originEid, bytes32 guid, uint256 actualAmountOut, uint256 expectedAmountOut, uint256 fee)` |
| `0xd40853e1a2bd39892d9b328c8a345de047a40d40b6b1c1220206a13a55f3d045` | `DummyTokenSet(uint32 originEid, address dummyToken)` |
| `0x91a78db8b70a6d450735b196f83bc5ea6c8b5ce7ac516d8a774daa0bbdb7727e` | `ReceiverSet(uint32 indexed originEid, address receiver)` |
| `0xae89cc546a32817df9e4d341f457b8ed8e6978ead08b129c47dd36a5a25314a9` | `LiquifierSet(address liquifier)` |
| `0xa0d5e8b51197b9b55e3cab7ce2df1d6e544a83b48bce8b14e28ae6b8d7923da9` | `LockBoxSet(address lockBox)` |
| `0x911ee1e2b03817cdb041d13f742d20850bfa79a83a1748a1b13bfc492ad5ba60` | `TokenOutSet(address tokenOut)` |
| `0x3775f769836afe879aa3c9566e0e76c7319f2c89727ed1d1c872d67eead2ff43` | `EEthSet(address eEth)` |
| `0xed679328aebf74ede77ae09efcf36e90244f83643dadac1c2d9f0b21a46f6ab7` | `Sweep(address token, address receiver, uint256 amount)` |

> Live (sampled, 150 most recent logs): `InsufficientDeposit` 137, `PeerSet` 9. `InsufficientDeposit` fires when the bridged ETH is less than the weETH already minted on L2 (`unbackedTokens` > 0). It is the key solvency signal for native minting.

### 1.4 Arbitrum weETH (`StandardArbERC20` beacon proxy)
| topic0 | Event |
|--------|-------|
| `0xe19260aff97b920c7df27010903aeb9c8d2be5d310a2c67824cf3f15396e4c16` | `Transfer(address indexed from, address indexed to, uint256 value, bytes data)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |

> The 4-argument `Transfer(address,address,uint256,bytes)` is the ERC-677 `transferAndCall` event. Gateway mint/burn shows as a 3-argument `Transfer` from/to `0x0`. The deposit itself is on the Arbitrum gateway (see arbitrum_native).

### 1.5 ETHFI OFT mesh (`EtherfiOFTAdapterUpgradeable` on Ethereum, `EtherfiMintBurnOFTAdapter` on Base/Arbitrum, `OFTUpgradeable` on Optimism)
Same `OFTSent` `0x8549…e59a` / `OFTReceived` `0xefed…fd9c` / `PeerSet` `0x2383…98b` topics as §1.1.

---

## 2. Function signatures (chain-agnostic)

### 2.1 weETH OFT / adapter
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xc7c7f5b3` | `send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)` | payable -> ((bytes32,uint64,(uint256,uint256)),(uint256,uint256)) |
| `0x3b6f743b` | `quoteSend((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),bool)` | view -> ((uint256,uint256)) |
| `0x0d35b415` | `quoteOFT((uint32,bytes32,uint256,uint256,bytes,bytes,bytes))` | view -> ((uint256,uint256),(int256,string)[],(uint256,uint256)) |
| `0x13137d65` | `lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)` | payable -> () |
| `0x40c10f19` | `mint(address,uint256)` | -> () |
| `0x3400288b` | `setPeer(uint32,bytes32)` | -> () |
| `0xbb0b6a53` | `peers(uint32)` | view -> (bytes32) |
| `0xf51b1aca` | `setInboundRateLimits((uint32,uint256,uint256)[])` | -> () |
| `0xe96e38e2` | `setOutboundRateLimits((uint32,uint256,uint256)[])` | -> () |
| `0x55b56c0c` | `inboundRateLimits(uint32)` | view -> (uint256,uint256,uint256,uint256) |
| `0x51c32a88` | `outboundRateLimits(uint32)` | view -> (uint256,uint256,uint256,uint256) |
| `0x7dd0480f` | `pauseBridge()` | -> () |
| `0xa82f143c` | `unpauseBridge()` | -> () |
| `0x5e280f11` | `endpoint()` | view -> (address) |
| `0xfc0c546a` | `token()` | view -> (address) |

> `mint(address,uint256)` exists only on the L2 OFT. `MINTER_ROLE` is held by the native-minting sync pool on Base/OP. The Ethereum adapter has no `mint`.

### 2.2 Native minting
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x0efe6a8b` | `deposit(address,uint256,uint256)` | payable -> (uint256) |
| `0x8b6099db` | `deposit(address,uint256,uint256,address)` | payable -> (uint256) |
| `0x03e74675` | `sync(address,bytes,(uint256,uint256))` | payable -> (uint256,uint256) |
| `0x08c35649` | `getConversionAmount(address,uint256)` | view -> (uint256) |
| `0x16089ef9` | `getConversionAmountUnsafe(address,uint256)` | view -> (uint256) |
| `0x23643524` | `getRateParameters(address)` | view -> ((address,uint64,uint32)) |
| `0x0f9566e6` | `setRateParameters(address,address,uint64,uint32)` | -> () |
| `0x141fb08a` | `onMessageReceived(uint32,bytes32,address,uint256,uint256)` | payable -> () |
| `0x09f37812` | `setReceiver(uint32,address)` | -> () |
| `0x86dc6e9a` | `setDummyToken(uint32,address)` | -> () |
| `0x62c06767` | `sweep(address,address,uint256)` | -> () |

### 2.3 Arbitrum weETH
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x8c2a993e` | `bridgeMint(address,uint256)` | -> () |
| `0x74f4f547` | `bridgeBurn(address,uint256)` | -> () |
| `0xc2eeeebd` | `l1Address()` | view -> (address) |
| `0x8fa74a0e` | `l2Gateway()` | view -> (address) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

| Role | Address | Pattern / notes |
|------|---------|-----------------|
| weETH (home token) | `0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee` | see [core.md](core.md) |
| **weETH OFT adapter** (lockbox) | `0xcd2eb13D6831d4602D80E5db9230A57596CDCA63` | Transparent proxy → `0xa82cc578927058af14fd84d96a817dc85ac4f946`; ProxyAdmin `0xa9E9bBf04F95688D7fd82036f83544630E463CAc`; `owner()` = Operating Timelock `0xcD42…5d7a` |
| **L1SyncPool** | `0xD789870beA40D056A4d26055d0bEFcC8755DA146` | Transparent proxy → `0x5d310451276d28a90cc6910449052d29a41e3abd`; ProxyAdmin `0xDBf6bE120D4dc72f01534673a1223182D9F6261D` |
| L1 receiver / dummy token — Base | `0x8963C96186bd05995AdaA9E1fda25B7181CCBc37` / `0x0295E0CE709723FB25A28b8f67C54a488BA5aE46` | Transparent proxies (impl `0x40819e33…11ca` / `0x20e88508…09ad`) |
| L1 receiver / dummy token — Optimism | `0x23CA5E5300d3b35a47DFeF6A36Ecba5AC0a96E03` / `0x6a26E8894B9BBD684A13647f67822ef142E0E45e` | Transparent proxies (impl `0xc25b0d51…d5f8` / `0x404f91bf…ecc9`) |
| ETHFI (home token) | `0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB` | immutable |
| **ETHFI OFT adapter** | `0xe0080d2F853ecDdbd81A643dC10DA075Df26fD3f` | UUPS (170 B) → `0xcc2b11a4ff737f4a23f55d49eca7d9b03e502b9d`; `token()` = ETHFI; `owner()` = `0x2aCA71020De61bb532008049e1Bd41E451aE8AdC` (L1 controller Safe) |

## 4. Addresses — the other chains

| Chain (ID, LZ eid) | weETH | Impl (EIP-1967) | ProxyAdmin | Owner | Other ether.fi pieces |
|--------------------|-------|-----------------|------------|-------|-----------------------|
| Base (8453, 30184) | `0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A` | `0xde8a2c33655aca88f258988ed74d1511876343d1` | `0x2F6f3cc4a275C7951FB79199F01eD82421eDFb68` | L2 Timelock `0x851D…F5C6` | Sync pool `0xc38e046dFDAdf15f7F56853674242888301208a5` (impl `0x390624d6…b984`); rate provider `0xF2c5519c634796B73dE90c7Dc27B4fEd560fC3ca`; Chainlink weETH/ETH feed `0x35e9D7001819Ea3B39Da906aE6b06A62cfe2c181`; ETHFI `0x6C240DDA6b5c336DF09A4D011139beAAa1eA2Aa2` + ETHFI mint/burn adapter `0xe0080d2F…fD3f` |
| BNB (56, 30102) | `0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A` | `0x70d7e0c93d8443325550ba3f71576f5f346b8aa9` | `0x2F6f3cc4a275C7951FB79199F01eD82421eDFb68` | L2 Timelock | no sync pool; no ETHFI |
| Avalanche (43114, 30106) | `0xA3D68b74bF0528fdD07263c60d6488749044914b` | `0x08db0db9b5f2dcbbfdc26ff411fb2026e81da748` | `0x373ea3AEC25eB652ACa38504254eCD5459da6d19` | L2 Timelock | no sync pool; no ETHFI |
| Arbitrum (42161, 30110) | `0x35751007a407ca6FEFfE80b3cB397736D2cf4dbe` | **not an OFT**: `ClonableBeaconProxy`, beacon `0xe72ba9418b5f2ce0a6a40501fe77c6839aa37333` (owner `0xcf5757…a827`, not an ether.fi address) | — | Arbitrum (not ether.fi) | `l1Address()` = Ethereum weETH; `l2Gateway()` = `0x09e9222E96E7B4AE2a407B98d48e330053351EEe`. ETHFI `0x7189fb5B6504bbfF6a852B13B7B82a3c118fDc27` + ETHFI adapter `0xe0080d2F…fD3f` |
| Optimism (10, 30111) | `0x5A7fACB970D094B6C7FF1df0eA68D99E6e73CBFF` | `0x70d7e0c93d8443325550ba3f71576f5f346b8aa9` | `0x632304Edc891Afed1a7bDe9A40b19F1c393ad5F3` | L2 Timelock | Sync pool `0xC9475e18E2C5C26EA6ADCD55fabE07920beA887e` (impl `0xaeae84d0…71dc`); bucket rate limiter `0x9685Ff6E421F163A9A2FbB831F28344f8e4a964a`; rate provider `0xAaE0d7D8147C9f2C39A0B19974f8E684fA2bbA6f`; Chainlink weETH/ETH feed `0xb4479d436DDa5c1A79bD88D282725615202406E3`; **ETHFI OFT** = `0xe0080d2F853ecDdbd81A643dC10DA075Df26fD3f` (the token itself, UUPS → `0x4bfd4aae…ccfd1`) |
| Polygon PoS (137, 30109) | — | — | — | — | no weETH, no ETHFI (`peers(30109)` = 0 on both Ethereum adapters) |
| Robinhood Chain (4663, 30416) | `0xA3D68b74bF0528fdD07263c60d6488749044914b` | `0x08db0db9b5f2dcbbfdc26ff411fb2026e81da748` | `0x373ea3AEC25eB652ACa38504254eCD5459da6d19` | L2 Timelock | none (see [liquid.md](liquid.md) for an empty liquidUSD vault) |
| Arc (5042, 30417) | `0xA3D68b74bF0528fdD07263c60d6488749044914b` | `0x08db0db9b5f2dcbbfdc26ff411fb2026e81da748` | `0x373ea3AEC25eB652ACa38504254eCD5459da6d19` | L2 Timelock | none |

**L2 Timelock** = `0x851Dd540f4D2Ec78120De0a0cc87B21EdE5Df5C6`, the same literal on Base, BNB, Avalanche, Optimism, Robinhood Chain and Arc (OZ `TimelockController`, min delay 259,200 s = 3 days on Optimism). It owns the OFT and its ProxyAdmin.

---

## 5. Cross-chain summary

| Chain | weETH model | weETH address | totalSupply (2026-10-30) | Ethereum adapter peer | Native minting | ETHFI |
|-------|-------------|---------------|--------------------------|-----------------------|----------------|-------|
| Ethereum (1) | home + lockbox | `0xCd5f…b7ee` / adapter `0xcd2e…CA63` | — | — | L1SyncPool | home `0xFe0c…eB` + adapter `0xe008…fD3f` |
| Base (8453) | OFT | `0x04C0…150A` | 14,928 | ✓ | ✓ | ✓ |
| BNB (56) | OFT | `0x04C0…150A` | 1.46 | ✓ | — | — |
| Avalanche (43114) | OFT | `0xA3D6…914b` | 18.31 | ✓ | — | — |
| Arbitrum (42161) | Arbitrum canonical gateway | `0x3575…4dbe` | 44,233 | — (no peer) | — | ✓ (`0x7189…Dc27`) |
| Optimism (10) | OFT | `0x5A7f…CBFF` | 10,524 | ✓ | ✓ | ✓ (OFT `0xe008…fD3f`) |
| Polygon PoS (137) | — | — | — | — | — | — |
| Robinhood Chain (4663) | OFT | `0xA3D6…914b` | 0.366 | ✓ | — | — |
| Arc (5042) | OFT | `0xA3D6…914b` | 0.00255 | ✓ | — | — |

Vanity tells: `0xA3D68b74…914b` is the CREATE3 literal for every chain onboarded since 2025 (also Sonic, HyperEVM, Ink, Plasma, Monad). `0x04C0599A…150A` is shared by Base, BNB, Blast and Mode.

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| weETH OFTs (all OFT chains), Ethereum weETH adapter, L1SyncPool, L1 receivers/dummy tokens, L2 sync pools, rate providers, OP rate limiter | EIP-1967 **Transparent** | impl **and** admin slot set | ProxyAdmin (per chain, table §4) owned by the L2 Timelock (L2) or Operating Timelock (L1 adapter) |
| ETHFI OFT adapter (Ethereum), ETHFI OFT (OP), ETHFI token (Base/Arb) | UUPS | impl slot set, admin slot `0x0` | owner (controller Safe) |
| Arbitrum weETH | `ClonableBeaconProxy` | beacon slot `0xe72b…7333` | beacon owner `0xcf5757…a827` (not ether.fi) |

Watch `Upgraded(address)` `0xbc7cd75a…2d3b` and `AdminChanged` `0x7e644d79…7f2f` on every proxy, plus `PeerSet` and the rate-limit change topics.

---

## 7. Detection invariants & gotchas

1. **Arbitrum is not in the OFT mesh.** An Arbitrum weETH move to Ethereum is an Arbitrum gateway withdrawal, not an `OFTSent`. Do not expect an OFT event pair.
2. **One literal, different implementations.** `0xA3D6…914b` and `0x04C0…150A` are proxies. The impl differs per chain (`0x08db…`, `0x70d7…`, `0xde8a…`). The topic set is the same. Code size also differs (Avalanche 756 B, Robinhood 1,087 B, Arc 1,088 B).
3. **`0xe0080d2F…fD3f` has three roles.** On Ethereum it is the ETHFI OFT adapter. On Base and Arbitrum it is an ETHFI mint/burn adapter for the local ETHFI token. On Optimism it **is** the ETHFI token. It has no code on BNB, Avalanche, Polygon, Robinhood Chain or Arc.
4. **Native-minted weETH is unbacked until sync.** L2 `Deposit` mints weETH at once. Backing arrives on Ethereum only after `Sync` and the canonical-bridge delay. Watch `L1SyncPool.InsufficientDeposit` (`unbackedTokens`) and compare L2 minted vs L1 received.
5. **The L2 price is an oracle read.** `getConversionAmount()` uses the Chainlink `weETH / ETH` feed with a `freshPeriod`. `getConversionAmountUnsafe()` skips the freshness check. A stale feed blocks deposits in the safe path only.
6. **Rate limits are per peer eid.** `OutboundRateLimitsChanged`/`InboundRateLimitsChanged` carry `(eid, limit, window)` arrays. A drop to 0 pauses a lane. `pauseBridge()` pauses all lanes.
7. **`deposit(address,uint256,uint256)` selector `0x0efe6a8b` collides** with the Liquid Teller `deposit` on Ethereum ([liquid.md](liquid.md)). Key on the target address.
8. **Supply on Robinhood Chain and Arc is tiny** (0.366 and 0.00255 weETH). A large mint there is unusual. The OFT on both chains is real (owner = L2 Timelock, `endpoint()` = the local EndpointV2), not a decoy.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_OFT_SENT                   = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED               = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_OFT_PEER_SET               = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_OFT_INBOUND_LIMITS         = '\x983af742b0b5ca79aa5c0be76cea126e1baf3139ecd04624deac13853c4bebde'
TOPIC_OFT_OUTBOUND_LIMITS        = '\x55254e344b7fc8e2e038c1f7f20a1c7afe659c1a3bbfc4e35dd1ca9bba0ca0a0'
TOPIC_OFT_PAUSED                 = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_L2SP_DEPOSIT               = '\x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15'
TOPIC_L2SP_DEPOSIT_REFERRAL      = '\x66bfea63a3d589c5d7bbe344440ccf4b219832ab3266091fbf2d8875fbf065b8'
TOPIC_L2SP_SYNC                  = '\xdb49c955bbc09ebed0b7337419bcbc9ce581910150a5b1f91159e653a0a4978e'
TOPIC_L1SP_INSUFFICIENT_DEPOSIT  = '\xa089f492661ec30f616b1832904023bf44486a5bc56e729fc89bcd0b804cb526'
TOPIC_L1SP_FEE                   = '\xfb0c5352582a29d48fc4633bcde5055e28e653e2332400344eb55a3c5337af87'
TOPIC_RATE_PARAMETERS_SET        = '\xe32dd0e1ba6b23ac15f09a0c455561d7dbc2ad9b22f20259edfd397ae8ca8516'
TOPIC_ARB_TRANSFER_AND_CALL      = '\xe19260aff97b920c7df27010903aeb9c8d2be5d310a2c67824cf3f15396e4c16'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_OFT_SEND                     = '\xc7c7f5b3'
SEL_OFT_MINT                     = '\x40c10f19'
SEL_OFT_SET_PEER                 = '\x3400288b'
SEL_OFT_PAUSE_BRIDGE             = '\x7dd0480f'
SEL_L2SP_DEPOSIT                 = '\x0efe6a8b'
SEL_L2SP_DEPOSIT_REFERRAL        = '\x8b6099db'
SEL_L2SP_SYNC                    = '\x03e74675'
-- ===== Addresses =====
ETH_ETHERFI_WEETH_OFT_ADAPTER    = '\xcd2eb13d6831d4602d80e5db9230a57596cdca63'
ETH_ETHERFI_L1_SYNC_POOL         = '\xd789870bea40d056a4d26055d0befcc8755da146'
ETH_ETHERFI_ETHFI_OFT_ADAPTER    = '\xe0080d2f853ecddbd81a643dc10da075df26fd3f'
BASE_ETHERFI_WEETH               = '\x04c0599ae5a44757c0af6f9ec3b93da8976c150a'
BASE_ETHERFI_L2_SYNC_POOL        = '\xc38e046dfdadf15f7f56853674242888301208a5'
BASE_ETHERFI_RATE_PROVIDER       = '\xf2c5519c634796b73de90c7dc27b4fed560fc3ca'
BASE_ETHERFI_ETHFI               = '\x6c240dda6b5c336df09a4d011139beaaa1ea2aa2'
BNB_ETHERFI_WEETH                = '\x04c0599ae5a44757c0af6f9ec3b93da8976c150a'
AVAX_ETHERFI_WEETH               = '\xa3d68b74bf0528fdd07263c60d6488749044914b'
ARB_ETHERFI_WEETH                = '\x35751007a407ca6feffe80b3cb397736d2cf4dbe'
ARB_ETHERFI_ETHFI                = '\x7189fb5b6504bbff6a852b13b7b82a3c118fdc27'
OP_ETHERFI_WEETH                 = '\x5a7facb970d094b6c7ff1df0ea68d99e6e73cbff'
OP_ETHERFI_L2_SYNC_POOL          = '\xc9475e18e2c5c26ea6adcd55fabe07920bea887e'
OP_ETHERFI_RATE_PROVIDER         = '\xaae0d7d8147c9f2c39a0b19974f8e684fa2bba6f'
OP_ETHERFI_ETHFI                 = '\xe0080d2f853ecddbd81a643dc10da075df26fd3f'
ROBIN_ETHERFI_WEETH              = '\xa3d68b74bf0528fdd07263c60d6488749044914b'
ARC_ETHERFI_WEETH                = '\xa3d68b74bf0528fdd07263c60d6488749044914b'
L2_ETHERFI_TIMELOCK              = '\x851dd540f4d2ec78120de0a0cc87b21ede5df5c6'
```

---

## 9. Verification & sources

How the constants were verified (2026-10-30):
- **Topic0 / selectors:** computed locally as `keccak256(signature)` from verified implementation ABIs (Optimism explorer, Sourcify for Base, Routescan for Avalanche, Blockscout for Ethereum). The three OFT impls give identical event sets. Live check: Optimism weETH (`Transfer`, `OFTSent`), OP sync pool (`Deposit` 137, `DepositWithReferral` 9, `Sync` 4), Base weETH (`OFTReceived` 7, `OFTSent` 3 in 30,000 blocks), Ethereum adapter (`OFTReceived` 121, `OFTSent` 29), L1SyncPool (`InsufficientDeposit` 137). No unknown topic0 on these emitters.
- **Addresses:** official Deployed Contracts list + `registry/chains.json` + `utils/L2Constants.sol`, existence-checked with `eth_getCode` on all nine chains. Impl/admin/beacon slots read with `eth_getStorageAt`. `name()`, `symbol()`, `totalSupply()`, `owner()`, `endpoint()`, `token()` read with `eth_call`. Peers read with `peers(eid)` on both Ethereum adapters. Arbitrum wiring read with `l1Address()` / `l2Gateway()`.
- **Chain coverage:** Polygon PoS: no weETH/ETHFI literal has code and no Ethereum peer exists. Robinhood Chain and Arc: only the weETH OFT (plus the L2 Timelock and ProxyAdmin).

Authoritative sources:
- [etherfi-protocol/weETH-cross-chain](https://github.com/etherfi-protocol/weETH-cross-chain) — OFT, native minting, registry.
- [ether.fi Deployed Contracts](https://etherfi.gitbook.io/etherfi/developers/contracts-and-integrations/deployed-contracts)
- Explorers: [Etherscan](https://etherscan.io) · [Basescan](https://basescan.org) · [BscScan](https://bscscan.com) · [Snowtrace](https://snowtrace.io) · [Arbiscan](https://arbiscan.io) · [Optimism explorer](https://explorer.optimism.io)
