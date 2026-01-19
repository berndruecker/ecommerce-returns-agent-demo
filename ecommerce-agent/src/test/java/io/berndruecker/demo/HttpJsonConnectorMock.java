package io.berndruecker.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.Map;


import io.camunda.client.api.response.ActivatedJob;
import io.camunda.client.api.worker.JobClient;
import io.camunda.client.api.worker.JobHandler;

/**
 * Mocks the Camunda HTTP JSON connector (type: "io.camunda:http-json:1")
 * with a sequence of expected calls.
 */
public class HttpJsonConnectorMock implements JobHandler {


  private final Deque<StubMapping> mappings = new ArrayDeque<>();

//--------------------------------------------------
 // WireMock-like DSL
 // --------------------------------------------------

 public void stubFor(StubMapping mapping) {
   mappings.add(mapping);
 }

 public static RequestPatternBuilder get(String urlContains) {
   return new RequestPatternBuilder("GET", urlContains.toLowerCase());
 }

 public static RequestPatternBuilder post(String urlContains) {
   return new RequestPatternBuilder("POST", urlContains.toLowerCase());
 }

 public static ResponseDefinitionBuilder aResponse() {
   return new ResponseDefinitionBuilder();
 }

 // --------------------------------------------------
 // Job handler
 // --------------------------------------------------

  @Override
  public void handle(JobClient client, ActivatedJob job) throws Exception {
    StubMapping mapping = mappings.poll();
    assertNotNull(mapping, "No more HTTP calls expected, but connector was invoked");

    Map<String, Object> vars = job.getVariablesAsMap();

    String method = asString(vars.get("method")).toUpperCase();
    String url = asString(vars.get("url")).toLowerCase();

    assertEquals(mapping.method, method, "Unexpected HTTP method");
    assertTrue(
        url.contains(mapping.urlContains),
        "Unexpected URL. Expected to contain [" + mapping.urlContains + "] but was [" + url + "]"
    );

    // Simulated connector result
    Map<String, Object> httpResult = new HashMap<>();
    httpResult.put("status", mapping.response.status);
    httpResult.put("body", mapping.response.body);
    httpResult.put("reason", "OK");
    

    Map<String, Object> resultVariables = new HashMap<>();
    resultVariables.put("httpResult", httpResult);
    resultVariables.putAll(mapping.response.variables);

    client
        .newCompleteCommand(job)
        .variables(resultVariables)
        .send()
        .join();
  }

  public void verifyNoMoreCalls() {
    assertTrue(mappings.isEmpty(), "Not all expected HTTP calls were executed");
  }

  private static String asString(Object o) {
    return o == null ? null : String.valueOf(o);
  }

  public static class RequestPatternBuilder {
    private final String method;
    private final String urlContains;

    private RequestPatternBuilder(String method, String urlContains) {
      this.method = method;
      this.urlContains = urlContains;
    }

    public StubMapping willReturn(ResponseDefinitionBuilder response) {
      return new StubMapping(method, urlContains, response);
    }
  }

  public static class ResponseDefinitionBuilder {
    private int status;
    private String body;
    private Map<String, Object> variables = new HashMap<String, Object>();

    public ResponseDefinitionBuilder withStatus(int status) {
      this.status = status;
      return this;
    }

    public ResponseDefinitionBuilder withBody(String body) {
      this.body = body;
      return this;
    }

    public ResponseDefinitionBuilder withResultVariable(String varName, Object value) {
      this.variables.put(varName, value);
      return this;
    }
}

  public static class StubMapping {
    private final String method;
    private final String urlContains;
    private final ResponseDefinitionBuilder response;

    private StubMapping(String method, String urlContains, ResponseDefinitionBuilder response) {
      this.method = method;
      this.urlContains = urlContains;
      this.response = response;
    }
  }

}
