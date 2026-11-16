import Security
import UIKit
import WebKit

@MainActor final class LocalPaths: NSObject, WKURLSchemeHandler {
    private let run: String
    private let base: String
    let origin: String
    private let script: String
    private(set) var requests = 0
    private(set) var popupDenials = 0

    init(run: String, base: String, origin: String, script: String) {
        self.run = run
        self.base = base
        self.origin = origin
        self.script = script
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, origin == "\(url.scheme ?? "")://\(url.host ?? "")" else {
            task.didFailWithError(URLError(.unsupportedURL))
            return
        }
        let data: Data
        let type: String
        var headers = ["Cache-Control": "no-store"]
        switch url.path {
        case "/local.gif":
            type = "image/gif"
            data = Data(base64Encoded: "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")!
            headers["Set-Cookie"] = "c09_local=1; Path=/; Secure"
        case "/worker.js":
            type = "text/javascript"
            data = Data("postMessage('worker')".utf8)
        case "/guest", "/frame":
            if url.path == "/guest" { requests += 1 }
            let view = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?
                .first(where: { $0.name == "view" })?.value ?? ""
            let config: [String: Any] = ["run": run, "base": base, "origin": origin, "view": view, "frame": url.path == "/frame"]
            let json = String(decoding: try! JSONSerialization.data(withJSONObject: config), as: UTF8.self)
            let policy = "default-src 'none'; script-src 'unsafe-inline'; connect-src 'none'; "
                + "form-action 'none'; worker-src 'none'; frame-src 'self'; "
                + "img-src 'self' \(base)/static/; base-uri 'none'"
            type = "text/html; charset=utf-8"
            data = Data("""
            <!doctype html><meta charset=utf-8><meta http-equiv="Content-Security-Policy" content="\(policy)">
            <script>window.c09Config=\(json);
            \(script)</script><body>
            """.utf8)
        default:
            task.didFailWithError(URLError(.fileDoesNotExist))
            return
        }
        headers["Content-Type"] = type
        task.didReceive(HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: headers)!)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}

    func recordPopupDenial() { popupDenials += 1 }
}

@MainActor final class Controller: UIViewController, WKNavigationDelegate, WKUIDelegate {
    private struct OwnedView {
        let web: WKWebView
        let store: WKWebsiteDataStore
        let partition: String
        let origin: String?
        let loader: LocalPaths?
    }

    let run: String
    let base: String
    private let stack = UIStackView()
    private var loaders: [ObjectIdentifier: LocalPaths] = [:]
    private var samples: [[String: Any]] = []
    private var controls: [[String: Any]] = []
    private var errors: [[String: Any]] = []
    private var partitions: [String: String] = [:]
    private var anchor: SecCertificate!
    private var script = ""

    init(run: String, base: String) {
        self.run = run
        self.base = base
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError() }

    override func viewDidLoad() {
        super.viewDidLoad()
        stack.axis = .vertical
        stack.distribution = .fillEqually
        stack.frame = view.bounds
        stack.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(stack)
        Task { await execute() }
    }

    func webView(_ webView: WKWebView, didReceive challenge: URLAuthenticationChallenge,
                 completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        let space = challenge.protectionSpace
        guard space.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              ["localhost", "127.0.0.1"].contains(space.host),
              space.port == URL(string: base)?.port,
              let trust = space.serverTrust, let anchor else {
            completionHandler(.performDefaultHandling, nil)
            return
        }
        SecTrustSetAnchorCertificates(trust, [anchor] as CFArray)
        SecTrustSetAnchorCertificatesOnly(trust, true)
        if SecTrustEvaluateWithError(trust, nil) {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            errors.append(["tls": space.host])
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let loader = loaders[ObjectIdentifier(webView)], let url = action.request.url {
            let allowed = loader.origin == "\(url.scheme ?? "")://\(url.host ?? "")"
            decisionHandler(allowed ? .allow : .cancel)
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        loaders[ObjectIdentifier(webView)]?.recordPopupDenial()
        return nil
    }

    private func make(_ store: WKWebsiteDataStore, partition: String, origin: String? = nil) -> OwnedView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = store
        config.preferences.javaScriptCanOpenWindowsAutomatically = true
        let loader = origin.map { LocalPaths(run: run, base: base, origin: $0, script: script) }
        if let loader { config.setURLSchemeHandler(loader, forURLScheme: "moonpool") }
        let web = WKWebView(frame: .zero, configuration: config)
        if let loader { loaders[ObjectIdentifier(web)] = loader }
        web.navigationDelegate = self
        web.uiDelegate = self
        stack.addArrangedSubview(web)
        return OwnedView(web: web, store: store, partition: partition, origin: origin, loader: loader)
    }

    private func discard(_ owned: OwnedView) {
        owned.web.stopLoading()
        owned.web.navigationDelegate = nil
        owned.web.uiDelegate = nil
        loaders.removeValue(forKey: ObjectIdentifier(owned.web))
        stack.removeArrangedSubview(owned.web)
        owned.web.removeFromSuperview()
    }

    private func setPolicy(_ store: WKWebsiteDataStore, allow: Bool) async {
        await withCheckedContinuation { resume in
            store.httpCookieStore.setCookiePolicy(allow ? .allow : .disallow) { resume.resume() }
        }
    }

    private func policyAllows(_ store: WKWebsiteDataStore) async -> Bool {
        await withCheckedContinuation { resume in
            store.httpCookieStore.getCookiePolicy { resume.resume(returning: $0 == .allow) }
        }
    }

    private func recordsPresent(_ store: WKWebsiteDataStore) async -> Bool {
        await withCheckedContinuation { resume in
            store.fetchDataRecords(ofTypes: [WKWebsiteDataTypeCookies]) { resume.resume(returning: !$0.isEmpty) }
        }
    }

    private func cookiePairs(_ store: WKWebsiteDataStore) async -> [String] {
        await withCheckedContinuation { resume in
            store.httpCookieStore.getAllCookies {
                resume.resume(returning: $0.map { "\($0.name)=\($0.value)" }.sorted())
            }
        }
    }

    private func quoted(_ text: String) -> String {
        String(decoding: try! JSONEncoder().encode(text), as: UTF8.self)
    }

    private func awaitObject(_ web: WKWebView, _ expression: String) async throws -> [String: Any] {
        for _ in 0..<100 {
            if let text = try? await web.evaluateJavaScript("JSON.stringify(" + expression + ")") as? String,
               let value = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] {
                return value
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw NSError(domain: "FixtureObservationDeadline", code: 1, userInfo: [NSLocalizedDescriptionKey: expression])
    }

    private func controlPage(_ web: WKWebView, _ role: String, _ path: String, _ label: String) async throws -> [String: Any] {
        let host = role == "U" ? base.replacingOccurrences(of: "localhost", with: "127.0.0.1") : base
        let url = host + path + "?run=" + run + "&view=" + label
        web.load(URLRequest(url: URL(string: url)!, cachePolicy: .reloadIgnoringLocalCacheData))
        return try await awaitObject(web, "window.c09Control?.href === \(quoted(url)) ? window.c09Control : null")
    }

    private func control(_ owned: OwnedView, _ role: String, _ stage: String) async throws {
        let label = "\(role)-\(stage)"
        if stage == "before" {
            await setPolicy(owned.store, allow: true)
            _ = try await controlPage(owned.web, role, "/control", label)
        }
        let read = try await controlPage(owned.web, role, stage == "before" ? "/echo" : "/control", label)
        controls.append(["view": label, "cookie": read["cookie"]!, "policyAllows": await policyAllows(owned.store)])
    }

    private func gate(_ candidate: OwnedView, _ label: String, unknown: Bool = false) async throws {
        let oldCount = candidate.loader?.requests ?? 0
        let oldPopups = candidate.loader?.popupDenials ?? 0
        let before = label == "present" ? await cookiePairs(candidate.store) : []
        await setPolicy(candidate.store, allow: false)
        var events = ["policyComplete"]
        let allows = await policyAllows(candidate.store)
        events.append("policyRead")
        let presence: AdmissionGate.Presence
        var evidence: [String: Bool] = [:]
        if unknown || allows {
            presence = .unknown
        } else {
            let records = await recordsPresent(candidate.store)
            let cookies = await !cookiePairs(candidate.store).isEmpty
            evidence = ["records": records, "cookies": cookies]
            presence = records != cookies ? .unknown : (cookies ? .present : .empty)
        }
        events.append("presence")
        let owner = AdmissionGate { _, done in done(presence) }
        var loads = 0
        owner.admit(label, load: {
            events.append("load")
            loads += 1
            if label == "reload" { candidate.web.reload() }
            else { candidate.web.load(URLRequest(url: URL(string: candidate.origin! + "/guest?view=" + label)!)) }
        }, retire: {
            events.append("refuse")
            self.discard(candidate)
        })
        var guest: Any = NSNull()
        if loads == 1 {
            guest = try await awaitObject(candidate.web,
                "window.c09Result?.view === \(quoted(label)) ? window.c09Result : null")
            events.append("script")
        }
        let after = await cookiePairs(candidate.store)
        samples.append([
            "view": label, "partition": candidate.partition, "events": events,
            "policyAllows": allows, "presence": String(describing: presence), "presenceEvidence": evidence,
            "source": unknown ? "injected" : "native", "guest": guest, "loadCalls": loads,
            "guestResources": (candidate.loader?.requests ?? 0) - oldCount,
            "popupDenials": (candidate.loader?.popupDenials ?? 0) - oldPopups,
            "beforeCookies": before, "afterCookies": after, "afterPresent": !after.isEmpty,
        ])
    }

    private func execute() async {
        var complete = false
        // Initialize a never-loaded WebKit view before the first store operation.
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        let initializer = WKWebView(frame: .zero, configuration: config)
        defer { withExtendedLifetime(initializer) {} }
        do {
            let files = Bundle.main.bundleURL.appendingPathComponent("Fixtures")
            script = try String(contentsOf: files.appendingPathComponent("paths.js"), encoding: .utf8)
            let der = try Data(contentsOf: files.appendingPathComponent("ca.der"))
            guard let certificate = SecCertificateCreateWithData(nil, der as CFData) else {
                throw URLError(.serverCertificateHasUnknownRoot)
            }
            anchor = certificate
            let aID = UUID(), bID = UUID(), uID = UUID()
            let host = make(.default(), partition: "default")
            let other = make(WKWebsiteDataStore(forIdentifier: uID), partition: uID.uuidString)
            let seeded = make(WKWebsiteDataStore(forIdentifier: bID), partition: bID.uuidString)
            let origin = "moonpool://com.example.paths.\(run).a"
            let a = make(WKWebsiteDataStore(forIdentifier: aID), partition: aID.uuidString, origin: origin)
            partitions = ["A": a.partition, "B": seeded.partition, "H": host.partition, "U": other.partition]
            try await control(host, "H", "before")
            try await control(other, "U", "before")
            try await control(seeded, "B", "before")
            try await gate(a, "initial")
            try await control(host, "H", "after-A")
            try await control(other, "U", "after-A")
            try await control(seeded, "B", "after-A")
            try await gate(a, "reload")
            discard(a)
            try await gate(make(WKWebsiteDataStore(forIdentifier: aID), partition: aID.uuidString, origin: origin), "recreated")
            try await gate(make(seeded.store, partition: seeded.partition, origin: "moonpool://com.example.paths.\(run).b"), "present")
            try await control(host, "H", "after-B")
            try await control(other, "U", "after-B")
            try await gate(make(WKWebsiteDataStore(forIdentifier: aID), partition: aID.uuidString, origin: origin), "unknown", unknown: true)
            complete = true
        } catch { errors.append(["error": String(describing: error)]) }
        let report: [String: Any] = [
            "platform": "ios", "run": run, "release": UIDevice.current.systemVersion, "complete": complete,
            "samples": samples, "controls": controls, "partitions": partitions, "errors": errors,
        ]
        let path = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("report.json")
        if let data = try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: path, options: .atomic)
        }
    }
}

@main @MainActor final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let args = ProcessInfo.processInfo.arguments
        func value(_ key: String) -> String { args[args.firstIndex(of: key)! + 1] }
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = Controller(run: value("--run"), base: value("--base"))
        self.window = window
        window.makeKeyAndVisible()
        return true
    }
}
