import UIKit
import WebKit

@MainActor final class Scheme:NSObject,WKURLSchemeHandler {
    var onGuest:((String)->Void)?
    func webView(_ webView:WKWebView,start task:WKURLSchemeTask) {
        let url=task.request.url!,data:Data
        if url.path=="/prepare" { data=try! Data(contentsOf:Bundle.main.bundleURL.appendingPathComponent("Fixtures/storage.html")) }
        else if url.path=="/guest" { onGuest?(url.absoluteString);data=Data("<!doctype html><script>window.guestReady=new URLSearchParams(location.search).get('token');</script>".utf8) }
        else { data=Data("Unmapped research resource".utf8) }
        task.didReceive(URLResponse(url:url,mimeType:"text/html",expectedContentLength:data.count,textEncodingName:"utf-8"));task.didReceive(data);task.didFinish()
    }
    func webView(_ webView:WKWebView,stop task:WKURLSchemeTask) { }
}

@MainActor final class Controller:UIViewController,WKNavigationDelegate {
    let run:String,base:String
    let stack=UIStackView()
    var report:[String:Any]=[:],samples:[[String:Any]]=[],errors:[[String:Any]]=[]
    var guestResources:[String]=[]
    var hostStore:WKWebsiteDataStore!
    init(run:String,base:String){self.run=run;self.base=base;super.init(nibName:nil,bundle:nil)}
    required init?(coder:NSCoder){fatalError()}
    var documents:URL {FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]}
    func save(_ name:String){report["samples"]=samples;report["errors"]=errors;report["guestResources"]=guestResources;if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]){try? data.write(to:documents.appendingPathComponent(name),options:.atomic)}}
    func webView(_ webView:WKWebView,didFailProvisionalNavigation navigation:WKNavigation!,withError error:Error){failed(error)}
    func webView(_ webView:WKWebView,didFail navigation:WKNavigation!,withError error:Error){failed(error)}
    func failed(_ error:Error){let e=error as NSError;errors.append(["domain":e.domain,"code":e.code])}
    func make(_ store:WKWebsiteDataStore)->WKWebView {
        let c=WKWebViewConfiguration();c.websiteDataStore=store;let scheme=Scheme();scheme.onGuest={ [weak self] url in self?.guestResources.append(url) };c.setURLSchemeHandler(scheme,forURLScheme:"moonpool")
        let web=WKWebView(frame:.zero,configuration:c);web.navigationDelegate=self;stack.addArrangedSubview(web);return web
    }
    func discard(_ web:WKWebView){web.stopLoading();web.navigationDelegate=nil;stack.removeArrangedSubview(web);web.removeFromSuperview()}
    func policy(_ store:WKWebsiteDataStore,_ allow:Bool) async {
        await withCheckedContinuation { continuation in store.httpCookieStore.setCookiePolicy(allow ? .allow:.disallow){continuation.resume()} }
    }
    func allows(_ store:WKWebsiteDataStore) async -> Bool {
        await withCheckedContinuation { continuation in store.httpCookieStore.getCookiePolicy{continuation.resume(returning:$0 == .allow)} }
    }
    func inventory(_ store:WKWebsiteDataStore) async -> [HTTPCookie] {
        await withCheckedContinuation { continuation in store.httpCookieStore.getAllCookies{continuation.resume(returning:$0)} }
    }
    func snapshot(_ cookies:[HTTPCookie])->[[String:Any]] {
        cookies.sorted{$0.name<$1.name}.map{["name":$0.name,"value":$0.value,"domain":$0.domain,"path":$0.path,"httpOnly":$0.isHTTPOnly,"secure":$0.isSecure,"propertyKeys":($0.properties ?? [:]).keys.map(\.rawValue).sorted()]}
    }
    func quoted(_ text:String)->String {String(data:try! JSONEncoder().encode(text),encoding:.utf8)!}
    func poll(_ web:WKWebView,_ expression:String) async throws -> Any {
        for _ in 0..<120 {
            if let value=try? await web.evaluateJavaScript(expression),let text=value as? String,let data=text.data(using:.utf8),
               let parsed=try? JSONSerialization.jsonObject(with:data,options:[.fragmentsAllowed]),!(parsed is NSNull){return parsed}
            try? await Task.sleep(nanoseconds:100_000_000)
        }
        throw NSError(domain:"FixtureObservationDeadline",code:1)
    }
    func network(_ web:WKWebView,_ url:String) async throws {
        web.load(URLRequest(url:URL(string:url)!,cachePolicy:.reloadIgnoringLocalCacheData))
        _=try await poll(web,"JSON.stringify(window.networkReady === \(quoted(url)) ? {ready:true} : null)")
    }
    func prepare(_ web:WKWebView,_ origin:String,_ token:String,_ seed:Bool) async throws {
        web.load(URLRequest(url:URL(string:origin+"/prepare?token="+token+"&seed="+(seed ? "1":"0"))!))
        _=try await poll(web,"JSON.stringify(window.storageReady || null)")
    }
    func readData(_ web:WKWebView) async throws -> Any {
        _=try await web.evaluateJavaScript("window.afterRead=null;window.readPublicData().then(v=>window.afterRead=v);true")
        return try await poll(web,"JSON.stringify(window.afterRead || null)")
    }
    override func viewDidLoad(){super.viewDidLoad();stack.axis = .vertical;stack.distribution = .fillEqually;stack.frame=view.bounds;stack.autoresizingMask=[.flexibleWidth,.flexibleHeight];view.addSubview(stack);Task{await execute()}}
    func execute() async {
        report=["platform":"ios","run":run,"base":base,"os":UIDevice.current.systemVersion,"complete":false,"gateCases":GateCases.runAll()]
        // No cold store enumeration; this initializes WebKit without guest content.
        let initConfig=WKWebViewConfiguration();initConfig.websiteDataStore = .nonPersistent()
        let initializer=WKWebView(frame:.zero,configuration:initConfig)
        withExtendedLifetime(initializer){}
        hostStore = .default()
        do {
            let config=try JSONSerialization.jsonObject(with:Data(contentsOf:Bundle.main.bundleURL.appendingPathComponent("Fixtures/config.json"))) as! [String:Any]
            let cases=config["cases"] as! [[String:Any]],ids=config["ids"] as! [String:String]
            await policy(hostStore,true);let host=make(hostStore)
            try await network(host,base+"/seed?run="+run+"&case=host")
            for c in cases {
                let key=c["id"] as! String,token=run+"-"+key,identifier=UUID()
                let store=WKWebsiteDataStore(forIdentifier:identifier),origin="moonpool://"+ids[key]!
                await policy(store,true)
                let observer=make(store),net=make(store),service=base.replacingOccurrences(of:"localhost",with:c["host"] as! String)
                let query="?run="+run+"&case="+key
                try await prepare(observer,origin,token,true)
                try await network(net,service+"/seed"+query)
                try await network(net,service+(key=="offpath" ? "/hidden/echo":"/echo")+query)
                try await network(net,base+"/visible"+query)
                let visible=try await net.evaluateJavaScript("document.cookie") as? String ?? ""
                await policy(store,false)
                try await phase(key,"initial",store,observer,origin,token,visible)
                discard(observer);discard(net)
                let reopened=WKWebsiteDataStore(forIdentifier:identifier),read=make(reopened)
                try await prepare(read,origin,token,false)
                try await phase(key,"reopened",reopened,read,origin,token,visible)
                discard(read)
            }
            discard(host);report["complete"]=true
        }catch{report["error"]=String(describing:error)}
        save("report.json")
    }
    func phase(_ key:String,_ phase:String,_ store:WKWebsiteDataStore,_ observer:WKWebView,_ origin:String,_ token:String,_ visible:String) async throws {
        let before=await inventory(store),candidate=make(store)
        var loads=0,present=false
        var gate:AdmissionGate!
        let decision:String=await withCheckedContinuation { continuation in
            gate=AdmissionGate { _,done in Task { @MainActor in
                present = !(await self.inventory(store)).isEmpty
                let allow=await self.allows(store)
                done(allow ? .unknown : (present ? .present:.empty))
            } }
            gate.admit(token,load:{loads+=1;candidate.load(URLRequest(url:URL(string:origin+"/guest?token="+token)!));continuation.resume(returning:"admitted")},
                       retire:{self.discard(candidate);if loads==0{continuation.resume(returning:"refused")}})
        }
        let marker:Any=decision=="admitted" ? try await poll(candidate,"JSON.stringify(window.guestReady || null)"):NSNull()
        let data=try await readData(observer),after=await inventory(store),hostCookies=await inventory(hostStore)
        samples.append(["case":key,"phase":phase,"partition":store.identifier!.uuidString,"presence":present,"policyAllows":await allows(store),
                        "beforeNames":before.map(\.name).sorted(),"afterNames":after.map(\.name).sorted(),"beforeCookies":snapshot(before),"afterCookies":snapshot(after),
                        "storage":data,"expectedStorage":token,"decision":decision,"loadCalls":loads,"guestMarker":marker,"visibleJsCookie":visible,
                        "hostPolicyAllows":await allows(hostStore),"hostCookiePresent":hostCookies.contains{$0.name=="t28a_host" && $0.value=="public_host"},
                        "hostCookie":hostCookies.map{$0.name+"="+$0.value}.sorted().joined(separator:"; ")])
        save("progress.json");gate.close()
    }
}

@main @MainActor final class AppDelegate:UIResponder,UIApplicationDelegate {
    var window:UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?=nil)->Bool {
        let args=ProcessInfo.processInfo.arguments
        func value(_ key:String)->String{args[args.firstIndex(of:key)!+1]}
        let window=UIWindow(frame:UIScreen.main.bounds);window.rootViewController=Controller(run:value("--run"),base:value("--base"));self.window=window;window.makeKeyAndVisible();return true
    }
}
