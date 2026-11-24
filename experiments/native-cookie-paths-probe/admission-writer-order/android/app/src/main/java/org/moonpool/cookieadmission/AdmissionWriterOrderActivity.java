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
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

public final class AdmissionWriterOrderActivity extends Activity {
    private static final String COOKIE = "mp_admission_order=fixture";
    private static final String POLICY = "default-src 'none'; script-src 'unsafe-inline'; worker-src 'none'; base-uri 'none'";
    private final Handler ui = new Handler(Looper.getMainLooper());
    private FrameLayout views;

    private final class Trial {
        final Profile profile;
        final String origin, marker;
        final StoreOperations operations = new StoreOperations();
        final List<String> events = new ArrayList<>();
        final AtomicInteger loader = new AtomicInteger();
        final AdmissionGate gate;
        AdmissionGate.Handle handle;
        Runnable resumeInspection, finishAdmission;
        Map<String, Boolean> inspection, writeState;
        String writerResult = "pending", writtenCookie;
        Boolean writerCallback;
        int writerStarts, guestLoads;
        WebView web;

        Trial(Profile profile, String origin, String marker, boolean pauseAfterInspection) {
            this.profile = profile;
            this.origin = origin;
            this.marker = marker;
            gate = new AdmissionGate((name, complete) -> {
                events.add("inspection:start");
                inspection = cookieState(profile);
                AdmissionGate.Presence presence = AdmissionGate.Presence.UNKNOWN;
                if (!inspection.get("accept")) {
                    presence = inspection.get("present") ? AdmissionGate.Presence.PRESENT : AdmissionGate.Presence.EMPTY;
                }
                events.add("inspection:" + presence.name().toLowerCase(Locale.ROOT));
                AdmissionGate.Presence observed = presence;
                if (pauseAfterInspection) {
                    resumeInspection = () -> complete.accept(observed);
                } else {
                    complete.accept(observed);
                }
            });
        }

        void requestAdmission() {
            events.add("admission:request");
            operations.submit(done -> {
                finishAdmission = done;
                handle = gate.admit("guest", () -> open(this), this::retire);
            });
        }

        void completeAdmission() {
            Runnable done = finishAdmission;
            finishAdmission = null;
            done.run();
        }

        void requestWrite() {
            events.add("writer:request");
            operations.submit(done -> {
                if (handle != null && handle.live && web != null) {
                    writerResult = "refused-live";
                    events.add("writer:refused-live");
                    done.run();
                    return;
                }
                writerStarts++;
                events.add("writer:start");
                profile.getCookieManager().setCookie(origin + "/", COOKIE + "; Path=/; Secure", callback -> {
                    writerCallback = Boolean.TRUE.equals(callback);
                    events.add("writer:callback");
                    ui.post(() -> {
                        writerResult = writerCallback ? "stored" : "failed";
                        writeState = cookieState(profile);
                        writtenCookie = profile.getCookieManager().getCookie(origin + "/");
                        events.add("writer:readback");
                        done.run();
                    });
                });
            });
        }

        void retire() {
            if (web != null) {
                views.removeView(web);
                web.destroy();
                web = null;
            }
            if (finishAdmission != null) {
                events.add("admission:refuse");
                completeAdmission();
            }
        }

        void close() {
            operations.close();
            gate.close();
        }

        JSONObject admissionCheckpoint() throws Exception {
            return new JSONObject().put("writerStarts", writerStarts).put("guestLoads", guestLoads)
                .put("writerResult", writerResult).put("cookie", new JSONObject(cookieState(profile)));
        }

        JSONObject sample(JSONObject before) throws Exception {
            return new JSONObject().put("profile", profile.getName()).put("origin", origin).put("before", before)
                .put("inspection", new JSONObject(inspection)).put("writerResult", writerResult)
                .put("writerStarts", writerStarts).put("guestLoads", guestLoads).put("loader", loader.get())
                .put("after", new JSONObject(cookieState(profile))).put("events", new JSONArray(events));
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

    private static Map<String, Boolean> cookieState(Profile profile) {
        CookieManager manager = profile.getCookieManager();
        return Map.of("accept", manager.acceptCookie(), "present", manager.hasCookies());
    }

    private Trial fresh(String run, String label, boolean pauseAfterInspection) throws Exception {
        return main(() -> {
            ProfileStore profiles = ProfileStore.getInstance();
            String name = "admission-writer-order-" + run + "-" + label;
            if (profiles.getAllProfileNames().contains(name)) {
                throw new IllegalStateException("The fixture requires an unused named profile");
            }
            Profile profile = profiles.getOrCreateProfile(name);
            profile.getCookieManager().setAcceptCookie(false);
            return new Trial(profile, "https://mp-" + run + "-" + label + ".invalid",
                run + "-" + label, pauseAfterInspection);
        });
    }

    private WebResourceResponse response(int status, String mime, String body) {
        return new WebResourceResponse(mime, "UTF-8", status, status == 200 ? "OK" : "Forbidden",
            Map.of("Cache-Control", "no-store", "Content-Security-Policy", POLICY),
            new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));
    }

    private void open(Trial trial) {
        String entry = trial.origin + "/entry";
        String page = "<!doctype html><meta charset=utf-8><title>Admission writer order</title><script>"
            + "window.writerOrderGuest={origin:window.origin,cookie:document.cookie,marker:"
            + JSONObject.quote(trial.marker) + "};</script>";
        WebView web = new WebView(this);
        WebViewCompat.setProfile(web, trial.profile.getName());
        if (!trial.profile.getName().equals(WebViewCompat.getProfile(web).getName())) {
            throw new IllegalStateException("Unexpected view profile");
        }
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView ignored, WebResourceRequest request) {
                return !entry.equals(request.getUrl().toString());
            }

            @Override public WebResourceResponse shouldInterceptRequest(WebView ignored, WebResourceRequest request) {
                if (request.isForMainFrame() && "GET".equals(request.getMethod())
                        && entry.equals(request.getUrl().toString())) {
                    trial.loader.incrementAndGet();
                    return response(200, "text/html", page);
                }
                return response(403, "text/plain", "");
            }
        });
        views.addView(web);
        trial.web = web;
        trial.guestLoads++;
        trial.events.add("admission:load");
        web.loadUrl(entry);
    }

    private JSONObject observe(WebView web) throws Exception {
        if (web == null) throw new IllegalStateException("No admitted fixture view");
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(15);
        while (System.nanoTime() < deadline) {
            CompletableFuture<String> result = new CompletableFuture<>();
            ui.post(() -> web.evaluateJavascript("JSON.stringify(window.writerOrderGuest || null)", result::complete));
            try {
                String raw = result.get(1, TimeUnit.SECONDS);
                if (new JSONTokener(raw == null ? "null" : raw).nextValue() instanceof String text
                        && new JSONTokener(text).nextValue() instanceof JSONObject guest) {
                    return guest;
                }
            } catch (TimeoutException pending) {
                continue;
            }
            Thread.sleep(100);
        }
        throw new TimeoutException("The admitted fixture document did not report");
    }

    private JSONObject admissionFirst(String run) throws Exception {
        Trial trial = fresh(run, "admission", true);
        JSONObject before = main(() -> new JSONObject(cookieState(trial.profile)));
        try {
            JSONObject heldAfterRead = main(() -> {
                trial.requestAdmission();
                trial.requestWrite();
                return trial.admissionCheckpoint();
            });
            WebView admitted = main(() -> {
                trial.resumeInspection.run();
                trial.resumeInspection = null;
                return trial.web;
            });
            JSONObject guest = observe(admitted);
            return main(() -> {
                trial.events.add("guest:observed");
                JSONObject heldAtGuest = trial.admissionCheckpoint();
                trial.completeAdmission();
                return trial.sample(before).put("heldAfterRead", heldAfterRead)
                    .put("heldAtGuest", heldAtGuest).put("guest", guest);
            });
        } finally {
            main(() -> { trial.close(); return null; });
        }
    }

    private JSONObject writerFirst(String run) throws Exception {
        Trial trial = fresh(run, "writer", false);
        JSONObject before = main(() -> new JSONObject(cookieState(trial.profile)));
        try {
            JSONObject heldWhileWriting = main(() -> {
                trial.requestWrite();
                trial.requestAdmission();
                return new JSONObject().put("writerStarts", trial.writerStarts)
                    .put("writerCallback", trial.writerCallback == null ? JSONObject.NULL : trial.writerCallback)
                    .put("inspectionStarted", trial.events.contains("inspection:start")).put("guestLoads", trial.guestLoads);
            });
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(12);
            while (System.nanoTime() < deadline) {
                JSONObject finished = main(() -> {
                    if (trial.handle == null || !trial.handle.completed) return null;
                    String afterCookie = trial.profile.getCookieManager().getCookie(trial.origin + "/");
                    return trial.sample(before).put("heldWhileWriting", heldWhileWriting)
                        .put("afterCookie", afterCookie == null ? JSONObject.NULL : afterCookie)
                        .put("write", new JSONObject().put("callback", trial.writerCallback)
                            .put("state", new JSONObject(trial.writeState)).put("cookie", trial.writtenCookie));
                });
                if (finished != null) return finished;
                Thread.sleep(100);
            }
            throw new TimeoutException("The writer-first admission did not settle");
        } finally {
            main(() -> { trial.close(); return null; });
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
            JSONObject cases = new JSONObject();
            report.put("cases", cases);
            cases.put("admissionFirst", admissionFirst(run));
            cases.put("writerFirst", writerFirst(run));
            report.put("complete", true);
        } catch (Exception failure) {
            try {
                report.put("error", failure.toString());
            } catch (org.json.JSONException encoding) {
                android.util.Log.e("AdmissionWriterProbe", "Unable to encode failure", encoding);
            }
        }
        try (FileOutputStream file = openFileOutput("report.json", MODE_PRIVATE)) {
            file.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception failure) {
            android.util.Log.e("AdmissionWriterProbe", "Unable to write observations", failure);
        }
    }
}
