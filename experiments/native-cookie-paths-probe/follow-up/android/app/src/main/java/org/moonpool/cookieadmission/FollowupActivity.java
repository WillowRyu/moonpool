package org.moonpool.cookieadmission;

import android.app.Activity;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;
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
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import okhttp3.HttpUrl;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

/** An owned loader and a positive retained-worker control in one native profile. */
public final class FollowupActivity extends Activity {
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final AtomicInteger entryLoads = new AtomicInteger();
    private FrameLayout layout;
    private String run, base, origin, profileName;
    private String images, seed, script;
    private StaticImages remote;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        layout = new FrameLayout(this);
        setContentView(layout);
        run = getIntent().getStringExtra("run");
        base = getIntent().getStringExtra("base");
        new Thread(this::execute).start();
    }

    private static JSONObject object(Object... pairs) {
        JSONObject value = new JSONObject();
        try {
            for (int i = 0; i < pairs.length; i += 2) value.put((String) pairs[i], pairs[i + 1]);
            return value;
        } catch (Exception error) {
            throw new IllegalStateException(error);
        }
    }

    private <T> T main(Callable<T> job) throws Exception {
        FutureTask<T> task = new FutureTask<>(job);
        ui.post(task);
        return task.get(12, TimeUnit.SECONDS);
    }

    private JSONObject observe(WebView web, String property) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(14);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> value = new CompletableFuture<>();
            ui.post(() -> web.evaluateJavascript("JSON.stringify(window." + property + " || null)", value::complete));
            String raw;
            try {
                raw = value.get(1, TimeUnit.SECONDS);
            } catch (TimeoutException provisionalNavigation) {
                continue;
            }
            Object encoded = new JSONTokener(raw == null ? "null" : raw).nextValue();
            if (encoded instanceof String json && new JSONTokener(json).nextValue() instanceof JSONObject data) {
                return data;
            }
            Thread.sleep(100);
        }
        throw new IllegalStateException("Deadline waiting for " + property);
    }

    private String asset(String name) throws Exception {
        try (InputStream input = getAssets().open(name); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int count;
            while ((count = input.read(buffer)) != -1) bytes.write(buffer, 0, count);
            return bytes.toString(StandardCharsets.UTF_8.name());
        }
    }

    private WebResourceResponse response(int status, String mime, byte[] data) {
        return new WebResourceResponse(mime, "UTF-8", status, status == 200 ? "OK" : "Forbidden",
            Map.of("Cache-Control", "no-store"), new ByteArrayInputStream(data));
    }

    private WebResourceResponse text(String mime, String body) {
        return response(200, mime, body.getBytes(StandardCharsets.UTF_8));
    }

    private WebResourceResponse denied() {
        return response(403, "text/plain", new byte[0]);
    }

    private boolean local(Uri uri) {
        return origin.equals(uri.getScheme() + "://" + uri.getEncodedAuthority());
    }

    private WebView create(boolean workerFixture) throws Exception {
        return main(() -> {
            WebView web = new WebView(this);
            WebViewCompat.setProfile(web, profileName);
            web.getSettings().setJavaScriptEnabled(true);
            web.getSettings().setDomStorageEnabled(true);
            web.getSettings().setAllowFileAccess(false);
            web.getSettings().setAllowContentAccess(false);
            web.setWebViewClient(new WebViewClient() {
                @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    return !local(request.getUrl());
                }

                @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                    Uri url = request.getUrl();
                    if (!local(url) || !"GET".equals(request.getMethod())) return denied();
                    String path = url.getEncodedPath();
                    if (workerFixture) {
                        if ("/worker/seed".equals(path)) return text("text/html", seed);
                        if ("/worker/sw.js".equals(path)) return text("text/javascript", script);
                        if ("/worker/entry".equals(path)) {
                            entryLoads.incrementAndGet();
                            return text("text/html", "<script>window.c09Worker={entry:'native-loader'}</script>");
                        }
                        return denied();
                    }
                    if ("/images".equals(path)) {
                        return text("text/html", "<!doctype html><meta charset=utf-8>"
                            + "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; "
                            + "script-src 'unsafe-inline'; img-src 'self'; worker-src 'none'\"><script>"
                            + images + "</script>");
                    }
                    if (!path.startsWith("/image/")) return denied();
                    try {
                        byte[] image = remote.get(path.substring("/image/".length()));
                        return image == null ? denied() : response(200, "image/gif", image);
                    } catch (java.io.IOException network) {
                        return denied();
                    }
                }
            });
            layout.addView(web);
            return web;
        });
    }

    private void destroy(WebView web) {
        web.stopLoading();
        layout.removeView(web);
        web.destroy();
    }

    private void testImages(Profile profile, JSONObject report) throws Exception {
        CookieManager cookies = profile.getCookieManager();
        WebView page = create(false);
        JSONObject admission = main(() -> {
            cookies.setAcceptCookie(false);
            boolean policy = !cookies.acceptCookie();
            boolean empty = !cookies.hasCookies();
            AdmissionGate gate = new AdmissionGate((name, done) -> done.accept(policy && empty
                ? AdmissionGate.Presence.EMPTY : AdmissionGate.Presence.UNKNOWN));
            gate.admit("images", () -> page.loadUrl(origin + "/images"), () -> destroy(page));
            return object("policyDisallowed", policy, "empty", empty);
        });
        report.put("admission", admission);
        if (!admission.getBoolean("empty") || !admission.getBoolean("policyDisallowed")) {
            throw new IllegalStateException("Image admission refused");
        }
        report.put("guest", observe(page, "c09Images"));
        admission.put("afterEmpty", main(() -> !cookies.hasCookies()));
        main(() -> { destroy(page); return null; });
    }

    private void testWorker(Profile profile, JSONObject report) throws Exception {
        ServiceWorkerController worker = profile.getServiceWorkerController();
        JSONObject witness = object("state", "unverified");
        report.put("worker", witness);
        WebView seedView = create(true);
        main(() -> {
            worker.getServiceWorkerWebSettings().setBlockNetworkLoads(false);
            worker.setServiceWorkerClient(new ServiceWorkerClient() {
                @Override public WebResourceResponse shouldInterceptRequest(WebResourceRequest request) {
                    Uri uri = request.getUrl();
                    return local(uri) && "/worker/sw.js".equals(uri.getEncodedPath())
                        ? text("text/javascript", script) : null;
                }
            });
            seedView.loadUrl(origin + "/worker/seed");
            return null;
        });
        JSONObject installed = observe(seedView, "c09Worker");
        witness.put("seed", installed);
        if (!installed.optBoolean("registered") || !"reached".equals(installed.optString("network"))) {
            throw new IllegalStateException("Worker seed or network control failed: " + installed);
        }
        witness.put("registered", true);
        witness.put("scope", installed.getString("scope"));
        witness.put("networkBlocked", main(() -> {
            destroy(seedView);
            worker.getServiceWorkerWebSettings().setBlockNetworkLoads(true);
            return worker.getServiceWorkerWebSettings().getBlockNetworkLoads();
        }));
        witness.put("seedViewDestroyed", true);
        // Diagnostic load in the owned test app before testing the gate's refusal.
        WebView diagnostic = create(true);
        main(() -> { diagnostic.loadUrl(origin + "/worker/entry"); return null; });
        JSONObject retained = observe(diagnostic, "c09Worker");
        witness.put("entry", retained.optString("entry"));
        witness.put("workerFetch", retained.optString("workerFetch"));
        witness.put("retainedRegistration", retained.optBoolean("retainedRegistration"));
        witness.put("loaderEntries", entryLoads.get());
        if (!retained.optBoolean("retainedRegistration")) {
            throw new IllegalStateException("Retained worker witness missing: " + retained);
        }
        witness.put("state", "retained");
        main(() -> { destroy(diagnostic); return null; });

        WebView candidate = create(false);
        int[] loads = {0};
        main(() -> {
            AdmissionGate gate = new AdmissionGate((name, done) -> done.accept(AdmissionGate.Presence.UNKNOWN));
            gate.admit("retained worker", () -> {
                loads[0]++;
                candidate.loadUrl(origin + "/images");
            }, () -> destroy(candidate));
            return null;
        });
        witness.put("guestLoads", loads[0]);
        witness.put("admission", loads[0] == 0 ? "refused" : "admitted");
    }

    private void execute() {
        JSONArray errors = new JSONArray();
        JSONObject report = object("platform", "android", "run", run, "complete", false, "errors", errors);
        try {
            HttpUrl endpoint = HttpUrl.parse(base);
            if (run == null || !run.matches("[a-z0-9-]{1,48}") || endpoint == null || !endpoint.isHttps()
                    || !"localhost".equals(endpoint.host()) || !base.equals("https://localhost:" + endpoint.port())) {
                throw new IllegalArgumentException("Expected the owned loopback fixture");
            }
            origin = "https://mp-" + run + ".invalid";
            profileName = "c09-follow-up-" + run;
            images = asset("images.js");
            seed = asset("worker-seed.html");
            script = "self.c09Config=" + object("run", run, "base", base, "entry", asset("worker-entry.html"))
                + ";\n" + asset("worker.js");
            remote = new StaticImages(endpoint, run);
            Profile profile = main(() -> {
                if (!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)) {
                    throw new UnsupportedOperationException("Named profiles unavailable");
                }
                return ProfileStore.getInstance().getOrCreateProfile(profileName);
            });
            report.put("release", android.os.Build.VERSION.RELEASE);
            report.put("provider", main(() -> WebViewCompat.getCurrentWebViewPackage(this).versionName));
            testImages(profile, report);
            testWorker(profile, report);
            report.put("complete", true);
        } catch (Exception error) {
            errors.put(error.toString());
        }
        try (java.io.FileOutputStream out = openFileOutput("report.json", MODE_PRIVATE)) {
            out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) {
            android.util.Log.e("CookiePathsFollowup", "Unable to write report", error);
        }
    }
}
