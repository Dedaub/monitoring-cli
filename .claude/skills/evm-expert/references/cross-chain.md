# Cross-Chain Messaging & Bridging

Reference for cross-chain communication protocols on EVM. Covers LayerZero, Wormhole, Axelar, Hyperlane, and CCIP with integration patterns, security models, and key addresses.

---

## Protocol Comparison

| Feature | LayerZero V2 | Wormhole | Axelar | Chainlink CCIP | Hyperlane |
|---------|-------------|----------|--------|---------------|-----------|
| Security Model | DVN (configurable) | 19 Guardians (13/19) | PoS validators | DON (Chainlink nodes) | ISM (configurable) |
| Chain IDs | Endpoint IDs (eid) | Wormhole chain IDs | String names | Chain selectors | Domain IDs |
| Token Standard | OFT | NTT / Token Bridge | ITS | CCIP tokens | Warp Routes |
| Message Format | bytes | VAA (signed) | GMP payload | Client.EVM2AnyMessage | bytes |
| Gas Payment | LayerZero endpoint | Relayer or manual | AxelarGasService | LINK or native | IGP (Interchain Gas) |

**CRITICAL: None of these protocols use standard EVM chain IDs.** Each has its own identifier system.

---

## LayerZero V2

### Architecture
- **OApp** (Omnichain Application): base contract for cross-chain messaging
- **OFT** (Omnichain Fungible Token): cross-chain ERC-20
- **DVN** (Decentralized Verifier Network): configurable security (choose verifiers)
- **Executor**: handles gas payment on destination chain

### Endpoint IDs (NOT chain IDs)
| Chain | eid |
|-------|-----|
| Ethereum | 30101 |
| Arbitrum | 30110 |
| Optimism | 30111 |
| Base | 30184 |
| Polygon | 30109 |
| Avalanche | 30106 |
| BNB Chain | 30102 |

### EndpointV2 Address (SAME on all EVM chains)
`0x1a44076050125825900e736c501f859c50fE728c`

### Integration Pattern
```solidity
import { OApp, MessagingFee } from "@layerzerolabs/oapp-evm/contracts/oapp/OApp.sol";

contract MyOApp is OApp {
    constructor(address _endpoint, address _owner) OApp(_endpoint, _owner) {}

    // Send message
    function send(uint32 _dstEid, bytes calldata _payload, bytes calldata _options)
        external payable
    {
        _lzSend(_dstEid, _payload, _options, MessagingFee(msg.value, 0), payable(msg.sender));
    }

    // Receive message
    function _lzReceive(Origin calldata, bytes32, bytes calldata _payload, address, bytes calldata)
        internal override
    {
        // Process incoming message
    }
}
```

### Key Patterns
- **Peers are bytes32**: `bytes32(uint256(uint160(addr)))` — left-pad address to 32 bytes
- **2D Nonces**: upper 192 bits = key, lower 64 bits = sequence → enables parallel execution
- **OFT shared decimals**: default 6 → removes dust on cross-chain transfers (avoids rounding issues)
- **DVN configuration**: choose LayerZero + optional secondary (Polyhedra, Google Cloud)
- **Composed messages**: chain multiple cross-chain operations in one flow

---

## Wormhole

### Architecture
- **Guardian Network**: 19 guardians, 13/19 threshold for message attestation
- **VAA** (Verified Action Approval): signed message containing payload
- **NTT** (Native Token Transfers): burn/mint canonical tokens
- **Token Bridge**: lock/wrap legacy bridge (wrapped tokens)
- **Standard Relayer**: automatic delivery with gas payment

### Wormhole Chain IDs (NOT EVM chain IDs)
| Chain | Wormhole ID | EVM Chain ID |
|-------|------------|-------------|
| Ethereum | 2 | 1 |
| BSC | 4 | 56 |
| Polygon | 5 | 137 |
| Avalanche | 6 | 43114 |
| Arbitrum | 23 | 42161 |
| Optimism | 24 | 10 |
| Base | 30 | 8453 |

### Core Bridge Address (Ethereum)
`0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B`

### Standard Relayer (same across chains)
`0x27428DD2d3DD32A4D7f7C497eAaa23130d894911`

### Integration Pattern
```solidity
// Sending
function sendMessage(uint16 targetChain, address targetAddress, bytes memory payload)
    external payable
{
    uint256 cost = wormholeRelayer.quoteEVMDeliveryPrice(targetChain, 0, GAS_LIMIT);
    wormholeRelayer.sendPayloadToEvm{value: cost}(
        targetChain,
        targetAddress,
        payload,
        0,         // receiver value
        GAS_LIMIT
    );
}

// Receiving
function receiveWormholeMessages(
    bytes memory payload,
    bytes[] memory,     // additional VAAs
    bytes32 sourceAddress,
    uint16 sourceChain,
    bytes32 deliveryHash
) public payable override {
    require(msg.sender == address(wormholeRelayer), "Only relayer");
    // Process payload
}
```

### Consistency Levels
| Level | Meaning | Use Case |
|-------|---------|----------|
| 1 | Instant (unconfirmed) | Low-value messages |
| 15 | Finalized | Standard cross-chain |
| 200 | Safe | High-value transfers |

### NTT vs Token Bridge
- **NTT**: Burns on source, mints on destination → canonical token on all chains
- **Token Bridge**: Locks on source, mints wrapped → creates synthetic tokens (WETH.w, USDC.w)
- Prefer NTT for new deployments; Token Bridge is legacy

---

## Axelar

### Architecture
- **GMP** (General Message Passing): arbitrary cross-chain calls
- **ITS** (Interchain Token Service): deploy+manage tokens across chains
- **Gateway**: entry point for cross-chain messages per chain
- **Gas Service**: prepay execution gas on destination

### Chain Names (STRINGS, not IDs)
```
"ethereum", "arbitrum", "optimism", "base", "polygon", "avalanche", "binance"
```

### Gateway Addresses
| Chain | Address |
|-------|---------|
| Ethereum | `0x4F4495243837681061C4743b74B3eEdf548D56A5` |
| Arbitrum | `0xe432150cce91c13a887f7D836923d5597adD8E31` |
| Base | `0xe432150cce91c13a887f7D836923d5597adD8E31` |
| Optimism | `0xe432150cce91c13a887f7D836923d5597adD8E31` |

### Integration Pattern
```solidity
import { AxelarExecutable } from "@axelar-network/axelar-gmp-sdk-solidity/contracts/executable/AxelarExecutable.sol";

contract MyApp is AxelarExecutable {
    constructor(address gateway_) AxelarExecutable(gateway_) {}

    // Send
    function sendMessage(string calldata destChain, string calldata destAddr, bytes calldata payload)
        external payable
    {
        // MUST prepay gas
        gasService.payNativeGasForContractCall{value: msg.value}(
            address(this), destChain, destAddr, payload, msg.sender
        );
        gateway.callContract(destChain, destAddr, payload);
    }

    // Receive
    function _execute(string calldata sourceChain, string calldata sourceAddress, bytes calldata payload)
        internal override
    {
        // Validate source
        require(keccak256(bytes(sourceAddress)) == trustedRemote[sourceChain], "Untrusted");
        // Process
    }
}
```

### ITS (Interchain Token Service)
- Token IDs are deterministic: `keccak256(abi.encode(deployer, salt))` — same across all chains
- Deploy once, available everywhere with same ID
- Supports: mint/burn, lock/unlock, and custom token managers

---

## Hyperlane

### Architecture
- **Mailbox**: core messaging contract (dispatch/process)
- **ISM** (Interchain Security Module): configurable validation (multisig, aggregation, routing)
- **Hook system**: extensible pre/post-dispatch logic
- **Warp Routes**: token bridging (native, synthetic, collateral)
- **IGP** (Interchain Gas Paymaster): gas payment for cross-chain

### Key Pattern
```solidity
// Sending via Mailbox
IMailbox mailbox = IMailbox(MAILBOX_ADDRESS);
bytes32 messageId = mailbox.dispatch{value: gasPayment}(
    destinationDomain,
    recipientAddress,  // bytes32
    messageBody
);

// Receiving
function handle(uint32 _origin, bytes32 _sender, bytes calldata _body) external {
    require(msg.sender == address(mailbox), "Only mailbox");
    // Process message
}
```

### Unique: Flexible Security
- Choose ISM per application (not global like Wormhole/Axelar)
- Multisig ISM: N-of-M validator signatures
- Aggregation ISM: combine multiple ISMs (e.g., multisig AND optimistic)
- Routing ISM: different ISMs per origin chain

---

## Cross-Chain Security Considerations

### 1. Source Validation
Always validate the source chain AND source address:
```solidity
// LayerZero: peer checking is built into OApp via setPeer()
// Wormhole: check sourceChain + sourceAddress against trusted mapping
// Axelar: validate sourceChain + sourceAddress in _execute()
```

### 2. Message Replay Protection
- LayerZero: nonce-based (automatic)
- Wormhole: VAA hash deduplication (track processed hashes)
- Axelar: gateway handles deduplication

### 3. Finality Assumptions
- Source chain must reach finality before cross-chain message is valid
- Different chains have different finality times (Ethereum ~15min, Polygon ~30min, Arbitrum ~7 days for L1 finality)
- Some protocols allow configurable consistency levels (Wormhole)

### 4. Gas Payment
- Always estimate and prepay gas for destination execution
- Underpaying gas = message stuck (requires manual retry)
- Overpaying = excess typically refunded (protocol-dependent)

### 5. Token Bridging Models
| Model | How It Works | Pros | Cons |
|-------|-------------|------|------|
| Lock/Wrap | Lock on source, mint wrapped on dest | Simple | Wrapped tokens (liquidity fragmentation) |
| Burn/Mint | Burn on source, mint on dest | Canonical token | Requires mint authority |
| Liquidity Pool | Swap via pools on each side | No wrapping | Requires liquidity provisioning |

---

## Chain Selector / ID Reference

| Chain | EVM ID | LayerZero eid | Wormhole ID | Axelar Name | CCIP Selector |
|-------|--------|--------------|-------------|-------------|---------------|
| Ethereum | 1 | 30101 | 2 | "ethereum" | `5009297550715157269` |
| Arbitrum | 42161 | 30110 | 23 | "arbitrum" | `4949039107694359620` |
| Optimism | 10 | 30111 | 24 | "optimism" | `3734403246176062136` |
| Base | 8453 | 30184 | 30 | "base" | `15971525489660198786` |
| Polygon | 137 | 30109 | 5 | "polygon" | `4051577828743386545` |
| Avalanche | 43114 | 30106 | 6 | "avalanche" | `6433500567565415381` |
| BSC | 56 | 30102 | 4 | "binance" | `11344663589394136015` |
