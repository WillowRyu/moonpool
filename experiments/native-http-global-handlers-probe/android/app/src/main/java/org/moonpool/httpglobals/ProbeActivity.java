package org.moonpool.httpglobals;

import android.app.Activity;
import android.os.Bundle;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.InvocationTargetException;
import java.net.Authenticator;
import java.net.CookieHandler;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.HttpCookie;
import java.net.HttpURLConnection;
import java.net.PasswordAuthentication;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Plays a host app that set process-wide HTTP handlers, then sends requests the way a broker would.
 * Each case gets fresh handlers and clears them afterwards. All credentials are public fixture values.
 */
public final class ProbeActivity extends Activity {
 private String run;
 private int port;
 private JSONObject report;
 private final JSONArray observations=new JSONArray(),errors=new JSONArray();
 private RecordingManager lastManager;
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
 static JSONObject getEvent(URI uri,Map<String,List<String>> headers) {
  JSONArray names=new JSONArray();for(String key:headers.keySet())if(key!=null)names.put(key);
  return obj("op","get","uri",uri.toString(),"requestHeaderNames",names);
 }
 static JSONObject putEvent(URI uri,Map<String,List<String>> headers) {return obj("op","put","uri",uri.toString(),"setCookie",setCookies(headers));}

 /** A plain CookieHandler, optionally returning a host cookie for every request. */
 static final class RecordingHandler extends CookieHandler {
  final JSONArray events;final boolean sentinel;
  RecordingHandler(JSONArray events,boolean sentinel){this.events=events;this.sentinel=sentinel;}
  @Override public Map<String,List<String>> get(URI uri,Map<String,List<String>> headers){
   events.put(getEvent(uri,headers));
   return sentinel?Map.of("Cookie",List.of("host_ambient=sentinel")):Map.of();
  }
  @Override public void put(URI uri,Map<String,List<String>> headers){events.put(putEvent(uri,headers));}
 }
 /** The real JDK cookie jar, which is the class hosts such as Capacitor build on. */
 static final class RecordingManager extends CookieManager {
  JSONArray events;
  RecordingManager(JSONArray events){super(null,CookiePolicy.ACCEPT_ALL);this.events=events;}
  @Override public Map<String,List<String>> get(URI uri,Map<String,List<String>> headers) throws java.io.IOException {events.put(getEvent(uri,headers));return super.get(uri,headers);}
  @Override public void put(URI uri,Map<String,List<String>> headers) throws java.io.IOException {events.put(putEvent(uri,headers));super.put(uri,headers);}
 }
 static final class RecordingAuthenticator extends Authenticator {
  /** The harness asking whether its own authenticator is in place, which must not look like a request. */
  static volatile boolean harnessCheck;
  final JSONArray events;final boolean answer;
  RecordingAuthenticator(JSONArray events,boolean answer){this.events=events;this.answer=answer;}
  @Override protected PasswordAuthentication getPasswordAuthentication(){
   if(harnessCheck)return new PasswordAuthentication("harness","check".toCharArray());
   events.put(obj("host",String.valueOf(getRequestingHost()),"port",getRequestingPort(),"protocol",String.valueOf(getRequestingProtocol()),"prompt",String.valueOf(getRequestingPrompt()),
    "scheme",String.valueOf(getRequestingScheme()),"url",String.valueOf(getRequestingURL()),"type",String.valueOf(getRequestorType())));
   return answer?new PasswordAuthentication("moonpool-fixture-user","not-a-secret".toCharArray()):null;
  }
 }
 static void install(CookieHandler handler,Authenticator authenticator){CookieHandler.setDefault(handler);Authenticator.setDefault(authenticator);}
 static PasswordAuthentication askGlobal(){return Authenticator.requestPasswordAuthentication("probe.invalid",null,443,"https","probe","Basic");}
 static boolean authenticatorVisible(){
  RecordingAuthenticator.harnessCheck=true;
  try{return askGlobal()!=null;}finally{RecordingAuthenticator.harnessCheck=false;}
 }
 static boolean hasMethod(Class<?> type,String name,Class<?>... args){try{type.getMethod(name,args);return true;}catch(NoSuchMethodException e){return false;}}
 /** Desktop Java 9 added this, but android.jar does not declare it, so it can only be looked for at run time. */
 static String setAuthenticatorByReflection(HttpURLConnection conn,Authenticator authenticator){
  try{HttpURLConnection.class.getMethod("setAuthenticator",Authenticator.class).invoke(conn,authenticator);return "applied";}
  catch(InvocationTargetException e){return e.getCause().getClass().getSimpleName();}
  catch(Exception e){return e.getClass().getSimpleName();}
 }

 @Override public void onCreate(Bundle state) {
  super.onCreate(state);run=getIntent().getStringExtra("run");port=getIntent().getIntExtra("port",0);
  report=obj("platform","android","run",run,"release",android.os.Build.VERSION.RELEASE,"sdkInt",android.os.Build.VERSION.SDK_INT,"observations",observations,"errors",errors,"complete",false);
  new Thread(this::execute).start();
 }
 void execute(){
  try {
   report.put("api",obj("setAuthenticator",hasMethod(HttpURLConnection.class,"setAuthenticator",Authenticator.class),"authenticatorGetDefault",hasMethod(Authenticator.class,"getDefault"),
    "cookieHandlerGetDefault",hasMethod(CookieHandler.class,"getDefault"),"defaultAllowUserInteraction",HttpURLConnection.getDefaultAllowUserInteraction()));
   report.put("globalsAtStart",obj("cookieHandlerNull",CookieHandler.getDefault()==null,"authenticatorNull",!authenticatorVisible()));
   JSONArray cases;
   try(InputStream input=getAssets().open("cases.json")){cases=new JSONArray(read(input));}
   for(int i=0;i<cases.length();i++){
    try{observations.put(perform(cases.getJSONObject(i)));}finally{install(null,null);}
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
   case "recording":return new RecordingHandler(events,true);
   case "recording-empty":return new RecordingHandler(events,false);
   case "previous":lastManager.events=events;return lastManager;
   default:
  }
  RecordingManager manager=new RecordingManager(events);
  if(kind.equals("manager-seeded")){
   HttpCookie cookie=new HttpCookie("host_session","host-fixture");cookie.setPath("/");cookie.setDomain("localhost");
   manager.getCookieStore().add(new URI("https://localhost:"+port+"/"),cookie);
  }else if(kind.equals("manager-other-domain")){
   HttpCookie cookie=new HttpCookie("host_other","host-fixture");cookie.setPath("/");cookie.setDomain("host.example");
   manager.getCookieStore().add(new URI("https://host.example/"),cookie);
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
 JSONObject perform(JSONObject c) throws Exception {
  String id=c.getString("id");
  if(c.optString("kind").equals("detect-probe")){
   // Sends nothing. It asks the global directly, which is the only detection left if getDefault is absent, and it runs host code.
   JSONObject item=empty(id);
   install(null,authenticatorFor(c,item.getJSONArray("authenticatorEvents")));
   item.put("probeAnswered",askGlobal()!=null);
   install(null,null);
   item.put("probeAnsweredAfterClear",askGlobal()!=null);
   return item;
  }
  if(c.optString("kind").equals("tls-negative")){
   // Outside the app's scoped domains, so only the system's own roots apply and must refuse this certificate.
   JSONObject item=empty(id);
   try{item.put("status",((HttpURLConnection)new URL("https://10.0.2.2:"+port+c.getString("path")+"?run="+run+"&case="+id).openConnection()).getResponseCode());}
   catch(Exception e){item.put("error",e.getClass().getSimpleName());}
   return item;
  }
  JSONObject item=empty(id);
  JSONArray handlerEvents=item.getJSONArray("handlerEvents"),authEvents=item.getJSONArray("authenticatorEvents"),perEvents=item.getJSONArray("perConnectionEvents");
  CookieHandler handler=handlerFor(c,handlerEvents);
  Authenticator authenticator=authenticatorFor(c,authEvents);
  String timing=c.optString("install","before-open");
  if(!timing.equals("after-open"))install(handler,authenticator);
  HttpURLConnection conn=(HttpURLConnection)new URL("https://localhost:"+port+c.getString("path")+"?run="+run+"&case="+id).openConnection();
  // openConnection is the earliest moment a broker holds the connection, so this is the race a check-then-open faces.
  if(timing.equals("after-open"))install(handler,authenticator);
  else if(timing.equals("cleared-after-open"))install(null,null);
  conn.setInstanceFollowRedirects(false);conn.setUseCaches(false);conn.setConnectTimeout(10000);conn.setReadTimeout(20000);
  conn.setRequestMethod(c.optString("method","GET"));
  if(c.has("attachCookie"))conn.setRequestProperty("Cookie",c.getString("attachCookie"));
  if(c.has("presetAuthorization"))conn.setRequestProperty("Authorization",c.getString("presetAuthorization"));
  if(c.optBoolean("perConnectionAuthenticator"))item.put("perConnectionResult",setAuthenticatorByReflection(conn,new RecordingAuthenticator(perEvents,false)));
  item.put("handlerVisible",CookieHandler.getDefault()!=null);
  item.put("authenticatorVisible",authenticatorVisible());
  try {
   if(c.has("body")){
    byte[] body=c.getString("body").getBytes(StandardCharsets.UTF_8);
    conn.setDoOutput(true);
    if(c.optBoolean("streaming"))conn.setFixedLengthStreamingMode(body.length);
    try(OutputStream out=conn.getOutputStream()){out.write(body);}
   }
   int status=conn.getResponseCode();
   item.put("status",status);
   JSONArray fields=setCookies(conn.getHeaderFields());
   if(fields.length()>0)item.put("setCookieFields",fields);
   String location=conn.getHeaderField("Location");
   if(location!=null)item.put("location",location);
   item.put("bodyText",read(status>=400?conn.getErrorStream():conn.getInputStream()));
  }catch(Exception e){
   item.put("error",e.getClass().getSimpleName()+": "+e.getMessage());
  }
  if(handler instanceof RecordingManager){
   JSONArray store=item.getJSONArray("storeAfter");
   for(HttpCookie cookie:((RecordingManager)handler).getCookieStore().getCookies())
    store.put(obj("name",cookie.getName(),"httpOnly",cookie.isHttpOnly(),"secure",cookie.getSecure(),"domain",String.valueOf(cookie.getDomain()),"path",String.valueOf(cookie.getPath())));
  }
  return item;
 }
 static JSONObject empty(String id){
  return obj("case",id,"status",JSONObject.NULL,"error",JSONObject.NULL,"location",JSONObject.NULL,"bodyText",JSONObject.NULL,"setCookieFields",JSONObject.NULL,
   "handlerEvents",new JSONArray(),"authenticatorEvents",new JSONArray(),"perConnectionEvents",new JSONArray(),"storeAfter",new JSONArray(),
   "handlerVisible",false,"authenticatorVisible",false,"perConnectionResult",JSONObject.NULL,"probeAnswered",JSONObject.NULL,"probeAnsweredAfterClear",JSONObject.NULL);
 }
 void save(String name){try(java.io.FileOutputStream out=openFileOutput(name,MODE_PRIVATE)){out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}}
}
