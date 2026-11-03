import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Server-side cart event log. Every client attempt is either accepted, with a
 * server sequence number, or rejected with an explicit reason. Accepted events
 * are the only input to session-level funnel analysis.
 */
public final class CartEventLog {

    public enum Type { VIEW, ADD, REMOVE, CHECKOUT, ORDER }

    public enum Reject { DUPLICATE_SUBMIT, EMPTY_CART, NOT_IN_CART, SESSION_CLOSED, INVALID_QUANTITY, INVALID_PRICE }

    /** A client attempt. clientTs may be skewed; it is recorded but never trusted for ordering. */
    public record Attempt(String sessionId, long clientTs, Type type, String sku,
                          int qty, long unitCents, String idempotencyKey) { }

    public record Accepted(long seq, Attempt attempt, long orderCents) { }

    public record Rejected(Attempt attempt, Reject reason) { }

    private static final class Session {
        final Map<String, Integer> cart = new LinkedHashMap<>();
        final Map<String, Long> price = new HashMap<>();
        boolean closed;
    }

    private final Map<String, Session> sessions = new HashMap<>();
    private final Set<String> acceptedOrderKeys = new HashSet<>();
    private final List<Accepted> accepted = new ArrayList<>();
    private final List<Rejected> rejected = new ArrayList<>();
    private long nextSeq = 1;

    /** Applies one attempt and returns the rejection reason, or null when accepted. */
    public Reject submit(Attempt a) {
        Session s = sessions.computeIfAbsent(a.sessionId(), k -> new Session());
        Reject reason = validate(s, a);
        if (reason != null) {
            rejected.add(new Rejected(a, reason));
            return reason;
        }
        long orderCents = 0;
        switch (a.type()) {
            case ADD -> {
                s.cart.merge(a.sku(), a.qty(), Integer::sum);
                s.price.put(a.sku(), a.unitCents());
            }
            case REMOVE -> {
                int left = s.cart.get(a.sku()) - a.qty();
                if (left > 0) s.cart.put(a.sku(), left); else s.cart.remove(a.sku());
            }
            case ORDER -> {
                for (Map.Entry<String, Integer> e : s.cart.entrySet()) {
                    orderCents = Math.addExact(orderCents, Math.multiplyExact(s.price.get(e.getKey()), e.getValue()));
                }
                acceptedOrderKeys.add(a.idempotencyKey());
                s.closed = true;
            }
            default -> { }
        }
        accepted.add(new Accepted(nextSeq++, a, orderCents));
        return null;
    }

    private Reject validate(Session s, Attempt a) {
        if (a.type() == Type.ORDER && acceptedOrderKeys.contains(a.idempotencyKey())) return Reject.DUPLICATE_SUBMIT;
        if (s.closed) return Reject.SESSION_CLOSED;
        switch (a.type()) {
            case ADD -> {
                if (a.qty() < 1 || a.qty() > 99) return Reject.INVALID_QUANTITY;
                if (a.unitCents() <= 0) return Reject.INVALID_PRICE;
            }
            case REMOVE -> {
                if (a.qty() < 1) return Reject.INVALID_QUANTITY;
                Integer held = s.cart.get(a.sku());
                if (held == null || held < a.qty()) return Reject.NOT_IN_CART;
            }
            case CHECKOUT, ORDER -> {
                if (s.cart.isEmpty()) return Reject.EMPTY_CART;
                if (a.type() == Type.ORDER && (a.idempotencyKey() == null || a.idempotencyKey().isEmpty())) {
                    throw new IllegalArgumentException("ORDER requires an idempotency key");
                }
            }
            default -> { }
        }
        return null;
    }

    public List<Accepted> accepted() { return List.copyOf(accepted); }

    public List<Rejected> rejected() { return List.copyOf(rejected); }

    /** Number of items currently held in a session's cart, for tests. */
    public int cartUnits(String sessionId) {
        Session s = sessions.get(sessionId);
        return s == null ? 0 : s.cart.values().stream().mapToInt(Integer::intValue).sum();
    }
}
