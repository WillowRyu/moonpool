package org.moonpool.httpokhttp;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Authenticator;
import java.net.CacheRequest;
import java.net.CacheResponse;
import java.net.CookieHandler;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.HttpCookie;
import java.net.HttpURLConnection;
import java.net.PasswordAuthentication;
import java.net.Proxy;
import java.net.ProxySelector;
import java.net.ResponseCache;
import java.net.SocketAddress;
import java.net.URI;
import java.net.URL;
import java.net.URLConnection;
import java.nio.charset.StandardCharsets;
import java.security.cert.X509Certificate;
import java.util.List;
import java.util.Map;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import okhttp3.Call;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okio.BufferedSink;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Plays a host app that set process-wide HTTP state, then sends requests through OkHttp configured as a broker
 * would be. The same globals on HttpURLConnection are positive controls in the same run. All credentials are
 * public fixture values, and the trust-everything state exists only for the two foreign host cases.
 */
public final class ProbeActivity extends Activity {
 private String run;
 private int port,control;
 private JSONObject report;
 private final JSONArray observations=new JSONArray(),errors=new JSONArray();
 private RecordingManager lastManager;
 private ProxySelector originalProxySelector;
 private SSLSocketFactory originalSocketFactory;
 private HostnameVerifier originalVerifier;
 static JSONObject obj(Object... fields) {
  JSONObject o=new JSONObject();try {for(int i=0;i<fields.length;i+=2)o.put((String)fields[i],fields[i+1]);}catch(Exception e){throw new IllegalStateException(e);}return o;
 }
 static String read(InputStream input) throws Exception {
  if(input==null)return "";
  try(input;ByteArrayOutputStream out=new ByteArrayOutputStream()) {
   byte[] bytes=new byte[4096];int n;while((n=input.read(bytes))!=-1)out.write(bytes,0,n);return out.toString(StandardCharsets.UTF_8.name());
  }
 }
 static JSONArray setCookies(Map<String,List<String>> headers) {
  JSONArray found=new JSONArray();
  for(Map.Entry<String,List<String>> entry:headers.entrySet())
   if(entry.getKey()!=null&&entry.getKey().equalsIgnoreCase("Set-Cookie"))for(String value:entry.getValue())found.put(value);
  return found;
 }
 static JSONObject getEvent(URI uri){return obj("op","get","uri",uri.toString());}
 static JSONObject putEvent(URI uri,Map<String,List<String>> headers){return obj("op","put","uri",uri.toString(),"setCookie",setCookies(headers));}

 static final class RecordingHandler extends CookieHandler {
  final JSONArray events;
  RecordingHandler(JSONArray events){this.events=events;}
  @Override public Map<String,List<String>> get(URI uri,Map<String,List<String>> headers){events.put(getEvent(uri));return Map.of("Cookie",List.of("host_ambient=sentinel"));}
  @Override public void put(URI uri,Map<String,List<String>> headers){events.put(putEvent(uri,headers));}
 }
 static final class RecordingManager extends CookieManager {
  JSONArray events;
  RecordingManager(JSONArray events){super(null,CookiePolicy.ACCEPT_ALL);this.events=events;}
  @Override public Map<String,List<String>> get(URI uri,Map<String,List<String>> headers) throws IOException {events.put(getEvent(uri));return super.get(uri,headers);}
  @Override public void put(URI uri,Map<String,List<String>> headers) throws IOException {events.put(putEvent(uri,headers));super.put(uri,headers);}
 }
 static final class RecordingAuthenticator extends Authenticator {
  /** The harness asking whether its own authenticator is in place, which must not look like a request. */
  static volatile boolean harnessCheck;
  final JSONArray events;final boolean answer;
  RecordingAuthenticator(JSONArray events,boolean answer){this.events=events;this.answer=answer;}
  @Override protected PasswordAuthentication getPasswordAuthentication(){
   if(harnessCheck)return new PasswordAuthentication("harness","check".toCharArray());
   events.put(obj("host",String.valueOf(getRequestingHost()),"scheme",String.valueOf(getRequestingScheme()),"url",String.valueOf(getRequestingURL())));
   return answer?new PasswordAuthentication("moonpool-fixture-user","not-a-secret".toCharArray()):null;
  }
 }
 static final class RecordingResponseCache extends ResponseCache {
  final JSONArray events;
  RecordingResponseCache(JSONArray events){this.events=events;}
  @Override public CacheResponse get(URI uri,String method,Map<String,List<String>> headers){events.put(getEvent(uri));return null;}
  @Override public CacheRequest put(URI uri,URLConnection connection){events.put(obj("op","put","uri",uri.toString()));return null;}
 }
 static final class RecordingProxySelector extends ProxySelector {
  final JSONArray events;
  RecordingProxySelector(JSONArray events){this.events=events;}
  @Override public List<Proxy> select(URI uri){events.put(obj("uri",uri.toString()));return List.of(Proxy.NO_PROXY);}
  @Override public void connectFailed(URI uri,SocketAddress address,IOException e){}
 }
 /** Stands for a host that turned off validation for its own traffic. Only the foreign host cases install it. */
 @SuppressLint({"TrustAllX509TrustManager","CustomX509TrustManager","BadHostnameVerifier","AllowAllHostnameVerifier"})
 static void installGlobalTrustAll() throws Exception {
  X509TrustManager everything=new X509TrustManager(){
   @Override public void checkClientTrusted(X509Certificate[] chain,String type){}
   @Override public void checkServerTrusted(X509Certificate[] chain,String type){}
   @Override public X509Certificate[] getAcceptedIssuers(){return new X509Certificate[0];}
  };
  SSLContext context=SSLContext.getInstance("TLS");context.init(null,new TrustManager[]{everything},null);
  HttpsURLConnection.setDefaultSSLSocketFactory(context.getSocketFactory());
  HttpsURLConnection.setDefaultHostnameVerifier((host,session)->true);
 }
 static void install(CookieHandler handler,Authenticator authenticator){CookieHandler.setDefault(handler);Authenticator.setDefault(authenticator);}
 static boolean authenticatorVisible(){
  RecordingAuthenticator.harnessCheck=true;
  try{return Authenticator.requestPasswordAuthentication("probe.invalid",null,443,"https","probe","Basic")!=null;}finally{RecordingAuthenticator.harnessCheck=false;}
 }
 void resetGlobals(){
  install(null,null);ResponseCache.setDefault(null);ProxySelector.setDefault(originalProxySelector);
  HttpsURLConnection.setDefaultSSLSocketFactory(originalSocketFactory);HttpsURLConnection.setDefaultHostnameVerifier(originalVerifier);
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);run=getIntent().getStringExtra("run");port=getIntent().getIntExtra("port",0);control=getIntent().getIntExtra("control",0);
  report=obj("platform","android","run",run,"release",android.os.Build.VERSION.RELEASE,"sdkInt",android.os.Build.VERSION.SDK_INT,"observations",observations,"errors",errors,"complete",false);
  new Thread(this::execute).start();
 }
 void execute(){
  try {
   originalProxySelector=ProxySelector.getDefault();originalSocketFactory=HttpsURLConnection.getDefaultSSLSocketFactory();originalVerifier=HttpsURLConnection.getDefaultHostnameVerifier();
   report.put("globalsAtStart",obj("cookieHandlerNull",CookieHandler.getDefault()==null,"authenticatorNull",!authenticatorVisible(),"responseCacheNull",ResponseCache.getDefault()==null));
   report.put("okhttpVersion",okhttp3.OkHttp.VERSION);
   JSONArray cases;
   try(InputStream input=getAssets().open("cases.json")){cases=new JSONArray(read(input));}
   for(int i=0;i<cases.length();i++){
    try{observations.put(perform(cases.getJSONObject(i)));}finally{resetGlobals();}
    save("progress.json");
   }
   report.put("complete",true);
  }catch(Exception e){errors.put(obj("error",e.toString()));}
  save("report.json");
 }
 CookieHandler handlerFor(JSONObject c,JSONArray events) throws Exception {
  String kind=c.optString("handler");
  switch(kind){
   case "":return null;
   case "recording":return new RecordingHandler(events);
   case "previous":lastManager.events=events;return lastManager;
   default:
  }
  RecordingManager manager=new RecordingManager(events);
  if(kind.equals("manager-seeded")){
   HttpCookie cookie=new HttpCookie("host_session","host-fixture");cookie.setPath("/");cookie.setDomain("localhost");
   manager.getCookieStore().add(new URI("https://localhost:"+port+"/"),cookie);
  }else if(!kind.equals("manager"))throw new IllegalArgumentException(kind);
  lastManager=manager;
  return manager;
 }
 static Authenticator authenticatorFor(JSONObject c,JSONArray events){
  switch(c.optString("authenticator")){
   case "":return null;
   case "credentials":return new RecordingAuthenticator(events,true);
   case "null":return new RecordingAuthenticator(events,false);
   default:throw new IllegalArgumentException(c.optString("authenticator"));
  }
 }
 /** Cookie jar and authenticator are deliberately left at their defaults, because those defaults are what is being measured. */
 static OkHttpClient clientFor(String kind){
  if(kind.equals("default"))return new OkHttpClient();
  OkHttpClient.Builder builder=new OkHttpClient.Builder().followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false).cache(null);
  if(kind.equals("broker-no-proxy"))builder.proxy(Proxy.NO_PROXY);
  if(kind.equals("broker-interceptor"))builder.addNetworkInterceptor(chain->{
   // The resend decision happens above network interceptors, so hiding the header there is the only per-client lever.
   Response response=chain.proceed(chain.request());
   String value=response.header("Retry-After");
   return value==null?response:response.newBuilder().removeHeader("Retry-After").header("X-Moonpool-Retry-After",value).build();
  });
  return builder.build();
 }
 static RequestBody oneShot(byte[] bytes){
  return new RequestBody(){
   @Override public MediaType contentType(){return null;}
   @Override public long contentLength(){return bytes.length;}
   @Override public void writeTo(BufferedSink sink) throws IOException {sink.write(bytes);}
   @Override public boolean isOneShot(){return true;}
  };
 }
 String url(JSONObject c) throws Exception {
  String host=c.optBoolean("foreignHost")?"10.0.2.2":"localhost";
  return "https://"+host+":"+port+c.getString("path")+"?run="+run+"&case="+c.optString("requestCase",c.getString("id"));
 }
 Request request(JSONObject c) throws Exception {
  RequestBody body=null;
  if(c.has("body")){
   byte[] bytes=c.getString("body").getBytes(StandardCharsets.UTF_8);
   body=c.optBoolean("oneShot")?oneShot(bytes):RequestBody.create(bytes,null);
  }
  Request.Builder builder=new Request.Builder().url(url(c)).method(c.optString("method","GET"),body);
  if(c.has("attachCookie"))builder.header("Cookie",c.getString("attachCookie"));
  if(c.has("presetAuthorization"))builder.header("Authorization",c.getString("presetAuthorization"));
  return builder.build();
 }
 boolean ask(String path,JSONObject c) throws Exception {
  HttpURLConnection conn=(HttpURLConnection)new URL("https://localhost:"+control+path+"?run="+run+"&case="+c.getString("id")).openConnection();
  conn.setConnectTimeout(10000);conn.setReadTimeout(10000);
  String body=read(conn.getInputStream());conn.disconnect();
  return new JSONObject(body).optBoolean("held");
 }
 static void headersInto(JSONObject item,Response response) throws Exception {
  item.put("status",response.code());
  List<String> fields=response.headers("Set-Cookie");
  if(!fields.isEmpty())item.put("setCookieFields",new JSONArray(fields));
  String location=response.header("Location");
  if(location!=null)item.put("location",location);
  String retry=response.header("Retry-After"),kept=response.header("X-Moonpool-Retry-After");
  if(retry!=null)item.put("retryAfterVisible",retry);
  if(kept!=null)item.put("preservedRetryAfter",kept);
 }
 JSONObject perform(JSONObject c) throws Exception {
  JSONObject item=empty(c.getString("id"));
  JSONArray handlerEvents=item.getJSONArray("handlerEvents"),authEvents=item.getJSONArray("authenticatorEvents");
  CookieHandler handler=handlerFor(c,handlerEvents);
  Authenticator authenticator=authenticatorFor(c,authEvents);
  if(c.optBoolean("responseCache"))ResponseCache.setDefault(new RecordingResponseCache(item.getJSONArray("responseCacheEvents")));
  if(c.optBoolean("proxySelector"))ProxySelector.setDefault(new RecordingProxySelector(item.getJSONArray("proxySelectorEvents")));
  if(c.optBoolean("trustAll"))installGlobalTrustAll();
  boolean late=c.optString("install").equals("after-call");
  if(!late)install(handler,authenticator);
  String clientKind=c.optString("client","broker");
  try {
   if(clientKind.equals("huc")){performHuc(c,item);return item;}
   Call call=clientFor(clientKind).newCall(request(c));
   // A broker's shared client is built long before a host may set anything, so setting them now is that order.
   if(late)install(handler,authenticator);
   item.put("handlerVisible",CookieHandler.getDefault()!=null);
   item.put("authenticatorVisible",authenticatorVisible());
   String kind=c.optString("kind");
   if(kind.startsWith("hold"))performHold(c,item,call);
   else try(Response response=call.execute()){
    headersInto(item,response);
    item.put("bodyText",response.body().string());
   }
  }catch(Exception e){
   item.put("error",e.getClass().getSimpleName()+": "+e.getMessage());
  }
  if(handler instanceof RecordingManager){
   JSONArray store=new JSONArray();
   for(HttpCookie cookie:((RecordingManager)handler).getCookieStore().getCookies())store.put(obj("name",cookie.getName(),"httpOnly",cookie.isHttpOnly()));
   item.put("storeAfter",store);
  }
  return item;
 }
 void performHuc(JSONObject c,JSONObject item) throws Exception {
  HttpURLConnection conn=(HttpURLConnection)new URL(url(c)).openConnection();
  conn.setInstanceFollowRedirects(false);conn.setConnectTimeout(10000);conn.setReadTimeout(20000);
  // Left at its default only where the response cache is what the control is proving.
  if(!c.optBoolean("responseCache"))conn.setUseCaches(false);
  item.put("handlerVisible",CookieHandler.getDefault()!=null);
  item.put("authenticatorVisible",authenticatorVisible());
  if(c.has("body")){conn.setDoOutput(true);try(OutputStream out=conn.getOutputStream()){out.write(c.getString("body").getBytes(StandardCharsets.UTF_8));}}
  int status=conn.getResponseCode();
  item.put("status",status);
  JSONArray fields=setCookies(conn.getHeaderFields());
  if(fields.length()>0)item.put("setCookieFields",fields);
  item.put("bodyText",read(status>=400?conn.getErrorStream():conn.getInputStream()));
 }
 /** Header state is recorded before the body, so a hold can show what is visible at header time. */
 void performHold(JSONObject c,JSONObject item,Call call) throws Exception {
  JSONObject[] seen={null};String[] text={null};Exception[] failure={null};
  Thread worker=new Thread(()->{
   try(Response response=call.execute()){
    JSONObject head=empty(c.getString("id"));headersInto(head,response);
    synchronized(seen){seen[0]=head;}
    text[0]=response.body().string();
   }catch(Exception e){failure[0]=e;}
  });
  worker.start();
  boolean holdHeaders=c.optString("kind").equals("hold-headers");
  if(holdHeaders){for(int i=0;i<50&&!ask("/held",c);i++)Thread.sleep(100);Thread.sleep(300);}
  else{for(int i=0;i<30;i++){synchronized(seen){if(seen[0]!=null)break;}Thread.sleep(100);}Thread.sleep(300);}
  boolean headers;
  synchronized(seen){headers=seen[0]!=null;}
  boolean bodyEarly=text[0]!=null;
  ask("/release",c);worker.join(25000);
  if(failure[0]!=null)throw failure[0];
  item.put("status",seen[0].get("status"));
  item.put("setCookieFields",seen[0].get("setCookieFields"));
  item.put("bodyText",text[0]);
  if(holdHeaders)item.put("respondedBeforeRelease",headers);
  else{item.put("headersBeforeRelease",headers);item.put("bodyBeforeRelease",bodyEarly);}
 }
 static JSONObject empty(String id){
  return obj("case",id,"status",JSONObject.NULL,"error",JSONObject.NULL,"location",JSONObject.NULL,"bodyText",JSONObject.NULL,"setCookieFields",JSONObject.NULL,
   "handlerEvents",new JSONArray(),"authenticatorEvents",new JSONArray(),"responseCacheEvents",new JSONArray(),"proxySelectorEvents",new JSONArray(),
   "handlerVisible",false,"authenticatorVisible",false);
 }
 void save(String name){try(java.io.FileOutputStream out=openFileOutput(name,MODE_PRIVATE)){out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}}
}
