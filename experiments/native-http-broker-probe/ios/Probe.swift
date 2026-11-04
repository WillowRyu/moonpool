import UIKit

final class Exchange {
    var response:HTTPURLResponse?,data=Data(),error:Error?,done=false
    var headersDelivered:((HTTPURLResponse)->Void)?
    var finished:(()->Void)?
}

/// No ambient cookies, credentials, cache or automatic redirects. Every delegate call runs on the main queue.
/// Server trust is pinned to the probe's own CA, so nothing is added to the device's trust store.
final class Client:NSObject,URLSessionDataDelegate {
    let anchor:SecCertificate
    var exchanges:[Int:Exchange]=[:]
    var session:URLSession!
    let answersChallenges:Bool
    init(anchor:SecCertificate,configuration:URLSessionConfiguration,answersChallenges:Bool){
        self.anchor=anchor;self.answersChallenges=answersChallenges;super.init()
        session=URLSession(configuration:configuration,delegate:self,delegateQueue:.main)
    }
    static func broker()->URLSessionConfiguration {
        let c=URLSessionConfiguration.ephemeral
        c.httpCookieStorage=nil;c.httpCookieAcceptPolicy = .never;c.httpShouldSetCookies=false
        c.urlCache=nil;c.urlCredentialStorage=nil;c.requestCachePolicy = .reloadIgnoringLocalCacheData
        c.timeoutIntervalForRequest=40
        return c
    }
    func urlSession(_ session:URLSession,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        guard challenge.protectionSpace.authenticationMethod==NSURLAuthenticationMethodServerTrust,let trust=challenge.protectionSpace.serverTrust else {completionHandler(.performDefaultHandling,nil);return}
        SecTrustSetAnchorCertificates(trust,[anchor] as CFArray);SecTrustSetAnchorCertificatesOnly(trust,true)
        var failure:CFError?
        if SecTrustEvaluateWithError(trust,&failure){completionHandler(.useCredential,URLCredential(trust:trust))}else{completionHandler(.cancelAuthenticationChallenge,nil)}
    }
    func urlSession(_ session:URLSession,task:URLSessionTask,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        completionHandler(answersChallenges ? .performDefaultHandling:.rejectProtectionSpace,nil)
    }
    func urlSession(_ session:URLSession,task:URLSessionTask,willPerformHTTPRedirection response:HTTPURLResponse,newRequest request:URLRequest,completionHandler:@escaping(URLRequest?)->Void){
        completionHandler(nil)
    }
    func urlSession(_ session:URLSession,dataTask:URLSessionDataTask,didReceive response:URLResponse,completionHandler:@escaping(URLSession.ResponseDisposition)->Void){
        if let exchange=exchanges[dataTask.taskIdentifier],let http=response as? HTTPURLResponse {exchange.response=http;exchange.data=Data();exchange.headersDelivered?(http)}
        completionHandler(.allow)
    }
    func urlSession(_ session:URLSession,dataTask:URLSessionDataTask,didReceive data:Data){exchanges[dataTask.taskIdentifier]?.data.append(data)}
    func urlSession(_ session:URLSession,task:URLSessionTask,didCompleteWithError error:Error?){
        guard let exchange=exchanges[task.taskIdentifier] else {return}
        exchange.error=error;exchange.done=true;exchange.finished?();exchange.finished=nil
    }
    func start(_ request:URLRequest,headers:((HTTPURLResponse)->Void)?=nil,finished:(()->Void)?=nil)->Exchange {
        let task=session.dataTask(with:request),exchange=Exchange()
        exchange.headersDelivered=headers;exchange.finished=finished
        exchanges[task.taskIdentifier]=exchange;task.resume();return exchange
    }
    func finish(_ exchange:Exchange) async {
        if exchange.done {return}
        await withCheckedContinuation{continuation in exchange.finished={continuation.resume()}}
    }
}

final class Cookie {
    var host="",path="/",name="",value="",httpOnly=false,created=0
}
final class Portal {
    let app:String,grants:Set<String>;var retired=false
    init(app:String,grants:Set<String>){self.app=app;self.grants=grants}
}
final class AppSession {var jar:[Cookie]=[],generation=0}
final class Pending {var outcome:[String:Any]?,start:(()->Void)?
    func settle(_ value:[String:Any]){outcome=value}
}
func denied(_ code:Any,_ reason:String?=nil)->[String:Any]{
    var found:[String:Any]=["ok":false,"code":code];if let reason {found["reason"]=reason};return found
}

/// Research broker: one in-memory jar per app, selected by a host-side portal binding. Not a public API, and its
/// cookie parser is only the small subset these cases need, because the C04 cookie profile is not frozen.
/// All jar work runs on the main queue, so mutations are serialized in delivery order.
final class Broker {
    static let requestFields:Set<String>=["url","method","credentials","headers","body"],cookieFields:Set<String>=["name","value","path","maxAge"]
    static let forbiddenHeaders:Set<String>=["cookie","cookie2","host","origin","proxy-authorization","content-length","transfer-encoding","connection","te","upgrade","keep-alive"]
    var portals:[String:Portal]=[:],apps:[String:AppSession]=[:],events:[[String:Any]]=[],sequence=0
    let approved:Set<String>,client:Client
    init(client:Client,approved:Set<String>){self.client=client;self.approved=approved}
    func bind(_ id:String,app:String,grants:Set<String>){portals[id]=Portal(app:app,grants:grants);if apps[app]==nil {apps[app]=AppSession()}}
    func event(_ kind:String,_ label:String){sequence+=1;events.append(["seq":sequence,"kind":kind,"label":label])}
    /// Pinned order: owner, then scope, then fields, then service. A missing scope beats malformed fields (SPEC 4.2).
    func admit(_ portal:Portal,_ scope:String)->[String:Any]? {
        if portal.retired {return denied("retired")}
        return portal.grants.contains(scope) ? nil:denied(-32000)
    }
    func secure(_ text:String)->URLComponents? {
        guard let url=URLComponents(string:text),url.scheme=="https",url.user==nil,url.password==nil,url.fragment==nil,url.host != nil else {return nil}
        return url
    }
    func isApproved(_ url:URLComponents)->Bool {approved.contains("\(url.host!.lowercased()):\(url.port ?? 443)")}
    func admitRequest(_ portal:Portal,_ params:[String:Any])->[String:Any]? {
        if let refused=admit(portal,"http") {return refused}
        if !Set(params.keys).isSubset(of:Broker.requestFields) {return denied(-32602)}
        let credentials=params["credentials"] as? String ?? "include"
        if credentials != "include"&&credentials != "omit" {return denied(-32602)}
        for name in (params["headers"] as? [String:String] ?? [:]).keys {
            let lower=name.lowercased()
            if Broker.forbiddenHeaders.contains(lower)||lower.hasPrefix("sec-")||lower.hasPrefix("proxy-") {return denied(-32602)}
        }
        guard let url=secure(params["url"] as! String) else {return denied(-32602)}
        return isApproved(url) ? nil:denied(-32000)
    }
    func request(_ portalId:String,_ label:String,_ params:[String:Any],deferred:Bool)->Pending {
        let pending=Pending(),portal=portals[portalId]!
        if let refused=admitRequest(portal,params) {pending.settle(refused);return pending}
        let session=apps[portal.app]!,generation=session.generation
        pending.start={[unowned self] in self.dispatch(portal,session,generation,label,params,pending)}
        if !deferred {pending.start!()}
        return pending
    }
    func finish(_ portal:Portal,_ pending:Pending,_ outcome:[String:Any]){pending.settle(portal.retired ? ["delivered":false]:outcome)}
    /// The owner and generation are rechecked here because queued work may start after a reset.
    func dispatch(_ portal:Portal,_ session:AppSession,_ generation:Int,_ label:String,_ params:[String:Any],_ pending:Pending){
        if session.generation != generation {finish(portal,pending,denied(-32007,"sessionReset"));return}
        let include=(params["credentials"] as? String ?? "include") != "omit",url=secure(params["url"] as! String)!
        var request=URLRequest(url:url.url!)
        request.httpMethod=params["method"] as? String ?? "GET"
        if let body=params["body"] as? String {request.httpBody=Data(body.utf8)}
        for (name,value) in params["headers"] as? [String:String] ?? [:] {request.setValue(value,forHTTPHeaderField:name)}
        if include {let cookie=cookieHeader(session,url);if !cookie.isEmpty {request.setValue(cookie,forHTTPHeaderField:"Cookie")}}
        var exchange:Exchange!
        var committed=false
        exchange=client.start(request,headers:{[unowned self] response in
            // A resend after a Basic challenge can deliver headers once per final response. Commit runs for what arrives.
            if committed {return}
            committed=true
            self.commit(session,generation,include,label,url,response)
        },finished:{[unowned self] in
            if session.generation != generation {self.finish(portal,pending,denied(-32007,"sessionReset"));return}
            guard exchange.error==nil,let response=exchange.response else {self.finish(portal,pending,denied(-32007,"network"));return}
            self.finish(portal,pending,["ok":true,"status":response.statusCode,"headers":Broker.projected(response),"bodyText":String(decoding:exchange.data,as:UTF8.self)])
        })
    }
    /// Runs when the client delivers response headers. A stale generation is fenced, not written.
    func commit(_ session:AppSession,_ generation:Int,_ include:Bool,_ label:String,_ url:URLComponents,_ response:HTTPURLResponse){
        event("headers",label)
        guard let folded=response.value(forHTTPHeaderField:"Set-Cookie"),include else {return}
        if session.generation != generation {event("fence",label);return}
        for line in Broker.splitFolded(folded) {store(session,line,url)}
        event("commit",label)
    }
    static func projected(_ response:HTTPURLResponse)->[String:String] {
        var headers:[String:String]=[:]
        for (name,value) in response.allHeaderFields {
            let lower="\(name)".lowercased()
            if lower != "set-cookie"&&lower != "set-cookie2" {headers[lower]="\(value)"}
        }
        return headers
    }
    /// The same rule as the Android adapter: split where a comma precedes a name=.
    static func splitFolded(_ value:String)->[String] {
        let pattern=try! NSRegularExpression(pattern:",\\s*(?=[^;,=\\s]+=)")
        var found:[String]=[],last=value.startIndex
        for match in pattern.matches(in:value,range:NSRange(value.startIndex...,in:value)) {
            let range=Range(match.range,in:value)!
            found.append(String(value[last..<range.lowerBound]));last=range.upperBound
        }
        found.append(String(value[last...]))
        return found
    }
    static func pathMatches(_ request:String,_ cookie:String)->Bool {
        if request==cookie {return true}
        guard request.hasPrefix(cookie) else {return false}
        return cookie.hasSuffix("/")||request.dropFirst(cookie.count).first=="/"
    }
    static func defaultPath(_ path:String)->String {
        guard let last=path.lastIndex(of:"/"),last != path.startIndex else {return "/"}
        return String(path[..<last])
    }
    func store(_ session:AppSession,_ line:String,_ url:URLComponents){
        let parts=line.components(separatedBy:";")
        guard let equals=parts[0].firstIndex(of:"="),equals != parts[0].startIndex else {return}
        let cookie=Cookie()
        cookie.name=parts[0][..<equals].trimmingCharacters(in:.whitespaces)
        cookie.value=parts[0][parts[0].index(after:equals)...].trimmingCharacters(in:.whitespaces)
        cookie.host=url.host!.lowercased();cookie.path=Broker.defaultPath(url.path)
        var isSecure=false,sameSiteNone=false,maxAge:Int?=nil
        for part in parts.dropFirst() {
            let pieces=part.split(separator:"=",maxSplits:1,omittingEmptySubsequences:false)
            let key=pieces[0].trimmingCharacters(in:.whitespaces).lowercased(),value=pieces.count>1 ? pieces[1].trimmingCharacters(in:.whitespaces):""
            switch key {
            case "path": if value.hasPrefix("/") {cookie.path=value}
            case "domain": if value.lowercased() != cookie.host {return}
            case "secure": isSecure=true
            case "httponly": cookie.httpOnly=true
            case "samesite": sameSiteNone=value.lowercased()=="none"
            case "max-age": maxAge=Int(value) ?? maxAge
            default: break
            }
        }
        if sameSiteNone&&(!isSecure) {return}
        put(session,cookie,delete:(maxAge ?? 1)<=0)
    }
    func put(_ session:AppSession,_ cookie:Cookie,delete:Bool){
        let existing=find(session,cookie.host,cookie.path,cookie.name)
        if let existing {cookie.created=existing.created} else {sequence+=1;cookie.created=sequence}
        session.jar.removeAll{$0===existing}
        if !delete {session.jar.append(cookie)}
    }
    func find(_ session:AppSession,_ host:String,_ path:String,_ name:String)->Cookie? {
        session.jar.first{$0.host==host&&$0.path==path&&$0.name==name}
    }
    func matching(_ session:AppSession,_ url:URLComponents)->[Cookie] {
        let host=url.host!.lowercased(),path=url.path.isEmpty ? "/":url.path
        return session.jar.filter{$0.host==host&&Broker.pathMatches(path,$0.path)}.sorted{a,b in
            a.path.count != b.path.count ? a.path.count>b.path.count:a.created<b.created
        }
    }
    func cookieHeader(_ session:AppSession,_ url:URLComponents)->String {
        matching(session,url).map{"\($0.name)=\($0.value)"}.joined(separator:"; ")
    }
    func cookieTarget(_ portal:Portal,_ text:String)->(URLComponents?,[String:Any]?) {
        if let refused=admit(portal,"cookies") {return (nil,refused)}
        guard let url=secure(text) else {return (nil,denied(-32602))}
        return isApproved(url) ? (url,nil):(nil,denied(-32000))
    }
    func cookiesGet(_ portalId:String,_ text:String)->[String:Any] {
        let portal=portals[portalId]!,(found,refused)=cookieTarget(portal,text)
        guard let url=found else {return refused!}
        let readable:[[String:Any]]=matching(apps[portal.app]!,url).filter{!$0.httpOnly}.map{["name":$0.name,"path":$0.path,"value":$0.value]}
        return ["ok":true,"cookies":readable]
    }
    func cookiesSet(_ portalId:String,_ text:String,_ fields:[String:Any])->[String:Any] {
        let portal=portals[portalId]!
        if let refused=admit(portal,"cookies") {return refused}
        if !Set(fields.keys).isSubset(of:Broker.cookieFields) {return denied(-32602)}
        let (found,refused)=cookieTarget(portal,text)
        guard let url=found else {return refused!}
        let session=apps[portal.app]!,host=url.host!.lowercased(),path=fields["path"] as? String ?? "/",name=fields["name"] as! String
        if find(session,host,path,name)?.httpOnly==true {return denied(-32000)}
        let cookie=Cookie();cookie.host=host;cookie.path=path;cookie.name=name;cookie.value=fields["value"] as! String
        put(session,cookie,delete:(fields["maxAge"] as? Int ?? 1)<=0)
        return ["ok":true]
    }
    func cookiesDelete(_ portalId:String,_ text:String,_ fields:[String:Any])->[String:Any] {
        let portal=portals[portalId]!,(found,refused)=cookieTarget(portal,text)
        guard let url=found else {return refused!}
        let session=apps[portal.app]!,existing=find(session,url.host!.lowercased(),fields["path"] as? String ?? "/",fields["name"] as! String)
        if existing?.httpOnly==true {return denied(-32000)}
        session.jar.removeAll{$0===existing}
        return ["ok":true]
    }
    /// Advances the generation first, so no in-flight response can write after this returns.
    func reset(_ portalId:String)->[String:Any] {
        let portal=portals[portalId]!
        if let refused=admit(portal,"http") {return refused}
        let session=apps[portal.app]!
        session.generation+=1;session.jar.removeAll();event("reset",portalId)
        return ["ok":true]
    }
    /// Harness evidence only. Nothing the guest can reach calls this.
    func snapshot(_ app:String)->[String] {(apps[app]?.jar ?? []).map{"\($0.name)=\($0.value)"}.sorted()}
    func hasEvent(_ kind:String,_ label:String)->Bool {events.contains{$0["kind"] as? String==kind&&$0["label"] as? String==label}}
}

@MainActor final class Controller:UIViewController {
    let run:String,port:String,second:String,control:String
    var report:[String:Any]=[:],observations:[[String:Any]]=[],errors:[[String:Any]]=[]
    var brokerClient:Client!,harness:Client!,hostClient:Client!
    var hostCredentialSpace:URLProtectionSpace?,hostCredential:URLCredential?
    let barrierSeconds=40.0
    init(run:String,port:String,second:String,control:String){self.run=run;self.port=port;self.second=second;self.control=control;super.init(nibName:nil,bundle:nil)}
    required init?(coder:NSCoder){fatalError()}
    var fixtures:URL {Bundle.main.bundleURL.appendingPathComponent("Fixtures")}
    func save(_ name:String){report["observations"]=observations;report["errors"]=errors;if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]){try? data.write(to:FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent(name),options:.atomic)}}
    func sleep(_ seconds:Double) async {try? await Task.sleep(nanoseconds:UInt64(seconds*1_000_000_000))}
    func listenerPort(_ name:String?)->String {name=="service2" ? second:port}
    func url(_ c:[String:Any],_ label:String,_ target:[String:Any]?=nil)->String {
        let t=target ?? [:]
        let userinfo=(t["userinfo"] as? String).map{$0+"@"} ?? "",fragment=(t["fragment"] as? String).map{"#"+$0} ?? ""
        return "\(t["scheme"] as? String ?? "https")://\(userinfo)\(t["host"] as? String ?? "localhost"):\(listenerPort(t["listener"] as? String))\(t["path"] as? String ?? "/s")?run=\(run)&case=\(c["id"] as! String)&step=\(label)\(fragment)"
    }
    func held(_ c:[String:Any],_ label:String,_ path:String) async -> Bool {
        let exchange=harness.start(URLRequest(url:URL(string:"https://localhost:\(control)\(path)?run=\(run)&case=\(c["id"] as! String)&step=\(label)")!))
        await harness.finish(exchange)
        return ((try? JSONSerialization.jsonObject(with:exchange.data)) as? [String:Any])?["held"] as? Bool ?? false
    }
    func until(_ check:() async -> Bool) async -> Bool {
        let deadline=Date().addingTimeInterval(barrierSeconds)
        while Date()<deadline {
            if await check() {return true}
            await sleep(0.05)
        }
        return false
    }
    func perform(_ c:[String:Any]) async -> [String:Any] {
        var steps:[[String:Any]]=[],timedOut:[String]=[],pending:[String:Pending]=[:]
        var approved:Set<String>=[]
        if let declared=c["approved"] as? [[String:String]] {for entry in declared {approved.insert("\(entry["host"]!):\(listenerPort(entry["listener"]))")}} else {approved.insert("localhost:\(port)")}
        let broker=Broker(client:brokerClient,approved:approved)
        for (id,value) in c["portals"] as! [String:[String:Any]] {broker.bind(id,app:value["app"] as! String,grants:Set(value["grants"] as! [String]))}
        func settle(_ label:String) async {
            let found=pending[label]!
            if !(await until{found.outcome != nil}) {timedOut.append("await:\(label)");return}
            steps.append(["label":label,"op":"request","outcome":found.outcome!])
        }
        for s in c["steps"] as! [[String:Any]] {
            let op=s["op"] as! String,label=s["label"] as! String,portal=s["portal"] as? String ?? "A1"
            switch op {
            case "request":
                var params=s["params"] as? [String:Any] ?? [:]
                let target=params.removeValue(forKey:"target") as? [String:Any],deferred=params.removeValue(forKey:"deferred") as? Bool ?? false
                params["url"]=url(c,label,target)
                pending[label]=broker.request(portal,label,params,deferred:deferred)
                if s["wait"] as? Bool != false {await settle(label)}
            case "await": await settle(label)
            case "held":
                if !(await until{await held(c,label,"/held")}) {timedOut.append("held:\(label)")}
            case "release": _=await held(c,label,"/release")
            case "awaitEvent":
                let kind=s["kind"] as! String
                if !(await until{broker.hasEvent(kind,label)}) {timedOut.append("event:\(kind):\(label)")}
            case "startQueued": pending[label]!.start!()
            case "retire":
                broker.portals[s["portal"] as! String]!.retired=true
                steps.append(["label":label,"op":op,"outcome":["ok":true]])
            case "bind":
                broker.bind(s["portal"] as! String,app:s["app"] as! String,grants:Set(s["grants"] as! [String]))
                steps.append(["label":label,"op":op,"outcome":["ok":true]])
            case "reset": steps.append(["label":label,"op":op,"outcome":broker.reset(portal)])
            case "cookiesGet":
                let target=(s["path"] as? String).map{["path":$0] as [String:Any]}
                steps.append(["label":label,"op":op,"outcome":broker.cookiesGet(portal,url(c,label,target))])
            case "cookiesSet": steps.append(["label":label,"op":op,"outcome":broker.cookiesSet(portal,url(c,label),s["cookie"] as! [String:Any])])
            case "cookiesDelete": steps.append(["label":label,"op":op,"outcome":broker.cookiesDelete(portal,url(c,label),s["cookie"] as! [String:Any])])
            case "snapshot": steps.append(["label":label,"op":op,"outcome":["ok":true],"jar":broker.snapshot(s["app"] as! String)])
            case "tlsNegative": steps.append(["label":label,"op":op,"outcome":await tlsNegative(c,label)])
            case "hostSeed": hostSeed();steps.append(["label":label,"op":op,"outcome":["ok":true]])
            case "hostRequest":
                let exchange=hostClient.start(URLRequest(url:URL(string:url(c,label))!))
                await hostClient.finish(exchange)
                steps.append(["label":label,"op":op,"outcome":["ok":exchange.error==nil,"status":exchange.response?.statusCode ?? NSNull()]])
            case "hostInspect":
                let saw=HTTPCookieStorage.shared.cookies?.contains{$0.name==(s["marker"] as! String)} ?? false
                steps.append(["label":label,"op":op,"outcome":["hostSawMarker":saw]])
            case "hostClear": hostClear();steps.append(["label":label,"op":op,"outcome":["ok":true]])
            default: errors.append(["error":"unknown op "+op])
            }
        }
        return ["case":c["id"]!,"steps":steps,"events":broker.events,"timedOut":timedOut]
    }
    /// No pinning delegate: default validation with the device's own roots must refuse the probe's certificate.
    func tlsNegative(_ c:[String:Any],_ label:String) async -> [String:Any] {
        do {
            let (_,response)=try await URLSession(configuration:Client.broker()).data(for:URLRequest(url:URL(string:url(c,label))!))
            return ["ok":true,"status":(response as? HTTPURLResponse)?.statusCode ?? NSNull()]
        } catch {return denied("tlsRefused")}
    }
    /// Stands for a host with its own login in the process's shared stores. Session persistence keeps it off disk.
    func hostSeed(){
        HTTPCookieStorage.shared.cookieAcceptPolicy = .always
        HTTPCookieStorage.shared.setCookie(HTTPCookie(properties:[.domain:"localhost",.path:"/",.name:"host_ambient",.value:"sentinel"])!)
        let space=URLProtectionSpace(host:"localhost",port:Int(port)!,protocol:"https",realm:"t28",authenticationMethod:NSURLAuthenticationMethodHTTPBasic)
        let credential=URLCredential(user:"moonpool-fixture-user",password:"not-a-secret",persistence:.forSession)
        URLCredentialStorage.shared.setDefaultCredential(credential,for:space)
        hostCredentialSpace=space;hostCredential=credential
    }
    func hostClear(){
        for cookie in HTTPCookieStorage.shared.cookies ?? [] {HTTPCookieStorage.shared.deleteCookie(cookie)}
        if let space=hostCredentialSpace,let credential=hostCredential {URLCredentialStorage.shared.remove(credential,for:space)}
        hostCredentialSpace=nil;hostCredential=nil
    }
    override func viewDidLoad(){super.viewDidLoad();Task{await execute()}}
    func execute() async {
        report=["platform":"ios","run":run,"release":UIDevice.current.systemVersion,"client":"URLSession","complete":false]
        do {
            let der=try Data(contentsOf:fixtures.appendingPathComponent("ca.der"))
            let anchor=SecCertificateCreateWithData(nil,der as CFData)!
            brokerClient=Client(anchor:anchor,configuration:Client.broker(),answersChallenges:false)
            harness=Client(anchor:anchor,configuration:Client.broker(),answersChallenges:false)
            hostClient=Client(anchor:anchor,configuration:URLSessionConfiguration.default,answersChallenges:true)
            hostClear()
            let cases=try JSONSerialization.jsonObject(with:Data(contentsOf:fixtures.appendingPathComponent("cases.json"))) as! [[String:Any]]
            for c in cases {
                observations.append(await perform(c));hostClear();save("progress.json")
            }
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
        let window=UIWindow(frame:UIScreen.main.bounds);window.rootViewController=Controller(run:value("--run"),port:value("--port"),second:value("--second"),control:value("--control"));self.window=window;window.makeKeyAndVisible();return true
    }
}
