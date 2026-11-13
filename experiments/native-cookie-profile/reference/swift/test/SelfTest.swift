import CryptoKit
import Foundation
@testable import CookieProfile

/// The Swift port's building blocks against sources independent of it: RFC 3492 samples, Foundation's Gregorian
/// calendar and an NSRegularExpression with Java's ASCII whitespace class. check.py compares the PSL rules digest
/// with the Java reference's, and the c04-1 corpus covers the cookie rules themselves.
final class SelfTest {
    private var checks = 0
    private var failures: [String] = []

    func run(_ pinned: [UInt8]) throws -> Int32 {
        try punycode()
        try requests()
        try publicSuffixes(pinned)
        dates()
        civilDays()
        try foldedSplit()
        if !failures.isEmpty {
            failures.forEach { print($0) }
            print("self-test: \(failures.count) of \(checks) checks failed")
            return 3
        }
        print("self-test: \(checks) checks passed")
        return 0
    }

    private func expect<T: Equatable>(_ expected: T, _ observed: T, _ label: String) {
        checks += 1
        if expected != observed {
            failures.append("FAIL \(label): expected \(expected), observed \(observed)")
        }
    }

    private func scalars(_ points: UInt32...) -> String {
        var text = ""
        text.unicodeScalars.append(contentsOf: points.map { Unicode.Scalar($0)! })
        return text
    }

    private func punycode() throws {
        // RFC 3492 section 7.1 samples (A), (B), (L) and (S).
        expect("egbpdaj6bu4bxfgehfvwxn", try Punycode.encode(scalars(0x0644, 0x064A, 0x0647, 0x0645, 0x0627,
            0x0628, 0x062A, 0x0643, 0x0644, 0x0645, 0x0648, 0x0634, 0x0639, 0x0631, 0x0628, 0x064A, 0x061F)),
            "RFC 3492 sample A")
        expect("ihqwcrb4cv8a8dqg056pqjye", try Punycode.encode(scalars(0x4ED6, 0x4EEC, 0x4E3A, 0x4EC0, 0x4E48,
            0x4E0D, 0x8BF4, 0x4E2D, 0x6587)), "RFC 3492 sample B")
        expect("3B-ww4c5e180e575a65lsy2b", try Punycode.encode(scalars(0x0033, 0x5E74, 0x0042, 0x7D44, 0x91D1,
            0x516B, 0x5148, 0x751F)), "RFC 3492 sample L")
        expect("-> $1.00 <--", try Punycode.encode("-> $1.00 <-"), "RFC 3492 sample S")
        expect("xn--55qx5d", try Punycode.toALabel("公司"), "A-label for the D11 rule")
        expect("example", try Punycode.toALabel("EXAMPLE"), "ASCII labels lowercase without a prefix")
    }

    private func requests() throws {
        // URI.getHost() keeps IPv6 brackets and Foundation's URL.host drops them. Both must name the same jar host.
        let hosts: [(String, String, Bool)] = [
            ("::1", "[::1]", true), ("[::1]", "[::1]", true), ("127.0.0.1", "127.0.0.1", true),
            ("API.Example.COM", "api.example.com", false), ("xn--55qx5d.cn", "xn--55qx5d.cn", false),
        ]
        for (input, host, ip) in hosts {
            let request = try CookieJar.Request.of(host: input, encodedPath: "")
            expect(host, request.host, "canonical host for \(input)")
            expect(ip, request.ip, "IP classification for \(input)")
            expect("/", request.path, "empty request path for \(input)")
        }
    }

    private func publicSuffixes(_ pinned: [UInt8]) throws {
        let list = try PublicSuffixList.parse(pinned)
        expect(6951, list.icannRules, "ICANN rule count in c04-1")
        expect(3463, list.privateRules, "PRIVATE rule count in c04-1")

        // Apple platforms have no IDNA API. The digest below must match the Java reference, which checks
        // every Unicode label against java.net.IDN.
        let canonical = list.canonicalRules()
        let digest = SHA256.hash(data: Array(canonical.joined(separator: "\n").utf8))
            .map { String(format: "%02x", $0) }.joined()
        print("self-test: \(canonical.count) canonical PSL rules")
        print("self-test: PSL rules sha256 \(digest)")

        let cases = [
            ("co.uk", "co.uk"), ("shop.co.uk", "co.uk"), ("example.com", "com"), ("api.example.com", "com"),
            ("foo.ck", "foo.ck"), ("shop.foo.ck", "foo.ck"), ("www.ck", "ck"), ("shop.www.ck", "ck"),
            ("test", "test"), ("shop.test", "test"), ("github.io", "github.io"), ("shop.github.io", "github.io"),
            ("xn--55qx5d.cn", "xn--55qx5d.cn"), ("abyme.dev", "abyme.dev"),
        ]
        for (host, suffix) in cases {
            expect(suffix, list.publicSuffix(host), "public suffix of \(host)")
        }
    }

    private static let utc: Calendar = {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "UTC")!
        return calendar
    }()

    private func utc(_ year: Int, _ month: Int, _ day: Int, _ hour: Int, _ minute: Int, _ second: Int) -> Int64? {
        let parts = DateComponents(year: year, month: month, day: day, hour: hour, minute: minute, second: second)
        return Int64(SelfTest.utc.date(from: parts)!.timeIntervalSince1970)
    }

    private func dates() {
        let nov1994 = utc(1994, 11, 6, 8, 49, 37)
        let cases: [(String, Int64?)] = [
            // RFC 7231 section 7.1.1.1 forms, all of which RFC 6265 section 5.1.1 accepts.
            ("Sun, 06 Nov 1994 08:49:37 GMT", nov1994),
            ("Sunday, 06-Nov-94 08:49:37 GMT", nov1994),
            ("Sun Nov  6 08:49:37 1994", nov1994),
            // Tokens can come in any order. A two-digit year 70-99 means 19xx, 0-69 means 20xx.
            ("1994 Nov 06 08:49:37", nov1994),
            ("Wed, 21 Oct 70 07:28:00 GMT", utc(1970, 10, 21, 7, 28, 0)),
            ("Wed, 21 Oct 69 07:28:00 GMT", utc(2069, 10, 21, 7, 28, 0)),
            ("Wed, 21 Oct 2099 07:28:00 GMT", utc(2099, 10, 21, 7, 28, 0)),
            ("29 Feb 2028 00:00:00", utc(2028, 2, 29, 0, 0, 0)),
            ("1 jAnUaRy 1601 0:0:0", utc(1601, 1, 1, 0, 0, 0)),
            ("31 Dec 9999 23:59:59", utc(9999, 12, 31, 23, 59, 59)),
            // Rejections under section 5.1.1 step 5, and dates that do not exist.
            ("tomorrow", nil),
            ("Wed, 21 Oct 2015 GMT", nil),
            ("Wed, 21 Oct 1600 07:28:00 GMT", nil),
            ("Wed, 32 Oct 2015 07:28:00 GMT", nil),
            ("Wed, 00 Oct 2015 07:28:00 GMT", nil),
            ("Wed, 21 Oct 2015 24:00:00 GMT", nil),
            ("Wed, 21 Oct 2015 07:60:00 GMT", nil),
            ("Wed, 21 Oct 2015 07:28:60 GMT", nil),
            ("29 Feb 2026 00:00:00", nil),
            ("31 Apr 2026 00:00:00", nil),
            // A three-digit time field or day does not match its production.
            ("Wed, 21 Oct 2015 07:28:000 GMT", nil),
            ("Wed, 210 Oct 2015 07:28:00 GMT", nil),
        ]
        for (value, expected) in cases {
            expect(expected, CookieDate.parse(value), "date \(value)")
        }
    }

    private func civilDays() {
        // Day arithmetic is hand-written so Java and Swift share it. Compare it with Foundation's calendar.
        var differences = 0
        for year in 1601...9999 {
            for month in 1...12 {
                let first = SelfTest.utc.date(from: DateComponents(year: year, month: month, day: 1))!
                let last = SelfTest.utc.range(of: .day, in: .month, for: first)!.count
                let end = SelfTest.utc.date(from: DateComponents(year: year, month: month, day: last))!
                let same = last == CookieDate.daysInMonth(year, month)
                    && Int64(end.timeIntervalSince1970) / 86_400 == CookieDate.daysFromCivil(Int64(year), month, last)
                if !same {
                    differences += 1
                    if differences <= 5 { failures.append("FAIL calendar differs from Foundation at \(year)-\(month)") }
                }
            }
        }
        checks += 1
        if differences > 0 {
            failures.append("FAIL \(differences) months from 1601 to 9999 differ from Foundation")
        }
    }

    /// Split with an ICU regex, as the retained iOS broker does.
    private func regexSplit(_ pattern: NSRegularExpression, _ value: String) -> [String] {
        var found: [String] = []
        var last = value.startIndex
        for match in pattern.matches(in: value, range: NSRange(value.startIndex..., in: value)) {
            let range = Range(match.range, in: value)!
            found.append(String(value[last..<range.lowerBound]))
            last = range.upperBound
        }
        found.append(String(value[last...]))
        return found
    }

    private func foldedSplit() throws {
        // Java's \s is [ \t\n\x0B\f\r]. Spelling it out gives ICU the reference rule.
        let ascii = try NSRegularExpression(pattern: ",[ \\t\\n\\x0B\\f\\r]*(?=[^;,= \\t\\n\\x0B\\f\\r]+=)")
        let retained = try NSRegularExpression(pattern: ",\\s*(?=[^;,=\\s]+=)")
        let samples = [
            "", "a=1", "a=1, b=2", "a=1,b=2", "sid=abc, x=y; Path=/; HttpOnly",
            "a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT", "a=1, =x", "a=1, ;b=2", "a=1,\tb=2", "a=1, \u{00a0}b=2",
            "a=1; Foo=\u{00e9}, keep=1", ",b=2", "a=1,,b=2",
        ]
        for sample in samples {
            expect(regexSplit(ascii, sample), CookieJar.splitFolded(sample), "split \(sample)")
        }
        expect(["a=1", "\u{00a0}b=2"], CookieJar.splitFolded("a=1,\u{00a0}b=2"), "U+00A0 is not split whitespace")

        // The same seeded search as the Java self-test, with its own generator.
        let alphabet: [Unicode.Scalar] = ["a", "b", "=", ";", ",", " ", "\t", "\u{000b}", "\u{00e9}", "\u{00a0}"]
        var random = SplitMix64(seed: 20_261_111)
        var differences = 0
        var retainedDifferences = 0
        for _ in 0..<200_000 {
            var sample = ""
            for _ in 0..<random.next(14) {
                sample.unicodeScalars.append(alphabet[random.next(alphabet.count)])
            }
            let split = CookieJar.splitFolded(sample)
            if regexSplit(ascii, sample) != split {
                differences += 1
                if differences <= 5 { failures.append("FAIL split differs for \(sample.debugDescription)") }
            }
            if regexSplit(retained, sample) != split {
                retainedDifferences += 1
            }
        }
        checks += 1
        if differences > 0 {
            failures.append("FAIL \(differences) seeded split samples differ from the ASCII regex")
        }
        print("self-test: the retained iOS regex splits \(retainedDifferences) of 200000 seeded samples differently")
    }
}

/// A small deterministic generator, so the seeded search does not depend on the system's random source.
struct SplitMix64 {
    private var state: UInt64
    init(seed: UInt64) { state = seed }

    mutating func next(_ bound: Int) -> Int {
        state &+= 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return Int((z ^ (z >> 31)) % UInt64(bound))
    }
}
