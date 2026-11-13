/// RFC 3492 Punycode encoder, used once to turn Unicode Public Suffix List labels into A-labels. A port of
/// Punycode.java. Apple platforms have no IDNA API, and it applies no Unicode mapping or case folding.
public enum Punycode {
    private static let base = 36
    private static let tMin = 1
    private static let tMax = 26
    private static let skew = 38
    private static let damp = 700
    private static let initialBias = 72
    private static let initialN = 0x80

    /// A lowercase ASCII label stays as is. Any other label becomes `xn--` plus its Punycode.
    public static func toALabel(_ label: String) throws -> String {
        if label.utf8.contains(where: { $0 >= 0x80 }) {
            return try "xn--" + encode(label)
        }
        return Ascii.lower(label)
    }

    /// RFC 3492 section 6.3, over Unicode scalars. Basic code points keep their case, as the RFC requires.
    public static func encode(_ input: String) throws -> String {
        let points = input.unicodeScalars.map { Int($0.value) }
        var output = points.filter { $0 < initialN }.map { UInt8($0) }
        let basic = output.count
        var handled = basic
        if basic > 0 {
            output.append(UInt8(ascii: "-"))
        }
        var n = initialN
        var delta = 0
        var bias = initialBias
        while handled < points.count {
            let next = points.filter { $0 >= n }.min()!
            delta += (next - n) * (handled + 1)
            n = next
            for point in points {
                if point < n {
                    delta += 1
                }
                if point == n {
                    var q = delta
                    var k = base
                    while true {
                        let t = k <= bias ? tMin : min(k - bias, tMax)
                        if q < t {
                            break
                        }
                        output.append(digit(t + (q - t) % (base - t)))
                        q = (q - t) / (base - t)
                        k += base
                    }
                    output.append(digit(q))
                    bias = adapt(delta, handled + 1, handled == basic)
                    delta = 0
                    handled += 1
                }
            }
            if delta > Int(Int32.max) {
                throw ProfileError("Punycode overflow")
            }
            delta += 1
            n += 1
        }
        return String(decoding: output, as: UTF8.self)
    }

    private static func adapt(_ value: Int, _ points: Int, _ first: Bool) -> Int {
        var delta = first ? value / damp : value / 2
        delta += delta / points
        var k = 0
        while delta > ((base - tMin) * tMax) / 2 {
            delta /= base - tMin
            k += base
        }
        return k + (base - tMin + 1) * delta / (delta + skew)
    }

    private static func digit(_ value: Int) -> UInt8 {
        UInt8(value < 26 ? 0x61 + value : 0x30 + value - 26)
    }
}
