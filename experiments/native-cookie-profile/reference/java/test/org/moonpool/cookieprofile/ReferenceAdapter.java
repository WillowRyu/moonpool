package org.moonpool.cookieprofile;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import org.json.JSONArray;

/** Desktop entry point for the same C04 replay bundled in the Android experiment. */
final class ReferenceAdapter {
    public static void main(String[] args) throws Exception {
        PublicSuffixList publicSuffixes = PublicSuffixList.parse(pinned(Path.of(args[0]), args[1]));
        JSONArray cases = new JSONArray(new String(System.in.readAllBytes(), StandardCharsets.UTF_8));
        System.out.println(CorpusReplay.run(publicSuffixes, cases));
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
}
