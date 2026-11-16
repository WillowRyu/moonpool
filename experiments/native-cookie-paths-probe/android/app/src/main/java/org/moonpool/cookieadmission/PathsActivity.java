package org.moonpool.cookieadmission;

import android.app.Activity;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import androidx.webkit.CookieManagerCompat;
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
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

/** Owned WebView fixture. Trusted control loads and admitted guest views use different profiles. */
public final class PathsActivity extends Activity {
    private static final byte[] PIXEL = android.util.Base64.decode(
        "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", android.util.Base64.DEFAULT);
    private static final Set<String> STATIC = Set.of(
        "/static/seed.gif", "/static/echo.gif", "/static/redirect-other", "/static/redirect-same");
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final JSONArray samples = new JSONArray();
    private final JSONArray controls = new JSONArray();
    private final JSONArray errors = new JSONArray();
    private final JSONObject partitions = new JSONObject();
    private LinearLayout layout;
    private String run, base, script;
    private Uri service;

    private record OwnedView(WebView view, Profile profile, String origin, AtomicInteger requests,
                             AtomicInteger popupDenials) {}

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        run = getIntent().getStringExtra("run");
        base = getIntent().getStringExtra("base");
        service = Uri.parse(base);
        layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        setContentView(layout);
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

    private <T> T main(Callable<T> operation) throws Exception {
        FutureTask<T> task = new FutureTask<>(operation);
        ui.post(task);
        return task.get(12, TimeUnit.SECONDS);
    }

    private JSONObject awaitObject(WebView web, String expression) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(12);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> result = new CompletableFuture<>();
            ui.post(() -> web.evaluateJavascript("JSON.stringify(" + expression + ")", result::complete));
            String raw;
            try {
                raw = result.get(1, TimeUnit.SECONDS);
            } catch (TimeoutException ignored) {
                // A provisional navigation can discard the old document's callback.
                continue;
            }
            Object outer = new JSONTokener(raw == null ? "null" : raw).nextValue();
            if (outer instanceof String text) {
                Object value = new JSONTokener(text).nextValue();
                if (value instanceof JSONObject data) return data;
            }
            Thread.sleep(100);
        }
        throw new IllegalStateException("Fixture observation deadline for " + expression);
    }

    private String readScript() throws Exception {
        try (InputStream in = getAssets().open("paths.js"); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int count;
            while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
            return out.toString(StandardCharsets.UTF_8.name());
        }
    }

    private String policy() {
        return "default-src 'none'; script-src 'unsafe-inline'; connect-src 'none'; "
            + "form-action 'none'; worker-src 'none'; frame-src 'self'; "
            + "img-src 'self' " + base + "/static/; base-uri 'none'";
    }

    private WebResourceResponse response(int status, String mime, byte[] body, Map<String, String> headers) {
        return new WebResourceResponse(mime, "UTF-8", status, status == 200 ? "OK" : "Forbidden",
            headers, new ByteArrayInputStream(body));
    }

    private WebResourceResponse local(Uri url, String origin, AtomicInteger requests) {
        String path = url.getPath();
        if ("/local.gif".equals(path)) {
            return response(200, "image/gif", PIXEL, Map.of("Cache-Control", "no-store",
                "Set-Cookie", "c09_local=1; Path=/; Secure"));
        }
        if ("/worker.js".equals(path)) {
            return response(200, "text/javascript", "postMessage('worker')".getBytes(StandardCharsets.UTF_8),
                Map.of("Cache-Control", "no-store"));
        }
        if ("/guest".equals(path) || "/frame".equals(path)) {
            if ("/guest".equals(path)) requests.incrementAndGet();
            JSONObject config = object("base", base, "origin", origin, "run", run,
                "view", url.getQueryParameter("view"), "frame", "/frame".equals(path));
            String html = "<!doctype html><meta charset=utf-8><meta http-equiv=\"Content-Security-Policy\" content=\""
                + policy() + "\"><script>window.c09Config=" + config + ";\n" + script + "</script><body>";
            return response(200, "text/html", html.getBytes(StandardCharsets.UTF_8), Map.of("Cache-Control", "no-store"));
        }
        return denied();
    }

    private WebResourceResponse denied() {
        return response(403, "text/plain", new byte[0], Map.of("Cache-Control", "no-store"));
    }

    private OwnedView make(String profileName, String origin) throws Exception {
        return main(() -> {
            WebView web = new WebView(this);
            if (profileName != null) WebViewCompat.setProfile(web, profileName);
            Profile profile = WebViewCompat.getProfile(web);
            AtomicInteger requests = new AtomicInteger();
            AtomicInteger popupDenials = new AtomicInteger();
            web.getSettings().setJavaScriptEnabled(true);
            web.getSettings().setDomStorageEnabled(true);
            web.getSettings().setAllowFileAccess(false);
            web.getSettings().setAllowContentAccess(false);
            web.getSettings().setSupportMultipleWindows(true);
            web.getSettings().setJavaScriptCanOpenWindowsAutomatically(true);
            web.setWebChromeClient(new WebChromeClient() {
                @Override public boolean onCreateWindow(WebView view, boolean dialog, boolean gesture,
                                                        android.os.Message result) {
                    popupDenials.incrementAndGet();
                    return false;
                }
            });
            web.setWebViewClient(new WebViewClient() {
                @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                    Uri url = request.getUrl();
                    boolean https = "https".equals(url.getScheme());
                    boolean loopback = https && url.getPort() == service.getPort()
                        && ("localhost".equals(url.getHost()) || "127.0.0.1".equals(url.getHost()));
                    if (loopback && (origin == null || ("localhost".equals(url.getHost()) && STATIC.contains(url.getPath())))) {
                        return null;
                    }
                    if (origin != null && origin.equals(url.getScheme() + "://" + url.getEncodedAuthority())) {
                        return local(url, origin, requests);
                    }
                    return denied();
                }

                @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    Uri url = request.getUrl();
                    return origin != null && !origin.equals(url.getScheme() + "://" + url.getEncodedAuthority());
                }

                @Override public void onReceivedSslError(WebView view, android.webkit.SslErrorHandler handler,
                        android.net.http.SslError error) {
                    errors.put(object("tls", error.getPrimaryError()));
                    handler.cancel();
                }
            });
            layout.addView(web, new LinearLayout.LayoutParams(-1, 120));
            return new OwnedView(web, profile, origin, requests, popupDenials);
        });
    }

    private void discard(OwnedView candidate) {
        candidate.view().stopLoading();
        layout.removeView(candidate.view());
        candidate.view().destroy();
    }

    private String profile(String role) {
        return "cookie-paths-" + run + "-" + role;
    }

    private void control(OwnedView owned, String role, String stage) throws Exception {
        String label = role + "-" + stage;
        CookieManager manager = owned.profile().getCookieManager();
        if ("before".equals(stage)) {
            main(() -> { manager.setAcceptCookie(true); return null; });
            controlPage(owned.view(), role, "/control", label);
        }
        JSONObject value = controlPage(owned.view(), role, "before".equals(stage) ? "/echo" : "/control", label);
        controls.put(object("view", label, "cookie", value.getString("cookie"),
            "policyAllows", main(manager::acceptCookie)));
    }

    private JSONObject controlPage(WebView web, String role, String path, String label) throws Exception {
        String host = "U".equals(role) ? base.replace("localhost", "127.0.0.1") : base;
        String url = host + path + "?run=" + run + "&view=" + label;
        main(() -> { web.loadUrl(url); return null; });
        return awaitObject(web, "window.c09Control?.href === " + JSONObject.quote(url) + " ? window.c09Control : null");
    }

    private List<String> cookiePairs(CookieManager manager) {
        return CookieManagerCompat.getCookieInfo(manager, base + "/echo").stream()
            .map(value -> value.split(";", 2)[0]).sorted().collect(java.util.stream.Collectors.toList());
    }

    private void gate(OwnedView candidate, String label, boolean unknown) throws Exception {
        CookieManager manager = candidate.profile().getCookieManager();
        int oldCount = candidate.requests().get();
        int oldPopups = candidate.popupDenials().get();
        JSONArray events = new JSONArray();
        AtomicInteger loads = new AtomicInteger();
        List<String> before = main(() -> cookiePairs(manager));
        String[] presence = new String[1];
        boolean[] policyAllows = new boolean[1];
        boolean admitted = main(() -> {
            AdmissionGate owner = new AdmissionGate((name, complete) -> {
                manager.setAcceptCookie(false);
                events.put("policyComplete");
                policyAllows[0] = manager.acceptCookie();
                events.put("policyRead");
                AdmissionGate.Presence verdict = unknown || policyAllows[0]
                    ? AdmissionGate.Presence.UNKNOWN
                    : manager.hasCookies() ? AdmissionGate.Presence.PRESENT : AdmissionGate.Presence.EMPTY;
                presence[0] = verdict.name().toLowerCase(java.util.Locale.ROOT);
                events.put("presence");
                complete.accept(verdict);
            });
            owner.admit(label, () -> {
                events.put("load");
                loads.incrementAndGet();
                if ("reload".equals(label)) candidate.view().reload();
                else candidate.view().loadUrl(candidate.origin() + "/guest?view=" + label);
            }, () -> {
                events.put("refuse");
                discard(candidate);
            });
            return loads.get() == 1;
        });
        Object guest = JSONObject.NULL;
        if (admitted) {
            guest = awaitObject(candidate.view(), "window.c09Result?.view === " + JSONObject.quote(label)
                + " ? window.c09Result : null");
            events.put("script");
        }
        samples.put(object("view", label, "partition", candidate.profile().getName(), "events", events,
            "presence", presence[0], "policyAllows", policyAllows[0], "source", unknown ? "injected" : "native",
            "guest", guest, "loadCalls", loads.get(), "guestResources", candidate.requests().get() - oldCount,
            "popupDenials", candidate.popupDenials().get() - oldPopups,
            "beforeCookies", new JSONArray(before), "afterCookies", new JSONArray(main(() -> cookiePairs(manager))),
            "afterPresent", main(manager::hasCookies)));
    }

    private void execute() {
        JSONObject report = object("platform", "android", "run", run, "samples", samples, "controls", controls,
            "partitions", partitions, "errors", errors, "complete", false);
        try {
            main(() -> {
                if (!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)
                        || !WebViewFeature.isFeatureSupported(WebViewFeature.GET_COOKIE_INFO)) {
                    throw new IllegalStateException("Scoped profile and cookie inventory are required");
                }
                return null;
            });
            script = readScript();
            report.put("release", android.os.Build.VERSION.RELEASE);
            report.put("provider", main(() -> WebViewCompat.getCurrentWebViewPackage(this).versionName));
            OwnedView host = make(null, null);
            OwnedView other = make(profile("U"), null);
            OwnedView seeded = make(profile("B"), null);
            String origin = "https://mp-" + run + "-a.invalid";
            OwnedView a = make(profile("A"), origin);
            partitions.put("H", host.profile().getName());
            partitions.put("U", other.profile().getName());
            partitions.put("B", seeded.profile().getName());
            partitions.put("A", a.profile().getName());
            control(host, "H", "before");
            control(other, "U", "before");
            control(seeded, "B", "before");
            gate(a, "initial", false);
            control(host, "H", "after-A");
            control(other, "U", "after-A");
            control(seeded, "B", "after-A");
            gate(a, "reload", false);
            main(() -> { discard(a); return null; });
            gate(make(profile("A"), origin), "recreated", false);
            gate(make(profile("B"), "https://mp-" + run + "-b.invalid"), "present", false);
            control(host, "H", "after-B");
            control(other, "U", "after-B");
            gate(make(profile("A"), origin), "unknown", true);
            report.put("complete", true);
        } catch (Exception error) {
            errors.put(object("error", error.toString()));
        }
        try (java.io.FileOutputStream output = openFileOutput("report.json", MODE_PRIVATE)) {
            output.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) {
            android.util.Log.e("CookiePathsProbe", "Unable to write report", error);
        }
    }
}
