import java.io.PrintStream;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.List;
import okhttp3.Cookie;
import okhttp3.HttpUrl;

/**
 * Feeds each vector to OkHttp's public cookie parser and prints one JSON object per line.
 * Only public API: Cookie.parse, Cookie.matches and HttpUrl.get. OkHttp has no cookie store,
 * so this measures parsing and matching, never replacement, ordering or eviction.
 */
public final class ParseProbe {
  public static void main(String[] args) throws Exception {
    PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
    List<String> rows = Files.readAllLines(Path.of(args[0]), StandardCharsets.UTF_8);
    for (String row : rows) {
      String[] parts = row.split("\t", -1);
      out.println(observe(parts[0], decode(parts[1]), decode(parts[2]), decode(parts[3])));
    }
  }

  private static String decode(String text) {
    return new String(Base64.getDecoder().decode(text), StandardCharsets.UTF_8);
  }

  private static String observe(String id, String url, String line, String checks) {
    StringBuilder json = new StringBuilder("{\"id\":").append(quote(id));
    try {
      Cookie cookie = Cookie.parse(HttpUrl.get(url), line);
      json.append(",\"accepted\":").append(cookie != null);
      if (cookie != null) {
        json.append(",\"cookie\":{")
            .append("\"name\":").append(quote(cookie.name()))
            .append(",\"value\":").append(quote(cookie.value()))
            .append(",\"domain\":").append(quote(cookie.domain()))
            .append(",\"path\":").append(quote(cookie.path()))
            .append(",\"hostOnly\":").append(cookie.hostOnly())
            .append(",\"httpOnly\":").append(cookie.httpOnly())
            .append(",\"secure\":").append(cookie.secure())
            .append(",\"persistent\":").append(cookie.persistent())
            .append(",\"expiresAt\":").append(cookie.expiresAt());
        String sameSite = sameSite(cookie);
        if (sameSite != null) json.append(",\"sameSite\":").append(quote(sameSite));
        json.append("},\"sends\":[");
        if (!checks.isEmpty()) {
          String[] targets = checks.split("\n");
          for (int i = 0; i < targets.length; i++) {
            if (i > 0) json.append(',');
            json.append(cookie.matches(HttpUrl.get(targets[i])));
          }
        }
        json.append(']');
      }
    } catch (RuntimeException error) {
      json.append(",\"error\":").append(quote(error.getClass().getName() + ": " + error.getMessage()));
    }
    return json.append('}').toString();
  }

  /** Read through reflection so the probe still compiles if a version lacks the accessor; absent means "not reported". */
  private static String sameSite(Cookie cookie) {
    try {
      Method accessor = Cookie.class.getMethod("sameSite");
      return (String) accessor.invoke(cookie);
    } catch (ReflectiveOperationException missing) {
      return null;
    }
  }

  private static String quote(String text) {
    StringBuilder out = new StringBuilder("\"");
    for (char c : text.toCharArray()) {
      switch (c) {
        case '"' -> out.append("\\\"");
        case '\\' -> out.append("\\\\");
        default -> {
          if (c < 0x20 || c == 0x7f) out.append(String.format("\\u%04x", (int) c));
          else out.append(c);
        }
      }
    }
    return out.append('"').toString();
  }
}
