import Foundation

// Research-only registration seam. WK security-origin roundtrip is measured separately.
enum Admission {
    static func accepts(_ id: String, scheme: String, host: String, port: Int) -> Bool {
        url(for: id) != nil && scheme == "moonpool" && host == id && port == 0
    }
    static func url(for id: String) -> URL? {
        guard id.range(of: "^[a-z0-9]+(\\.[a-z0-9-]+)+$", options: .regularExpression) != nil,
              let url = URL(string: "moonpool://\(id)/"), url.scheme == "moonpool", url.host == id,
              url.port == nil, url.user == nil, url.password == nil,
              url.absoluteString == "moonpool://\(id)/" else { return nil }
        return url
    }
}
