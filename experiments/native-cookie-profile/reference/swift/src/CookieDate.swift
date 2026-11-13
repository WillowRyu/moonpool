/// RFC 6265 section 5.1.1 cookie-date parsing (D5). A port of CookieDate.java, with the same hand-written
/// calendar arithmetic.
public enum CookieDate {
    private static let months: [[UInt8]] = [
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    ].map { Array($0.utf8) }

    /// Epoch seconds in UTC, or nil when the value fails the algorithm.
    public static func parse(_ value: String) -> Int64? {
        var hour = -1
        var minute = -1
        var second = -1
        var day = -1
        var month = -1
        var year = -1
        for token in tokens(Array(value.utf8)) {
            if hour < 0, let fields = time(token) {
                (hour, minute, second) = fields
                continue
            }
            if day < 0 {
                day = leadingNumber(token, 1, 2)
                if day >= 0 {
                    continue
                }
            }
            if month < 0 {
                month = monthOf(token)
                if month > 0 {
                    continue
                }
                month = -1
            }
            if year < 0 {
                year = leadingNumber(token, 2, 4)
            }
        }
        if hour < 0 || day < 0 || month < 0 || year < 0 {
            return nil
        }
        if year >= 70 && year <= 99 {
            year += 1900
        } else if year <= 69 {
            year += 2000
        }
        if day < 1 || day > 31 || year < 1601 || hour > 23 || minute > 59 || second > 59
            || day > daysInMonth(year, month) {
            return nil
        }
        return daysFromCivil(Int64(year), month, day) * 86_400 + Int64(hour) * 3_600 + Int64(minute) * 60
            + Int64(second)
    }

    /// Date tokens are runs of non-delimiter octets.
    private static func tokens(_ bytes: [UInt8]) -> [ArraySlice<UInt8>] {
        var tokens: [ArraySlice<UInt8>] = []
        var start: Int?
        for index in 0...bytes.count {
            let delimiter = index == bytes.count || isDelimiter(bytes[index])
            if !delimiter && start == nil {
                start = index
            } else if delimiter, let first = start {
                tokens.append(bytes[first..<index])
                start = nil
            }
        }
        return tokens
    }

    /// delimiter = %x09 / %x20-2F / %x3B-40 / %x5B-60 / %x7B-7E
    private static func isDelimiter(_ byte: UInt8) -> Bool {
        byte == 0x09 || (0x20...0x2F).contains(byte) || (0x3B...0x40).contains(byte)
            || (0x5B...0x60).contains(byte) || (0x7B...0x7E).contains(byte)
    }

    /// time = hms-time ( non-digit *OCTET ), with each time-field 1*2DIGIT.
    private static func time(_ token: ArraySlice<UInt8>) -> (Int, Int, Int)? {
        var fields = [0, 0, 0]
        var position = token.startIndex
        for field in 0..<3 {
            let start = position
            while position < token.endIndex && position - start < 2 && Ascii.isDigit(token[position]) {
                position += 1
            }
            if position == start {
                return nil
            }
            fields[field] = number(token[start..<position])
            let more = position < token.endIndex
            if field < 2 {
                if !more || token[position] != UInt8(ascii: ":") {
                    return nil
                }
                position += 1
            } else if more && Ascii.isDigit(token[position]) {
                return nil
            }
        }
        return (fields[0], fields[1], fields[2])
    }

    /// min*maxDIGIT ( non-digit *OCTET ), for day-of-month and year.
    private static func leadingNumber(_ token: ArraySlice<UInt8>, _ min: Int, _ max: Int) -> Int {
        let digits = token.prefix(while: Ascii.isDigit)
        return digits.count < min || digits.count > max ? -1 : number(digits)
    }

    private static func number(_ digits: ArraySlice<UInt8>) -> Int {
        digits.reduce(0) { $0 * 10 + Int($1 - 0x30) }
    }

    private static func monthOf(_ token: ArraySlice<UInt8>) -> Int {
        guard token.count >= 3 else {
            return -1
        }
        let prefix = token.prefix(3).map(Ascii.lowerByte)
        return months.firstIndex(of: prefix).map { $0 + 1 } ?? -1
    }

    static func daysInMonth(_ year: Int, _ month: Int) -> Int {
        let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
        switch month {
        case 2: return leap ? 29 : 28
        case 4, 6, 9, 11: return 30
        default: return 31
        }
    }

    /// Days since 1970-01-01 for a proleptic Gregorian date (Howard Hinnant's days_from_civil).
    static func daysFromCivil(_ value: Int64, _ month: Int, _ day: Int) -> Int64 {
        let year = value - (month <= 2 ? 1 : 0)
        let era = (year >= 0 ? year : year - 399) / 400
        let yearOfEra = year - era * 400
        let dayOfYear = (153 * Int64(month > 2 ? month - 3 : month + 9) + 2) / 5 + Int64(day) - 1
        let dayOfEra = yearOfEra * 365 + yearOfEra / 4 - yearOfEra / 100 + dayOfYear
        return era * 146_097 + dayOfEra - 719_468
    }
}
