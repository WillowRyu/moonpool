package org.moonpool.cookieprofile;

import java.util.ArrayList;
import java.util.List;

/**
 * RFC 6265 section 5.1.1 cookie-date parsing (D5). Calendar arithmetic is written out rather than taken from
 * {@code java.time}, so the Swift port can follow the same steps.
 */
public final class CookieDate {
    private static final String[] MONTHS = {
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    };

    private CookieDate() {}

    /** Epoch seconds in UTC, or {@code null} when the value fails the algorithm. */
    public static Long parse(String value) {
        int hour = -1;
        int minute = -1;
        int second = -1;
        int day = -1;
        int month = -1;
        int year = -1;
        for (String token : tokens(value)) {
            if (hour < 0) {
                int[] time = time(token);
                if (time != null) {
                    hour = time[0];
                    minute = time[1];
                    second = time[2];
                    continue;
                }
            }
            if (day < 0) {
                day = leadingNumber(token, 1, 2);
                if (day >= 0) {
                    continue;
                }
            }
            if (month < 0) {
                month = month(token);
                if (month > 0) {
                    continue;
                }
                month = -1;
            }
            if (year < 0) {
                year = leadingNumber(token, 2, 4);
            }
        }
        if (hour < 0 || day < 0 || month < 0 || year < 0) {
            return null;
        }
        if (year >= 70 && year <= 99) {
            year += 1900;
        } else if (year <= 69) {
            year += 2000;
        }
        if (day < 1 || day > 31 || year < 1601 || hour > 23 || minute > 59 || second > 59
                || day > daysInMonth(year, month)) {
            return null;
        }
        return daysFromCivil(year, month, day) * 86_400L + hour * 3_600L + minute * 60L + second;
    }

    /** Date tokens are runs of non-delimiter octets. */
    private static List<String> tokens(String value) {
        List<String> tokens = new ArrayList<>();
        int start = -1;
        for (int index = 0; index <= value.length(); index++) {
            boolean delimiter = index == value.length() || isDelimiter(value.charAt(index));
            if (!delimiter && start < 0) {
                start = index;
            } else if (delimiter && start >= 0) {
                tokens.add(value.substring(start, index));
                start = -1;
            }
        }
        return tokens;
    }

    /** delimiter = %x09 / %x20-2F / %x3B-40 / %x5B-60 / %x7B-7E */
    private static boolean isDelimiter(char c) {
        return c == 0x09 || (c >= 0x20 && c <= 0x2F) || (c >= 0x3B && c <= 0x40)
            || (c >= 0x5B && c <= 0x60) || (c >= 0x7B && c <= 0x7E);
    }

    /** time = hms-time ( non-digit *OCTET ), with each time-field 1*2DIGIT. */
    private static int[] time(String token) {
        int[] fields = new int[3];
        int position = 0;
        for (int field = 0; field < 3; field++) {
            int start = position;
            while (position < token.length() && position - start < 2 && Ascii.isDigit(token.charAt(position))) {
                position++;
            }
            if (position == start) {
                return null;
            }
            fields[field] = Integer.parseInt(token.substring(start, position));
            boolean more = position < token.length();
            if (field < 2) {
                if (!more || token.charAt(position) != ':') {
                    return null;
                }
                position++;
            } else if (more && Ascii.isDigit(token.charAt(position))) {
                return null;
            }
        }
        return fields;
    }

    /** min*maxDIGIT ( non-digit *OCTET ), for day-of-month and year. */
    private static int leadingNumber(String token, int min, int max) {
        int digits = 0;
        while (digits < token.length() && Ascii.isDigit(token.charAt(digits))) {
            digits++;
        }
        return digits < min || digits > max ? -1 : Integer.parseInt(token.substring(0, digits));
    }

    private static int month(String token) {
        if (token.length() < 3) {
            return -1;
        }
        String prefix = Ascii.lower(token.substring(0, 3));
        for (int index = 0; index < MONTHS.length; index++) {
            if (MONTHS[index].equals(prefix)) {
                return index + 1;
            }
        }
        return -1;
    }

    static int daysInMonth(int year, int month) {
        boolean leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
        return switch (month) {
            case 2 -> leap ? 29 : 28;
            case 4, 6, 9, 11 -> 30;
            default -> 31;
        };
    }

    /** Days since 1970-01-01 for a proleptic Gregorian date (Howard Hinnant's days_from_civil). */
    static long daysFromCivil(long year, int month, int day) {
        year -= month <= 2 ? 1 : 0;
        long era = (year >= 0 ? year : year - 399) / 400;
        long yearOfEra = year - era * 400;
        long dayOfYear = (153L * (month > 2 ? month - 3 : month + 9) + 2) / 5 + day - 1;
        long dayOfEra = yearOfEra * 365 + yearOfEra / 4 - yearOfEra / 100 + dayOfYear;
        return era * 146_097 + dayOfEra - 719_468;
    }
}
