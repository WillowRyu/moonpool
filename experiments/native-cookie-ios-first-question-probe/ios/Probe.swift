import UIKit
import WebKit

@MainActor final class Scheme:NSObject,WKURLSchemeHandler {
    func webView(_ webView:WKWebView,start task:WKURLSchemeTask) {
        let url=task.request.url!,fixtures=Bundle.main.bundleURL.appendingPathComponent("Fixtures")
        let file=["/frame":"frame.html","/storage":"storage.html"][url.path]
        let data=file.flatMap{try? Data(contentsOf:fixtures.appendingPathComponent($0))} ?? Data("Unmapped research resource".utf8)
        task.didReceive(URLResponse(url:url,mimeType:"text/html",expectedContentLength:data.count,textEncodingName:"utf-8"));task.didReceive(data);task.didFinish()
    }
    func webView(_ webView:WKWebView,stop task:WKURLSchemeTask) { }
}

@MainActor final class Controller:UIViewController,WKNavigationDelegate {
    let run:String,base:String,mode:String,only:String?
    let stack=UIStackView()
    var report:[String:Any]=[:],seeded:[[String:Any]]=[],checks:[[String:Any]]=[],errors:[[String:Any]]=[]
    init(run:String,base:String,mode:String,only:String?){self.run=run;self.base=base;self.mode=mode;self.only=only;super.init(nibName:nil,bundle:nil)}
    required init?(coder:NSCoder){fatalError()}
    var documents:URL {FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]}
    func save(_ name:String){report["seeded"]=seeded;report["checks"]=checks;report["errors"]=errors;if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]){try? data.write(to:documents.appendingPathComponent(name),options:.atomic)}}
    func webView(_ webView:WKWebView,didFailProvisionalNavigation navigation:WKNavigation!,withError error:Error){failed(error)}
    func webView(_ webView:WKWebView,didFail navigation:WKNavigation!,withError error:Error){failed(error)}
    func failed(_ error:Error){let e=error as NSError;errors.append(["domain":e.domain,"code":e.code])}
    func make(_ store:WKWebsiteDataStore)->WKWebView {
        let c=WKWebViewConfiguration();c.websiteDataStore=store;c.setURLSchemeHandler(Scheme(),forURLScheme:"moonpool")
        let web=WKWebView(frame:.zero,configuration:c);web.navigationDelegate=self;stack.addArrangedSubview(web);return web
    }
    func discard(_ web:WKWebView){web.navigationDelegate=nil;web.stopLoading();stack.removeArrangedSubview(web);web.removeFromSuperview()}
    func policy(_ store:WKWebsiteDataStore,_ allow:Bool) async {
        await withCheckedContinuation { continuation in store.httpCookieStore.setCookiePolicy(allow ? .allow:.disallow){continuation.resume()} }
    }
    func allows(_ store:WKWebsiteDataStore) async -> Bool {
        await withCheckedContinuation { continuation in store.httpCookieStore.getCookiePolicy{continuation.resume(returning:$0 == .allow)} }
    }
    func names(_ store:WKWebsiteDataStore) async -> [String] {
        await withCheckedContinuation { continuation in store.httpCookieStore.getAllCookies{continuation.resume(returning:$0.map(\.name).sorted())} }
    }
    func records(_ store:WKWebsiteDataStore) async -> [String] {
        await withCheckedContinuation { continuation in
            store.fetchDataRecords(ofTypes:[WKWebsiteDataTypeCookies]){continuation.resume(returning:$0.map(\.displayName).sorted())}
        }
    }
    func sleep(_ seconds:Double) async {try? await Task.sleep(nanoseconds:UInt64(seconds*1_000_000_000))}
    func origin(_ top:String)->String {top=="moonpool" ? "moonpool://com.example.emptystore":base.replacingOccurrences(of:"localhost",with:top)}
    /// A deadline is a recorded outcome here: the verifier decides what a failed load means.
    func pollText(_ web:WKWebView,_ expression:String,seconds:Double=5) async -> String? {
        for _ in 0..<Int(seconds*10) {
            if let value=try? await web.evaluateJavaScript(expression),let text=value as? String {return text}
            await sleep(0.1)
        }
        return nil
    }
    /// Loads the service page directly (first-party) or framed under `top`.
    func visit(_ store:WKWebsiteDataStore,_ c:[String:Any],_ step:String,top:String,write:String) async -> Bool {
        let service=c["service"] as! String
        let page=origin(service)+"/page?run="+run+"&case="+(c["id"] as! String)+"&step="+step+"&write="+write
        let web=make(store);defer{discard(web)}
        let direct=top==service,target=page.addingPercentEncoding(withAllowedCharacters:.alphanumerics)!
        web.load(URLRequest(url:URL(string:direct ? page:origin(top)+"/frame?target="+target)!,cachePolicy:.reloadIgnoringLocalCacheData))
        return await pollText(web,direct ? "window.pageResult||null":"window.frameResult||null") != nil
    }
    /// Public fixture data in localStorage and IndexedDB, in the guest's own custom-scheme origin.
    func storage(_ store:WKWebsiteDataStore,_ id:String,seed:Bool) async -> Any {
        let web=make(store);defer{discard(web)}
        web.load(URLRequest(url:URL(string:origin("moonpool")+"/storage?token="+id+"&seed="+(seed ? "1":"0"))!))
        guard let text=await pollText(web,"window.storageReady ? JSON.stringify(window.storageReady):null"),let data=text.data(using:.utf8),
              let parsed=try? JSONSerialization.jsonObject(with:data) else {return NSNull()}
        return parsed
    }
    override func viewDidLoad(){super.viewDidLoad();stack.axis = .vertical;stack.distribution = .fillEqually;stack.frame=view.bounds;stack.autoresizingMask=[.flexibleWidth,.flexibleHeight];view.addSubview(stack);Task{await execute()}}
    func execute() async {
        report=["platform":"ios","run":run,"base":base,"mode":mode,"only":only ?? NSNull(),"os":UIDevice.current.systemVersion,"complete":false]
        // Retained working order: initialize WebKit with an empty never-loaded view before any
        // identified store. The known crashing first-call enumeration is never executed.
        let initConfig=WKWebViewConfiguration();initConfig.websiteDataStore = .nonPersistent()
        let initializer=WKWebView(frame:.zero,configuration:initConfig)
        withExtendedLifetime(initializer){}
        do {
            let config=try JSONSerialization.jsonObject(with:Data(contentsOf:Bundle.main.bundleURL.appendingPathComponent("Fixtures/config.json"))) as! [String:Any]
            let stores=config["stores"] as! [[String:Any]],saved=documents.appendingPathComponent("partitions.json")
            if mode=="seed" {
                for c in stores {seeded.append(await seed(c));save("progress.json")}
                let identifiers=Dictionary(uniqueKeysWithValues:seeded.map{($0["case"] as! String,$0["partition"] as! String)})
                try JSONSerialization.data(withJSONObject:identifiers).write(to:saved,options:.atomic)
                // Cookies written shortly before an exit did not always survive it, so every store settles first.
                await sleep(45)
            } else {
                // Exactly one store, so this is the first cookie question this process asks.
                let identifiers=try JSONSerialization.jsonObject(with:Data(contentsOf:saved)) as! [String:String]
                for c in stores where c["id"] as? String==only {checks.append(await check(c,identifiers[c["id"] as! String]!));save("progress.json")}
            }
            report["complete"]=true
        }catch{report["error"]=String(describing:error)}
        save("report.json")
    }
    /// Runs in an earlier process than the check. A never-denied store receives no policy call at all.
    func seed(_ c:[String:Any]) async -> [String:Any] {
        let store=WKWebsiteDataStore(forIdentifier:UUID()),id=c["id"] as! String
        let keeper=make(store);defer{discard(keeper)}
        if c["allowBefore"] as! Bool {await policy(store,true)}
        var loaded:[Bool]=[]
        for step in c["steps"] as! [[String:String]] {loaded.append(await visit(store,c,step["step"]!,top:step["top"]!,write:"header"))}
        var ready:Any=NSNull()
        if c["storage"] as! Bool {
            let written=await storage(store,id,seed:true)
            ready = !(written is NSNull)
        }
        await sleep(0.3)
        let inventory=await names(store)
        if c["denyAfter"] as! Bool {await policy(store,false)}
        return ["case":id,"kind":c["kind"]!,"partition":store.identifier!.uuidString,"visitsLoaded":loaded,"storageReady":ready,"inventoryAfterSeed":inventory]
    }
    func evaluate(_ store:WKWebsiteDataStore,_ order:String) async -> [String:Any] {
        if order=="records-first" {
            let found=await records(store)
            return ["records":found,"names":await names(store)]
        }
        let found=await names(store)
        return ["names":found,"records":await records(store)]
    }
    /// The accepted rule: await the deny policy, then ask both sources. Nothing else may precede it,
    /// because a policy read or a load would itself change what the first enumeration reports.
    func check(_ c:[String:Any],_ identifier:String) async -> [String:Any] {
        let id=c["id"] as! String,order=c["order"] as! String
        let store=WKWebsiteDataStore(forIdentifier:UUID(uuidString:identifier)!)
        let keeper=make(store);defer{discard(keeper)}
        var entry:[String:Any]=["case":id,"kind":c["kind"]!,"order":order,"partition":store.identifier!.uuidString]
        if c["hazard"] as! Bool {entry["namesBeforePolicy"]=await names(store)}
        await policy(store,false)
        entry["first"]=await evaluate(store,order)
        entry["policyAllowsAfterRule"]=await allows(store)
        await sleep(1)
        entry["later"]=await evaluate(store,order)
        entry["witnessFirstLoaded"]=await visit(store,c,"witness-first",top:c["service"] as! String,write:"none")
        entry["witnessXsiteLoaded"]=await visit(store,c,"witness-xsite",top:c["seedTop"] as! String,write:"none")
        entry["storage"]=c["storage"] as! Bool ? await storage(store,id,seed:false):NSNull()
        entry["inventoryFinal"]=await names(store)
        return entry
    }
}

@main @MainActor final class AppDelegate:UIResponder,UIApplicationDelegate {
    var window:UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?=nil)->Bool {
        let args=ProcessInfo.processInfo.arguments
        func value(_ key:String)->String{args[args.firstIndex(of:key)!+1]}
        let only=args.contains("--only") ? value("--only"):nil
        let window=UIWindow(frame:UIScreen.main.bounds);window.rootViewController=Controller(run:value("--run"),base:value("--base"),mode:value("--mode"),only:only);self.window=window;window.makeKeyAndVisible();return true
    }
}
