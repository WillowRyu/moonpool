import UIKit

final class Exchange {
    var challenges:[[String:Any]]=[],responses:[[String:Any]]=[],data=Data(),status:Int?,error:String?,done=false
    var finished:(()->Void)?
}

/// The research broker's session: no ambient cookies, credentials, cache or redirects. Every delegate call runs on the main queue.
/// Server trust is pinned to the probe's own CA, so nothing is added to the device's trust store.
final class Client:NSObject,URLSessionDataDelegate {
    let anchor:SecCertificate
    var exchanges:[Int:Exchange]=[:],dispositions:[Int:URLSession.AuthChallengeDisposition]=[:]
    var session:URLSession!
    init(anchor:SecCertificate){
        self.anchor=anchor;super.init()
        let c=URLSessionConfiguration.ephemeral
        c.httpCookieStorage=nil;c.httpCookieAcceptPolicy = .never;c.httpShouldSetCookies=false
        c.urlCache=nil;c.urlCredentialStorage=nil;c.requestCachePolicy = .reloadIgnoringLocalCacheData
        c.timeoutIntervalForRequest=40
        session=URLSession(configuration:c,delegate:self,delegateQueue:.main)
    }
    func urlSession(_ session:URLSession,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        guard challenge.protectionSpace.authenticationMethod==NSURLAuthenticationMethodServerTrust,let trust=challenge.protectionSpace.serverTrust else {completionHandler(.performDefaultHandling,nil);return}
        SecTrustSetAnchorCertificates(trust,[anchor] as CFArray);SecTrustSetAnchorCertificatesOnly(trust,true)
        var failure:CFError?
        if SecTrustEvaluateWithError(trust,&failure){completionHandler(.useCredential,URLCredential(trust:trust))}else{completionHandler(.cancelAuthenticationChallenge,nil)}
    }
    /// The question this probe asks: what does the challenge show of the response that caused it?
    func urlSession(_ session:URLSession,task:URLSessionTask,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        let http=challenge.failureResponse as? HTTPURLResponse
        exchanges[task.taskIdentifier]?.challenges.append([
            "method":challenge.protectionSpace.authenticationMethod,"previousFailureCount":challenge.previousFailureCount,
            "hasFailureResponse":challenge.failureResponse != nil,"status":http?.statusCode ?? NSNull(),
            "setCookie":http?.value(forHTTPHeaderField:"Set-Cookie") ?? NSNull(),
        ])
        completionHandler(dispositions[task.taskIdentifier] ?? .rejectProtectionSpace,nil)
    }
    func urlSession(_ session:URLSession,task:URLSessionTask,willPerformHTTPRedirection response:HTTPURLResponse,newRequest request:URLRequest,completionHandler:@escaping(URLRequest?)->Void){
        completionHandler(nil)
    }
    func urlSession(_ session:URLSession,dataTask:URLSessionDataTask,didReceive response:URLResponse,completionHandler:@escaping(URLSession.ResponseDisposition)->Void){
        if let exchange=exchanges[dataTask.taskIdentifier],let http=response as? HTTPURLResponse {
            exchange.status=http.statusCode;exchange.data=Data()
            exchange.responses.append(["status":http.statusCode,"setCookie":http.value(forHTTPHeaderField:"Set-Cookie") ?? NSNull()])
        }
        completionHandler(.allow)
    }
    func urlSession(_ session:URLSession,dataTask:URLSessionDataTask,didReceive data:Data){exchanges[dataTask.taskIdentifier]?.data.append(data)}
    func urlSession(_ session:URLSession,task:URLSessionTask,didCompleteWithError error:Error?){
        guard let exchange=exchanges[task.taskIdentifier] else {return}
        exchange.error=error.map{String(describing:$0)};exchange.done=true;exchange.finished?();exchange.finished=nil
    }
    func perform(_ request:URLRequest,disposition:URLSession.AuthChallengeDisposition) async -> Exchange {
        let task=session.dataTask(with:request),exchange=Exchange()
        exchanges[task.taskIdentifier]=exchange;dispositions[task.taskIdentifier]=disposition
        await withCheckedContinuation{(continuation:CheckedContinuation<Void,Never>) in
            exchange.finished={continuation.resume()}
            task.resume()
        }
        return exchange
    }
}

@MainActor final class Controller:UIViewController {
    let run:String,port:String
    init(run:String,port:String){self.run=run;self.port=port;super.init(nibName:nil,bundle:nil)}
    required init?(coder:NSCoder){fatalError()}
    override func viewDidLoad(){super.viewDidLoad();Task{await execute()}}
    func execute() async {
        var observations:[[String:Any]]=[],errors:[[String:Any]]=[],complete=false
        do {
            let fixtures=Bundle.main.bundleURL.appendingPathComponent("Fixtures")
            let anchor=SecCertificateCreateWithData(nil,try Data(contentsOf:fixtures.appendingPathComponent("ca.der")) as CFData)!
            let client=Client(anchor:anchor)
            let cases=try JSONSerialization.jsonObject(with:Data(contentsOf:fixtures.appendingPathComponent("cases.json"))) as! [[String:Any]]
            for c in cases {
                let id=c["id"] as! String
                var request=URLRequest(url:URL(string:"https://localhost:\(port)/s?run=\(run)&case=\(id)")!)
                request.httpMethod=c["method"] as? String ?? "GET"
                if let body=c["body"] as? String {request.httpBody=Data(body.utf8)}
                for (name,value) in c["headers"] as? [String:String] ?? [:] {request.setValue(value,forHTTPHeaderField:name)}
                let exchange=await client.perform(request,disposition:c["disposition"] as? String=="default" ? .performDefaultHandling:.rejectProtectionSpace)
                observations.append(["case":id,"challenges":exchange.challenges,"responses":exchange.responses,"status":exchange.status ?? NSNull(),"error":exchange.error ?? NSNull(),"bodyText":String(decoding:exchange.data,as:UTF8.self)])
            }
            complete=true
        } catch {errors.append(["error":String(describing:error)])}
        let report:[String:Any]=["platform":"ios","run":run,"release":UIDevice.current.systemVersion,"complete":complete,"errors":errors,"observations":observations]
        if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]) {
            try? data.write(to:FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("report.json"),options:.atomic)
        }
    }
}

@main @MainActor final class AppDelegate:UIResponder,UIApplicationDelegate {
    var window:UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?=nil)->Bool {
        let args=ProcessInfo.processInfo.arguments
        func value(_ key:String)->String {args[args.firstIndex(of:key)!+1]}
        let window=UIWindow(frame:UIScreen.main.bounds);window.rootViewController=Controller(run:value("--run"),port:value("--port"));self.window=window;window.makeKeyAndVisible();return true
    }
}
