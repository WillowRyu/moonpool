import Security
import UIKit
import WebKit

/// The fixture's native resource loader owns every redirect request.
final class StaticImages: NSObject, URLSessionTaskDelegate {
    private static let start = [
        "direct": "/static/direct.gif", "approved": "/static/redirect-approved",
        "path": "/static/redirect-path", "other": "/static/redirect-other",
        "encoded": "/static/redirect-encoded",
    ]
    private static let allowed = Set(start.values).union(["/static/final.gif"])
    private let origin: URL
    private let run: String
    private let anchor: SecCertificate
    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.httpCookieStorage = nil
        config.httpCookieAcceptPolicy = .never
        config.httpShouldSetCookies = false
        config.urlCredentialStorage = nil
        config.urlCache = nil
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()

    init(origin: URL, run: String, anchor: SecCertificate) {
        self.origin = origin
        self.run = run
        self.anchor = anchor
    }

    func close() {
        session.invalidateAndCancel()
    }

    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        let space = challenge.protectionSpace
        guard space.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              space.host == origin.host, space.port == origin.port, let trust = space.serverTrust else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        SecTrustSetAnchorCertificates(trust, [anchor] as CFArray)
        SecTrustSetAnchorCertificatesOnly(trust, true)
        if SecTrustEvaluateWithError(trust, nil) {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        completionHandler(.rejectProtectionSpace, nil)
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }

    private func allowed(_ url: URL, query: String) -> Bool {
        guard let parts = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return false }
        return parts.scheme == "https" && parts.host == origin.host && parts.port == origin.port &&
            parts.user == nil && parts.password == nil && parts.fragment == nil &&
            Self.allowed.contains(parts.percentEncodedPath) && parts.percentEncodedQuery == query
    }

    func get(_ name: String) async throws -> Data? {
        guard let path = Self.start[name] else { return nil }
        let query = "run=\(run)&case=\(name)"
        var url = URL(string: path + "?" + query, relativeTo: origin)?.absoluteURL
        for _ in 0..<5 {
            guard let current = url, allowed(current, query: query) else { return nil }
            var request = URLRequest(url: current)
            request.httpShouldHandleCookies = false
            let (bytes, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else { return nil }
            if [301, 302, 303, 307, 308].contains(http.statusCode),
               let location = http.value(forHTTPHeaderField: "Location") {
                url = URL(string: location, relativeTo: current)?.absoluteURL
                continue
            }
            guard http.statusCode == 200 && http.mimeType == "image/gif" else { return nil }
            return bytes
        }
        return nil
    }
}

@MainActor final class ImageScheme: NSObject, WKURLSchemeHandler {
    private let origin: String
    private let script: String
    private let images: StaticImages
    private var active: [ObjectIdentifier: Task<Void, Never>] = [:]

    init(origin: String, script: String, images: StaticImages) {
        self.origin = origin
        self.script = script
        self.images = images
    }

    private func finish(_ task: WKURLSchemeTask, _ url: URL, _ type: String, _ data: Data) {
        task.didReceive(HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil,
                                       headerFields: ["Content-Type": type, "Cache-Control": "no-store"])!)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, task.request.httpMethod == "GET",
              origin == "\(url.scheme ?? "")://\(url.host ?? "")" else {
            task.didFailWithError(URLError(.unsupportedURL))
            return
        }
        if url.path == "/images" {
            let html = """
                <!doctype html><meta charset=utf-8><meta http-equiv="Content-Security-Policy"
                content="default-src 'none'; script-src 'unsafe-inline'; img-src 'self'; worker-src 'none'">
                <script>\(script)</script>
                """
            finish(task, url, "text/html; charset=utf-8", Data(html.utf8))
            return
        }
        guard url.path.hasPrefix("/image/") else {
            task.didFailWithError(URLError(.unsupportedURL))
            return
        }
        let name = String(url.path.dropFirst("/image/".count))
        let key = ObjectIdentifier(task as AnyObject)
        active[key] = Task {
            let bytes = try? await images.get(name)
            guard !Task.isCancelled, active.removeValue(forKey: key) != nil else { return }
            if let bytes { finish(task, url, "image/gif", bytes) }
            else { task.didFailWithError(URLError(.resourceUnavailable)) }
        }
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {
        active.removeValue(forKey: ObjectIdentifier(task as AnyObject))?.cancel()
    }
}

@MainActor final class Controller: UIViewController {
    let run: String
    let base: String

    init(run: String, base: String) {
        self.run = run
        self.base = base
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError() }

    override func viewDidLoad() {
        super.viewDidLoad()
        Task { await execute() }
    }

    private func sources(_ store: WKWebsiteDataStore) async -> [String: Bool] {
        let records: Bool = await withCheckedContinuation { resume in
            store.fetchDataRecords(ofTypes: [WKWebsiteDataTypeCookies]) { resume.resume(returning: !$0.isEmpty) }
        }
        let cookies: Bool = await withCheckedContinuation { resume in
            store.httpCookieStore.getAllCookies { resume.resume(returning: !$0.isEmpty) }
        }
        return ["records": records, "cookies": cookies]
    }

    private func denyCookies(_ store: WKWebsiteDataStore) async -> Bool {
        await withCheckedContinuation { resume in
            store.httpCookieStore.setCookiePolicy(.disallow) { resume.resume() }
        }
        return await withCheckedContinuation { resume in
            store.httpCookieStore.getCookiePolicy { resume.resume(returning: $0 == .disallow) }
        }
    }

    private func observe(_ web: WKWebView) async throws -> [String: Any] {
        for _ in 0..<140 {
            if let text = try? await web.evaluateJavaScript("JSON.stringify(window.c09Images || null)") as? String,
               let value = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] {
                return value
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw NSError(domain: "ImageObservationDeadline", code: 1)
    }

    private func execute() async {
        var report: [String: Any] = ["run": run, "platform": "ios", "release": UIDevice.current.systemVersion,
                                     "complete": false, "errors": [] as [String]]
        // Initialize WebKit before the first store operation.
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        let initializer = WKWebView(frame: .zero, configuration: config)
        defer { withExtendedLifetime(initializer) {} }
        do {
            guard run.range(of: "^[a-z0-9-]{1,48}$", options: .regularExpression) != nil,
                  let url = URL(string: base), let port = url.port, base == "https://localhost:\(port)" else {
                throw URLError(.unsupportedURL)
            }
            let files = Bundle.main.bundleURL.appendingPathComponent("Fixtures")
            let der = try Data(contentsOf: files.appendingPathComponent("ca.der"))
            guard let anchor = SecCertificateCreateWithData(nil, der as CFData) else {
                throw URLError(.serverCertificateHasUnknownRoot)
            }
            let script = try String(contentsOf: files.appendingPathComponent("images.js"), encoding: .utf8)
            let origin = "moonpool://com.example.paths." + run
            let resource = StaticImages(origin: url, run: run, anchor: anchor)
            defer { resource.close() }
            let store = WKWebsiteDataStore(forIdentifier: UUID())
            let disallowed = await denyCookies(store)
            let before = await sources(store)
            let empty = !before.values.contains(true)
            guard disallowed && empty else { throw NSError(domain: "StoreAdmissionRefused", code: 1) }
            let guest = WKWebViewConfiguration()
            guest.websiteDataStore = store
            guest.setURLSchemeHandler(ImageScheme(origin: origin, script: script, images: resource), forURLScheme: "moonpool")
            let web = WKWebView(frame: view.bounds, configuration: guest)
            view.addSubview(web)
            web.load(URLRequest(url: URL(string: origin + "/images")!))
            let observation = try await observe(web)
            let after = await sources(store)
            report["guest"] = observation
            report["worker"] = ["state": observation["serviceWorker"] as? Bool == false ? "unsupported" : "unverified"]
            report["admission"] = ["empty": empty, "policyDisallowed": disallowed, "sources": before,
                                    "afterEmpty": !after.values.contains(true)]
            report["complete"] = true
        } catch {
            report["errors"] = [String(describing: error)]
        }
        let output = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("report.json")
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
        func value(_ key: String) -> String { args[args.firstIndex(of: key)! + 1] }
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = Controller(run: value("--run"), base: value("--base"))
        self.window = window
        window.makeKeyAndVisible()
        return true
    }
}
