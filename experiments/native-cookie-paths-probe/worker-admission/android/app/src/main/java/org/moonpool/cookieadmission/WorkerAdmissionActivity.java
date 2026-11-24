package org.moonpool.cookieadmission;

import android.app.Activity;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.ServiceWorkerClient;
import android.webkit.ServiceWorkerController;
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
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

/** An Android-only pre-admission probe with host-injected content and owned worker controls. */
public final class WorkerAdmissionActivity extends Activity {
    private static final Set<String> CASES = Set.of("root", "offpath", "used", "fresh", "opaque");
    private static final String ENTRY = "/entry";
    private final Handler ui = new Handler(Looper.getMainLooper());
    private FrameLayout layout;
    private String run, phase, requestedCase;
    private String seedScript, workerScript, inspectScript, dataScript;

    private enum Mode { SEED, INSPECT, GUEST, DIAGNOSTIC }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        layout = new FrameLayout(this);
        setContentView(layout);
        run = getIntent().getStringExtra("run");
        phase = getIntent().getStringExtra("phase");
        requestedCase = getIntent().getStringExtra("case");
        new Thread(this::execute).start();
    }

    private static JSONObject object(Object... pairs) {
        JSONObject result = new JSONObject();
        try {
            for (int i = 0; i < pairs.length; i += 2) result.put((String) pairs[i], pairs[i + 1]);
            return result;
        } catch (Exception error) {
            throw new IllegalStateException(error);
        }
    }

    private String origin(String key) {
        return "https://mp-" + run + "-" + key + ".invalid";
    }

    private String partition(String key) {
        return "worker-admission-" + run + "-" + key;
    }

    private <T> T main(Callable<T> operation) throws Exception {
        FutureTask<T> task = new FutureTask<>(operation);
        ui.post(task);
        return task.get(12, TimeUnit.SECONDS);
    }

    private JSONObject observe(WebView web, String property) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(14);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> result = new CompletableFuture<>();
            ui.post(() -> web.evaluateJavascript("JSON.stringify(window." + property + " || null)", result::complete));
            String raw;
            try {
                raw = result.get(1, TimeUnit.SECONDS);
            } catch (TimeoutException provisionalNavigation) {
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

    private String asset(String name) throws Exception {
        try (InputStream input = getAssets().open(name); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int count;
            while ((count = input.read(buffer)) != -1) bytes.write(buffer, 0, count);
            return bytes.toString(StandardCharsets.UTF_8.name());
        }
    }

    private WebResourceResponse response(int status, String mime, String body) {
        return new WebResourceResponse(mime, "UTF-8", status, status == 200 ? "OK" : "Forbidden",
            Map.of("Cache-Control", "no-store"), new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));
    }

    private String page(String script, boolean inspection) {
        String policy = inspection
            ? "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; "
                + "frame-src about:; base-uri 'none'; form-action 'none'\">"
            : "";
        return "<!doctype html><meta charset=utf-8>" + policy + "<script>" + script + "</script>";
    }

    private boolean atOrigin(Uri uri, String expectedOrigin) {
        return expectedOrigin.equals(uri.getScheme() + "://" + uri.getEncodedAuthority());
    }

    private WebResourceResponse workerResponse(WebResourceRequest request, String expectedOrigin) {
        Uri uri = request.getUrl();
        String path = uri.getEncodedPath();
        if (atOrigin(uri, expectedOrigin) && "GET".equals(request.getMethod())
                && ("/worker.js".equals(path) || "/outside/worker.js".equals(path))) {
            return response(200, "text/javascript", workerScript);
        }
        return response(403, "text/plain", "");
    }

    private WebView create(String profile, String expectedOrigin, Mode mode, String seedPage,
                           ConcurrentLinkedQueue<String> inspectionRequests) {
        WebView web = new WebView(this);
        WebViewCompat.setProfile(web, profile);
        if (!profile.equals(WebViewCompat.getProfile(web).getName())) {
            throw new IllegalStateException("The WebView is bound to a different profile");
        }
        web.getSettings().setJavaScriptEnabled(mode != Mode.DIAGNOSTIC);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.getSettings().setBlockNetworkLoads(mode == Mode.INSPECT);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if (mode == Mode.INSPECT) return !("about".equals(url.getScheme()) || "data".equals(url.getScheme()));
                return !atOrigin(url, expectedOrigin);
            }

            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (mode == Mode.INSPECT) {
                    if ("data".equals(uri.getScheme()) || "about".equals(uri.getScheme())) return null;
                    inspectionRequests.add(uri.toString());
                    return response(403, "text/plain", "");
                }
                if (!atOrigin(uri, expectedOrigin) || !"GET".equals(request.getMethod())) {
                    return response(403, "text/plain", "");
                }
                String path = uri.getEncodedPath();
                if (mode == Mode.SEED && ("/seed".equals(path) || "/outside/seed".equals(path))) {
                    return response(200, "text/html", seedPage);
                }
                if (mode == Mode.SEED && ("/worker.js".equals(path) || "/outside/worker.js".equals(path))) {
                    return workerResponse(request, expectedOrigin);
                }
                if (mode == Mode.GUEST && ENTRY.equals(path)) {
                    return response(200, "text/html", page("window.workerGuest={marker:'guest',origin:window.origin}", true));
                }
                if (mode == Mode.DIAGNOSTIC && (ENTRY.equals(path) || "/outside/entry".equals(path))) {
                    return response(200, "text/html", "<!doctype html><title>c09-loader</title>");
                }
                return response(403, "text/plain", "");
            }
        });
        layout.addView(web);
        return web;
    }

    private void destroy(WebView web) {
        web.stopLoading();
        layout.removeView(web);
        web.destroy();
    }

    private JSONObject seed(String key) throws Exception {
        String origin = origin(key), profileName = partition(key);
        String scope = "root".equals(key) ? "/" : ("offpath".equals(key) ? "/outside/" : null);
        String source = "window.workerProbe=" + object("run", run, "scope", scope == null ? JSONObject.NULL : scope)
            + ";\n" + dataScript + "\n" + seedScript;
        WebView view = main(() -> {
            ProfileStore profiles = ProfileStore.getInstance();
            if (profiles.getAllProfileNames().contains(profileName)) {
                throw new IllegalStateException("The probe requires a fresh run tag");
            }
            Profile profile = profiles.getOrCreateProfile(profileName);
            profile.getCookieManager().setAcceptCookie(false);
            ServiceWorkerController service = profile.getServiceWorkerController();
            service.getServiceWorkerWebSettings().setBlockNetworkLoads(false);
            service.setServiceWorkerClient(new ServiceWorkerClient() {
                @Override public WebResourceResponse shouldInterceptRequest(WebResourceRequest request) {
                    return workerResponse(request, origin);
                }
            });
            WebView web = create(profileName, origin, Mode.SEED, page(source, false), null);
            web.loadUrl(origin + ("/outside/".equals(scope) ? "/outside/seed" : "/seed"));
            return web;
        });
        JSONObject marker = observe(view, "workerSeed");
        main(() -> { destroy(view); return null; });
        if (marker.has("error")) throw new IllegalStateException("Seed " + key + ": " + marker);
        return object("case", key, "profile", profileName, "seed", marker);
    }

    private boolean trusted(JSONObject proof, String origin, String nonce, ConcurrentLinkedQueue<String> requests) {
        return requests.isEmpty() && "host".equals(proof.optString("source")) && nonce.equals(proof.optString("nonce"))
            && origin.equals(proof.optString("origin")) && origin.equals(proof.optString("contextOrigin"))
            && proof.optBoolean("api") && !proof.has("error")
            && proof.optJSONArray("scopes") != null && proof.has("controller");
    }

    private void check(JSONObject report) throws Exception {
        String key = "opaque".equals(requestedCase) ? "used" : requestedCase;
        String origin = origin(key), profileName = partition(key);
        boolean fresh = "fresh".equals(key);
        JSONArray events = new JSONArray();
        report.put("events", events);
        report.put("profile", profileName);
        Profile profile = main(() -> {
            ProfileStore profiles = ProfileStore.getInstance();
            boolean present = profiles.getAllProfileNames().contains(profileName);
            report.put("profilePresent", present);
            if (present == fresh) throw new IllegalStateException("The stored profile does not match the case");
            Profile selected = profiles.getOrCreateProfile(profileName);
            selected.getCookieManager().setAcceptCookie(false);
            selected.getServiceWorkerController().getServiceWorkerWebSettings().setBlockNetworkLoads(true);
            return selected;
        });
        events.put("policy");
        ConcurrentLinkedQueue<String> requests = new ConcurrentLinkedQueue<>();
        String nonce = UUID.randomUUID().toString();
        String html = page("window.workerProbe=" + object("nonce", nonce) + ";\n" + dataScript + "\n" + inspectScript, true);
        WebView inspector = main(() -> create(profileName, origin, Mode.INSPECT, null, requests));
        JSONObject policy = main(() -> object("cookieDeny", !profile.getCookieManager().acceptCookie(),
            "workerNetworkBlocked", profile.getServiceWorkerController().getServiceWorkerWebSettings().getBlockNetworkLoads(),
            "browserNetworkBlocked", inspector.getSettings().getBlockNetworkLoads()));
        report.put("policy", policy);
        if (!policy.getBoolean("cookieDeny") || !policy.getBoolean("workerNetworkBlocked")
                || !policy.getBoolean("browserNetworkBlocked")) {
            main(() -> { destroy(inspector); return null; });
            throw new IllegalStateException("The inspection policies could not be verified");
        }
        events.put("inspect");
        main(() -> {
            String base = "opaque".equals(requestedCase) ? null : origin + ENTRY;
            inspector.loadDataWithBaseURL(base, html, "text/html", "UTF-8", null);
            return null;
        });
        JSONObject evidence;
        try {
            evidence = observe(inspector, "workerProbeResult");
        } catch (TimeoutException timeout) {
            evidence = object("error", timeout.toString());
        }
        main(() -> { destroy(inspector); return null; });
        report.put("proof", evidence);
        report.put("nonceMatches", nonce.equals(evidence.optString("nonce")));
        report.put("inspectionRequests", new JSONArray(requests));
        boolean cookiePresent = main(profile.getCookieManager()::hasCookies);
        report.put("cookiePresent", cookiePresent);
        AdmissionGate.Presence verdict = AdmissionGate.Presence.UNKNOWN;
        if (trusted(evidence, origin, nonce, requests)) {
            verdict = cookiePresent || evidence.getJSONArray("scopes").length() > 0 || !evidence.isNull("controller")
                ? AdmissionGate.Presence.PRESENT : AdmissionGate.Presence.EMPTY;
        }
        report.put("verdict", verdict.name().toLowerCase(java.util.Locale.ROOT));
        events.put("verdict");
        runGuest(report, events, profileName, origin, verdict);
        if ("root".equals(key) || "offpath".equals(key)) {
            report.put("diagnostic", diagnostic(profileName, origin, key));
        } else report.put("diagnostic", JSONObject.NULL);
    }

    private JSONObject diagnostic(String profileName, String origin, String key) throws Exception {
        WebView witness = main(() -> {
            WebView view = create(profileName, origin, Mode.DIAGNOSTIC, null, null);
            view.loadUrl(origin + ("offpath".equals(key) ? "/outside/entry" : ENTRY));
            return view;
        });
        try {
            String title = null;
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(6);
            while (System.nanoTime() < deadline) {
                title = main(witness::getTitle);
                if ("c09-worker".equals(title) || "c09-loader".equals(title)) break;
                Thread.sleep(100);
            }
            String nonce = UUID.randomUUID().toString();
            JSONObject observation = object("title", title == null ? JSONObject.NULL : title,
                "pageScriptsEnabled", main(() -> witness.getSettings().getJavaScriptEnabled()));
            if ("root".equals(key) && ("c09-worker".equals(title) || "c09-loader".equals(title))) {
                CompletableFuture<String> nativeEvaluation = new CompletableFuture<>();
                ui.post(() -> witness.evaluateJavascript(JSONObject.quote(nonce), nativeEvaluation::complete));
                boolean evaluated = false;
                try {
                    evaluated = JSONObject.quote(nonce).equals(nativeEvaluation.get(2, TimeUnit.SECONDS));
                } catch (TimeoutException deadlineExpired) {
                    observation.put("hostEvaluationError", deadlineExpired.toString());
                }
                observation.put("hostEvaluationReturned", evaluated);
                if (!evaluated) return observation;
                main(() -> {
                    witness.evaluateJavascript("window.workerProbe=" + object("nonce", nonce) + ";\n"
                        + dataScript + "\n" + inspectScript, null);
                    return null;
                });
                try {
                    JSONObject evaluation = observe(witness, "workerProbeResult");
                    observation.put("evaluation", evaluation);
                    observation.put("nonceMatches", nonce.equals(evaluation.optString("nonce")));
                } catch (TimeoutException timeout) {
                    observation.put("evaluationError", timeout.toString());
                }
            }
            return observation;
        } finally {
            main(() -> { destroy(witness); return null; });
        }
    }

    private void runGuest(JSONObject report, JSONArray events, String profile, String origin,
                          AdmissionGate.Presence verdict) throws Exception {
        int[] loads = {0};
        WebView guest = main(() -> {
            WebView view = create(profile, origin, Mode.GUEST, null, null);
            AdmissionGate gate = new AdmissionGate((name, complete) -> complete.accept(verdict));
            gate.admit("guest", () -> {
                loads[0]++;
                events.put("guest");
                view.loadUrl(origin + ENTRY);
            }, () -> {
                events.put("refuse");
                destroy(view);
            });
            return view;
        });
        report.put("guestLoads", loads[0]);
        if (loads[0] == 0) {
            report.put("guest", JSONObject.NULL);
            return;
        }
        report.put("guest", observe(guest, "workerGuest"));
        main(() -> { destroy(guest); return null; });
    }

    private void execute() {
        JSONObject report = object("run", run, "phase", phase, "pid", android.os.Process.myPid(), "complete", false);
        try {
            if (run == null || !run.matches("[a-z0-9-]{1,28}") ||
                    !("seed".equals(phase) || ("check".equals(phase) && CASES.contains(requestedCase)))) {
                throw new IllegalArgumentException("Expected a valid run tag and probe phase");
            }
            report.put("provider", main(() -> {
                if (!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)) {
                    throw new UnsupportedOperationException("Named profiles unavailable");
                }
                return WebViewCompat.getCurrentWebViewPackage(this).versionName;
            }));
            report.put("release", android.os.Build.VERSION.RELEASE);
            seedScript = asset("seed.js");
            workerScript = asset("worker.js");
            inspectScript = asset("inspect.js");
            dataScript = asset("store.js");
            if ("seed".equals(phase)) {
                JSONArray profiles = new JSONArray();
                report.put("profiles", profiles);
                for (String key : List.of("used", "root", "offpath")) profiles.put(seed(key));
            } else {
                report.put("case", requestedCase);
                check(report);
            }
            report.put("complete", true);
        } catch (Exception error) {
            try {
                report.put("error", error.toString());
            } catch (org.json.JSONException encoding) {
                android.util.Log.e("WorkerAdmissionProbe", "Unable to encode error", encoding);
            }
        }
        try (java.io.FileOutputStream out = openFileOutput("report.json", MODE_PRIVATE)) {
            out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) {
            android.util.Log.e("WorkerAdmissionProbe", "Unable to write report", error);
        }
    }

}
