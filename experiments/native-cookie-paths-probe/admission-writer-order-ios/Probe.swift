import UIKit
import WebKit

private struct FixtureError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}

@MainActor private final class FixturePage: NSObject, WKURLSchemeHandler {
    private let url: URL
    private let body: String
    private let served: () -> Void

    init(url: URL, body: String, served: @escaping () -> Void) {
        self.url = url
        self.body = body
        self.served = served
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        let headers = ["Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"]
        guard task.request.url == url, task.request.httpMethod == "GET",
              let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: headers)
        else {
            task.didFailWithError(URLError(.unsupportedURL))
            return
        }
        served()
        task.didReceive(response)
        task.didReceive(Data(body.utf8))
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}

@MainActor private final class Trial {
    private let id = UUID()
    private let target: UIView
    private let origin: String
    private let marker: String
    private let cookieDomain: String
    private let pauseAfterInspection: Bool
    private let store: WKWebsiteDataStore
    private let operations = StoreOperations()
    private var events: [String] = []
    private var resumeInspection: (() -> Void)?
    private var finishAdmission: (() -> Void)?
    private var handle: AdmissionGate.Handle?
    private var inspection: [String: Bool]?
    private var writeEvidence: [String: Bool]?
    private var writerResult = "pending"
    private var writerCallbackCompleted = false
    private var writerStarts = 0
    private var guestLoads = 0
    private var loader = 0
    private var web: WKWebView?

    private lazy var gate = AdmissionGate { [weak self] _, complete in
        self?.events.append("inspection:start")
        Task { @MainActor in
            guard let self else { complete(.unknown); return }
            let evidence = await self.prepareInspection()
            self.inspection = evidence
            let presence = cookiePresence(evidence)
            self.events.append("inspection:\(presence)")
            if self.pauseAfterInspection {
                self.resumeInspection = { complete(presence) }
            } else {
                complete(presence)
            }
        }
    }

    init(run: String, label: String, target: UIView, pauseAfterInspection: Bool) throws {
        self.target = target
        self.origin = "moonpool://com.example.writer-order.\(run).\(label)"
        self.marker = "\(run)-\(label)"
        self.cookieDomain = "mp-\(run)-\(label).invalid"
        self.pauseAfterInspection = pauseAfterInspection
        self.store = WKWebsiteDataStore(forIdentifier: id)
        guard store.identifier == id, store.isPersistent else {
            throw FixtureError("Unexpected identified website data store")
        }
    }

    private func cookieState() async -> [String: Bool] {
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
            $0.name == "mp_admission_order" && $0.value == "fixture" && $0.domain == cookieDomain && $0.path == "/"
        }
        return ["policyDisallowed": denied, "records": records, "cookies": !cookies.isEmpty, "fixturePresent": fixture]
    }

    private func prepareInspection() async -> [String: Bool] {
        await withCheckedContinuation { resume in
            store.httpCookieStore.setCookiePolicy(.disallow) { resume.resume() }
        }
        return await cookieState()
    }

    private func requestAdmission() throws {
        events.append("admission:request")
        guard operations.submit({ [weak self] done in
            guard let self else { return }
            self.finishAdmission = done
            self.handle = self.gate.admit("guest", load: { [weak self] in
                guard let self else { throw FixtureError("The fixture owner is inactive") }
                try self.open()
            }, retire: { [weak self] in self?.retire() })
        }) else { throw FixtureError("The owner is closed") }
    }

    private func requestWrite() throws {
        guard let cookie = HTTPCookie(properties: [
            .domain: cookieDomain, .path: "/", .name: "mp_admission_order", .value: "fixture", .secure: "TRUE",
        ]) else { throw FixtureError("Could not create the test cookie") }
        events.append("writer:request")
        guard operations.submit({ [weak self] done in
            guard let self else { return }
            if self.handle?.live == true, self.web != nil {
                self.writerResult = "refused-live"
                self.events.append("writer:refused-live")
                done()
                return
            }
            self.writerStarts += 1
            self.events.append("writer:start")
            self.store.httpCookieStore.setCookie(cookie) { [weak self] in
                guard let self else { return }
                self.writerCallbackCompleted = true
                self.events.append("writer:callback")
                Task { @MainActor in
                    let evidence = await self.cookieState()
                    self.writeEvidence = evidence
                    self.writerResult = cookiePresence(evidence) == .present && evidence["fixturePresent"] == true
                        ? "stored" : "unconfirmed"
                    self.events.append("writer:readback")
                    done()
                }
            }
        }) else { throw FixtureError("The owner is closed") }
    }

    private func completeAdmission() {
        let done = finishAdmission
        finishAdmission = nil
        done?()
    }

    private func open() throws {
        guard let url = URL(string: origin + "/entry") else { throw FixtureError("Invalid fixture origin") }
        let token = String(decoding: try JSONEncoder().encode(marker), as: UTF8.self)
        let html = """
        <!doctype html><meta charset="utf-8"><title>Admission writer order</title>
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; worker-src 'none'; base-uri 'none'">
        <script>window.writerOrderGuest = { origin: window.origin, cookie: document.cookie, marker: \(token) };</script>
        """
        let config = WKWebViewConfiguration()
        config.websiteDataStore = store
        config.setURLSchemeHandler(FixturePage(url: url, body: html) { [weak self] in
            self?.loader += 1
        }, forURLScheme: "moonpool")
        let view = WKWebView(frame: target.bounds, configuration: config)
        guard view.configuration.websiteDataStore.identifier == id else {
            throw FixtureError("Unexpected WebView store binding")
        }
        target.addSubview(view)
        web = view
        guestLoads += 1
        events.append("admission:load")
        view.load(URLRequest(url: url))
    }

    private func retire() {
        if let web {
            web.stopLoading()
            web.removeFromSuperview()
            self.web = nil
        }
        if finishAdmission != nil {
            events.append("admission:refuse")
            completeAdmission()
        }
    }

    private func checkpoint() async -> [String: Any] {
        let cookie = await cookieState()
        return ["writerStarts": writerStarts, "guestLoads": guestLoads, "writerResult": writerResult, "cookie": cookie]
    }

    private func awaitCondition(_ message: String, _ ready: () -> Bool) async throws {
        for _ in 0..<150 {
            if ready() { return }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw FixtureError(message)
    }

    private func guestObservation() async throws -> [String: Any] {
        guard let web else { throw FixtureError("The fixture document was not admitted") }
        for _ in 0..<150 {
            if let value = try? await web.evaluateJavaScript("JSON.stringify(window.writerOrderGuest || null)"),
               let text = value as? String,
               let result = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] {
                return result
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw FixtureError("The first guest script did not report")
    }

    private func sample(_ before: [String: Bool]) async -> [String: Any] {
        let after = await cookieState()
        return [
            "store": id.uuidString, "origin": origin, "before": before,
            "inspection": inspection ?? [:], "writerResult": writerResult, "writerStarts": writerStarts,
            "guestLoads": guestLoads, "loader": loader, "after": after, "events": events,
        ]
    }

    func admissionFirst() async throws -> [String: Any] {
        let before = await prepareInspection()
        try requestAdmission()
        try await awaitCondition("The inspection did not pause") { resumeInspection != nil }
        try requestWrite()
        let heldAfterRead = await checkpoint()
        let resume = resumeInspection
        resumeInspection = nil
        resume?()
        let guest = try await guestObservation()
        events.append("guest:observed")
        let heldAtGuest = await checkpoint()
        completeAdmission()
        var result = await sample(before)
        result["heldAfterRead"] = heldAfterRead
        result["heldAtGuest"] = heldAtGuest
        result["guest"] = guest
        return result
    }

    func writerFirst() async throws -> [String: Any] {
        let before = await prepareInspection()
        try requestWrite()
        try requestAdmission()
        let heldWhileWriting: [String: Any] = [
            "writerStarts": writerStarts, "writerCallbackCompleted": writerCallbackCompleted,
            "inspectionStarted": events.contains("inspection:start"), "guestLoads": guestLoads,
        ]
        try await awaitCondition("The writer-first admission did not settle") { handle?.completed == true }
        var result = await sample(before)
        result["heldWhileWriting"] = heldWhileWriting
        result["write"] = ["callbackCompleted": writerCallbackCompleted, "cookie": writeEvidence ?? [:]] as [String: Any]
        return result
    }

    func close() {
        operations.close()
        gate.close()
    }
}

@MainActor private final class ProbeController: UIViewController {
    private let run: String

    init(run: String) {
        self.run = run
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { return nil }

    private func measure(_ report: inout [String: Any]) async throws {
        let admission = try Trial(run: run, label: "admission", target: view, pauseAfterInspection: true)
        defer { admission.close() }
        let first = try await admission.admissionFirst()
        admission.close()
        report["cases"] = ["admissionFirst": first]

        let writer = try Trial(run: run, label: "writer", target: view, pauseAfterInspection: false)
        defer { writer.close() }
        let second = try await writer.writerFirst()
        report["cases"] = ["admissionFirst": first, "writerFirst": second]
    }

    func runProbe() async {
        var report: [String: Any] = [
            "run": run, "platform": "ios", "release": UIDevice.current.systemVersion,
            "pid": Int(ProcessInfo.processInfo.processIdentifier), "complete": false,
        ]
        // Initialize WebKit before identified-store and cookie operations.
        let warmup = WKWebViewConfiguration()
        warmup.websiteDataStore = .nonPersistent()
        let initializer = WKWebView(frame: .zero, configuration: warmup)
        defer { withExtendedLifetime(initializer) {} }
        report["initializedWebKit"] = true
        do {
            guard run.range(of: "^[a-z0-9-]{1,28}$", options: .regularExpression) != nil else {
                throw FixtureError("Invalid run tag")
            }
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
        let controller = ProbeController(run: run)
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = controller
        self.window = window
        window.makeKeyAndVisible()
        Task { await controller.runProbe() }
        return true
    }
}
