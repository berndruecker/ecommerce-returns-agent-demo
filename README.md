
# E-Commerce Returns Agent Demo

## Overview

This demo showcases an AI-powered customer support agent that handles e-commerce product returns using Camunda 8 and AWS Bedrock. The agent can:

- **Answer customer questions** about orders and products via chat
- **Process return requests** by creating RMAs in Magento
- **Handle special cases** like end-of-life (EOL) product returns that require Salesforce exception approvals
- **Register returns in Manhattan WMS** to ensure warehouse acceptance
- **Search products** to help customers find replacement items
- **Communicate with customers** through multiple channels (chat, SMS via Twilio)

The demo integrates multiple backend systems:
- **Magento** - E-commerce platform (order history, RMA creation)
- **Manhattan WMS** - Warehouse management (return registration)
- **Salesforce** - Customer support cases and exception handling
- **Twilio** - SMS communication

## Architecture

The process runs as an **AI Agent** (reasoning loop) in Camunda 8:
1. Customer sends a message (email, chat, WhatsApp, or SMS)
2. AI agent analyzes the request and decides which tools to call
3. Tools execute (Magento, WMS, Salesforce connectors, ...)
4. Results are fed back to the AI
5. AI generates a response and sends it to the customer (possibly with questions)
6. Loop continues until the conversation ends

## Prerequisites

- **Camunda 8** (Desktop Modeler + C8Run or SaaS cluster)
- **Python 3.9+** (for fake backend services)
- **Java 17+** and Maven (if building the connector worker)
- **AWS Bedrock Access** (for Claude Sonnet 4.5) - or other AI provider
- **Salesforce Developer Account** 
- **Twilio Account** (for SMS/WhatsApp support)
- **ngrok** (optional, for exposing local webhooks to Twilio)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repo-url>
cd ecommerce-returns-agent-demo
```


### 2. Start the Fake Backend Services

The fake backends simulate Magento, Manhattan WMS, and other systems:

```bash
cd fake-backends
pip install -r requirements.txt
python main.py
```

The backend will start on `http://localhost:8100` with the following endpoints:
- `/commerce/*` - Magento e-commerce APIs
- `/wms/*` - Manhattan WMS APIs
- `/erp/*` - ERP system APIs
- `/policy/*` - Return policy APIs

### 3. Set Up Camunda 8

#### Option A: Using C8Run (Local)

1. Download and install [Camunda 8 Desktop Modeler](https://camunda.com/download/modeler/)
2. Download and start **C8Run** 
3. C8Run will start on `http://localhost:8080` (Operate) and `http://localhost:8086` (connector runtime)

#### Option B: Using Camunda SaaS

1. Create a cluster on [Camunda Cloud](https://camunda.io)
2. Create API credentials (Client ID + Secret)
3. Configure connection in Desktop Modeler

### 4. Configure Camunda Secrets

For C8Run create a `.env` file or set the following environment variables:

```bash
# AWS Bedrock (required)
AWS_BEDROCK_ACCESS_KEY=your_access_key
AWS_BEDROCK_SECRET_KEY=your_secret_key

# Salesforce (required for exception handling)
SALESFORCE_BASE_URL=https://your-instance.salesforce.com
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret

# Backend Base URL
DEMO_BACKEND_BASE_URL=http://localhost:8100

# Twilio (optional, for SMS)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
```


### 5. Deploy BPMN Processes

1. Open **Camunda Desktop Modeler**
2. Open the `ecommerce-agent/src/main/resources/` folder
3. Deploy each BPMN file:
	- `ecommerce-agent.bpmn` (main agent process)
	- `customer-communication-question.bpmn` (communication subprocess)
	- `twilio-receiver.bpmn` (SMS webhook receiver)

### 6. Deploy Element Templates

Copy the element templates to your Modeler's template folder:

**Windows:**
```bash
copy fake-backends\camunda-element-templates\*.json "%USERPROFILE%\.camunda\element-templates\"
```

**macOS/Linux:**
```bash
cp fake-backends/camunda-element-templates/*.json ~/.camunda/element-templates/
```

### 7. (Optional) Set Up Twilio Webhook

If using SMS/WhatsApp support:

1. Start ngrok to expose your local C8Run connector runtime:
	```bash
	ngrok http 8086
	```

2. Configure Twilio webhook URL:
	- URL: `https://<your-ngrok-url>/message` (from ngrok output)
	- Method: POST

### 8. Start a Process Instance

* Send a message through your configured chat channel (Slack, Teams, etc.)
* Send an SMS to your Twilio number


## Sample Storyline
The customer is auto-identified by WhatsApp number (no login needed). Conversation example:

```
[15:58] Customer (WhatsApp): I want to return the router I bought because it is too slow for gaming
[15:58] Agent (Twilio): I see you ordered a HomeStream Basic Router, delivered Jan 13, 2026 for $149.99. Is this the router you want to return?
[15:58] Customer: yes
[15:58] Agent: I found a better fit: Gaming Pro AX5700 WiFi 6 Router (ultra-low latency, WiFi 6, QoS). Price $199.99. Want to exchange?
[15:59] Customer: Yes please
[16:00] Agent: Done. Summary:
	1) Created return RMA-449F96B5 for the HomeStream Basic Router
	2) Applied $149.99 store credit to the new purchase
	3) Placed order for the Gaming Pro AX5700 WiFi 6 Router

You will receive the return label by email. The new router ships shortly with tracking details.
[16:02] Customer: thats all
```

**What happened technically**
- Auto-identify customer via WhatsApp number
- Look up customer via Salesforce
- Lookup recent orders in Magento (find HomeStream Basic)
- Offer gaming-optimized replacement via product search; collect consent
- Apply store credit and place new order in Magento
- Create RMA in Magento
- Register return in Manhattan WMS (with overrides if needed)
- Confirm via Twilio message


## Project Structure

```
ecommerce-returns-agent-demo/
├── ecommerce-agent/                 # Main Camunda process
│   └── src/main/resources/
│       ├── ecommerce-agent.bpmn     # Main AI agent loop
│       ├── customer-communication-question.bpmn
│       └── twilio-receiver.bpmn
├── fake-backends/                   # Python backend simulators
│   ├── main.py                      # FastAPI application
│   ├── data_store.py               # In-memory data
│   ├── routers/                    # API endpoints
│   │   ├── commerce.py             # Magento APIs
│   │   ├── wms.py                  # Manhattan WMS APIs
│   │   └── ...
│   └── camunda-element-templates/  # Connector templates
│       ├── magento-connector.json
│       └── manhattan-wms-connector.json
└── README.md
```

## License

See LICENSE file for details.
