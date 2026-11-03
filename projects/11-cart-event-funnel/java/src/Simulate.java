import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Random;

/**
 * Deterministic simulation of shopping sessions with known funnel parameters and
 * injected client faults: repeated order submissions, clock skew, invalid
 * removals, empty-cart orders and events after an order. Because the true
 * outcome of every session is known, the analysis can check whether it recovers it.
 */
public final class Simulate {

    static final double P_ADD = 0.35, P_CHECKOUT = 0.50, P_ORDER = 0.70;
    static final double P_DOUBLE_SUBMIT = 0.15, P_SKEW = 0.04, P_BAD_REMOVE = 0.03;
    static final double P_EMPTY_ORDER = 0.02, P_LATE_EVENT = 0.05, P_REMOVE = 0.20;
    static final int CATALOG = 20;

    record Truth(String sessionId, boolean added, boolean checkout, boolean ordered) { }

    static long priceOf(int sku) { return 990L + 1_250L * sku; }

    static String sku(int i) { return String.format(Locale.ROOT, "SKU%02d", i); }

    /** Generates one session's attempts in server receive order and returns its true outcome. */
    static Truth session(Random r, String id, long start, List<CartEventLog.Attempt> out) {
        long[] clock = {start};
        java.util.function.Supplier<Long> ts = () -> {
            clock[0] += 500 + r.nextInt(19_500);
            long t = clock[0];
            return r.nextDouble() < P_SKEW ? t - r.nextInt(30_000) : t;
        };
        int views = 1 + r.nextInt(5);
        for (int i = 0; i < views; i++) {
            int k = r.nextInt(CATALOG);
            out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.VIEW, sku(k), 0, priceOf(k), ""));
        }
        if (r.nextDouble() < P_BAD_REMOVE) {
            out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.REMOVE, sku(r.nextInt(CATALOG)), 1, 0, ""));
        }
        boolean added = r.nextDouble() < P_ADD;
        if (!added) {
            if (r.nextDouble() < P_EMPTY_ORDER) {
                out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.ORDER, "", 0, 0, id + "-order"));
            }
            return new Truth(id, false, false, false);
        }
        int lines = 1 + r.nextInt(3), units = 0, first = -1;
        for (int i = 0; i < lines; i++) {
            int k = r.nextInt(CATALOG), q = 1 + r.nextInt(3);
            if (first < 0) first = k;
            units += q;
            out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.ADD, sku(k), q, priceOf(k), ""));
        }
        if (units > 1 && r.nextDouble() < P_REMOVE) {
            out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.REMOVE, sku(first), 1, 0, ""));
        }
        boolean checkout = r.nextDouble() < P_CHECKOUT;
        if (!checkout) return new Truth(id, true, false, false);
        out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.CHECKOUT, "", 0, 0, ""));
        boolean ordered = r.nextDouble() < P_ORDER;
        if (!ordered) return new Truth(id, true, true, false);
        String key = id + "-order";
        out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.ORDER, "", 0, 0, key));
        if (r.nextDouble() < P_DOUBLE_SUBMIT) {
            out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.ORDER, "", 0, 0, key));
        }
        if (r.nextDouble() < P_LATE_EVENT) {
            int k = r.nextInt(CATALOG);
            out.add(new CartEventLog.Attempt(id, ts.get(), CartEventLog.Type.VIEW, sku(k), 0, priceOf(k), ""));
        }
        return new Truth(id, true, true, true);
    }

    static String row(CartEventLog.Attempt a) {
        return String.join(",", a.sessionId(), Long.toString(a.clientTs()), a.type().name(), a.sku(),
                Integer.toString(a.qty()), Long.toString(a.unitCents()), a.idempotencyKey());
    }

    static final String ATTEMPT_HEADER = "session_id,client_ts,type,sku,qty,unit_cents,idempotency_key";

    static void writeMain(Path dir, long seed, int n) throws IOException {
        Random r = new Random(seed);
        List<CartEventLog.Attempt> attempts = new ArrayList<>();
        List<Truth> truth = new ArrayList<>();
        long start = 1_700_000_000_000L;
        for (int i = 1; i <= n; i++) {
            truth.add(session(r, String.format(Locale.ROOT, "S%05d", i), start, attempts));
            start += 60_000 + r.nextInt(240_000);
        }
        CartEventLog log = new CartEventLog();
        attempts.forEach(log::submit);
        try (PrintWriter w = writer(dir.resolve("raw_attempts.csv"))) {
            w.println("attempt_index," + ATTEMPT_HEADER);
            for (int i = 0; i < attempts.size(); i++) w.println((i + 1) + "," + row(attempts.get(i)));
        }
        try (PrintWriter w = writer(dir.resolve("accepted_events.csv"))) {
            w.println("seq," + ATTEMPT_HEADER + ",order_cents");
            for (CartEventLog.Accepted a : log.accepted()) w.println(a.seq() + "," + row(a.attempt()) + "," + a.orderCents());
        }
        try (PrintWriter w = writer(dir.resolve("rejected_events.csv"))) {
            w.println(ATTEMPT_HEADER + ",reason");
            for (CartEventLog.Rejected x : log.rejected()) w.println(row(x.attempt()) + "," + x.reason());
        }
        try (PrintWriter w = writer(dir.resolve("truth_sessions.csv"))) {
            w.println("session_id,added,checkout,ordered");
            for (Truth t : truth) w.println(t.sessionId() + "," + bit(t.added()) + "," + bit(t.checkout()) + "," + bit(t.ordered()));
        }
    }

    /** Many independent replicates, reduced to accepted-log session flags, for interval coverage checks. */
    static void writeReplicates(Path dir, long seed, int reps, int n) throws IOException {
        try (PrintWriter w = writer(dir.resolve("replicate_sessions.csv"))) {
            w.println("replicate,added,checkout,ordered,raw_order_attempts");
            for (int rep = 1; rep <= reps; rep++) {
                Random r = new Random(seed * 1_000_003L + rep);
                List<CartEventLog.Attempt> attempts = new ArrayList<>();
                List<String> ids = new ArrayList<>();
                long start = 1_700_000_000_000L;
                for (int i = 1; i <= n; i++) {
                    String id = String.format(Locale.ROOT, "R%03d-S%05d", rep, i);
                    ids.add(id);
                    session(r, id, start, attempts);
                    start += 60_000 + r.nextInt(240_000);
                }
                CartEventLog log = new CartEventLog();
                attempts.forEach(log::submit);
                java.util.Map<String, int[]> flags = new java.util.HashMap<>();
                for (String id : ids) flags.put(id, new int[4]);
                for (CartEventLog.Attempt a : attempts) {
                    if (a.type() == CartEventLog.Type.ORDER) flags.get(a.sessionId())[3]++;
                }
                for (CartEventLog.Accepted a : log.accepted()) {
                    int[] f = flags.get(a.attempt().sessionId());
                    switch (a.attempt().type()) {
                        case ADD -> f[0] = 1;
                        case CHECKOUT -> f[1] = 1;
                        case ORDER -> f[2] = 1;
                        default -> { }
                    }
                }
                for (String id : ids) {
                    int[] f = flags.get(id);
                    w.println(rep + "," + f[0] + "," + f[1] + "," + f[2] + "," + f[3]);
                }
            }
        }
    }

    static void writeParams(Path dir, long seed, int n, int reps, int repSessions) throws IOException {
        try (PrintWriter w = writer(dir.resolve("params.json"))) {
            w.printf(Locale.ROOT, "{%n  \"seed\": %d,%n  \"sessions\": %d,%n  \"replicates\": %d,%n"
                    + "  \"replicate_sessions\": %d,%n  \"p_add\": %.2f,%n  \"p_checkout_given_add\": %.2f,%n"
                    + "  \"p_order_given_checkout\": %.2f,%n  \"p_double_submit\": %.2f,%n  \"p_clock_skew\": %.2f,%n"
                    + "  \"p_bad_remove\": %.2f,%n  \"p_empty_cart_order\": %.2f,%n  \"p_event_after_order\": %.2f%n}%n",
                    seed, n, reps, repSessions, P_ADD, P_CHECKOUT, P_ORDER, P_DOUBLE_SUBMIT, P_SKEW,
                    P_BAD_REMOVE, P_EMPTY_ORDER, P_LATE_EVENT);
        }
    }

    static String bit(boolean b) { return b ? "1" : "0"; }

    static PrintWriter writer(Path p) throws IOException {
        return new PrintWriter(Files.newBufferedWriter(p, StandardCharsets.UTF_8));
    }

    public static void main(String[] args) throws IOException {
        Path dir = Path.of(args.length > 0 ? args[0] : "data");
        long seed = 20261102L;
        int sessions = 3000, reps = 200, repSessions = 1000;
        Files.createDirectories(dir);
        writeMain(dir, seed, sessions);
        writeReplicates(dir, seed, reps, repSessions);
        writeParams(dir, seed, sessions, reps, repSessions);
        System.out.println("Simulated " + sessions + " sessions and " + reps + " replicates into " + dir);
    }
}
