package org.moonpool.cookieadmission;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;
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
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
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

public final class ProfileRetirementActivity extends Activity {
    private static final String COOKIE = "mp_retirement=fixture";
    private static final String POLICY = "default-src 'none'; script-src 'unsafe-inline'; worker-src 'none'; base-uri 'none'";
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final List<String> events = new ArrayList<>();
    private final Map<String, Map<String, Boolean>> inspections = new LinkedHashMap<>();
    private final ConcurrentLinkedQueue<String> loader = new ConcurrentLinkedQueue<>();
    private FrameLayout views;
    private String storeScript;

    private final class Partition {
        final Profile profile;
        final String origin, marker;
        final AdmissionGate gate;
        final List<Portal> portals = new ArrayList<>();

        Partition(Profile profile, String origin, String marker) {
            this.profile = profile;
            this.origin = origin;
            this.marker = marker;
            gate = new AdmissionGate((name, complete) -> {
                events.add(name + ":inspect");
                ui.post(() -> {
                    AdmissionGate.Presence presence = AdmissionGate.Presence.UNKNOWN;
                    try {
                        Map<String, Boolean> state = cookieState(profile);
                        inspections.put(name, state);
                        if (!state.get("accept")) {
                            presence = state.get("present") ? AdmissionGate.Presence.PRESENT : AdmissionGate.Presence.EMPTY;
                        }
                    } catch (RuntimeException unavailable) {
                        // The gate must retire the affected group when native evidence cannot be read.
                    }
                    events.add(name + ":" + presence.name().toLowerCase(Locale.ROOT));
                    complete.accept(presence);
                });
            });
        }
    }

    private static final class Portal {
        final String name;
        final Partition partition;
        AdmissionGate.Handle handle;
        WebView web;
        int loads, retireCalls;
        boolean destroyed, groupInactiveAtDestroy;

        Portal(String name, Partition partition) {
            this.name = name;
            this.partition = partition;
        }

        WebView liveView() {
            return handle != null && handle.live ? web : null;
        }
    }

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

    private Partition createPartition(String run, String key) throws Exception {
        return main(() -> {
            ProfileStore profiles = ProfileStore.getInstance();
            String suffix = run + "-" + key;
            String name = "profile-retirement-" + suffix;
            if (profiles.getAllProfileNames().contains(name)) {
                throw new IllegalStateException("The fixture requires an unused named profile");
            }
            Profile profile = profiles.getOrCreateProfile(name);
            profile.getCookieManager().setAcceptCookie(false);
            return new Partition(profile, "https://mp-" + suffix + ".invalid", suffix);
        });
    }

    private static Map<String, Boolean> cookieState(Profile profile) {
        CookieManager manager = profile.getCookieManager();
        return Map.of("accept", manager.acceptCookie(), "present", manager.hasCookies());
    }

    private WebView createView(String profile, WebViewClient client, boolean offline) {
        WebView view = new WebView(this);
        WebViewCompat.setProfile(view, profile);
        if (!profile.equals(WebViewCompat.getProfile(view).getName())) {
            throw new IllegalStateException("Unexpected WebView profile");
        }
        view.getSettings().setJavaScriptEnabled(true);
        view.getSettings().setDomStorageEnabled(true);
        view.getSettings().setAllowFileAccess(false);
        view.getSettings().setAllowContentAccess(false);
        if (offline) view.getSettings().setBlockNetworkLoads(true);
        view.setWebViewClient(client);
        views.addView(view);
        return view;
    }

    private void destroy(WebView view) {
        views.removeView(view);
        view.destroy();
    }

    private WebResourceResponse response(int status, String type, String body) {
        return new WebResourceResponse(type, "UTF-8", status, status == 200 ? "OK" : "Forbidden",
            Map.of("Cache-Control", "no-store", "Content-Security-Policy", POLICY),
            new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));
    }

    private boolean atOrigin(WebResourceRequest request, String origin) {
        return origin.equals(request.getUrl().getScheme() + "://" + request.getUrl().getEncodedAuthority());
    }

    private void open(Portal portal, boolean seed) {
        String name = portal.name;
        String origin = portal.partition.origin;
        String path = "/" + name;
        String marker = seed ? JSONObject.quote(portal.partition.marker) : "undefined";
        String html = "<!doctype html><meta charset=utf-8><title>Retirement fixture</title><script>"
            + storeScript + "\n(async () => { window.retirementFixture = { name: " + JSONObject.quote(name)
            + ", origin: window.origin, instance: crypto.randomUUID(), pulse: 0, cookie: document.cookie,"
            + " marker: await window.workerAdmissionData(" + marker + ") }; })();</script>";
        WebView web = createView(portal.partition.profile.getName(), new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView ignored, WebResourceRequest request) {
                return !atOrigin(request, origin);
            }

            @Override public WebResourceResponse shouldInterceptRequest(WebView ignored, WebResourceRequest request) {
                if (atOrigin(request, origin) && request.isForMainFrame() && "GET".equals(request.getMethod())
                        && path.equals(request.getUrl().getEncodedPath())) {
                    loader.add(name);
                    return response(200, "text/html", html);
                }
                return response(403, "text/plain", "");
            }
        }, false);
        portal.web = web;
        portal.loads++;
        events.add(name + ":load");
        web.loadUrl(origin + path);
    }

    private void retire(Portal portal) {
        portal.retireCalls++;
        if (portal.web == null) {
            events.add(portal.name + ":refuse");
            return;
        }
        portal.groupInactiveAtDestroy = portal.partition.portals.stream()
            .noneMatch(sibling -> sibling.handle != null && sibling.handle.live);
        destroy(portal.web);
        portal.web = null;
        portal.destroyed = true;
        events.add(portal.name + ":destroy");
    }

    private Portal admit(Partition partition, String name, boolean seed) {
        Portal portal = new Portal(name, partition);
        partition.portals.add(portal);
        portal.handle = partition.gate.admit(name, () -> open(portal, seed), () -> retire(portal));
        return portal;
    }

    private JSONObject state(Portal portal) throws Exception {
        return new JSONObject().put("live", portal.handle.live).put("loads", portal.loads)
            .put("retireCalls", portal.retireCalls).put("destroyed", portal.destroyed)
            .put("attached", portal.web != null && portal.web.getParent() == views && portal.web.isAttachedToWindow())
            .put("groupInactiveAtDestroy", portal.groupInactiveAtDestroy);
    }

    private JSONObject observe(WebView view, String expression) throws Exception {
        if (view == null) throw new IllegalStateException("The fixture view is inactive");
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(15);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> value = new CompletableFuture<>();
            ui.post(() -> view.evaluateJavascript(expression, value::complete));
            try {
                String raw = value.get(1, TimeUnit.SECONDS);
                if (new JSONTokener(raw == null ? "null" : raw).nextValue() instanceof String json
                        && new JSONTokener(json).nextValue() instanceof JSONObject result) {
                    return result;
                }
            } catch (TimeoutException pending) {
                continue;
            }
            Thread.sleep(100);
        }
        throw new TimeoutException("The fixture did not report its document");
    }

    private JSONObject guestObservation(Portal portal) throws Exception {
        return observe(main(portal::liveView), "JSON.stringify(window.retirementFixture && "
            + "{...window.retirementFixture, pulse: ++window.retirementFixture.pulse})");
    }

    private JSONObject initial(Portal portal) throws Exception {
        JSONObject document = guestObservation(portal);
        return main(() -> new JSONObject().put("state", state(portal)).put("document", document)
            .put("profile", WebViewCompat.getProfile(portal.liveView()).getName()));
    }

    private JSONObject setFixtureCookie(Partition partition) throws Exception {
        CompletableFuture<Boolean> completed = new CompletableFuture<>();
        main(() -> {
            partition.profile.getCookieManager().setCookie(partition.origin + "/", COOKIE + "; Path=/; Secure",
                completed::complete);
            return null;
        });
        boolean callback = completed.get(8, TimeUnit.SECONDS);
        return main(() -> {
            events.add("a:write-complete");
            return new JSONObject().put("callback", callback).put("state", new JSONObject(cookieState(partition.profile)))
                .put("cookie", partition.profile.getCookieManager().getCookie(partition.origin + "/"));
        });
    }

    private JSONObject preservedA(Partition partition) throws Exception {
        String nonce = UUID.randomUUID().toString();
        String html = "<!doctype html><meta charset=utf-8><meta http-equiv=\"Content-Security-Policy\" content=\""
            + POLICY + "\"><script>" + storeScript + "\n(async () => { window.hostMarker = { nonce: "
            + JSONObject.quote(nonce) + ", origin: window.origin, marker: await window.workerAdmissionData() }; })();</script>";
        ConcurrentLinkedQueue<String> requests = new ConcurrentLinkedQueue<>();
        WebView witness = main(() -> {
            Profile existing = ProfileStore.getInstance().getProfile(partition.profile.getName());
            if (existing == null) throw new IllegalStateException("The original profile is missing");
            WebView view = createView(existing.getName(), new WebViewClient() {
                @Override public boolean shouldOverrideUrlLoading(WebView ignored, WebResourceRequest request) {
                    return true;
                }

                @Override public WebResourceResponse shouldInterceptRequest(WebView ignored, WebResourceRequest request) {
                    String scheme = request.getUrl().getScheme();
                    if ("data".equals(scheme) || "about".equals(scheme)) return null;
                    requests.add(request.getUrl().toString());
                    return response(403, "text/plain", "");
                }
            }, true);
            view.loadDataWithBaseURL(partition.origin + "/host-marker", html, "text/html", "UTF-8", null);
            return view;
        });
        try {
            JSONObject data = observe(witness, "JSON.stringify(window.hostMarker || null)");
            return main(() -> new JSONObject().put("profile", WebViewCompat.getProfile(witness).getName())
                .put("nonceMatched", nonce.equals(data.getString("nonce")))
                .put("origin", data.getString("origin")).put("marker", data.get("marker"))
                .put("unexpectedRequests", new JSONArray(requests)).put("state", new JSONObject(cookieState(partition.profile)))
                .put("cookie", partition.profile.getCookieManager().getCookie(partition.origin + "/")));
        } finally {
            main(() -> { destroy(witness); return null; });
        }
    }

    private void measure(String run, JSONObject report) throws Exception {
        Partition a = createPartition(run, "a");
        Partition b = createPartition(run, "b");
        report.put("profiles", new JSONObject(Map.of(
            "a", Map.of("name", a.profile.getName(), "origin", a.origin),
            "b", Map.of("name", b.profile.getName(), "origin", b.origin))));
        try {
            JSONObject initial = new JSONObject();
            report.put("initial", initial);
            Portal a1 = main(() -> admit(a, "a1", true));
            initial.put("a1", initial(a1));
            Portal a2 = main(() -> admit(a, "a2", false));
            initial.put("a2", initial(a2));
            Portal b1 = main(() -> admit(b, "b1", true));
            initial.put("b1", initial(b1));
            report.put("writer", setFixtureCookie(a));
            Portal a3 = main(() -> {
                Portal pending = admit(a, "a3", false);
                report.put("pending", new JSONObject().put("a3", state(pending)).put("a1", state(a1)).put("a2", state(a2)));
                events.add("a3:pending");
                return pending;
            });
            Portal a4 = main(() -> admit(a, "a4", false));
            report.put("states", main(() -> new JSONObject().put("a1", state(a1)).put("a2", state(a2))
                .put("a3", state(a3)).put("a4", state(a4)).put("b1", state(b1))));
            report.put("retiredAccess", main(() -> new JSONObject().put("a1", a1.liveView() != null).put("a2", a2.liveView() != null)));
            report.put("continuedB", guestObservation(b1));
            report.put("bPolicy", main(() -> new JSONObject(cookieState(b.profile))));
            report.put("preservedA", preservedA(a));
            report.put("inspections", main(() -> new JSONObject(inspections)));
            report.put("events", main(() -> new JSONArray(events)));
            report.put("loader", new JSONArray(loader));
        } finally {
            main(() -> { a.gate.close(); b.gate.close(); return null; });
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
            storeScript = asset("store.js");
            measure(run, report);
            report.put("complete", true);
        } catch (Exception failure) {
            try {
                report.put("error", failure.toString());
            } catch (org.json.JSONException encoding) {
                android.util.Log.e("ProfileRetirementProbe", "Unable to encode failure", encoding);
            }
        }
        try (FileOutputStream file = openFileOutput("report.json", MODE_PRIVATE)) {
            file.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception failure) {
            android.util.Log.e("ProfileRetirementProbe", "Unable to write observations", failure);
        }
    }
}
