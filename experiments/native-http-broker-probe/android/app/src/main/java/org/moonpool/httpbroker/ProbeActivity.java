package org.moonpool.httpbroker;

import android.app.Activity;
import android.os.Bundle;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Authenticator;
import java.net.CookieHandler;
import java.net.HttpURLConnection;
import java.net.PasswordAuthentication;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import org.json.JSONArray;
import org.json.JSONObject;

/** Runs the shared scenarios against the research broker. All cookies and credentials are public fixture values. */
public final class ProbeActivity extends Activity {
 private static final int BARRIER_SECONDS=20;
 private String run;
 private int port,second,control;
 private JSONObject report;
 private final JSONArray observations=new JSONArray(),errors=new JSONArray();
 private final OkHttpClient harness=new OkHttpClient();
 private final OkHttpClient brokerClient=Broker.newClient();
 private final List<String> hostPuts=new ArrayList<>();

 static JSONObject obj(Object... fields){return Broker.obj(fields);}
 static String read(InputStream input) throws Exception {
  if(input==null)return "";
  try(input;ByteArrayOutputStream out=new ByteArrayOutputStream()){
   byte[] bytes=new byte[4096];int n;while((n=input.read(bytes))!=-1)out.write(bytes,0,n);return out.toString(StandardCharsets.UTF_8.name());
  }
 }
 /** Stands for a host that set process-wide state for its own login. */
 final class HostHandler extends CookieHandler {
  @Override public Map<String,List<String>> get(URI uri,Map<String,List<String>> headers){return Map.of("Cookie",List.of("host_ambient=sentinel"));}
  @Override public void put(URI uri,Map<String,List<String>> headers){
   for(Map.Entry<String,List<String>> entry:headers.entrySet())if("Set-Cookie".equalsIgnoreCase(entry.getKey()))synchronized(hostPuts){hostPuts.addAll(entry.getValue());}
  }
 }
 static final class HostAuthenticator extends Authenticator {
  @Override protected PasswordAuthentication getPasswordAuthentication(){return new PasswordAuthentication("moonpool-fixture-user","not-a-secret".toCharArray());}
 }
 @Override public void onCreate(Bundle state){
  super.onCreate(state);
  run=getIntent().getStringExtra("run");port=getIntent().getIntExtra("port",0);second=getIntent().getIntExtra("second",0);control=getIntent().getIntExtra("control",0);
  report=obj("platform","android","run",run,"release",android.os.Build.VERSION.RELEASE,"sdkInt",android.os.Build.VERSION.SDK_INT,"observations",observations,"errors",errors,"complete",false);
  new Thread(this::execute).start();
 }
 void execute(){
  try{
   report.put("client","OkHttp "+okhttp3.OkHttp.VERSION);
   JSONArray cases;
   try(InputStream input=getAssets().open("cases.json")){cases=new JSONArray(read(input));}
   for(int i=0;i<cases.length();i++){
    try{observations.put(perform(cases.getJSONObject(i)));}finally{CookieHandler.setDefault(null);Authenticator.setDefault(null);}
    save("progress.json");
   }
   report.put("complete",true);
  }catch(Exception e){errors.put(obj("error",e.toString()));}
  save("report.json");
 }
 int listenerPort(String name){return name.equals("service2")?second:port;}
 String url(JSONObject c,String label,JSONObject target){
  JSONObject t=target==null?new JSONObject():target;
  String userinfo=t.optString("userinfo");
  String fragment=t.optString("fragment");
  return t.optString("scheme","https")+"://"+(userinfo.isEmpty()?"":userinfo+"@")+t.optString("host","localhost")+(t.optBoolean("defaultPort")?"":":"+listenerPort(t.optString("listener","service")))
   +t.optString("path","/s")+"?run="+run+"&case="+c.optString("id")+"&step="+label+(fragment.isEmpty()?"":"#"+fragment);
 }
 boolean held(JSONObject c,String label,String path) throws Exception {
  Request request=new Request.Builder().url("https://localhost:"+control+path+"?run="+run+"&case="+c.getString("id")+"&step="+label).build();
  try(Response response=harness.newCall(request).execute()){return new JSONObject(response.body().string()).optBoolean("held");}
 }
 JSONObject perform(JSONObject c) throws Exception {
  JSONArray steps=new JSONArray(),timedOut=new JSONArray();
  Set<String> approved=new HashSet<>();
  JSONArray declared=c.optJSONArray("approved");
  if(declared==null)approved.add("localhost:"+port);
  else for(int i=0;i<declared.length();i++){JSONObject entry=declared.getJSONObject(i);approved.add(entry.getString("host")+":"+(entry.has("port")?entry.getInt("port"):listenerPort(entry.getString("listener"))));}
  Broker broker=new Broker(brokerClient,approved);
  JSONObject portals=c.getJSONObject("portals");
  for(java.util.Iterator<String> keys=portals.keys();keys.hasNext();){String id=keys.next();JSONObject p=portals.getJSONObject(id);broker.bind(id,p.getString("app"),grants(p.getJSONArray("grants")));}
  synchronized(hostPuts){hostPuts.clear();}
  Map<String,Broker.Pending> pending=new HashMap<>();
  JSONArray list=c.getJSONArray("steps");
  for(int i=0;i<list.length();i++){
   JSONObject s=list.getJSONObject(i);
   String op=s.getString("op"),label=s.getString("label");
   switch(op){
    case "request":{
     JSONObject given=s.optJSONObject("params");
     JSONObject params=given==null?new JSONObject():new JSONObject(given.toString());
     JSONObject target=(JSONObject)params.remove("target");
     boolean deferred=params.optBoolean("deferred");
     params.remove("deferred");
     if(!s.optBoolean("omitUrl")&&!params.has("url"))params.put("url",url(c,label,target));
     pending.put(label,broker.request(s.getString("portal"),label,params,deferred));
     if(s.optBoolean("wait",true))settle(steps,timedOut,pending,label);
     break;
    }
    case "await":settle(steps,timedOut,pending,label);break;
    case "held":
     if(!until(()->held(c,label,"/held")))timedOut.put("held:"+label);
     break;
    case "release":held(c,label,"/release");break;
    case "awaitEvent":{
     String kind=s.getString("kind");
     if(!until(()->broker.hasEvent(kind,label)))timedOut.put("event:"+kind+":"+label);
     break;
    }
    case "startQueued":{Broker.Pending queued=pending.get(label);queued.start.run();break;}
    case "retire":broker.retire(s.getString("portal"));steps.put(obj("label",label,"op",op,"outcome",obj("ok",true)));break;
    case "bind":broker.bind(s.getString("portal"),s.getString("app"),grants(s.getJSONArray("grants")));steps.put(obj("label",label,"op",op,"outcome",obj("ok",true)));break;
    case "reset":steps.put(obj("label",label,"op",op,"outcome",broker.reset(s.optString("portal","A1"))));break;
    case "cookiesGet":
     steps.put(obj("label",label,"op",op,"outcome",broker.cookiesGet(s.optString("portal","A1"),url(c,label,s.has("path")?obj("path",s.getString("path")):null))));
     break;
    case "cookiesSet":steps.put(obj("label",label,"op",op,"outcome",broker.cookiesSet(s.optString("portal","A1"),url(c,label,null),s.getJSONObject("cookie"))));break;
    case "cookiesDelete":steps.put(obj("label",label,"op",op,"outcome",broker.cookiesDelete(s.optString("portal","A1"),url(c,label,null),s.getJSONObject("cookie"))));break;
    case "snapshot":steps.put(obj("label",label,"op",op,"outcome",obj("ok",true),"jar",broker.snapshot(s.getString("app"))));break;
    case "tlsNegative":steps.put(obj("label",label,"op",op,"outcome",tlsNegative(c,label)));break;
    case "hostSeed":
     CookieHandler.setDefault(new HostHandler());Authenticator.setDefault(new HostAuthenticator());
     steps.put(obj("label",label,"op",op,"outcome",obj("ok",true)));
     break;
    case "hostRequest":steps.put(obj("label",label,"op",op,"outcome",hostRequest(c,label)));break;
    case "hostInspect":{
     boolean saw=false;
     synchronized(hostPuts){for(String value:hostPuts)saw|=value.contains(s.getString("marker"));}
     steps.put(obj("label",label,"op",op,"outcome",obj("hostSawMarker",saw)));
     break;
    }
    case "hostClear":
     CookieHandler.setDefault(null);Authenticator.setDefault(null);
     steps.put(obj("label",label,"op",op,"outcome",obj("ok",true)));
     break;
    default:throw new IllegalArgumentException(op);
   }
  }
  return obj("case",c.getString("id"),"steps",steps,"events",broker.events,"timedOut",timedOut);
 }
 static Set<String> grants(JSONArray values) throws Exception {
  Set<String> found=new HashSet<>();
  for(int i=0;i<values.length();i++)found.add(values.getString(i));
  return found;
 }
 interface Check {boolean ok() throws Exception;}
 static boolean until(Check check) throws Exception {
  long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(BARRIER_SECONDS);
  while(System.nanoTime()<deadline){if(check.ok())return true;Thread.sleep(50);}
  return false;
 }
 void settle(JSONArray steps,JSONArray timedOut,Map<String,Broker.Pending> pending,String label) throws Exception {
  Broker.Pending found=pending.get(label);
  if(!found.done.await(BARRIER_SECONDS+10,TimeUnit.SECONDS)){timedOut.put("await:"+label);return;}
  steps.put(obj("label",label,"op","request","outcome",found.outcome));
 }
 /** The emulator's name for the host is outside the probe CA's scope, so ordinary validation must refuse it. */
 JSONObject tlsNegative(JSONObject c,String label) throws Exception {
  Request request=new Request.Builder().url(url(c,label,obj("host","10.0.2.2"))).build();
  try(Response response=harness.newCall(request).execute()){return obj("ok",true,"status",response.code());}
  catch(javax.net.ssl.SSLException e){return obj("ok",false,"code","tlsRefused","detail",e.getClass().getSimpleName());}
  catch(java.io.IOException e){return obj("ok",false,"code","notTls","detail",e.getClass().getSimpleName());}
 }
 /** The host's own HttpURLConnection: the positive control that its global state is live in this process. */
 JSONObject hostRequest(JSONObject c,String label) throws Exception {
  HttpURLConnection conn=(HttpURLConnection)new URL(url(c,label,null)).openConnection();
  conn.setInstanceFollowRedirects(false);conn.setConnectTimeout(10000);conn.setReadTimeout(20000);conn.setUseCaches(false);
  try{
   int status=conn.getResponseCode();
   read(status>=400?conn.getErrorStream():conn.getInputStream());
   return obj("ok",true,"status",status);
  }finally{conn.disconnect();}
 }
 void save(String name){try(OutputStream out=openFileOutput(name,MODE_PRIVATE)){out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}}
}
