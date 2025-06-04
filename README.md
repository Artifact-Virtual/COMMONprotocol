# The COMMON Protocol

> Communication Context Protocl

A lightweight, universal protocol for direct communication between language models (ULMs), agents, and clients—without reliance on external APIs or complex infrastructure.

## Overview

**Simplified Context Protocol (SCP)** enables any language model (LLM/ULM), agent, or client to exchange messages directly and securely. It is designed for easy integration, minimal configuration, and basic security, focusing on interoperability and simplicity. SCP is ideal for research, prototyping, and production environments where fast, flexible, and secure LLM-to-LLM or agent communication is required.

## Key Features

- **Universal Interoperability:** Connects any language model, agent, or client regardless of framework or vendor.
- **No External APIs Required:** All communication is direct—no dependency on third-party APIs or cloud services.
- **Minimal Configuration:** Simple setup with basic configuration files and scripts.
- **Basic Security:** Supports shared secrets or API keys for authentication.
- **Extensible:** Easily adaptable for new message types, agents, or relay mechanisms.
- **Internal and External Modes:** Clear separation between internal protocol logic and external client/relay implementations.

## Architecture

```text
[Client/Agent] <---> [SCP Server] <---> [Other Agents/Clients]
      |                    |                    |
[External]           [Internal]           [External]
```

- **internal/**: Core protocol logic (agent, server)
- **external/**: Example clients, relay server, and integration points

## Directory Structure

```text
simplifiedcontextprotocol/
├── README.md                # This documentation
├── internal/
│   ├── agent.py             # Agent implementation for SCP
│   └── server.py            # Main SCP server for message routing
├── external/
│   ├── client-example.py    # Example client for connecting to SCP
│   └── relay_server,py      # Relay/proxy server for message forwarding
└── .git/                    # Version control (if present)
```

## Usage

### 1. Start the SCP Server

```powershell
cd internal
python server.py
```

### 2. Run an Agent

```powershell
python agent.py
```

### 3. Connect a Client (Example)

```powershell
cd ../external
python client-example.py
```

### 4. (Optional) Use the Relay Server

```powershell
python relay_server,py
```

## Security

- **Shared Secrets/API Keys:** Configure agents and clients to use a shared secret or API key for basic authentication.
- **No Complex Auth:** SCP intentionally avoids complex authentication to reduce lockout risks and simplify integration.
- **Network Security:** For production, run SCP components on trusted networks or use VPN/tunneling as needed.

## Integration & Extensibility

- **Add New Agents:** Implement new agents by extending `agent.py`.
- **Custom Clients:** Use `client-example.py` as a template for your own clients in any language.
- **Relay/Proxy:** Use or extend `relay_server,py` to bridge networks or protocols.

## When to Use SCP

- Direct LLM-to-LLM or agent communication
- Prototyping multi-agent systems
- Research on language model interoperability
- Secure, internal message passing without cloud dependencies

## License

This project is open-source and available under the MIT License.

---

**Simplified Context Protocol**: Fast, flexible, and universal communication for language models and agents.
