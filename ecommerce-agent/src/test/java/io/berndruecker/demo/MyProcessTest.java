package io.berndruecker.demo;

import static io.camunda.process.test.api.CamundaAssert.assertThatProcessInstance;
import static io.camunda.process.test.api.assertions.ProcessInstanceSelectors.byProcessId;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse;
import java.time.Duration;
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
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.junit.jupiter.Container;
import org.wiremock.spring.EnableWireMock;

import io.camunda.client.CamundaClient;
import io.camunda.client.annotation.Deployment;
import io.camunda.process.test.api.CamundaAssert;
import io.camunda.process.test.api.CamundaProcessTestContext;
import io.camunda.process.test.api.CamundaSpringProcessTest;
import io.camunda.process.test.api.assertions.ProcessInstanceAssert;

import static org.awaitility.Awaitility.await;



@SpringBootTest(classes = MyProcessTest.TestProcessApplication.class)
@CamundaSpringProcessTest
@org.testcontainers.junit.jupiter.Testcontainers
public class MyProcessTest {

  private static final String SALESFORCE_CONTACT_ID = "0039Q00001VsHMXQA3";
  // Need an app to deploy
  @SpringBootApplication
  @Deployment(resources = {"classpath:/ecommerce-agent.bpmn", "classpath:/communication-agent.bpmn", "classpath:/message-receiver.bpmn", "classpath:/message-sender.bpmn"})
  static class TestProcessApplication {}

  private static final String CONNECTOR_ID = "twilio";   
  private static final String EMAIL_ADDRESS = "camunda.demo.bernd@gmail.com";
  
    @Autowired private CamundaClient client;
    @Autowired private CamundaProcessTestContext processTestContext;

    
//    @Container
//    static GenericContainer<?> fakeBackend = new GenericContainer<>("berndruecker/ecommerce-fake-backends")
//        .withExposedPorts(8100)
//        .withNetworkAliases("fake-backends")
//        .waitingFor(Wait.forHttp("/").forStatusCode(200));
    
//    static String fakeBackendHostUrl() {
//      return "http://" + fakeBackend.getHost() + ":" + fakeBackend.getMappedPort(8100);
//    }
    
    @BeforeEach
    void setup() {
      Testcontainers.exposeHostPorts(8100); // Fake Backend - want to use it in demo
    }
    
    @Test
    void shouldCreateProcessInstance() throws URISyntaxException {
//      CamundaAssert.setAssertionTimeout(Duration.ofSeconds(75)); // increase for LLM calls
      
        Map<String, Object> variables = new HashMap<String, Object>();

        String initialChat = "Hi, I want to return a router I bought online.";
        String mobilePhone = "+49123456789";
        
        variables.put("supportCase", buildSupportCase(initialChat, mobilePhone));
        
        // Prepare WireMock for Salesforce Call (lookup customer)
        // Don't use WireMock - but mock the HTTP connector itself, because I can't obverwrite the Twilio URL from the connector
        //stubFor(get("/services/data/").willReturn(aResponse().withStatus(200).withBody(createSalesforceDummyResponse(mobilePhone))));            
        HttpJsonConnectorMock httpMock = new HttpJsonConnectorMock();
        
        // 
        httpMock.stubFor(HttpJsonConnectorMock.get("{{secrets.salesforce_base_url}}/services/data/").willReturn(
                         HttpJsonConnectorMock.aResponse().withStatus(200).withResultVariable("customer", buildCustomer(mobilePhone))));

       // secrets are not replaced in this mock
        httpMock.stubFor(HttpJsonConnectorMock.post("/2010-04-01/Accounts/{{secrets.twilio_account_sid}}/Messages.json").willReturn(
                         HttpJsonConnectorMock.aResponse().withStatus(200)
                            .withBody("""
                                {
                                  "sid": "SM123",
                                  "status": "queued"
                                }
                                """)));
        
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
        final var request = HttpRequest.newBuilder()
                .uri(new URI(processTestContext.getConnectorsAddress() + "/inbound/" + CONNECTOR_ID))
                .header("Content-Type", "application/json")
                .POST(BodyPublishers.ofString(createTwilioPayload(initialChat, mobilePhone)))
                .build();
        final var httpClient = HttpClient.newHttpClient();
        Awaitility.await().untilAsserted(() -> {
           final var response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
           Assertions.assertThat(response.statusCode())
                      .describedAs("Expect invoking the inbound connector successfully")
                      .isEqualTo(200);
        });
                      
   

        assertThatProcessInstance(byProcessId("customer-communication-agent"))
          .isActive()
          .hasCompletedElement("Task_Salesforce_LookupContact", 1)
          .hasVariableSatisfies("customer", java.util.Map.class, customer -> {
              Assertions.assertThat(customer).containsEntry("id", SALESFORCE_CONTACT_ID);
              Assertions.assertThat(customer).containsEntry("mobilePhone", mobilePhone);
          })          
          .hasCompletedElement("Tool_StartEcommerceAgent", 1); // necessary to wait for it to happen

        
//        
        ProcessInstanceAssert processInstanceAssert = assertThatProcessInstance(byProcessId("ecommerce-agent"))
          .isActive()
////          .hasCompletedElement("Task_Salesforce_LookupContact", 1)
////          .hasVariableSatisfies("customer", java.util.Map.class, customer -> {
////            Assertions.assertThat(customer).containsEntry("id", "0039Q00001VsHMXQA3");
////            Assertions.assertThat(customer).containsEntry("mobilePhone", mobilePhone);
////          })
          .hasCompletedElement("Tool_Magento_ListRecentOrders", 1);
//          .hasActiveElementsExactly("Tool_AskCustomer");
        
//        await().untilAsserted(() -> 
//          processInstanceAssert.hasCompletedElement("Tool_Magento_ListRecentOrders", 1)
//        );
        
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
    
    public static Map<String, Object> buildCustomer(String mobilePhone) {
      Map<String, Object> customer = new HashMap<>();
      customer.put("id", SALESFORCE_CONTACT_ID);
      customer.put("emailAddress", EMAIL_ADDRESS);
      customer.put("mobilePhone", mobilePhone);
      return customer;
    }
   
}
