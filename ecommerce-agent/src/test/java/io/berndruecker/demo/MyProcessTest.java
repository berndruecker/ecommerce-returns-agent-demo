package io.berndruecker.demo;

import static io.camunda.process.test.api.CamundaAssert.assertThatProcessInstance;
import static io.camunda.process.test.api.assertions.ProcessInstanceSelectors.byProcessId;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.assertj.core.api.Assertions;
import org.awaitility.Awaitility;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.context.SpringBootTest;
import org.testcontainers.Testcontainers;
import org.wiremock.spring.EnableWireMock;

import io.camunda.client.CamundaClient;
import io.camunda.client.annotation.Deployment;
import io.camunda.process.test.api.CamundaProcessTestContext;
import io.camunda.process.test.api.CamundaSpringProcessTest;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static com.github.tomakehurst.wiremock.client.WireMock.equalToJson;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.postRequestedFor;
import static com.github.tomakehurst.wiremock.client.WireMock.stubFor;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.client.WireMock.verify;


@EnableWireMock
@SpringBootTest(classes = MyProcessTest.TestProcessApplication.class)
@CamundaSpringProcessTest
public class MyProcessTest {

  // Need an app to deploy
  @SpringBootApplication
  @Deployment(resources = {"classpath:/ecommerce-agent.bpmn", "classpath:/communication-agent.bpmn", "classpath:/message-receiver.bpmn", "classpath:/message-sender.bpmn"})
  static class TestProcessApplication {}

  private static final String CONNECTOR_ID = "twilio";   
  
    @Autowired private CamundaClient client;
    @Autowired private CamundaProcessTestContext processTestContext;
    
    @Value("${wiremock.server.port}")
    private int wireMockPort;

    @BeforeEach
    void setup() {
      Testcontainers.exposeHostPorts(wireMockPort);
    }
    
    @Test
    void shouldCreateProcessInstance() throws URISyntaxException {
        Map<String, Object> variables = new HashMap<String, Object>();

        String initialChat = "Hi, I want to return a router I bought online.";
        String mobilePhone = "+49123456789";
        
        variables.put("supportCase", buildSupportCase(initialChat, mobilePhone));
        
        
        HttpJsonConnectorMock httpMock = new HttpJsonConnectorMock();
        httpMock.stubFor(
                HttpJsonConnectorMock.get("/services/data/")
                    .willReturn(
                        HttpJsonConnectorMock.aResponse()
                            .withStatus(200)
                            .withBody(createSalesforceDummyResponse(mobilePhone))
                    )
            );

        httpMock.stubFor(
                HttpJsonConnectorMock.post("/2010-04-01/Accounts/" + "123" + "/Messages.json")
                    .willReturn(
                        HttpJsonConnectorMock.aResponse()
                            .withStatus(200)
                            .withBody("""
                                {
                                  "sid": "SM123",
                                  "status": "queued"
                                }
                                """)
                    )
            );
        
        processTestContext
          .mockJobWorker("io.camunda:http-json:1")
          .withHandler(httpMock);         

//        // when
//        final ProcessInstanceEvent processInstance =
//            client
//                .newCreateInstanceCommand()
//                .bpmnProcessId("ecommerce-agent")
//                .latestVersion()
//                .variables(variables)
//                .send()
//                .join();
        
        // Start via simulating Twilio:
        final var request =
            HttpRequest.newBuilder()
                .uri(new URI(processTestContext.getConnectorsAddress() + "/inbound/" + CONNECTOR_ID))
                .header("Content-Type", "application/json")
                .POST(BodyPublishers.ofString(createTwilioPayload(initialChat, mobilePhone)))
                .build();
        final var httpClient = HttpClient.newHttpClient();
        Awaitility.await()
            .untilAsserted(
                () -> {
                  final var response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

                  Assertions.assertThat(response.statusCode())
                      .describedAs("Expect invoking the inbound connector successfully")
                      .isEqualTo(200);
                });
              
        
        // Prepare WireMock for Salesforce Call (lookup customer)
        // Don't use WireMock - but mock the HTTP connector itself, because I can't obverwrite the Twilio URL from the connector
        //stubFor(get("/services/data/").willReturn(aResponse().withStatus(200).withBody(createSalesforceDummyResponse(mobilePhone))));       

        assertThatProcessInstance(byProcessId("customer-communication-agent"))
          .isActive()
          .hasCompletedElement("Task_Salesforce_LookupContact", 1)
          .hasCompletedElement("Tool_StartEcommerceAgent", 1); // necessary to wait for it to happen

        assertThatProcessInstance(byProcessId("ecommerce-agent"))
          .isActive()
          .hasCompletedElement("Task_Salesforce_LookupContact", 1)
          .hasVariableSatisfies("customer", java.util.Map.class, customer -> {
            Assertions.assertThat(customer).containsEntry("id", "0039Q00001VsHMXQA3");
            Assertions.assertThat(customer).containsEntry("mobilePhone", mobilePhone);
          })
          .hasCompletedElement("Tool_Magento_ListRecentOrders", 1)
          .hasActiveElementsExactly("Tool_AskCustomer");
        
        // Check text to customer should be around "I see a router delivered 12 days ago for $150."
        
        
        //httpMock.assertAllExpectedCallsUsed();
    }
    public static String buildSupportCase(String request, String mobilePhone) {
      return buildSupportCase(request, mobilePhone, "camunda.demo.bernd@gmail.com", null);
      
    }
    
    public static String createSalesforceDummyResponse(String mobilePhone) {
      return "{"
          + "\"status\": 200,"
          + "\"body\": {"
          +     "\"totalSize\": 1,"
          +     "\"done\": true,"
          +     "\"records\": ["
          +         "{"
          +             "\"Id\": \"0039Q00001VcSaVQAV\","
          +             "\"AccountId\": \"0019Q00001KUtpCQAT\","
          +             "\"Name\": \"Bernd Ruecker\","
          +             "\"Email\": \"bernd.it.depends.ruecker@gmail.com\","
          +             "\"MobilePhone\": \"" + mobilePhone + "\""
          +         "}"
          +     "]"
          + "},"
          + "\"reason\": \"OK\","
          + "\"document\": null"
          + "}";
  }

    public static String createTwilioPayload(String text, String mobilePhone) {
        // Generate unique IDs for this message
        String messageId = UUID.randomUUID().toString();
        String accountSid = "AC0f547190a12a31e6fce04b80d9fe69b8";
        
        // Extract WaId from mobilePhone (remove + sign if present)
        String waId = mobilePhone.replace("+", "");
        
        // Build the JSON payload as a string
        return "{\r\n"
            + "    \"SmsMessageSid\": \"" + messageId + "\",\r\n"
            + "    \"NumMedia\": \"0\",\r\n"
            + "    \"ProfileName\": \"Customer\",\r\n"
            + "    \"Body\": \"" + text.replace("\"", "\\\"") + "\",\r\n"
            + "    \"To\": \"whatsapp:+14155238886\",\r\n"
            + "    \"AccountSid\": \"" + accountSid + "\",\r\n"
            + "    \"ChannelMetadata\": \"{\\\"type\\\":\\\"whatsapp\\\",\\\"data\\\":{\\\"context\\\":{\\\"ProfileName\\\":\\\"Customer\\\",\\\"WaId\\\":\\\"" + waId + "\\\"}}}\",\r\n"
            + "    \"From\": \"whatsapp:" + mobilePhone + "\",\r\n"
            + "    \"ApiVersion\": \"2010-04-01\",\r\n"
            + "    \"MessageType\": \"text\",\r\n"
            + "    \"SmsSid\": \"" + messageId + "\",\r\n"
            + "    \"WaId\": \"" + waId + "\",\r\n"
            + "    \"SmsStatus\": \"received\",\r\n"
            + "    \"NumSegments\": \"1\",\r\n"
            + "    \"ReferralNumMedia\": \"0\",\r\n"
            + "    \"MessageSid\": \"" + messageId + "\"\r\n"
            + "}";
    }
    
    public static String buildSupportCase(String request, String mobilePhone, String emailAddress, String conversationId) {
        return "{\r\n"
            + "    \"subject\": \"WhatsApp Return Request\",\r\n"
            + "    \"request\": \"" + request.replace("\"", "\\\"") + "\",\r\n"
            + "    \"communicationContext\": {\r\n"
            + "        \"channel\": \"whatsApp\",\r\n"
            + "        \"channelId\": \"" + mobilePhone + "\",\r\n"
            + "        \"emailAddress\": \"" + emailAddress + "\",\r\n"
            + "        \"mobilePhone\": \"" + mobilePhone + "\",\r\n"
//            + "        \"conversationId\": \"" + conversationId + "\",\r\n"
//            + "        \"lastMessageId\": \"msg-001\"\r\n"
            + "    }\r\n"
            + "}";
    }
    
}
