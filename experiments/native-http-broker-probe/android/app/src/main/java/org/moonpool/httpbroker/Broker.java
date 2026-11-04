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
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Research broker: one in-memory cookie jar per app, selected by a host-side portal binding. Not a public API, and its
 * cookie parser is only the small subset these cases need, because the C04 cookie profile is not frozen.
 * The field names and error values are proposals under test.
 */
final class Broker {
 static final Set<String> REQUEST_FIELDS=new HashSet<>(Arrays.asList("url","method","credentials","headers","body"));
 static final Set<String> COOKIE_FIELDS=new HashSet<>(Arrays.asList("name","value","path","maxAge"));
 static final Set<String> FORBIDDEN_HEADERS=new HashSet<>(Arrays.asList("cookie","cookie2","host","origin","proxy-authorization","content-length","transfer-encoding","connection","te","upgrade","keep-alive"));
 static final class Cookie {String host,path,name,value;boolean httpOnly;long created;}
 static final class Portal {final String app;final Set<String> grants;boolean retired;Portal(String app,Set<String> grants){this.app=app;this.grants=grants;}}
 static final class App {final List<Cookie> jar=new ArrayList<>();int generation;}
 static final class Pending {final CountDownLatch done=new CountDownLatch(1);JSONObject outcome;Runnable start;}

 final Map<String,Portal> portals=new HashMap<>();
 final Map<String,App> apps=new HashMap<>();
 final Set<String> approved;
 final JSONArray events=new JSONArray();
 final OkHttpClient client;
 private long sequence;
 Broker(OkHttpClient client,Set<String> approved){this.client=client;this.approved=approved;}

 /** Followed ProxySelector, and hid Retry-After, per ADR 0027. Cookies, authentication and cache stay off. */
 static OkHttpClient newClient(){
  return new OkHttpClient.Builder().followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false).cache(null)
   .addNetworkInterceptor(chain->{
    Response response=chain.proceed(chain.request());
    String value=response.header("Retry-After");
    return value==null?response:response.newBuilder().removeHeader("Retry-After").header("X-Moonpool-Retry-After",value).build();
   }).build();
 }
 synchronized void bind(String id,String app,Set<String> grants){portals.put(id,new Portal(app,grants));apps.computeIfAbsent(app,key->new App());}
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
 private static URI secureUrl(String text){
  try{
   URI uri=new URI(text);
   boolean bad=!"https".equals(uri.getScheme())||uri.getRawUserInfo()!=null||uri.getRawFragment()!=null||uri.getHost()==null;
   return bad?null:uri;
  }catch(Exception e){return null;}
 }
 private boolean isApproved(URI uri){return approved.contains(uri.getHost().toLowerCase(Locale.ROOT)+":"+uri.getPort());}

 Pending request(String portalId,String label,JSONObject params,boolean deferred) throws Exception {
  Pending pending=new Pending();
  JSONObject denied=admitRequest(portals.get(portalId),params);
  if(denied!=null){pending.outcome=denied;pending.done.countDown();return pending;}
  Portal portal=portals.get(portalId);
  App app=apps.get(portal.app);
  int generation;
  synchronized(this){generation=app.generation;}
  pending.start=()->dispatch(portal,app,generation,label,params,pending);
  if(!deferred)pending.start.run();
  return pending;
 }
 private JSONObject admitRequest(Portal portal,JSONObject params) throws Exception {
  JSONObject denied=admit(portal,"http");
  if(denied!=null)return denied;
  for(Iterator<String> keys=params.keys();keys.hasNext();)if(!REQUEST_FIELDS.contains(keys.next()))return error(-32602);
  String credentials=params.optString("credentials","include");
  if(!credentials.equals("include")&&!credentials.equals("omit"))return error(-32602);
  JSONObject headers=params.optJSONObject("headers");
  if(headers!=null)for(Iterator<String> keys=headers.keys();keys.hasNext();){
   String name=keys.next().toLowerCase(Locale.ROOT);
   if(FORBIDDEN_HEADERS.contains(name)||name.startsWith("sec-")||name.startsWith("proxy-"))return error(-32602);
  }
  URI uri=secureUrl(params.getString("url"));
  if(uri==null)return error(-32602);
  return isApproved(uri)?null:error(-32000);
 }
 /** The owner and generation are rechecked here because queued work may start after a reset. */
 private void dispatch(Portal portal,App app,int generation,String label,JSONObject params,Pending pending){
  try{
   boolean include=!params.optString("credentials","include").equals("omit");
   URI uri=new URI(params.getString("url"));
   Request.Builder builder=new Request.Builder().url(params.getString("url"));
   String body=params.optString("body",null);
   builder.method(params.optString("method","GET"),body==null?null:RequestBody.create(body.getBytes(java.nio.charset.StandardCharsets.UTF_8),null));
   JSONObject headers=params.optJSONObject("headers");
   if(headers!=null)for(Iterator<String> keys=headers.keys();keys.hasNext();){String name=keys.next();builder.header(name,headers.getString(name));}
   synchronized(this){
    if(app.generation!=generation){finish(portal,pending,error(-32007,"sessionReset"));return;}
    if(include){String cookie=cookieHeader(app,uri);if(!cookie.isEmpty())builder.header("Cookie",cookie);}
   }
   client.newCall(builder.build()).enqueue(new Callback(){
    @Override public void onFailure(Call call,IOException e){settleFailure(portal,app,generation,pending);}
    @Override public void onResponse(Call call,Response response){
     try(response){
      commit(app,generation,include,label,uri,response);
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
 private synchronized void commit(App app,int generation,boolean include,String label,URI uri,Response response){
  event("headers",label);
  List<String> fields=response.headers("Set-Cookie");
  if(fields.isEmpty()||!include)return;
  if(app.generation!=generation){event("fence",label);return;}
  for(String line:splitFolded(String.join(", ",fields)))store(app,line,uri);
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
 static String[] splitFolded(String value){return value.split(",\\s*(?=[^;,=\\s]+=)");}
 private static boolean pathMatches(String request,String cookie){
  return request.equals(cookie)||(request.startsWith(cookie)&&(cookie.endsWith("/")||request.charAt(cookie.length())=='/'));
 }
 private static String defaultPath(String path){
  int last=path==null?-1:path.lastIndexOf('/');
  return last<=0?"/":path.substring(0,last);
 }
 private void store(App app,String line,URI uri){
  String[] parts=line.split(";");
  int equals=parts[0].indexOf('=');
  if(equals<=0)return;
  Cookie cookie=new Cookie();
  cookie.name=parts[0].substring(0,equals).trim();
  cookie.value=parts[0].substring(equals+1).trim();
  cookie.host=uri.getHost().toLowerCase(Locale.ROOT);
  cookie.path=defaultPath(uri.getPath());
  boolean secure=false,sameSiteNone=false;
  Long maxAge=null;
  for(int i=1;i<parts.length;i++){
   String[] attribute=parts[i].trim().split("=",2);
   String key=attribute[0].trim().toLowerCase(Locale.ROOT),value=attribute.length>1?attribute[1].trim():"";
   switch(key){
    case "path":if(value.startsWith("/"))cookie.path=value;break;
    case "domain":if(!value.equalsIgnoreCase(cookie.host))return;break;
    case "secure":secure=true;break;
    case "httponly":cookie.httpOnly=true;break;
    case "samesite":sameSiteNone=value.equalsIgnoreCase("none");break;
    case "max-age":try{maxAge=Long.parseLong(value);}catch(NumberFormatException ignored){}break;
    default:
   }
  }
  if(sameSiteNone&&!secure)return;
  put(app,cookie,maxAge!=null&&maxAge<=0);
 }
 private void put(App app,Cookie cookie,boolean delete){
  Cookie existing=find(app,cookie.host,cookie.path,cookie.name);
  cookie.created=existing==null?++sequence:existing.created;
  if(existing!=null)app.jar.remove(existing);
  if(!delete)app.jar.add(cookie);
 }
 private static Cookie find(App app,String host,String path,String name){
  for(Cookie cookie:app.jar)if(cookie.host.equals(host)&&cookie.path.equals(path)&&cookie.name.equals(name))return cookie;
  return null;
 }
 private static List<Cookie> matching(App app,URI uri){
  List<Cookie> found=new ArrayList<>();
  String host=uri.getHost().toLowerCase(Locale.ROOT),path=uri.getPath()==null||uri.getPath().isEmpty()?"/":uri.getPath();
  for(Cookie cookie:app.jar)if(cookie.host.equals(host)&&pathMatches(path,cookie.path))found.add(cookie);
  Collections.sort(found,(a,b)->a.path.length()!=b.path.length()?b.path.length()-a.path.length():Long.compare(a.created,b.created));
  return found;
 }
 private static String cookieHeader(App app,URI uri){
  StringBuilder header=new StringBuilder();
  for(Cookie cookie:matching(app,uri)){if(header.length()>0)header.append("; ");header.append(cookie.name).append('=').append(cookie.value);}
  return header.toString();
 }

 synchronized JSONObject cookiesGet(String portalId,String url) throws Exception {
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"cookies");
  if(denied!=null)return denied;
  URI uri=secureUrl(url);
  if(uri==null)return error(-32602);
  if(!isApproved(uri))return error(-32000);
  JSONArray cookies=new JSONArray();
  for(Cookie cookie:matching(apps.get(portal.app),uri))if(!cookie.httpOnly)cookies.put(obj("name",cookie.name,"path",cookie.path,"value",cookie.value));
  return obj("ok",true,"cookies",cookies);
 }
 synchronized JSONObject cookiesSet(String portalId,String url,JSONObject fields) throws Exception {
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"cookies");
  if(denied!=null)return denied;
  for(Iterator<String> keys=fields.keys();keys.hasNext();)if(!COOKIE_FIELDS.contains(keys.next()))return error(-32602);
  URI uri=secureUrl(url);
  if(uri==null)return error(-32602);
  if(!isApproved(uri))return error(-32000);
  App app=apps.get(portal.app);
  String host=uri.getHost().toLowerCase(Locale.ROOT),path=fields.optString("path","/");
  Cookie existing=find(app,host,path,fields.getString("name"));
  if(existing!=null&&existing.httpOnly)return error(-32000);
  Cookie cookie=new Cookie();
  cookie.host=host;cookie.path=path;cookie.name=fields.getString("name");cookie.value=fields.getString("value");
  put(app,cookie,fields.has("maxAge")&&fields.getLong("maxAge")<=0);
  return obj("ok",true);
 }
 synchronized JSONObject cookiesDelete(String portalId,String url,JSONObject fields) throws Exception {
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"cookies");
  if(denied!=null)return denied;
  URI uri=secureUrl(url);
  if(uri==null)return error(-32602);
  if(!isApproved(uri))return error(-32000);
  App app=apps.get(portal.app);
  Cookie existing=find(app,uri.getHost().toLowerCase(Locale.ROOT),fields.optString("path","/"),fields.getString("name"));
  if(existing!=null&&existing.httpOnly)return error(-32000);
  if(existing!=null)app.jar.remove(existing);
  return obj("ok",true);
 }
 /** Advances the generation first, so no in-flight response can write after this returns. */
 synchronized JSONObject reset(String portalId){
  Portal portal=portals.get(portalId);
  JSONObject denied=admit(portal,"http");
  if(denied!=null)return denied;
  App app=apps.get(portal.app);
  app.generation++;
  app.jar.clear();
  event("reset",portalId);
  return obj("ok",true);
 }
 /** Harness evidence only. Nothing the guest can reach calls this. */
 synchronized JSONArray snapshot(String appId){
  List<String> found=new ArrayList<>();
  App app=apps.get(appId);
  if(app!=null)for(Cookie cookie:app.jar)found.add(cookie.name+"="+cookie.value);
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
