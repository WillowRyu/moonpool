import CryptoKit
import Network
import UIKit

final class Exchange {
    var response:HTTPURLResponse?,data=Data(),error:Error?,done=false
    var headersDelivered:((HTTPURLResponse)->Void)?,challengeResponse:((HTTPURLResponse)->Void)?
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
        c.timeoutIntervalForRequest=40 // Matches the Android client's timeouts.
        return c
    }
    func urlSession(_ session:URLSession,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        guard challenge.protectionSpace.authenticationMethod==NSURLAuthenticationMethodServerTrust,let trust=challenge.protectionSpace.serverTrust else {completionHandler(.performDefaultHandling,nil);return}
        SecTrustSetAnchorCertificates(trust,[anchor] as CFArray);SecTrustSetAnchorCertificatesOnly(trust,true)
        var failure:CFError?
        if SecTrustEvaluateWithError(trust,&failure){completionHandler(.useCredential,URLCredential(trust:trust))}else{completionHandler(.cancelAuthenticationChallenge,nil)}
    }
    /// The first response of a Basic resend comes here and never reaches the response callback below.
    func urlSession(_ session:URLSession,task:URLSessionTask,didReceive challenge:URLAuthenticationChallenge,completionHandler:@escaping(URLSession.AuthChallengeDisposition,URLCredential?)->Void){
        if let http=challenge.failureResponse as? HTTPURLResponse {exchanges[task.taskIdentifier]?.challengeResponse?(http)}
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
    func start(_ request:URLRequest,headers:((HTTPURLResponse)->Void)?=nil,challenged:((HTTPURLResponse)->Void)?=nil,finished:(()->Void)?=nil)->Exchange {
        let task=session.dataTask(with:request),exchange=Exchange()
        exchange.headersDelivered=headers;exchange.challengeResponse=challenged;exchange.finished=finished
        exchanges[task.taskIdentifier]=exchange;task.resume();return exchange
    }
    func finish(_ exchange:Exchange) async {
        if exchange.done {return}
        await withCheckedContinuation{continuation in exchange.finished={continuation.resume()}}
    }
}

final class Portal {
    let app:String,grants:Set<String>;var retired=false
    init(app:String,grants:Set<String>){self.app=app;self.grants=grants}
}
final class AppSession {
    var jar:CookieJar
    var generation=0
    init(publicSuffixes:PublicSuffixList){jar=CookieJar(publicSuffixes:publicSuffixes)}
}
final class Pending {var outcome:[String:Any]?,start:(()->Void)?
    func settle(_ value:[String:Any]){outcome=value}
}
func denied(_ code:Any,_ reason:String?=nil)->[String:Any]{
    var found:[String:Any]=["ok":false,"code":code];if let reason {found["reason"]=reason};return found
}

/// Research broker: one in-memory c04-1 jar per app, selected by a host-side portal binding.
/// All jar work runs on the main queue, so mutations are serialized in delivery order.
final class Broker {
    struct ServiceOrigin:Hashable {
        let host:String
        let port:Int
    }
    private struct ServiceTarget {
        let url:URL
        let origin:ServiceOrigin
        let cookieRequest:CookieJar.Request
    }
    static let requestFields:Set<String>=["url","method","credentials","headers","body"],cookieFields:Set<String>=["name","value","path","maxAge"]
    static let forbiddenHeaders:Set<String>=["cookie","cookie2","host","origin","proxy-authorization","content-length","transfer-encoding","connection","te","upgrade","keep-alive"]
    static let methods:Set<String>=["GET","HEAD","POST","PUT","PATCH","DELETE","OPTIONS"],bodylessMethods:Set<String>=["GET","HEAD"]
    static let cookieDeleteFields:Set<String>=["name","path"]
    static let tokenScalars=Set("!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".unicodeScalars)
    static func isToken(_ text:String)->Bool {!text.isEmpty&&text.unicodeScalars.allSatisfy{tokenScalars.contains($0)}}
    static func isHeaderValue(_ text:String)->Bool {text.unicodeScalars.allSatisfy{$0=="\t"||(0x20...0x7E).contains($0.value)}}
    /// RFC 6265 cookie-octets, so a script value cannot add a pair beside a protected cookie.
    static func isCookieValue(_ text:String)->Bool {
        text.unicodeScalars.allSatisfy{(0x21...0x7E).contains($0.value) && ![0x22,0x2C,0x3B,0x5C].contains($0.value)}
    }
    static func isCookiePath(_ text:String)->Bool {
        text.hasPrefix("/")&&text.unicodeScalars.allSatisfy{(0x20...0x7E).contains($0.value)&&$0.value != 0x3B}
    }
    static func integer(_ value:Any)->Int? {
        guard let number=value as? NSNumber,CFGetTypeID(number) != CFBooleanGetTypeID(),!CFNumberIsFloatType(number) else {return nil}
        return number.intValue
    }
    var portals:[String:Portal]=[:],apps:[String:AppSession]=[:],events:[[String:Any]]=[],sequence=0
    let client:Client
    private let approved:Set<ServiceOrigin>
    private let publicSuffixes:PublicSuffixList
    private let clock:()->Int64
    init(client:Client,approved:Set<ServiceOrigin>,publicSuffixes:PublicSuffixList,clock:@escaping ()->Int64){
        self.client=client
        self.approved=Set(approved.compactMap(Broker.canonicalRegistration))
        self.publicSuffixes=publicSuffixes
        self.clock=clock
    }
    func bind(_ id:String,app:String,grants:Set<String>){
        portals[id]=Portal(app:app,grants:grants)
        if apps[app]==nil {apps[app]=AppSession(publicSuffixes:publicSuffixes)}
    }
    func event(_ kind:String,_ label:String){sequence+=1;events.append(["seq":sequence,"kind":kind,"label":label])}
    /// Pinned order: owner, then scope, then fields, then service. A missing scope beats malformed fields (SPEC 4.2).
    func admit(_ portal:Portal,_ scope:String)->[String:Any]? {
        if portal.retired {return denied("retired")}
        return portal.grants.contains(scope) ? nil:denied(-32000)
    }
    private static func secureTarget(_ text:String)->ServiceTarget? {
        // Foundation can map Unicode or discard characters before exposing a URL host.
        let prefix="https://".utf8,bytes=text.utf8
        guard bytes.starts(with:prefix) else {return nil}
        let authority=bytes.dropFirst(prefix.count).prefix { byte in
            byte != UInt8(ascii:"/") && byte != UInt8(ascii:"?") && byte != UInt8(ascii:"#")
        }
        guard !authority.isEmpty,authority.allSatisfy({ (0x21...0x7E).contains($0) && $0 != UInt8(ascii:"%") })
        else {return nil}
        guard let input=URL(string:text),
              var parts=URLComponents(url:input,resolvingAgainstBaseURL:false),
              parts.scheme=="https",parts.user==nil,parts.password==nil,parts.fragment==nil,
              parts.rangeOfPort==nil || parts.port != nil,
              (1...65535).contains(parts.port ?? 443),
              let inputHost=input.host(percentEncoded:true),!inputHost.contains("%") else {return nil}
        let host:String
        if inputHost.contains(":") {
            // OkHttp turns mapped literals into IPv4 targets. Reject that authority change on both platforms.
            guard let address=IPv6Address(inputHost),!address.isIPv4Mapped else {return nil}
            host=canonicalIPv6(address)
            parts.percentEncodedHost="[\(host)]"
        } else {
            guard inputHost.split(separator:".").allSatisfy({ label in
                !label.hasPrefix("-") && !label.hasSuffix("-")
                    && label.utf8.allSatisfy { (0x30...0x39).contains($0) || (0x41...0x5A).contains($0)
                        || (0x61...0x7A).contains($0) || $0==0x2D }
            }) else {return nil}
            host=inputHost.lowercased()
            parts.percentEncodedHost=host
        }
        parts.percentEncodedPath=dispatchedPath(parts.percentEncodedPath)
        guard let url=parts.url,url.host(percentEncoded:true)==host,
              let cookieRequest=try? CookieJar.Request.of(host:host,encodedPath:url.path(percentEncoded:true)) else {return nil}
        let origin=ServiceOrigin(host:host,port:url.port ?? 443)
        return ServiceTarget(url:url,origin:origin,cookieRequest:cookieRequest)
    }
    private static func canonicalIPv6(_ address:IPv6Address)->String {
        let text=address.debugDescription
        guard text.contains(".") else {return text}
        // Darwin may print the last two groups of an IPv4-compatible address in dotted notation.
        let tail=address.rawValue.suffix(4).reduce(UInt32(0)) { ($0 << 8) | UInt32($1) }
        return "::\(String(tail >> 16,radix:16)):\(String(tail & 0xffff,radix:16))"
    }
    private static func dispatchedPath(_ path:String)->String {
        // Resolve the same literal and percent-encoded dot segments as OkHttp. Keep every other byte.
        let segments=path.dropFirst().split(separator:"/",omittingEmptySubsequences:false)
        var resolved:[Substring]=[]
        for (index,segment) in segments.enumerated() {
            switch segment.lowercased() {
            case ".", "%2e":
                if index==segments.count-1 {resolved.append("")}
            case "..", ".%2e", "%2e.", "%2e%2e":
                _=resolved.popLast()
                if index==segments.count-1 {resolved.append("")}
            default: resolved.append(segment)
            }
        }
        return "/"+resolved.joined(separator:"/")
    }
    private static func canonicalRegistration(_ registration:ServiceOrigin)->ServiceOrigin? {
        let host=registration.host
        // Registrations supply a host field, so it cannot introduce a URL path or query.
        guard !host.utf8.contains(where:{ "/?#".utf8.contains($0) }) else {return nil}
        let authority=host.contains(":") && !host.hasPrefix("[") ? "[\(host)]" : host
        return secureTarget("https://\(authority):\(registration.port)/")?.origin
    }
    private func isApproved(_ target:ServiceTarget)->Bool {approved.contains(target.origin)}
    /// A value of the wrong type is refused, never read as the default: credentials:false must not mean include.
    static func validRequestFields(_ params:[String:Any])->Bool {
        if !Set(params.keys).isSubset(of:requestFields) {return false}
        var method="GET"
        if let given=params["method"] {
            guard let text=given as? String,methods.contains(text) else {return false}
            method=text
        }
        if let given=params["credentials"] {
            guard let text=given as? String,text=="include"||text=="omit" else {return false}
        }
        if let given=params["body"] {
            guard given is String,!bodylessMethods.contains(method) else {return false}
        }
        guard let given=params["headers"] else {return true}
        guard let headers=given as? [String:Any] else {return false}
        for (name,value) in headers {
            let lower=name.lowercased()
            if forbiddenHeaders.contains(lower)||lower.hasPrefix("sec-")||lower.hasPrefix("proxy-") {return false}
            guard isToken(name),let text=value as? String,isHeaderValue(text) else {return false}
        }
        return true
    }
    func request(_ portalId:String,_ label:String,_ params:[String:Any],deferred:Bool)->Pending {
        let pending=Pending(),portal=portals[portalId]!
        if let refused=admit(portal,"http") {pending.settle(refused);return pending}
        guard Broker.validRequestFields(params),let text=params["url"] as? String,
              let target=Broker.secureTarget(text) else {pending.settle(denied(-32602));return pending}
        guard isApproved(target) else {pending.settle(denied(-32000));return pending}
        let session=apps[portal.app]!,generation=session.generation
        pending.start={[unowned self] in self.dispatch(portal,session,generation,label,params,target,pending)}
        if !deferred {pending.start!()}
        return pending
    }
    func finish(_ portal:Portal,_ pending:Pending,_ outcome:[String:Any]){pending.settle(portal.retired ? ["delivered":false]:outcome)}
    /// The owner and generation are rechecked here because queued work may start after a close or a reset.
    private func dispatch(_ portal:Portal,_ session:AppSession,_ generation:Int,_ label:String,_ params:[String:Any],_ target:ServiceTarget,_ pending:Pending){
        if portal.retired {finish(portal,pending,denied("retired"));return}
        if session.generation != generation {finish(portal,pending,denied(-32007,"sessionReset"));return}
        let include=(params["credentials"] as? String ?? "include") != "omit"
        var request=URLRequest(url:target.url)
        request.httpMethod=params["method"] as? String ?? "GET"
        if let body=params["body"] as? String {request.httpBody=Data(body.utf8)}
        for (name,value) in params["headers"] as? [String:String] ?? [:] {request.setValue(value,forHTTPHeaderField:name)}
        if include {
            let cookie=session.jar.cookieHeader(target.cookieRequest,now:clock())
            if !cookie.isEmpty {request.setValue(cookie,forHTTPHeaderField:"Cookie")}
        }
        var exchange:Exchange!
        // One batch per guest request, from the first response: Android sends once, so a resend must not change the jar.
        var committed=false
        let commitOnce:(HTTPURLResponse)->Void={[unowned self] response in
            if committed {return}
            committed=true
            self.commit(session,generation,include,label,target.cookieRequest,response)
        }
        exchange=client.start(request,headers:commitOnce,challenged:commitOnce,finished:{[unowned self] in
            if session.generation != generation {self.finish(portal,pending,denied(-32007,"sessionReset"));return}
            guard exchange.error==nil,let response=exchange.response else {self.finish(portal,pending,denied(-32007,"network"));return}
            self.finish(portal,pending,["ok":true,"status":response.statusCode,"headers":Broker.projected(response),"bodyText":String(decoding:exchange.data,as:UTF8.self)])
        })
    }
    /// Runs when the client delivers response headers. A stale generation is fenced, not written.
    func commit(_ session:AppSession,_ generation:Int,_ include:Bool,_ label:String,_ request:CookieJar.Request,_ response:HTTPURLResponse){
        event("headers",label)
        guard let folded=response.value(forHTTPHeaderField:"Set-Cookie"),include else {return}
        if session.generation != generation {event("fence",label);return}
        session.jar.receive([folded],request,now:clock())
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
    private func cookieTarget(_ portal:Portal,_ text:String)->(ServiceTarget?,[String:Any]?) {
        if let refused=admit(portal,"cookies") {return (nil,refused)}
        guard let target=Broker.secureTarget(text) else {return (nil,denied(-32602))}
        return isApproved(target) ? (target,nil):(nil,denied(-32000))
    }
    func cookiesGet(_ portalId:String,_ text:String)->[String:Any] {
        let portal=portals[portalId]!,(found,refused)=cookieTarget(portal,text)
        guard let target=found else {return refused!}
        let readable=apps[portal.app]!.jar.scriptCookies(target.cookieRequest,now:clock()).map {
            ["name":$0.name,"path":$0.path,"value":$0.value]
        }
        return ["ok":true,"cookies":readable]
    }
    func cookiesSet(_ portalId:String,_ text:String,_ fields:[String:Any])->[String:Any] {
        let portal=portals[portalId]!
        if let refused=admit(portal,"cookies") {return refused}
        if !Set(fields.keys).isSubset(of:Broker.cookieFields) {return denied(-32602)}
        guard let name=fields["name"] as? String,let value=fields["value"] as? String,Broker.isToken(name),Broker.isCookieValue(value) else {return denied(-32602)}
        var path="/",maxAge:Int64?
        if let given=fields["path"] {
            guard let text=given as? String,Broker.isCookiePath(text) else {return denied(-32602)}
            path=text
        }
        if let given=fields["maxAge"] {
            guard let age=Broker.integer(given) else {return denied(-32602)}
            maxAge=Int64(age)
        }
        let (found,refused)=cookieTarget(portal,text)
        guard let target=found else {return refused!}
        let stored=apps[portal.app]!.jar.setScriptCookie(target.cookieRequest,name:name,value:value,path:path,maxAge:maxAge,now:clock())
        return stored ? ["ok":true]:denied(-32000)
    }
    func cookiesDelete(_ portalId:String,_ text:String,_ fields:[String:Any])->[String:Any] {
        let portal=portals[portalId]!
        if let refused=admit(portal,"cookies") {return refused}
        if !Set(fields.keys).isSubset(of:Broker.cookieDeleteFields) {return denied(-32602)}
        guard let name=fields["name"] as? String,Broker.isToken(name) else {return denied(-32602)}
        var path="/"
        if let given=fields["path"] {
            guard let text=given as? String,Broker.isCookiePath(text) else {return denied(-32602)}
            path=text
        }
        let (found,refused)=cookieTarget(portal,text)
        guard let target=found else {return refused!}
        let deleted=apps[portal.app]!.jar.deleteScriptCookie(target.cookieRequest,name:name,path:path,now:clock())
        return deleted ? ["ok":true]:denied(-32000)
    }
    /// Advances the generation first, so no in-flight response can write after this returns.
    func reset(_ portalId:String)->[String:Any] {
        let portal=portals[portalId]!
        if let refused=admit(portal,"http") {return refused}
        let session=apps[portal.app]!
        session.generation+=1;session.jar=CookieJar(publicSuffixes:publicSuffixes);event("reset",portalId)
        return ["ok":true]
    }
    /// Harness evidence only. Nothing the guest can reach calls this.
    func snapshot(_ app:String)->[String] {(apps[app]?.jar.entries ?? []).map{"\($0.name)=\($0.value)"}.sorted()}
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
        let portSuffix=t["defaultPort"] as? Bool==true ? "":":\(listenerPort(t["listener"] as? String))"
        return "\(t["scheme"] as? String ?? "https")://\(userinfo)\(t["host"] as? String ?? "localhost")\(portSuffix)\(t["path"] as? String ?? "/s")?run=\(run)&case=\(c["id"] as! String)&step=\(label)\(fragment)"
    }
    func askControl(_ c:[String:Any],_ label:String,_ path:String) async -> Exchange {
        let exchange=harness.start(URLRequest(url:URL(string:"https://localhost:\(control)\(path)?run=\(run)&case=\(c["id"] as! String)&step=\(label)")!))
        await harness.finish(exchange)
        return exchange
    }
    func held(_ c:[String:Any],_ label:String) async -> Bool {
        let exchange=await askControl(c,label,"/held")
        return ((try? JSONSerialization.jsonObject(with:exchange.data)) as? [String:Any])?["held"] as? Bool ?? false
    }
    func release(_ c:[String:Any],_ label:String) async -> Bool {
        let exchange=await askControl(c,label,"/release")
        return exchange.error==nil&&exchange.response?.statusCode==200
    }
    func until(_ check:() async -> Bool) async -> Bool {
        let deadline=Date().addingTimeInterval(barrierSeconds)
        while Date()<deadline {
            if await check() {return true}
            await sleep(0.05)
        }
        return false
    }
    func perform(_ c:[String:Any],publicSuffixes:PublicSuffixList) async -> [String:Any] {
        var steps:[[String:Any]]=[],timedOut:[String]=[],pending:[String:Pending]=[:]
        var approved:Set<Broker.ServiceOrigin>=[]
        if let declared=c["approved"] as? [[String:Any]] {
            for entry in declared {
                let servicePort=entry["port"] as? Int ?? Int(listenerPort(entry["listener"] as? String))!
                approved.insert(Broker.ServiceOrigin(host:entry["host"] as! String,port:servicePort))
            }
        } else {approved.insert(Broker.ServiceOrigin(host:"localhost",port:Int(port)!))}
        let start=c["clock"] as? Int64
        var fixtureTime=start
        let broker=Broker(client:brokerClient,approved:approved,publicSuffixes:publicSuffixes) {
            fixtureTime ?? Int64(Date().timeIntervalSince1970)
        }
        for (id,value) in c["portals"] as! [String:[String:Any]] {broker.bind(id,app:value["app"] as! String,grants:Set(value["grants"] as! [String]))}
        func settle(_ label:String) async {
            let found=pending[label]!
            if !(await until{found.outcome != nil}) {timedOut.append("await:\(label)");return}
            steps.append(["label":label,"op":"request","outcome":found.outcome!])
        }
        for s in c["steps"] as! [[String:Any]] {
            if let start,let offset=s["at"] as? Int64 {fixtureTime=start+offset}
            let op=s["op"] as! String,label=s["label"] as! String,portal=s["portal"] as? String ?? "A1"
            switch op {
            case "request":
                var params=s["params"] as? [String:Any] ?? [:]
                let target=params.removeValue(forKey:"target") as? [String:Any],deferred=params.removeValue(forKey:"deferred") as? Bool ?? false
                if s["omitUrl"] as? Bool != true&&params["url"]==nil {params["url"]=url(c,label,target)}
                pending[label]=broker.request(portal,label,params,deferred:deferred)
                if s["wait"] as? Bool != false {await settle(label)}
            case "await": await settle(label)
            case "held":
                if !(await until{await held(c,label)}) {timedOut.append("held:\(label)")}
            case "release":
                if !(await release(c,label)) {timedOut.append("release:\(label)")}
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
                let target=s["target"] as? [String:Any] ?? (s["path"] as? String).map{["path":$0]}
                steps.append(["label":label,"op":op,"outcome":broker.cookiesGet(portal,url(c,label,target))])
            case "cookiesSet":
                let target=s["target"] as? [String:Any]
                steps.append(["label":label,"op":op,"outcome":broker.cookiesSet(portal,url(c,label,target),s["cookie"] as! [String:Any])])
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
    static let tlsFailures:Set<URLError.Code>=[.secureConnectionFailed,.serverCertificateHasBadDate,.serverCertificateUntrusted,.serverCertificateHasUnknownRoot,.serverCertificateNotYetValid]
    /// No pinning delegate: default validation with the device's own roots must refuse the probe's certificate.
    func tlsNegative(_ c:[String:Any],_ label:String) async -> [String:Any] {
        do {
            let (_,response)=try await URLSession(configuration:Client.broker()).data(for:URLRequest(url:URL(string:url(c,label))!))
            return ["ok":true,"status":(response as? HTTPURLResponse)?.statusCode ?? NSNull()]
        } catch let error as URLError where Controller.tlsFailures.contains(error.code) {
            return ["ok":false,"code":"tlsRefused","detail":error.code.rawValue]
        } catch {return ["ok":false,"code":"notTls","detail":(error as NSError).code]}
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
            let psl=try Data(contentsOf:fixtures.appendingPathComponent("public_suffix_list.dat"))
            let publicSuffixes=try PublicSuffixList.parse(Array(psl))
            report["pslSha256"]=SHA256.hash(data:psl).map{String(format:"%02x",$0)}.joined()
            let inputs=try Data(contentsOf:fixtures.appendingPathComponent("profile-inputs.json"))
            report["profileObservations"]=try Adapter.replay(inputs,publicSuffixes:publicSuffixes)
            let cases=try JSONSerialization.jsonObject(with:Data(contentsOf:fixtures.appendingPathComponent("cases.json"))) as! [[String:Any]]
            for c in cases {
                observations.append(await perform(c,publicSuffixes:publicSuffixes));hostClear();save("progress.json")
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
