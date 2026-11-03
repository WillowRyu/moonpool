package org.moonpool.cookieadmission;

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
import androidx.webkit.CookieManagerCompat;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

/** Public fixture observations; the setup observer is not an admitted guest. */
public final class ProbeActivity extends Activity {
 private final Handler main=new Handler(Looper.getMainLooper());
 private LinearLayout layout;
 private String run,base;
 private JSONObject config,report;
 private final JSONArray samples=new JSONArray(),errors=new JSONArray(),guestResources=new JSONArray();
 private Profile hostProfile;
 private WebView host;
 static JSONObject obj(Object... fields) {
  JSONObject o=new JSONObject();try {for(int i=0;i<fields.length;i+=2)o.put((String)fields[i],fields[i+1]);}catch(Exception e){throw new IllegalStateException(e);}return o;
 }
 String asset(String name) throws Exception {
  try(java.io.InputStream input=getAssets().open(name);java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream()) {
   byte[] bytes=new byte[4096];int n;while((n=input.read(bytes))!=-1)out.write(bytes,0,n);return out.toString(StandardCharsets.UTF_8.name());
  }
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);run=getIntent().getStringExtra("run");base=getIntent().getStringExtra("base");
  layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);setContentView(layout);
  report=obj("platform","android","run",run,"base",base,"samples",samples,"errors",errors,"guestResources",guestResources,"complete",false,"gateCases",new JSONObject(GateCases.runAll()));
  try {
   if(!WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE))throw new IllegalStateException("MULTI_PROFILE unavailable");
   config=new JSONObject(asset("config.json"));
   report.put("providerVersion",WebViewCompat.getCurrentWebViewPackage(this).versionName);report.put("release",android.os.Build.VERSION.RELEASE);
   report.put("getCookieInfoSupported",WebViewFeature.isFeatureSupported(WebViewFeature.GET_COOKIE_INFO));
   host=web(null,null);hostProfile=WebViewCompat.getProfile(host);hostProfile.getCookieManager().setAcceptCookie(true);
   CompletableFuture<Void> chain=network(host,base+"/seed?run="+run+"&case=host").thenApply(v->null);
   JSONArray cases=config.getJSONArray("cases");
   for(int i=0;i<cases.length();i++){JSONObject c=cases.getJSONObject(i);chain=chain.thenCompose(v->caseRun(c));}
   chain.whenComplete((v,error)->{try{report.put("complete",error==null);if(error!=null)report.put("error",error.toString());}catch(Exception ignored){}save("report.json");});
  }catch(Exception e){try{report.put("error",e.toString());}catch(Exception ignored){}save("report.json");}
 }
 WebView web(String profile,String origin) {
  WebView web=new WebView(this);if(profile!=null)WebViewCompat.setProfile(web,profile);
  web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);
  web.setWebViewClient(new WebViewClient(){
   @Override public WebResourceResponse shouldInterceptRequest(WebView w,WebResourceRequest request){
    String host=request.getUrl().getHost(),path=request.getUrl().getPath();
    if("localhost".equals(host)||"127.0.0.1".equals(host))return null;
    try {
     if(origin!=null&&java.net.URI.create(origin).getHost().equals(host)){
      if("/prepare".equals(path))return response(asset("storage.html"));
      if("/guest".equals(path)){
       synchronized(guestResources){guestResources.put(request.getUrl().toString());}
       return response("<!doctype html><script>window.guestReady=new URLSearchParams(location.search).get('token');</script>");
      }
     }
    }catch(Exception ignored){}
    return response("Unmapped research resource");
   }
   @Override public void onReceivedError(WebView w,WebResourceRequest request,android.webkit.WebResourceError error){if(request.isForMainFrame())errors.put(obj("url",request.getUrl().toString(),"code",error.getErrorCode()));}
   @Override public void onReceivedSslError(WebView w,android.webkit.SslErrorHandler handler,android.net.http.SslError error){errors.put(obj("tlsError",error.getPrimaryError()));handler.cancel();}
  });layout.addView(web,new LinearLayout.LayoutParams(-1,100));return web;
 }
 WebResourceResponse response(String text){return new WebResourceResponse("text/html","UTF-8",200,"OK",Map.of("Cache-Control","no-store"),new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)));}
 void discard(WebView web){web.stopLoading();layout.removeView(web);web.destroy();}
 CompletableFuture<Object> js(WebView web,String script){
  CompletableFuture<Object> future=new CompletableFuture<>();web.evaluateJavascript(script,raw->{try{Object outer=new JSONTokener(raw).nextValue();future.complete(outer instanceof String?new JSONTokener((String)outer).nextValue():outer);}catch(Exception e){future.completeExceptionally(e);}});return future;
 }
 CompletableFuture<Object> poll(WebView web,String script,int left){
  return js(web,script).thenCompose(value->{if(value!=JSONObject.NULL&&value!=null)return CompletableFuture.completedFuture(value);
   if(left==0)return CompletableFuture.failedFuture(new IllegalStateException("Fixture observation deadline"));
   CompletableFuture<Object> pending=new CompletableFuture<>();main.postDelayed(()->poll(web,script,left-1).whenComplete((v,e)->{if(e!=null)pending.completeExceptionally(e);else pending.complete(v);}),100);return pending;});
 }
 CompletableFuture<Object> network(WebView web,String url){web.loadUrl(url);return poll(web,"JSON.stringify(window.networkReady==="+JSONObject.quote(url)+" ? {ready:true} : null)",120);}
 CompletableFuture<Object> prepare(WebView web,String origin,String token,boolean seed){web.loadUrl(origin+"/prepare?token="+token+"&seed="+(seed?"1":"0"));return poll(web,"JSON.stringify(window.storageReady || null)",120);}
 CompletableFuture<Object> storage(WebView web){return js(web,"window.afterRead=null; window.readPublicData().then(v=>window.afterRead=v); JSON.stringify(null)").thenCompose(v->poll(web,"JSON.stringify(window.afterRead || null)",120));}
 List<String> cookies(Profile profile,String url){
  List<String> list=new ArrayList<>();
  if(WebViewFeature.isFeatureSupported(WebViewFeature.GET_COOKIE_INFO))list.addAll(CookieManagerCompat.getCookieInfo(profile.getCookieManager(),url));
  else {String raw=profile.getCookieManager().getCookie(url);if(raw!=null)Collections.addAll(list,raw.split("; "));}
  Collections.sort(list);return list;
 }
 JSONArray names(List<String> cookies){JSONArray names=new JSONArray();for(String cookie:cookies)names.put(cookie.split("=",2)[0]);return names;}
 CompletableFuture<Void> caseRun(JSONObject c){
  try {
   String id=c.getString("id"),token=run+"-"+id,origin=config.getJSONObject("origins").getString(id);
   Profile profile=ProfileStore.getInstance().getOrCreateProfile("admission-"+run+"-"+id);profile.getCookieManager().setAcceptCookie(true);
   WebView observer=web(profile.getName(),origin),net=web(profile.getName(),null);
   String service=base.replace("localhost",c.getString("host"));String query="?run="+run+"&case="+id;
   String receipt=service+(id.equals("offpath")?"/hidden/echo":"/echo")+query;
   return prepare(observer,origin,token,true)
    .thenCompose(v->network(net,service+"/seed"+query)).thenCompose(v->network(net,receipt))
    .thenCompose(v->network(net,base+"/visible"+query)).thenCompose(v->js(net,"JSON.stringify(document.cookie)"))
    .thenCompose(visible->{profile.getCookieManager().setAcceptCookie(false);
     return phase(c,"initial",profile,observer,origin,token,receipt,visible)
      .thenCompose(v->{discard(observer);discard(net);Profile reopened=ProfileStore.getInstance().getOrCreateProfile(profile.getName());WebView read=web(reopened.getName(),origin);
       return prepare(read,origin,token,false).thenCompose(x->phase(c,"reopened",reopened,read,origin,token,receipt,visible)).thenRun(()->discard(read));});});
  }catch(Exception e){return CompletableFuture.failedFuture(e);}
 }
 CompletableFuture<Void> phase(JSONObject c,String phase,Profile profile,WebView observer,String origin,String token,String receipt,Object visible){
  List<String> before=cookies(profile,receipt);WebView candidate=web(profile.getName(),origin);
  int[] loads={0};boolean[] presence={false};CompletableFuture<String> verdict=new CompletableFuture<>();
  AdmissionGate gate=new AdmissionGate((name,done)->main.post(()->{
   presence[0]=profile.getCookieManager().hasCookies();
   done.accept(profile.getCookieManager().acceptCookie()?AdmissionGate.Presence.UNKNOWN:presence[0]?AdmissionGate.Presence.PRESENT:AdmissionGate.Presence.EMPTY);
  }));
  gate.admit(token,()->{loads[0]++;candidate.loadUrl(origin+"/guest?token="+token);verdict.complete("admitted");},()->{discard(candidate);verdict.complete("refused");});
  return verdict.thenCompose(decision->{
   CompletableFuture<Object> guest=decision.equals("admitted")?poll(candidate,"JSON.stringify(window.guestReady || null)",120):CompletableFuture.completedFuture(JSONObject.NULL);
   return guest.thenCompose(marker->storage(observer).thenAccept(data->{
    List<String> after=cookies(profile,receipt);
    samples.put(obj("case",c.optString("id"),"phase",phase,"partition",profile.getName(),"presence",presence[0],"policyAllows",profile.getCookieManager().acceptCookie(),
     "beforeCookies",new JSONArray(before),"afterCookies",new JSONArray(after),"beforeNames",names(before),"afterNames",names(after),"storage",data,"expectedStorage",token,
     "decision",decision,"loadCalls",loads[0],"guestMarker",marker,"visibleJsCookie",visible,"hostPolicyAllows",hostProfile.getCookieManager().acceptCookie(),"hostCookiePresent",hostProfile.getCookieManager().hasCookies(),
     "hostCookie",hostProfile.getCookieManager().getCookie(base+"/visible"),"urlScopedCookie",profile.getCookieManager().getCookie(base+"/visible")==null?"":profile.getCookieManager().getCookie(base+"/visible")));
    save("progress.json");gate.close();
   }));
  });
 }
 void save(String name){try(java.io.FileOutputStream out=openFileOutput(name,MODE_PRIVATE)){out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}}
}
