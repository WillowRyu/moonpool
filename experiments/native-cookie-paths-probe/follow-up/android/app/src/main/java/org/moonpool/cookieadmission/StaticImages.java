package org.moonpool.cookieadmission;

import java.io.IOException;
import java.util.Map;
import java.util.Set;
import okhttp3.Authenticator;
import okhttp3.CookieJar;
import okhttp3.HttpUrl;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

/** Fixture-only native loader with explicit, rechecked redirect hops. */
final class StaticImages {
    private static final Map<String, String> START = Map.of(
        "direct", "/static/direct.gif", "approved", "/static/redirect-approved",
        "path", "/static/redirect-path", "other", "/static/redirect-other",
        "encoded", "/static/redirect-encoded");
    private static final Set<String> ALLOWED = Set.of(
        "/static/direct.gif", "/static/redirect-approved", "/static/redirect-path",
        "/static/redirect-other", "/static/redirect-encoded", "/static/final.gif");
    private final HttpUrl origin;
    private final String run;
    private final OkHttpClient client = new OkHttpClient.Builder()
        .followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false)
        .cookieJar(CookieJar.NO_COOKIES).authenticator(Authenticator.NONE)
        .proxyAuthenticator(Authenticator.NONE).cache(null).build();

    StaticImages(HttpUrl origin, String run) {
        this.origin = origin;
        this.run = run;
    }

    byte[] get(String name) throws IOException {
        String path = START.get(name);
        if (path == null) return null;
        String query = "run=" + run + "&case=" + name;
        HttpUrl url = origin.resolve(path + "?" + query);
        for (int hop = 0; hop < 5 && allowed(url, query); hop++) {
            try (Response response = client.newCall(new Request.Builder().url(url).build()).execute()) {
                if (response.isRedirect()) {
                    String location = response.header("Location");
                    url = location == null ? null : url.resolve(location);
                    continue;
                }
                if (response.code() == 200 && "image/gif".equals(response.header("Content-Type"))) {
                    return response.body().bytes();
                }
                return null;
            }
        }
        return null;
    }

    private boolean allowed(HttpUrl url, String query) {
        return url != null && url.isHttps() && url.host().equals(origin.host()) && url.port() == origin.port()
            && url.username().isEmpty() && url.password().isEmpty() && url.fragment() == null
            && ALLOWED.contains(url.encodedPath()) && query.equals(url.encodedQuery());
    }
}
