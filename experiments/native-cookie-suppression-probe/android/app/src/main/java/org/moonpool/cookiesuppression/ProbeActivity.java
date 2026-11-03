package org.moonpool.cookiesuppression;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.widget.LinearLayout;
import androidx.webkit.Profile;
import androidx.webkit.ProfileStore;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

/** Isolated observation fixture; no guest bridge or production runtime. */
public final class ProbeActivity extends Activity {
 private final Handler handler = new Handler(Looper.getMainLooper());
 private final Map<String, WebView> views = new LinkedHashMap<>();
 private final Map<String, Profile> profiles = new LinkedHashMap<>();
 private final JSONArray samples = new JSONArray(), events = new JSONArray();
 private LinearLayout layout;
 private JSONObject config, report;
 private JSONArray cases;
 private String run, base, stage = "";
 private int index;
 private final Map<WebView, JSONArray> errors = new LinkedHashMap<>();
 private static JSONObject obj(Object... fields) {
  JSONObject result = new JSONObject();
  try { for (int i=0; i<fields.length; i+=2) result.put((String)fields[i], fields[i+1]); }
  catch (Exception error) { throw new IllegalStateException(error); }
  return result;
 }
 private String asset(String name) throws Exception {
  try (java.io.InputStream input=getAssets().open(name); java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream()) {
   byte[] bytes=new byte[4096]; int read;
   while ((read=input.read(bytes))!=-1) out.write(bytes,0,read);
   return out.toString(StandardCharsets.UTF_8.name());
  }
 }
 private String owner(String view) { return view.startsWith("a") ? "a" : view; }
 @Override public void onCreate(Bundle saved) {
  super.onCreate(saved);
  run = getIntent().getStringExtra("run"); base = getIntent().getStringExtra("base");
  layout = new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL); setContentView(layout);
  report = obj("platform", "android", "run", run, "base", base, "samples", samples, "events", events,
   "sdk", android.os.Build.VERSION.SDK_INT, "release", android.os.Build.VERSION.RELEASE);
  try {
   if (!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)) throw new IllegalStateException("MULTI_PROFILE unavailable");
   config = new JSONObject(asset("config.json")); cases = config.getJSONArray("cases");
   android.content.pm.PackageInfo provider = WebViewCompat.getCurrentWebViewPackage(this);
   report.put("providerVersion", provider.versionName);
   for (String name : new String[]{"a", "b", "u"}) profiles.put(name, ProfileStore.getInstance().getOrCreateProfile("cookie-probe-" + run + "-" + name));
   makeViews();
   for (Profile p : profiles.values()) p.getCookieManager().setAcceptCookie(true);
   JSONObject partitionNames = new JSONObject();
   for (Map.Entry<String, Profile> pair : profiles.entrySet()) partitionNames.put(pair.getKey(), pair.getValue().getName());
   report.put("partitions", partitionNames); next();
  } catch (Exception error) { fail(error); }
 }
 private void makeViews() {
  for (String name : new String[]{"a1", "a2", "b", "h", "u"}) {
   String owner = owner(name);
   WebView web = new WebView(this);
   if (!owner.equals("h")) WebViewCompat.setProfile(web, profiles.get(owner).getName());
   Profile actual = WebViewCompat.getProfile(web);
   if (owner.equals("h")) profiles.put("h", actual);
   web.getSettings().setJavaScriptEnabled(true); web.getSettings().setDomStorageEnabled(true);
   web.getSettings().setAllowFileAccess(false); web.getSettings().setAllowContentAccess(false);
   errors.put(web, new JSONArray());
   web.setWebViewClient(new WebViewClient() {
    @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
     String host=request.getUrl().getHost(), path=request.getUrl().getPath();
     if ("localhost".equals(host)) return null;
     try {
      String expected = java.net.URI.create(config.getJSONObject("androidOrigins").getString(owner)).getHost();
      if (!"https".equals(request.getUrl().getScheme()) || !expected.equals(host)) return response("text/plain", "Unmapped fixture");
      if ("/page".equals(path)) return response("text/html", asset("page.html"));
      if ("/frame".equals(path)) return response("text/html", "<!doctype html><p>cookie-frame-ready</p>");
     } catch (Exception error) { return response("text/plain", "Fixture failure"); }
     return response("text/plain", "Local miss");
    }
    @Override public void onReceivedError(WebView v, WebResourceRequest r, android.webkit.WebResourceError e) {
     if (r.isForMainFrame()) errors.get(v).put(obj("code", e.getErrorCode(), "url", r.getUrl().toString()));
    }
    @Override public void onReceivedSslError(WebView v, android.webkit.SslErrorHandler h, android.net.http.SslError e) {
     errors.get(v).put(obj("tlsError", e.getPrimaryError())); h.cancel();
    }
   });
   views.put(name, web); layout.addView(web, new LinearLayout.LayoutParams(-1, 100));
   events.put(obj("event", "created", "view", name, "profile", actual.getName()));
  }
 }
 private WebResourceResponse response(String mime, String content) {
  return new WebResourceResponse(mime, "UTF-8", 200, "OK", Map.of("Cache-Control", "no-store"), new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8)));
 }
 private void next() {
  try {
   if (index == cases.length()) { report.put("complete", true); save(); return; }
   JSONObject c=cases.getJSONObject(index++); String nextStage=c.getString("stage");
   if (!stage.equals(nextStage)) {
    stage=nextStage;
    if (stage.equals("a-blocked")) profiles.get("a").getCookieManager().setAcceptCookie(false);
    if (stage.equals("ab-blocked")) profiles.get("b").getCookieManager().setAcceptCookie(false);
    if (stage.equals("recreated") || stage.equals("fresh-blocked")) {
     for (WebView web : views.values()) { layout.removeView(web); web.destroy(); }
     views.clear();
     if (stage.equals("fresh-blocked")) for (String o : new String[]{"a","b"}) {
      profiles.put(o,ProfileStore.getInstance().getOrCreateProfile("cookie-probe-"+run+"-fresh-"+o));
      profiles.get(o).getCookieManager().setAcceptCookie(false);
     }
     makeViews();
    }
    JSONObject policies=new JSONObject();
    for (Map.Entry<String, Profile> entry : profiles.entrySet()) policies.put(entry.getKey(), entry.getValue().getCookieManager().acceptCookie());
    events.put(obj("event", "policy", "stage", stage, "values", policies));
    if (!policies.getBoolean("h") || !policies.getBoolean("u") || (stage.equals("a-blocked") && !policies.getBoolean("b"))) {
     report.put("unsupported", "Cookie policy affected unrelated control partition"); report.put("complete", false); save(); return;
    }
   }
   WebView web=views.get(c.getString("view")); Profile p=WebViewCompat.getProfile(web);
   String origin=c.getString("kind").equals("remote") ? base : config.getJSONObject("androidOrigins").getString(c.getString("owner"));
   String url=origin + "/page?run="+run+"&case="+c.getString("id");
   boolean allows=p.getCookieManager().acceptCookie();
   errors.put(web, new JSONArray());
   events.put(obj("event", "load", "case", c.getString("id"), "policyAllows", allows, "profile", p.getName()));
   web.loadUrl(url); poll(web,c,url,allows,100);
  } catch (Exception error) { fail(error); }
 }
 private void poll(WebView web, JSONObject c, String url, boolean allows, int remaining) {
  web.evaluateJavascript("JSON.stringify(window.cookieProbe || null)", raw -> {
   try {
    Object outer = new JSONTokener(raw).nextValue();
    Object parsed = outer instanceof String ? new JSONTokener((String)outer).nextValue() : JSONObject.NULL;
    if (parsed instanceof JSONObject doc && c.getString("id").equals(doc.optString("case")) && (doc.optBoolean("complete") || doc.has("error"))) {
     Profile p=WebViewCompat.getProfile(web); p.getCookieManager().flush();
     String nativeCookies=p.getCookieManager().getCookie(url); JSONArray values=new JSONArray();
     if (nativeCookies != null) for (String part : nativeCookies.split(";")) if (part.trim().startsWith("t28_")) values.put(part.trim().split("=",2)[1]);
     String actual="unknown";
     for (Map.Entry<String, Profile> pair : profiles.entrySet()) if (pair.getValue().getName().equals(p.getName())) actual=pair.getKey();
     JSONObject sample=new JSONObject(c.toString());
     sample.put("policyAllows",allows); sample.put("actualPartition",actual); sample.put("profile",p.getName());
     sample.put("document",doc); sample.put("nativeCookieValues",values); sample.put("nativeCookies",nativeCookies == null ? "" : nativeCookies);
     sample.put("policyBeforeLoad",true); sample.put("loadErrors",errors.get(web)); sample.put("nativeUrl",web.getUrl());
     samples.put(sample); saveProgress(); next(); return;
    }
    if (remaining==0) { report.put("failedCase",c.getString("id")); report.put("lastDocument",parsed); report.put("complete",false); save(); return; }
    handler.postDelayed(() -> poll(web,c,url,allows,remaining-1),100);
   } catch (Exception error) { fail(error); }
  });
 }
 private void fail(Exception error) { try { report.put("error",error.toString()); report.put("complete",false); } catch(Exception ignored) { } save(); }
 private void saveProgress() { try (java.io.FileOutputStream out=openFileOutput("progress.json",MODE_PRIVATE)) { out.write(report.toString(2).getBytes(StandardCharsets.UTF_8)); } catch(Exception ignored) { } }
 private void save() { try (java.io.FileOutputStream out=openFileOutput("report.json",MODE_PRIVATE)) { out.write(report.toString(2).getBytes(StandardCharsets.UTF_8)); } catch(Exception ignored) { } }
}
