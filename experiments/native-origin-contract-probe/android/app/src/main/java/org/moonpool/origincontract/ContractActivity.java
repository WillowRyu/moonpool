package org.moonpool.origincontract;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.widget.LinearLayout;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import androidx.webkit.Profile;
import androidx.webkit.ProfileStore;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Research fixture, with no native bridge and only public marker cookies. */
public final class ContractActivity extends Activity {
 private final Handler main = new Handler(Looper.getMainLooper());
 private final JSONArray samples = new JSONArray(), events = new JSONArray();
 private final Registration a = Registration.derive("com.example.a"), b = Registration.derive("com.example.b");
 private final List<Runnable> steps = new ArrayList<>();
 private final List<WebView> webs = new ArrayList<>();
 private LinearLayout layout;
 private JSONObject report;
 private String tag, phase;
 private int step;
 private boolean seed;
 interface Value { void accept(Object value); }
 private static JSONObject obj(Object... args) {
  JSONObject o = new JSONObject();
  try { for (int i = 0; i < args.length; i += 2) o.put((String)args[i], args[i + 1]); }
  catch (Exception e) { throw new IllegalStateException(e); }
  return o;
 }
 private synchronized void event(String kind, Object... args) {
  JSONObject value = obj(args);
  try { value.put("kind", kind); events.put(value); } catch (Exception e) { throw new IllegalStateException(e); }
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  tag = getIntent().getStringExtra("tag"); phase = getIntent().getStringExtra("phase"); seed = "seed".equals(phase);
  layout = new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL); setContentView(layout);
  boolean multi = WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE);
  android.content.pm.PackageInfo provider = WebViewCompat.getCurrentWebViewPackage(this);
  report = obj("phase", phase, "tag", tag, "multiProfile", multi, "providerPackage", provider == null ? "unavailable" : provider.packageName,
   "providerVersion", provider == null ? "unavailable" : provider.versionName, "sdk", android.os.Build.VERSION.SDK_INT,
   "release", android.os.Build.VERSION.RELEASE, "samples", samples, "events", events,
   "a", obj("id", a.id, "key", a.key, "origin", a.origin, "profile", a.profile),
   "b", obj("id", b.id, "key", b.key, "origin", b.origin, "profile", b.profile));
  if (!multi) { event("unsupported-before-load"); save(); return; }
  try {
   register(a); register(b);
   ProfileStore.getInstance().getOrCreateProfile("t28-host-public-sentinel");
   // A real provider failure control; never exposed to guest execution.
   WebView early = new WebView(this);
   early.getSettings();
   try { WebViewCompat.setProfile(early, "t28-early-control"); event("early-settings", "outcome", "accepted"); }
   catch (IllegalStateException expected) { event("early-settings", "outcome", "rejected", "exception", expected.getClass().getSimpleName()); }
   early.destroy();
   WebView fixed = new WebView(this);
   String prior = WebViewCompat.getProfile(fixed).getName();
   try { WebViewCompat.setProfile(fixed, "t28-profile-after-get"); event("early-getProfile", "outcome", "accepted", "priorProfile", prior); }
   catch (IllegalStateException expected) { event("early-getProfile", "outcome", "rejected", "priorProfile", prior, "exception", expected.getClass().getSimpleName()); }
   fixed.destroy();
   WebView a1 = web(a.profile, "a1"), a2 = web(a.profile, "a2"), bv = web(b.profile, "b");
   steps.add(() -> local(a1, a, "a-initial", seed));
   steps.add(() -> local(bv, b, "b-initial", seed));
   steps.add(() -> local(a2, a, "a-shared", false));
   steps.add(() -> local(web(a.profile, "b-within-a-profile"), b, "b-within-a-profile", false));
   steps.add(() -> local(a1, a, "a-before-reload", false));
   steps.add(() -> local(a1, a, "a-reload", false));
   steps.add(() -> { a2.destroy(); WebView recreated = web(a.profile, "a-recreated"); local(recreated, a, "a-recreated", false); });
   steps.add(() -> remote(web(a.profile, "remote-a"), "a", seed));
   steps.add(() -> remote(web(b.profile, "remote-b"), "b", seed));
   steps.add(() -> remote(web("t28-host-public-sentinel", "remote-host"), "host", seed));
   steps.add(() -> remote(web(a.profile, "remote-a-shared"), "a-shared", false));
   next();
  } catch (Exception error) { event("setup-error", "exception", error.getClass().getSimpleName(), "message", String.valueOf(error.getMessage())); save(); }
 }
 private void register(Registration r) {
  android.content.SharedPreferences prefs = getSharedPreferences("t28-registrations", MODE_PRIVATE);
  String stored = prefs.getString(r.id, null);
  boolean exists = ProfileStore.getInstance().getAllProfileNames().contains(r.profile);
  if (stored == null && !exists && seed) {
   ProfileStore.getInstance().getOrCreateProfile(r.profile);
   if (!prefs.edit().putString(r.id, r.profile).commit()) throw new IllegalStateException("Metadata persistence failed");
   stored = r.profile; exists = true;
  }
  Registration.admit(true, r, stored, exists);
  event("registration", "id", r.id, "profile", stored, "exists", exists);
 }
 private WebResourceResponse response(String mime, String body) {
  return new WebResourceResponse(mime, "UTF-8", 200, "OK", Map.of("Cache-Control", "no-store"), new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));
 }
 private WebView web(String profileName, String name) {
  WebView web = new WebView(this);
  WebViewCompat.setProfile(web, profileName); // Before settings, client, cookies, or load.
  Profile profile = WebViewCompat.getProfile(web);
  event("profile-before-use", "view", name, "requested", profileName, "actual", profile.getName());
  web.getSettings().setJavaScriptEnabled(true); web.getSettings().setDomStorageEnabled(true);
  web.getSettings().setAllowFileAccess(false); web.getSettings().setAllowContentAccess(false);
  web.setWebViewClient(new WebViewClient() {
   @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest request) {
    android.net.Uri uri = request.getUrl();
    String host = uri.getHost();
    if ("https".equals(uri.getScheme()) && (uri.getPort() == -1 || uri.getPort() == 443) && (host.equals(java.net.URI.create(a.origin).getHost()) || host.equals(java.net.URI.create(b.origin).getHost()))) {
     String path = uri.getPath();
     // Test-only foreign app resolver: loaded frames test SOP, not loader containment.
     if ("/frame.html".equals(path)) { event("frame-served", "view", name, "url", uri.toString()); return response("text/html", "<!doctype html><body>loaded-" + uri.getQueryParameter("app") + "<script>parent.postMessage({marker:document.body.firstChild.textContent},'*')</script></body>"); }
     try {
      if ("/index.html".equals(path) || "/probe.js".equals(path)) return new WebResourceResponse(path.endsWith(".js") ? "text/javascript" : "text/html", "UTF-8", getAssets().open(path.substring(1)));
     } catch (Exception e) { event("asset-error", "path", path); }
     return response("text/plain", "Local miss, no network fallback");
    }
    if ("https".equals(uri.getScheme()) && "example.com".equals(host) && (uri.getPort() == -1 || uri.getPort() == 443)) {
     event("remote-network-request", "view", name, "url", uri.toString(), "mainFrame", request.isForMainFrame());
     return null; // Actual public TLS network path; no TLS override or interception.
    }
    return response("text/plain", "Unmapped research request");
   }
   @Override public void onReceivedError(WebView v, WebResourceRequest request, android.webkit.WebResourceError error) {
    event("load-error", "view", name, "mainFrame", request.isForMainFrame(), "code", error.getErrorCode());
   }
   @Override public void onReceivedSslError(WebView v, android.webkit.SslErrorHandler handler, android.net.http.SslError error) {
    event("tls-error", "view", name, "primaryError", error.getPrimaryError()); handler.cancel();
   }
  });
  webs.add(web); layout.addView(web, new LinearLayout.LayoutParams(-1, 120)); return web;
 }
 private void next() { if (step < steps.size()) steps.get(step++).run(); else save(); }
 private void poll(WebView web, String expression, int remaining, Value callback) {
  web.evaluateJavascript(expression, raw -> {
   try {
    Object outer = new JSONTokener(raw).nextValue();
    Object result = outer instanceof String ? new JSONTokener((String)outer).nextValue() : JSONObject.NULL;
    if (result instanceof JSONObject) { callback.accept(result); return; }
   } catch (Exception error) { event("decode-error", "exception", error.getClass().getSimpleName()); }
   if (remaining == 0) callback.accept(obj("timeout", true, "nativeUrl", String.valueOf(web.getUrl())));
   else main.postDelayed(() -> poll(web, expression, remaining - 1, callback), 100);
  });
 }
 private void local(WebView web, Registration r, String name, boolean write) {
  Registration other = r == a ? b : a;
  String url = r.origin + "/index.html?app=" + (r == a ? "a" : "b") + "&seed=" + write + "&tag=" + tag + "&other=" + java.net.URI.create(other.origin).getHost();
  String loadAction = "a-reload".equals(name) ? "reload" : "loadUrl";
  if ("reload".equals(loadAction)) web.reload(); else web.loadUrl(url);
  main.postDelayed(() -> poll(web, "JSON.stringify(window.t28 && window.t28.href === " + JSONObject.quote(url) + " ? window.t28 : null)", 200, result -> {
   Profile p = WebViewCompat.getProfile(web); p.getCookieManager().flush();
   samples.put(obj("name", name, "type", "local", "loadAction", loadAction, "profile", p.getName(), "document", result,
    "ownNativeCookies", nullable(p.getCookieManager().getCookie(r.origin)), "siblingNativeCookies", nullable(p.getCookieManager().getCookie(other.origin))));
   next();
  }), 400);
 }
 private Object nullable(String value) { return value == null ? JSONObject.NULL : value; }
 private String markers(String value) {
  if (value == null) return "";
  java.util.List<String> result = new java.util.ArrayList<>();
  for (String part : value.split(";")) if (part.trim().startsWith("t28_")) result.add(part.trim());
  return String.join("; ", result);
 }
 private void remote(WebView web, String owner, boolean write) {
  web.loadUrl("https://example.com/");
  String marker = tag + "-" + (owner.equals("a-shared") ? "a" : owner);
  String script = "JSON.stringify(location.origin === 'https://example.com' && document.title === 'Example Domain' && document.readyState === 'complete' ? {origin:location.origin,title:document.title,secureContext:isSecureContext,ready:document.readyState,before:document.cookie.split(';').map(x=>x.trim()).filter(x=>x.startsWith('t28_')).join('; ')} : null)";
  main.postDelayed(() -> poll(web, script, 300, before -> {
   if (((JSONObject)before).optBoolean("timeout")) { samples.put(obj("name", "remote-" + owner, "type", "remote", "before", before)); next(); return; }
   String cookieScript = (write ? "document.cookie='t28_remote=" + marker + "; Path=/; Max-Age=86400; Secure; SameSite=Lax';" : "")
    + "JSON.stringify({origin:location.origin,title:document.title,cookie:document.cookie.split(';').map(x=>x.trim()).filter(x=>x.startsWith('t28_')).join('; '),secureContext:isSecureContext})";
   web.evaluateJavascript(cookieScript, raw -> {
    try {
     Object outer = new JSONTokener(raw).nextValue(); Object after = new JSONTokener((String)outer).nextValue();
     Profile p = WebViewCompat.getProfile(web); p.getCookieManager().flush();
     samples.put(obj("name", "remote-" + owner, "type", "remote", "profile", p.getName(), "before", before, "after", after,
      "nativeCookies", markers(p.getCookieManager().getCookie("https://example.com/"))));
    } catch (Exception error) { event("remote-decode-error", "exception", error.getClass().getSimpleName()); }
    next();
   });
  }), 500);
 }
 private void save() {
  try (java.io.FileOutputStream out = openFileOutput("report.json", MODE_PRIVATE)) {
   out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
  } catch (Exception error) { throw new IllegalStateException(error); }
 }
}
