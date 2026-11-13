package org.moonpool.cookieprofile;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * The pinned Public Suffix List of profile c04-1 (D2-A), with ICANN and PRIVATE rules evaluated together.
 *
 * <p>This data decides which services can share a domain cookie, so it is a SPEC section 9 boundary. Loading fails
 * instead of guessing: malformed UTF-8, a rule outside both sections, a missing section or an unexpected wildcard
 * stops the load.
 */
public final class PublicSuffixList {
    private static final String BEGIN_ICANN = "// ===BEGIN ICANN DOMAINS===";
    private static final String END_ICANN = "// ===END ICANN DOMAINS===";
    private static final String BEGIN_PRIVATE = "// ===BEGIN PRIVATE DOMAINS===";
    private static final String END_PRIVATE = "// ===END PRIVATE DOMAINS===";

    private final Set<String> rules = new HashSet<>();
    private final Set<String> exceptions = new HashSet<>();
    private int icannRules;
    private int privateRules;

    private PublicSuffixList() {}

    public static PublicSuffixList parse(byte[] utf8) {
        String text;
        try {
            text = StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(utf8))
                .toString();
        } catch (CharacterCodingException error) {
            throw new IllegalArgumentException("the PSL is not valid UTF-8", error);
        }

        PublicSuffixList list = new PublicSuffixList();
        String section = null;
        List<String> seen = new ArrayList<>();
        for (String line : split(text, '\n')) {
            if (line.startsWith("//")) {
                String marker = line.trim();
                switch (marker) {
                    case BEGIN_ICANN, BEGIN_PRIVATE -> {
                        if (section != null || seen.contains(marker)) {
                            throw new IllegalArgumentException("unexpected PSL marker " + marker);
                        }
                        section = marker;
                        seen.add(marker);
                    }
                    case END_ICANN, END_PRIVATE -> {
                        String begin = marker.equals(END_ICANN) ? BEGIN_ICANN : BEGIN_PRIVATE;
                        if (!begin.equals(section)) {
                            throw new IllegalArgumentException("unexpected PSL marker " + marker);
                        }
                        section = null;
                        seen.add(marker);
                    }
                    default -> { }
                }
                continue;
            }
            // The PSL format reads each line only up to its first whitespace.
            String rule = firstToken(line);
            if (rule.isEmpty()) {
                continue;
            }
            if (section == null) {
                throw new IllegalArgumentException("PSL rule outside the ICANN and PRIVATE sections: " + rule);
            }
            list.add(rule);
            if (section.equals(BEGIN_ICANN)) {
                list.icannRules++;
            } else {
                list.privateRules++;
            }
        }
        if (section != null || !seen.equals(List.of(BEGIN_ICANN, END_ICANN, BEGIN_PRIVATE, END_PRIVATE))) {
            throw new IllegalArgumentException("the PSL must contain one ICANN and then one PRIVATE section");
        }
        return list;
    }

    public int icannRules() {
        return icannRules;
    }

    public int privateRules() {
        return privateRules;
    }

    /**
     * The PSL formal algorithm for a canonical lowercase ASCII host. An exception rule prevails and loses its
     * leftmost label. Otherwise the matching rule with the most labels wins, and with no match the implicit
     * {@code *} rule makes the last label the suffix.
     */
    public String publicSuffix(String host) {
        String[] labels = split(host, '.').toArray(new String[0]);
        for (int index = 0; index < labels.length; index++) {
            if (exceptions.contains(join(labels, index))) {
                return join(labels, index + 1);
            }
        }
        for (int index = 0; index < labels.length; index++) {
            String candidate = join(labels, index);
            String wildcard = index + 1 < labels.length ? "*." + join(labels, index + 1) : "*";
            if (rules.contains(candidate) || rules.contains(wildcard)) {
                return candidate;
            }
        }
        return labels[labels.length - 1];
    }

    public boolean isPublicSuffix(String domain) {
        return publicSuffix(domain).equals(domain);
    }

    private void add(String rule) {
        boolean exception = rule.startsWith("!");
        List<String> labels = split(exception ? rule.substring(1) : rule, '.');
        StringBuilder key = new StringBuilder();
        for (int index = 0; index < labels.size(); index++) {
            String label = labels.get(index);
            boolean wildcard = label.equals("*");
            if (label.isEmpty() || (wildcard && (exception || index > 0)) || (!wildcard && label.contains("*"))) {
                throw new IllegalArgumentException("unsupported PSL rule " + rule);
            }
            if (index > 0) {
                key.append('.');
            }
            key.append(wildcard ? label : Punycode.toALabel(label));
        }
        (exception ? exceptions : rules).add(key.toString());
    }

    /** ASCII whitespace only, so a Unicode table difference between platforms cannot change a rule. */
    private static String firstToken(String line) {
        int end = 0;
        while (end < line.length() && " \t\r\u000b\f".indexOf(line.charAt(end)) < 0) {
            end++;
        }
        return line.substring(0, end);
    }

    private static String join(String[] labels, int start) {
        return String.join(".", java.util.Arrays.asList(labels).subList(start, labels.length));
    }

    /** Splits on one character and keeps empty pieces, unlike {@code String.split}. */
    static List<String> split(String text, char separator) {
        List<String> pieces = new ArrayList<>();
        int start = 0;
        for (int index = 0; index <= text.length(); index++) {
            if (index == text.length() || text.charAt(index) == separator) {
                pieces.add(text.substring(start, index));
                start = index + 1;
            }
        }
        return pieces;
    }
}
