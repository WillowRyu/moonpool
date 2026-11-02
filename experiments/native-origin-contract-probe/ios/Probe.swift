import UIKit
import WebKit

@MainActor
final class Scheme: NSObject, WKURLSchemeHandler {
    var record: (([String: Any]) -> Void)?
    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        let url = task.request.url!
        let data: Data
        let mime: String
        if url.path == "/probe.js" {
            data = try! Data(contentsOf: Bundle.main.bundleURL.appendingPathComponent("Fixtures/probe.js"))
            mime = "text/javascript"
        } else if url.path == "/frame.html" {
            data = Data("<!doctype html><meta charset=utf-8><p id=marker>\(url.host ?? "")</p><script>parent.postMessage({kind:'t28-frame',host:location.hostname},'*')</script>".utf8)
            mime = "text/html"
        } else if url.path == "/diagnostic.html" {
            data = Data("<!doctype html><script>webkit.messageHandlers.observe.postMessage({kind:'diagnostic',href:location.href,host:location.hostname,origin:location.origin})</script>".utf8)
            mime = "text/html"
        } else {
            data = try! Data(contentsOf: Bundle.main.bundleURL.appendingPathComponent("Fixtures/index.html"))
            mime = "text/html"
        }
        task.didReceive(URLResponse(url: url, mimeType: mime, expectedContentLength: data.count, textEncodingName: "utf-8"))
        task.didReceive(data)
        task.didFinish()
        record?(["event": "scheme-delivered", "url": url.absoluteString, "bytes": data.count, "mime": mime])
    }
    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) { }
}

@MainActor
final class Controller: UIViewController, WKScriptMessageHandler, WKNavigationDelegate {
    let phase: String
    let run: String
    let startup: String
    let stack = UIStackView()
    var stores: [String: WKWebsiteDataStore] = [:]
    var assignments: [String: UUID] = [:]
    var views: [String: WKWebView] = [:]
    var names: [ObjectIdentifier: String] = [:]
    var messages: [[String: Any]] = []
    var samples: [[String: Any]] = []
    var events: [[String: Any]] = []
    var identity: [[String: Any]] = []
    var output: URL { documents.appendingPathComponent("report.json") }
    var documents: URL { FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0] }
    init(phase: String, run: String, startup: String = "none") { self.phase = phase; self.run = run; self.startup = startup; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { fatalError() }

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        let origin = message.frameInfo.securityOrigin
        messages.append(["view": message.webView.flatMap { names[ObjectIdentifier($0)] } ?? "retired", "body": message.body,
            "nativeOrigin": ["scheme": origin.protocol, "host": origin.host, "port": origin.port],
            "mainFrame": message.frameInfo.isMainFrame])
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { failure(webView, error) }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { failure(webView, error) }
    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        let http = response.response as? HTTPURLResponse
        events.append(["view": names[ObjectIdentifier(webView)] ?? "retired", "event": "navigation-response",
            "url": response.response.url?.absoluteString ?? "", "status": http?.statusCode ?? 0,
            "mime": response.response.mimeType ?? "", "mainFrame": response.isForMainFrame])
        decisionHandler(.allow)
    }
    func failure(_ web: WKWebView, _ error: Error) {
        let value = error as NSError
        events.append(["view": names[ObjectIdentifier(web)] ?? "retired", "event": "load-error", "domain": value.domain,
            "code": value.code, "description": value.localizedDescription])
    }
    func make(_ name: String, store: WKWebsiteDataStore) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = store
        let handler = Scheme()
        handler.record = { [weak self] event in
            var value = event; value["view"] = name; self?.events.append(value)
        }
        config.setURLSchemeHandler(handler, forURLScheme: "moonpool")
        config.userContentController.add(self, name: "observe")
        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = self
        stack.addArrangedSubview(web)
        names[ObjectIdentifier(web)] = name
        events.append(["event": "view-created", "view": name, "storeIdentifier": web.configuration.websiteDataStore.identifier?.uuidString ?? "nil",
            "persistent": web.configuration.websiteDataStore.isPersistent])
        return web
    }
    func discard(_ web: WKWebView) {
        web.stopLoading(); web.navigationDelegate = nil
        web.configuration.userContentController.removeScriptMessageHandler(forName: "observe")
        stack.removeArrangedSubview(web); web.removeFromSuperview(); names.removeValue(forKey: ObjectIdentifier(web))
    }
    func pause(_ seconds: Double) async { try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000)) }
    func js(_ web: WKWebView, _ script: String) async -> Any {
        do { return try await web.evaluateJavaScript(script) ?? NSNull() }
        catch { return ["evaluationError": (error as NSError).localizedDescription] }
    }
    func localURL(_ app: String, seed: Bool) -> URL {
        var parts = URLComponents(string: "moonpool://com.example.probe.\(app)/")!
        parts.queryItems = [URLQueryItem(name: "seed", value: String(seed)), URLQueryItem(name: "run", value: run)]
        return parts.url!
    }
    func checkpoint(_ label: String) {
        try? JSONSerialization.data(withJSONObject: ["stage": label, "samples": samples, "events": events, "identity": identity], options: [.prettyPrinted, .sortedKeys]).write(to: documents.appendingPathComponent("progress.json"), options: .atomic)
    }
    func local(_ label: String, _ web: WKWebView, target: URL?, reload: Bool = false) async {
        let start = messages.count
        let eventStart = events.count
        if reload {
            _ = await js(web, "history.replaceState(null,'','?seed=false&run=\(run)'); true")
            web.reload()
        } else if let target { web.load(URLRequest(url: target)) }
        for _ in 0..<150 {
            if messages.dropFirst(start).contains(where: { ($0["view"] as? String) == names[ObjectIdentifier(web)] && (($0["body"] as? [String: Any])?["kind"] as? String) == "local" }) { break }
            await pause(0.1)
        }
        let freshMessage = messages.dropFirst(start).last(where: { $0["view"] as? String == names[ObjectIdentifier(web)] && (($0["body"] as? [String: Any])?["kind"] as? String) == "local" })
        let text = await js(web, "JSON.stringify(window.t28Report || null)")
        var observation: Any = text
        if let string = text as? String, let data = string.data(using: .utf8), let parsed = try? JSONSerialization.jsonObject(with: data) { observation = parsed }
        samples.append(["label": label, "kind": "local", "url": web.url?.absoluteString ?? "", "storeIdentifier": web.configuration.websiteDataStore.identifier?.uuidString ?? "nil", "observation": observation,
            "observedFreshLocalMessage": freshMessage != nil, "freshNativeMessage": freshMessage ?? [:],
            "loadErrors": Array(events.dropFirst(eventStart).filter { $0["event"] as? String == "load-error" && $0["view"] as? String == names[ObjectIdentifier(web)] })])
        checkpoint(label)
    }
    func cookies(_ store: WKWebsiteDataStore) async -> [[String: Any]] {
        await withCheckedContinuation { continuation in
            store.httpCookieStore.getAllCookies { cookies in
                continuation.resume(returning: cookies.filter { $0.name.hasPrefix("t28_") }.map {
                    ["name": $0.name, "value": $0.value, "domain": $0.domain, "path": $0.path,
                     "secure": $0.isSecure, "sessionOnly": $0.isSessionOnly,
                     "expires": $0.expiresDate?.timeIntervalSince1970 ?? 0]
                })
            }
        }
    }
    func remote(_ label: String, _ web: WKWebView, store: WKWebsiteDataStore, owner: String, seed: Bool) async {
        web.load(URLRequest(url: URL(string: "https://example.com/?moonpool-t28=public-fixture")!))
        var loaded = false
        for _ in 0..<180 {
            let result = await js(web, "JSON.stringify({ready:document.readyState,scheme:location.protocol,host:location.hostname,title:document.title})")
            if let text = result as? String, let data = text.data(using: .utf8), let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               object["scheme"] as? String == "https:", object["host"] as? String == "example.com", object["ready"] as? String == "complete", object["title"] as? String == "Example Domain" { loaded = true; break }
            await pause(0.15)
        }
        let beforeCookie = await js(web, "document.cookie.split('; ').filter(x=>x.startsWith('t28_')).join('; ')")
        let beforeNative = await cookies(store)
        if loaded && seed {
            _ = await js(web, "document.cookie='t28_remote=\(owner)_\(run); Max-Age=86400; Path=/; Secure; SameSite=Lax'; document.cookie='t28_parent=forbidden; Domain=com; Max-Age=86400; Path=/; Secure'; document.cookie='t28_sibling=forbidden; Domain=other.example.com; Max-Age=86400; Path=/; Secure'; true")
        }
        _ = await js(web, "webkit.messageHandlers.observe.postMessage({kind:'https-control',href:location.href,host:location.hostname,title:document.title}); true")
        let observation = await js(web, "JSON.stringify({href:location.href,scheme:location.protocol,host:location.hostname,cookie:document.cookie.split('; ').filter(x=>x.startsWith('t28_')).join('; '),title:document.title,ready:document.readyState})")
        var decoded: Any = observation
        if let string = observation as? String, let data = string.data(using: .utf8), let parsed = try? JSONSerialization.jsonObject(with: data) { decoded = parsed }
        samples.append(["label": label, "kind": "https", "owner": owner, "storeIdentifier": web.configuration.websiteDataStore.identifier?.uuidString ?? "nil", "loaded": loaded, "url": web.url?.absoluteString ?? "",
            "observation": decoded, "beforeCookie": beforeCookie, "beforeNativeCookies": beforeNative, "nativeCookies": await cookies(store)])
        checkpoint(label)
    }
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        stack.axis = .vertical; stack.distribution = .fillEqually; stack.frame = view.bounds
        stack.autoresizingMask = [.flexibleWidth, .flexibleHeight]; view.addSubview(stack)
        Task { await execute() }
    }
    func execute() async {
        try? FileManager.default.removeItem(at: output)
        var report: [String: Any] = ["phase": phase, "run": run, "os": UIDevice.current.systemVersion,
            "storeAPI": "WKWebsiteDataStore(forIdentifier:)", "customCookieStatus": "unavailable; empty is not isolation evidence",
            "remoteHost": "https://example.com", "securityScope": "Public sentinel markers only; no authentication or TLS override"]
        if startup != "none" {
            report["startupControl"] = startup
            report["guestLoads"] = 0
            try! JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: documents.appendingPathComponent("startup-before.json"), options: .atomic)
            var initializer: WKWebView?
            if startup == "initialized" {
                let config = WKWebViewConfiguration()
                config.websiteDataStore = .nonPersistent()
                initializer = WKWebView(frame: .zero, configuration: config)
            }
            let identifiers: [UUID]
            if startup == "cold-callback" {
                identifiers = await withCheckedContinuation { continuation in
                    WKWebsiteDataStore.fetchAllDataStoreIdentifiers { continuation.resume(returning: $0) }
                }
            } else { identifiers = await WKWebsiteDataStore.allDataStoreIdentifiers }
            withExtendedLifetime(initializer) { }
            report["identifiedStores"] = identifiers.map(\.uuidString).sorted()
            report["complete"] = true
            try! JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: output, options: .atomic)
            return
        }
        do {
            guard #available(iOS 17.0, *) else { throw RegistryFailure.unsupported }
            var known = Set(UserDefaults.standard.stringArray(forKey: "knownStoreIDs") ?? [])
            let pinned = (UserDefaults.standard.dictionary(forKey: "pinnedStoreAssignments") as? [String: String] ?? [:]).compactMapValues(UUID.init(uuidString:))
            // Initialize WebKit's main run loop before enumeration; no document is loaded.
            let initializerConfig = WKWebViewConfiguration()
            initializerConfig.websiteDataStore = .nonPersistent()
            let initializer = WKWebView(frame: .zero, configuration: initializerConfig)
            report["enumerationInitialization"] = "Empty nonpersistent WKWebView, never loaded; no guest or default-store fallback"
            let existingIDs = Set(await WKWebsiteDataStore.allDataStoreIdentifiers)
            withExtendedLifetime(initializer) { }
            let registryFile = documents.appendingPathComponent("store-registry.json")
            let registryExists = FileManager.default.fileExists(atPath: registryFile.path)
            try StoreRegistry.requireMetadata(registryExists: registryExists, anchorsExist: !known.isEmpty || !pinned.isEmpty, available: existingIDs)
            if registryExists {
                let persisted = try JSONDecoder().decode([StoreAssignment].self, from: Data(contentsOf: registryFile))
                known.formUnion(persisted.map(\.id))
            }
            report["existingStoreIdentifiersBeforeOpen"] = existingIDs.map(\.uuidString).sorted()
            report["knownStoreAssignmentsBeforeOpen"] = pinned.mapValues(\.uuidString)
            let registry = StoreRegistry(file: documents.appendingPathComponent("store-registry.json"), knownIDs: known, pinned: pinned)
            for app in ["a", "b", "host", "diagnostics"] {
                let id = "com.example.probe.\(app)"
                assignments[app] = try registry.resolve(id, supported: true)
                try StoreRegistry.requireExisting(assignments[app]!, known: known.contains(id), available: existingIDs)
                stores[app] = WKWebsiteDataStore(forIdentifier: assignments[app]!)
            }
            UserDefaults.standard.set(assignments.keys.map { "com.example.probe.\($0)" }, forKey: "knownStoreIDs")
            UserDefaults.standard.set(assignments.reduce(into: [String: String]()) { $0["com.example.probe.\($1.key)"] = $1.value.uuidString }, forKey: "pinnedStoreAssignments")
            report["assignments"] = assignments.mapValues(\.uuidString)
            report["stores"] = stores.mapValues { ["persistent": $0.isPersistent, "identifier": $0.identifier?.uuidString ?? "nil"] as [String: Any] }
            let vectors = try JSONSerialization.jsonObject(with: Data(contentsOf: Bundle.main.bundleURL.appendingPathComponent("Fixtures/identity-vectors.json"))) as! [String: Any]
            for vector in vectors["vectors"] as! [[String: Any]] {
                let id = vector["id"] as! String
                var row: [String: Any] = ["name": vector["name"]!, "id": id, "manifestValid": vector["manifestValid"]!, "urlAdmission": Admission.url(for: id) != nil]
                let candidate = Admission.url(for: id) ?? (["uppercase", "port", "escape"].contains(vector["name"] as! String) ? URL(string: "moonpool://\(id)/") : nil)
                if let target = candidate?.appendingPathComponent("diagnostic.html") {
                    row["diagnosticOnly"] = true
                    let viewName = "diagnostic-\(vector["name"]!)"
                    let diagnostic = make(viewName, store: stores["diagnostics"]!)
                    let start = messages.count
                    diagnostic.load(URLRequest(url: target))
                    for _ in 0..<60 {
                        if messages.dropFirst(start).contains(where: { $0["view"] as? String == viewName && (($0["body"] as? [String: Any])?["kind"] as? String) == "diagnostic" }) { break }; await pause(0.05)
                    }
                    row["nativeURL"] = diagnostic.url?.absoluteString ?? ""
                    if let message = messages.dropFirst(start).first(where: { $0["view"] as? String == viewName && (($0["body"] as? [String: Any])?["kind"] as? String) == "diagnostic" }) {
                        row["message"] = message
                        let origin = message["nativeOrigin"] as! [String: Any]
                        row["measuredAdmission"] = Admission.accepts(id, scheme: origin["scheme"] as! String, host: origin["host"] as! String, port: origin["port"] as! Int)
                    }
                    else { row["loadUnavailable"] = true }
                    discard(diagnostic)
                }
                identity.append(row)
                checkpoint("identity-\(vector["name"]!)")
            }
            for app in ["a", "b"] { views[app] = make(app, store: stores[app]!) }
            for app in ["a", "b"] { await local("initial-\(app)", views[app]!, target: localURL(app, seed: phase == "seed")) }
            let second = make("a-second", store: WKWebsiteDataStore(forIdentifier: assignments["a"]!))
            await local("same-app-second", second, target: localURL("a", seed: false)); discard(second)
            await local("reload-a", views["a"]!, target: nil, reload: true)
            discard(views.removeValue(forKey: "a")!)
            views["a"] = make("a-recreated", store: WKWebsiteDataStore(forIdentifier: assignments["a"]!))
            await local("recreate-a", views["a"]!, target: localURL("a", seed: false))
            let foreign = make("b-under-a-store", store: stores["a"]!)
            await local("b-under-a-store", foreign, target: localURL("b", seed: false)); discard(foreign)
            await local("a-after-origin-control", views["a"]!, target: localURL("a", seed: false))
            for app in ["a", "b", "host"] {
                let web = make("remote-\(app)", store: stores[app]!)
                await remote("https-initial-\(app)", web, store: stores[app]!, owner: app, seed: phase == "seed")
                discard(web)
            }
            for app in ["a", "b", "host"] {
                let store = WKWebsiteDataStore(forIdentifier: assignments[app]!)
                let web = make("remote-recreated-\(app)", store: store)
                await remote("https-recreated-\(app)", web, store: store, owner: app, seed: false)
                discard(web)
            }
            await pause(3)
            report["registry"] = try JSONSerialization.jsonObject(with: Data(contentsOf: documents.appendingPathComponent("store-registry.json")))
        } catch { report["error"] = String(describing: error) }
        report["identity"] = identity; report["messages"] = messages; report["samples"] = samples; report["events"] = events
        report["complete"] = true
        try! JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: output, options: .atomic)
    }
}

@main @MainActor final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let args = ProcessInfo.processInfo.arguments
        func value(_ key: String) -> String { args[args.firstIndex(of: key)! + 1] }
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = Controller(phase: value("--phase"), run: value("--run"), startup: args.contains("--startup-control") ? value("--startup-control") : "none")
        self.window = window; window.makeKeyAndVisible(); return true
    }
}
