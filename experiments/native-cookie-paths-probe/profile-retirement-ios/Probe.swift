import UIKit
import WebKit

@MainActor private final class FixturePage: NSObject, WKURLSchemeHandler {
    private let url: URL
    private let html: String
    private let served: () -> Void

    init(url: URL, html: String, served: @escaping () -> Void) {
        self.url = url
        self.html = html
        self.served = served
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard task.request.url == url, task.request.httpMethod == "GET",
              let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil,
                                              headerFields: ["Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"])
        else {
            task.didFailWithError(URLError(.unsupportedURL))
            return
        }
        served()
        task.didReceive(response)
        task.didReceive(Data(html.utf8))
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}

@MainActor private final class Partition {
    let store: WKWebsiteDataStore
    let id: String
    let origin: String
    let marker: String
    let gate: AdmissionGate
    var portals: [Portal] = []

    init(store: WKWebsiteDataStore, id: String, origin: String, marker: String, gate: AdmissionGate) {
        self.store = store
        self.id = id
        self.origin = origin
        self.marker = marker
        self.gate = gate
    }
}

@MainActor private final class Portal {
    let name: String
    unowned let partition: Partition
    var handle: AdmissionGate.Handle?
    var web: WKWebView?
    weak var formerWebView: WKWebView?
    var loads = 0
    var retireCalls = 0
    var released = false
    var groupInactiveAtRelease = false

    init(name: String, partition: Partition) {
        self.name = name
        self.partition = partition
    }

    var liveView: WKWebView? { handle?.live == true ? web : nil }

    var state: [String: Any] {
        ["live": handle?.live == true, "loads": loads, "retireCalls": retireCalls,
         "released": released, "attached": web?.window != nil, "groupInactiveAtRelease": groupInactiveAtRelease]
    }
}

private struct FixtureError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}

@MainActor private final class RetirementController: UIViewController {
    private let run: String
    private let policy = "default-src 'none'; script-src 'unsafe-inline'; worker-src 'none'; base-uri 'none'"
    private var storeScript = ""
    private var guestScript = ""
    private var events: [String] = []
    private var loader: [String] = []
    private var inspections: [String: [String: Bool]] = [:]

    init(run: String) {
        self.run = run
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { return nil }

    private var cookieDomain: String { "mp-\(run)-a.invalid" }

    private func inspect(_ store: WKWebsiteDataStore) async -> [String: Bool] {
        await withCheckedContinuation { resume in
            store.httpCookieStore.setCookiePolicy(.disallow) { resume.resume() }
        }
        let denied: Bool = await withCheckedContinuation { resume in
            store.httpCookieStore.getCookiePolicy { resume.resume(returning: $0 == .disallow) }
        }
        let records: Bool = await withCheckedContinuation { resume in
            store.fetchDataRecords(ofTypes: [WKWebsiteDataTypeCookies]) { resume.resume(returning: !$0.isEmpty) }
        }
        let cookies: [HTTPCookie] = await withCheckedContinuation { resume in
            store.httpCookieStore.getAllCookies { resume.resume(returning: $0) }
        }
        let fixture = cookies.contains {
            $0.name == "mp_retirement" && $0.value == "fixture" && $0.domain == cookieDomain && $0.path == "/"
        }
        return ["policyDisallowed": denied, "records": records, "cookies": !cookies.isEmpty, "fixturePresent": fixture]
    }

    private func makePartition(_ key: String) throws -> Partition {
        let id = UUID()
        let store = WKWebsiteDataStore(forIdentifier: id)
        guard store.identifier == id, store.isPersistent else {
            throw FixtureError("Unexpected website data store")
        }
        let gate = AdmissionGate { [weak self] name, complete in
            self?.events.append("\(name):inspect")
            Task { @MainActor in
                guard let self else { complete(.unknown); return }
                let state = await self.inspect(store)
                self.inspections[name] = state
                let presence = cookiePresence(state)
                self.events.append("\(name):\(presence)")
                complete(presence)
            }
        }
        return Partition(store: store, id: id.uuidString, origin: "moonpool://com.example.retirement.\(run).\(key)",
                         marker: "\(run)-\(key)", gate: gate)
    }

    private func quote(_ value: String) throws -> String {
        String(decoding: try JSONEncoder().encode(value), as: UTF8.self)
    }

    private func makeView(_ partition: Partition, url: URL, script: String, served: @escaping () -> Void) throws -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = partition.store
        let html = """
        <!doctype html><meta charset="utf-8"><title>Retirement fixture</title>
        <meta http-equiv="Content-Security-Policy" content="\(policy)">
        <script>\(storeScript)
        \(script)</script><body>
        """
        config.setURLSchemeHandler(FixturePage(url: url, html: html, served: served), forURLScheme: "moonpool")
        let web = WKWebView(frame: view.bounds, configuration: config)
        guard web.configuration.websiteDataStore.identifier?.uuidString == partition.id else {
            throw FixtureError("Unexpected WebView binding")
        }
        view.addSubview(web)
        return web
    }

    private func open(_ portal: Portal, seed: Bool) throws {
        let partition = portal.partition
        let name = portal.name
        let marker = seed ? try quote(partition.marker) : "undefined"
        let url = URL(string: "\(partition.origin)/\(name)")!
        let script = "window.retirementConfig = { name: \(try quote(name)), marker: \(marker) };\n\(guestScript)"
        let web = try makeView(partition, url: url, script: script) { [weak self] in self?.loader.append(name) }
        portal.web = web
        portal.loads += 1
        events.append("\(name):load")
        web.load(URLRequest(url: url))
    }

    private func retire(_ portal: Portal) {
        portal.retireCalls += 1
        guard let web = portal.web else {
            events.append("\(portal.name):refuse")
            return
        }
        portal.groupInactiveAtRelease = portal.partition.portals.allSatisfy { $0.handle?.live != true }
        web.stopLoading()
        web.removeFromSuperview()
        portal.formerWebView = web
        portal.web = nil
        portal.released = web.superview == nil
        events.append("\(portal.name):release")
    }

    private func admit(_ partition: Partition, _ name: String, seed: Bool = false) -> Portal {
        let portal = Portal(name: name, partition: partition)
        partition.portals.append(portal)
        portal.handle = partition.gate.admit(name, load: { [weak self, weak portal] in
            guard let self, let portal else { throw FixtureError("The fixture owner is inactive") }
            try self.open(portal, seed: seed)
        }, retire: { [weak self, weak portal] in
            guard let self, let portal else { return }
            self.retire(portal)
        })
        return portal
    }

    private func awaitDecision(_ portal: Portal) async throws {
        for _ in 0..<150 {
            if let handle = portal.handle, handle.completed || !handle.live { return }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw FixtureError("Admission did not settle for \(portal.name)")
    }

    private func observe(_ view: WKWebView, expression: String) async throws -> [String: Any] {
        for _ in 0..<160 {
            if let message = try? await view.evaluateJavaScript(expression),
               let text = message as? String,
               let object = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] {
                return object
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw FixtureError("The fixture document did not report")
    }

    private func guestObservation(_ portal: Portal) async throws -> [String: Any] {
        guard let web = portal.liveView else { throw FixtureError("Inactive fixture view \(portal.name)") }
        return try await observe(web, expression: "JSON.stringify(window.retirementFixture && "
            + "{...window.retirementFixture, pulse: ++window.retirementFixture.pulse})")
    }

    private func initial(_ portal: Portal) async throws -> [String: Any] {
        try await awaitDecision(portal)
        let document = try await guestObservation(portal)
        guard let identifier = portal.liveView?.configuration.websiteDataStore.identifier else {
            throw FixtureError("Missing initial view binding")
        }
        return ["state": portal.state, "document": document, "store": identifier.uuidString]
    }

    private func writeCookie(_ partition: Partition) async throws -> [String: Any] {
        guard let cookie = HTTPCookie(properties: [
            .domain: cookieDomain, .path: "/", .name: "mp_retirement", .value: "fixture", .secure: "TRUE",
        ]) else { throw FixtureError("Could not create the public fixture cookie") }
        await withCheckedContinuation { resume in
            partition.store.httpCookieStore.setCookie(cookie) { resume.resume() }
        }
        events.append("a:write-complete")
        return ["completed": true, "name": cookie.name, "value": cookie.value]
    }

    private func preservedA(_ partition: Partition) async throws -> [String: Any] {
        let nonce = UUID().uuidString
        let script = """
        (async () => { window.hostMarker = {
            nonce: \(try quote(nonce)), origin: window.origin, marker: await window.workerAdmissionData()
        }; })();
        """
        let url = URL(string: "\(partition.origin)/host-marker")!
        var receipts = 0
        let web = try makeView(partition, url: url, script: script) { receipts += 1 }
        defer {
            web.stopLoading()
            web.removeFromSuperview()
        }
        web.load(URLRequest(url: url))
        let marker = try await observe(web, expression: "JSON.stringify(window.hostMarker || null)")
        guard let identifier = web.configuration.websiteDataStore.identifier else {
            throw FixtureError("Missing original store on the host witness")
        }
        return ["store": identifier.uuidString, "origin": marker["origin"] ?? NSNull(),
                "marker": marker["marker"] ?? NSNull(), "nonceMatched": marker["nonce"] as? String == nonce,
                "hostReceipts": receipts, "cookieState": await inspect(partition.store)]
    }

    private func measure(_ report: inout [String: Any]) async throws {
        let a = try makePartition("a")
        let b = try makePartition("b")
        defer { a.gate.close(); b.gate.close() }
        report["stores"] = ["a": ["id": a.id, "origin": a.origin], "b": ["id": b.id, "origin": b.origin]]
        let a1 = admit(a, "a1", seed: true)
        let first = try await initial(a1)
        let a2 = admit(a, "a2")
        let second = try await initial(a2)
        let b1 = admit(b, "b1", seed: true)
        let separate = try await initial(b1)
        report["initial"] = ["a1": first, "a2": second, "b1": separate]
        report["writer"] = try await writeCookie(a)
        let a3 = admit(a, "a3")
        report["pending"] = ["a3": a3.state, "a1": a1.state, "a2": a2.state]
        events.append("a3:pending")
        try await awaitDecision(a3)
        let a4 = admit(a, "a4")
        report["states"] = ["a1": a1.state, "a2": a2.state, "a3": a3.state, "a4": a4.state, "b1": b1.state]
        report["retiredAccess"] = ["a1": a1.liveView != nil, "a2": a2.liveView != nil]
        report["continuedB"] = try await guestObservation(b1)
        report["bPolicy"] = await inspect(b.store)
        report["preservedA"] = try await preservedA(a)
        report["weakReferencesCleared"] = ["a1": a1.formerWebView == nil, "a2": a2.formerWebView == nil]
        report["inspections"] = inspections
        report["events"] = events
        report["loader"] = loader
    }

    func runProbe() async {
        var report: [String: Any] = [
            "run": run, "release": UIDevice.current.systemVersion, "pid": Int(ProcessInfo.processInfo.processIdentifier),
            "platform": "ios", "complete": false,
        ]
        // Initialize WebKit with a never-loaded view before identified stores or cookie operations.
        let warmup = WKWebViewConfiguration()
        warmup.websiteDataStore = .nonPersistent()
        let initializer = WKWebView(frame: .zero, configuration: warmup)
        defer { withExtendedLifetime(initializer) {} }
        report["initializedWebKit"] = true
        do {
            guard run.range(of: "^[a-z0-9-]{1,28}$", options: .regularExpression) != nil else {
                throw FixtureError("Invalid run tag")
            }
            let assets = Bundle.main.bundleURL.appendingPathComponent("Fixtures")
            storeScript = try String(contentsOf: assets.appendingPathComponent("store.js"), encoding: .utf8)
            guestScript = try String(contentsOf: assets.appendingPathComponent("guest.js"), encoding: .utf8)
            try await measure(&report)
            report["complete"] = true
        } catch {
            report["error"] = error.localizedDescription
        }
        let output = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("report.json")
        if let bytes = try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]) {
            try? bytes.write(to: output, options: .atomic)
        }
    }
}

@main @MainActor final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let args = ProcessInfo.processInfo.arguments
        let run = args.firstIndex(of: "--run").flatMap { args.dropFirst($0 + 1).first } ?? ""
        let controller = RetirementController(run: run)
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = controller
        self.window = window
        window.makeKeyAndVisible()
        Task { await controller.runProbe() }
        return true
    }
}
