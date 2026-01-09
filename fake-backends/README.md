# E-Commerce Returns Agent Demo - Backend Systems

A comprehensive mock backend application that simulates multiple enterprise systems for demonstrating an AI-powered returns agent. Built with FastAPI and designed to run on Google Cloud Run.

## 🎯 Purpose

This application provides realistic mock endpoints for demonstrating a seamless, AI-driven customer returns experience. It simulates integration with multiple backend systems:

- **Magento** (Commerce Platform) - Orders, products, cart, RMA
- **SAP** (ERP/Inventory) - SKU lifecycle, return eligibility, availability
- **Manhattan WMS** (Warehouse Management) - Fulfillment, returns, shipments
- **Returns Policy Service** - Policy evaluation and exceptions
- **Returns Provider** (Logistics) - Label generation
- **Payments** - Store credits and charges
- **Notifications** - Email notifications

## 🚀 Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

   # option A: run standalone worker
   python camunda_worker.py

   # option B: run inside the FastAPI app (default: enabled)
   python main.py                   # worker auto-starts
   CAMUNDA_WORKER_ENABLED=false python main.py  # disable if needed
   ```
   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload --port 8100
   ```

3. **Access the application:**
   - Homepage: http://localhost:8100
   - API Documentation: http://localhost:8100/docs
   - OpenAPI Spec: http://localhost:8100/openapi.json

### Docker

1. **Build the image:**
   ```bash
   docker build -t ecommerce-returns-demo .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8100:8100 ecommerce-returns-demo
   ```

### Google Cloud Run Deployment

1. **Build and push to Google Container Registry:**
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ecommerce-returns-demo
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy ecommerce-returns-demo \
     --image gcr.io/YOUR_PROJECT_ID/ecommerce-returns-demo \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

## ⚙️ Camunda 8 Magento Connector (Python Worker)

This repo includes a lightweight Camunda 8 worker that routes service tasks to the fake Magento endpoints and an element template for the Modeler.

### Files
- Worker: [camunda_worker.py](camunda_worker.py)
- Element template: [camunda/element-templates/magento-connector.json](camunda/element-templates/magento-connector.json)

### Run the worker locally

```bash
pip install -r requirements.txt
# option A: run standalone
python camunda_worker.py

# option B: run inside the FastAPI app (sets a background thread)
CAMUNDA_WORKER_ENABLED=true python main.py
```

Environment variables (optional):
- `MAGENTO_API_BASE` (default `http://localhost:8100/commerce`)
- Self-managed Zeebe: `ZEEBE_ADDRESS` (default `localhost:26500`)
- Camunda 8 SaaS: `ZEEBE_CLIENT_ID`, `ZEEBE_CLIENT_SECRET`, `ZEEBE_ADDRESS` (cluster id), `ZEEBE_REGION` (default `bru-2`), `ZEEBE_AUTHORIZATION_SERVER_URL` (optional)
- In-process worker control: set `CAMUNDA_WORKER_ENABLED=false` to disable (defaults to enabled)

### Use in Modeler
1) Import `camunda/element-templates/magento-connector.json` as an element template.
2) Drop a Service Task, choose **Magento Connector (Demo)**.
3) Select an operation (list orders, product search, create RMA, create cart, add item, apply store credit, place order).
4) The template dynamically shows the required fields per operation.
5) Result is stored by default in `magentoResponse` (configurable via result variable field).

## 🔌 SAP MCP Server (Model Context Protocol)

The application includes an MCP server that exposes SAP ERP endpoints as callable tools. This enables integration with Camunda 8.9's MCP Remote connector.

### MCP Endpoint

**Base URL:** `http://localhost:8100/mcp/sse`

### Available Tools

1. **sap_check_return_eligibility** - Check if a SKU is eligible for return
   - Parameters: `sku`, `orderId`, `daysSinceDelivery`

2. **sap_get_sku_info** - Get SKU lifecycle and clearance information
   - Parameters: `sku`

3. **sap_check_availability** - Check product availability and stock level
   - Parameters: `sku`

### Using with Camunda 8.9 MCP Remote

1. **Configure MCP Remote Connector** in your BPMN:
   ```
   MCP Server URL: http://localhost:8100/mcp/sse
   Tool Name: sap_check_return_eligibility (or other tool names)
   Arguments: { "sku": "RTR-AC1900", "orderId": "ORD-2025-001234", "daysSinceDelivery": 12 }
   ```

2. **Environment Variable** (optional):
   - `SAP_API_BASE` - Override SAP endpoint base URL (default: `http://localhost:8100/erp`)

### Testing MCP Server

You can test the MCP server using any MCP client or curl:

```bash
# The server uses SSE (Server-Sent Events) transport
# Use MCP client libraries or Camunda 8.9 MCP Remote connector to call tools
```

## 📋 Demo Scenario

The application is pre-loaded with sample data for the following scenario:

**Customer:** John Smith (CUST001)
- Recently purchased an AC1900 router (12 days ago)
- Router is discontinued and experiencing performance issues
- Wants to return and upgrade

**Available Products:**
- RTR-AC1900: Original router (discontinued)
- RTR-AX5400: WiFi 6 gaming router (recommended)
- RTR-AXE7800: Premium WiFi 6E router
- RTR-AX3000: Budget WiFi 6 option

**Demo Flow:**
1. Customer contacts via WhatsApp about return
2. Agent retrieves customer orders
3. Agent identifies the router and checks return eligibility
4. Agent detects discontinued item, applies exception
5. Agent recommends better gaming router
6. Agent orchestrates: return approval, label generation, store credit, new purchase, shipment

## 🔌 API Endpoints

### Commerce (Magento)
- `GET /commerce/customers/{customerId}/orders` - List recent orders
- `GET /commerce/catalog/products` - Search products with filters
- `POST /commerce/rmas` - Create return authorization
- `POST /commerce/carts` - Create shopping cart
- `POST /commerce/carts/{cartId}/items` - Add items to cart
- `POST /commerce/carts/{cartId}/discounts/store-credit` - Apply store credit
- `POST /commerce/orders` - Place order

### ERP (SAP)
- `GET /erp/skus/{sku}/return-eligibility` - Check return eligibility
- `GET /erp/skus/{sku}` - Get SKU lifecycle info
- `GET /erp/availability` - Check product availability

### WMS (Manhattan)
- `GET /wms/fulfillment/eligibility` - Check fulfillment capability
- `POST /wms/returns/expected` - Create expected return
- `POST /wms/shipments/release` - Release shipment for delivery

### Policy
- `POST /policy/returns/evaluate` - Evaluate return with rules and exceptions

### Returns Provider
- `POST /returns/labels` - Generate prepaid return label

### Payments
- `POST /payments/credits` - Issue instant store credit
- `POST /payments/charges` - Charge payment

### Notifications
- `POST /notify/email` - Send email with attachments

## 📊 Data Management

All data is stored in-memory and can be modified at runtime through the API. Data includes:
- Customers
- Products
- Orders
- RMAs
- Carts
- Store credits
- Shipments
- Email notifications

The data resets when the application restarts, making it perfect for demos.

## 🛠️ Technology Stack

- **Framework:** FastAPI (modern, fast, with automatic API docs)
- **Language:** Python 3.11
- **Server:** Uvicorn with uvloop for high performance
- **Validation:** Pydantic v2 for data validation
- **Templates:** Jinja2 for HTML rendering
- **Container:** Docker with multi-stage build
- **Cloud:** Google Cloud Run ready

## 📝 Project Structure

```
ecommerce-returns-agent-demo/
├── main.py                 # FastAPI application entry point
├── models.py              # Pydantic data models
├── data_store.py          # In-memory data store with sample data
├── routers/               # API route handlers
│   ├── commerce.py        # Magento endpoints
│   ├── erp.py            # SAP endpoints
│   ├── wms.py            # Manhattan WMS endpoints
│   ├── policy.py         # Policy service endpoints
│   ├── returns_provider.py # Returns provider endpoints
│   ├── payments.py       # Payment endpoints
│   └── notifications.py  # Notification endpoints
├── templates/            # HTML templates
│   └── index.html       # Homepage
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container definition
├── .dockerignore       # Docker ignore rules
└── README.md           # This file
```

## 🎨 Customization

### Adding New Products
Edit `data_store.py` and add products to the `_initialize_demo_data()` method:

```python
self.products["NEW-SKU"] = Product(
    sku="NEW-SKU",
    name="Product Name",
    category=ProductCategory.ROUTERS,
    price=199.99,
    # ... other fields
)
```

### Adding New Customers
Similar to products, add customers in `data_store.py`:

```python
self.customers.append(Customer(
    customer_id="CUST002",
    name="Jane Doe",
    # ... other fields
))
```

### Modifying Business Rules
Edit the relevant router file in the `routers/` directory. For example, to change return policy logic, edit `routers/policy.py`.

## 🔍 Health Checks

The application includes a health check endpoint for monitoring:
- `GET /health` - Returns `{"status": "healthy"}`

## 📖 API Documentation

FastAPI automatically generates interactive API documentation:
- **Swagger UI:** http://localhost:8100/docs
- **ReDoc:** http://localhost:8100/redoc

These provide interactive testing of all endpoints with request/response examples.

## 🐛 Development

### Running Tests
(Add your testing framework here)

### Code Style
The code follows PEP 8 guidelines and uses type hints throughout.

## 📄 License

See LICENSE file for details.

## 🤝 Contributing

This is a demo application. Feel free to fork and customize for your needs.

## 📧 Support

For questions or issues, please open an issue in the repository.
