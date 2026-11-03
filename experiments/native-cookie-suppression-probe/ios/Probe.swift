import UIKit
import WebKit

@MainActor final class LocalScheme: NSObject, WKURLSchemeHandler {
    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        let url = task.request.url!
        let data: Data
        if url.path == "/page" { data = try! Data(contentsOf: Bundle.main.bundleURL.appendingPathComponent("Fixtures/page.html")) }
        else if url.path == "/frame" { data = Data("<!doctype html><p>cookie-frame-ready</p>".utf8) }
        else { data = Data("Local miss".utf8) }
        task.didReceive(URLResponse(url: url, mimeType: "text/html", expectedContentLength: data.count, textEncodingName: "utf-8"))
        task.didReceive(data); task.didFinish()
    }
    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) { }
}

@MainActor final class Controller: UIViewController, WKNavigationDelegate {
    let run: String, base: String
    let stack = UIStackView()
    var stores: [String: WKWebsiteDataStore] = [:]
    var views: [String: WKWebView] = [:]
    var identifiers: [String: UUID] = [:]
    var events: [[String: Any]] = [], samples: [[String: Any]] = []
    var errors: [ObjectIdentifier: [[String: Any]]] = [:]
    var report: [String: Any] = [:]
    init(run: String, base: String) { self.run=run; self.base=base; super.init(nibName:nil,bundle:nil) }
    required init?(coder: NSCoder) { fatalError() }
    var documents: URL { FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0] }
    func save(_ name: String) {
        report["samples"]=samples; report["events"]=events
        if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]) {
            try? data.write(to:documents.appendingPathComponent(name),options:.atomic)
        }
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { failed(webView,error) }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { failed(webView,error) }
    func failed(_ web: WKWebView,_ error: Error) {
        let e=error as NSError
        errors[ObjectIdentifier(web),default:[]].append(["domain":e.domain,"code":e.code])
    }
    func owner(_ name: String) -> String { name.hasPrefix("a") ? "a" : name }
    func makeViews() {
        for name in ["a1","a2","b","h","u"] {
            let o=owner(name), config=WKWebViewConfiguration()
            config.websiteDataStore=stores[o]!
            config.setURLSchemeHandler(LocalScheme(),forURLScheme:"moonpool")
            let web=WKWebView(frame:.zero,configuration:config); web.navigationDelegate=self
            views[name]=web; stack.addArrangedSubview(web)
            events.append(["event":"created","view":name,"store":config.websiteDataStore.identifier?.uuidString ?? "default"])
        }
    }
    func setPolicy(_ owner: String,_ allow: Bool) async {
        await withCheckedContinuation { continuation in
            stores[owner]!.httpCookieStore.setCookiePolicy(allow ? .allow : .disallow) { continuation.resume() }
        }
    }
    func allows(_ store: WKWebsiteDataStore) async -> Bool {
        await withCheckedContinuation { continuation in
            store.httpCookieStore.getCookiePolicy { continuation.resume(returning:$0 == .allow) }
        }
    }
    func cookies(_ store: WKWebsiteDataStore) async -> [[String: Any]] {
        await withCheckedContinuation { continuation in
            store.httpCookieStore.getAllCookies { list in
                continuation.resume(returning:list.filter { $0.name.hasPrefix("t28_") }.map {
                    ["name":$0.name,"value":$0.value,"domain":$0.domain,"path":$0.path,"secure":$0.isSecure]
                })
            }
        }
    }
    override func viewDidLoad() {
        super.viewDidLoad(); stack.axis = .vertical; stack.distribution = .fillEqually
        stack.frame=view.bounds; stack.autoresizingMask=[.flexibleWidth,.flexibleHeight]; view.addSubview(stack)
        Task { await execute() }
    }
    func execute() async {
        report=["platform":"ios","run":run,"base":base,"os":UIDevice.current.systemVersion,"complete":false]
        // No store enumeration or crash-control path exists in this fixture.
        let initializationConfig=WKWebViewConfiguration(); initializationConfig.websiteDataStore = .nonPersistent()
        let initializer=WKWebView(frame:.zero,configuration:initializationConfig)
        for name in ["a","b","u"] {
            let id=UUID(); identifiers[name]=id; stores[name]=WKWebsiteDataStore(forIdentifier:id)
        }
        stores["h"] = .default()
        withExtendedLifetime(initializer) { }
        report["partitions"]=identifiers.mapValues(\.uuidString).merging(["h":"default"]) { old,_ in old }
        makeViews()
        for name in ["a","b","h","u"] { await setPolicy(name,true) }
        do {
            let config=try JSONSerialization.jsonObject(with:Data(contentsOf:Bundle.main.bundleURL.appendingPathComponent("Fixtures/config.json"))) as! [String:Any]
            let cases=config["cases"] as! [[String:Any]], ids=config["ids"] as! [String:String]
            var stage=""
            for c in cases {
                let nextStage=c["stage"] as! String
                if stage != nextStage {
                    stage=nextStage
                    if stage == "a-blocked" { await setPolicy("a",false) }
                    if stage == "ab-blocked" { await setPolicy("b",false) }
                    if stage == "recreated" || stage == "fresh-blocked" {
                        for web in views.values { web.stopLoading(); web.navigationDelegate=nil; stack.removeArrangedSubview(web); web.removeFromSuperview() }
                        views.removeAll()
                        if stage == "fresh-blocked" {
                            for name in ["a","b"] {
                                identifiers[name]=UUID(); stores[name]=WKWebsiteDataStore(forIdentifier:identifiers[name]!)
                                await setPolicy(name,false)
                            }
                        } else {
                            for name in ["a","b","u"] { stores[name]=WKWebsiteDataStore(forIdentifier:identifiers[name]!) }
                        }
                        makeViews()
                    }
                    var policies:[String:Bool]=[:]
                    for name in ["a","b","h","u"] { policies[name]=await allows(stores[name]!) }
                    events.append(["event":"policy","stage":stage,"values":policies])
                    if policies["h"] != true || policies["u"] != true || (stage == "a-blocked" && policies["b"] != true) {
                        report["unsupported"]="Cookie policy affected unrelated control partition"; save("report.json"); return
                    }
                }
                let name=c["view"] as! String, o=c["owner"] as! String, key=c["id"] as! String
                let web=views[name]!, store=web.configuration.websiteDataStore
                let allow=await allows(store)
                let origin=c["kind"] as! String == "remote" ? base : "moonpool://"+ids[o]!
                let url=URL(string:origin+"/page?run="+run+"&case="+key)!
                errors[ObjectIdentifier(web)]=[]
                events.append(["event":"load","case":key,"policyAllows":allow,"store":store.identifier?.uuidString ?? "default"])
                web.load(URLRequest(url:url,cachePolicy:.reloadIgnoringLocalCacheData))
                var document:[String:Any]=[:]
                for _ in 0..<120 {
                    if let value=try? await web.evaluateJavaScript("JSON.stringify(window.cookieProbe || null)"),
                       let text=value as? String, let data=text.data(using:.utf8),
                       let parsed=try? JSONSerialization.jsonObject(with:data) as? [String:Any], parsed["case"] as? String == key {
                        document=parsed
                        if parsed["complete"] as? Bool == true || parsed["error"] != nil { break }
                    }
                    try? await Task.sleep(nanoseconds:100_000_000)
                }
                if document["complete"] as? Bool != true {
                    report["failedCase"]=key; report["lastDocument"]=document; save("report.json"); return
                }
                let native=await cookies(store)
                let actual=store.identifier.flatMap { id in identifiers.first(where:{$0.value==id})?.key } ?? (store === stores["h"]! ? "h" : "unknown")
                var sample=c
                sample["document"]=document; sample["policyAllows"]=allow; sample["policyBeforeLoad"]=true
                sample["actualPartition"]=actual; sample["store"]=store.identifier?.uuidString ?? "default"
                sample["nativeCookieValues"]=native.map {$0["value"]!}; sample["nativeCookies"]=native
                sample["loadErrors"]=errors[ObjectIdentifier(web)] ?? []; sample["nativeUrl"]=web.url?.absoluteString ?? ""
                samples.append(sample); save("progress.json")
            }
            report["complete"]=true
        } catch { report["error"]=String(describing:error) }
        save("report.json")
    }
}

@main @MainActor final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window:UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?=nil) -> Bool {
        let args=ProcessInfo.processInfo.arguments
        func value(_ key:String) -> String { args[args.firstIndex(of:key)!+1] }
        let window=UIWindow(frame:UIScreen.main.bounds)
        window.rootViewController=Controller(run:value("--run"),base:value("--base")); self.window=window; window.makeKeyAndVisible(); return true
    }
}
