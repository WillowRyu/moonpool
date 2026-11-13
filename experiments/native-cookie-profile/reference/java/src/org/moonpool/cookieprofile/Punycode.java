package org.moonpool.cookieprofile;

/**
 * RFC 3492 Punycode encoder, used once to turn Unicode Public Suffix List labels into A-labels.
 *
 * <p>It is written out instead of calling {@code java.net.IDN} because iOS has no matching API, and both SDKs must
 * compute the same labels from the same PSL bytes. It applies no Unicode mapping or case folding: the pinned
 * snapshot's Unicode labels are already normalized, which the self-test checks against the JDK's IDNA conversion.
 */
public final class Punycode {
    private static final int BASE = 36;
    private static final int T_MIN = 1;
    private static final int T_MAX = 26;
    private static final int SKEW = 38;
    private static final int DAMP = 700;
    private static final int INITIAL_BIAS = 72;
    private static final int INITIAL_N = 0x80;

    private Punycode() {}

    /** A lowercase ASCII label stays as is. Any other label becomes {@code xn--} plus its Punycode. */
    public static String toALabel(String label) {
        for (int index = 0; index < label.length(); index++) {
            if (label.charAt(index) >= 0x80) {
                return "xn--" + encode(label);
            }
        }
        return Ascii.lower(label);
    }

    /** RFC 3492 section 6.3, over code points. Basic code points keep their case, as the RFC requires. */
    public static String encode(String input) {
        int[] points = input.codePoints().toArray();
        StringBuilder output = new StringBuilder();
        for (int point : points) {
            if (point < INITIAL_N) {
                output.append((char) point);
            }
        }
        int basic = output.length();
        int handled = basic;
        if (basic > 0) {
            output.append('-');
        }
        int n = INITIAL_N;
        long delta = 0;
        int bias = INITIAL_BIAS;
        while (handled < points.length) {
            int next = Integer.MAX_VALUE;
            for (int point : points) {
                if (point >= n && point < next) {
                    next = point;
                }
            }
            delta += (long) (next - n) * (handled + 1);
            n = next;
            for (int point : points) {
                if (point < n) {
                    delta++;
                }
                if (point == n) {
                    long q = delta;
                    for (int k = BASE; ; k += BASE) {
                        int t = k <= bias ? T_MIN : Math.min(k - bias, T_MAX);
                        if (q < t) {
                            break;
                        }
                        output.append(digit((int) (t + (q - t) % (BASE - t))));
                        q = (q - t) / (BASE - t);
                    }
                    output.append(digit((int) q));
                    bias = adapt(delta, handled + 1, handled == basic);
                    delta = 0;
                    handled++;
                }
            }
            if (delta > Integer.MAX_VALUE) {
                throw new IllegalArgumentException("Punycode overflow");
            }
            delta++;
            n++;
        }
        return output.toString();
    }

    private static int adapt(long delta, int points, boolean first) {
        delta = first ? delta / DAMP : delta / 2;
        delta += delta / points;
        int k = 0;
        while (delta > ((BASE - T_MIN) * T_MAX) / 2) {
            delta /= BASE - T_MIN;
            k += BASE;
        }
        return (int) (k + (BASE - T_MIN + 1) * delta / (delta + SKEW));
    }

    private static char digit(int value) {
        return (char) (value < 26 ? 'a' + value : '0' + value - 26);
    }
}
