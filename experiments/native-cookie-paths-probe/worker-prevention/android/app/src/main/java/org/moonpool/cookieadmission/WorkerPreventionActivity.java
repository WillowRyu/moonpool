package org.moonpool.cookieadmission;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.ServiceWorkerClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import androidx.webkit.Profile;
import androidx.webkit.ProfileStore;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

public final class WorkerPreventionActivity extends Activity {
    private static final List<String> CASES = List.of("managed", "retained", "unknown", "unconfirmed");
    private static final String ENTRY = "/entry";
    private static final String FRAME = "/child/frame";
    private static final String ENTRY_WORKER = "/worker.js";
    private static final String FRAME_WORKER = "/child/worker.js";
    private static final String POLICY = "worker-src 'none'";
    private static final String PROVENANCE_VERSION = "2";
    private final Handler ui = new Handler(Looper.getMainLooper());
    private FrameLayout views;
    private String run, phase, requestedCase;
    private String registrationScript, storeScript, workerScript;
    private String webViewVersion;

    private record Partition(String profile, String origin, String marker) {}

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        views = new FrameLayout(this);
        setContentView(views);
        run = getIntent().getStringExtra("run");
        phase = getIntent().getStringExtra("phase");
        requestedCase = getIntent().getStringExtra("case");
        new Thread(this::execute).start();
    }

    private Partition partition(String key) {
        String marker = run + "-" + key;
        return new Partition("worker-prevention-" + marker, "https://mp-" + marker + ".invalid", marker);
    }

    private <T> T main(Callable<T> operation) throws Exception {
        FutureTask<T> task = new FutureTask<>(operation);
        ui.post(task);
        return task.get(12, TimeUnit.SECONDS);
    }

    private String asset(String name) throws Exception {
        try (InputStream input = getAssets().open(name); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int count;
            while ((count = input.read(buffer)) != -1) bytes.write(buffer, 0, count);
            return bytes.toString(StandardCharsets.UTF_8.name());
        }
    }

    private WebView view(Partition partition, WebViewClient client, boolean offline) {
        WebView web = new WebView(this);
        WebViewCompat.setProfile(web, partition.profile());
        if (!partition.profile().equals(WebViewCompat.getProfile(web).getName())) {
            throw new IllegalStateException("Unexpected WebView profile");
        }
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.getSettings().setBlockNetworkLoads(offline);
        web.setWebViewClient(client);
        views.addView(web);
        return web;
    }

    private void destroy(WebView web) {
        web.stopLoading();
        views.removeView(web);
        web.destroy();
    }

    private JSONObject observe(WebView web, String property) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(15);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> result = new CompletableFuture<>();
            ui.post(() -> web.evaluateJavascript("JSON.stringify(window." + property + " || null)", result::complete));
            String raw;
            try {
                raw = result.get(1, TimeUnit.SECONDS);
            } catch (TimeoutException pending) {
                continue;
            }
            if (new JSONTokener(raw == null ? "null" : raw).nextValue() instanceof String json
                    && new JSONTokener(json).nextValue() instanceof JSONObject data) {
                return data;
            }
            Thread.sleep(100);
        }
        throw new TimeoutException("No " + property + " observation");
    }

    private WebResourceResponse response(int status, String mime, String body, String policy) {
        Map<String, String> headers = policy.isEmpty()
            ? Map.of("Cache-Control", "no-store")
            : Map.of("Cache-Control", "no-store", "Content-Security-Policy", policy);
        return new WebResourceResponse(mime, "UTF-8", status, status == 200 ? "OK" : "Forbidden",
            headers, new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));
    }

    private boolean atOrigin(WebResourceRequest request, Partition partition) {
        return partition.origin().equals(request.getUrl().getScheme() + "://" + request.getUrl().getEncodedAuthority());
    }

    private WebResourceResponse workerResponse(WebResourceRequest request, Partition partition,
                                                ConcurrentLinkedQueue<String> requests) {
        String path = request.getUrl().getEncodedPath();
        if (atOrigin(request, partition) && "GET".equals(request.getMethod())
                && (ENTRY_WORKER.equals(path) || FRAME_WORKER.equals(path))) {
            requests.add(path);
            return response(200, "text/javascript", workerScript, "");
        }
        return response(403, "text/plain", "", "");
    }

    private void measureGuest(Profile profile, Partition partition, boolean guarded, String writeMarker,
                              AdmissionGate.Presence verdict, JSONArray events, JSONObject report) throws Exception {
        String policy = guarded ? POLICY : "";
        String marker = writeMarker == null ? "undefined" : JSONObject.quote(writeMarker);
        String page = "<!doctype html><meta charset=utf-8><title>Moonpool test mini app</title>"
            + "<body><script>window.workerPreventionWrite=" + marker + ";\n"
            + storeScript + "\n" + registrationScript + "</script>";
        ConcurrentHashMap<String, String> policies = new ConcurrentHashMap<>();
        ConcurrentLinkedQueue<String> requests = new ConcurrentLinkedQueue<>();
        int[] loads = {0};
        WebView web = main(() -> {
            WebView[] opened = {null};
            AdmissionGate gate = new AdmissionGate((name, complete) -> complete.accept(verdict));
            gate.admit(partition.profile(), () -> {
                var workers = profile.getServiceWorkerController();
                workers.getServiceWorkerWebSettings().setBlockNetworkLoads(false);
                workers.setServiceWorkerClient(new ServiceWorkerClient() {
                    @Override public WebResourceResponse shouldInterceptRequest(WebResourceRequest request) {
                        return workerResponse(request, partition, requests);
                    }
                });
                WebView guest = view(partition, new WebViewClient() {
                    @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                        return !atOrigin(request, partition);
                    }

                    @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                        String path = request.getUrl().getEncodedPath();
                        if (atOrigin(request, partition) && "GET".equals(request.getMethod())
                                && (ENTRY.equals(path) || FRAME.equals(path))) {
                            WebResourceResponse document = response(200, "text/html", page, policy);
                            policies.put(path, document.getResponseHeaders().getOrDefault("Content-Security-Policy", ""));
                            return document;
                        }
                        return workerResponse(request, partition, requests);
                    }
                }, false);
                opened[0] = guest;
                loads[0]++;
                events.put("guest");
                guest.loadUrl(partition.origin() + ENTRY);
            }, () -> {
                events.put("refuse");
                if (opened[0] != null) {
                    destroy(opened[0]);
                    opened[0] = null;
                }
            });
            return opened[0];
        });
        report.put("guestLoads", loads[0]);
        if (web == null) {
            report.put("guest", JSONObject.NULL);
        } else {
            try {
                JSONObject guest = observe(web, "workerPreventionResult");
                report.put("guest", guest);
                report.put("marker", guest.opt("marker"));
                report.put("markerOrigin", guest.opt("origin"));
            } finally {
                main(() -> { destroy(web); return null; });
            }
        }
        report.put("documentPolicies", new JSONObject(policies));
        report.put("workerRequests", new JSONArray(requests));
    }

    private void markerOnly(Partition partition, boolean write, JSONObject report) throws Exception {
        String nonce = UUID.randomUUID().toString();
        String marker = write ? JSONObject.quote(partition.marker()) : "";
        String html = "<!doctype html><meta charset=utf-8><meta http-equiv=\"Content-Security-Policy\""
            + " content=\"default-src 'none'; script-src 'unsafe-inline'; base-uri 'none'\"><script>"
            + storeScript + "\n(async () => { window.workerPreventionMarker = { nonce: " + JSONObject.quote(nonce)
            + ", origin: window.origin, marker: await window.workerAdmissionData(" + marker + ") }; })();</script>";
        ConcurrentLinkedQueue<String> requests = new ConcurrentLinkedQueue<>();
        WebView web = main(() -> {
            WebView inspector = view(partition, new WebViewClient() {
                @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    return true;
                }

                @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                    String scheme = request.getUrl().getScheme();
                    if ("data".equals(scheme) || "about".equals(scheme)) return null;
                    requests.add(request.getUrl().toString());
                    return response(403, "text/plain", "", "");
                }
            }, true);
            inspector.loadDataWithBaseURL(partition.origin() + "/host-marker", html, "text/html", "UTF-8", null);
            return inspector;
        });
        try {
            JSONObject evidence = observe(web, "workerPreventionMarker");
            if (!nonce.equals(evidence.optString("nonce")) || !partition.origin().equals(evidence.optString("origin"))
                    || !requests.isEmpty()) {
                throw new IllegalStateException("Untrusted marker readback");
            }
            report.put("marker", evidence.get("marker"));
            report.put("markerOrigin", evidence.getString("origin"));
        } finally {
            main(() -> { destroy(web); return null; });
        }
    }

    private SharedPreferences provenance() {
        return getSharedPreferences("worker-prevention", MODE_PRIVATE);
    }

    private String expectedProvenance(Partition partition) {
        return String.join("\n", PROVENANCE_VERSION, partition.origin(), POLICY,
            Integer.toString(android.os.Build.VERSION.SDK_INT), webViewVersion);
    }

    private boolean blockedByPolicy(JSONObject attempt, String origin, String workerPath) {
        if (attempt == null || !(attempt.opt("error") instanceof String error) || error.isEmpty()) return false;
        JSONObject violation = attempt.optJSONObject("violation");
        return origin.equals(attempt.opt("origin")) && "rejected".equals(attempt.opt("outcome"))
            && violation != null && violation.length() == 3
            && "worker-src".equals(violation.opt("directive"))
            && "enforce".equals(violation.opt("disposition"))
            && (origin + workerPath).equals(violation.opt("blockedURI"));
    }

    private boolean guardedObservation(Partition partition, JSONObject report) throws Exception {
        JSONObject guest = report.optJSONObject("guest");
        if (guest == null) return false;
        JSONObject attempts = guest.optJSONObject("attempts");
        JSONArray scopes = guest.optJSONArray("scopes");
        return partition.origin().equals(guest.optString("origin"))
            && partition.marker().equals(guest.optString("marker"))
            && guest.has("controller") && guest.isNull("controller")
            && scopes != null && scopes.length() == 0
            && report.getJSONArray("workerRequests").length() == 0
            && POLICY.equals(report.getJSONObject("documentPolicies").optString(ENTRY))
            && POLICY.equals(report.getJSONObject("documentPolicies").optString(FRAME))
            && attempts != null
            && blockedByPolicy(attempts.optJSONObject("main"), partition.origin(), ENTRY_WORKER)
            && blockedByPolicy(attempts.optJSONObject("frame"), partition.origin(), FRAME_WORKER);
    }

    private JSONObject seed(String key) throws Exception {
        Partition partition = partition(key);
        Profile profile = main(() -> {
            ProfileStore profiles = ProfileStore.getInstance();
            if (profiles.getAllProfileNames().contains(partition.profile())) {
                throw new IllegalStateException("The probe requires a fresh profile");
            }
            Profile created = profiles.getOrCreateProfile(partition.profile());
            created.getCookieManager().setAcceptCookie(false);
            return created;
        });
        JSONObject report = new JSONObject();
        report.put("profile", partition.profile());
        report.put("created", true);
        boolean deny = main(() -> !profile.getCookieManager().acceptCookie());
        report.put("cookieDeny", deny);
        if (!deny || main(() -> profile.getCookieManager().hasCookies())) {
            throw new IllegalStateException("The new fixture profile is not cookie-free under deny");
        }
        boolean guarded = "managed".equals(key) || "unconfirmed".equals(key);
        if ("unknown".equals(key)) {
            markerOnly(partition, true, report);
        } else {
            measureGuest(profile, partition, guarded, partition.marker(),
                AdmissionGate.Presence.EMPTY, new JSONArray(), report);
        }
        if ("unconfirmed".equals(key)) {
            JSONObject frame = report.getJSONObject("guest").getJSONObject("attempts").getJSONObject("frame");
            report.put("withheldFrameEvent", frame.remove("violation"));
        }
        boolean recorded = guarded && guardedObservation(partition, report);
        if (recorded && !provenance().edit().putString(partition.profile(), expectedProvenance(partition)).commit()) {
            throw new IllegalStateException("The fixture provenance record could not be persisted");
        }
        report.put("provenance", recorded);
        return report;
    }

    private void check(JSONObject report) throws Exception {
        Partition partition = partition(requestedCase);
        JSONArray events = new JSONArray();
        report.put("case", requestedCase);
        report.put("events", events);
        report.put("profile", partition.profile());
        Profile profile = main(() -> {
            Profile existing = ProfileStore.getInstance().getProfile(partition.profile());
            if (existing == null) throw new IllegalStateException("Expected the original profile");
            existing.getCookieManager().setAcceptCookie(false);
            return existing;
        });
        report.put("profilePresent", true);
        events.put("policy");
        boolean deny = main(() -> !profile.getCookieManager().acceptCookie());
        boolean cookies = main(() -> profile.getCookieManager().hasCookies());
        boolean recorded = expectedProvenance(partition).equals(provenance().getString(partition.profile(), null));
        report.put("cookieDeny", deny);
        report.put("cookiePresent", cookies);
        report.put("provenance", recorded);
        AdmissionGate.Presence verdict = AdmissionGate.Presence.UNKNOWN;
        if (deny && recorded) verdict = cookies ? AdmissionGate.Presence.PRESENT : AdmissionGate.Presence.EMPTY;
        report.put("verdict", verdict.name().toLowerCase(Locale.ROOT));
        events.put("decision");
        measureGuest(profile, partition, true, null, verdict, events, report);
        if (verdict != AdmissionGate.Presence.EMPTY) markerOnly(partition, false, report);
    }

    private void execute() {
        JSONObject report = new JSONObject();
        try {
            report.put("run", run);
            report.put("phase", phase);
            report.put("pid", android.os.Process.myPid());
            report.put("complete", false);
            if (run == null || !run.matches("[a-z0-9-]{1,28}") ||
                    !("seed".equals(phase) || ("check".equals(phase) && CASES.contains(requestedCase)))) {
                throw new IllegalArgumentException("Expected a valid run tag and phase");
            }
            webViewVersion = main(() -> {
                if (!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)) {
                    throw new UnsupportedOperationException("Named profiles unavailable");
                }
                return WebViewCompat.getCurrentWebViewPackage(this).versionName;
            });
            report.put("provider", webViewVersion);
            report.put("sdk", android.os.Build.VERSION.SDK_INT);
            report.put("release", android.os.Build.VERSION.RELEASE);
            registrationScript = asset("register.js");
            storeScript = asset("store.js");
            workerScript = asset("worker.js");
            if ("seed".equals(phase)) {
                JSONObject profiles = new JSONObject();
                report.put("profiles", profiles);
                for (String key : CASES) profiles.put(key, seed(key));
            } else {
                check(report);
            }
            report.put("complete", true);
        } catch (Exception error) {
            try {
                report.put("error", error.toString());
            } catch (org.json.JSONException encoding) {
                android.util.Log.e("WorkerPreventionProbe", "Unable to encode failure", encoding);
            }
        }
        try (FileOutputStream file = openFileOutput("report.json", MODE_PRIVATE)) {
            file.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) {
            android.util.Log.e("WorkerPreventionProbe", "Unable to write report", error);
        }
    }
}
