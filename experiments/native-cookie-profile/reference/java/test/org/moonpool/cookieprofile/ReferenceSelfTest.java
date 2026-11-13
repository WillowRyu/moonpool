package org.moonpool.cookieprofile;

import java.net.IDN;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.regex.Pattern;

/**
 * Checks the reference parser's building blocks against independent sources: RFC 3492 samples,
 * the JDK's IDN and java.time, and the retained brokers' split regex. The c04-1 corpus covers
 * the cookie rules themselves.
 */
final class ReferenceSelfTest {
    /** The split both research brokers use (ADR 0027 rule 1). */
    private static final Pattern BROKER_SPLIT = Pattern.compile(",\\s*(?=[^;,=\\s]+=)");
    /** Distinct from the JVM's status 1 for an uncaught exception, which check.py reports as a setup error. */
    static final int CHECKS_FAILED = 3;

    private static int checks;
    private static final List<String> failures = new ArrayList<>();

    public static void main(String[] args) throws Exception {
        byte[] pinned = ReferenceAdapter.pinned(Path.of(args[0]), args[1]);
        punycode();
        requests();
        publicSuffixes(pinned);
        dates();
        civilDays();
        foldedSplit();
        if (!failures.isEmpty()) {
            failures.forEach(System.out::println);
            System.out.println("self-test: " + failures.size() + " of " + checks + " checks failed");
            System.exit(CHECKS_FAILED);
        }
        System.out.println("self-test: " + checks + " checks passed");
    }

    private static void expect(Object expected, Object observed, String label) {
        checks++;
        if (!java.util.Objects.equals(expected, observed)) {
            failures.add("FAIL " + label + ": expected " + expected + ", observed " + observed);
        }
    }

    private static String codePoints(int... points) {
        return new String(points, 0, points.length);
    }

    private static void punycode() {
        // RFC 3492 section 7.1 samples (A), (B), (L) and (S).
        expect("egbpdaj6bu4bxfgehfvwxn", Punycode.encode(codePoints(0x0644, 0x064A, 0x0647, 0x0645, 0x0627,
            0x0628, 0x062A, 0x0643, 0x0644, 0x0645, 0x0648, 0x0634, 0x0639, 0x0631, 0x0628, 0x064A, 0x061F)),
            "RFC 3492 sample A");
        expect("ihqwcrb4cv8a8dqg056pqjye", Punycode.encode(codePoints(0x4ED6, 0x4EEC, 0x4E3A, 0x4EC0, 0x4E48,
            0x4E0D, 0x8BF4, 0x4E2D, 0x6587)), "RFC 3492 sample B");
        expect("3B-ww4c5e180e575a65lsy2b", Punycode.encode(codePoints(0x0033, 0x5E74, 0x0042, 0x7D44, 0x91D1,
            0x516B, 0x5148, 0x751F)), "RFC 3492 sample L");
        expect("-> $1.00 <--", Punycode.encode("-> $1.00 <-"), "RFC 3492 sample S");
        expect("xn--55qx5d", Punycode.toALabel("公司"), "A-label for the D11 rule");
        expect("example", Punycode.toALabel("EXAMPLE"), "ASCII labels lowercase without a prefix");
    }

    private static void requests() {
        // URI.getHost() keeps IPv6 brackets and Foundation's URL.host drops them. Both must name the same jar host.
        String[][] hosts = {
            {"::1", "[::1]", "true"}, {"[::1]", "[::1]", "true"}, {"127.0.0.1", "127.0.0.1", "true"},
            {"API.Example.COM", "api.example.com", "false"}, {"xn--55qx5d.cn", "xn--55qx5d.cn", "false"},
        };
        for (String[] item : hosts) {
            CookieJar.Request request = CookieJar.Request.of(item[0], "");
            expect(item[1], request.host, "canonical host for " + item[0]);
            expect(Boolean.parseBoolean(item[2]), request.ip, "IP classification for " + item[0]);
            expect("/", request.path, "empty request path for " + item[0]);
        }

        // Accepted 2026-11-13 (contract §2): approval and the jar take only canonical hosts. A DNS name has no
        // empty label apart from one trailing dot. A last label that is a number makes the host IPv4, which must
        // then be four decimal octets with no leading zero and no trailing dot.
        String[][] accepted = {
            {"a.github.io.", "false"}, {"0.0.0.0", "true"}, {"255.255.255.255", "true"}, {"10.0.0.1", "true"},
            {"1a", "false"}, {"example.0xg", "false"}, {"shop.xn--55qx5d.cn", "false"},
        };
        for (String[] item : accepted) {
            try {
                expect(Boolean.parseBoolean(item[1]), CookieJar.Request.of(item[0], "").ip, "IP classification for " + item[0]);
            } catch (IllegalArgumentException refused) {
                expect("accepted", "refused", "canonical host " + item[0]);
            }
        }
        String[] refused = {
            "a..example.com", ".example.com", "example.com..", ".", "127.0.0.1.", "127.1", "0x7f.0.0.1",
            "010.0.0.1", "256.0.0.1", "1.2.3.4.5", "example.123", "a.0x", "a.0X1F",
        };
        for (String host : refused) {
            String outcome;
            try {
                CookieJar.Request.of(host, "");
                outcome = "accepted";
            } catch (IllegalArgumentException expected) {
                outcome = "refused";
            }
            expect("refused", outcome, "non-canonical host " + host);
        }
    }

    private static void publicSuffixes(byte[] pinned) throws Exception {
        PublicSuffixList list = PublicSuffixList.parse(pinned);
        expect(6951, list.icannRules(), "ICANN rule count in c04-1");
        expect(3463, list.privateRules(), "PRIVATE rule count in c04-1");

        // The SDKs convert with their own encoder. Here the JDK's IDNA2003 conversion must agree on every Unicode
        // label. Its Unicode 3.2 tables reject newer scripts unless unassigned code points are allowed.
        int unicodeLabels = 0;
        int newerThanIdna2003 = 0;
        for (String line : new String(pinned, StandardCharsets.UTF_8).split("\n", -1)) {
            if (line.isEmpty() || line.startsWith("//")) {
                continue;
            }
            for (String label : line.replace("!", "").split("\\.", -1)) {
                if (label.chars().allMatch(c -> c < 0x80)) {
                    continue;
                }
                unicodeLabels++;
                try {
                    IDN.toASCII(label, 0);
                } catch (IllegalArgumentException unassigned) {
                    newerThanIdna2003++;
                }
                expect(IDN.toASCII(label, IDN.ALLOW_UNASSIGNED).toLowerCase(Locale.ROOT), Punycode.toALabel(label),
                    "A-label " + label);
            }
        }
        System.out.println("self-test: " + unicodeLabels + " Unicode PSL labels match java.net.IDN; "
            + newerThanIdna2003 + " need its ALLOW_UNASSIGNED flag");

        // check.py compares this line with the Swift port's, so both ports must build the same rule set.
        List<String> canonical = list.canonicalRules();
        byte[] digest = java.security.MessageDigest.getInstance("SHA-256")
            .digest(String.join("\n", canonical).getBytes(StandardCharsets.UTF_8));
        System.out.println("self-test: " + canonical.size() + " canonical PSL rules");
        System.out.println("self-test: PSL rules sha256 " + java.util.HexFormat.of().formatHex(digest));

        String[][] cases = {
            {"co.uk", "co.uk"}, {"shop.co.uk", "co.uk"}, {"example.com", "com"}, {"api.example.com", "com"},
            {"foo.ck", "foo.ck"}, {"shop.foo.ck", "foo.ck"}, {"www.ck", "ck"}, {"shop.www.ck", "ck"},
            {"test", "test"}, {"shop.test", "test"}, {"github.io", "github.io"}, {"shop.github.io", "github.io"},
            {"xn--55qx5d.cn", "xn--55qx5d.cn"}, {"abyme.dev", "abyme.dev"},
            // The PSL format ignores one trailing dot, and the result keeps it. Other empty labels fail closed.
            {"github.io.", "github.io."}, {"a.github.io.", "github.io."}, {"co.uk.", "co.uk."},
            {"example.com.", "com."}, {"github.io..", "github.io.."}, {".github.io", ".github.io"},
            {"a..b.example", "a..b.example"},
        };
        for (String[] item : cases) {
            expect(item[1], list.publicSuffix(item[0]), "public suffix of " + item[0]);
        }
    }

    private static Long utc(int year, int month, int day, int hour, int minute, int second) {
        return ZonedDateTime.of(year, month, day, hour, minute, second, 0, ZoneOffset.UTC).toEpochSecond();
    }

    private static void dates() {
        Long nov1994 = utc(1994, 11, 6, 8, 49, 37);
        Object[][] cases = {
            // RFC 7231 section 7.1.1.1 forms, all of which RFC 6265 section 5.1.1 accepts.
            {"Sun, 06 Nov 1994 08:49:37 GMT", nov1994},
            {"Sunday, 06-Nov-94 08:49:37 GMT", nov1994},
            {"Sun Nov  6 08:49:37 1994", nov1994},
            // Tokens can come in any order. A two-digit year 70-99 means 19xx, 0-69 means 20xx.
            {"1994 Nov 06 08:49:37", nov1994},
            {"Wed, 21 Oct 70 07:28:00 GMT", utc(1970, 10, 21, 7, 28, 0)},
            {"Wed, 21 Oct 69 07:28:00 GMT", utc(2069, 10, 21, 7, 28, 0)},
            {"Wed, 21 Oct 2099 07:28:00 GMT", utc(2099, 10, 21, 7, 28, 0)},
            {"29 Feb 2028 00:00:00", utc(2028, 2, 29, 0, 0, 0)},
            {"1 jAnUaRy 1601 0:0:0", utc(1601, 1, 1, 0, 0, 0)},
            {"31 Dec 9999 23:59:59", utc(9999, 12, 31, 23, 59, 59)},
            // Rejections under section 5.1.1 step 5, and dates that do not exist.
            {"tomorrow", null},
            {"Wed, 21 Oct 2015 GMT", null},
            {"Wed, 21 Oct 1600 07:28:00 GMT", null},
            {"Wed, 32 Oct 2015 07:28:00 GMT", null},
            {"Wed, 00 Oct 2015 07:28:00 GMT", null},
            {"Wed, 21 Oct 2015 24:00:00 GMT", null},
            {"Wed, 21 Oct 2015 07:60:00 GMT", null},
            {"Wed, 21 Oct 2015 07:28:60 GMT", null},
            {"29 Feb 2026 00:00:00", null},
            {"31 Apr 2026 00:00:00", null},
            // A three-digit time field or day does not match its production.
            {"Wed, 21 Oct 2015 07:28:000 GMT", null},
            {"Wed, 210 Oct 2015 07:28:00 GMT", null},
        };
        for (Object[] item : cases) {
            expect(item[1], CookieDate.parse((String) item[0]), "date " + item[0]);
        }
    }

    private static void civilDays() {
        // Day arithmetic is hand-written so Swift can share it. Compare it with java.time across the accepted range.
        int differences = 0;
        for (int year = 1601; year <= 9999; year++) {
            for (int month = 1; month <= 12; month++) {
                int last = LocalDate.of(year, month, 1).lengthOfMonth();
                boolean same = last == CookieDate.daysInMonth(year, month)
                    && LocalDate.of(year, month, last).toEpochDay() == CookieDate.daysFromCivil(year, month, last);
                if (!same && differences++ < 5) {
                    failures.add("FAIL calendar differs from java.time at " + year + "-" + month);
                }
            }
        }
        checks++;
        if (differences > 0) {
            failures.add("FAIL " + differences + " months from 1601 to 9999 differ from java.time");
        }
    }

    private static void foldedSplit() {
        String[] samples = {
            "", "a=1", "a=1, b=2", "a=1,b=2", "sid=abc, x=y; Path=/; HttpOnly",
            "a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT", "a=1, =x", "a=1, ;b=2", "a=1,\tb=2", "a=1,  b=2",
            "a=1; Foo=é, keep=1", ",b=2", "a=1,,b=2",
        };
        for (String sample : samples) {
            expect(Arrays.asList(BROKER_SPLIT.split(sample)), CookieJar.splitFolded(sample), "split " + sample);
        }
        // A seeded search over the characters the regex treats specially. U+00A0 is outside Java's ASCII \s.
        char[] alphabet = {'a', 'b', '=', ';', ',', ' ', '\t', '\u000b', 'é', ' '};
        Random random = new Random(20261111L);
        int differences = 0;
        for (int round = 0; round < 200_000; round++) {
            char[] text = new char[random.nextInt(14)];
            for (int index = 0; index < text.length; index++) {
                text[index] = alphabet[random.nextInt(alphabet.length)];
            }
            String sample = new String(text);
            if (!Arrays.asList(BROKER_SPLIT.split(sample)).equals(CookieJar.splitFolded(sample)) && differences++ < 5) {
                failures.add("FAIL split differs for " + sample.replace("\t", "\\t"));
            }
        }
        checks++;
        if (differences > 0) {
            failures.add("FAIL " + differences + " seeded split samples differ from the broker regex");
        }
    }
}
