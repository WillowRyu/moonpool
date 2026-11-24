package org.moonpool.workercontexts;

import android.app.Activity;
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
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

public final class WorkerContextsActivity extends Activity {
    private static final String ENTRY = "/entry";
    private static final String CSP = "Content-Security-Policy";
    private static final String POLICY = "worker-src 'none'";
    private final Handler ui = new Handler(Looper.getMainLooper());
    private FrameLayout views;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        views = new FrameLayout(this);
        setContentView(views);
        String run = getIntent().getStringExtra("run");
        new Thread(() -> collect(run)).start();
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

    private JSONObject observe(WebView view) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(22);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> evaluated = new CompletableFuture<>();
            ui.post(() -> view.evaluateJavascript("JSON.stringify(window.workerContextsResult || null)", evaluated::complete));
            try {
                String raw = evaluated.get(1, TimeUnit.SECONDS);
                if (new JSONTokener(raw == null ? "null" : raw).nextValue() instanceof String value
                        && new JSONTokener(value).nextValue() instanceof JSONObject evidence) {
                    return evidence;
                }
            } catch (TimeoutException pending) {
                continue;
            }
            Thread.sleep(100);
        }
        throw new TimeoutException("No worker context observations");
    }

    private WebResourceResponse response(int status, String mime, String body, String policy) {
        Map<String, String> headers = policy.isEmpty()
            ? Map.of("Cache-Control", "no-store")
            : Map.of("Cache-Control", "no-store", CSP, policy);
        return new WebResourceResponse(mime, "UTF-8", status, status == 200 ? "OK" : "Forbidden",
            headers, new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));
    }

    private boolean atOrigin(WebResourceRequest request, String origin) {
        return origin.equals(request.getUrl().getScheme() + "://" + request.getUrl().getEncodedAuthority());
    }

    private boolean inheritedPage(WebResourceRequest request) {
        String url = request.getUrl().toString();
        return "about:blank".equals(url) || "about:srcdoc".equals(url);
    }

    private WebResourceResponse scriptResponse(WebResourceRequest request, String origin,
            Map<String, String> scripts, ConcurrentLinkedQueue<String> receipts) {
        String path = request.getUrl().getEncodedPath();
        if (atOrigin(request, origin) && "GET".equals(request.getMethod()) && scripts.containsKey(path)) {
            receipts.add(path);
            return response(200, "text/javascript", scripts.get(path), "");
        }
        return response(403, "text/plain", "", "");
    }

    private JSONObject measure(String run, String mode, String html, Map<String, String> scripts) throws Exception {
        String profile = "worker-contexts-" + run + "-" + mode;
        String origin = "https://mp-" + run + "-" + mode + ".invalid";
        String policy = "guarded".equals(mode) ? POLICY : "";
        ConcurrentLinkedQueue<String> receipts = new ConcurrentLinkedQueue<>();
        AtomicReference<String> observedPolicy = new AtomicReference<>();
        WebView view = main(() -> {
            ProfileStore profiles = ProfileStore.getInstance();
            if (profiles.getAllProfileNames().contains(profile)) {
                throw new IllegalStateException("The fixture requires an unused named profile");
            }
            Profile created = profiles.getOrCreateProfile(profile);
            created.getCookieManager().setAcceptCookie(false);
            if (created.getCookieManager().acceptCookie()) {
                throw new IllegalStateException("Cookie deny did not take effect");
            }
            var workers = created.getServiceWorkerController();
            workers.getServiceWorkerWebSettings().setBlockNetworkLoads(false);
            workers.setServiceWorkerClient(new ServiceWorkerClient() {
                @Override public WebResourceResponse shouldInterceptRequest(WebResourceRequest request) {
                    return scriptResponse(request, origin, scripts, receipts);
                }
            });
            WebView web = new WebView(this);
            WebViewCompat.setProfile(web, profile);
            if (!profile.equals(WebViewCompat.getProfile(web).getName())) {
                throw new IllegalStateException("Unexpected WebView profile");
            }
            web.getSettings().setJavaScriptEnabled(true);
            web.getSettings().setDomStorageEnabled(true);
            web.getSettings().setAllowFileAccess(false);
            web.getSettings().setAllowContentAccess(false);
            web.setWebViewClient(new WebViewClient() {
                @Override public boolean shouldOverrideUrlLoading(WebView ignored, WebResourceRequest request) {
                    return !(atOrigin(request, origin) || inheritedPage(request));
                }

                @Override public WebResourceResponse shouldInterceptRequest(WebView ignored, WebResourceRequest request) {
                    if (inheritedPage(request)) return null;
                    if (atOrigin(request, origin) && "GET".equals(request.getMethod())
                            && ENTRY.equals(request.getUrl().getEncodedPath())) {
                        WebResourceResponse document = response(200, "text/html", html, policy);
                        receipts.add(ENTRY);
                        observedPolicy.set(document.getResponseHeaders().getOrDefault(CSP, ""));
                        return document;
                    }
                    return scriptResponse(request, origin, scripts, receipts);
                }
            });
            views.addView(web);
            web.loadUrl(origin + ENTRY);
            return web;
        });
        try {
            JSONObject page = observe(view);
            return new JSONObject().put("profile", profile).put("created", true)
                .put("policy", observedPolicy.get()).put("requests", new JSONArray(receipts)).put("page", page);
        } finally {
            main(() -> {
                view.stopLoading();
                views.removeView(view);
                view.destroy();
                return null;
            });
        }
    }

    private void collect(String run) {
        JSONObject report = new JSONObject();
        try {
            report.put("run", run).put("pid", android.os.Process.myPid()).put("complete", false);
            if (run == null || !run.matches("[a-z0-9-]{1,28}")) {
                throw new IllegalArgumentException("Expected a valid run tag");
            }
            report.put("provider", main(() -> {
                if (!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)) {
                    throw new UnsupportedOperationException("Named profiles unavailable");
                }
                return WebViewCompat.getCurrentWebViewPackage(this).versionName;
            }));
            report.put("sdk", android.os.Build.VERSION.SDK_INT).put("release", android.os.Build.VERSION.RELEASE);
            String html = "<!doctype html><meta charset=utf-8><title>Worker contexts</title>"
                + "<body><script src=\"/probe.js\"></script>";
            Map<String, String> scripts = Map.of("/probe.js", asset("probe.js"),
                "/dedicated.js", asset("dedicated.js"), "/service.js", asset("service.js"));
            JSONObject samples = new JSONObject();
            report.put("samples", samples);
            samples.put("control", measure(run, "control", html, scripts));
            samples.put("guarded", measure(run, "guarded", html, scripts));
            report.put("complete", true);
        } catch (Exception failure) {
            try {
                report.put("error", failure.toString());
            } catch (org.json.JSONException encoding) {
                android.util.Log.e("WorkerContextsProbe", "Unable to encode failure", encoding);
            }
        }
        try (FileOutputStream file = openFileOutput("report.json", MODE_PRIVATE)) {
            file.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception failure) {
            android.util.Log.e("WorkerContextsProbe", "Unable to write results", failure);
        }
    }
}
