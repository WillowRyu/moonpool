package org.moonpool.cookieprofile;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Feeds c04-1 fixture steps to the reference jar. The adapter does what a native broker would do around the
 * parser: read the request URL, supply the clock and translate results to JSON. Expected values stay in check.py.
 */
final class ReferenceAdapter {
    private static final Set<String> SET_FIELDS = Set.of("name", "value", "path", "maxAge");
    private static final DateTimeFormatter UTC =
        DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss'Z'", Locale.ROOT).withZone(ZoneOffset.UTC);

    public static void main(String[] args) throws Exception {
        PublicSuffixList publicSuffixes = PublicSuffixList.parse(pinned(Path.of(args[0]), args[1]));
        JSONArray cases = new JSONArray(new String(System.in.readAllBytes(), StandardCharsets.UTF_8));
        JSONArray results = new JSONArray();
        for (int index = 0; index < cases.length(); index++) {
            JSONObject vector = cases.getJSONObject(index);
            JSONArray observations = observe(new CookieJar(publicSuffixes), vector.getJSONArray("steps"));
            results.put(new JSONObject().put("id", vector.getString("id")).put("observations", observations));
        }
        System.out.println(results);
    }

    /** Parse only the bytes whose digest matches the profile, so the checked file is the one in use. */
    static byte[] pinned(Path path, String sha256) throws Exception {
        byte[] bytes = Files.readAllBytes(path);
        String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        if (!digest.equals(sha256)) {
            throw new IllegalArgumentException("PSL SHA-256 " + digest + " differs from " + sha256);
        }
        return bytes;
    }

    private static JSONArray observe(CookieJar jar, JSONArray steps) throws Exception {
        JSONArray observations = new JSONArray();
        for (int index = 0; index < steps.length(); index++) {
            JSONObject step = steps.getJSONObject(index);
            CookieJar.Request request = request(step.getString("url"));
            long now = Instant.parse(step.getString("now")).getEpochSecond();
            String operation = step.getString("op");
            switch (operation) {
                case "receive" -> {
                    jar.receive(strings(step.getJSONArray("fields")), request, now);
                    observations.put(JSONObject.NULL);
                }
                case "header" -> observations.put(jar.cookieHeader(request, now));
                case "read" -> observations.put(scriptView(jar.scriptCookies(request, now)));
                case "set" -> observations.put(set(jar, request, step.getJSONObject("fields"), now));
                // A snapshot does not remove expired entries, so the corpus sees what header and read removed.
                case "jar" -> observations.put(snapshot(jar.entries()));
                default -> throw new IllegalArgumentException("Unknown fixture operation " + operation);
            }
        }
        return observations;
    }

    /** OkHttp's encodedPath and URLComponents.percentEncodedPath are the D4 inputs. URI.getRawPath matches them. */
    private static CookieJar.Request request(String url) throws Exception {
        URI uri = new URI(url);
        if (!"https".equals(uri.getScheme()) || uri.getHost() == null) {
            throw new IllegalArgumentException("fixture URLs must be HTTPS service URLs: " + url);
        }
        return CookieJar.Request.of(uri.getHost(), uri.getRawPath() == null ? "" : uri.getRawPath());
    }

    private static List<String> strings(JSONArray values) {
        List<String> result = new ArrayList<>();
        for (int index = 0; index < values.length(); index++) {
            result.add(values.getString(index));
        }
        return result;
    }

    /** The research brokers' proposed cookies.set fields. Their bridge errors belong to T29. */
    private static boolean set(CookieJar jar, CookieJar.Request request, JSONObject fields, long now) {
        for (Iterator<String> keys = fields.keys(); keys.hasNext(); ) {
            if (!SET_FIELDS.contains(keys.next())) {
                return false;
            }
        }
        Object name = fields.opt("name");
        Object value = fields.opt("value");
        Object path = fields.opt("path");
        Object maxAge = fields.opt("maxAge");
        if (!(name instanceof String) || !(value instanceof String) || (path != null && !(path instanceof String))
                || (maxAge != null && !(maxAge instanceof Integer) && !(maxAge instanceof Long))) {
            return false;
        }
        Long seconds = maxAge == null ? null : ((Number) maxAge).longValue();
        return jar.setScriptCookie(request, (String) name, (String) value, (String) path, seconds, now);
    }

    private static JSONArray scriptView(List<CookieJar.Cookie> cookies) {
        JSONArray result = new JSONArray();
        for (CookieJar.Cookie cookie : cookies) {
            result.put(new JSONObject().put("name", cookie.name).put("value", cookie.value).put("path", cookie.path));
        }
        return result;
    }

    private static JSONArray snapshot(List<CookieJar.Cookie> cookies) {
        JSONArray result = new JSONArray();
        for (CookieJar.Cookie cookie : cookies) {
            result.put(new JSONObject()
                .put("name", cookie.name)
                .put("value", cookie.value)
                .put("domain", cookie.domain)
                .put("path", cookie.path)
                .put("hostOnly", cookie.hostOnly)
                .put("httpOnly", cookie.httpOnly)
                .put("expiresAt", cookie.expiresAt == null ? JSONObject.NULL
                    : UTC.format(Instant.ofEpochSecond(cookie.expiresAt)))
                .put("sameSite", switch (cookie.sameSite) {
                    case DEFAULT -> "default";
                    case STRICT -> "Strict";
                    case LAX -> "Lax";
                    case NONE -> "None";
                }));
        }
        return result;
    }
}
