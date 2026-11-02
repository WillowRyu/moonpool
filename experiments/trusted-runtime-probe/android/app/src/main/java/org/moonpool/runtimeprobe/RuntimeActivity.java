package org.moonpool.runtimeprobe;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.WebView;
import android.widget.TextView;
import androidx.javascriptengine.JavaScriptIsolate;
import androidx.javascriptengine.JavaScriptSandbox;
import com.google.common.util.concurrent.ListenableFuture;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Host-only engine compatibility; public JS provider fixtures, no guest bridge. */
public final class RuntimeActivity extends Activity {
    private final ExecutorService executor = Executors.newSingleThreadExecutor(task -> new Thread(task, "MoonpoolT27Host"));
    private final Handler main = new Handler(Looper.getMainLooper());
    private final JSONArray samples = new JSONArray();
    private final JSONArray events = new JSONArray();
    private final Map<String,String> snapshots = new HashMap<>();
    private JavaScriptSandbox sandbox;
    private String bundle;
    private String scheduler;
    private String run;
    private TextView status;
    private JSONObject report;
    private int index;

    interface Result { void accept(String value); }
    private static JSONObject json(Object... pairs) {
        JSONObject value = new JSONObject();
        try { for (int i=0;i<pairs.length;i+=2) value.put((String)pairs[i],pairs[i+1]); }
        catch(Exception error) { throw new IllegalStateException(error); }
        return value;
    }
    private void event(String type,String owner) { events.put(json("type",type,"owner",owner)); }
    private String asset(String name) throws Exception {
        try (var stream=getAssets().open(name); var bytes=new ByteArrayOutputStream()) {
            byte[] chunk=new byte[8192];int count;
            while((count=stream.read(chunk))!=-1) bytes.write(chunk,0,count);
            return bytes.toString(StandardCharsets.UTF_8.name());
        }
    }
    private final class Owner {
        final String name;
        final JavaScriptIsolate isolate;
        boolean active=true;
        Owner(String name) {
            this.name=name;isolate=sandbox.createIsolate();
            event(Looper.myLooper()!=Looper.getMainLooper() && Thread.currentThread().getName().equals("MoonpoolT27Host") ? "owner-executor-confirmed" : "wrong-executor",name);
        }
        void eval(String script,Result next) {
            if(!active) {event("retired-control-dropped",name);return;}
            ListenableFuture<String> future=isolate.evaluateJavaScriptAsync(script);
            future.addListener(()->{
                if(!active) {event("late-control-dropped",name);return;}
                try { next.accept(future.get()); }
                catch(Exception error) {fail(error);}
            },executor);
        }
        void close() {
            active=false;isolate.close();
            main.postDelayed(()->executor.execute(()->{
                if(!active) {event("late-control-dropped",name);return;}
                event("late-control-unexpectedly-active",name);
            }),40);
        }
    }
    private void next() {
        if(index==3) {main.postDelayed(()->executor.execute(this::finishProbe),150);return;}
        String name=new String[]{"a-first","a-recreated","b-independent"}[index];
        String app=index==2?"com.example.runtime.b":"com.example.runtime.a";
        String write=index==0?"saved-A":index==2?"saved-B":null;index++;
        JSONObject config=json("appId",app,"platform","android","initialValue",snapshots.getOrDefault(app,null)==null?JSONObject.NULL:snapshots.get(app));
        if(write!=null) {try {config.put("writeValue",write);}catch(Exception error){fail(error);return;}}
        runOnUiThread(()->status.setText("T27 JavaScriptSandbox / "+run+" / "+name));
        JavaScriptIsolate guest=sandbox.createIsolate();
        ListenableFuture<String> future=guest.evaluateJavaScriptAsync("typeof __t27");
        future.addListener(()->{
            try {
                boolean isolated=future.get().equals("undefined");guest.close();
                Owner owner=new Owner(name);
                owner.eval(scheduler+"\n"+bundle+"\n__t27.start("+JSONObject.quote(config.toString())+");'started'",
                    ignored->poll(owner,app,isolated,400));
            }catch(Exception error){fail(error);}
        },executor);
    }
    private void poll(Owner owner,String app,boolean isolated,int remaining) {
        owner.eval("__t27Scheduler.tick();__t27.report()",text->{
            try {
                JSONObject common=new JSONObject(text);
                if(common.optBoolean("complete")||remaining==0) {
                    if(common.opt("storedValue") instanceof String) snapshots.put(app,common.getString("storedValue"));
                    owner.eval("__t27.close();__t27Scheduler.clear();JSON.stringify(__t27Scheduler.snapshot())",state->{
                        samples.put(json("name",owner.name,"appId",app,"common",common,
                            "guestProbeGlobalAbsent",isolated,"schedulerAfterClose",state));
                        owner.close();next();
                    });
                } else main.postDelayed(()->executor.execute(()->poll(owner,app,isolated,remaining-1)),5);
            }catch(Exception error){fail(error);}
        });
    }
    private void fail(Exception error) {
        try {report.put("errorClass",error.getClass().getSimpleName());}catch(Exception ignored){}
        finishProbe();
    }
    private void finishProbe() {
        if(sandbox!=null) {sandbox.close();sandbox=null;}
        try {
            report.put("samples",samples);report.put("events",events);report.put("complete",true);
            try(var file=new FileOutputStream(new File(getFilesDir(),"report.json"))) {
                file.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
            }
            runOnUiThread(()->status.setText("T27 JavaScriptSandbox / "+run+" complete: "+samples.length()+" runtime owners"));
        }catch(Exception error){runOnUiThread(()->status.setText("Report write failed"));}
    }
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);run=getIntent().getStringExtra("run");
        if(!java.util.List.of("first","repeat").contains(run))throw new IllegalArgumentException("Unknown run");
        status=new TextView(this);status.setTextSize(19);status.setPadding(20,100,20,30);setContentView(status);
        new File(getFilesDir(),"report.json").delete();
        boolean supported=JavaScriptSandbox.isSupported();
        report=json("platform","android","engine","JavaScriptSandbox","run",run,"supported",supported,
            "os",android.os.Build.VERSION.RELEASE,"sdk",android.os.Build.VERSION.SDK_INT,
            "executor","one native executor serializes runtime owners",
            "providerScope","JS provider test doubles; native snapshot seeding only");
        if(WebView.getCurrentWebViewPackage()!=null) {
            try {report.put("webView",WebView.getCurrentWebViewPackage().versionName);report.put("webViewPackage",WebView.getCurrentWebViewPackage().packageName);}catch(Exception error){throw new IllegalStateException(error);}
        }
        if(!supported) {finishProbe();return;}
        try {bundle=asset("kernel-probe.js");scheduler=asset("timer-adapter.js");}catch(Exception error){fail(error);return;}
        ListenableFuture<JavaScriptSandbox> future=JavaScriptSandbox.createConnectedInstanceAsync(this);
        future.addListener(()->{
            try {sandbox=future.get();next();}catch(Exception error){fail(error);}
        },executor);
    }
    @Override protected void onDestroy() {
        main.removeCallbacksAndMessages(null);
        executor.shutdown();super.onDestroy();
    }
}
