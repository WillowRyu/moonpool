import UIKit

/// Feeds each vector to iOS's own cookie parser, then to a private in-memory cookie storage, the per-app jar option W would use.
/// No network, no WebView. Each vector gets a fresh ephemeral storage, checked empty before and emptied after.
enum Probe {
    static func describe(_ cookie:HTTPCookie)->[String:Any] {
        [
            "name":cookie.name,"value":cookie.value,"domain":cookie.domain,"path":cookie.path,
            "secure":cookie.isSecure,"httpOnly":cookie.isHTTPOnly,"sessionOnly":cookie.isSessionOnly,
            "expiresMs":cookie.expiresDate.map {Int64(($0.timeIntervalSince1970*1000).rounded())} ?? NSNull(),
            "sameSite":cookie.sameSitePolicy?.rawValue ?? NSNull(),
        ]
    }

    static func decode(_ field:Substring)->String {
        String(decoding:Data(base64Encoded:String(field)) ?? Data(),as:UTF8.self)
    }

    static func observe(_ row:String)->[String:Any] {
        let parts=row.split(separator:"\t",omittingEmptySubsequences:false)
        let id=String(parts[0]),url=decode(parts[1]),line=decode(parts[2]),checks=decode(parts[3])
        var observation:[String:Any]=["id":id]
        guard let target=URL(string:url) else {observation["error"]="bad url";return observation}
        let configuration=URLSessionConfiguration.ephemeral
        guard let storage=configuration.httpCookieStorage else {observation["error"]="no storage";return observation}
        storage.cookieAcceptPolicy = .always
        observation["startedEmpty"]=(storage.cookies ?? []).isEmpty
        let parsed=HTTPCookie.cookies(withResponseHeaderFields:["Set-Cookie":line],for:target)
        storage.setCookies(parsed,for:target,mainDocumentURL:nil)
        let stored=storage.cookies ?? []
        let name=parsed.first?.name
        let targets=checks.isEmpty ? []:checks.components(separatedBy:"\n")
        observation["parsed"]=parsed.map(describe)
        observation["stored"]=stored.map(describe)
        observation["sends"]=targets.map {check in
            guard let name,let url=URL(string:check) else {return false}
            return (storage.cookies(for:url) ?? []).contains {$0.name==name}
        }
        for cookie in stored {storage.deleteCookie(cookie)}
        observation["endedEmpty"]=(storage.cookies ?? []).isEmpty
        return observation
    }
}

@MainActor final class Controller:UIViewController {
    let run:String,now:String
    init(run:String,now:String){self.run=run;self.now=now;super.init(nibName:nil,bundle:nil)}
    required init?(coder:NSCoder){fatalError()}
    override func viewDidLoad(){super.viewDidLoad();DispatchQueue.main.async {self.execute()}}
    func execute(){
        let documents=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]
        let started=Int64((Date().timeIntervalSince1970*1000).rounded())
        var observations:[[String:Any]]=[],errors:[String]=[],complete=false
        do {
            let rows=try String(contentsOf:documents.appendingPathComponent("input.tsv"),encoding:.utf8).split(separator:"\n").map(String.init)
            observations=rows.map(Probe.observe)
            complete=true
        } catch {errors.append(String(describing:error))}
        let report:[String:Any]=["platform":"ios","run":run,"nowMs":Int64(now) ?? 0,"appStartMs":started,"release":UIDevice.current.systemVersion,
                                 "complete":complete,"errors":errors,"observations":observations]
        if let data=try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]) {
            try? data.write(to:documents.appendingPathComponent("report.json"),options:.atomic)
        }
    }
}

@main @MainActor final class AppDelegate:UIResponder,UIApplicationDelegate {
    var window:UIWindow?
    func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?=nil)->Bool {
        let args=ProcessInfo.processInfo.arguments
        func value(_ key:String)->String {args[args.firstIndex(of:key)!+1]}
        let window=UIWindow(frame:UIScreen.main.bounds);window.rootViewController=Controller(run:value("--run"),now:value("--now"))
        self.window=window;window.makeKeyAndVisible();return true
    }
}
