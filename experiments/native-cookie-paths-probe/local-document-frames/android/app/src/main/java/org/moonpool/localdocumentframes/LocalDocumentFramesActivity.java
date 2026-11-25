package org.moonpool.localdocumentframes;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
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

public final class LocalDocumentFramesActivity extends Activity {
    private static final List<String> FRAME_KINDS = List.of("same", "blob", "data");
    private static final List<String> INHERITED_FRAME_KINDS = List.of("blank", "srcdoc");
    private static final String CSP = "Content-Security-Policy";
    private static final String SAME_FRAME = "/same-frame";
    private static final String BEFORE_BLANK = "/before-blank";
    private static final String BEFORE_BLANK_HTML = "<!doctype html><p id=\"before-blank\">Before navigation</p>";
    private static final String POLICY = "default-src 'none'; script-src 'self' 'unsafe-inline'; "
        + "frame-src 'self'; worker-src 'none'; base-uri 'none'";
    private final Handler ui = new Handler(Looper.getMainLooper());
    private FrameLayout views;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        views = new FrameLayout(this);
        setContentView(views);
        String run = getIntent().getStringExtra("run");
        String frameSource = getIntent().getStringExtra("frameSource");
        String documentSet = getIntent().getStringExtra("documentSet");
        new Thread(() -> collect(run, frameSource == null ? "self" : frameSource,
            documentSet == null ? "local" : documentSet)).start();
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
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(31);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> evaluated = new CompletableFuture<>();
            ui.post(() -> view.evaluateJavascript("JSON.stringify(window.localFramesResult || null)", evaluated::complete));
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

    private boolean generatedSubframe(WebResourceRequest request) {
        String scheme = request.getUrl().getScheme();
        String url = request.getUrl().toString();
        return !request.isForMainFrame() && ("blob".equals(scheme) || "data".equals(scheme)
            || "about:blank".equals(url) || "about:srcdoc".equals(url));
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

    private JSONObject measure(String run, String mode, String frameSource, List<String> kinds, String html,
            Map<String, String> scripts) throws Exception {
        String profile = "local-document-frames-" + run + "-" + mode;
        String origin = "https://mp-" + run + "-" + mode + ".invalid";
        String guardedPolicy = "origin".equals(frameSource) ? POLICY.replace("frame-src 'self'", "frame-src " + origin) : POLICY;
        String policy = "guarded".equals(mode) ? guardedPolicy : "";
        Profile created = main(() -> {
            ProfileStore profiles = ProfileStore.getInstance();
            if (profiles.getAllProfileNames().contains(profile)) {
                throw new IllegalStateException("The fixture requires an unused named profile");
            }
            Profile selected = profiles.getOrCreateProfile(profile);
            selected.getCookieManager().setAcceptCookie(false);
            if (selected.getCookieManager().acceptCookie()) {
                throw new IllegalStateException("Cookie deny did not take effect");
            }
            return selected;
        });
        JSONObject frames = new JSONObject();
        for (String kind : kinds) {
            frames.put(kind, measureFrame(profile, origin, kind, policy, html, scripts));
        }
        return new JSONObject().put("profile", profile).put("created", true).put("frames", frames)
            .put("cookieDeny", main(() -> !created.getCookieManager().acceptCookie()));
    }

    private JSONObject measureFrame(String profile, String origin, String kind, String policy,
            String html, Map<String, String> scripts) throws Exception {
        String entryPath = "/entry/" + kind;
        ConcurrentLinkedQueue<String> receipts = new ConcurrentLinkedQueue<>();
        AtomicReference<String> observedPolicy = new AtomicReference<>();
        AtomicReference<String> previousDocumentPolicy = new AtomicReference<>();
        WebView view = main(() -> {
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
                    return !(atOrigin(request, origin) || generatedSubframe(request));
                }

                @Override public WebResourceResponse shouldInterceptRequest(WebView ignored, WebResourceRequest request) {
                    if (generatedSubframe(request)) return null;
                    String path = request.getUrl().getEncodedPath();
                    boolean entry = request.isForMainFrame() && entryPath.equals(path);
                    boolean sameFrame = "same".equals(kind) && !request.isForMainFrame() && SAME_FRAME.equals(path);
                    boolean beforeBlank = "blank-navigation".equals(kind) && !request.isForMainFrame() && BEFORE_BLANK.equals(path);
                    if (atOrigin(request, origin) && "GET".equals(request.getMethod()) && (entry || sameFrame || beforeBlank)) {
                        WebResourceResponse document = beforeBlank
                            ? response(200, "text/html", BEFORE_BLANK_HTML, "")
                            : response(200, "text/html", html, policy);
                        receipts.add(path);
                        if (entry) observedPolicy.set(document.getResponseHeaders().getOrDefault(CSP, ""));
                        if (beforeBlank) previousDocumentPolicy.set(document.getResponseHeaders().getOrDefault(CSP, ""));
                        return document;
                    }
                    return scriptResponse(request, origin, scripts, receipts);
                }
            });
            views.addView(web);
            web.loadUrl(origin + entryPath);
            return web;
        });
        try {
            JSONObject page = observe(view);
            JSONObject result = new JSONObject().put("parentUrl", main(view::getUrl)).put("policy", observedPolicy.get())
                .put("requests", new JSONArray(receipts)).put("page", page);
            if ("blank-navigation".equals(kind)) result.put("previousDocumentPolicy", previousDocumentPolicy.get());
            return result;
        } finally {
            main(() -> {
                view.stopLoading();
                views.removeView(view);
                view.destroy();
                return null;
            });
        }
    }

    private void collect(String run, String frameSource, String documentSet) {
        JSONObject report = new JSONObject();
        try {
            report.put("run", run).put("pid", android.os.Process.myPid()).put("complete", false)
                .put("frameSource", frameSource).put("documentSet", documentSet);
            if (run == null || !run.matches("[a-z0-9-]{1,28}")) {
                throw new IllegalArgumentException("Expected a valid run tag");
            }
            if (!"self".equals(frameSource) && !"origin".equals(frameSource)) {
                throw new IllegalArgumentException("Expected a valid frame source");
            }
            List<String> kinds = switch (documentSet) {
                case "local" -> FRAME_KINDS;
                case "inherited" -> INHERITED_FRAME_KINDS;
                case "navigation" -> List.of("blank-navigation");
                default -> throw new IllegalArgumentException("Expected a valid document set");
            };
            report.put("provider", main(() -> {
                if (!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)) {
                    throw new UnsupportedOperationException("Named profiles unavailable");
                }
                return WebViewCompat.getCurrentWebViewPackage(this).versionName;
            }));
            report.put("sdk", android.os.Build.VERSION.SDK_INT).put("release", android.os.Build.VERSION.RELEASE);
            String html = "<!doctype html><meta charset=utf-8><title>Local document frames</title>"
                + "<body><script src=\"/probe.js\"></script>";
            Map<String, String> scripts = Map.of("/probe.js", asset("probe.js"),
                "/worker.js", asset("worker.js"));
            JSONObject samples = new JSONObject();
            report.put("samples", samples);
            samples.put("control", measure(run, "control", frameSource, kinds, html, scripts));
            samples.put("guarded", measure(run, "guarded", frameSource, kinds, html, scripts));
            report.put("complete", true);
        } catch (Exception failure) {
            try {
                report.put("error", failure.toString());
            } catch (org.json.JSONException encoding) {
                android.util.Log.e("LocalDocumentFramesProbe", "Unable to encode failure", encoding);
            }
        }
        try (FileOutputStream file = openFileOutput("report.json", MODE_PRIVATE)) {
            file.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception failure) {
            android.util.Log.e("LocalDocumentFramesProbe", "Unable to write results", failure);
        }
    }
}
