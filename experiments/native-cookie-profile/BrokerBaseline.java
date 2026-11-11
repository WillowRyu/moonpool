package org.moonpool.httpbroker;

import java.lang.reflect.Method;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

/** Test adapter for the retained broker's cookie operations on the desktop JVM. */
final class BrokerBaseline {
    private static final String PORTAL = "fixture";
    private static final String APP = "com.example.fixture";

    public static void main(String[] args) throws Exception {
        // The device probe keeps these operations private. Invoke their original bodies with fixture inputs.
        Method store = Broker.class.getDeclaredMethod("store", Broker.App.class, String.class, URI.class);
        Method header = Broker.class.getDeclaredMethod("cookieHeader", Broker.App.class, URI.class);
        store.setAccessible(true);
        header.setAccessible(true);

        JSONArray cases = new JSONArray(new String(System.in.readAllBytes(), StandardCharsets.UTF_8));
        JSONArray results = new JSONArray();
        for (int index = 0; index < cases.length(); index++) {
            JSONObject vector = cases.getJSONObject(index);
            JSONArray observations = observe(vector.getJSONArray("steps"), store, header);
            results.put(Broker.obj("id", vector.getString("id"), "observations", observations));
        }
        System.out.println(results);
    }

    private static JSONArray observe(JSONArray steps, Method store, Method header) throws Exception {
        Set<String> approved = new HashSet<>();
        for (int index = 0; index < steps.length(); index++) {
            URI url = URI.create(steps.getJSONObject(index).getString("url"));
            int port = url.getPort() == -1 ? 443 : url.getPort();
            approved.add(url.getHost().toLowerCase(Locale.ROOT) + ":" + port);
        }

        Broker broker = new Broker(null, approved);
        broker.bind(PORTAL, APP, Set.of("cookies"));
        Broker.App app = broker.apps.get(APP);
        JSONArray observations = new JSONArray();
        for (int index = 0; index < steps.length(); index++) {
            JSONObject step = steps.getJSONObject(index);
            String target = step.getString("url");
            URI url = URI.create(target);
            String operation = step.getString("op");
            // This broker has no expiry clock. The next implementation will consume the fixture's "now".
            switch (operation) {
                case "receive" -> {
                    receive(broker, app, store, step.getJSONArray("fields"), url);
                    observations.put(JSONObject.NULL);
                }
                case "header" -> observations.put(header.invoke(null, app, url));
                case "jar" -> observations.put(snapshot(app));
                case "read" -> observations.put(broker.cookiesGet(PORTAL, target).getJSONArray("cookies"));
                case "set" -> observations.put(broker.cookiesSet(PORTAL, target, step.getJSONObject("fields"))
                    .getBoolean("ok"));
                default -> throw new IllegalArgumentException("Unknown fixture operation " + operation);
            }
        }
        return observations;
    }

    private static void receive(Broker broker, Broker.App app, Method store, JSONArray fields, URI url)
            throws Exception {
        List<String> values = new ArrayList<>();
        for (int index = 0; index < fields.length(); index++) {
            values.add(fields.getString(index));
        }
        for (String line : Broker.splitFolded(String.join(", ", values))) {
            store.invoke(broker, app, line, url);
        }
    }

    private static JSONArray snapshot(Broker.App app) {
        JSONArray cookies = new JSONArray();
        for (Broker.Cookie cookie : app.jar) {
            // Every baseline entry matches its exact host and lives for the in-memory session.
            cookies.put(Broker.obj(
                "name", cookie.name, "value", cookie.value, "domain", cookie.host, "path", cookie.path,
                "hostOnly", true, "httpOnly", cookie.httpOnly, "expiresAt", JSONObject.NULL
            ));
        }
        return cookies;
    }
}
