package io.berndruecker.demo;

import java.util.HashMap;
import java.util.Map;

import org.assertj.core.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.context.SpringBootTest;

import io.camunda.client.CamundaClient;
import io.camunda.client.annotation.Deployment;
import io.camunda.client.api.response.ProcessInstanceEvent;
import io.camunda.process.test.api.CamundaAssert;
import io.camunda.process.test.api.CamundaProcessTestContext;
import io.camunda.process.test.api.CamundaSpringProcessTest;
import static io.camunda.process.test.api.assertions.ProcessInstanceAssert.*;
import static io.camunda.process.test.api.CamundaAssert.*;


@SpringBootTest(classes = MyProcessTest.TestProcessApplication.class)
@CamundaSpringProcessTest
public class MyProcessTest {

  @SpringBootApplication
  @Deployment(resources = {"classpath:/ecommerce-agent.bpmn", "classpath:/customer-communication-question.bpmn"})
  static class TestProcessApplication {}   
  
    @Autowired private CamundaClient client;
    @Autowired private CamundaProcessTestContext processTestContext;

    @Test
    void shouldCreateProcessInstance() {
        Map<String, Object> variables = new HashMap<String, Object>();

        String initialChat = "Hi, I want to return a router I bought online.";
        String mobilePhone = "+49123456789";
        
        variables.put("supportCase", "{\r\n"
            + "    \"subject\": \"WhatsApp Request\",\r\n"
            + "    \"request\": \""+ initialChat  +"\",\r\n"
            + "    \"communicationContext\": {\r\n"
            + "        \"channel\" : \"whatsApp\",\r\n"
            + "        \"channelId\": \\\"+49123456789\\\",\r\n"
            + "        \"emailAddress\": \"bernd.it.depends.ruecker@gmail.com\",\r\n"
            + "        \"mobilePhone\": \""+mobilePhone+"\",\r\n"
            + "        \"conversationId\": conversationUUID,\r\n"
            + "        \"lastMessageId\": message.id\r\n"
            + "    }\r\n"
            + "}");

        // when
        final ProcessInstanceEvent processInstance =
            client
                .newCreateInstanceCommand()
                .bpmnProcessId("ecommerce-agent")
                .latestVersion()
                .variables(variables)
                .send()
                .join();

        
        // then
        assertThat(processInstance).isActive()
          .hasCompletedElement("Task_Salesforce_LookupContact", 1)
          .hasVariableSatisfies("customer", java.util.Map.class, customer -> {
            Assertions.assertThat(customer).containsEntry("id", "0039Q00001VsHMXQA3");
            Assertions.assertThat(customer).containsEntry("mobilePhone", mobilePhone);
          })
          .hasCompletedElement("Tool_Magento_ListRecentOrders", 1)
          .hasActiveElementsExactly("Tool_AskCustomer");
        
        // Check text to customer should be around "I see a router delivered 12 days ago for $150."
    }
    
 
}