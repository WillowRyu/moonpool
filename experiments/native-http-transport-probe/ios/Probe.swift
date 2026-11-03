import UIKit

final class Exchange {
    var response:HTTPURLResponse?,data=Data(),error:Error?,done=false,redirects=0,challenges=0
    var disposition=URLSession.AuthChallengeDisposition.rejectProtectionSpace
    var finished:(()->Void)?
}

/// Configured as a broker would need: no ambient cookies, credentials, cache or automatic redirects.
/// Every delegate call runs on the main queue. Server trust is pinned to the probe's own CA, so nothing
/// is added to the device's trust store and ordinary validation stays on.
final class Client:NSObject,URLSessionDataDelegate {
    let anchor:SecCertificate
    var exchanges:[Int:Exchange]=[:]
    var session:URLSession!
    init(anchor:SecCertificate){
        self.anchor=anchor;super.init()
        session=URLSession(configuration:Client.configuration(),delegate:self,delegateQueue:.main)
    }
    static func configuration()->URLSessionConfiguration {
        let c=URLSessionConfiguration.ephemeral
        c.httpCookieStorage=nil;c.httpCookieAcceptPolicy = .never;c.httpShouldSetCookies=false
        c.urlCache=nil;c.urlCredentialStorage=nil;c.requestCachePolicy = .reloadIgnoringLocalCacheData
        c.timeoutIntervalForRequest=20
        return c
    }
    func urlSession(_ session:URLSession,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        guard challenge.protectionSpace.authenticationMethod==NSURLAuthenticationMethodServerTrust,let trust=challenge.protectionSpace.serverTrust else {completionHandler(.performDefaultHandling,nil);return}
        SecTrustSetAnchorCertificates(trust,[anchor] as CFArray);SecTrustSetAnchorCertificatesOnly(trust,true)
        var failure:CFError?
        if SecTrustEvaluateWithError(trust,&failure){completionHandler(.useCredential,URLCredential(trust:trust))}else{completionHandler(.cancelAuthenticationChallenge,nil)}
    }
    func urlSession(_ session:URLSession,task:URLSessionTask,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        let exchange=exchanges[task.taskIdentifier];exchange?.challenges+=1
        completionHandler(exchange?.disposition ?? .rejectProtectionSpace,nil)
    }
    func urlSession(_ session:URLSession,task:URLSessionTask,willPerformHTTPRedirection response:HTTPURLResponse,newRequest request:URLRequest,completionHandler:@escaping(URLRequest?)->Void){
        exchanges[task.taskIdentifier]?.redirects+=1;completionHandler(nil)
    }
    func urlSession(_ session:URLSession,dataTask:URLSessionDataTask,didReceive response:URLResponse,completionHandler:@escaping(URLSession.ResponseDisposition)->Void){
        exchanges[dataTask.taskIdentifier]?.response=response as? HTTPURLResponse;completionHandler(.allow)
    }
    func urlSession(_ session:URLSession,dataTask:URLSessionDataTask,didReceive data:Data){exchanges[dataTask.taskIdentifier]?.data.append(data)}
    func urlSession(_ session:URLSession,task:URLSessionTask,didCompleteWithError error:Error?){
        guard let exchange=exchanges[task.taskIdentifier] else {return}
        exchange.error=error;exchange.done=true;exchange.finished?();exchange.finished=nil
    }
    func start(_ request:URLRequest,disposition:String?=nil)->Exchange {
        let task=session.dataTask(with:request),exchange=Exchange()
        if disposition=="default" {exchange.disposition = .performDefaultHandling}
        if disposition=="cancel" {exchange.disposition = .cancelAuthenticationChallenge}
        if disposition=="use-nil" {exchange.disposition = .useCredential}
        exchanges[task.taskIdentifier]=exchange;task.resume();return exchange
    }
    func finish(_ exchange:Exchange) async {
        if exchange.done {return}
        await withCheckedContinuation{continuation in exchange.finished={continuation.resume()}}
    }
}

@MainActor final class Controller:UIViewController {
    let run:String,port:String,control:String
    var report:[String:Any]=[:],observations:[[String:Any]]=[],errors:[[String:Any]]=[]
    var client:Client!
    init(run:String,port:String,control:String){self.run=run;self.port=port;self.control=control;super.init(nibName:nil,bundle:nil)}
    required init?(coder:NSCoder){fatalError()}
    var fixtures:URL {Bundle.main.bundleURL.appendingPathComponent("Fixtures")}
    func save(_ name:String){report["observations"]=observations;report["errors"]=errors;if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]){try? data.write(to:FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent(name),options:.atomic)}}
    func sleep(_ seconds:Double) async {try? await Task.sleep(nanoseconds:UInt64(seconds*1_000_000_000))}
    func request(_ c:[String:Any])->URLRequest {
        let name=c["requestCase"] as? String ?? c["id"] as! String
        var request=URLRequest(url:URL(string:"https://localhost:\(port)\(c["path"] as! String)?run=\(run)&case=\(name)")!)
        request.httpMethod=c["method"] as? String ?? "GET"
        if let body=c["body"] as? String {request.httpBody=Data(body.utf8)}
        if let cookie=c["attachCookie"] as? String {request.setValue(cookie,forHTTPHeaderField:"Cookie")}
        return request
    }
    func ask(_ path:String,_ c:[String:Any]) async -> [String:Any] {
        let exchange=client.start(URLRequest(url:URL(string:"https://localhost:\(control)\(path)?run=\(run)&case=\(c["id"] as! String)")!))
        await client.finish(exchange)
        return (try? JSONSerialization.jsonObject(with:exchange.data)) as? [String:Any] ?? [:]
    }
    func observe(_ c:[String:Any],_ exchange:Exchange)->[String:Any] {
        var item:[String:Any]=["case":c["id"]!,"status":exchange.response?.statusCode ?? NSNull(),"redirectCallbacks":exchange.redirects,"challengeCallbacks":exchange.challenges,"setCookieFields":NSNull(),
                               "bodyText":exchange.response==nil ? NSNull():String(decoding:exchange.data,as:UTF8.self)]
        if let error=exchange.error as NSError? {item["error"]="\(error.domain):\(error.code)"} else {item["error"]=NSNull()}
        guard let response=exchange.response else {item["setCookieFolded"]=NSNull();item["location"]=NSNull();return item}
        item["setCookieFolded"]=response.value(forHTTPHeaderField:"Set-Cookie") ?? NSNull()
        item["location"]=response.value(forHTTPHeaderField:"Location") ?? NSNull()
        item["headerNames"]=response.allHeaderFields.keys.map{"\($0)"}.sorted()
        // Diagnostic only: what the platform's own parser makes of the same response.
        let headers=Dictionary(uniqueKeysWithValues:response.allHeaderFields.map{("\($0.key)","\($0.value)")})
        item["platformParsed"]=HTTPCookie.cookies(withResponseHeaderFields:headers,for:response.url!).map{cookie in
            ["name":cookie.name,"value":cookie.value,"path":cookie.path,"domain":cookie.domain,"httpOnly":cookie.isHTTPOnly,"secure":cookie.isSecure,"session":cookie.isSessionOnly,"sameSite":cookie.sameSitePolicy?.rawValue ?? NSNull()] as [String:Any]
        }
        return item
    }
    func perform(_ c:[String:Any]) async -> [String:Any] {
        switch c["kind"] as? String {
        case "hold-headers":
            let exchange=client.start(request(c))
            for _ in 0..<50 {
                if (await ask("/held",c))["held"] as? Bool==true {break}
                await sleep(0.1)
            }
            await sleep(0.3)
            let responded=exchange.response != nil
            _=await ask("/release",c)
            await client.finish(exchange)
            var item=observe(c,exchange);item["respondedBeforeRelease"]=responded;return item
        case "hold-body":
            let exchange=client.start(request(c))
            for _ in 0..<30 where exchange.response==nil {await sleep(0.1)}
            await sleep(0.3)
            let headers=exchange.response != nil,body = !exchange.data.isEmpty || exchange.done
            _=await ask("/release",c)
            await client.finish(exchange)
            var item=observe(c,exchange);item["headersBeforeRelease"]=headers;item["bodyBeforeRelease"]=body;return item
        case "tls-negative":
            // No delegate: default validation with the device's own roots must refuse the probe's certificate.
            let plain=URLSession(configuration:Client.configuration())
            do {
                let (_,response)=try await plain.data(for:request(c))
                return ["case":c["id"]!,"status":(response as? HTTPURLResponse)?.statusCode ?? NSNull(),"error":NSNull(),"location":NSNull(),"bodyText":NSNull(),"setCookieFields":NSNull(),"setCookieFolded":NSNull()]
            } catch {
                let e=error as NSError
                return ["case":c["id"]!,"status":NSNull(),"error":"\(e.domain):\(e.code)","location":NSNull(),"bodyText":NSNull(),"setCookieFields":NSNull(),"setCookieFolded":NSNull()]
            }
        default:
            let exchange=client.start(request(c),disposition:c["challengeDisposition"] as? String)
            await client.finish(exchange)
            return observe(c,exchange)
        }
    }
    override func viewDidLoad(){super.viewDidLoad();Task{await execute()}}
    func execute() async {
        report=["platform":"ios","run":run,"release":UIDevice.current.systemVersion,"complete":false]
        do {
            let der=try Data(contentsOf:fixtures.appendingPathComponent("ca.der"))
            client=Client(anchor:SecCertificateCreateWithData(nil,der as CFData)!)
            let cases=try JSONSerialization.jsonObject(with:Data(contentsOf:fixtures.appendingPathComponent("cases.json"))) as! [[String:Any]]
            for c in cases {observations.append(await perform(c));save("progress.json")}
            report["sharedCookieStorageCount"]=HTTPCookieStorage.shared.cookies?.count ?? 0
            report["complete"]=true
        }catch{errors.append(["error":String(describing:error)])}
        save("report.json")
    }
}

@main @MainActor final class AppDelegate:UIResponder,UIApplicationDelegate {
    var window:UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?=nil)->Bool {
        let args=ProcessInfo.processInfo.arguments
        func value(_ key:String)->String{args[args.firstIndex(of:key)!+1]}
        let window=UIWindow(frame:UIScreen.main.bounds);window.rootViewController=Controller(run:value("--run"),port:value("--port"),control:value("--control"));self.window=window;window.makeKeyAndVisible();return true
    }
}
