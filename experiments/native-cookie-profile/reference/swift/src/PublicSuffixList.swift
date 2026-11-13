/// The pinned Public Suffix List of profile c04-1 (D2-A), with ICANN and PRIVATE rules evaluated together. A port
/// of PublicSuffixList.java. This data decides which services can share a domain cookie, a SPEC section 9 boundary,
/// so loading fails instead of guessing.
public struct PublicSuffixList: Sendable {
    private static let beginICANN = "// ===BEGIN ICANN DOMAINS==="
    private static let endICANN = "// ===END ICANN DOMAINS==="
    private static let beginPrivate = "// ===BEGIN PRIVATE DOMAINS==="
    private static let endPrivate = "// ===END PRIVATE DOMAINS==="

    private var rules: Set<String> = []
    private var exceptions: Set<String> = []
    public private(set) var icannRules = 0
    public private(set) var privateRules = 0

    public static func parse(_ utf8: [UInt8]) throws -> PublicSuffixList {
        try validateUTF8(utf8)
        var list = PublicSuffixList()
        var section: String?
        var seen: [String] = []
        for line in Ascii.split(utf8[...], UInt8(ascii: "\n")) {
            if line.starts(with: [0x2F, 0x2F]) {
                // Java's String.trim removes every byte up to U+0020 at both ends.
                let marker = Ascii.string(trimControls(line))
                switch marker {
                case beginICANN, beginPrivate:
                    if section != nil || seen.contains(marker) {
                        throw ProfileError("unexpected PSL marker \(marker)")
                    }
                    section = marker
                    seen.append(marker)
                case endICANN, endPrivate:
                    if section != (marker == endICANN ? beginICANN : beginPrivate) {
                        throw ProfileError("unexpected PSL marker \(marker)")
                    }
                    section = nil
                    seen.append(marker)
                default:
                    break
                }
                continue
            }
            // The PSL format reads each line only up to its first whitespace.
            let rule = firstToken(line)
            if rule.isEmpty {
                continue
            }
            guard let current = section else {
                throw ProfileError("PSL rule outside the ICANN and PRIVATE sections: \(Ascii.string(rule))")
            }
            try list.add(rule)
            if current == beginICANN {
                list.icannRules += 1
            } else {
                list.privateRules += 1
            }
        }
        if section != nil || seen != [beginICANN, endICANN, beginPrivate, endPrivate] {
            throw ProfileError("the PSL must contain one ICANN and then one PRIVATE section")
        }
        return list
    }

    /// The PSL formal algorithm for a canonical lowercase ASCII host, as in the Java reference. One trailing dot
    /// is removed for the lookup and restored in the result. Any other empty label makes the whole name a public
    /// suffix, so no domain cookie can name it.
    public func publicSuffix(_ host: String) -> String {
        var bytes = Array(host.utf8)[...]
        let trailingDot = bytes.last == UInt8(ascii: ".")
        if trailingDot {
            bytes = bytes.dropLast()
        }
        let labels = Ascii.split(bytes, UInt8(ascii: ".")).map(Ascii.string)
        if labels.contains(where: { $0.utf8.isEmpty }) {
            return host
        }
        let suffix = lookup(labels)
        return trailingDot ? suffix + "." : suffix
    }

    private func lookup(_ labels: [String]) -> String {
        func join(_ start: Int) -> String {
            labels[start...].joined(separator: ".")
        }
        for index in labels.indices where exceptions.contains(join(index)) {
            return join(index + 1)
        }
        for index in labels.indices {
            let candidate = join(index)
            let wildcard = index + 1 < labels.count ? "*." + join(index + 1) : "*"
            if rules.contains(candidate) || rules.contains(wildcard) {
                return candidate
            }
        }
        return labels[labels.count - 1]
    }

    public func isPublicSuffix(_ domain: String) -> Bool {
        publicSuffix(domain) == domain
    }

    /// Every rule after A-label conversion, exceptions with `!`, sorted so ports can compare digests.
    func canonicalRules() -> [String] {
        (Array(rules) + exceptions.map { "!" + $0 }).sorted()
    }

    private mutating func add(_ rule: ArraySlice<UInt8>) throws {
        let exception = rule.first == UInt8(ascii: "!")
        let labels = Ascii.split(exception ? rule.dropFirst() : rule, UInt8(ascii: "."))
        var key: [String] = []
        for (index, label) in labels.enumerated() {
            let wildcard = label.elementsEqual([UInt8(ascii: "*")])
            if label.isEmpty || (wildcard && (exception || index > 0))
                || (!wildcard && label.contains(UInt8(ascii: "*"))) {
                throw ProfileError("unsupported PSL rule \(Ascii.string(rule))")
            }
            key.append(wildcard ? "*" : try Punycode.toALabel(Ascii.string(label)))
        }
        if exception {
            exceptions.insert(key.joined(separator: "."))
        } else {
            rules.insert(key.joined(separator: "."))
        }
    }

    /// Strict decoding, like Java's REPORT action: an ill-formed sequence stops the load.
    private static func validateUTF8(_ bytes: [UInt8]) throws {
        var iterator = bytes.makeIterator()
        var codec = UTF8()
        while true {
            switch codec.decode(&iterator) {
            case .scalarValue: continue
            case .emptyInput: return
            case .error: throw ProfileError("the PSL is not valid UTF-8")
            }
        }
    }

    private static func trimControls(_ bytes: ArraySlice<UInt8>) -> ArraySlice<UInt8> {
        var start = bytes.startIndex
        var end = bytes.endIndex
        while start < end && bytes[start] <= 0x20 {
            start += 1
        }
        while end > start && bytes[end - 1] <= 0x20 {
            end -= 1
        }
        return bytes[start..<end]
    }

    /// ASCII whitespace only, as in the Java reference.
    private static func firstToken(_ line: ArraySlice<UInt8>) -> ArraySlice<UInt8> {
        let stop = line.firstIndex { [0x20, 0x09, 0x0D, 0x0B, 0x0C].contains($0) } ?? line.endIndex
        return line[line.startIndex..<stop]
    }
}
