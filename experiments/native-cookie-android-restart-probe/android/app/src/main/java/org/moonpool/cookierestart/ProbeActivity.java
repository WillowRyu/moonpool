package org.moonpool.cookierestart;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import androidx.webkit.Profile;
import androidx.webkit.ProfileStore;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.io.ByteArrayInputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

/** Writes public fixture stores in one process and answers hasCookies for them in a new one. */
public final class ProbeActivity extends Activity {
 private static final String GUEST="https://mp-probe.invalid";
 private final Handler main=new Handler(Looper.getMainLooper());
 private LinearLayout layout;
 private String run,base,mode,cycle;
 private JSONObject report;
 private final JSONArray seeded=new JSONArray(),checks=new JSONArray(),errors=new JSONArray();
 static JSONObject obj(Object... fields) {
  JSONObject o=new JSONObject();try {for(int i=0;i<fields.length;i+=2)o.put((String)fields[i],fields[i+1]);}catch(Exception e){throw new IllegalStateException(e);}return o;
 }
 String asset(String name) throws Exception {
  try(java.io.InputStream input=getAssets().open(name);java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream()) {
   byte[] bytes=new byte[4096];int n;while((n=input.read(bytes))!=-1)out.write(bytes,0,n);return out.toString(StandardCharsets.UTF_8.name());
  }
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);run=getIntent().getStringExtra("run");base=getIntent().getStringExtra("base");mode=getIntent().getStringExtra("mode");cycle=getIntent().getStringExtra("cycle");
  layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);setContentView(layout);
  String only=getIntent().getStringExtra("only");
  report=obj("platform","android","run",run,"base",base,"mode",mode,"cycle",cycle,"seeded",seeded,"checks",checks,"errors",errors,"complete",false);
  try {
   if(only!=null)report.put("only",only);
   if(!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE))throw new IllegalStateException("MULTI_PROFILE unavailable");
   report.put("providerVersion",WebViewCompat.getCurrentWebViewPackage(this).versionName);report.put("release",android.os.Build.VERSION.RELEASE);
   JSONArray stores=new JSONObject(asset("config.json")).getJSONArray("stores");
   CompletableFuture<Void> chain=CompletableFuture.completedFuture(null);
   if(mode.equals("seed")) {
    // Cookies written shortly before an exit may not survive it, so ordinary stores settle first.
    // Late stores then measure that window on purpose.
    for(int i=0;i<stores.length();i++){JSONObject c=stores.getJSONObject(i);if(!c.getBoolean("brandNew")&&!c.getBoolean("late"))chain=chain.thenCompose(v->seed(c));}
    chain=chain.thenCompose(v->delay(45000));
    for(int i=0;i<stores.length();i++){JSONObject c=stores.getJSONObject(i);if(c.getBoolean("late"))chain=chain.thenCompose(v->seed(c));}
   } else {
    for(int i=0;i<stores.length();i++){JSONObject c=stores.getJSONObject(i);if(only==null||only.equals(c.getString("id")))chain=chain.thenCompose(v->check(c));}
   }
   chain.whenComplete((v,error)->{try{report.put("complete",error==null);if(error!=null)report.put("error",error.toString());}catch(Exception ignored){}save("report.json");});
  }catch(Exception e){try{report.put("error",e.toString());}catch(Exception ignored){}save("report.json");}
 }
 String profileName(JSONObject c) throws Exception {return "restart-"+cycle+"-"+c.getString("id");}
 String origin(String top){return top.equals("guest")?GUEST:base.replace("localhost",top);}
 WebView web(String profile,boolean thirdParty){
  WebView web=new WebView(this);WebViewCompat.setProfile(web,profile);
  web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);
  if(thirdParty)ProfileStore.getInstance().getProfile(profile).getCookieManager().setAcceptThirdPartyCookies(web,true);
  web.setWebViewClient(new WebViewClient(){
   @Override public WebResourceResponse shouldInterceptRequest(WebView w,WebResourceRequest request){
    String host=request.getUrl().getHost(),path=request.getUrl().getPath();
    if("localhost".equals(host)||"127.0.0.1".equals(host))return null;
    try {
     if("/frame".equals(path))return response(asset("frame.html"));
     if("/storage".equals(path))return response(asset("storage.html"));
    }catch(Exception ignored){}
    return response("Unmapped research resource");
   }
   @Override public void onReceivedError(WebView w,WebResourceRequest request,android.webkit.WebResourceError error){if(request.isForMainFrame())errors.put(obj("url",request.getUrl().getPath(),"code",error.getErrorCode()));}
   @Override public void onReceivedSslError(WebView w,android.webkit.SslErrorHandler handler,android.net.http.SslError error){errors.put(obj("tlsError",error.getPrimaryError()));handler.cancel();}
  });layout.addView(web,new LinearLayout.LayoutParams(-1,100));return web;
 }
 WebResourceResponse response(String text){return new WebResourceResponse("text/html","UTF-8",200,"OK",Map.of("Cache-Control","no-store"),new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)));}
 void discard(WebView web){web.stopLoading();layout.removeView(web);web.destroy();}
 CompletableFuture<Void> delay(long ms){CompletableFuture<Void> done=new CompletableFuture<>();main.postDelayed(()->done.complete(null),ms);return done;}
 /** A deadline is a recorded outcome here: the verifier decides what a failed load means. */
 CompletableFuture<String> poll(WebView web,String script,int left){
  CompletableFuture<String> result=new CompletableFuture<>();
  web.evaluateJavascript(script,raw->{
   if(raw!=null&&!raw.equals("null")){result.complete(raw);return;}
   if(left==0){result.complete(null);return;}
   main.postDelayed(()->poll(web,script,left-1).thenAccept(result::complete),100);
  });return result;
 }
 CompletableFuture<Boolean> visit(String profile,JSONObject c,String step,String top,String write) throws Exception {
  String service=c.getString("service"),page=origin(service)+"/page?run="+run+"&case="+c.getString("id")+"&step="+step+"&write="+write;
  boolean direct=top.equals(service);WebView web=web(profile,c.getBoolean("thirdParty"));
  web.loadUrl(direct?page:origin(top)+"/frame?target="+URLEncoder.encode(page,"UTF-8"));
  return poll(web,direct?"window.pageResult||null":"window.frameResult||null",50).thenApply(raw->{discard(web);return raw!=null;});
 }
 CompletableFuture<Object> storage(String profile,String id,boolean write){
  WebView web=web(profile,false);web.loadUrl(GUEST+"/storage?token="+id+"&seed="+(write?"1":"0"));
  return poll(web,"window.storageReady ? JSON.stringify(window.storageReady):null",80).thenApply(raw->{
   discard(web);
   try {return raw==null?JSONObject.NULL:new JSONTokener((String)new JSONTokener(raw).nextValue()).nextValue();}catch(Exception e){return JSONObject.NULL;}
  });
 }
 CompletableFuture<Void> seed(JSONObject c){
  try {
   String id=c.getString("id"),name=profileName(c);
   Profile profile=ProfileStore.getInstance().getOrCreateProfile(name);CookieManager manager=profile.getCookieManager();
   if(c.getBoolean("denyBefore"))manager.setAcceptCookie(false);
   JSONArray loaded=new JSONArray(),steps=c.getJSONArray("steps");
   CompletableFuture<Void> chain=CompletableFuture.completedFuture(null);
   for(int i=0;i<steps.length();i++){JSONObject step=steps.getJSONObject(i);chain=chain.thenCompose(v->{try{return visit(name,c,step.getString("step"),step.getString("top"),"header").thenAccept(loaded::put);}catch(Exception e){return CompletableFuture.failedFuture(e);}});}
   Object[] ready={JSONObject.NULL};
   if(c.getBoolean("storage"))chain=chain.thenCompose(v->storage(name,id,true).thenAccept(data->ready[0]=data!=JSONObject.NULL));
   return chain.thenCompose(v->delay((long)Math.max(300,c.optDouble("wait",0)*1000))).thenAccept(v->{
    boolean has=manager.hasCookies();
    if(c.optBoolean("denyAfter"))manager.setAcceptCookie(false);
    synchronized(seeded){seeded.put(obj("case",id,"kind",c.optString("kind"),"profile",name,"visitsLoaded",loaded,"storageReady",ready[0],"hasCookies",has));}
    save("progress.json");
   });
  }catch(Exception e){return CompletableFuture.failedFuture(e);}
 }
 /**
  * "bare" answers before anything else touches this profile, "view" after a never-loaded view on it,
  * and "policy" after the accepted deny step. Every store then answers under deny. Witnesses run
  * under allow, because Android's deny policy withholds retained cookies from requests.
  */
 CompletableFuture<Void> check(JSONObject c){
  try {
   String id=c.getString("id"),order=c.getString("order"),name=profileName(c);
   Profile profile=ProfileStore.getInstance().getOrCreateProfile(name);CookieManager manager=profile.getCookieManager();
   WebView keeper=order.equals("view")?web(name,false):null;
   if(order.equals("policy"))manager.setAcceptCookie(false);
   long started=System.nanoTime();boolean first=manager.hasCookies();long elapsed=(System.nanoTime()-started)/1000000;
   boolean acceptAfterFirst=manager.acceptCookie();
   manager.setAcceptCookie(false);
   boolean afterPolicy=manager.hasCookies(),acceptAtRule=manager.acceptCookie();
   JSONObject entry=obj("case",id,"kind",c.getString("kind"),"order",order,"profile",name,"first",first,"firstMs",elapsed,"acceptAfterFirst",acceptAfterFirst,"afterPolicy",afterPolicy,"acceptAtRule",acceptAtRule);
   return delay(1000).thenCompose(v->{
    try {
     entry.put("later",manager.hasCookies());
     manager.setAcceptCookie(true);entry.put("acceptDuringWitness",manager.acceptCookie());
     return visit(name,c,"witness-first",c.getString("service"),"none").thenCompose(a->{
      try {entry.put("witnessFirstLoaded",a);return visit(name,c,"witness-xsite",c.getString("seedTop"),"none");}catch(Exception e){return CompletableFuture.failedFuture(e);}
     });
    }catch(Exception e){return CompletableFuture.failedFuture(e);}
   }).thenCompose(b->{
    try {
     entry.put("witnessXsiteLoaded",b);manager.setAcceptCookie(false);
     return c.getBoolean("storage")?storage(name,id,false):CompletableFuture.completedFuture((Object)JSONObject.NULL);
    }catch(Exception e){return CompletableFuture.failedFuture(e);}
   }).thenAccept(data->{
    try {entry.put("storage",data);entry.put("finalHasCookies",manager.hasCookies());}catch(Exception e){throw new IllegalStateException(e);}
    if(keeper!=null)discard(keeper);
    synchronized(checks){checks.put(entry);}
    save("progress.json");
   });
  }catch(Exception e){return CompletableFuture.failedFuture(e);}
 }
 void save(String name){try(java.io.FileOutputStream out=openFileOutput(name,MODE_PRIVATE)){out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}}
}
