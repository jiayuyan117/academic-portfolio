import java.io.IOException;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.regex.Pattern;

/** Dependency-free failure-oriented tests; checks run without Java -ea. */
public final class CatalogTest {
    private static int passed;
    private static void check(boolean ok, String why) {
        if (!ok) throw new AssertionError(why);
    }
    interface Action { void run() throws Exception; }
    private static void rejects(Class<? extends Throwable> type, Action action) throws Exception {
        try { action.run(); } catch (Throwable e) {
            if (type.isInstance(e)) return;
            throw new AssertionError("Expected " + type + ", got " + e, e);
        }
        throw new AssertionError("Expected " + type);
    }
    private static void test(String name, Action action) throws Exception {
        action.run(); passed++; System.out.println("PASS " + name);
    }
    private static HttpResponse<String> request(HttpClient client, String base, String path,
                                               String method, String body, String origin) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + path));
        if (origin != null) b.header("Origin", origin);
        if (method.equals("POST")) b.header("Content-Type", "application/x-www-form-urlencoded");
        return client.send(b.method(method, HttpRequest.BodyPublishers.ofString(body)).build(),
                HttpResponse.BodyHandlers.ofString());
    }
    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("catalog-test-");
        try {
            test("exact money and invalid numeric formats", () -> {
                check(Catalog.price("0.29") == 29 && Catalog.price("1000000.00") == 100000000, "exact cents");
                for (String bad : List.of("-1", "NaN", "1e2", "0.001", "1000000.01", "", " 1"))
                    rejects(IllegalArgumentException.class, () -> Catalog.price(bad));
            });
            test("CRUD, Unicode search, validation and restart", () -> {
                Path file = dir.resolve("crud.tsv");
                try (Catalog c = new Catalog(file)) {
                    c.save("BOOK-1", "教材 <sample>", "19.90", 8, 0);
                    check(c.list("教材").size() == 1 && c.list("book").size() == 1, "search");
                    c.save("BOOK-1", "Notebook", "20.01", 9, 1);
                    rejects(IllegalArgumentException.class, () -> c.save("BAD", "x\ty", "1", 0, 0));
                    rejects(IllegalArgumentException.class, () -> c.save("BAD", "x", "1", -1, 0));
                    check(c.list("").size() == 1, "invalid inputs changed state");
                }
                try (Catalog c = new Catalog(file)) {
                    check(c.list("").get(0).cents() == 2001, "restart money");
                    c.delete("BOOK-1", 2);
                }
                try (Catalog c = new Catalog(file)) { check(c.list("").isEmpty(), "delete restart"); }
            });
            test("stale edit, duplicate create and delete/recreate ABA", () -> {
                try (Catalog c = new Catalog(dir.resolve("version.tsv"))) {
                    c.save("A", "First", "1", 0, 0);
                    rejects(Catalog.Conflict.class, () -> c.save("A", "Duplicate", "1", 0, 0));
                    c.save("A", "Second", "2", 0, 1);
                    rejects(Catalog.Conflict.class, () -> c.delete("A", 1));
                    c.delete("A", 2);
                    c.save("A", "Recreated", "3", 0, 0);
                    rejects(Catalog.Conflict.class, () -> c.save("A", "Stale", "1", 0, 1));
                    check(c.list("").get(0).name().equals("Recreated"), "stale overwrite");
                }
            });
            test("two competing edits: exactly one commits", () -> {
                try (Catalog c = new Catalog(dir.resolve("race.tsv"))) {
                    c.save("A", "Before", "1", 0, 0);
                    ExecutorService pool = Executors.newFixedThreadPool(2);
                    CountDownLatch gate = new CountDownLatch(1);
                    Callable<Boolean> edit = () -> {
                        gate.await();
                        try { c.save("A", "After", "2", 1, 1); return true; }
                        catch (Catalog.Conflict e) { return false; }
                    };
                    try {
                        Future<Boolean> a = pool.submit(edit), b = pool.submit(edit);
                        gate.countDown();
                        check(a.get() ^ b.get(), "lost update");
                    } finally { pool.shutdownNow(); }
                }
            });
            test("second opener lock exclusion and lock release", () -> {
                Path file = dir.resolve("lock.tsv");
                try (Catalog c = new Catalog(file)) {
                    rejects(java.nio.channels.OverlappingFileLockException.class, () -> new Catalog(file));
                }
                try (Catalog c = new Catalog(file)) { check(c.list("").isEmpty(), "lock release"); }
            });
            test("corrupt snapshots fail closed and retain bytes", () -> {
                Path file = dir.resolve("corrupt.tsv");
                for (String bad : List.of("", "CATALOG-1\t1\nA\tName\t-1\t0\t1\n",
                        "CATALOG-1\t1\nA\tName\t1\t0\t1\nA\tName\t1\t0\t1\n")) {
                    Files.writeString(file, bad);
                    rejects(IOException.class, () -> new Catalog(file));
                    check(Files.readString(file).equals(bad), "corrupt file overwritten");
                }
            });
            test("failed storage commit does not publish memory", () -> {
                Path file = dir.resolve("failure.tsv");
                try (Catalog c = new Catalog(file)) {
                    Files.createDirectory(file);
                    Files.writeString(file.resolve("blocker"), "force move failure");
                    rejects(IOException.class, () -> c.save("A", "Not committed", "1", 0, 0));
                    check(c.list("").isEmpty(), "memory published before disk");
                }
            });
            test("HTTP CRUD, escaping, conflict and method semantics", () -> {
                try (Catalog c = new Catalog(dir.resolve("http.tsv"));
                     CatalogServer server = new CatalogServer(c, 0)) {
                    HttpClient client = HttpClient.newHttpClient();
                    String base = "http://127.0.0.1:" + server.port();
                    var page = request(client, base, "/", "GET", "", null);
                    var matcher = Pattern.compile("name='token' value='([^']+)'").matcher(page.body());
                    check(page.statusCode() == 200 && matcher.find(), "render/token");
                    String fields = "token=" + matcher.group(1) + "&sku=A&name=%3Cscript%3E&price=0.29&stock=2&version=0";
                    check(request(client, base, "/save", "POST", "token=" + matcher.group(1) + "&version=0", base)
                            .statusCode() == 400, "missing SKU");
                    var wrongType = client.send(HttpRequest.newBuilder(URI.create(base + "/save"))
                            .POST(HttpRequest.BodyPublishers.ofString(fields)).build(), HttpResponse.BodyHandlers.ofString());
                    check(wrongType.statusCode() == 415, "content type");
                    check(page.headers().firstValue("Content-Security-Policy").orElse("").contains("frame-ancestors 'none'"),
                            "CSP");
                    check(request(client, base, "/save", "POST", fields, base).statusCode() == 303, "create");
                    check(request(client, base, "/save", "POST", fields, base).statusCode() == 409, "conflict");
                    String html = request(client, base, "/?q=A", "GET", "", null).body();
                    check(html.contains("&lt;script&gt;") && !html.contains("<script>"), "stored XSS");
                    check(request(client, base, "/delete", "GET", "", null).statusCode() == 405, "GET mutation");
                    check(request(client, base, "/unknown", "GET", "", null).statusCode() == 404, "routing");
                    check(request(client, base, "/save", "POST", fields.replace("version=0", "version=1"), base)
                            .statusCode() == 303, "update");
                    check(request(client, base, "/delete", "POST", fields.replace("version=0", "version=2"), base)
                            .statusCode() == 303 && c.list("").isEmpty(), "delete");
                }
            });
            test("HTTP CSRF, cross-origin, malformed and oversized requests", () -> {
                try (Catalog c = new Catalog(dir.resolve("security.tsv"));
                     CatalogServer server = new CatalogServer(c, 0)) {
                    HttpClient client = HttpClient.newHttpClient();
                    String base = "http://127.0.0.1:" + server.port();
                    check(request(client, base, "/save", "POST", "sku=A", null).statusCode() == 403, "token");
                    check(request(client, base, "/save", "POST", "", "https://example.com").statusCode() == 403, "origin");
                    check(request(client, base, "/save", "POST", "x".repeat(8193), null).statusCode() == 413, "size");
                    check(request(client, base, "/?q=A&q=B", "GET", "", null).statusCode() == 400, "duplicate query");
                    check(request(client, base, "/save", "POST", "q=%ZZ", null).statusCode() == 400, "malformed form");
                    check(c.list("").isEmpty(), "rejected requests mutated state");
                }
            });
            test("strict form parsing", () -> {
                rejects(IllegalArgumentException.class, () -> CatalogServer.form("sku=A&sku=B"));
                rejects(IllegalArgumentException.class, () -> CatalogServer.form("q=%ZZ"));
                rejects(IllegalArgumentException.class, () -> CatalogServer.form("q"));
                check(CatalogServer.form("q=%E4%B9%A6").get("q").equals("书"), "UTF-8");
            });
            System.out.println("RESULT: " + passed + " tests passed, 0 failed");
        } finally {
            try (var paths = Files.walk(dir)) {
                for (Path p : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(p);
            }
        }
    }
}
