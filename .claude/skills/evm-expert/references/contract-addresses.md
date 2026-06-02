# Contract Addresses Reference

Production contract addresses for major protocols across EVM chains. All addresses are checksummed. Verify on-chain before use with `cast code <address>`.

---

## Universal Addresses (Same on ALL EVM Chains)

| Contract | Address | Purpose |
|----------|---------|---------|
| Multicall3 | `0xcA11bde05977b3631167028862bE2a173976CA11` | Batch read calls |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | Gasless token approvals |
| EntryPoint v0.7 | `0x0000000071727De22E5E9d8BAf0edAc6f37da032` | ERC-4337 AA |
| Safe Singleton v1.4.1 | `0x41675C099F32341bf84BFc5382aF534df5C7461a` | Safe multisig impl |
| Safe ProxyFactory | `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` | Safe deployment |
| CREATE2 Deployer | `0x4e59b44847b379578588920cA78FbF26c0B4956C` | Deterministic deployment |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fE728c` | Cross-chain messaging |
| Wormhole Relayer | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | Cross-chain delivery |
| Null Address | `0x0000000000000000000000000000000000000000` | Burn/null |

---

## Ethereum Mainnet (Chain ID: 1)

### Stablecoins & Wrapped Tokens
| Token | Address | Decimals |
|-------|---------|----------|
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | 6 |
| USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | 6 |
| DAI | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | 18 |
| WETH | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | 18 |
| WBTC | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | 8 |
| wstETH | `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` | 18 |
| stETH | `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84` | 18 |
| rETH | `0xae78736Cd615f374D3085123A210448E74Fc6393` | 18 |
| cbETH | `0xBe9895146f7AF43049ca1c1AE358B0541Ea49BBa` | 18 |
| USDS | `0xdC035D45d973E3EC169d2276DDab16f1e407384F` | 18 |

### Uniswap
| Contract | Address |
|----------|---------|
| V2 Factory | `0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f` |
| V2 Router02 | `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D` |
| V3 Factory | `0x1F98431c8aD98523631AE4a59f267346ea31F984` |
| SwapRouter02 | `0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45` |
| NonfungiblePositionManager | `0xC36442b4a4522E871399CD717aBDD847Ab11FE88` |
| QuoterV2 | `0x61fFE014bA17989E743c5F6cB21bF9697530B21e` |
| UniversalRouter | `0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD` |
| V4 PoolManager | `0x000000000004444c5dc75cB358380D2e3dE08A90` |

### Aave V3
| Contract | Address |
|----------|---------|
| Pool | `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2` |
| PoolAddressesProvider | `0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e` |
| Oracle | `0x54586bE62E3c3580375aE3723C145253060Ca0C2` |

### Compound V3
| Contract | Address |
|----------|---------|
| Comet USDC | `0xc3d688B66703497DAA19211EEdff47f25384cdc3` |
| COMP Token | `0xc00e94Cb662C3520282E6f5717214004A7f26888` |
| Comet Rewards | `0x1B0e765F6224C21223AeA2af16c1C46E38885a40` |

### Maker / Sky
| Contract | Address |
|----------|---------|
| Vat | `0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B` |
| Jug | `0x19c0976f590D67707E62397C87829d896Dc0f1F1` |
| CDP Manager | `0x5ef30b9986345249bc32d8928B7ee64DE9435E39` |
| DAI | `0x6B175474E89094C44Da98b954EedeAC495271d0F` |
| MKR | `0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2` |
| SKY | `0x56072C95FAA7932F4D8Aa042BE0611d2a2CE73a5` |
| Pot (DSR) | `0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7` |

### Morpho Blue
| Contract | Address |
|----------|---------|
| Morpho (singleton) | `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb` |

### Curve
| Contract | Address |
|----------|---------|
| 3pool | `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7` |
| stETH/ETH | `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` |
| Tricrypto2 | `0xD51a44d3FaE010294C616388b506AcdA1bfAAE46` |
| Router | `0xF0d4c12A5768D806021F80a262B4d39d26C58b8D` |

### Lido
| Contract | Address |
|----------|---------|
| stETH (proxy) | `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84` |
| wstETH | `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` |
| WithdrawalQueue | `0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1` |

### EigenLayer
| Contract | Address |
|----------|---------|
| StrategyManager | `0x858646372CC42E1A627fcE94aa7A7033e7CF075A` |
| stETH Strategy | `0x93c4b944D05dfe6df7645A86cd2206016c51564D` |
| rETH Strategy | `0x1BeE69b7dFFfA4E2d53C2a2Df135C388AD25dCD2` |
| cbETH Strategy | `0x54945180dB7943c0ed0FEE7EdaB2Bd24620256bc` |

### Pendle
| Contract | Address |
|----------|---------|
| Router | `0x888888888889758F76e7103c6CbF23ABbF58F946` |
| RouterStatic | `0x263833d47eA3fA4a30d59B2E6C1A0e682eF1C078` |
| PtOracle | `0x66a1096C6366b2529274dF4f5D8f56DA60a2CacD` |

### Chainlink Feeds
| Pair | Address | Decimals | Heartbeat |
|------|---------|----------|-----------|
| ETH/USD | `0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419` | 8 | 3600s |
| BTC/USD | `0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c` | 8 | 3600s |
| USDC/USD | `0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6` | 8 | 86400s |
| DAI/USD | `0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9` | 8 | 3600s |
| LINK/USD | `0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c` | 8 | 3600s |
| wstETH/ETH | `0x536218f9E9Eb48863970252233c8F271f554C2d0` | 18 | 86400s |

### Oracles
| Contract | Address |
|----------|---------|
| Pyth | `0x4305FB66699C3B2702D4d05CF36551390A4c69C6` |

### ENS
| Contract | Address |
|----------|---------|
| Registry | `0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e` |
| Public Resolver | `0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63` |
| Registrar Controller | `0x253553366Da8546fC250F225fe3d25d0C782303b` |
| Reverse Registrar | `0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb` |

### Cross-Chain
| Contract | Address |
|----------|---------|
| Wormhole Core Bridge | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` |
| Axelar Gateway | `0x4F4495243837681061C4743b74B3eEdf548D56A5` |

---

## Arbitrum One (Chain ID: 42161)

### Tokens
| Token | Address | Decimals |
|-------|---------|----------|
| USDC (native) | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | 6 |
| USDC.e (bridged) | `0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8` | 6 |
| USDT | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | 6 |
| WETH | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` | 18 |
| ARB | `0x912CE59144191C1204E64559FE8253a0e49E6548` | 18 |
| wstETH | `0x5979D7b546E38E9Ab8097BF1A5f63df3b2CdE9F2` | 18 |

### GMX V2
| Contract | Address |
|----------|---------|
| ExchangeRouter | `0x69C527fC77291722b52649E45c838e41be8Bf5d5` |
| Router (approvals) | `0x7452c558d45f8afC8c83dAe62C3f8A5BE19c71f6` |
| Reader | `0x22199a49A999c351eF7927602CFB187ec3cae489` |
| DataStore | `0xFD70de6b91282D8017aA4E741e9Ae325CAb992d8` |

### Chainlink Feeds
| Pair | Address | Heartbeat |
|------|---------|-----------|
| ETH/USD | `0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612` | 86400s |
| Sequencer Uptime | `0xFdB631F5EE196F0ed6FAa767959853A9F217697D` | — |

### Cross-Chain
| Contract | Address |
|----------|---------|
| Axelar Gateway | `0xe432150cce91c13a887f7D836923d5597adD8E31` |
| Pyth | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` |

---

## Base (Chain ID: 8453)

### Tokens
| Token | Address | Decimals |
|-------|---------|----------|
| USDC (native) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 6 |
| USDbC (bridged) | `0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA` | 6 |
| WETH | `0x4200000000000000000000000000000000000006` | 18 |
| cbETH | `0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22` | 18 |

### OP Stack Predeploys (same on all OP Stack chains)
| Contract | Address |
|----------|---------|
| L2CrossDomainMessenger | `0x4200000000000000000000000000000000000007` |
| L2StandardBridge | `0x4200000000000000000000000000000000000010` |
| GasPriceOracle | `0x420000000000000000000000000000000000000F` |
| L1Block | `0x4200000000000000000000000000000000000015` |
| L2ToL1MessagePasser | `0x4200000000000000000000000000000000000016` |

### L1 Contracts (on Ethereum)
| Contract | Address |
|----------|---------|
| OptimismPortal | `0x49048044D57e1C92A77f79988d21Fa8fAF36f97B` |

### Chainlink Feeds
| Pair | Address | Heartbeat |
|------|---------|-----------|
| Sequencer Uptime | `0xBCF85224fc0756B9Fa45aA7892530B47e10b6433` | — |

### Cross-Chain
| Contract | Address |
|----------|---------|
| Axelar Gateway | `0xe432150cce91c13a887f7D836923d5597adD8E31` |
| Pyth | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` |

---

## Optimism (Chain ID: 10)

### Tokens
| Token | Address | Decimals |
|-------|---------|----------|
| USDC (native) | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | 6 |
| USDC.e (bridged) | `0x7F5c764cBc14f9669B88837ca1490cCa17c31607` | 6 |
| USDT | `0x94b008aA00579c1307B0EF2c499aD98a8ce58e58` | 6 |
| WETH | `0x4200000000000000000000000000000000000006` | 18 |
| OP | `0x4200000000000000000000000000000000000042` | 18 |
| wstETH | `0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb` | 18 |

### Chainlink Feeds
| Pair | Address | Heartbeat |
|------|---------|-----------|
| Sequencer Uptime | `0x371EAD81c9102C9BF4874A9075FFFf170F2Ee389` | — |

---

## Polygon PoS (Chain ID: 137)

### Tokens
| Token | Address | Decimals |
|-------|---------|----------|
| USDC (native) | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | 6 |
| USDC.e (bridged) | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` | 6 |
| USDT | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` | 6 |
| WPOL | `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` | 18 |
| WETH | `0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619` | 18 |

### L1 Contracts (on Ethereum)
| Contract | Address |
|----------|---------|
| RootChain | `0x86E4Dc95c7FBdBf52e33D563BbDB00823894C287` |
| RootChainManager | `0xA0c68C638235ee32657e8f720a23ceC1bFc77C77` |
| POL Token | `0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6` |
| MATIC Token | `0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0` |

---

## BNB Smart Chain (Chain ID: 56)

### Tokens
| Token | Address | Decimals |
|-------|---------|----------|
| USDT (BSC) | `0x55d398326f99059fF775485246999027B3197955` | 18 |
| USDC (BSC) | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | 18 |
| WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` | 18 |
| BUSD | `0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56` | 18 |

---

## Token Decimal Gotchas

**NEVER assume 18 decimals.** Common non-18-decimal tokens:

| Token | Decimals | Chains |
|-------|----------|--------|
| USDC | 6 | Ethereum, Arbitrum, Base, Optimism, Polygon |
| USDT | 6 | Ethereum, Arbitrum, Optimism, Polygon |
| USDT (BSC) | **18** | BSC only |
| USDC (BSC) | **18** | BSC only |
| WBTC | 8 | Ethereum |
| GUSD | 2 | Ethereum |

### Native vs Bridged Tokens
- **USDC** (native, Circle-minted) vs **USDC.e** (bridged from Ethereum)
- Different contract addresses, same decimals
- Native USDC is preferred (more liquidity, official support)
- Check `token.symbol()` — some bridged tokens show different symbols

---

## Verification Commands

```bash
# Verify contract has code
cast code 0xAddress --rpc-url $RPC_URL

# Check if proxy — read EIP-1967 implementation slot
cast storage 0xProxy 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc --rpc-url $RPC_URL

# Read token decimals
cast call 0xToken "decimals()" --rpc-url $RPC_URL | cast --to-dec

# Read token symbol
cast call 0xToken "symbol()" --rpc-url $RPC_URL | cast --to-ascii
```
