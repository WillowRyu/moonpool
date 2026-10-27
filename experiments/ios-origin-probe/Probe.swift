import UIKit
import WebKit

// Research data only. No guest-callable native handler or privileged kernel.
@MainActor
final class SchemeHandler: NSObject, WKURLSchemeHandler {
    var record: (([String: Any]) -> Void)?
    private var pending: [ObjectIdentifier: Int] = [:]
    private var sequence = 0
    var pendingCount: Int { pending.count }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        let key = ObjectIdentifier(task as AnyObject)
        sequence += 1
        let number = sequence
        pending[key] = number
        let url = task.request.url!
        record?(["type": "scheme-start", "task": number, "url": url.absoluteString])
        let delay = url.lastPathComponent == "delayed.html" ? 1.5 : 0.01
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self else { return }
            guard self.pending.removeValue(forKey: key) != nil else {
                self.record?(["type": "scheme-suppressed-after-stop", "task": number])
                return
            }
            let host = url.host ?? ""
            let app = host == "com.example.probe.a" ? "a" : host == "com.example.probe.b" ? "b" : nil
            let path = url.path.removingPercentEncoding ?? url.path
            var status = 404
            var data = Data("Unknown app or outside package".utf8)
            var mime = "text/plain"
            if let app, path.hasPrefix("/assets/") {
                var resource = String(path.dropFirst(8))
                if resource == "second.html" || resource == "delayed.html" { resource = "index.html" }
                if !resource.isEmpty && !resource.contains("..") && !resource.contains("\\") && !resource.hasPrefix("/") {
                    let group = ["probe.js", "style.css", "marker.svg"].contains(resource) ? "common" : "apps/\(app)"
                    let file = Bundle.main.bundleURL.appendingPathComponent("Fixtures/\(group)/\(resource)")
                    if let bytes = try? Data(contentsOf: file) {
                        status = 200
                        data = bytes
                        mime = ["html": "text/html", "js": "text/javascript", "css": "text/css", "svg": "image/svg+xml", "json": "application/json"][file.pathExtension] ?? "application/octet-stream"
                    } else { data = Data("Missing bundled resource".utf8) }
                }
            }
            let response = HTTPURLResponse(url: url, statusCode: status, httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": "\(mime); charset=utf-8", "Cache-Control": "no-store"])!
            task.didReceive(response)
            task.didReceive(data)
            task.didFinish()
            self.record?(["type": "scheme-finished", "task": number, "status": status, "url": url.absoluteString])
        }
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {
        if let number = pending.removeValue(forKey: ObjectIdentifier(task as AnyObject)) {
            record?(["type": "scheme-stop", "task": number, "url": task.request.url?.absoluteString ?? ""])
        }
    }
}

@MainActor
final class ProbeController: UIViewController, WKNavigationDelegate {
    let profile: String
    let phase: String
    let store = WKWebsiteDataStore.default()
    let stack = UIStackView()
    let status = UILabel()
    var views: [String: WKWebView] = [:]
    var labels: [ObjectIdentifier: String] = [:]
    var handlers: [SchemeHandler] = []
    var events: [[String: Any]] = []
    var samples: [[String: Any]] = []
    var steps: [(@escaping () -> Void) -> Void] = []
    var stepIndex = 0
    var report: [String: Any] = [:]
    var output: URL { FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("report.json") }

    init(profile: String, phase: String) {
        self.profile = profile
        self.phase = phase
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { fatalError("Programmatic research app") }

    func base(_ app: String) -> String {
        if profile == "http-control" { return app == "a" ? "http://localhost:8878" : "http://127.0.0.1:8879" }
        return "moonpool://com.example.probe.\(app)"
    }

    func url(_ app: String, _ page: String = "index.html", seed: Bool = false) -> URL {
        var parts = URLComponents(string: "\(base(app))/assets/\(page)")!
        let other = app == "a" ? "b" : "a"
        let unknown = profile == "http-control" ? "http://localhost:8878/unknown-app/data.json" : "moonpool://com.example.probe.unknown/assets/data.json"
        parts.queryItems = [URLQueryItem(name: "profile", value: profile), URLQueryItem(name: "seed", value: String(seed)),
            URLQueryItem(name: "cross", value: "\(base(other))/assets/"), URLQueryItem(name: "unknown", value: unknown)]
        return parts.url!
    }

    func makeView(_ label: String) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = store
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        let handler = SchemeHandler()
        handler.record = { [weak self] value in
            var event = value
            event["view"] = label
            self?.events.append(event)
        }
        handlers.append(handler)
        configuration.setURLSchemeHandler(handler, forURLScheme: "moonpool")
        let web = WKWebView(frame: .zero, configuration: configuration)
        web.navigationDelegate = self
        labels[ObjectIdentifier(web)] = label
        stack.addArrangedSubview(web)
        return web
    }

    func remove(_ web: WKWebView) {
        web.stopLoading()
        web.navigationDelegate = nil
        stack.removeArrangedSubview(web)
        web.removeFromSuperview()
        labels.removeValue(forKey: ObjectIdentifier(web))
    }

    func poll(_ web: WKWebView, remaining: Int = 130, done: @escaping (Any) -> Void) {
        web.evaluateJavaScript("JSON.stringify(window.t24Report || null)") { value, _ in
            if let text = value as? String, let data = text.data(using: .utf8),
               let object = try? JSONSerialization.jsonObject(with: data), object is [String: Any] {
                done(object)
            } else if remaining == 0 {
                done(["unavailable": true, "reason": "No fixture report before deadline", "nativeUrl": web.url?.absoluteString ?? ""])
            } else {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { self.poll(web, remaining: remaining - 1, done: done) }
            }
        }
    }

    func sample(_ label: String, _ web: WKWebView, next: @escaping () -> Void) {
        status.text = "T24 \(profile) / \(phase) / \(label)"
        poll(web) { value in
            self.samples.append(["label": label, "nativeUrl": web.url?.absoluteString ?? "", "observation": value])
            next()
        }
    }

    func load(_ label: String, _ web: WKWebView, _ target: URL, next: @escaping () -> Void) {
        web.evaluateJavaScript("window.t24Report = null") { _, _ in
            web.load(URLRequest(url: target))
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { self.sample(label, web, next: next) }
        }
    }

    func recollect(_ label: String, _ web: WKWebView, next: @escaping () -> Void) {
        web.evaluateJavaScript("window.t24Report = null; void window.t24Collect(false)") { _, _ in self.sample(label, web, next: next) }
    }

    func next() {
        if stepIndex < steps.count {
            let step = steps[stepIndex]
            stepIndex += 1
            step { self.next() }
            return
        }
        store.fetchDataRecords(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes()) { records in
            self.report["websiteDataRecords"] = records.map { ["name": $0.displayName, "types": Array($0.dataTypes).sorted()] }
            self.report["samples"] = self.samples
            self.report["events"] = self.events
            self.report["pendingSchemeTasks"] = self.handlers.reduce(0) { $0 + $1.pendingCount }
            self.report["complete"] = true
            do {
                let data = try JSONSerialization.data(withJSONObject: self.report, options: [.prettyPrinted, .sortedKeys])
                try data.write(to: self.output, options: .atomic)
                self.status.text = "T24 \(self.profile) / \(self.phase) complete — \(self.samples.count) observations"
            } catch { self.status.text = "Report write failed" }
        }
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        try? FileManager.default.removeItem(at: output)
        view.backgroundColor = .systemBackground
        stack.axis = .vertical
        stack.distribution = .fillEqually
        stack.translatesAutoresizingMaskIntoConstraints = false
        status.numberOfLines = 3
        status.font = .systemFont(ofSize: 15)
        stack.addArrangedSubview(status)
        view.addSubview(stack)
        NSLayoutConstraint.activate([stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            stack.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 8),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -8)])
        report = ["profile": profile, "phase": phase, "os": UIDevice.current.systemVersion,
            "dataStore": "default persistent store shared by A/B", "dataStorePersistent": store.isPersistent,
            "webkitHandlesMoonpool": WKWebView.handlesURLScheme("moonpool"), "webkitHandlesHTTPS": WKWebView.handlesURLScheme("https")]
        views["a"] = makeView("a")
        views["b"] = makeView("b")
        let seed = phase == "seed"
        steps.append { next in self.load("initial-a", self.views["a"]!, self.url("a", seed: seed), next: next) }
        steps.append { next in self.load("initial-b", self.views["b"]!, self.url("b", seed: seed), next: next) }
        steps.append { next in self.recollect("a-after-b", self.views["a"]!, next: next) }
        steps.append { next in self.recollect("b-after-a", self.views["b"]!, next: next) }
        steps.append { next in
            let second = self.makeView("a-second-instance")
            self.load("same-app-second-instance", second, self.url("a")) { self.remove(second); next() }
        }
        steps.append { next in
            let a = self.views["a"]!
            a.evaluateJavaScript("window.t24Report = null") { _, _ in
                a.reload()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { self.sample("reload-a", a, next: next) }
            }
        }
        steps.append { next in
            self.remove(self.views.removeValue(forKey: "a")!)
            let a = self.makeView("a-recreated")
            self.views["a"] = a
            self.load("recreate-a", a, self.url("a"), next: next)
        }
        steps.append { next in self.load("same-app-navigation", self.views["a"]!, self.url("a", "second.html"), next: next) }
        steps.append { next in self.load("foreign-app-navigation", self.views["a"]!, self.url("b"), next: next) }
        steps.append { next in self.load("external-navigation", self.views["a"]!, URL(string: "http://127.0.0.1:8877/external")!, next: next) }
        steps.append { next in self.load("return-to-a", self.views["a"]!, self.url("a"), next: next) }
        if profile == "custom-scheme" {
            steps.append { next in
                let cancel = self.makeView("cancelled-resource")
                cancel.load(URLRequest(url: self.url("a", "delayed.html")))
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { self.remove(cancel) }
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.9) { next() }
            }
        }
        next()
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let origin = action.sourceFrame.securityOrigin
        let url = action.request.url
        let allowed = url?.scheme == "moonpool" || ["localhost", "127.0.0.1"].contains(url?.host ?? "") || url?.scheme == "about"
        events.append(["type": "navigation", "view": labels[ObjectIdentifier(webView)] ?? "retired", "url": url?.absoluteString ?? "",
            "sourceFrame": ["protocol": origin.protocol, "host": origin.host, "port": origin.port, "mainFrame": action.sourceFrame.isMainFrame],
            "targetMainFrame": action.targetFrame?.isMainFrame ?? false, "allowed": allowed])
        decisionHandler(allowed ? .allow : .cancel)
    }
    func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
        events.append(["type": "committed", "view": labels[ObjectIdentifier(webView)] ?? "retired", "url": webView.url?.absoluteString ?? ""])
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        events.append(["type": "finished", "view": labels[ObjectIdentifier(webView)] ?? "retired", "url": webView.url?.absoluteString ?? ""])
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { failure(webView, error) }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { failure(webView, error) }
    func failure(_ web: WKWebView, _ error: Error) {
        let value = error as NSError
        events.append(["type": "load-error", "view": labels[ObjectIdentifier(web)] ?? "retired", "url": web.url?.absoluteString ?? "",
            "domain": value.domain, "code": value.code, "message": value.localizedDescription])
    }
}

@main
@MainActor
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let args = ProcessInfo.processInfo.arguments
        func argument(_ name: String) -> String {
            guard let index = args.firstIndex(of: name), index + 1 < args.count else { fatalError("Missing probe argument") }
            return args[index + 1]
        }
        let profile = argument("--profile")
        let phase = argument("--phase")
        precondition(["custom-scheme", "http-control"].contains(profile) && ["seed", "restart"].contains(phase))
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = ProbeController(profile: profile, phase: phase)
        self.window = window
        window.makeKeyAndVisible()
        return true
    }
}
