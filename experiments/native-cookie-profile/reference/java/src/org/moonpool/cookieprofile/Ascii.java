package org.moonpool.cookieprofile;

/** ASCII-only text helpers, so neither platform's Unicode case or whitespace rules can change a result. */
final class Ascii {
    private Ascii() {}

    static String lower(String text) {
        StringBuilder result = new StringBuilder(text.length());
        for (int index = 0; index < text.length(); index++) {
            char c = text.charAt(index);
            result.append(c >= 'A' && c <= 'Z' ? (char) (c + ('a' - 'A')) : c);
        }
        return result.toString();
    }

    static boolean startsWithIgnoreCase(String text, String lowercasePrefix) {
        return text.length() >= lowercasePrefix.length()
            && lower(text.substring(0, lowercasePrefix.length())).equals(lowercasePrefix);
    }

    static boolean isDigit(char c) {
        return c >= '0' && c <= '9';
    }

    /** RFC 6265 WSP: space and horizontal tab. */
    static String trimWhitespace(String text) {
        int start = 0;
        int end = text.length();
        while (start < end && (text.charAt(start) == ' ' || text.charAt(start) == '\t')) {
            start++;
        }
        while (end > start && (text.charAt(end - 1) == ' ' || text.charAt(end - 1) == '\t')) {
            end--;
        }
        return text.substring(start, end);
    }
}
