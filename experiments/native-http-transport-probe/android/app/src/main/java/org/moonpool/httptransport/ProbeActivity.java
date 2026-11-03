package org.moonpool.httptransport;

import android.app.Activity;
import android.os.Bundle;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.CookieHandler;
import java.net.HttpCookie;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

/** Blocking calls run on one worker thread. The app's network security config scopes the probe CA to loopback. */
public final class ProbeActivity extends Activity {
 private String run;
 private int port,control;
 private JSONObject report;
 private final JSONArray observations=new JSONArray(),errors=new JSONArray();
 static JSONObject obj(Object... fields) {
  JSONObject o=new JSONObject();try {for(int i=0;i<fields.length;i+=2)o.put((String)fields[i],fields[i+1]);}catch(Exception e){throw new IllegalStateException(e);}return o;
 }
 static String read(InputStream input) throws Exception {
  if(input==null)return "";
  try(input;ByteArrayOutputStream out=new ByteArrayOutputStream()) {
   byte[] bytes=new byte[4096];int n;while((n=input.read(bytes))!=-1)out.write(bytes,0,n);return out.toString(StandardCharsets.UTF_8.name());
  }
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);run=getIntent().getStringExtra("run");port=getIntent().getIntExtra("port",0);control=getIntent().getIntExtra("control",0);
  report=obj("platform","android","run",run,"release",android.os.Build.VERSION.RELEASE,"sdkInt",android.os.Build.VERSION.SDK_INT,"observations",observations,"errors",errors,"complete",false);
  new Thread(this::execute).start();
 }
 void execute(){
  try {
   report.put("defaultCookieHandlerNull",CookieHandler.getDefault()==null);
   JSONArray cases;
   try(InputStream input=getAssets().open("cases.json")){cases=new JSONArray(read(input));}
   for(int i=0;i<cases.length();i++){observations.put(perform(cases.getJSONObject(i)));save("progress.json");}
   report.put("complete",true);
  }catch(Exception e){errors.put(obj("error",e.toString()));}
  save("report.json");
 }
 HttpURLConnection open(String origin,JSONObject c) throws Exception {
  String name=c.optString("requestCase",c.getString("id"));
  HttpURLConnection conn=(HttpURLConnection)new URL(origin+c.getString("path")+"?run="+run+"&case="+name).openConnection();
  conn.setInstanceFollowRedirects(false);conn.setUseCaches(false);conn.setConnectTimeout(10000);conn.setReadTimeout(20000);
  conn.setRequestMethod(c.optString("method","GET"));
  if(c.has("attachCookie"))conn.setRequestProperty("Cookie",c.getString("attachCookie"));
  if(c.has("body")){conn.setDoOutput(true);try(OutputStream out=conn.getOutputStream()){out.write(c.getString("body").getBytes(StandardCharsets.UTF_8));}}
  return conn;
 }
 boolean ask(String path,JSONObject c) throws Exception {
  HttpURLConnection conn=(HttpURLConnection)new URL("https://localhost:"+control+path+"?run="+run+"&case="+c.getString("id")).openConnection();
  conn.setConnectTimeout(10000);conn.setReadTimeout(10000);
  String body=read(conn.getInputStream());conn.disconnect();
  return new JSONObject(body).optBoolean("held");
 }
 /** Header state is read before the body, so a hold can show what is visible at header time. */
 JSONObject head(JSONObject c,HttpURLConnection conn) throws Exception {
  int status=conn.getResponseCode();
  List<String> fields=null;JSONArray names=new JSONArray();
  for(Map.Entry<String,List<String>> entry:conn.getHeaderFields().entrySet()){
   String key=entry.getKey();if(key==null)continue;names.put(key);
   if(key.equalsIgnoreCase("Set-Cookie"))fields=new ArrayList<>(entry.getValue());
  }
  List<String> exact=conn.getHeaderFields().get("Set-Cookie");
  JSONArray parsed=new JSONArray();
  if(fields!=null)for(String field:fields){
   // Diagnostic only: what the platform's own parser makes of the same field.
   try {for(HttpCookie cookie:HttpCookie.parse(field))parsed.put(obj("name",cookie.getName(),"value",cookie.getValue(),"path",String.valueOf(cookie.getPath()),"httpOnly",cookie.isHttpOnly(),"secure",cookie.getSecure(),"maxAge",cookie.getMaxAge()));}
   catch(Exception e){parsed.put(obj("parseError",e.getClass().getSimpleName()));}
  }
  String location=conn.getHeaderField("Location");
  return obj("case",c.getString("id"),"status",status,"error",JSONObject.NULL,"location",location==null?JSONObject.NULL:location,"setCookieFolded",JSONObject.NULL,
   "setCookieFields",fields==null?JSONObject.NULL:new JSONArray(fields),"exactKeySetCookieFound",exact!=null,"headerNames",names,"platformParsed",parsed);
 }
 String body(HttpURLConnection conn,int status) throws Exception {return read(status>=400?conn.getErrorStream():conn.getInputStream());}
 JSONObject perform(JSONObject c) throws Exception {
  String origin="https://localhost:"+port,kind=c.optString("kind");
  if(kind.equals("tls-negative")) {
   // Outside the app's scoped domains, so only the system's own roots apply and must refuse this certificate.
   try {
    HttpURLConnection conn=open("https://10.0.2.2:"+port,c);int status=conn.getResponseCode();
    return obj("case",c.getString("id"),"status",status,"error",JSONObject.NULL,"location",JSONObject.NULL,"bodyText",JSONObject.NULL,"setCookieFields",JSONObject.NULL,"setCookieFolded",JSONObject.NULL);
   }catch(Exception e){
    return obj("case",c.getString("id"),"status",JSONObject.NULL,"error",e.getClass().getSimpleName(),"location",JSONObject.NULL,"bodyText",JSONObject.NULL,"setCookieFields",JSONObject.NULL,"setCookieFolded",JSONObject.NULL);
   }
  }
  if(kind.equals("hold-headers")||kind.equals("hold-body")) {
   JSONObject[] item={null};String[] text={null};Exception[] failure={null};
   Thread worker=new Thread(()->{
    try {HttpURLConnection conn=open(origin,c);JSONObject seen=head(c,conn);synchronized(item){item[0]=seen;}text[0]=body(conn,seen.getInt("status"));}
    catch(Exception e){failure[0]=e;}
   });
   worker.start();
   boolean headers=false;
   if(kind.equals("hold-headers")) {
    for(int i=0;i<50&&!ask("/held",c);i++)Thread.sleep(100);
    Thread.sleep(300);
   } else {
    for(int i=0;i<30;i++){synchronized(item){if(item[0]!=null)break;}Thread.sleep(100);}
    Thread.sleep(300);
   }
   synchronized(item){headers=item[0]!=null;}
   boolean bodyEarly=text[0]!=null;
   ask("/release",c);worker.join(25000);
   if(failure[0]!=null)throw failure[0];
   JSONObject result=item[0];result.put("bodyText",text[0]);
   if(kind.equals("hold-headers"))result.put("respondedBeforeRelease",headers);
   else {result.put("headersBeforeRelease",headers);result.put("bodyBeforeRelease",bodyEarly);}
   return result;
  }
  HttpURLConnection conn=open(origin,c);
  JSONObject result=head(c,conn);
  result.put("bodyText",body(conn,result.getInt("status")));
  return result;
 }
 void save(String name){try(java.io.FileOutputStream out=openFileOutput(name,MODE_PRIVATE)){out.write(report.toString(2).getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}}
}
