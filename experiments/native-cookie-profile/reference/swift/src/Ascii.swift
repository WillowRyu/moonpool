/// A setup error, such as a malformed PSL or a request host the adapter did not canonicalize.
public struct ProfileError: Error, CustomStringConvertible {
    public let description: String
    init(_ description: String) { self.description = description }
}

/// ASCII-only helpers over UTF-8 bytes. Swift's String compares, splits and matches prefixes by Character, with
/// Unicode canonical equivalence, so the port works on bytes wherever the Java reference works on chars.
enum Ascii {
    static func lowerByte(_ byte: UInt8) -> UInt8 {
        byte >= 0x41 && byte <= 0x5A ? byte + 0x20 : byte
    }

    static func lower(_ text: String) -> String {
        String(decoding: text.utf8.map(lowerByte), as: UTF8.self)
    }

    static func string(_ bytes: ArraySlice<UInt8>) -> String {
        String(decoding: bytes, as: UTF8.self)
    }

    static func startsWithIgnoreCase(_ text: String, _ lowercasePrefix: String) -> Bool {
        let bytes = Array(text.utf8)
        let prefix = Array(lowercasePrefix.utf8)
        return bytes.count >= prefix.count && zip(bytes, prefix).allSatisfy { lowerByte($0) == $1 }
    }

    static func hasSuffix(_ text: String, _ suffix: String) -> Bool {
        text.utf8.count >= suffix.utf8.count && text.utf8.suffix(suffix.utf8.count).elementsEqual(suffix.utf8)
    }

    static func isDigit(_ byte: UInt8) -> Bool {
        byte >= 0x30 && byte <= 0x39
    }

    /// RFC 6265 WSP: space and horizontal tab.
    static func trimWhitespace(_ bytes: ArraySlice<UInt8>) -> ArraySlice<UInt8> {
        var start = bytes.startIndex
        var end = bytes.endIndex
        while start < end && (bytes[start] == 0x20 || bytes[start] == 0x09) {
            start += 1
        }
        while end > start && (bytes[end - 1] == 0x20 || bytes[end - 1] == 0x09) {
            end -= 1
        }
        return bytes[start..<end]
    }

    /// Splits on one byte and keeps empty pieces.
    static func split(_ bytes: ArraySlice<UInt8>, _ separator: UInt8) -> [ArraySlice<UInt8>] {
        var pieces: [ArraySlice<UInt8>] = []
        var start = bytes.startIndex
        for index in bytes.indices where bytes[index] == separator {
            pieces.append(bytes[start..<index])
            start = index + 1
        }
        pieces.append(bytes[start..<bytes.endIndex])
        return pieces
    }
}
