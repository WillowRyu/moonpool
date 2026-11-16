package org.moonpool.httpbroker;

import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.function.LongSupplier;
import java.util.regex.Pattern;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.HttpUrl;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.json.JSONArray;
import org.json.JSONObject;
import org.moonpool.cookieprofile.CookieJar;
import org.moonpool.cookieprofile.PublicSuffixList;

/**
 * Research broker: one in-memory c04-1 jar per app, selected by a host-side portal binding.
 * The field names and error values are proposals under test.
 */
final class Broker {
 static final Set<String> REQUEST_FIELDS=new HashSet<>(Arrays.asList("url","method","credentials","headers","body"));
 static final Set<String> COOKIE_FIELDS=new HashSet<>(Arrays.asList("name","value","path","maxAge"));
 static final Set<String> COOKIE_DELETE_FIELDS=new HashSet<>(Arrays.asList("name","path"));
 static final Set<String> METHODS=new HashSet<>(Arrays.asList("GET","HEAD","POST","PUT","PATCH","DELETE","OPTIONS"));
 static final Set<String> BODYLESS_METHODS=new HashSet<>(Arrays.asList("GET","HEAD"));
 /** OkHttp refuses these without a body, while URLSession sends them empty. */
 static final Set<String> BODY_REQUIRED_METHODS=new HashSet<>(Arrays.asList("POST","PUT","PATCH"));
 static final long TIMEOUT_SECONDS=40;
 static final Pattern TOKEN=Pattern.compile("[!#$%&'*+\\-.^_`|~0-9A-Za-z]+");
 static final Pattern HEADER_VALUE=Pattern.compile("[\\t\\x20-\\x7E]*");
 static final Pattern COOKIE_VALUE=Pattern.compile("[\\x21\\x23-\\x2B\\x2D-\\x3A\\x3C-\\x5B\\x5D-\\x7E]*");
 static final Pattern COOKIE_PATH=Pattern.compile("/[\\x20-\\x3A\\x3C-\\x7E]*");
 static final Set<String> FORBIDDEN_HEADERS=new HashSet<>(Arrays.asList("cookie","cookie2","host","origin","proxy-authorization","content-length","transfer-encoding","connection","te","upgrade","keep-alive"));
 static final class Portal {final String app;final Set<String> grants;boolean retired;Portal(String app,Set<String> grants){this.app=app;this.grants=grants;}}
 static final class App {
  CookieJar jar;
  int generation;
  App(PublicSuffixList publicSuffixes){jar=new CookieJar(publicSuffixes);}
 }
 static final class Pending {final CountDownLatch done=new CountDownLatch(1);JSONObject outcome;Runnable start;}
 record ServiceOrigin(String host,int port) {}
 private record ServiceTarget(HttpUrl url,CookieJar.Request cookieRequest) {
  ServiceOrigin origin(){return new ServiceOrigin(url.host(),url.port());}
 }

 final Map<String,Portal> portals=new HashMap<>();
 final Map<String,App> apps=new HashMap<>();
 private final Set<ServiceOrigin> approved=new HashSet<>();
 final JSONArray events=new JSONArray();
 final OkHttpClient client;
 private final PublicSuffixList publicSuffixes;
 private final LongSupplier clock;
 private long sequence;
 Broker(OkHttpClient client,Set<ServiceOrigin> registrations,PublicSuffixList publicSuffixes,LongSupplier clock){
  this.client=client;
  this.publicSuffixes=publicSuffixes;
  this.clock=clock;
  for(ServiceOrigin registration:registrations){
   ServiceOrigin origin=canonicalRegistration(registration);
   if(origin!=null)approved.add(origin);
  }
 }

 /** Followed ProxySelector, and hid Retry-After, per ADR 0027. Cookies, authentication and cache stay off. Timeouts match iOS. */
 static OkHttpClient newClient(){
  return new OkHttpClient.Builder().followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false).cache(null)
   .connectTimeout(TIMEOUT_SECONDS,TimeUnit.SECONDS).readTimeout(TIMEOUT_SECONDS,TimeUnit.SECONDS).writeTimeout(TIMEOUT_SECONDS,TimeUnit.SECONDS)
   .addNetworkInterceptor(chain->{
    Response response=chain.proceed(chain.request());
    String value=response.header("Retry-After");
    return value==null?response:response.newBuilder().removeHeader("Retry-After").header("X-Moonpool-Retry-After",value).build();
   }).build();
 }
 synchronized void bind(String id,String app,Set<String> grants){portals.put(id,new Portal(app,grants));apps.computeIfAbsent(app,key->new App(publicSuffixes));}
 synchronized void retire(String id){portals.get(id).retired=true;}
 static JSONObject obj(Object... fields){
  JSONObject o=new JSONObject();try{for(int i=0;i<fields.length;i+=2)o.put((String)fields[i],fields[i+1]);}catch(Exception e){throw new IllegalStateException(e);}return o;
 }
 static JSONObject error(Object code){return obj("ok",false,"code",code);}
 static JSONObject error(Object code,String reason){return obj("ok",false,"code",code,"reason",reason);}
 private synchronized void event(String kind,String label){events.put(obj("seq",++sequence,"kind",kind,"label",label));}

 /** Pinned order: owner, then scope, then fields, then service. A missing scope beats malformed fields (SPEC 4.2). */
 private synchronized JSONObject admit(Portal portal,String scope){
  if(portal.retired)return error("retired");
  return portal.grants.contains(scope)?null:error(-32000);
 }
 private static ServiceTarget secureTarget(String text){
  try{
   URI uri=new URI(text);
   String host=uri.getHost();
   if(!"https".equals(uri.getScheme())||uri.getRawUserInfo()!=null||uri.getRawFragment()!=null||host==null)return null;
   // Check before OkHttp normalizes aliases, then use its exact URL for approval, dispatch and the jar.
   CookieJar.Request.of(host,"");
   HttpUrl url=HttpUrl.parse(text);
   if(url==null||host.startsWith("[")&&!url.host().contains(":"))return null;
   return new ServiceTarget(url,CookieJar.Request.of(url.host(),url.encodedPath()));
  }catch(java.net.URISyntaxException|IllegalArgumentException e){return null;}
 }
 private static ServiceOrigin canonicalRegistration(ServiceOrigin registration){
  String host=registration.host();
  // Registrations supply a host field, so it cannot introduce a URL path or query.
  if(host.chars().anyMatch(ch->"/?#".indexOf(ch)>=0))return null;
  String authority=host.contains(":")&&!host.startsWith("[")?"["+host+"]":host;
  ServiceTarget target=secureTarget("https://"+authority+":"+registration.port()+"/");
  return target==null?null:target.origin();
 }
 private boolean isApproved(ServiceTarget target){return approved.contains(target.origin());}

 private static Pending rejected(JSONObject outcome){
  Pending pending=new Pending();
  pending.outcome=outcome;
  pending.done.countDown();
  return pending;
 }

 Pending request(String portalId,String label,JSONObject params,boolean deferred) throws Exception {
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"http");
  if(denied!=null)return rejected(denied);
  if(!validRequestFields(params))return rejected(error(-32602));
  ServiceTarget target=secureTarget(params.getString("url"));
  if(target==null)return rejected(error(-32602));
  if(!isApproved(target))return rejected(error(-32000));
  Pending pending=new Pending();
  App app=apps.get(portal.app);
  int generation;
  synchronized(this){generation=app.generation;}
  pending.start=()->dispatch(portal,app,generation,label,params,target,pending);
  if(!deferred)pending.start.run();
  return pending;
 }
 /** A value of the wrong type is refused rather than coerced, because iOS would read it differently. */
 private static boolean validRequestFields(JSONObject params){
  for(Iterator<String> keys=params.keys();keys.hasNext();)if(!REQUEST_FIELDS.contains(keys.next()))return false;
  Object url=params.opt("url"),method=params.opt("method"),credentials=params.opt("credentials"),body=params.opt("body"),headers=params.opt("headers");
  if(!(url instanceof String))return false;
  if(method!=null&&!METHODS.contains(method))return false;
  if(credentials!=null&&!"include".equals(credentials)&&!"omit".equals(credentials))return false;
  if(body!=null&&(!(body instanceof String)||BODYLESS_METHODS.contains(method==null?"GET":method)))return false;
  if(headers==null)return true;
  if(!(headers instanceof JSONObject))return false;
  JSONObject fields=(JSONObject)headers;
  for(Iterator<String> keys=fields.keys();keys.hasNext();){
   String name=keys.next(),lower=name.toLowerCase(Locale.ROOT);
   Object value=fields.opt(name);
   if(FORBIDDEN_HEADERS.contains(lower)||lower.startsWith("sec-")||lower.startsWith("proxy-"))return false;
   if(!TOKEN.matcher(name).matches()||!(value instanceof String)||!HEADER_VALUE.matcher((String)value).matches())return false;
  }
  return true;
 }
 /** The owner and generation are rechecked here because queued work may start after a close or a reset. */
 private void dispatch(Portal portal,App app,int generation,String label,JSONObject params,ServiceTarget target,Pending pending){
  try{
   boolean include=!params.optString("credentials","include").equals("omit");
   Request.Builder builder=new Request.Builder().url(target.url());
   String method=params.optString("method","GET"),body=params.optString("body",null);
   byte[] bytes=body==null?(BODY_REQUIRED_METHODS.contains(method)?new byte[0]:null):body.getBytes(java.nio.charset.StandardCharsets.UTF_8);
   builder.method(method,bytes==null?null:RequestBody.create(bytes,null));
   JSONObject headers=params.optJSONObject("headers");
   if(headers!=null)for(Iterator<String> keys=headers.keys();keys.hasNext();){String name=keys.next();builder.header(name,headers.getString(name));}
   synchronized(this){
    if(portal.retired){finish(portal,pending,error("retired"));return;}
    if(app.generation!=generation){finish(portal,pending,error(-32007,"sessionReset"));return;}
    if(include){
     String cookie=app.jar.cookieHeader(target.cookieRequest(),clock.getAsLong());
     if(!cookie.isEmpty())builder.header("Cookie",cookie);
    }
   }
   client.newCall(builder.build()).enqueue(new Callback(){
    @Override public void onFailure(Call call,IOException e){settleFailure(portal,app,generation,pending);}
    @Override public void onResponse(Call call,Response response){
     try(response){
      commit(app,generation,include,label,target.cookieRequest(),response);
      String text=response.body().string();
      synchronized(Broker.this){
       if(app.generation!=generation){finish(portal,pending,error(-32007,"sessionReset"));return;}
      }
      finish(portal,pending,obj("ok",true,"status",response.code(),"headers",projected(response),"bodyText",text));
     }catch(Exception e){settleFailure(portal,app,generation,pending);}
    }
   });
  }catch(Exception e){finish(portal,pending,error(-32603));}
 }
 private void settleFailure(Portal portal,App app,int generation,Pending pending){
  boolean reset;
  synchronized(this){reset=app.generation!=generation;}
  finish(portal,pending,reset?error(-32007,"sessionReset"):error(-32007,"network"));
 }
 private synchronized void finish(Portal portal,Pending pending,JSONObject outcome){
  pending.outcome=portal.retired?obj("delivered",false):outcome;
  pending.done.countDown();
 }
 /** Runs when the client delivers response headers, before the body is read. A stale generation is fenced, not written. */
 private synchronized void commit(App app,int generation,boolean include,String label,CookieJar.Request request,Response response){
  event("headers",label);
  List<String> fields=response.headers("Set-Cookie");
  if(fields.isEmpty()||!include)return;
  if(app.generation!=generation){event("fence",label);return;}
  app.jar.receive(fields,request,clock.getAsLong());
  event("commit",label);
 }
 private static JSONObject projected(Response response) throws Exception {
  JSONObject headers=new JSONObject();
  for(String name:response.headers().names()){
   String lower=name.toLowerCase(Locale.ROOT);
   if(lower.equals("set-cookie")||lower.equals("set-cookie2"))continue;
   headers.put(lower.equals("x-moonpool-retry-after")?"retry-after":lower,String.join(", ",response.headers(name)));
  }
  return headers;
 }
 /** Script cookies follow the RFC 6265 grammar, so a value cannot add a pair beside a protected cookie. */
 private static boolean validCookieFields(JSONObject fields,Set<String> allowed,boolean needsValue){
  for(Iterator<String> keys=fields.keys();keys.hasNext();)if(!allowed.contains(keys.next()))return false;
  Object name=fields.opt("name"),value=fields.opt("value"),path=fields.opt("path"),age=fields.opt("maxAge");
  if(!(name instanceof String)||!TOKEN.matcher((String)name).matches())return false;
  if(needsValue&&(!(value instanceof String)||!COOKIE_VALUE.matcher((String)value).matches()))return false;
  if(path!=null&&(!(path instanceof String)||!COOKIE_PATH.matcher((String)path).matches()))return false;
  return age==null||age instanceof Integer||age instanceof Long;
 }

 synchronized JSONObject cookiesGet(String portalId,String url) throws Exception {
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"cookies");
  if(denied!=null)return denied;
  ServiceTarget target=secureTarget(url);
  if(target==null)return error(-32602);
  if(!isApproved(target))return error(-32000);
  JSONArray cookies=new JSONArray();
  App app=apps.get(portal.app);
  for(CookieJar.Cookie cookie:app.jar.scriptCookies(target.cookieRequest(),clock.getAsLong())){
   cookies.put(obj("name",cookie.name,"path",cookie.path,"value",cookie.value));
  }
  return obj("ok",true,"cookies",cookies);
 }
 synchronized JSONObject cookiesSet(String portalId,String url,JSONObject fields) throws Exception {
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"cookies");
  if(denied!=null)return denied;
  if(!validCookieFields(fields,COOKIE_FIELDS,true))return error(-32602);
  ServiceTarget target=secureTarget(url);
  if(target==null)return error(-32602);
  if(!isApproved(target))return error(-32000);
  Long maxAge=fields.has("maxAge")?fields.getLong("maxAge"):null;
  boolean stored=apps.get(portal.app).jar.setScriptCookie(target.cookieRequest(),fields.getString("name"),
      fields.getString("value"),fields.optString("path","/"),maxAge,clock.getAsLong());
  return stored?obj("ok",true):error(-32000);
 }
 synchronized JSONObject cookiesDelete(String portalId,String url,JSONObject fields) throws Exception {
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"cookies");
  if(denied!=null)return denied;
  if(!validCookieFields(fields,COOKIE_DELETE_FIELDS,false))return error(-32602);
  ServiceTarget target=secureTarget(url);
  if(target==null)return error(-32602);
  if(!isApproved(target))return error(-32000);
  boolean deleted=apps.get(portal.app).jar.deleteScriptCookie(target.cookieRequest(),fields.getString("name"),
      fields.optString("path","/"),clock.getAsLong());
  return deleted?obj("ok",true):error(-32000);
 }
 /** Advances the generation first, so no in-flight response can write after this returns. */
 synchronized JSONObject reset(String portalId){
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"http");
  if(denied!=null)return denied;
  App app=apps.get(portal.app);
  app.generation++;
  app.jar=new CookieJar(publicSuffixes);
  event("reset",portalId);
  return obj("ok",true);
 }
 /** Harness evidence only. Nothing the guest can reach calls this. */
 synchronized JSONArray snapshot(String appId){
  List<String> found=new ArrayList<>();
  App app=apps.get(appId);
  if(app!=null)for(CookieJar.Cookie cookie:app.jar.entries())found.add(cookie.name+"="+cookie.value);
  Collections.sort(found);
  return new JSONArray(found);
 }
 synchronized boolean hasEvent(String kind,String label) throws Exception {
  for(int i=0;i<events.length();i++){
   JSONObject event=events.getJSONObject(i);
   if(event.getString("kind").equals(kind)&&event.getString("label").equals(label))return true;
  }
  return false;
 }
}
