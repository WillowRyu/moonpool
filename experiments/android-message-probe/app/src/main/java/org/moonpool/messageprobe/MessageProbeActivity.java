package org.moonpool.messageprobe;

import android.app.Activity;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Base64;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.webkit.JavaScriptReplyProxy;
import androidx.webkit.WebMessageCompat;
import androidx.webkit.WebMessagePortCompat;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Native API measurements only. There is no Moonpool dispatcher or provider. */
public final class MessageProbeActivity extends Activity {
    private final Handler main = new Handler(Looper.getMainLooper());
    private final JSONArray events = new JSONArray();
    private final JSONArray samples = new JSONArray();
    private final List<Step> steps = new ArrayList<>();
    private final List<PortBinding> ports = new ArrayList<>();
    private final IdentityHashMap<JavaScriptReplyProxy, Integer> proxies = new IdentityHashMap<>();
    private final long start = SystemClock.elapsedRealtime();
    private LinearLayout layout;
    private TextView status;
    private JSONObject report;
    private String profile;
    private String run;
    private Slot a;
    private Slot b;
    private Slot c;
    private Proof oldProof;
    private Proof reloadProof;
    private int stepIndex;
    private int proofSequence;
    private boolean finished;

    interface Step { void run(Runnable next); }
    interface Condition { boolean ready(JSONObject snapshot); }

    private static JSONObject json(Object... pairs) {
        JSONObject value = new JSONObject();
        try {
            for (int i = 0; i < pairs.length; i += 2) value.put((String) pairs[i], pairs[i + 1]);
        } catch (Exception error) { throw new IllegalStateException(error); }
        return value;
    }

    private synchronized void event(String type, Object... pairs) {
        JSONObject value = json(pairs);
        try {
            value.put("type", type);
            value.put("sequence", events.length() + 1);
            value.put("elapsedMs", SystemClock.elapsedRealtime() - start);
            events.put(value);
        } catch (Exception error) { throw new IllegalStateException(error); }
    }

    private String origin(String app) {
        return "custom".equals(profile) ? "moonpool://com.example.probe." + app
            : "https://com.example.probe." + app + ".test";
    }

    private String url(String app, String doc) {
        String other = "a".equals(app) ? "b" : "a";
        return origin(app) + "/assets/index.html?doc=" + Uri.encode(doc)
            + "&self=" + Uri.encode(origin(app)) + "&other=" + Uri.encode(origin(other));
    }

    private int proxyId(JavaScriptReplyProxy proxy) {
        if (!proxies.containsKey(proxy)) proxies.put(proxy, proxies.size() + 1);
        return proxies.get(proxy);
    }

    private static final class Proof {
        final String value;
        final int id;
        final JavaScriptReplyProxy reply;
        Proof(String value, int id, JavaScriptReplyProxy reply) { this.value = value; this.id = id; this.reply = reply; }
    }

    private final class Slot {
        final String name;
        final String expectedOrigin;
        final WebView web;
        boolean active = true;
        boolean pageFinished;
        int readyCount;
        Proof proof;
        WebView lastSender;
        String lastOrigin;
        boolean lastMain;
        Slot(String name, String app) {
            this.name = name;
            expectedOrigin = origin(app);
            web = new WebView(MessageProbeActivity.this);
            web.getSettings().setJavaScriptEnabled(true);
            web.getSettings().setAllowFileAccess(false);
            web.getSettings().setAllowContentAccess(false);
            web.setWebViewClient(new WebViewClient() {
                @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                    Uri uri = request.getUrl();
                    String path = uri.getPath();
                    if ((origin("a").equals(uri.getScheme() + "://" + uri.getHost())
                        || origin("b").equals(uri.getScheme() + "://" + uri.getHost()))
                        && List.of("/assets/index.html", "/assets/probe.js").contains(path)) {
                        try { return new WebResourceResponse(path.endsWith(".js") ? "text/javascript" : "text/html", "UTF-8",
                            getAssets().open(path.substring(8))); }
                        catch (Exception error) { event("asset-error", "view", name, "error", error.getClass().getSimpleName()); }
                    }
                    event("blocked-resource", "view", name, "url", uri.toString());
                    return new WebResourceResponse("text/plain", "UTF-8", 451, "Blocked", Map.of(),
                        new ByteArrayInputStream("No network fallback".getBytes(StandardCharsets.UTF_8)));
                }
                @Override public void onPageStarted(WebView view, String target, Bitmap icon) {
                    event("page-started", "view", name, "url", target);
                }
                @Override public void onPageFinished(WebView view, String target) {
                    pageFinished = true;
                    event("page-finished", "view", name, "url", target);
                }
                @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    event("navigation", "view", name, "url", request.getUrl().toString(), "mainFrame", request.isForMainFrame());
                    return false; // Observe only; this is not production navigation containment.
                }
            });
            Set<String> observers = "custom".equals(profile) ? Set.of("moonpool://") : Set.of(origin("a"), origin("b"));
            WebViewCompat.addWebMessageListener(web, "T25Observe", observers,
                (sender, message, source, isMain, reply) -> receive(this, "observer", sender, message, source, isMain, reply));
            try {
                WebViewCompat.addWebMessageListener(web, "T25Pinned", Set.of(expectedOrigin),
                    (sender, message, source, isMain, reply) -> receive(this, "pinned", sender, message, source, isMain, reply));
                event("pinned-registration", "view", name, "rule", expectedOrigin, "accepted", true);
            } catch (IllegalArgumentException error) {
                event("pinned-registration", "view", name, "rule", expectedOrigin, "accepted", false,
                    "error", error.getClass().getSimpleName());
            }
            layout.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        }
    }

    private void receive(Slot slot, String channel, WebView sender, WebMessageCompat message,
                         Uri source, boolean isMain, JavaScriptReplyProxy reply) {
        if (message.getType() != WebMessageCompat.TYPE_STRING) {
            event("non-string", "view", slot.name, "channel", channel); return;
        }
        try {
            JSONObject data = new JSONObject(message.getData());
            String decision = Admission.reason(slot.web, sender, slot.expectedOrigin, source.toString(), isMain, slot.active);
            event("listener", "view", slot.name, "channel", channel, "senderMatches", sender == slot.web,
                "sourceOrigin", source.toString(), "mainFrame", isMain, "decision", decision,
                "kind", data.optString("kind"), "doc", data.optString("doc"), "proxy", proxyId(reply),
                "claimedOrigin", data.optString("claimedOrigin"), "claimedMainFrame", data.optBoolean("claimedMainFrame"),
                "beforePageFinished", !slot.pageFinished, "readyState", data.optString("readyState"));
            if (isMain && "observer".equals(channel)) {
                slot.lastSender = sender; slot.lastOrigin = source.toString(); slot.lastMain = true;
                if ("ready".equals(data.optString("kind"))) slot.readyCount++;
            }
            if (!"accepted".equals(decision)) {
                WebMessagePortCompat[] received = message.getPorts();
                if (received != null) for (WebMessagePortCompat port : received) port.close();
                return;
            }
            if ("pinned".equals(channel) && "offer".equals(data.optString("kind"))) {
                WebMessagePortCompat[] received = message.getPorts();
                event("listener-port-offer", "view", slot.name, "count", received == null ? 0 : received.length,
                    "sourceOrigin", source.toString(), "mainFrame", isMain, "proxy", proxyId(reply));
                if (received != null && received.length == 1) {
                    PortBinding binding = new PortBinding(slot, "listener-offer", null, false, received[0]);
                    ports.add(binding);
                    binding.host.setWebMessageCallback(new WebMessagePortCompat.WebMessageCallbackCompat() {
                        @Override public void onMessage(WebMessagePortCompat port, WebMessageCompat value) {
                            receivePort(binding, port, value, "platform");
                        }
                    });
                }
            }
            if ("observer".equals(channel) && "ready".equals(data.optString("kind"))) {
                byte[] bytes = new byte[24]; new SecureRandom().nextBytes(bytes);
                slot.proof = new Proof(Base64.encodeToString(bytes, Base64.NO_WRAP), ++proofSequence, reply);
                reply.postMessage(json("kind", "challenge", "value", slot.proof.value).toString());
                event("challenge-sent", "view", slot.name, "proofId", slot.proof.id, "proxy", proxyId(reply));
            } else if ("pinned".equals(channel)) {
                reply.postMessage(json("kind", "pinned-ack", "doc", data.optString("doc")).toString());
            }
        } catch (Exception error) { event("listener-error", "view", slot.name, "error", error.getClass().getSimpleName()); }
    }

    private final class PortBinding {
        final Slot slot;
        final String label;
        final Proof proof;
        final boolean requireProof;
        final WebMessagePortCompat host;
        boolean retired;
        int received;
        WebMessageCompat lastMessage;
        PortBinding(Slot slot, String label, Proof proof, boolean requireProof, WebMessagePortCompat host) {
            this.slot = slot; this.label = label; this.proof = proof; this.requireProof = requireProof; this.host = host;
        }
    }

    private void receivePort(PortBinding binding, WebMessagePortCompat sender, WebMessageCompat message, String provenance) {
        try {
            JSONObject data = new JSONObject(message.getData());
            boolean matches = binding.proof != null && binding.proof.value.equals(data.optString("proof"));
            // AndroidX supplies a different callback wrapper. Authority is the native
            // callback registration captured above, not wrapper equality or page claims.
            String decision = !binding.slot.active || binding.retired ? "retired"
                : binding.requireProof && !matches ? "wrong-document-proof" : "accepted";
            event("port-message", "view", binding.slot.name, "label", binding.label, "provenance", provenance,
                "claimedDoc", data.optString("doc"), "claimedOrigin", data.optString("claimedOrigin"),
                "messageSequence", data.optInt("seq"), "decision", decision, "proofMatches", matches,
                "callbackWrapperMatches", sender == binding.host,
                "requireProof", binding.requireProof, "originMetadataAvailable", false, "frameMetadataAvailable", false);
            if ("platform".equals(provenance)) { binding.received++; binding.lastMessage = message; }
            if ("accepted".equals(decision)) binding.host.postMessage(new WebMessageCompat("ack:" + binding.label + ":" + data.optInt("seq")));
        } catch (Exception error) { event("port-error", "label", binding.label, "error", error.getClass().getSimpleName()); }
    }

    private PortBinding transfer(Slot slot, String label, String target, Proof proof, boolean requireProof, boolean forward) {
        WebMessagePortCompat[] pair = WebViewCompat.createWebMessageChannel(slot.web);
        PortBinding binding = new PortBinding(slot, label, proof, requireProof, pair[0]);
        ports.add(binding);
        pair[0].setWebMessageCallback(new WebMessagePortCompat.WebMessageCallbackCompat() {
            @Override public void onMessage(WebMessagePortCompat port, WebMessageCompat message) { receivePort(binding, port, message, "platform"); }
        });
        event("port-transfer", "view", slot.name, "label", label, "targetOrigin", target,
            "proofId", proof == null ? 0 : proof.id, "requireProof", requireProof, "forward", forward);
        WebViewCompat.postWebMessage(slot.web, new WebMessageCompat(json("kind", "bootstrap", "label", label,
            "requireProof", requireProof, "forward", forward).toString(), new WebMessagePortCompat[] { pair[1] }), Uri.parse(target));
        return binding;
    }

    private void snapshot(String label, Slot slot, Condition condition, int remaining, Runnable done) {
        status.setText("T25 " + profile + " / " + run + " / " + label);
        slot.web.evaluateJavascript("JSON.stringify(window.t25Report || null)", raw -> {
            JSONObject data = null;
            try {
                Object outer = new JSONTokener(raw).nextValue();
                if (outer instanceof String) data = new JSONObject((String) outer);
            } catch (Exception ignored) { /* Polling may cross a document replacement. */ }
            if (data != null && condition.ready(data)) {
                samples.put(json("label", label, "view", slot.name, "observation", data)); done.run();
            } else if (remaining == 0) {
                samples.put(json("label", label, "view", slot.name, "unavailable", true)); done.run();
            } else main.postDelayed(() -> snapshot(label, slot, condition, remaining - 1, done), 50);
        });
    }

    private void sample(String label, Slot slot, Runnable done) {
        snapshot(label, slot, data -> data.optBoolean("ready"), 100, done);
    }

    private void load(String label, Slot slot, String app, String doc, boolean reload, Runnable done) {
        int previous = slot.readyCount;
        slot.pageFinished = false;
        slot.proof = null;
        slot.web.evaluateJavascript("window.t25Report = null", ignored -> {
            if (reload) slot.web.reload(); else slot.web.loadUrl(url(app, doc));
            snapshot(label, slot, data -> doc.equals(data.optString("doc")) && data.optBoolean("ready")
                && data.optJSONArray("frames") != null && data.optJSONArray("frames").length() == 2
                && slot.readyCount > previous
                && (!"https".equals(profile) || !origin(app).equals(slot.expectedOrigin) || data.optBoolean("challengeReceived")), 160, done);
        });
    }

    private void portStep(String label, Proof proof, boolean authenticated, boolean forward, Runnable done) {
        PortBinding binding = transfer(a, label, origin("a"), proof, authenticated, forward);
        snapshot(label, a, data -> binding.received == 3
            && (authenticated && binding.proof != a.proof || replyCount(data, label) == 3), 100, done);
    }

    private int replyCount(JSONObject data, String label) {
        JSONArray replies = data.optJSONArray("portReplies");
        int count = 0;
        if (replies != null) for (int i = 0; i < replies.length(); i++) {
            if (label.equals(replies.optJSONObject(i).optString("label"))) count++;
        }
        return count;
    }

    private void next() {
        if (finished) return;
        if (stepIndex < steps.size()) { steps.get(stepIndex++).run(this::next); return; }
        finishProbe();
    }

    private void finishProbe() {
        finished = true;
        for (PortBinding binding : ports) {
            binding.retired = true;
            try { binding.host.close(); } catch (Exception error) { event("close-error", "label", binding.label, "error", error.getClass().getSimpleName()); }
        }
        try {
            report.put("samples", samples); report.put("events", events); report.put("complete", true);
            try (FileOutputStream output = new FileOutputStream(new File(getFilesDir(), "report.json"))) {
                output.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
            }
            status.setText("T25 " + profile + " / " + run + " complete: " + samples.length() + " snapshots");
        } catch (Exception error) { status.setText("Report write failed: " + error.getClass().getSimpleName()); }
    }

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        profile = getIntent().getStringExtra("profile"); run = getIntent().getStringExtra("run");
        if (!List.of("https", "custom").contains(profile) || run == null) throw new IllegalArgumentException("Unknown probe arguments");
        new File(getFilesDir(), "report.json").delete();
        layout = new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL); layout.setPadding(8, 65, 8, 30);
        status = new TextView(this); status.setTextSize(16); layout.addView(status); setContentView(layout);
        report = json("profile", profile, "run", run, "sdk", android.os.Build.VERSION.SDK_INT,
            "os", android.os.Build.VERSION.RELEASE);
        JSONObject features = new JSONObject(); boolean supported = true;
        for (String feature : List.of(WebViewFeature.WEB_MESSAGE_LISTENER, WebViewFeature.CREATE_WEB_MESSAGE_CHANNEL,
            WebViewFeature.POST_WEB_MESSAGE, WebViewFeature.WEB_MESSAGE_PORT_POST_MESSAGE,
            WebViewFeature.WEB_MESSAGE_PORT_SET_MESSAGE_CALLBACK, WebViewFeature.WEB_MESSAGE_PORT_CLOSE)) {
            boolean value = WebViewFeature.isFeatureSupported(feature);
            try { features.put(feature, value); } catch (Exception error) { throw new IllegalStateException(error); }
            supported &= value;
        }
        try { report.put("features", features); } catch (Exception error) { throw new IllegalStateException(error); }
        if (!supported) { event("unsupported", "action", "No channel fallback installed"); finishProbe(); return; }
        a = new Slot("a", "a"); b = new Slot("b", "b"); c = new Slot("same-origin-other-view", "a");
        try {
            report.put("webView", WebView.getCurrentWebViewPackage().versionName);
            report.put("webViewPackage", WebView.getCurrentWebViewPackage().packageName);
        } catch (Exception error) { throw new IllegalStateException(error); }
        steps.add(done -> load("initial-a", a, "a", "a1", false, done));
        steps.add(done -> load("initial-b", b, "b", "b1", false, done));
        steps.add(done -> load("same-origin-other-view", c, "a", "c1", false, done));
        steps.add(done -> {
            event("host-route-replay", "actualView", c.name, "targetView", a.name, "sourceOrigin", c.lastOrigin,
                "decision", Admission.reason(a.web, c.lastSender, a.expectedOrigin, c.lastOrigin, c.lastMain, a.active));
            a.web.evaluateJavascript("window.t25Send('repeat')", ignored -> main.postDelayed(done, 100));
        });
        if ("https".equals(profile)) addHTTPS();
        next();
    }

    private void addHTTPS() {
        steps.add(done -> {
            transfer(a, "wrong-target", origin("b"), a.proof, false, false);
            main.postDelayed(() -> sample("wrong-target", a, done), 250);
        });
        steps.add(done -> portStep("raw-positive", a.proof, false, false, done));
        steps.add(done -> portStep("proof-positive", a.proof, true, false, done));
        steps.add(done -> a.web.evaluateJavascript("window.t25Offer()", ignored ->
            snapshot("listener-offer", a, data -> replyCount(data, "listener-offer") == 3, 100, done)));
        steps.add(done -> portStep("proof-delegated", a.proof, true, true, done));
        steps.add(done -> { oldProof = a.proof; load("same-origin-replacement", a, "a", "a2", false, done); });
        steps.add(done -> {
            event("proxy-comparison", "label", "replacement", "sameProxy", oldProof.reply == a.proof.reply);
            oldProof.reply.postMessage(json("kind", "late-for-a1").toString());
            event("old-proxy-post", "label", "replacement");
            main.postDelayed(() -> sample("late-proxy-replacement", a, done), 200);
        });
        steps.add(done -> portStep("stale-origin-only", oldProof, false, false, done));
        steps.add(done -> portStep("stale-proof", oldProof, true, false, done));
        steps.add(done -> portStep("replacement-proof-positive", a.proof, true, false, done));
        steps.add(done -> { reloadProof = a.proof; load("same-url-reload", a, "a", "a2", true, done); });
        steps.add(done -> {
            event("proxy-comparison", "label", "reload", "sameProxy", reloadProof.reply == a.proof.reply);
            reloadProof.reply.postMessage(json("kind", "late-for-a2").toString());
            event("old-proxy-post", "label", "reload");
            main.postDelayed(() -> sample("late-proxy-reload", a, done), 200);
        });
        steps.add(done -> portStep("reload-stale-proof", reloadProof, true, false, done));
        steps.add(done -> load("foreign-navigation", a, "b", "a-foreign", false, done));
        steps.add(done -> load("return-navigation", a, "a", "a-return", false, done));
        steps.add(done -> {
            a.active = false;
            event("host-listener-replay", "view", a.name,
                "decision", Admission.reason(a.web, a.lastSender, a.expectedOrigin, a.lastOrigin, a.lastMain, a.active));
            PortBinding raw = ports.stream().filter(item -> "raw-positive".equals(item.label)).findFirst().get();
            raw.retired = true;
            receivePort(raw, raw.host, raw.lastMessage, "host-replay");
            raw.host.close(); raw.host.close();
            try {
                raw.host.postMessage(new WebMessageCompat("after-close"));
                event("post-after-close", "threw", false);
            } catch (IllegalStateException error) { event("post-after-close", "threw", true, "error", error.getClass().getSimpleName()); }
            a.web.evaluateJavascript("window.t25Send('after-retire')", ignored -> main.postDelayed(() -> sample("retired-binding", a, done), 150));
        });
    }

    @Override protected void onDestroy() {
        main.removeCallbacksAndMessages(null);
        for (Slot slot : new Slot[] { a, b, c }) if (slot != null) {
            slot.active = false; layout.removeView(slot.web); slot.web.destroy();
        }
        super.onDestroy();
    }
}
