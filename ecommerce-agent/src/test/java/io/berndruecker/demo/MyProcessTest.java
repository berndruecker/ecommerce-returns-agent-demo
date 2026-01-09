package io.berndruecker.demo;

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

@SpringBootTest(classes = MyProcessTest.TestProcessApplication.class)
@CamundaSpringProcessTest
public class MyProcessTest {

    @Autowired private CamundaClient client;
    @Autowired private CamundaProcessTestContext processTestContext;

    @Test
    void shouldCreateProcessInstance() {
        // given process definition is deployed

        // when
        final ProcessInstanceEvent processInstance =
            client
                .newCreateInstanceCommand()
                .bpmnProcessId("ecommerce-agent")
                .latestVersion()
                .send()
                .join();

        // then
        CamundaAssert.assertThat(processInstance).isActive();
    }
    
    @SpringBootApplication
    @Deployment(resources = "classpath:/ecommerce-agent.bpmn")
    static class TestProcessApplication {}    
}