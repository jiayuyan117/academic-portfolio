import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.*;

/** Loopback-only teaching server; deliberately not an authenticated deployment. */
public final class CatalogServer implements AutoCloseable {
    private final Catalog catalog;
    private final HttpServer server;
    private final ExecutorService workers = Executors.newFixedThreadPool(4);
    private final String token = UUID.randomUUID().toString();

    public CatalogServer(Catalog catalog, int port) throws IOException {
        this.catalog = catalog;
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 16);
        server.createContext("/", this::handle);
        server.setExecutor(workers);
        server.start();
    }
    public int port() { return server.getAddress().getPort(); }
    static String escape(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\"", "&quot;").replace("'", "&#39;");
    }
    static Map<String, String> form(String body) {
        Map<String, String> fields = new HashMap<>();
        if (body.isEmpty()) return fields;
        for (String part : body.split("&", -1)) {
            String[] pair = part.split("=", 2);
            if (pair.length != 2) throw new IllegalArgumentException("Malformed form");
            String key = URLDecoder.decode(pair[0], StandardCharsets.UTF_8);
            String value = URLDecoder.decode(pair[1], StandardCharsets.UTF_8);
            if (fields.put(key, value) != null) throw new IllegalArgumentException("Duplicate field");
        }
        return fields;
    }
    private void handle(HttpExchange x) throws IOException {
        try {
            String host = "127.0.0.1:" + port();
            if (!host.equals(x.getRequestHeaders().getFirst("Host"))) {
                respond(x, 403, "Use http://" + host); return;
            }
            String path = x.getRequestURI().getPath();
            if (!Set.of("/", "/save", "/delete").contains(path)) { respond(x, 404, "Not found"); return; }
            if (path.equals("/") && x.getRequestMethod().equals("GET")) {
                String query = x.getRequestURI().getRawQuery();
                if (query != null && query.length() > 2048) { respond(x, 414, "Query too long"); return; }
                respond(x, 200, page(form(query == null ? "" : query).getOrDefault("q", "")));
                return;
            }
            if (path.equals("/") || !x.getRequestMethod().equals("POST")) {
                x.getResponseHeaders().set("Allow", path.equals("/") ? "GET" : "POST");
                respond(x, 405, "Method not allowed"); return;
            }
            String origin = x.getRequestHeaders().getFirst("Origin");
            if (origin != null && !origin.equals("http://" + host)) { respond(x, 403, "Origin rejected"); return; }
            String type = x.getRequestHeaders().getFirst("Content-Type");
            if (type == null || !type.split(";")[0].trim().equalsIgnoreCase("application/x-www-form-urlencoded")) {
                respond(x, 415, "Use form encoding"); return;
            }
            byte[] body = x.getRequestBody().readNBytes(8193);
            if (body.length > 8192) { respond(x, 413, "Form too large"); return; }
            Map<String, String> f = form(new String(body, StandardCharsets.UTF_8));
            if (!token.equals(f.get("token"))) { respond(x, 403, "Form token rejected"); return; }
            long version = Long.parseLong(f.getOrDefault("version", ""));
            if (path.equals("/save")) catalog.save(f.get("sku"), f.get("name"), f.get("price"),
                    Integer.parseInt(f.getOrDefault("stock", "")), version);
            else catalog.delete(f.get("sku"), version);
            x.getResponseHeaders().set("Location", "/");
            respond(x, 303, "Saved. Reload the catalog.");
        } catch (Catalog.Conflict e) {
            respond(x, 409, escape(e.getMessage()) + " <a href='/'>Reload</a>");
        } catch (IllegalArgumentException e) {
            respond(x, 400, "Invalid input. Check SKU, name, price, stock and version. <a href='/'>Reload</a>");
        } catch (IOException e) {
            respond(x, 503, "Storage unavailable; change not acknowledged. <a href='/'>Reload</a>");
        } finally { x.close(); }
    }
    private String hidden(String name, String value) {
        return "<input type='hidden' name='" + name + "' value='" + escape(value) + "'>";
    }
    private String fields(Catalog.Product p) {
        return hidden("token", token) + hidden("version", p == null ? "0" : "" + p.version())
                + "<label>SKU <input name='sku' required maxlength='24' pattern='[A-Z0-9-]{1,24}' "
                + (p == null ? "" : "readonly ") + "value='" + (p == null ? "" : escape(p.sku())) + "'></label>"
                + "<label>Name <input name='name' required maxlength='100' value='"
                + (p == null ? "" : escape(p.name())) + "'></label>"
                + "<label>Price (CNY) <input name='price' required inputmode='decimal' value='"
                + (p == null ? "0.00" : java.math.BigDecimal.valueOf(p.cents(), 2).toPlainString()) + "'></label>"
                + "<label>Stock <input name='stock' type='number' min='0' max='1000000' required value='"
                + (p == null ? "0" : p.stock()) + "'></label><button>Save</button>";
    }
    private String page(String query) {
        StringBuilder html = new StringBuilder("""
                <!doctype html><html lang="en"><meta charset="utf-8">
                <meta name="viewport" content="width=device-width,initial-scale=1">
                <title>Local product catalog</title><style>
                body{font:16px/1.6 system-ui;max-width:960px;margin:40px auto;padding:0 20px;background:#f6f5f0;color:#14252c}
                section{background:white;padding:20px;margin:16px 0;border:1px solid #d2ddd9;border-radius:8px}
                label{display:inline-block;margin:8px}input,button{font:inherit;padding:7px;max-width:100%;box-sizing:border-box}
                button{background:#146964;color:white;border:0;cursor:pointer}a{color:#146964}
                </style><h1>Product catalog</h1>
                <p>Local engineering exercise · CNY prices · No real customer data. Changes persist on this machine.</p>
                <form method="get"><label>Search SKU or name <input name="q" value="
                """);
        html.append(escape(query)).append("\"></label><button>Search</button></form>")
                .append("<section><h2>Create product</h2><form method='post' action='/save'>")
                .append(fields(null)).append("</form></section><h2>Catalog results</h2>");
        List<Catalog.Product> results = catalog.list(query);
        if (results.isEmpty()) html.append("<p>No matching products.</p>");
        for (Catalog.Product p : results) {
            html.append("<section><h3>").append(escape(p.sku())).append(" · version ").append(p.version())
                    .append("</h3><form method='post' action='/save'>").append(fields(p))
                    .append("</form><form method='post' action='/delete'>").append(hidden("token", token))
                    .append(hidden("sku", p.sku())).append(hidden("version", "" + p.version()))
                    .append("<button>Delete ").append(escape(p.sku())).append("</button></form></section>");
        }
        return html.append("</html>").toString();
    }
    private void respond(HttpExchange x, int status, String html) throws IOException {
        x.getResponseHeaders().set("Content-Type", "text/html; charset=utf-8");
        x.getResponseHeaders().set("Cache-Control", "no-store");
        x.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        x.getResponseHeaders().set("Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'");
        byte[] bytes = html.getBytes(StandardCharsets.UTF_8);
        x.sendResponseHeaders(status, bytes.length);
        x.getResponseBody().write(bytes);
    }
    @Override public void close() { server.stop(0); workers.shutdownNow(); }
    public static void main(String[] args) throws Exception {
        Catalog catalog = new Catalog(Path.of(args.length > 0 ? args[0] : "data/catalog.tsv"));
        CatalogServer app = new CatalogServer(catalog, args.length > 1 ? Integer.parseInt(args[1]) : 8080);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            app.close();
            try { catalog.close(); } catch (IOException ignored) { }
        }));
        System.out.println("Local catalog: http://127.0.0.1:" + app.port());
    }
}
