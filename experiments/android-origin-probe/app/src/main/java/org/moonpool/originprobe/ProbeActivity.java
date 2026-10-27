package org.moonpool.originprobe;

import android.app.Activity;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.webkit.WebViewAssetLoader;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Platform observations only: no guest-callable native object or Moonpool kernel. */
public final class ProbeActivity extends Activity {
    private final Handler main = new Handler(Looper.getMainLooper());
    private final JSONArray events = new JSONArray();
    private final JSONArray samples = new JSONArray();
    private final List<Step> steps = new ArrayList<>();
    private JSONObject report;
    private LinearLayout views;
    private TextView status;
    private WebView a;
    private WebView b;
    private String profile;
    private String phase;
    private int stepIndex;
    private boolean retired;

    interface Step { void run(Runnable next); }
    interface Value { void accept(Object value); }

    private static JSONObject json(Object... pairs) {
        JSONObject value = new JSONObject();
        try {
            for (int i = 0; i < pairs.length; i += 2) value.put((String)pairs[i], pairs[i + 1]);
        } catch (Exception error) { throw new IllegalStateException(error); }
        return value;
    }

    private synchronized void event(String type, Object... pairs) {
        JSONObject value = json(pairs);
        try { value.put("type", type); events.put(value); }
        catch (Exception error) { throw new IllegalStateException(error); }
    }

    private String host(String app) {
        return "https-control".equals(profile) ? "com.example.probe." + app + ".test" : "com.example.probe." + app;
    }

    private String url(String app, String page, boolean seed) {
        return ("https-control".equals(profile) ? "https" : "moonpool") + "://" + host(app)
            + "/assets/" + page + "?profile=" + profile + "&seed=" + seed;
    }

    private WebResourceResponse response(int code, String text) {
        return new WebResourceResponse("text/plain", "UTF-8", code, code == 404 ? "Not Found" : "Blocked",
            Map.of(), new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)));
    }

    private WebResourceResponse asset(String app, String path) {
        // Each fixed host has a fixed root. Decoded traversal never selects another package.
        if (path.isEmpty() || path.contains("..") || path.contains("\\") || path.startsWith("/")) {
            return response(404, "Outside package");
        }
        String resource = "second.html".equals(path) ? "index.html" : path;
        String mime = resource.endsWith(".html") ? "text/html" : resource.endsWith(".js") ? "text/javascript"
            : resource.endsWith(".css") ? "text/css" : resource.endsWith(".svg") ? "image/svg+xml" : "application/json";
        String source = List.of("probe.js", "style.css", "marker.svg").contains(resource)
            ? "common/" + resource : "apps/" + app + "/" + resource;
        try { return new WebResourceResponse(mime, "UTF-8", getAssets().open(source)); }
        catch (Exception error) { return response(404, "Missing bundled resource"); }
    }

    private WebViewAssetLoader loader(String app) {
        return new WebViewAssetLoader.Builder().setDomain(host(app))
            .addPathHandler("/assets/", path -> asset(app, path)).build();
    }

    private WebView view(String owner) {
        WebView web = new WebView(this);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.setWebChromeClient(new WebChromeClient());
        WebViewAssetLoader loaderA = loader("a");
        WebViewAssetLoader loaderB = loader("b");
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest request) {
                Uri uri = request.getUrl();
                event("request", "view", owner, "url", uri.toString(), "mainFrame", request.isForMainFrame(),
                    "originHeader", request.getRequestHeaders().getOrDefault("Origin", "<absent>"));
                if ("127.0.0.1".equals(uri.getHost()) && uri.getPort() == 8877 && "http".equals(uri.getScheme())) {
                    event("network-control", "url", uri.toString());
                    return null; // Explicit loopback-only network fallthrough control.
                }
                if ("intercept-custom".equals(profile) && "moonpool".equals(uri.getScheme())) {
                    String app = host("a").equals(uri.getHost()) ? "a" : host("b").equals(uri.getHost()) ? "b" : null;
                    String path = uri.getPath();
                    if (app != null && path != null && path.startsWith("/assets/")) return asset(app, path.substring(8));
                    return response(404, "Unknown app or package path");
                }
                WebResourceResponse result = loaderA.shouldInterceptRequest(uri);
                if (result == null) result = loaderB.shouldInterceptRequest(uri);
                if (result != null) return result;
                event("loader-miss", "url", uri.toString());
                if ("moonpool".equals(uri.getScheme())) return null; // Observe official custom-scheme failure.
                return response(451, "No network fallback for unmapped hosts or paths");
            }
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                event("navigation", "view", owner, "url", r.getUrl().toString(), "mainFrame", r.isForMainFrame());
                return false; // Research without a bridge; containment is a later approved contract.
            }
            @Override public void onPageStarted(WebView v, String u, Bitmap icon) { event("started", "view", owner, "url", u); }
            @Override public void onPageFinished(WebView v, String u) { event("finished", "view", owner, "url", u); }
            @Override public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) {
                event("load-error", "view", owner, "url", r.getUrl().toString(), "mainFrame", r.isForMainFrame(),
                    "code", e.getErrorCode(), "description", e.getDescription().toString());
            }
        });
        views.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        return web;
    }

    private void poll(WebView web, int remaining, Value next) {
        web.evaluateJavascript("JSON.stringify(window.t23Report || null)", raw -> {
            try {
                Object outer = new JSONTokener(raw).nextValue();
                Object result = outer instanceof String ? new JSONTokener((String)outer).nextValue() : JSONObject.NULL;
                if (result instanceof JSONObject) { next.accept(result); return; }
            } catch (Exception error) { event("poll-error", "message", error.toString()); }
            if (remaining == 0) {
                next.accept(json("unavailable", true, "nativeUrl", String.valueOf(web.getUrl()), "reason", "No fixture report before deadline"));
            } else main.postDelayed(() -> poll(web, remaining - 1, next), 100);
        });
    }

    private void sample(String label, WebView web, Runnable next) {
        status.setText("T23 " + profile + " / " + phase + " / " + label);
        poll(web, 100, value -> {
            samples.put(json("label", label, "nativeUrl", String.valueOf(web.getUrl()), "observation", value));
            next.run();
        });
    }

    private void load(String label, WebView web, String target, Runnable next) {
        web.evaluateJavascript("window.t23Report = null", ignored -> {
            web.loadUrl(target);
            main.postDelayed(() -> sample(label, web, next), 300);
        });
    }

    private void recollect(String label, WebView web, Runnable next) {
        web.evaluateJavascript("window.t23Report = null; void window.t23Collect(false)", ignored -> sample(label, web, next));
    }

    private void next() {
        if (retired) return;
        if (stepIndex < steps.size()) { steps.get(stepIndex++).run(this::next); return; }
        try {
            report.put("samples", samples);
            synchronized (this) { report.put("events", events); }
            report.put("complete", true);
            try (FileOutputStream out = new FileOutputStream(new File(getFilesDir(), "report.json"))) {
                out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
            }
            status.setText("T23 " + profile + " / " + phase + " complete — " + samples.length() + " observations");
        } catch (Exception error) { status.setText("Report failure: " + error); }
    }

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        profile = getIntent().getStringExtra("profile");
        phase = getIntent().getStringExtra("phase");
        if (!List.of("asset-loader-custom", "intercept-custom", "https-control").contains(profile)) throw new IllegalArgumentException("Unknown profile");
        if (!List.of("seed", "restart").contains(phase)) throw new IllegalArgumentException("Unknown phase");
        new File(getFilesDir(), "report.json").delete();
        views = new LinearLayout(this); views.setOrientation(LinearLayout.VERTICAL);
        views.setPadding(8, 70, 8, 35);
        status = new TextView(this); status.setTextSize(17); views.addView(status);
        setContentView(views);
        report = json("profile", profile, "phase", phase, "sdk", android.os.Build.VERSION.SDK_INT,
            "os", android.os.Build.VERSION.RELEASE, "webView", WebView.getCurrentWebViewPackage().versionName,
            "webViewPackage", WebView.getCurrentWebViewPackage().packageName);
        try {
            WebResourceResponse custom = loader("a").shouldInterceptRequest(Uri.parse("moonpool://" + host("a") + "/assets/index.html"));
            report.put("officialLoaderAcceptsCustom", custom != null);
            if (custom != null && custom.getData() != null) custom.getData().close();
        } catch (Exception error) { event("direct-loader-error", "message", error.toString()); }
        a = view("a"); b = view("b");
        boolean seed = "seed".equals(phase);
        steps.add(done -> load("initial-a", a, url("a", "index.html", seed), done));
        steps.add(done -> load("initial-b", b, url("b", "index.html", seed), done));
        if (!"asset-loader-custom".equals(profile)) {
            steps.add(done -> recollect("a-after-b", a, done));
            steps.add(done -> recollect("b-after-a", b, done));
            steps.add(done -> {
                WebView same = view("a-second-instance");
                load("same-app-second-instance", same, url("a", "index.html", false), () -> {
                    views.removeView(same); same.destroy(); done.run();
                });
            });
            steps.add(done -> { a.reload(); main.postDelayed(() -> sample("reload-a", a, done), 300); });
            steps.add(done -> {
                views.removeView(a); a.destroy(); a = view("a-recreated");
                load("recreate-a", a, url("a", "index.html", false), done);
            });
            steps.add(done -> load("same-app-navigation", a, url("a", "second.html", false), done));
            steps.add(done -> load("foreign-app-navigation", a, url("b", "index.html", false), done));
            steps.add(done -> load("external-navigation", a, "http://127.0.0.1:8877/external", done));
            steps.add(done -> load("return-to-a", a, url("a", "index.html", false), done));
        }
        next();
    }

    @Override public void onDestroy() {
        retired = true;
        main.removeCallbacksAndMessages(null);
        if (a != null) { views.removeView(a); a.destroy(); }
        if (b != null) { views.removeView(b); b.destroy(); }
        super.onDestroy();
    }
}
