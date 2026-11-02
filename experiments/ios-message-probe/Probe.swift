import UIKit
import WebKit

@MainActor
final class Assets: NSObject, WKURLSchemeHandler {
    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url else { return }
        let allowedHost = ["com.example.probe.a", "com.example.probe.b"].contains(url.host ?? "")
        let allowedPath = ["/assets/index.html", "/assets/probe.js"].contains(url.path)
        let file = Bundle.main.bundleURL.appendingPathComponent("Fixtures/\(url.lastPathComponent)")
        let bytes = allowedHost && allowedPath ? try? Data(contentsOf: file) : nil
        let response = HTTPURLResponse(url: url, statusCode: bytes == nil ? 404 : 200,
            httpVersion: "HTTP/1.1", headerFields: ["Content-Type": url.path.hasSuffix(".js") ? "text/javascript; charset=utf-8" : "text/html; charset=utf-8", "Cache-Control": "no-store"])!
        task.didReceive(response)
        task.didReceive(bytes ?? Data("Missing public fixture".utf8))
        task.didFinish()
    }
    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}

@MainActor
final class ReplyHandler: NSObject, WKScriptMessageHandlerWithReply {
    weak var owner: MessageController?
    weak var slot: MessageSlot?
    let world: WKContentWorld
    init(owner: MessageController, slot: MessageSlot, world: WKContentWorld) {
        self.owner = owner; self.slot = slot; self.world = world
    }
    func userContentController(_ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage, replyHandler: @escaping (Any?, String?) -> Void) {
        guard let owner, let slot else { replyHandler(nil, "retired"); return }
        owner.receive(slot, message, expectedWorld: world, reply: replyHandler)
    }
}

@MainActor
final class HeldReply {
    let reply: (Any?, String?) -> Void
    let doc: String
    let instance: String
    let frame: WKFrameInfo
    var completed = false
    init(reply: @escaping (Any?, String?) -> Void, doc: String, instance: String, frame: WKFrameInfo) {
        self.reply = reply; self.doc = doc; self.instance = instance; self.frame = frame
    }
    func complete(_ marker: String, error: String? = nil) {
        guard !completed else { return }
        completed = true
        reply(["marker": marker, "sourceDoc": doc, "sourceInstance": instance, "id": 2], error)
    }
}

@MainActor
final class MessageSlot {
    let name: String
    let app: String
    let expected: ProbeOrigin
    let world = WKContentWorld.world(name: "MoonpoolT26")
    var web: WKWebView!
    var handlers: [ReplyHandler] = []
    var active = true
    var pageFinished = false
    var readyCount = 0
    var held: HeldReply?
    var lastFrame: WKFrameInfo?
    var lastOrigin: ProbeOrigin?
    var lastSender: WKWebView?

    init(_ owner: MessageController, name: String, app: String) {
        self.name = name; self.app = app
        expected = ProbeOrigin(scheme: "moonpool", host: "com.example.probe.\(app)", port: 0)
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        config.setURLSchemeHandler(Assets(), forURLScheme: "moonpool")
        for (name, world) in [("t26Page", WKContentWorld.page), ("t26Isolated", world)] {
            let handler = ReplyHandler(owner: owner, slot: self, world: world)
            handlers.append(handler)
            config.userContentController.addScriptMessageHandler(handler, contentWorld: world, name: name)
        }
        let file = Bundle.main.bundleURL.appendingPathComponent("Fixtures/isolated.js")
        let script = try! String(contentsOf: file, encoding: .utf8)
        config.userContentController.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentStart,
            forMainFrameOnly: owner.profile == "main-only", in: world))
        web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = owner
        owner.labels[ObjectIdentifier(web)] = name
        owner.stack.addArrangedSubview(web)
    }
}

@MainActor
final class MessageController: UIViewController, WKNavigationDelegate {
    let profile: String
    let run: String
    let stack = UIStackView()
    let status = UILabel()
    var labels: [ObjectIdentifier: String] = [:]
    var slots: [MessageSlot] = []
    var events: [[String: Any]] = []
    var samples: [[String: Any]] = []
    var steps: [(@escaping () -> Void) -> Void] = []
    var heldReplies: [HeldReply] = []
    var stepIndex = 0
    var old: HeldReply?
    var a: MessageSlot { slots[0] }
    var b: MessageSlot { slots[1] }
    var c: MessageSlot { slots[2] }
    var output: URL { FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("report.json") }

    init(profile: String, run: String) { self.profile = profile; self.run = run; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { fatalError("Programmatic research app") }

    func event(_ type: String, _ fields: [String: Any] = [:]) {
        var value = fields; value["type"] = type; value["sequence"] = events.count + 1
        events.append(value)
    }
    func origin(_ app: String) -> String { "moonpool://com.example.probe.\(app)" }
    func url(_ app: String, doc: String) -> URL {
        var parts = URLComponents(string: "\(origin(app))/assets/index.html")!
        parts.queryItems = [URLQueryItem(name: "doc", value: doc), URLQueryItem(name: "self", value: origin(app)),
            URLQueryItem(name: "other", value: origin(app == "a" ? "b" : "a"))]
        return parts.url!
    }
    func nativeOrigin(_ frame: WKFrameInfo) -> ProbeOrigin {
        let value = frame.securityOrigin
        return ProbeOrigin(scheme: value.protocol, host: value.host, port: value.port)
    }
    func originData(_ origin: ProbeOrigin) -> [String: Any] { ["scheme": origin.scheme, "host": origin.host, "port": origin.port] }

    func receive(_ slot: MessageSlot, _ message: WKScriptMessage, expectedWorld: WKContentWorld,
                 reply: @escaping (Any?, String?) -> Void) {
        let data = message.body as? [String: Any] ?? [:]
        let kind = data["kind"] as? String ?? "invalid"
        let actual = nativeOrigin(message.frameInfo)
        let world = message.world.name ?? "page"
        let expectedName = expectedWorld.name ?? "page"
        let decision = Admission.reason(owner: slot.web, sender: message.webView, expected: slot.expected,
            actual: actual, mainFrame: message.frameInfo.isMainFrame, expectedWorld: expectedName,
            actualWorld: world, active: slot.active)
        event("message", ["view": slot.name, "handler": message.name, "world": world,
            "expectedWorld": expectedName, "origin": originData(actual), "mainFrame": message.frameInfo.isMainFrame,
            "webViewMatches": message.webView === slot.web, "kind": kind, "decision": decision,
            "doc": data["doc"] as? String ?? "", "instance": data["instance"] as? String ?? "",
            "claimedOrigin": data["claimedOrigin"] as? String ?? "", "claimedMainFrame": data["claimedMainFrame"] as? Bool ?? false,
            "beforePageFinished": !slot.pageFinished, "readyState": data["readyState"] as? String ?? ""])
        if message.name == "t26Page" && message.frameInfo.isMainFrame {
            slot.lastFrame = message.frameInfo; slot.lastOrigin = actual; slot.lastSender = message.webView
            if kind == "ready" { slot.readyCount += 1 }
        }
        guard decision == "accepted" else { reply(nil, "denied:\(decision)"); return }
        if kind == "hold" {
            let held = HeldReply(reply: reply, doc: data["doc"] as? String ?? "", instance: data["instance"] as? String ?? "", frame: message.frameInfo)
            heldReplies.append(held); slot.held = held
            event("reply-held", ["view": slot.name, "doc": held.doc, "instance": held.instance, "id": data["id"] ?? NSNull()])
            return
        }
        reply(["marker": "immediate:\(kind)", "sourceDoc": data["doc"] as? String ?? "", "world": world], nil)
    }

    func snapshot(_ label: String, _ slot: MessageSlot, remaining: Int = 130,
                  condition: @escaping ([String: Any]) -> Bool = { $0["ready"] as? Bool == true }, done: @escaping () -> Void) {
        status.text = "T26 \(profile) / \(run) / \(label)"
        slot.web.evaluateJavaScript("JSON.stringify(window.t26Collect ? window.t26Collect() : null)") { value, _ in
            if let text = value as? String, let bytes = text.data(using: .utf8),
               let data = (try? JSONSerialization.jsonObject(with: bytes)) as? [String: Any], condition(data) {
                self.samples.append(["label": label, "view": slot.name, "observation": data]); done()
            } else if remaining == 0 {
                self.samples.append(["label": label, "view": slot.name, "unavailable": true]); done()
            } else {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                    self.snapshot(label, slot, remaining: remaining - 1, condition: condition, done: done)
                }
            }
        }
    }

    func load(_ label: String, _ slot: MessageSlot, app: String, doc: String, reload: Bool = false, done: @escaping () -> Void) {
        let before = slot.readyCount
        slot.pageFinished = false; slot.held = nil
        slot.web.evaluateJavaScript("window.t26Collect = null") { _, _ in
            if reload { slot.web.reload() } else { slot.web.load(URLRequest(url: self.url(app, doc: doc))) }
            self.snapshot(label, slot, condition: { data in
                let replies = data["replies"] as? [[String: Any]] ?? []
                let rejected = data["rejected"] as? [[String: Any]] ?? []
                return data["doc"] as? String == doc && data["ready"] as? Bool == true
                    && (data["frames"] as? [Any])?.count == 2 && slot.readyCount > before
                    && (!replies.isEmpty || !rejected.isEmpty) && data["sharedDOMMarker"] as? String == "shared-dom-marker"
            }, done: done)
        }
    }

    func completeOld(_ label: String, done: @escaping () -> Void) {
        old?.complete("old:\(label)")
        event("old-reply-called", ["label": label, "doc": old?.doc ?? "missing", "instance": old?.instance ?? "missing"])
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { self.snapshot(label, self.a, done: done) }
    }

    func legacy(_ label: String, done: @escaping () -> Void) {
        let value: [String: Any] = ["id": 2, "marker": "old:\(label)", "sourceDoc": old?.doc ?? "missing"]
        let data = try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        let script = "window.t26ReceiveLegacy(\(String(data: data, encoding: .utf8)!))"
        event("legacy-eval-attempt", ["label": label, "sourceDoc": old?.doc ?? "missing"])
        a.web.evaluateJavaScript(script) { result, error in
            self.event("legacy-eval-result", ["label": label, "success": error == nil, "result": result ?? NSNull()])
            self.snapshot(label, self.a, done: done)
        }
    }

    func frameEval(_ label: String, frame: WKFrameInfo?, done: @escaping () -> Void) {
        let value: [String: Any] = ["id": 999, "marker": "frame:\(label)"]
        event("frame-eval-attempt", ["label": label, "capturedURL": frame?.request.url?.absoluteString ?? "nil"])
        a.web.callAsyncJavaScript("return window.t26ReceiveLegacy(data)", arguments: ["data": value], in: frame, in: .page) { result in
            switch result {
            case .success(let value): self.event("frame-eval-result", ["label": label, "success": true, "result": value])
            case .failure(let error):
                let error = error as NSError
                self.event("frame-eval-result", ["label": label, "success": false, "domain": error.domain, "code": error.code])
            }
            self.snapshot(label, self.a, done: done)
        }
    }

    func currentReply(_ label: String, done: @escaping () -> Void) {
        a.held?.complete("current:\(label)")
        event("current-reply-called", ["label": label])
        snapshot(label, a, condition: { ($0["heldResults"] as? [Any])?.count == 1 }, done: done)
    }

    func next() {
        if stepIndex < steps.count {
            let step = steps[stepIndex]; stepIndex += 1; step { self.next() }; return
        }
        for held in heldReplies where !held.completed { held.complete("probe-finished", error: "probe-finished") }
        let report: [String: Any] = ["profile": profile, "run": run, "os": UIDevice.current.systemVersion,
            "samples": samples, "events": events, "complete": true, "heldCompletionsCalled": heldReplies.allSatisfy { $0.completed }]
        do {
            let bytes = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
            try bytes.write(to: output, options: .atomic)
            status.text = "T26 \(profile)/\(run) complete: \(samples.count) snapshots"
        } catch { status.text = "Report write failed" }
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        try? FileManager.default.removeItem(at: output)
        view.backgroundColor = .systemBackground
        stack.axis = .vertical; stack.distribution = .fillEqually; stack.translatesAutoresizingMaskIntoConstraints = false
        status.numberOfLines = 2; status.font = .systemFont(ofSize: 15); stack.addArrangedSubview(status)
        view.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 8),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -8),
            stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor), stack.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor)])
        slots = [MessageSlot(self, name: "a", app: "a"), MessageSlot(self, name: "b", app: "b"), MessageSlot(self, name: "same-origin-other-view", app: "a")]
        steps.append { self.load("initial-a", self.a, app: "a", doc: "a1", done: $0) }
        steps.append { self.load("initial-b", self.b, app: "b", doc: "b1", done: $0) }
        steps.append { self.load("same-origin-other-view", self.c, app: "a", doc: "c1", done: $0) }
        steps.append { done in
            self.event("host-route-replay", ["sourceView": self.c.name, "targetView": self.a.name,
                "decision": Admission.reason(owner: self.a.web, sender: self.c.lastSender, expected: self.a.expected,
                    actual: self.c.lastOrigin!, mainFrame: true, expectedWorld: "page", actualWorld: "page", active: true)])
            self.frameEval("current-frame-positive", frame: self.a.lastFrame, done: done)
        }
        steps.append { done in
            self.a.web.evaluateJavaScript("JSON.stringify({value:window.__t26WorldValue,replies:window.__t26IsolatedReplies,doc:new URLSearchParams(location.search).get('doc')})", in: nil, in: self.a.world) { result in
                switch result {
                case .success(let value): self.event("world-eval", ["success": true, "value": value])
                case .failure(let error): self.event("world-eval", ["success": false, "code": (error as NSError).code])
                }
                self.snapshot("isolated-world", self.a, done: done)
            }
        }
        steps.append { done in self.old = self.a.held; self.load("same-origin-replacement", self.a, app: "a", doc: "a2", done: done) }
        steps.append { self.completeOld("old-reply-replacement", done: $0) }
        steps.append { self.legacy("legacy-global-replacement", done: $0) }
        steps.append { self.frameEval("stale-frame-replacement", frame: self.old?.frame, done: $0) }
        steps.append { self.currentReply("replacement-positive", done: $0) }
        steps.append { done in
            self.a.web.evaluateJavaScript("window.t26Hold()") { _, _ in
                self.snapshot("prepare-reload", self.a, condition: { _ in self.a.held?.completed == false }) {
                    self.old = self.a.held
                    self.load("same-url-reload", self.a, app: "a", doc: "a2", reload: true, done: done)
                }
            }
        }
        steps.append { self.completeOld("old-reply-reload", done: $0) }
        steps.append { self.legacy("legacy-global-reload", done: $0) }
        steps.append { self.frameEval("stale-frame-reload", frame: self.old?.frame, done: $0) }
        steps.append { self.currentReply("reload-positive", done: $0) }
        steps.append { self.load("foreign-navigation", self.a, app: "b", doc: "a-foreign", done: $0) }
        steps.append { self.load("return-navigation", self.a, app: "a", doc: "a-return", done: $0) }
        steps.append { done in
            self.a.active = false
            self.a.web.evaluateJavaScript("void window.t26Send('after-retire')") { _, _ in
                self.snapshot("retired-binding", self.a, condition: { data in
                    (data["rejected"] as? [[String: Any]])?.contains { $0["kind"] as? String == "after-retire" } == true
                }, done: done)
            }
        }
        steps.append { done in
            self.a.web.configuration.userContentController.removeScriptMessageHandler(forName: "t26Page", contentWorld: .page)
            self.a.web.configuration.userContentController.removeScriptMessageHandler(forName: "t26Isolated", contentWorld: self.a.world)
            self.event("handlers-removed", ["view": self.a.name])
            self.a.web.evaluateJavaScript("window.t26TryRemoved()") { _, _ in
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { self.snapshot("removed-reference", self.a, done: done) }
            }
        }
        next()
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        slots.first { $0.web === webView }?.pageFinished = true
        event("page-finished", ["view": labels[ObjectIdentifier(webView)] ?? "retired", "url": webView.url?.absoluteString ?? ""])
    }
    func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
        event("page-commit", ["view": labels[ObjectIdentifier(webView)] ?? "retired", "url": webView.url?.absoluteString ?? ""])
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let url = action.request.url
        let allowed = url?.scheme == "moonpool" && ["com.example.probe.a", "com.example.probe.b"].contains(url?.host ?? "") || url?.scheme == "about"
        event("navigation", ["view": labels[ObjectIdentifier(webView)] ?? "retired", "url": url?.absoluteString ?? "", "allowed": allowed])
        decisionHandler(allowed ? .allow : .cancel)
    }
}

@main
@MainActor
final class MessageApp: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let args = ProcessInfo.processInfo.arguments
        func argument(_ name: String) -> String { args[args.firstIndex(of: name)! + 1] }
        let profile = argument("--profile"); let run = argument("--run")
        precondition(["all-frames", "main-only"].contains(profile) && ["first", "repeat"].contains(run))
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = MessageController(profile: profile, run: run)
        self.window = window; window.makeKeyAndVisible(); return true
    }
}
