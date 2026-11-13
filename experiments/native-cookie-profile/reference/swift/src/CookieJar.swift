/// One mini app's cookie jar under profile c04-1, ported from CookieJar.java. Both SDKs must give a mini app the
/// same result, so this file follows the Java reference step by step and works on UTF-8 bytes where Java works on
/// chars. Callers supply the request host, the percent-encoded request path and the time in epoch seconds. Approval
/// of service origins stays with the broker (contract section 2).
///
/// Domain, public-suffix, prefix and `HttpOnly` rules here decide which service receives a session cookie and what
/// a script can read or plant, so this file is a SPEC section 9 boundary.
public final class CookieJar {
    /// D5: persistent expiry is capped at 400 days after receipt.
    public static let lifetimeCapSeconds: Int64 = 400 * 24 * 60 * 60
    /// D1: limit on the trimmed name plus value.
    static let maxNameValueOctets = 4096
    /// D1: attributes with a longer trimmed value are ignored.
    static let maxAttributeValueOctets = 1024

    public enum SameSite: Sendable {
        case `default`, strict, lax, none
    }

    /// The request host and the path exactly as sent on the wire (D4).
    public struct Request: Sendable {
        let host: String
        let path: String
        let ip: Bool

        /// The adapter passes an ASCII host: A-labels for DNS names, and an IPv6 literal with or without brackets.
        /// Foundation's URL.host drops the brackets, so the jar adds them back, as the Java reference does.
        public static func of(host: String, encodedPath: String) throws -> Request {
            guard !host.utf8.isEmpty, isVisibleAscii(host) else {
                throw ProfileError("request host must be canonical ASCII: \(host)")
            }
            let path = encodedPath.utf8.isEmpty ? "/" : encodedPath
            guard path.utf8.first == UInt8(ascii: "/"), isVisibleAscii(path) else {
                throw ProfileError("request path must be percent-encoded and absolute: \(path)")
            }
            var canonical = Ascii.lower(host)
            if canonical.utf8.contains(UInt8(ascii: ":")) && canonical.utf8.first != UInt8(ascii: "[") {
                canonical = "[" + canonical + "]"
            }
            return Request(host: canonical, path: path, ip: canonical.utf8.first == UInt8(ascii: "[") || isIpv4(canonical))
        }
    }

    /// A stored cookie. D3-B identity is name, domain, path and host-only.
    public struct Cookie: Sendable {
        public let name: String
        public let value: String
        public let domain: String
        public let path: String
        public let hostOnly: Bool
        public let httpOnly: Bool
        public let secure: Bool
        public let sameSite: SameSite
        /// Epoch seconds, or nil for a session cookie.
        public let expiresAt: Int64?
        /// D8: assigned to each new identity and kept when that identity is replaced.
        let creation: Int64

        func expired(_ now: Int64) -> Bool {
            if let expiresAt {
                return expiresAt <= now
            }
            return false
        }

        func identical(_ name: String, _ domain: String, _ path: String, _ hostOnly: Bool) -> Bool {
            self.name.utf8.elementsEqual(name.utf8) && self.domain.utf8.elementsEqual(domain.utf8)
                && self.path.utf8.elementsEqual(path.utf8) && self.hostOnly == hostOnly
        }
    }

    /// One split line after RFC 6265 section 5.2 parsing under D1.
    private struct Line {
        let name: String
        let value: String
        var expires: Int64?
        var maxAge: Int64?
        var domainPresent = false
        var domain: String?
        var path: String?
        var secure = false
        var httpOnly = false
        var sameSite = SameSite.default
    }

    private let publicSuffixes: PublicSuffixList
    private var storage: [Cookie] = []
    private var nextCreation: Int64 = 0

    public init(publicSuffixes: PublicSuffixList) {
        self.publicSuffixes = publicSuffixes
    }

    /// Stored entries in insertion order, including any expired entry no operation has removed yet.
    public var entries: [Cookie] {
        storage
    }

    /// Header fields from one response, in order. The adapter's fold-then-split rule applies to them together.
    public func receive(_ fields: [String], _ request: Request, now: Int64) {
        removeExpired(now)
        for line in CookieJar.splitFolded(fields.joined(separator: ", ")) {
            store(line, request, now)
        }
    }

    /// ADR 0027 rule 1 with Java's ASCII `\s`. NSRegularExpression's `\s` also matches Unicode spaces such as
    /// U+00A0, which is where the retained iOS broker splits differently.
    public static func splitFolded(_ folded: String) -> [String] {
        let bytes = Array(folded.utf8)
        var lines: [String] = []
        var start = 0
        var index = 0
        while index < bytes.count {
            if bytes[index] == UInt8(ascii: ",") {
                var name = index + 1
                while name < bytes.count && isRegexSpace(bytes[name]) {
                    name += 1
                }
                var end = name
                while end < bytes.count && !isNameStop(bytes[end]) {
                    end += 1
                }
                if end > name && end < bytes.count && bytes[end] == UInt8(ascii: "=") {
                    lines.append(Ascii.string(bytes[start..<index]))
                    start = name
                    index = name
                    continue
                }
            }
            index += 1
        }
        lines.append(Ascii.string(bytes[start...]))
        return lines
    }

    /// D8: matching cookies, longer path first, then earlier creation, as `name=value` pairs.
    public func cookieHeader(_ request: Request, now: Int64) -> String {
        removeExpired(now)
        return matching(request).map { $0.name + "=" + $0.value }.joined(separator: "; ")
    }

    /// The `cookies.get` view: the same selection and order without `HttpOnly` entries.
    public func scriptCookies(_ request: Request, now: Int64) -> [Cookie] {
        removeExpired(now)
        return matching(request).filter { !$0.httpOnly }
    }

    /// The research brokers' proposed structured `cookies.set`, as in the Java reference. T29 owns the public
    /// schema and error codes.
    public func setScriptCookie(
        _ request: Request, name: String, value: String, path: String?, maxAge: Int64?, now: Int64
    ) -> Bool {
        removeExpired(now)
        if !CookieJar.isToken(name) || !CookieJar.isCookieValue(value)
            || (path.map { !CookieJar.isScriptPath($0) } ?? false)
            || name.utf8.count + value.utf8.count > CookieJar.maxNameValueOctets
            || (path.map { $0.utf8.count > CookieJar.maxAttributeValueOctets } ?? false) {
            return false
        }
        if Ascii.startsWithIgnoreCase(name, "__secure-") || Ascii.startsWithIgnoreCase(name, "__host-") {
            return false
        }
        let cookiePath = path ?? "/"
        let existing = find(name, request.host, cookiePath, true)
        if let existing, storage[existing].httpOnly {
            return false
        }
        let expiresAt = maxAge.map { now + max(0, min($0, CookieJar.lifetimeCapSeconds)) }
        commit(existing, Cookie(name: name, value: value, domain: request.host, path: cookiePath, hostOnly: true,
            httpOnly: false, secure: false, sameSite: .default, expiresAt: expiresAt, creation: 0), now)
        return true
    }

    private func store(_ text: String, _ request: Request, _ now: Int64) {
        guard let line = CookieJar.parse(text) else {
            return
        }

        // D2: canonicalize Domain, then require the request host to be inside it. IP hosts accept only themselves.
        var domain = request.host
        var hostOnly = true
        if let attribute = line.domain {
            let bytes = Array(attribute.utf8)
            let canonical = Ascii.lower(Ascii.string(bytes.first == UInt8(ascii: ".") ? bytes.dropFirst() : bytes[...]))
            if !canonical.utf8.isEmpty {
                if request.ip {
                    if !canonical.utf8.elementsEqual(request.host.utf8) {
                        return
                    }
                } else {
                    let equal = canonical.utf8.elementsEqual(request.host.utf8)
                    if !equal && !Ascii.hasSuffix(request.host, "." + canonical) {
                        return
                    }
                    if !publicSuffixes.isPublicSuffix(canonical) {
                        domain = canonical
                        hostOnly = false
                    } else if !equal {
                        return
                    }
                }
            }
        }

        // RFC 6265 section 5.2.4: an invalid Path attribute means the default path.
        let path = line.path ?? CookieJar.defaultPath(request.path)

        // D7: every service request is HTTPS, so Secure is always allowed, and SameSite=None needs it.
        if line.sameSite == .none && !line.secure {
            return
        }
        // D6, before any commit or expiry deletion. __Host- needs an explicit Path=/ and no Domain attribute at all.
        if Ascii.startsWithIgnoreCase(line.name, "__secure-") && !line.secure {
            return
        }
        if Ascii.startsWithIgnoreCase(line.name, "__host-")
            && (!line.secure || line.domainPresent || !(line.path.map { $0.utf8.elementsEqual("/".utf8) } ?? false)) {
            return
        }

        // D5: the last valid Max-Age wins over the last valid Expires; both are capped at 400 days after receipt.
        var expiresAt: Int64?
        if let maxAge = line.maxAge {
            expiresAt = now + maxAge
        } else if let expires = line.expires {
            expiresAt = min(expires, now + CookieJar.lifetimeCapSeconds)
        }
        let existing = find(line.name, domain, path, hostOnly)
        commit(existing, Cookie(name: line.name, value: line.value, domain: domain, path: path, hostOnly: hostOnly,
            httpOnly: line.httpOnly, secure: line.secure, sameSite: line.sameSite, expiresAt: expiresAt, creation: 0),
            now)
    }

    /// Replace the identity, keeping its creation order, or delete it when the new expiry is not in the future.
    private func commit(_ existing: Int?, _ cookie: Cookie, _ now: Int64) {
        var creation: Int64?
        if let existing {
            creation = storage[existing].creation
            storage.remove(at: existing)
        }
        if cookie.expired(now) {
            return
        }
        if creation == nil {
            creation = nextCreation
            nextCreation += 1
        }
        storage.append(Cookie(name: cookie.name, value: cookie.value, domain: cookie.domain, path: cookie.path,
            hostOnly: cookie.hostOnly, httpOnly: cookie.httpOnly, secure: cookie.secure, sameSite: cookie.sameSite,
            expiresAt: cookie.expiresAt, creation: creation!))
    }

    /// RFC 6265 section 5.2 with the D1 character and size rules. nil rejects the whole line.
    private static func parse(_ text: String) -> Line? {
        let bytes = Array(text.utf8)
        if bytes.contains(where: { $0 != 0x09 && ($0 < 0x20 || $0 > 0x7E) }) {
            return nil
        }
        let semicolon = bytes.firstIndex(of: UInt8(ascii: ";"))
        let pair = bytes[..<(semicolon ?? bytes.count)]
        guard let equals = pair.firstIndex(of: UInt8(ascii: "=")) else {
            return nil
        }
        let name = Ascii.trimWhitespace(pair[..<equals])
        let value = Ascii.trimWhitespace(pair[(equals + 1)...])
        if name.isEmpty || name.count + value.count > maxNameValueOctets {
            return nil
        }
        var line = Line(name: Ascii.string(name), value: Ascii.string(value))
        guard let semicolon else {
            return line
        }
        for attribute in Ascii.split(bytes[(semicolon + 1)...], UInt8(ascii: ";")) {
            let separator = attribute.firstIndex(of: UInt8(ascii: "="))
            let key = Ascii.lower(Ascii.string(Ascii.trimWhitespace(separator.map { attribute[..<$0] } ?? attribute)))
            let value = separator.map { Ascii.trimWhitespace(attribute[($0 + 1)...]) } ?? []
            // D6 counts an explicit Domain even when D1 ignores its value for length, so __Host- stays rejected.
            if key == "domain" {
                line.domainPresent = true
            }
            if value.count > maxAttributeValueOctets {
                continue
            }
            let text = Ascii.string(value)
            switch key {
            case "expires":
                if let date = CookieDate.parse(text) {
                    line.expires = date
                }
            case "max-age":
                if let seconds = maxAge(value) {
                    line.maxAge = seconds
                }
            case "domain":
                // An empty value is ignored for scope (D2). Its presence is recorded above for D6.
                if !value.isEmpty {
                    line.domain = text
                }
            case "path":
                line.path = value.first == UInt8(ascii: "/") ? text : nil
            case "secure":
                line.secure = true
            case "httponly":
                line.httpOnly = true
            case "samesite":
                switch Ascii.lower(text) {
                case "strict": line.sameSite = .strict
                case "lax": line.sameSite = .lax
                case "none": line.sameSite = .none
                default: line.sameSite = .default
                }
            default:
                break // D9: Partitioned, Priority and other attributes are ignored.
            }
        }
        return line
    }

    /// D5: one or more ASCII digits with an optional leading `-`, saturated to `[0, cap]`.
    private static func maxAge(_ value: ArraySlice<UInt8>) -> Int64? {
        let negative = value.first == UInt8(ascii: "-")
        let digits = negative ? value.dropFirst() : value
        if digits.isEmpty {
            return nil
        }
        var seconds: Int64 = 0
        for byte in digits {
            if !Ascii.isDigit(byte) {
                return nil
            }
            seconds = min(seconds * 10 + Int64(byte - 0x30), lifetimeCapSeconds)
        }
        return negative ? 0 : seconds
    }

    private func removeExpired(_ now: Int64) {
        storage.removeAll { $0.expired(now) }
    }

    private func find(_ name: String, _ domain: String, _ path: String, _ hostOnly: Bool) -> Int? {
        storage.firstIndex { $0.identical(name, domain, path, hostOnly) }
    }

    private func matching(_ request: Request) -> [Cookie] {
        storage.filter { CookieJar.domainMatches($0, request) && CookieJar.pathMatches(request.path, $0.path) }
            .sorted { a, b in
                a.path.utf8.count != b.path.utf8.count ? a.path.utf8.count > b.path.utf8.count : a.creation < b.creation
            }
    }

    /// A host-only cookie needs the exact host. A domain cookie also matches DNS subdomains at a dot boundary.
    private static func domainMatches(_ cookie: Cookie, _ request: Request) -> Bool {
        let equal = request.host.utf8.elementsEqual(cookie.domain.utf8)
        if cookie.hostOnly {
            return equal
        }
        return !request.ip && (equal || Ascii.hasSuffix(request.host, "." + cookie.domain))
    }

    /// RFC 6265 section 5.1.4 over the encoded request path (D4).
    static func pathMatches(_ requestPath: String, _ cookiePath: String) -> Bool {
        let request = Array(requestPath.utf8)
        let cookie = Array(cookiePath.utf8)
        if request == cookie {
            return true
        }
        return request.starts(with: cookie)
            && (cookie.last == UInt8(ascii: "/") || request[cookie.count] == UInt8(ascii: "/"))
    }

    /// RFC 6265 section 5.1.4 default-path, over the encoded request path (D4).
    static func defaultPath(_ requestPath: String) -> String {
        let bytes = Array(requestPath.utf8)
        guard let last = bytes.lastIndex(of: UInt8(ascii: "/")), last > 0 else {
            return "/"
        }
        return Ascii.string(bytes[..<last])
    }

    /// Java's `\s` without UNICODE_CHARACTER_CLASS.
    private static func isRegexSpace(_ byte: UInt8) -> Bool {
        [0x20, 0x09, 0x0A, 0x0B, 0x0C, 0x0D].contains(byte)
    }

    private static func isNameStop(_ byte: UInt8) -> Bool {
        byte == UInt8(ascii: ";") || byte == UInt8(ascii: ",") || byte == UInt8(ascii: "=") || isRegexSpace(byte)
    }

    private static func isVisibleAscii(_ text: String) -> Bool {
        text.utf8.allSatisfy { $0 > 0x20 && $0 < 0x7F }
    }

    /// Four dotted decimal octets. Bracketed IPv6 is recognized by `Request.of`.
    private static func isIpv4(_ host: String) -> Bool {
        let parts = Ascii.split(Array(host.utf8)[...], UInt8(ascii: "."))
        return parts.count == 4 && parts.allSatisfy { part in
            !part.isEmpty && part.count <= 3 && part.allSatisfy(Ascii.isDigit)
                && part.reduce(0) { $0 * 10 + Int($1 - 0x30) } <= 255
        }
    }

    /// RFC 9110 token, as the research brokers require for script cookie names.
    private static func isToken(_ text: String) -> Bool {
        !text.utf8.isEmpty && text.utf8.allSatisfy { byte in
            Ascii.isDigit(byte) || (0x61...0x7A).contains(byte) || (0x41...0x5A).contains(byte)
                || "!#$%&'*+-.^_`|~".utf8.contains(byte)
        }
    }

    /// RFC 6265 cookie-octet, so a script value cannot add a pair beside a protected cookie.
    private static func isCookieValue(_ text: String) -> Bool {
        text.utf8.allSatisfy { byte in
            byte == 0x21 || (0x23...0x2B).contains(byte) || (0x2D...0x3A).contains(byte)
                || (0x3C...0x5B).contains(byte) || (0x5D...0x7E).contains(byte)
        }
    }

    /// `/` then visible ASCII and space without `;`.
    private static func isScriptPath(_ text: String) -> Bool {
        text.utf8.first == UInt8(ascii: "/") && text.utf8.dropFirst().allSatisfy { byte in
            byte >= 0x20 && byte <= 0x7E && byte != UInt8(ascii: ";")
        }
    }
}
