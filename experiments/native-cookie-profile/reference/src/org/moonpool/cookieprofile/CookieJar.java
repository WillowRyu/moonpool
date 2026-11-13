package org.moonpool.cookieprofile;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * One mini app's cookie jar under profile c04-1. This is the reference for the shared parser (ADR 0027): Android and
 * iOS adapters fold received {@code Set-Cookie} fields, and this class splits, parses, stores and selects them.
 *
 * <p>Callers supply the request host, the percent-encoded request path and the current time in epoch seconds. The
 * jar has no clock, no I/O and no platform cookie API. Approval of service origins stays with the broker (contract
 * section 2): every request given to this class is an approved HTTPS service URL of the same mini app.
 *
 * <p>Domain, public-suffix, prefix and {@code HttpOnly} rules here decide which service receives a session cookie
 * and what a script can read or plant, so this class is a SPEC section 9 boundary.
 */
public final class CookieJar {
    /** D5: persistent expiry is capped at 400 days after receipt. */
    public static final long LIFETIME_CAP_SECONDS = 400L * 24 * 60 * 60;
    /** D1: limit on the trimmed name plus value. */
    static final int MAX_NAME_VALUE_OCTETS = 4096;
    /** D1: attributes with a longer trimmed value are ignored. */
    static final int MAX_ATTRIBUTE_VALUE_OCTETS = 1024;

    public enum SameSite { DEFAULT, STRICT, LAX, NONE }

    /** The request host and the path exactly as sent on the wire (D4). */
    public static final class Request {
        final String host;
        final String path;
        final boolean ip;

        private Request(String host, String path, boolean ip) {
            this.host = host;
            this.path = path;
            this.ip = ip;
        }

        /** The adapter's URL parser has already canonicalized the host. An empty path means {@code /}. */
        public static Request of(String host, String encodedPath) {
            if (host.isEmpty() || !isVisibleAscii(host)) {
                throw new IllegalArgumentException("request host must be canonical ASCII: " + host);
            }
            String path = encodedPath.isEmpty() ? "/" : encodedPath;
            if (path.charAt(0) != '/' || !isVisibleAscii(path)) {
                throw new IllegalArgumentException("request path must be percent-encoded and absolute: " + path);
            }
            String canonical = Ascii.lower(host);
            return new Request(canonical, path, canonical.startsWith("[") || isIpv4(canonical));
        }
    }

    /** A stored cookie. D3-B identity is name, domain, path and host-only. */
    public static final class Cookie {
        public final String name;
        public final String value;
        public final String domain;
        public final String path;
        public final boolean hostOnly;
        public final boolean httpOnly;
        public final boolean secure;
        public final SameSite sameSite;
        /** Epoch seconds, or {@code null} for a session cookie. */
        public final Long expiresAt;
        /** D8: assigned to each new identity and kept when that identity is replaced. */
        final long creation;

        Cookie(String name, String value, String domain, String path, boolean hostOnly, boolean httpOnly,
               boolean secure, SameSite sameSite, Long expiresAt, long creation) {
            this.name = name;
            this.value = value;
            this.domain = domain;
            this.path = path;
            this.hostOnly = hostOnly;
            this.httpOnly = httpOnly;
            this.secure = secure;
            this.sameSite = sameSite;
            this.expiresAt = expiresAt;
            this.creation = creation;
        }

        boolean expired(long now) {
            return expiresAt != null && expiresAt <= now;
        }
    }

    /** One split line after RFC 6265 section 5.2 parsing under D1. */
    private static final class Line {
        String name;
        String value;
        Long expires;
        Long maxAge;
        boolean domainPresent;
        String domain;
        String path;
        boolean secure;
        boolean httpOnly;
        SameSite sameSite = SameSite.DEFAULT;
    }

    private final PublicSuffixList publicSuffixes;
    private final List<Cookie> entries = new ArrayList<>();
    private long nextCreation;

    public CookieJar(PublicSuffixList publicSuffixes) {
        this.publicSuffixes = publicSuffixes;
    }

    /** Header fields from one response, in order. The adapter's fold-then-split rule applies to them together. */
    public void receive(List<String> fields, Request request, long now) {
        removeExpired(now);
        for (String line : splitFolded(String.join(", ", fields))) {
            store(line, request, now);
        }
    }

    /**
     * ADR 0027 rule 1: split where a comma, optional whitespace and {@code name=} follow. This is the regex
     * {@code ,\s*(?=[^;,=\s]+=)} of both research brokers, written out with Java's ASCII {@code \s} so that
     * NSRegularExpression's Unicode whitespace cannot split differently on iOS.
     */
    public static List<String> splitFolded(String folded) {
        List<String> lines = new ArrayList<>();
        int start = 0;
        int index = 0;
        while (index < folded.length()) {
            if (folded.charAt(index) == ',') {
                int name = index + 1;
                while (name < folded.length() && isRegexSpace(folded.charAt(name))) {
                    name++;
                }
                int end = name;
                while (end < folded.length() && ";,=".indexOf(folded.charAt(end)) < 0 && !isRegexSpace(folded.charAt(end))) {
                    end++;
                }
                if (end > name && end < folded.length() && folded.charAt(end) == '=') {
                    lines.add(folded.substring(start, index));
                    start = name;
                    index = name;
                    continue;
                }
            }
            index++;
        }
        lines.add(folded.substring(start));
        return lines;
    }

    /** D8: matching cookies, longer path first, then earlier creation, as {@code name=value} pairs. */
    public String cookieHeader(Request request, long now) {
        removeExpired(now);
        StringBuilder header = new StringBuilder();
        for (Cookie cookie : matching(request)) {
            if (header.length() > 0) {
                header.append("; ");
            }
            header.append(cookie.name).append('=').append(cookie.value);
        }
        return header.toString();
    }

    /** The {@code cookies.get} view: the same selection and order without {@code HttpOnly} entries. */
    public List<Cookie> scriptCookies(Request request, long now) {
        removeExpired(now);
        List<Cookie> readable = new ArrayList<>();
        for (Cookie cookie : matching(request)) {
            if (!cookie.httpOnly) {
                readable.add(cookie);
            }
        }
        return readable;
    }

    /**
     * The research brokers' proposed structured {@code cookies.set}: a host-only cookie for the request host, path
     * {@code /} by default, and a positive {@code maxAge} capped like a response cookie. It rejects both prefixes
     * (D6) and any protected entry of the same identity. T29 owns the public schema and error codes.
     */
    public boolean setScriptCookie(Request request, String name, String value, String path, Long maxAge, long now) {
        removeExpired(now);
        if (!isToken(name) || !isCookieValue(value) || (path != null && !isScriptPath(path))
                || name.length() + value.length() > MAX_NAME_VALUE_OCTETS
                || (path != null && path.length() > MAX_ATTRIBUTE_VALUE_OCTETS)) {
            return false;
        }
        if (Ascii.startsWithIgnoreCase(name, "__secure-") || Ascii.startsWithIgnoreCase(name, "__host-")) {
            return false;
        }
        String cookiePath = path == null ? "/" : path;
        Cookie existing = find(name, request.host, cookiePath, true);
        if (existing != null && existing.httpOnly) {
            return false;
        }
        Long expiresAt = maxAge == null ? null : now + Math.max(0, Math.min(maxAge, LIFETIME_CAP_SECONDS));
        commit(existing, new Cookie(name, value, request.host, cookiePath, true, false, false, SameSite.DEFAULT,
            expiresAt, 0), now);
        return true;
    }

    /** Stored entries in insertion order, including any expired entry no operation has removed yet. */
    public List<Cookie> entries() {
        return Collections.unmodifiableList(new ArrayList<>(entries));
    }

    private void store(String text, Request request, long now) {
        Line line = parse(text);
        if (line == null) {
            return;
        }

        // D2: canonicalize Domain, then require the request host to be inside it. IP hosts accept only themselves.
        String domain = request.host;
        boolean hostOnly = true;
        if (line.domain != null) {
            String canonical = Ascii.lower(line.domain.startsWith(".") ? line.domain.substring(1) : line.domain);
            if (!canonical.isEmpty()) {
                if (request.ip) {
                    if (!canonical.equals(request.host)) {
                        return;
                    }
                } else {
                    if (!canonical.equals(request.host) && !request.host.endsWith("." + canonical)) {
                        return;
                    }
                    if (!publicSuffixes.isPublicSuffix(canonical)) {
                        domain = canonical;
                        hostOnly = false;
                    } else if (!canonical.equals(request.host)) {
                        return;
                    }
                }
            }
        }

        // RFC 6265 section 5.2.4: an invalid Path attribute means the default path.
        String path = line.path != null ? line.path : defaultPath(request.path);

        // D7: every service request is HTTPS, so Secure is always allowed, and SameSite=None needs it.
        if (line.sameSite == SameSite.NONE && !line.secure) {
            return;
        }
        // D6, before any commit or expiry deletion. __Host- needs an explicit Path=/ and no Domain attribute at all.
        if (Ascii.startsWithIgnoreCase(line.name, "__secure-") && !line.secure) {
            return;
        }
        if (Ascii.startsWithIgnoreCase(line.name, "__host-")
                && (!line.secure || line.domainPresent || !"/".equals(line.path))) {
            return;
        }

        // D5: the last valid Max-Age wins over the last valid Expires; both are capped at 400 days after receipt.
        Long expiresAt = null;
        if (line.maxAge != null) {
            expiresAt = now + line.maxAge;
        } else if (line.expires != null) {
            expiresAt = Math.min(line.expires, now + LIFETIME_CAP_SECONDS);
        }
        Cookie existing = find(line.name, domain, path, hostOnly);
        commit(existing, new Cookie(line.name, line.value, domain, path, hostOnly, line.httpOnly, line.secure,
            line.sameSite, expiresAt, 0), now);
    }

    /** Replace the identity, keeping its creation order, or delete it when the new expiry is not in the future. */
    private void commit(Cookie existing, Cookie cookie, long now) {
        if (existing != null) {
            entries.remove(existing);
        }
        if (cookie.expired(now)) {
            return;
        }
        long creation = existing != null ? existing.creation : nextCreation++;
        entries.add(new Cookie(cookie.name, cookie.value, cookie.domain, cookie.path, cookie.hostOnly,
            cookie.httpOnly, cookie.secure, cookie.sameSite, cookie.expiresAt, creation));
    }

    /** RFC 6265 section 5.2 with the D1 character and size rules. {@code null} rejects the whole line. */
    private static Line parse(String text) {
        for (int index = 0; index < text.length(); index++) {
            char c = text.charAt(index);
            if (c != '\t' && (c < 0x20 || c > 0x7E)) {
                return null;
            }
        }
        int semicolon = text.indexOf(';');
        String pair = semicolon < 0 ? text : text.substring(0, semicolon);
        int equals = pair.indexOf('=');
        if (equals < 0) {
            return null;
        }
        Line line = new Line();
        line.name = Ascii.trimWhitespace(pair.substring(0, equals));
        line.value = Ascii.trimWhitespace(pair.substring(equals + 1));
        if (line.name.isEmpty() || line.name.length() + line.value.length() > MAX_NAME_VALUE_OCTETS) {
            return null;
        }
        if (semicolon < 0) {
            return line;
        }
        for (String attribute : PublicSuffixList.split(text.substring(semicolon + 1), ';')) {
            int separator = attribute.indexOf('=');
            String key = Ascii.lower(Ascii.trimWhitespace(separator < 0 ? attribute : attribute.substring(0, separator)));
            String value = separator < 0 ? "" : Ascii.trimWhitespace(attribute.substring(separator + 1));
            if (value.length() > MAX_ATTRIBUTE_VALUE_OCTETS) {
                continue;
            }
            switch (key) {
                case "expires" -> {
                    Long date = CookieDate.parse(value);
                    if (date != null) {
                        line.expires = date;
                    }
                }
                case "max-age" -> {
                    Long seconds = maxAge(value);
                    if (seconds != null) {
                        line.maxAge = seconds;
                    }
                }
                case "domain" -> {
                    // An empty value is ignored for scope (D2), but __Host- still treats it as present (D6).
                    line.domainPresent = true;
                    if (!value.isEmpty()) {
                        line.domain = value;
                    }
                }
                case "path" -> line.path = value.startsWith("/") ? value : null;
                case "secure" -> line.secure = true;
                case "httponly" -> line.httpOnly = true;
                case "samesite" -> line.sameSite = switch (Ascii.lower(value)) {
                    case "strict" -> SameSite.STRICT;
                    case "lax" -> SameSite.LAX;
                    case "none" -> SameSite.NONE;
                    default -> SameSite.DEFAULT;
                };
                default -> { } // D9: Partitioned, Priority and other attributes are ignored.
            }
        }
        return line;
    }

    /** D5: one or more ASCII digits with an optional leading {@code -}, saturated to {@code [0, cap]}. */
    private static Long maxAge(String value) {
        boolean negative = value.startsWith("-");
        String digits = negative ? value.substring(1) : value;
        if (digits.isEmpty()) {
            return null;
        }
        long seconds = 0;
        for (int index = 0; index < digits.length(); index++) {
            char c = digits.charAt(index);
            if (!Ascii.isDigit(c)) {
                return null;
            }
            seconds = Math.min(seconds * 10 + (c - '0'), LIFETIME_CAP_SECONDS);
        }
        return negative ? 0L : seconds;
    }

    private void removeExpired(long now) {
        entries.removeIf(cookie -> cookie.expired(now));
    }

    private Cookie find(String name, String domain, String path, boolean hostOnly) {
        for (Cookie cookie : entries) {
            if (cookie.name.equals(name) && cookie.domain.equals(domain) && cookie.path.equals(path)
                    && cookie.hostOnly == hostOnly) {
                return cookie;
            }
        }
        return null;
    }

    private List<Cookie> matching(Request request) {
        List<Cookie> found = new ArrayList<>();
        for (Cookie cookie : entries) {
            if (domainMatches(cookie, request) && pathMatches(request.path, cookie.path)) {
                found.add(cookie);
            }
        }
        found.sort((a, b) -> a.path.length() != b.path.length()
            ? Integer.compare(b.path.length(), a.path.length())
            : Long.compare(a.creation, b.creation));
        return found;
    }

    /** A host-only cookie needs the exact host. A domain cookie also matches DNS subdomains at a dot boundary. */
    private static boolean domainMatches(Cookie cookie, Request request) {
        if (cookie.hostOnly) {
            return request.host.equals(cookie.domain);
        }
        return !request.ip && (request.host.equals(cookie.domain) || request.host.endsWith("." + cookie.domain));
    }

    /** RFC 6265 section 5.1.4 over the encoded request path (D4). */
    static boolean pathMatches(String requestPath, String cookiePath) {
        if (requestPath.equals(cookiePath)) {
            return true;
        }
        return requestPath.startsWith(cookiePath)
            && (cookiePath.endsWith("/") || requestPath.charAt(cookiePath.length()) == '/');
    }

    /** RFC 6265 section 5.1.4 default-path, over the encoded request path (D4). */
    static String defaultPath(String requestPath) {
        int last = requestPath.lastIndexOf('/');
        return last <= 0 ? "/" : requestPath.substring(0, last);
    }

    /** Java's {@code \s} without UNICODE_CHARACTER_CLASS. */
    private static boolean isRegexSpace(char c) {
        return c == ' ' || c == '\t' || c == '\n' || c == '\u000b' || c == '\f' || c == '\r';
    }

    private static boolean isVisibleAscii(String text) {
        for (int index = 0; index < text.length(); index++) {
            if (text.charAt(index) <= 0x20 || text.charAt(index) >= 0x7F) {
                return false;
            }
        }
        return true;
    }

    /** Four dotted decimal octets. Bracketed IPv6 is recognized by {@link Request#of}. */
    private static boolean isIpv4(String host) {
        List<String> parts = PublicSuffixList.split(host, '.');
        if (parts.size() != 4) {
            return false;
        }
        for (String part : parts) {
            if (part.isEmpty() || part.length() > 3) {
                return false;
            }
            for (int index = 0; index < part.length(); index++) {
                if (!Ascii.isDigit(part.charAt(index))) {
                    return false;
                }
            }
            if (Integer.parseInt(part) > 255) {
                return false;
            }
        }
        return true;
    }

    /** RFC 9110 token, as the research brokers require for script cookie names. */
    private static boolean isToken(String text) {
        if (text.isEmpty()) {
            return false;
        }
        for (int index = 0; index < text.length(); index++) {
            char c = text.charAt(index);
            if (!(Ascii.isDigit(c) || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                    || "!#$%&'*+-.^_`|~".indexOf(c) >= 0)) {
                return false;
            }
        }
        return true;
    }

    /** RFC 6265 cookie-octet, so a script value cannot add a pair beside a protected cookie. */
    private static boolean isCookieValue(String text) {
        for (int index = 0; index < text.length(); index++) {
            char c = text.charAt(index);
            if (!(c == 0x21 || (c >= 0x23 && c <= 0x2B) || (c >= 0x2D && c <= 0x3A) || (c >= 0x3C && c <= 0x5B)
                    || (c >= 0x5D && c <= 0x7E))) {
                return false;
            }
        }
        return true;
    }

    /** {@code /} then visible ASCII and space without {@code ;}. */
    private static boolean isScriptPath(String text) {
        if (!text.startsWith("/")) {
            return false;
        }
        for (int index = 1; index < text.length(); index++) {
            char c = text.charAt(index);
            if (c < 0x20 || c > 0x7E || c == ';') {
                return false;
            }
        }
        return true;
    }
}
