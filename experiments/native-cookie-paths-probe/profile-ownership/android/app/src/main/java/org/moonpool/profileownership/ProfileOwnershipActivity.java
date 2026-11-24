package org.moonpool.profileownership;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;
import androidx.webkit.Profile;
import androidx.webkit.ProfileStore;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

public final class ProfileOwnershipActivity extends Activity {
    private final Handler ui = new Handler(Looper.getMainLooper());

    private record Peer(boolean listed, Profile profile) {}

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        String run = getIntent().getStringExtra("run");
        new Thread(() -> collect(run)).start();
    }

    private <T> T main(Callable<T> operation) throws Exception {
        FutureTask<T> task = new FutureTask<>(operation);
        ui.post(task);
        return task.get(12, TimeUnit.SECONDS);
    }

    private Profile fresh(String run, String label, boolean accept) throws Exception {
        String name = "profile-ownership-" + run + "-" + label;
        return main(() -> {
            ProfileStore store = ProfileStore.getInstance();
            if (store.getAllProfileNames().contains(name)) {
                throw new IllegalStateException("The fixture requires an unused named profile");
            }
            Profile profile = store.getOrCreateProfile(name);
            profile.getCookieManager().setAcceptCookie(accept);
            return profile;
        });
    }

    private Peer lookUpByName(String name) throws Exception {
        return main(() -> {
            ProfileStore store = ProfileStore.getInstance();
            boolean listed = store.getAllProfileNames().contains(name);
            Profile profile = store.getProfile(name);
            if (profile == null) throw new IllegalStateException("The second caller could not resolve the fixture profile");
            return new Peer(listed, profile);
        });
    }

    private JSONObject snapshot(Profile profile, String url) throws Exception {
        return main(() -> {
            CookieManager manager = profile.getCookieManager();
            String cookie = manager.getCookie(url);
            return new JSONObject().put("accept", manager.acceptCookie()).put("hasCookies", manager.hasCookies())
                .put("cookie", cookie == null ? JSONObject.NULL : cookie);
        });
    }

    private JSONObject before(Profile profile, String url) throws Exception {
        return new JSONObject().put("profile", profile.getName()).put("created", true)
            .put("before", snapshot(profile, url));
    }

    private JSONObject write(Profile writer, Profile owner, String url, String marker) throws Exception {
        CompletableFuture<Boolean> completed = new CompletableFuture<>();
        main(() -> {
            writer.getCookieManager().setCookie(url, "mp_fixture=" + marker + "; Path=/; Secure", completed::complete);
            return null;
        });
        boolean succeeded = completed.get(8, TimeUnit.SECONDS);
        return new JSONObject().put("callback", succeeded).put("owner", snapshot(owner, url));
    }

    private void setPolicy(Profile profile, boolean accept) throws Exception {
        main(() -> {
            profile.getCookieManager().setAcceptCookie(accept);
            return null;
        });
    }

    private JSONObject trial(String run, String label, String url, boolean changePolicy) throws Exception {
        Profile owner = fresh(run, label, false);
        JSONObject report = before(owner, url);
        Peer peer = lookUpByName(owner.getName());
        report.put("peer", new JSONObject().put("listed", peer.listed()).put("profile", peer.profile().getName())
            .put("before", snapshot(peer.profile(), url)));
        if (changePolicy) {
            setPolicy(peer.profile(), true);
        }
        try {
            if (changePolicy) report.put("ownerAfterPolicy", snapshot(owner, url));
            JSONObject write = write(peer.profile(), owner, url, label);
            report.put("write", write.put("peer", snapshot(peer.profile(), url)));
        } finally {
            if (changePolicy) setPolicy(owner, false);
        }
        if (changePolicy) report.put("restored", snapshot(owner, url));
        return report;
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
            String url = "https://mp-" + run + ".invalid/";
            report.put("url", url);
            JSONObject cases = new JSONObject();
            report.put("cases", cases);
            Profile control = fresh(run, "control", true);
            JSONObject controlEvidence = before(control, url);
            cases.put("control", controlEvidence.put("write", write(control, control, url, "control")));
            cases.put("direct", trial(run, "direct", url, false));
            cases.put("policy", trial(run, "policy", url, true));
            controlEvidence.put("final", snapshot(control, url));
            report.put("complete", true);
        } catch (Exception failure) {
            try {
                report.put("error", failure.toString());
            } catch (org.json.JSONException encoding) {
                android.util.Log.e("ProfileOwnershipProbe", "Unable to encode failure", encoding);
            }
        }
        try (FileOutputStream file = openFileOutput("report.json", MODE_PRIVATE)) {
            file.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception failure) {
            android.util.Log.e("ProfileOwnershipProbe", "Unable to write observations", failure);
        }
    }
}
