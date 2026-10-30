# Circle FiatToken (USDC, EURC, cirBTC) — Topics, Selectors, Addresses (Ethereum, Base, Avalanche, Arbitrum, Optimism, Polygon PoS, Robinhood Chain, Arc; NOT BNB)

**Status:** verified on 2026-10-30 against live RPC on all nine target chains, Circle's USDC, EURC and cirBTC address pages, Arc's contract-address page and the canonical `circlefin/stablecoin-evm` repository (release `release-2026-08-12T202509`). Topics and selectors were recomputed as `keccak256(signature)` and found in the deployed implementation bytecode. Addresses were existence-checked with `eth_getCode`; implementations and admins were read from the proxy slots; roles were read with `eth_call`.
**Scope:** the three Circle tokens built on `FiatToken` (the USDC code base): **USDC** (6 dec), **EURC** (6 dec) and **cirBTC** (Circle Wrapped Bitcoin, 8 dec). It covers the token proxy, the implementation, the **MasterMinter** that controls supply, and Arc's **NativeFiatToken** (USDC as the native gas token). Chains: Ethereum (1), Base (8453), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663) and Arc (5042). **BNB Smart Chain (56) has no Circle-issued FiatToken.** Topics and selectors are chain-agnostic; addresses are network-specific. USYC is a different code base: see [usyc.md](usyc.md).

Every token is a legacy unstructured-storage proxy (`FiatTokenProxy`, zeppelinos slots, not EIP-1967) in front of a `FiatTokenV2_2` implementation (`version()` = `"2"`). Supply moves only through `mint` and `burn` by configured minters. Each minter has an allowance. The token's `masterMinter()` is a separate **MasterMinter** contract on every listed chain: its owner names controllers, and each controller manages one minter's allowance. Pause, blacklist and rescue are separate single-address roles. Each token and each chain has its own address and its own role holders.

---

## 0. Contract families & versions

| Component | Role | Pattern | Where |
|-----------|------|---------|-------|
| **FiatTokenProxy** | The token address. Holds balances. Delegates to the implementation. | Legacy zos `AdminUpgradeabilityProxy` (impl slot `0x7050c9e0…f8c3`, admin slot `0x10d6a54a…390b`) | every token, every chain |
| **FiatTokenV2_2** | Token logic: ERC-20, EIP-2612, EIP-3009, mint/burn, pause, blacklist, rescue. | implementation | per chain (often shared by USDC, EURC and cirBTC on one chain) |
| **NativeFiatTokenV2_2** | Arc USDC logic. Balances live in Arc's native coin through precompiles `0x1800…0000` (NativeCoinAuthority) and `0x1800…0001` (NativeCoinControl). | implementation | Arc USDC only |
| **MasterMinter** | `masterMinter()` of each token. Owner → controllers → one minter each; sets and changes minter allowances. | immutable (`Controller` + `MintController`) | every token, every chain |
| Arc system emitter | Emits an 18-decimal `Transfer` for every native USDC move (EIP-7708). | protocol | Arc (`0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE`) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 FiatToken — value events

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |
| `0xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8` | `Mint(address indexed minter, address indexed to, uint256 amount)` |
| `0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5` | `Burn(address indexed burner, uint256 amount)` |
| `0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5` | `AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce)` (EIP-3009) |
| `0x1cdd46ff242716cdaa72d159d339a485b3438398348d68f09d7c8c0a59353d81` | `AuthorizationCanceled(address indexed authorizer, bytes32 indexed nonce)` |

### 1.2 FiatToken — supply control and roles

| topic0 | Event |
|--------|-------|
| `0x46980fca912ef9bcdbd36877427b6b90e860769f604e89c0e67720cece530d20` | `MinterConfigured(address indexed minter, uint256 minterAllowedAmount)` |
| `0xe94479a9f7e1952cc78f2d6baab678adc1b772d936c6583def489e524cb66692` | `MinterRemoved(address indexed oldMinter)` |
| `0xdb66dfa9c6b8f5226fe9aac7e51897ae8ee94ac31dc70bb6c9900b2574b707e6` | `MasterMinterChanged(address indexed newMasterMinter)` |
| `0x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625` | `Pause()` |
| `0x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33` | `Unpause()` |
| `0xb80482a293ca2e013eda8683c9bd7fc8347cfdaeea5ede58cba46df502c2a604` | `PauserChanged(address indexed newAddress)` |
| `0xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855` | `Blacklisted(address indexed _account)` |
| `0x117e3210bb9aa7d9baff172026820255c6f6c30ba8999d1c2fd88e2848137c4e` | `UnBlacklisted(address indexed _account)` |
| `0xc67398012c111ce95ecb7429b933096c977380ee6c421175a71a4a4c6c88c06e` | `BlacklisterChanged(address indexed newBlacklister)` |
| `0xe475e580d85111348e40d8ca33cfdd74c30fe1655c2d8537a13abc10065ffa5a` | `RescuerChanged(address indexed newRescuer)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address previousOwner, address newOwner)` — **not indexed** in FiatToken |

### 1.3 FiatTokenProxy — upgrade events (emitted by the token address)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address implementation)` — **not indexed**: the new implementation is in `data`, not topic1 |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

### 1.4 MasterMinter (emitter = the token's `masterMinter()`)

| topic0 | Event |
|--------|-------|
| `0xa56687ff5096e83f6e2c673cda0b677f56bbfcdf5fe0555d5830c407ede193cb` | `ControllerConfigured(address indexed _controller, address indexed _worker)` |
| `0x33d83959be2573f5453b12eb9d43b3499bc57d96bd2f067ba44803c859e81113` | `ControllerRemoved(address indexed _controller)` |
| `0x9992ea32e96992be98be5c833cd5b9fd77314819d2146b6f06ab9cfef957af12` | `MinterManagerSet(address indexed _oldMinterManager, address indexed _newMinterManager)` |
| `0x5b0b60a4f757b33d9dcb8bd021b6aa371bb2e6f134086797aefcd8c0afab538c` | `MinterConfigured(address indexed _msgSender, address indexed _minter, uint256 _allowance)` |
| `0x4b5ef9a786cf64a7d82ebcf2d5132667edc9faef4ac36260d9a9e52c526b6232` | `MinterRemoved(address indexed _msgSender, address indexed _minter)` |
| `0x3703d23abba1e61f32acc0682fc062ea5c710672c7d100af5ecd08485e983ad0` | `MinterAllowanceIncremented(address indexed _msgSender, address indexed _minter, uint256 _increment, uint256 _newAllowance)` |
| `0x3cc75d3bf58b0100659088c03539964108d5d06342e1bd8085ee43ad8ff6f69a` | `MinterAllowanceDecremented(address indexed msgSender, address indexed minter, uint256 decrement, uint256 newAllowance)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address previousOwner, address newOwner)` |

`MinterConfigured` and `MinterRemoved` exist on both the token and the MasterMinter with **different** signatures, so the topic0 values differ. Filter by emitter anyway.

### 1.5 Arc — native USDC events

| Emitter | topic0 | Event | Decimals |
|---------|--------|-------|----------|
| `0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE` (system) | `0xddf252ad…b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — every native USDC move, mint and burn | 18 |
| `0x3600000000000000000000000000000000000000` (NativeFiatToken) | `0xddf252ad…b3ef` | `Transfer` for ERC-20 interface calls only; plus the §1.1–§1.2 events | 6 |
| `0x3600…0000` (per Arc docs) | `0x917c251bb231c4b997a420bebe47edad5c20e70715da16c38e9b2e172e44ab92` / `0xbc3fe0fc667d12a7a22748747f024a7d971127ffc48f6622675d3e97a2591a51` | `Blocklisted(address indexed account)` / `UnBlocklisted(address indexed account)` — named in Arc's indexing guide, **not** in the implementation bytecode | — |

The Arc implementation `0xc6ad…3ca6` contains `Blacklisted`/`UnBlacklisted` (§1.2), not `Blocklisted`/`UnBlocklisted`. Its `blacklist` calls `NativeCoinControl.blocklist(address)` (`0xe5c7160b`) on `0x1800…0001`. Watch both topic pairs on Arc until a live log shows which one fires.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors below are in the Ethereum implementation `0x4350…02dd` and the Arc USDC implementation `0xc6ad…3ca6` (PUSH4 scan).

### 2.1 FiatToken — value and supply

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` | `transfer(address,uint256)` / `transferFrom(address,address,uint256)` / `approve(address,uint256)` | ERC-20. |
| `0x40c10f19` | `mint(address,uint256)` | Minter only, within `minterAllowance`. Emits `Mint` + `Transfer(0x0 → to)`. |
| `0x42966c68` | `burn(uint256)` | Minter burns its own balance. Emits `Burn` + `Transfer(minter → 0x0)`. |
| `0xe3ee160e` / `0xcf092995` | `transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)` / `(…,bytes32,bytes)` | EIP-3009; emits `AuthorizationUsed`. |
| `0xef55bec6` / `0x88b7ab63` | `receiveWithAuthorization(…,uint8,bytes32,bytes32)` / `(…,bytes)` | EIP-3009, payee must call. |
| `0x5a049a70` / `0xb7b72899` | `cancelAuthorization(address,bytes32,uint8,bytes32,bytes32)` / `(address,bytes32,bytes)` | Emits `AuthorizationCanceled`. |
| `0xd505accf` / `0x9fd5a6cf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` / `permit(address,address,uint256,uint256,bytes)` | EIP-2612 (the `bytes` form supports ERC-1271 wallets). |
| `0x39509351` / `0xa457c2d7` | `increaseAllowance(address,uint256)` / `decreaseAllowance(address,uint256)` | |

### 2.2 FiatToken — admin

| Selector | Signature | Caller |
|----------|-----------|--------|
| `0x4e44d956` | `configureMinter(address,uint256)` | masterMinter → `MinterConfigured` |
| `0x3092afd5` | `removeMinter(address)` | masterMinter → `MinterRemoved` |
| `0xaa20e1e4` | `updateMasterMinter(address)` | owner → `MasterMinterChanged` |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | pauser |
| `0x554bab3c` | `updatePauser(address)` | owner |
| `0xf9f92be4` / `0x1a895266` | `blacklist(address)` / `unBlacklist(address)` | blacklister |
| `0xad38bf22` | `updateBlacklister(address)` | owner |
| `0xb2118a8d` | `rescueERC20(address,address,uint256)` | rescuer |
| `0x2ab60045` | `updateRescuer(address)` | owner |
| `0xf2fde38b` | `transferOwnership(address)` | owner |

### 2.3 FiatToken — views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x35d99f35` / `0x9fd0506d` / `0xbd102430` / `0x38a63183` / `0x8da5cb5b` | `masterMinter()` / `pauser()` / `blacklister()` / `rescuer()` / `owner()` | Role holders. |
| `0xaa271e1a` / `0x8a6db9c3` | `isMinter(address)` / `minterAllowance(address)` | |
| `0xfe575a87` / `0x5c975abb` | `isBlacklisted(address)` / `paused()` | |
| `0x18160ddd` / `0x70a08231` / `0x313ce567` | `totalSupply()` / `balanceOf(address)` / `decimals()` | |
| `0xe5a6b10f` / `0x54fd4d50` | `currency()` / `version()` | `"USD"`, `"EUR"`, …; `"2"`. |
| `0xe94a0102` | `authorizationState(address,bytes32)` | EIP-3009 nonce used? |
| `0xccd92d3e` / `0x7fd09916` / `0xdd0743b3` | `DECIMALS_SCALING_FACTOR()` / `NATIVE_COIN_AUTHORITY()` / `NATIVE_COIN_CONTROL()` | **Arc USDC only**: `1e12`, `0x1800…0000`, `0x1800…0001`. |

### 2.4 FiatTokenProxy (admin-gated; non-admin callers fall through to the token)

| Selector | Signature |
|----------|-----------|
| `0x3659cfe6` / `0x4f1ef286` | `upgradeTo(address)` / `upgradeToAndCall(address,bytes)` |
| `0x8f283970` | `changeAdmin(address)` |
| `0xf851a440` / `0x5c60da1b` | `admin()` / `implementation()` |

### 2.5 MasterMinter

| Selector | Signature | Caller |
|----------|-----------|--------|
| `0xc4faf7df` / `0xf6a74ed7` | `configureController(address,address)` / `removeController(address)` | owner |
| `0x542fef91` | `setMinterManager(address)` | owner |
| `0xcbf2b8bf` | `configureMinter(uint256)` | controller |
| `0x33db2ad2` / `0x7c6b8ef5` | `incrementMinterAllowance(uint256)` / `decrementMinterAllowance(uint256)` | controller |
| `0xea721569` | `removeMinter()` | controller |
| `0xc011b1c3` / `0x9398608b` | `getWorker(address)` / `getMinterManager()` | views |

---

## 3. Addresses — USDC

All addresses verified with `eth_getCode` on 2026-10-30. Implementation and admin come from the zeppelinos slots. Supply was read with `totalSupply()` on 2026-10-30.

| Chain | Token | Proxy size | Implementation | Proxy admin | MasterMinter | Supply |
|-------|-------|-----------:|----------------|-------------|--------------|-------:|
| Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 2,186 B | `0x43506849d7c04f9138d1a2050bbf3a0c054402dd` | `0x807a96288a1a408dbc13de2b1d087d10356395d2` | `0xe982615d461dd5cd06575bbea87624fda4e3de17` | 47.65 B |
| Base | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 1,852 B | `0x2ce6311ddae708829bc0784c967b7d77d19fd779` | `0x4fc7850364958d97b4d3f5a08f79db2493f8ca44` | `0x2230393edad0299b7e7b59f20aa856cd1bed52e1` | 4.26 B |
| Avalanche | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | 1,852 B | `0x30dfe0469803bce76f8f62ac24b18d33d3d6ffe6` | `0xf0f918c7c977c41b390f8bc69f294eff414a5cb7` | `0xb7887fed5e2f9dc1a66fbb65f76ba3731d82341a` | 347.6 M |
| Arbitrum | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 1,852 B | `0x86e721b43d4ecfa71119dd38c0f938a75fdb57b3` | `0x2e0a67588cfbcad40f9e4dd76052436190a77a68` | `0x8aff09e2259cacbf4fc4e3e53f3bf799efeeab36` | 2.47 B |
| Optimism | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 1,852 B | `0xded3b9a8dbedc2f9cb725b55d0e686a81e6d06dc` | `0xbb8a939e2b1923d248ac4c2f6aed0a4d71cb18a3` | `0x70429f78c2d7d1de6f89be421bce64ba876c325b` | 146.1 M |
| Polygon PoS | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 1,852 B | `0x235ae97b28466db30469b89a9fe4cff0659f82cb` | `0x9238e612387ebba4d4fa0d76dbfba99b453417b3` | `0x067b07ed153f2d4640638f7d2945fbe4ed1bf1ac` | 591.1 M |
| Robinhood Chain | `0x3884564ba51b349e7661c7e28ad947dee327fedf` | 1,798 B | `0x7698064ed94c67574377a5bdc9b327d28e04b5eb` | `0xbfbcbeab745ff7bcdaa96fff273d7b681f5373f4` | `0xe7d5614a708e778a5576f3bde2f701d8463676a8` | 2.62 |
| Arc | `0x3600000000000000000000000000000000000000` | 1,798 B | `0xc6ad664ac6679f4ce74e10e91449c93ec1ae3ca6` (NativeFiatTokenV2_2) | `0x9005e53e3ee2f27999f15e7a52c58f804fc716e0` | `0x5a6e6899ad7387ee1aae23041e3eb29ba11140e3` | 1.16 B |

USDC role holders (`owner()` / `pauser()` / `blacklister()`; `rescuer()` = `0x0` on every chain):

| Chain | Owner | Pauser | Blacklister |
|-------|-------|--------|-------------|
| Ethereum | `0xfcb19e6a322b27c06842a71e8c725399f049ae3a` | `0x4914f61d25e5c567143774b76edbf4d5109a8566` | `0x0a06be16275b95a7d2567fbdae118b36c7da78f9` |
| Base | `0x3abd6f64a422225e61e435bae41db12096106df7` | `0xd3571b3bc51cecff49194ad67afffc648d5e07b4` | `0x1f2e3a640175d20ac31ed523b6733b977173e277` |
| Avalanche | `0x4b7c0fed7e7bf8ecdd731fcbda18da25d060508e` | `0x303f2f7d963d13c12ba3a03fdadbb88277b106dd` | `0x00fec99ef111911f4c84e8a3c0bba93f3891d572` |
| Arbitrum | `0xc7a599037fda4ff8029df9a042af6053d061ebc9` | `0x36e3b4db327d9e66f5ae5a0200dcdbef0d2e240b` | `0xac5b4946a8c29eafb42e1742b3ab82e6d5771329` |
| Optimism | `0xb04ffa9bdaef530a837f73198ae9f94064c4441f` | `0xb8015408bcba72bcbb34775c81361fb496051c9b` | `0x551e855b7355c98534175879a300972856c04d7c` |
| Polygon PoS | `0xaee29e350dbb28ce77d0595d898be658626d2bcc` | `0xa2fb1d6bc5b7aeec5e7ef7fca16d60880c5c8ae1` | `0xe99cf1d0418302535936f96ea6625c71bf1695b6` |
| Robinhood Chain | `0xe99cc033fc15f4041390bf604dc796c2ecd47b49` | `0x506259b9cccc4141b14b18f4e56e655012e4a5b9` | `0x916c55cd3c9a733800b035fc9160c479f08b397e` |
| Arc | `0xf5a5658b55983e2aa037cac7a8431b510e8a97f4` | `0x51fa31e029abf0ce307bca9ee6bf48aed6345212` | `0x2a2b7ff330f15f9a8c52af5fec27d775f5138467` |

Robinhood Chain USDC is not on Circle's USDC address page (fetched 2026-10-30). It is the local token of the CCTP v2 mint route there ([../cctp/v2.md](../cctp/v2.md) §4.2).

## 4. Addresses — EURC

| Chain | Token | Proxy size | Implementation | Proxy admin | MasterMinter | Supply |
|-------|-------|-----------:|----------------|-------------|--------------|-------:|
| Ethereum | `0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c` | 1,852 B | `0x43506849d7c04f9138d1a2050bbf3a0c054402dd` | `0x9ed85723c5c55b746eb2c4b7e2a359b2091b8fe7` | `0x02398771fd1db790ef2b656ca3bcb3075f27a72c` | 318.7 M |
| Base | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` | 1,798 B | `0x2ce6311ddae708829bc0784c967b7d77d19fd779` | `0x4fa3c7461ba47ff34d4033ebaa30525c939991e1` | `0x114b64a8bf7bf0ab2a8a64a3e348307bd568726e` | 49.8 M |
| Avalanche | `0xC891EB4cbdEFf6e073e859e987815Ed1505c2ACD` | 1,852 B | `0x30dfe0469803bce76f8f62ac24b18d33d3d6ffe6` | `0x625c3d1e1cd9f515f90c3b472653f28d32765c22` | `0x48f0d284ba4dd0b3a9b72a10b13c94b43f0cadf0` | 3.81 M |
| Arc | `0xbEf5f6d51CB62b58e6A8f77868681825C6fe21c1` | 1,798 B | `0xc6061272419bb754a6c0386d1df81ddb3fe5cf3c` | `0xb6839a2b63a8f832161d636eb666423197f8be97` | `0x75f7e0800bb98ab6a965b0d9cb0ff5c27355bb57` | 7.97 M |

| Chain | Owner | Pauser | Blacklister |
|-------|-------|--------|-------------|
| Ethereum | `0x3101386a38bef8b79e49f12dea12938a30e8af96` | `0x2c576cfc9612541eb827b5c52479f364ddfafeb7` | `0x601c97ed567253bf09a51998d53c5aa73290bd73` |
| Base | `0xc25a042ae1a6350f4236139150ea6eff4f7d9b51` | `0xfa223f7bb88c8df670bb3acdf16fcb3abbc01c50` | `0x8415c913a925586b5169b0322f6ead8f5c9a1ead` |
| Avalanche | `0x7edf6545cb9b29bf89e911487888bae8b0c58e0f` | `0x133db2e59ddb0c153326a75910b6422a9a3c6575` | `0x3a1ea44b838a771fed2f81137d772c47a64f5d40` |
| Arc | `0x1b127715bb61d1561227748cabeaef51a745f371` | `0xea2f020633b235f14aaa24930238cc211f874e0b` | `0x24584e31ada775628f72dfea5829122cf65a5c01` |

EURC is **not** on BNB, Arbitrum, Optimism, Polygon PoS or Robinhood Chain (Circle's EURC page lists none of them; the four EURC literals return `0x` on every other target chain).

## 5. Addresses — cirBTC

| Chain | Token | Proxy size | Implementation | Proxy admin | MasterMinter | Supply |
|-------|-------|-----------:|----------------|-------------|--------------|-------:|
| Ethereum | `0x72DFB2E44f59C5AD2bAFE84314E5b99a7cd5075E` | 1,798 B | `0x43506849d7c04f9138d1a2050bbf3a0c054402dd` | `0xc9cee9efa5180597bb850a642aa75e5ec3b5a9bd` | `0xc0cc159c07a99eecc35c36f25fe7c1aeeb3587a2` | 888.20 BTC |
| Arc | `0x171A4217b86A807A64eB94757Db6849fb4bDbAA0` | 1,798 B | `0xc6061272419bb754a6c0386d1df81ddb3fe5cf3c` | `0xea93790965853bc7a1b898b524f73ea40c25acc2` | `0x081a1d99cc35957b406783903bb175e0e15e7b2d` | 5,292.78 BTC |

| Chain | Owner | Pauser | Blacklister |
|-------|-------|--------|-------------|
| Ethereum | `0xd50154994eac780c571ff5f7cec0ef2e60085182` | `0xabde92e0efe04a0c1469cd21bf400cb1969fa222` | `0xb5be9afa2ff55b8f9ae3e223b2f18ab6b84e1d79` |
| Arc | `0xbc22a4c5f2c1cdb50e2f55dbf9b5f73417d2e6cf` | `0x27d80d2cf432d35ee2eb29c39c44e1df7b8e3bab` | `0xf9c8a748b5192c4b10c446785f2b707b98c9ea79` |

cirBTC: `name()` = `Circle Wrapped Bitcoin`, 8 decimals. Not on the other seven target chains.

## 6. MasterMinter owners

| Token / chain | MasterMinter | Owner |
|---------------|--------------|-------|
| USDC Ethereum | `0xe982615d461dd5cd06575bbea87624fda4e3de17` (7,667 B) | `0xc1d9fe41d19dd52cb3ae5d1d3b0030b5d498c704` |
| USDC Base | `0x2230393edad0299b7e7b59f20aa856cd1bed52e1` | `0xb5bff84d169a72e76e94ec950da51bac90b60284` |
| USDC Avalanche | `0xb7887fed5e2f9dc1a66fbb65f76ba3731d82341a` | `0xb124608cb75e271de85a48ea15b86d6bdcb8145b` |
| USDC Arbitrum | `0x8aff09e2259cacbf4fc4e3e53f3bf799efeeab36` | `0xedc4ed529b990dd4ffb9ed47b6c3e385a9dcdd0a` |
| USDC Optimism | `0x70429f78c2d7d1de6f89be421bce64ba876c325b` | `0x06e542379c6acdbc1b6f9b635a742a9c8129a4e7` |
| USDC Polygon PoS | `0x067b07ed153f2d4640638f7d2945fbe4ed1bf1ac` | `0x05be21635f74d213d7941ca535c748952ee3637a` |
| USDC Robinhood Chain | `0xe7d5614a708e778a5576f3bde2f701d8463676a8` | `0x13d60b468a41235ff07dc124a08c2ece75254888` |
| USDC Arc | `0x5a6e6899ad7387ee1aae23041e3eb29ba11140e3` | `0xa9085994112d509134776d93b6b214672aab4244` |
| EURC Ethereum | `0x02398771fd1db790ef2b656ca3bcb3075f27a72c` | `0xa1a083189c5425af0bc59a58b2f1649d5236871b` |
| EURC Base | `0x114b64a8bf7bf0ab2a8a64a3e348307bd568726e` | `0xd8dda6b953c16f75a46309898d1ce154f58c898d` |
| EURC Avalanche | `0x48f0d284ba4dd0b3a9b72a10b13c94b43f0cadf0` | `0xfeb51c930d6e14138aae5d586f85f4ebd6c1aea8` |
| EURC Arc | `0x75f7e0800bb98ab6a965b0d9cb0ff5c27355bb57` | `0xb7850efbca3594e50977bd11a05833f18095e021` |
| cirBTC Ethereum | `0xc0cc159c07a99eecc35c36f25fe7c1aeeb3587a2` | `0x51834d9b4b25c470aea8d54f800a18db2da42256` |
| cirBTC Arc | `0x081a1d99cc35957b406783903bb175e0e15e7b2d` | `0xfa7b496f55f06f47d84adaa25edf560bc9ea4acd` |

`getMinterManager()` on each MasterMinter returns its token (read live). Code size is 5,470 B or 5,346 B, except Ethereum USDC (7,667 B, an older build with the same event set).

## 7. Cross-chain summary

| Chain | ID | USDC | EURC | cirBTC |
|-------|----|------|------|--------|
| Ethereum | 1 | ✅ `0xA0b8…eB48` | ✅ `0x1aBa…C33c` | ✅ `0x72DF…075E` |
| Base | 8453 | ✅ `0x8335…2913` | ✅ `0x60a3…db42` | — |
| BNB Smart Chain | 56 | — (no Circle-issued USDC) | — | — |
| Avalanche C-Chain | 43114 | ✅ `0xB97E…8a6E` | ✅ `0xC891…2ACD` | — |
| Arbitrum One | 42161 | ✅ `0xaf88…5831` | — | — |
| Optimism | 10 | ✅ `0x0b2C…Ff85` | — | — |
| Polygon PoS | 137 | ✅ `0x3c49…3359` | — | — |
| Robinhood Chain | 4663 | ✅ `0x3884…fedf` (not on Circle's list) | — | — |
| Arc | 5042 | ✅ `0x3600…0000` (native) | ✅ `0xbEf5…21c1` | ✅ `0x171A…bAA0` |

**Not Circle-issued, out of scope** (same "USD Coin" name, other issuers or bridges; read live): BNB Binance-Peg `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d`; Polygon bridged `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` ("USD Coin (PoS)"); Arbitrum bridged `0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8` ("USD Coin (Arb1)"); Optimism bridged `0x7F5c764cBc14f9669B88837ca1490cCa17c31607`; Avalanche bridged `0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664` (`USDC.e`). Do not treat their admin events as Circle events.

## 8. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **FiatTokenProxy** (every token) | Legacy zos `AdminUpgradeabilityProxy` | EIP-1967 impl and admin slots are `0x0`. Read impl at `0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3` and admin at `0x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b`. Runtime 1,798 B, 1,852 B or 2,186 B (Ethereum USDC). | Proxy admin (§3–§5). `upgradeTo` / `upgradeToAndCall` → `Upgraded(address)` with the impl in `data`. |
| **MasterMinter** | immutable | EIP-1967 and zos slots `0x0`. | Owner can only re-wire controllers, not code. |

Shared implementations: Ethereum USDC, EURC and cirBTC all use `0x4350…02dd`; Base USDC and EURC use `0x2ce6…d779`; Avalanche USDC and EURC use `0x30df…ffe6`; Arc EURC and cirBTC use `0xc606…cf3c`. An upgrade of one token does not change the others: each proxy keeps its own impl slot.

Arc history (zos impl slot read at sampled blocks and bisected): USDC has `0xc6ad…3ca6` from genesis; EURC got `0xc606…cf3c` at block 542,237 (2026-05-18) and cirBTC at block 560,194 (2026-05-18). No later change to 2026-10-30. The older-chain histories were not enumerated; read the slot for the current value.

## 9. Detection invariants & gotchas

1. **Supply = `Mint` and `Burn` only.** `Mint.minter` (topic1) names the minter contract: for USDC, the CCTP TokenMinter, the Gateway Minter and Circle treasury minters. Circle's mints and burns for issuance and redemption are the largest single-block supply changes. Measured: Ethereum USDC had 112 `Mint` and 76 `Burn` logs in 100 blocks; Arc USDC 22 `Mint` and 30 `Burn` in 2,000 blocks.
2. **`MinterConfigured` on the token is the allowance signal.** A sudden large allowance, or a new minter (`MinterConfigured` for an address that was not a minter), is a top-severity event. On the MasterMinter, watch `ControllerConfigured`, `MinterConfigured` and `MinterAllowanceIncremented`.
3. **`Upgraded` on FiatTokenProxy is not indexed.** Read the new implementation from `data[12:32]`. An `Upgraded` filter on topic1 finds nothing.
4. **`OwnershipTransferred` is not indexed in FiatToken.** The same topic0 has indexed fields in most other contracts. Decode by emitter.
5. **Blacklist freezes funds.** `Blacklisted(account)` stops transfers to and from the account. Track the set from `Blacklisted` / `UnBlacklisted` per token per chain.
6. **Arc USDC has two `Transfer` streams.** The system emitter `0xffff…fffe` logs every native move at 18 decimals. The token `0x3600…0000` logs ERC-20 interface calls at 6 decimals. One ERC-20 `transfer()` gives one log from each. Pick one emitter so you do not count twice. Gas fees emit no `Transfer`.
7. **Arc USDC `totalSupply()` reads the native coin.** It is the native supply (scaled by `1e12` to 6 decimals), not an ERC-20 counter.
8. **Arc blocklist naming conflict.** Arc's docs say the USDC contract emits `Blocklisted` / `UnBlocklisted`. The implementation code has `Blacklisted` / `UnBlacklisted` and calls the NativeCoinControl precompile. Monitor all four topics on `0x3600…0000` and on `0x1800…0001`.
9. **Same code, many addresses.** USDC, EURC and cirBTC share topic0 and selectors. The token is the emitter address only. Key every rule on `(chainId, address)`.
10. **Bridged look-alikes.** The non-Circle USDC tokens in §7 use the same `Transfer` topic and, in some cases, FiatToken-like admin events. Exclude them by address.
11. **cirBTC is 8 decimals.** Do not apply the 6-decimal USDC scale.
12. **Pause is global per token per chain.** `Pause()` blocks every transfer, mint and burn of that token on that chain.

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== FiatToken topics (chain-agnostic) =====
TOPIC_TRANSFER                  = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL                  = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_MINT                      = '\xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8'
TOPIC_BURN                      = '\xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'
TOPIC_AUTHORIZATION_USED        = '\x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5'
TOPIC_AUTHORIZATION_CANCELED    = '\x1cdd46ff242716cdaa72d159d339a485b3438398348d68f09d7c8c0a59353d81'
TOPIC_MINTER_CONFIGURED         = '\x46980fca912ef9bcdbd36877427b6b90e860769f604e89c0e67720cece530d20'
TOPIC_MINTER_REMOVED            = '\xe94479a9f7e1952cc78f2d6baab678adc1b772d936c6583def489e524cb66692'
TOPIC_MASTER_MINTER_CHANGED     = '\xdb66dfa9c6b8f5226fe9aac7e51897ae8ee94ac31dc70bb6c9900b2574b707e6'
TOPIC_PAUSE                     = '\x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625'
TOPIC_UNPAUSE                   = '\x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33'
TOPIC_PAUSER_CHANGED            = '\xb80482a293ca2e013eda8683c9bd7fc8347cfdaeea5ede58cba46df502c2a604'
TOPIC_BLACKLISTED               = '\xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855'
TOPIC_UNBLACKLISTED             = '\x117e3210bb9aa7d9baff172026820255c6f6c30ba8999d1c2fd88e2848137c4e'
TOPIC_BLACKLISTER_CHANGED       = '\xc67398012c111ce95ecb7429b933096c977380ee6c421175a71a4a4c6c88c06e'
TOPIC_RESCUER_CHANGED           = '\xe475e580d85111348e40d8ca33cfdd74c30fe1655c2d8537a13abc10065ffa5a'
TOPIC_OWNERSHIP_TRANSFERRED     = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_UPGRADED                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED             = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_ARC_BLOCKLISTED           = '\x917c251bb231c4b997a420bebe47edad5c20e70715da16c38e9b2e172e44ab92'
TOPIC_ARC_UNBLOCKLISTED         = '\xbc3fe0fc667d12a7a22748747f024a7d971127ffc48f6622675d3e97a2591a51'
-- ===== MasterMinter topics =====
TOPIC_MM_CONTROLLER_CONFIGURED  = '\xa56687ff5096e83f6e2c673cda0b677f56bbfcdf5fe0555d5830c407ede193cb'
TOPIC_MM_CONTROLLER_REMOVED     = '\x33d83959be2573f5453b12eb9d43b3499bc57d96bd2f067ba44803c859e81113'
TOPIC_MM_MINTER_MANAGER_SET     = '\x9992ea32e96992be98be5c833cd5b9fd77314819d2146b6f06ab9cfef957af12'
TOPIC_MM_MINTER_CONFIGURED      = '\x5b0b60a4f757b33d9dcb8bd021b6aa371bb2e6f134086797aefcd8c0afab538c'
TOPIC_MM_MINTER_REMOVED         = '\x4b5ef9a786cf64a7d82ebcf2d5132667edc9faef4ac36260d9a9e52c526b6232'
TOPIC_MM_ALLOWANCE_INCREMENTED  = '\x3703d23abba1e61f32acc0682fc062ea5c710672c7d100af5ecd08485e983ad0'
TOPIC_MM_ALLOWANCE_DECREMENTED  = '\x3cc75d3bf58b0100659088c03539964108d5d06342e1bd8085ee43ad8ff6f69a'
-- ===== Selectors (chain-agnostic) =====
SEL_MINT                        = '\x40c10f19'
SEL_BURN                        = '\x42966c68'
SEL_CONFIGURE_MINTER            = '\x4e44d956'
SEL_REMOVE_MINTER               = '\x3092afd5'
SEL_UPDATE_MASTER_MINTER        = '\xaa20e1e4'
SEL_PAUSE                       = '\x8456cb59'
SEL_UNPAUSE                     = '\x3f4ba83a'
SEL_UPDATE_PAUSER               = '\x554bab3c'
SEL_BLACKLIST                   = '\xf9f92be4'
SEL_UNBLACKLIST                 = '\x1a895266'
SEL_UPDATE_BLACKLISTER          = '\xad38bf22'
SEL_RESCUE_ERC20                = '\xb2118a8d'
SEL_UPDATE_RESCUER              = '\x2ab60045'
SEL_TRANSFER_OWNERSHIP          = '\xf2fde38b'
SEL_TRANSFER_WITH_AUTH_VRS      = '\xe3ee160e'
SEL_TRANSFER_WITH_AUTH_BYTES    = '\xcf092995'
SEL_RECEIVE_WITH_AUTH_VRS       = '\xef55bec6'
SEL_RECEIVE_WITH_AUTH_BYTES     = '\x88b7ab63'
SEL_PROXY_UPGRADE_TO            = '\x3659cfe6'
SEL_PROXY_UPGRADE_TO_AND_CALL   = '\x4f1ef286'
SEL_PROXY_CHANGE_ADMIN          = '\x8f283970'
SEL_MM_CONFIGURE_CONTROLLER     = '\xc4faf7df'
SEL_MM_REMOVE_CONTROLLER        = '\xf6a74ed7'
SEL_MM_SET_MINTER_MANAGER       = '\x542fef91'
SEL_MM_CONFIGURE_MINTER         = '\xcbf2b8bf'
SEL_MM_INCREMENT_ALLOWANCE      = '\x33db2ad2'
SEL_MM_DECREMENT_ALLOWANCE      = '\x7c6b8ef5'
SEL_MM_REMOVE_MINTER            = '\xea721569'
-- ===== USDC (network-specific) =====
ETH_USDC                        = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
BASE_USDC                       = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
AVAX_USDC                       = '\xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e'
ARB_USDC                        = '\xaf88d065e77c8cc2239327c5edb3a432268e5831'
OP_USDC                         = '\x0b2c639c533813f4aa9d7837caf62653d097ff85'
POLY_USDC                       = '\x3c499c542cef5e3811e1192ce70d8cc03d5c3359'
RH_USDC                         = '\x3884564ba51b349e7661c7e28ad947dee327fedf'
ARC_USDC                        = '\x3600000000000000000000000000000000000000'
ARC_NATIVE_USDC_EMITTER         = '\xfffffffffffffffffffffffffffffffffffffffe'
ARC_NATIVE_COIN_AUTHORITY       = '\x1800000000000000000000000000000000000000'
ARC_NATIVE_COIN_CONTROL         = '\x1800000000000000000000000000000000000001'
-- ===== EURC =====
ETH_EURC                        = '\x1abaea1f7c830bd89acc67ec4af516284b1bc33c'
BASE_EURC                       = '\x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42'
AVAX_EURC                       = '\xc891eb4cbdeff6e073e859e987815ed1505c2acd'
ARC_EURC                        = '\xbef5f6d51cb62b58e6a8f77868681825c6fe21c1'
-- ===== cirBTC =====
ETH_CIRBTC                      = '\x72dfb2e44f59c5ad2bafe84314e5b99a7cd5075e'
ARC_CIRBTC                      = '\x171a4217b86a807a64eb94757db6849fb4bdbaa0'
-- ===== MasterMinters =====
ETH_USDC_MASTER_MINTER          = '\xe982615d461dd5cd06575bbea87624fda4e3de17'
BASE_USDC_MASTER_MINTER         = '\x2230393edad0299b7e7b59f20aa856cd1bed52e1'
AVAX_USDC_MASTER_MINTER         = '\xb7887fed5e2f9dc1a66fbb65f76ba3731d82341a'
ARB_USDC_MASTER_MINTER          = '\x8aff09e2259cacbf4fc4e3e53f3bf799efeeab36'
OP_USDC_MASTER_MINTER           = '\x70429f78c2d7d1de6f89be421bce64ba876c325b'
POLY_USDC_MASTER_MINTER         = '\x067b07ed153f2d4640638f7d2945fbe4ed1bf1ac'
RH_USDC_MASTER_MINTER           = '\xe7d5614a708e778a5576f3bde2f701d8463676a8'
ARC_USDC_MASTER_MINTER          = '\x5a6e6899ad7387ee1aae23041e3eb29ba11140e3'
ETH_EURC_MASTER_MINTER          = '\x02398771fd1db790ef2b656ca3bcb3075f27a72c'
BASE_EURC_MASTER_MINTER         = '\x114b64a8bf7bf0ab2a8a64a3e348307bd568726e'
AVAX_EURC_MASTER_MINTER         = '\x48f0d284ba4dd0b3a9b72a10b13c94b43f0cadf0'
ARC_EURC_MASTER_MINTER          = '\x75f7e0800bb98ab6a965b0d9cb0ff5c27355bb57'
ETH_CIRBTC_MASTER_MINTER        = '\xc0cc159c07a99eecc35c36f25fe7c1aeeb3587a2'
ARC_CIRBTC_MASTER_MINTER        = '\x081a1d99cc35957b406783903bb175e0e15e7b2d'
```

## 11. Verification & sources

How constants were verified (2026-10-30):

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the verified ABIs of `FiatTokenV2_2` (Ethereum `0x4350…02dd`) and `NativeFiatTokenV2_2` (Arc `0xc6ad…3ca6`), and from `circlefin/stablecoin-evm` (`contracts/upgradeability/*.sol`, `contracts/minting/Controller.sol`, `contracts/minting/MintController.sol`, `contracts/v2/NativeFiatTokenV2_2.sol`). Every FiatToken topic and selector in §1–§2 was found in both implementations; the proxy topics and selectors in the Ethereum and Arc proxies; the MasterMinter topics and selectors in the Ethereum USDC and Arc USDC MasterMinters. `Blocklisted` / `UnBlocklisted` come from Arc's indexing guide and are **not** in the implementation.
- **Live logs:** `Transfer`, `Approval`, `Mint` (3 topics), `Burn` (2 topics) and `AuthorizationUsed` seen on Ethereum USDC (blocks 26,306,196–26,306,296), Ethereum EURC and cirBTC (9,000 blocks), Base EURC (5,000 blocks), and Arc USDC, EURC and cirBTC (2,000 and 40,000 blocks). Robinhood Chain USDC had no log in the last 50,000 blocks.
- **Addresses:** from Circle's USDC, EURC and cirBTC address pages and Arc's contract-address page. `eth_getCode` for every token literal on all nine chains: each literal has code only on its own chain. Implementations and admins from the zeppelinos slots; EIP-1967 slots are `0x0`. Roles, supply and `getMinterManager()` read with `eth_call`.

Authoritative sources:
- [circlefin/stablecoin-evm](https://github.com/circlefin/stablecoin-evm) — FiatToken, proxy, MasterMinter and NativeFiatToken sources
- [USDC contract addresses](https://developers.circle.com/stablecoins/usdc-contract-addresses) · [EURC contract addresses](https://developers.circle.com/stablecoins/eurc-contract-addresses) · [cirBTC contract addresses](https://developers.circle.com/assets/cirbtc-contract-addresses)
- [Arc contract addresses](https://docs.arc.io/arc/references/contract-addresses) · [Arc USDC system events](https://docs.arc.io/arc/references/usdc-system-events) · [Arc indexing guide](https://docs.arc.io/integrate/infrastructure/indexing-events)
- Explorers — [Etherscan USDC](https://etherscan.io/token/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48) · [Basescan USDC](https://basescan.org/token/0x833589fcd6edb6e08f4c7c32d4f71b54bda02913) · [Arc explorer](https://explorer.arc.io/address/0x3600000000000000000000000000000000000000)
