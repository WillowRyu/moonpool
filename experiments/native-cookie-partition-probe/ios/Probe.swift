import UIKit
import WebKit

@MainActor final class Scheme:NSObject,WKURLSchemeHandler {
    func webView(_ webView:WKWebView,start task:WKURLSchemeTask) {
        let url=task.request.url!
        let data=url.path=="/frame" ? (try? Data(contentsOf:Bundle.main.bundleURL.appendingPathComponent("Fixtures/frame.html"))) ?? Data():Data("Unmapped research resource".utf8)
        task.didReceive(URLResponse(url:url,mimeType:"text/html",expectedContentLength:data.count,textEncodingName:"utf-8"));task.didReceive(data);task.didFinish()
    }
    func webView(_ webView:WKWebView,stop task:WKURLSchemeTask) { }
}

/// Independent engine signal; a change here means a cookie write reached the store.
final class Watcher:NSObject,WKHTTPCookieStoreObserver {
    var changes=0
    func cookiesDidChange(in cookieStore:WKHTTPCookieStore) { changes+=1 }
}

@MainActor final class Controller:UIViewController,WKNavigationDelegate {
    let run:String,base:String,mode:String
    let stack=UIStackView()
    let control=URLSession(configuration:.ephemeral)
    var report:[String:Any]=[:],samples:[[String:Any]]=[],writers:[[String:Any]]=[],reopened:[[String:Any]]=[],seeded:[[String:Any]]=[],warmups:[[String:Any]]=[],errors:[[String:Any]]=[]
    init(run:String,base:String,mode:String){self.run=run;self.base=base;self.mode=mode;super.init(nibName:nil,bundle:nil)}
    required init?(coder:NSCoder){fatalError()}
    var documents:URL {FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]}
    func save(_ name:String){report["samples"]=samples;report["writers"]=writers;report["reopened"]=reopened;report["seeded"]=seeded;report["warmups"]=warmups;report["errors"]=errors;if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]){try? data.write(to:documents.appendingPathComponent(name),options:.atomic)}}
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
    func inventory(_ store:WKWebsiteDataStore) async -> [HTTPCookie] {
        await withCheckedContinuation { continuation in store.httpCookieStore.getAllCookies{continuation.resume(returning:$0)} }
    }
    func names(_ store:WKWebsiteDataStore) async -> [String] {(await inventory(store)).map(\.name).sorted()}
    func set(_ store:WKWebsiteDataStore,_ cookie:HTTPCookie) async {
        await withCheckedContinuation { continuation in store.httpCookieStore.setCookie(cookie){continuation.resume()} }
    }
    func snapshot(_ cookies:[HTTPCookie])->[[String:String]] {
        cookies.sorted{$0.name<$1.name}.map{cookie in Dictionary(uniqueKeysWithValues:(cookie.properties ?? [:]).map{($0.key.rawValue,String(describing:$0.value))})}
    }
    func sleep(_ seconds:Double) async {try? await Task.sleep(nanoseconds:UInt64(seconds*1_000_000_000))}
    func origin(_ top:String)->String {top=="moonpool" ? "moonpool://com.example.partition":base.replacingOccurrences(of:"localhost",with:top)}
    /// A deadline is a recorded outcome here: a blocked embedding must not end the run.
    func pollText(_ web:WKWebView,_ expression:String,seconds:Double=5) async -> String? {
        for _ in 0..<Int(seconds*10) {
            if let value=try? await web.evaluateJavaScript(expression),let text=value as? String {return text}
            await sleep(0.1)
        }
        return nil
    }
    func query(_ id:String,_ step:String)->String {"?run="+run+"&case="+id+"&step="+step}
    func ask(_ path:String,_ id:String) async -> [String:Any] {
        guard let url=URL(string:base+path+"?run="+run+"&case="+id),let (data,_)=try? await control.data(from:url),
              let parsed=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else {return [:]}
        return parsed
    }
    func waitHeld(_ id:String) async -> Bool {
        for _ in 0..<50 {
            if (await ask("/held",id))["held"] as? Bool == true {return true}
            await sleep(0.1)
        }
        return false
    }
    func parse(_ text:String?)->Any {
        guard let text,let data=text.data(using:.utf8),let parsed=try? JSONSerialization.jsonObject(with:data) else {return NSNull()}
        return parsed
    }
    /// Loads the service page either directly (first-party) or framed under `top`.
    func visit(_ store:WKWebsiteDataStore,_ c:[String:Any],_ step:String,top:String,write:String) async -> [String:Any] {
        let service=c["service"] as! String,id=c["id"] as! String
        let page=origin(service)+"/page"+query(id,step)+"&write="+write
        let web=make(store);defer{discard(web)}
        let direct=top==service
        let target=page.addingPercentEncoding(withAllowedCharacters:.alphanumerics)!
        web.load(URLRequest(url:URL(string:direct ? page:origin(top)+"/frame?target="+target)!,cachePolicy:.reloadIgnoringLocalCacheData))
        let text=await pollText(web,direct ? "window.pageResult||null":"window.frameResult||null")
        return ["loaded":text != nil,"top":top,"result":parse(text)]
    }
    /// Server-witnessed read: under deny, retained cookies are still sent on this OS.
    func echo(_ store:WKWebsiteDataStore,_ id:String) async {
        let web=make(store);defer{discard(web)}
        web.load(URLRequest(url:URL(string:base+"/page"+query(id,"echo")+"&write=none")!,cachePolicy:.reloadIgnoringLocalCacheData))
        _=await pollText(web,"window.pageResult||null")
    }
    func cookie(_ name:String)->HTTPCookie {
        HTTPCookie(properties:[.name:name,.value:"public",.domain:"localhost",.path:"/",.secure:"TRUE",.maximumAge:"600"])!
    }
    override func viewDidLoad(){super.viewDidLoad();stack.axis = .vertical;stack.distribution = .fillEqually;stack.frame=view.bounds;stack.autoresizingMask=[.flexibleWidth,.flexibleHeight];view.addSubview(stack);Task{await execute()}}
    func execute() async {
        report=["platform":"ios","run":run,"base":base,"mode":mode,"os":UIDevice.current.systemVersion,"complete":false]
        // Retained working order: initialize WebKit with an empty never-loaded view before
        // any identified store. The known crashing first-call enumeration is never executed.
        let initConfig=WKWebViewConfiguration();initConfig.websiteDataStore = .nonPersistent()
        let initializer=WKWebView(frame:.zero,configuration:initConfig)
        withExtendedLifetime(initializer){}
        do {
            let config=try JSONSerialization.jsonObject(with:Data(contentsOf:Bundle.main.bundleURL.appendingPathComponent("Fixtures/config.json"))) as! [String:Any]
            let partitions=config["partition"] as! [[String:Any]],saved=documents.appendingPathComponent("partitions.json")
            let warmupSaved=documents.appendingPathComponent("warmup-partitions.json")
            if mode=="warmup-seed" {
                for c in config["warmup"] as! [[String:Any]] {seeded.append(await warmupSeed(c));save("progress.json")}
                let identifiers=Dictionary(uniqueKeysWithValues:seeded.map{($0["case"] as! String,$0["partition"] as! String)})
                try JSONSerialization.data(withJSONObject:identifiers).write(to:warmupSaved,options:.atomic)
            } else if mode=="warmup" {
                let identifiers=try JSONSerialization.jsonObject(with:Data(contentsOf:warmupSaved)) as! [String:String]
                for c in config["warmup"] as! [[String:Any]] {warmups.append(await warmup(c,identifiers[c["id"] as! String]!));save("progress.json")}
            } else if mode=="reopen" {
                let identifiers=try JSONSerialization.jsonObject(with:Data(contentsOf:saved)) as! [String:String]
                for c in partitions {reopened.append(await reopen(c,identifiers[c["id"] as! String]!));save("progress.json")}
            } else {
                for c in partitions {samples.append(await partition(c));save("progress.json")}
                let identifiers=Dictionary(uniqueKeysWithValues:samples.map{($0["case"] as! String,$0["partition"] as! String)})
                try JSONSerialization.data(withJSONObject:identifiers).write(to:saved,options:.atomic)
                for c in config["writer"] as! [[String:Any]] {writers.append(await writer(c));save("progress.json")}
            }
            report["complete"]=true
        }catch{report["error"]=String(describing:error)}
        save("report.json")
    }
    func partition(_ c:[String:Any]) async -> [String:Any] {
        let store=WKWebsiteDataStore(forIdentifier:UUID()),write=c["write"] as! String,service=c["service"] as! String
        let seedTop=c["seedTop"] as! String,otherTop=c["otherTop"] as! String
        await policy(store,true)
        // A live view precedes every enumeration of this identified store.
        let keeper=make(store);defer{discard(keeper)}
        var visits:[String:Any]=[:]
        visits["seed"]=await visit(store,c,"seed",top:seedTop,write:write)
        await sleep(0.5)
        let afterSeed=await names(store)
        visits["read-same"]=await visit(store,c,"read-same",top:seedTop,write:"none")
        visits["read-other"]=await visit(store,c,"read-other",top:otherTop,write:"none")
        visits["read-first"]=await visit(store,c,"read-first",top:service,write:"none")
        let afterReads=await names(store),cookies=snapshot(await inventory(store))
        await policy(store,false)
        let afterDeny=await names(store),denied=await allows(store)
        visits["read-same-deny"]=await visit(store,c,"read-same-deny",top:seedTop,write:"none")
        return ["case":c["id"]!,"visits":visits,"inventoryAfterSeed":afterSeed,"inventoryAfterReads":afterReads,"inventoryAfterDeny":afterDeny,
                "inventoryFinal":await names(store),"policyAllowsAfterDeny":denied,"cookies":cookies,"partition":store.identifier!.uuidString]
    }
    /// The production admission path: a new process checks a store it did not write in this run.
    /// Inventory runs before any page loads in this store, with only a never-loaded view alive.
    func reopen(_ c:[String:Any],_ identifier:String) async -> [String:Any] {
        let store=WKWebsiteDataStore(forIdentifier:UUID(uuidString:identifier)!)
        let keeper=make(store);defer{discard(keeper)}
        let atOpen=await names(store),allowsAtOpen=await allows(store)
        let read=await visit(store,c,"read-same-reopen",top:c["seedTop"] as! String,write:"none")
        return ["case":c["id"]!,"partition":identifier,"inventoryAtOpen":atOpen,"policyAllowsAtOpen":allowsAtOpen,"visit":read,"inventoryFinal":await names(store)]
    }
    func warmupSeed(_ c:[String:Any]) async -> [String:Any] {
        let store=WKWebsiteDataStore(forIdentifier:UUID())
        await policy(store,true)
        let keeper=make(store);defer{discard(keeper)}
        let first=await visit(store,c,"seed-first",top:c["service"] as! String,write:"header")
        let xsite=await visit(store,c,"seed-xsite",top:c["seedTop"] as! String,write:"header")
        await sleep(0.5)
        await policy(store,false)
        return ["case":c["id"]!,"partition":store.identifier!.uuidString,"seedFirstLoaded":first["loaded"]!,"seedXsiteLoaded":xsite["loaded"]!,"inventoryAfterSeed":await names(store)]
    }
    func records(_ store:WKWebsiteDataStore) async -> [String] {
        await withCheckedContinuation { continuation in
            store.fetchDataRecords(ofTypes:[WKWebsiteDataTypeCookies]){continuation.resume(returning:$0.map(\.displayName).sorted())}
        }
    }
    /// Which non-guest step, if any, makes the first enumeration of a reopened store truthful?
    /// Each strategy owns one store, so one strategy cannot warm another's cookie state.
    func warmup(_ c:[String:Any],_ identifier:String) async -> [String:Any] {
        let id=c["id"] as! String,action=c["action"] as! String,service=c["service"] as! String
        let store=WKWebsiteDataStore(forIdentifier:UUID(uuidString:identifier)!)
        let keeper=make(store),helper=make(store);defer{discard(keeper);discard(helper)}
        switch action {
        case "policy": await policy(store,false)
        case "get-policy": _=await allows(store)
        case "blank":
            helper.load(URLRequest(url:URL(string:"about:blank")!))
            _=await pollText(helper,"document.readyState==='complete' ? 'ok':null")
        case "scheme":
            helper.load(URLRequest(url:URL(string:origin("moonpool")+"/frame?target=about%3Ablank")!))
            _=await pollText(helper,"document.readyState==='complete' ? 'ok':null")
        case "network":
            helper.load(URLRequest(url:URL(string:base+"/page"+query(id,"warm")+"&write=none")!,cachePolicy:.reloadIgnoringLocalCacheData))
            _=await pollText(helper,"window.pageResult||null")
        default: break
        }
        var timeline:[[String:Any]]=[],elapsed=0.0
        // "twice" repeats the enumeration with no added delay, separating a second call from elapsed time.
        for at in action=="wait" ? [0,0.5,2,5]:action=="twice" ? [0,0]:[0,2] {
            await sleep(at-elapsed);elapsed=at
            // Records are asked first so a truthful answer cannot come from the enumeration before it.
            let found=action=="records" ? await records(store):[]
            timeline.append(["at":at,"records":found,"names":await names(store)])
        }
        let first=await visit(store,c,"witness-first",top:service,write:"none")
        let xsite=await visit(store,c,"witness-xsite",top:c["seedTop"] as! String,write:"none")
        return ["case":id,"partition":identifier,"action":action,"timeline":timeline,"witnessFirstLoaded":first["loaded"]!,"witnessXsiteLoaded":xsite["loaded"]!,"inventoryFinal":await names(store)]
    }
    func writer(_ c:[String:Any]) async -> [String:Any] {
        let id=c["id"] as! String
        var sample:[String:Any]=["case":id,"kind":c["kind"]!]
        switch c["kind"] as! String {
        case "hold": await hold(c,id,&sample)
        case "burst": await burst(c,id,&sample)
        case "native-unawaited": await nativeUnawaited(id,&sample)
        case "native-under-deny": await nativeUnderDeny(id,&sample)
        default: await secondHandle(id,&sample)
        }
        return sample
    }
    /// The server parks a Set-Cookie response so the empty check happens while a real write is outstanding.
    func hold(_ c:[String:Any],_ id:String,_ sample:inout [String:Any]) async {
        let store=WKWebsiteDataStore(forIdentifier:UUID()),action=c["action"] as! String
        await policy(store,true)
        let keeper=make(store),web=make(store),watcher=Watcher();defer{discard(keeper)}
        store.httpCookieStore.add(watcher)
        let url=base+"/hold"+query(id,"hold"),navigation=c["request"] as! String=="navigation"
        if navigation {web.load(URLRequest(url:URL(string:url)!,cachePolicy:.reloadIgnoringLocalCacheData))}
        else {
            web.load(URLRequest(url:URL(string:base+"/page"+query(id,"host")+"&write=none")!,cachePolicy:.reloadIgnoringLocalCacheData))
            _=await pollText(web,"window.pageResult||null")
            _=try? await web.evaluateJavaScript("window.fetchDone=null;fetch(\"\(url)\",{credentials:'include'}).then(r=>r.text()).then(()=>{window.fetchDone='done'}).catch(e=>{window.fetchDone='error:'+e.name});'started'")
        }
        sample["heldObserved"]=await waitHeld(id)
        sample["inventoryBeforeRelease"]=await names(store)
        let changesAtCheck=watcher.changes
        if action=="deny" {await policy(store,false)}
        if action=="teardown" {discard(web);await sleep(0.3)}
        sample["policyAllows"]=await allows(store)
        _=await ask("/release",id)
        // A torn-down view has no page left to confirm delivery; the server's clientClosed row covers that case.
        sample["responseDelivered"]=action=="teardown" ? false:await pollText(web,navigation ? "window.networkReady ? 'ok':null":"window.fetchDone==='done' ? 'ok':null",seconds:4) != nil
        await sleep(1.5)
        sample["inventoryAfterRelease"]=await names(store)
        sample["observerChangesAfterCheck"]=watcher.changes-changesAtCheck
        await echo(store,id)
        sample["inventoryFinal"]=await names(store)
        if action != "teardown" {discard(web)}
        store.httpCookieStore.remove(watcher)
    }
    /// A live script keeps writing across the policy change; indexes show when each write was issued.
    func burst(_ c:[String:Any],_ id:String,_ sample:inout [String:Any]) async {
        let store=WKWebsiteDataStore(forIdentifier:UUID())
        await policy(store,true)
        let keeper=make(store),web=make(store);defer{discard(web);discard(keeper)}
        web.load(URLRequest(url:URL(string:base+"/writer"+query(id,"burst")+"&api="+(c["api"] as! String))!,cachePolicy:.reloadIgnoringLocalCacheData))
        _=await pollText(web,"window.writes>=3 ? 'go':null")
        await sleep(0.2)
        func writes() async -> Int {(try? await web.evaluateJavaScript("window.writes")) as? Int ?? -1}
        sample["writesAtStart"]=await writes()
        sample["inventoryBeforePolicy"]=await names(store)
        await policy(store,false)
        sample["writesAtCompletion"]=await writes()
        sample["inventoryAtCompletion"]=await names(store)
        sample["policyAllows"]=await allows(store)
        await sleep(1)
        sample["writesLater"]=await writes()
        sample["inventoryLater"]=await names(store)
        let stopped=(try? await web.evaluateJavaScript("window.stopWriter()")) as? String
        sample["stopped"]=stopped=="stopped"
        sample["writeError"]=((try? await web.evaluateJavaScript("window.writeError")) as? String) ?? NSNull()
        await echo(store,id)
        sample["inventoryFinal"]=await names(store)
    }
    /// Whether an enumeration observes a native write that was queued but not yet completed.
    func nativeUnawaited(_ id:String,_ sample:inout [String:Any]) async {
        let store=WKWebsiteDataStore(forIdentifier:UUID()),name="t28w_"+id
        await policy(store,true)
        let keeper=make(store);defer{discard(keeper)}
        store.httpCookieStore.setCookie(cookie(name),completionHandler:nil)
        sample["seenImmediately"]=(await names(store)).contains(name)
        await set(store,cookie(name+"_completed"))
        sample["seenAfterCompletion"]=(await names(store)).contains(name)
        sample["inventoryFinal"]=await names(store)
    }
    /// The deny policy governs web content; this measures whether it also covers the native API.
    func nativeUnderDeny(_ id:String,_ sample:inout [String:Any]) async {
        let store=WKWebsiteDataStore(forIdentifier:UUID())
        await policy(store,false)
        let keeper=make(store);defer{discard(keeper)}
        await set(store,cookie("t28w_"+id))
        sample["inventoryAfterSet"]=await names(store)
        sample["policyAllows"]=await allows(store)
        await echo(store,id)
    }
    /// Owner exclusion: can a second handle for the same identifier change the first handle's state?
    func secondHandle(_ id:String,_ sample:inout [String:Any]) async {
        let identifier=UUID(),first=WKWebsiteDataStore(forIdentifier:identifier),second=WKWebsiteDataStore(forIdentifier:identifier),name="t28w_"+id
        sample["sameObject"]=first===second
        let keeper=make(first);defer{discard(keeper)}
        await policy(first,false)
        sample["secondSeesFirstPolicy"]=(await allows(second))==false
        await policy(second,true)
        sample["firstSeesSecondPolicy"]=(await allows(first))==true
        await set(second,cookie(name))
        sample["firstSeesSecondCookie"]=(await names(first)).contains(name)
        await policy(first,false)
        sample["policyAfterRestore"]=(await allows(second))==false
    }
}

@main @MainActor final class AppDelegate:UIResponder,UIApplicationDelegate {
    var window:UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?=nil)->Bool {
        let args=ProcessInfo.processInfo.arguments
        func value(_ key:String)->String{args[args.firstIndex(of:key)!+1]}
        let window=UIWindow(frame:UIScreen.main.bounds);window.rootViewController=Controller(run:value("--run"),base:value("--base"),mode:value("--mode"));self.window=window;window.makeKeyAndVisible();return true
    }
}
