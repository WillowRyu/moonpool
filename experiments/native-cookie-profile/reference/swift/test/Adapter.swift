import Foundation
@testable import CookieProfile

/// Feeds c04-1 fixture steps to the Swift port, as ReferenceAdapter does for Java. It reads the request URL,
/// supplies the clock and translates results to JSON. Expected values stay in check.py.
enum Adapter {
    private static let setFields: Set<String> = ["name", "value", "path", "maxAge"]

    static func run(_ pinned: [UInt8]) throws {
        let publicSuffixes = try PublicSuffixList.parse(pinned)
        let input = FileHandle.standardInput.readDataToEndOfFile()
        guard let cases = try JSONSerialization.jsonObject(with: input) as? [[String: Any]] else {
            throw HarnessError("the input must be an array of cases")
        }
        var results: [[String: Any]] = []
        for vector in cases {
            guard let id = vector["id"] as? String, let steps = vector["steps"] as? [[String: Any]] else {
                throw HarnessError("each case needs an id and steps")
            }
            let jar = CookieJar(publicSuffixes: publicSuffixes)
            results.append(["id": id, "observations": try steps.map { try observe(jar, $0) }])
        }
        var output = try JSONSerialization.data(withJSONObject: results)
        output.append(0x0A)
        FileHandle.standardOutput.write(output)
    }

    private static func observe(_ jar: CookieJar, _ step: [String: Any]) throws -> Any {
        guard let operation = step["op"] as? String, let url = step["url"] as? String,
              let now = step["now"] as? String, let date = try? Date(now, strategy: .iso8601) else {
            throw HarnessError("each step needs op, url and now")
        }
        let request = try request(url)
        let seconds = Int64(date.timeIntervalSince1970)
        switch operation {
        case "receive":
            guard let fields = step["fields"] as? [String] else { throw HarnessError("receive needs fields") }
            jar.receive(fields, request, now: seconds)
            return NSNull()
        case "header":
            return jar.cookieHeader(request, now: seconds)
        case "read":
            return jar.scriptCookies(request, now: seconds).map { ["name": $0.name, "value": $0.value, "path": $0.path] }
        case "set":
            guard let fields = step["fields"] as? [String: Any] else { throw HarnessError("set needs fields") }
            return set(jar, request, fields, now: seconds)
        case "jar":
            // A snapshot does not remove expired entries, so the corpus sees what header and read removed.
            return jar.entries.map(snapshot)
        default:
            throw HarnessError("unknown fixture operation \(operation)")
        }
    }

    /// URL.host keeps an A-label as sent, unlike URLComponents.host, which decodes it to Unicode. It drops IPv6
    /// brackets, which the jar restores. path(percentEncoded:) is the D4 input, like URLComponents.percentEncodedPath.
    private static func request(_ text: String) throws -> CookieJar.Request {
        guard let url = URL(string: text), url.scheme == "https", let host = url.host(percentEncoded: true) else {
            throw HarnessError("fixture URLs must be HTTPS service URLs: \(text)")
        }
        return try CookieJar.Request.of(host: host, encodedPath: url.path(percentEncoded: true))
    }

    /// The research brokers' proposed cookies.set fields. A JSON number counts as maxAge only when it is an
    /// integer, as org.json's Integer or Long is for Java. Their bridge errors belong to T29.
    private static func set(_ jar: CookieJar, _ request: CookieJar.Request, _ fields: [String: Any], now: Int64) -> Bool {
        guard fields.keys.allSatisfy(setFields.contains),
              let name = fields["name"] as? String, let value = fields["value"] as? String else {
            return false
        }
        var path: String?
        if let raw = fields["path"] {
            guard let text = raw as? String else { return false }
            path = text
        }
        var maxAge: Int64?
        if let raw = fields["maxAge"] {
            guard let number = raw as? NSNumber, ["q", "l", "i", "s"].contains(String(cString: number.objCType)) else {
                return false
            }
            maxAge = number.int64Value
        }
        return jar.setScriptCookie(request, name: name, value: value, path: path, maxAge: maxAge, now: now)
    }

    private static func snapshot(_ cookie: CookieJar.Cookie) -> [String: Any] {
        let sameSite = switch cookie.sameSite {
        case .default: "default"
        case .strict: "Strict"
        case .lax: "Lax"
        case .none: "None"
        }
        let expiresAt: Any = cookie.expiresAt.map { Date(timeIntervalSince1970: TimeInterval($0)).formatted(.iso8601) }
            ?? NSNull()
        return [
            "name": cookie.name, "value": cookie.value, "domain": cookie.domain, "path": cookie.path,
            "hostOnly": cookie.hostOnly, "httpOnly": cookie.httpOnly, "expiresAt": expiresAt, "sameSite": sameSite,
        ]
    }
}
