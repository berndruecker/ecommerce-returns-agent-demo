

Running on localhost

* set authentications:

AWS_BEDROCK_ACCESS_KEY=
AWS_BEDROCK_SECRET_KEY=
SALESFORCE_BASE_URL=https://camunda--demoenv.sandbox.my.salesforce.com
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=
DEMO_BACKEND_BASE_URL=http://localhost:8100/
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=

* Run C8Run
* Deploy all BPMNs
* Use ngrok to forward local Webhook for Twilio (C8Run, port 8086 for connectors): --> https://catarina-unnicked-famishedly.ngrok-free.dev -> http://localhost:8086
* Run Fake Bakend (fake-backends --> python main.py)
