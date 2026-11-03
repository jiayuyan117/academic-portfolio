import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/** Failure-oriented checks for the event log and simulator. Assertions do not depend on -ea. */
public final class CartEventLogTest {

    private static int passed;

    static void check(boolean ok, String what) {
        if (!ok) throw new AssertionError(what);
    }

    static void test(String name, Runnable body) {
        body.run();
        passed++;
        System.out.println("PASS " + name);
    }

    static CartEventLog.Attempt a(String s, CartEventLog.Type t, String sku, int q, long cents, String key) {
        return new CartEventLog.Attempt(s, 0, t, sku, q, cents, key);
    }

    public static void main(String[] args) {
        test("repeated order submission is rejected and counted once", () -> {
            CartEventLog log = new CartEventLog();
            log.submit(a("S1", CartEventLog.Type.ADD, "A", 2, 500, ""));
            check(log.submit(a("S1", CartEventLog.Type.ORDER, "", 0, 0, "k1")) == null, "first order accepted");
            check(log.submit(a("S1", CartEventLog.Type.ORDER, "", 0, 0, "k1")) == CartEventLog.Reject.DUPLICATE_SUBMIT,
                    "retry rejected as duplicate");
            long orders = log.accepted().stream().filter(x -> x.attempt().type() == CartEventLog.Type.ORDER).count();
            check(orders == 1, "one accepted order");
        });
        test("order total is computed from the cart in integer cents", () -> {
            CartEventLog log = new CartEventLog();
            log.submit(a("S1", CartEventLog.Type.ADD, "A", 3, 1_999, ""));
            log.submit(a("S1", CartEventLog.Type.ADD, "B", 1, 5, ""));
            log.submit(a("S1", CartEventLog.Type.REMOVE, "A", 1, 0, ""));
            log.submit(a("S1", CartEventLog.Type.ORDER, "", 0, 0, "k"));
            CartEventLog.Accepted last = log.accepted().get(log.accepted().size() - 1);
            check(last.orderCents() == 2 * 1_999 + 5, "total " + last.orderCents());
        });
        test("empty-cart checkout and order are rejected", () -> {
            CartEventLog log = new CartEventLog();
            check(log.submit(a("S1", CartEventLog.Type.CHECKOUT, "", 0, 0, "")) == CartEventLog.Reject.EMPTY_CART, "checkout");
            check(log.submit(a("S1", CartEventLog.Type.ORDER, "", 0, 0, "k")) == CartEventLog.Reject.EMPTY_CART, "order");
            check(log.accepted().isEmpty(), "nothing accepted");
        });
        test("removing more than the cart holds is rejected without changing state", () -> {
            CartEventLog log = new CartEventLog();
            log.submit(a("S1", CartEventLog.Type.ADD, "A", 1, 100, ""));
            check(log.submit(a("S1", CartEventLog.Type.REMOVE, "A", 2, 0, "")) == CartEventLog.Reject.NOT_IN_CART, "over-remove");
            check(log.submit(a("S1", CartEventLog.Type.REMOVE, "B", 1, 0, "")) == CartEventLog.Reject.NOT_IN_CART, "absent sku");
            check(log.cartUnits("S1") == 1, "cart unchanged");
        });
        test("events after an accepted order are rejected", () -> {
            CartEventLog log = new CartEventLog();
            log.submit(a("S1", CartEventLog.Type.ADD, "A", 1, 100, ""));
            log.submit(a("S1", CartEventLog.Type.ORDER, "", 0, 0, "k"));
            check(log.submit(a("S1", CartEventLog.Type.VIEW, "A", 0, 100, "")) == CartEventLog.Reject.SESSION_CLOSED, "late view");
        });
        test("invalid quantity and price are rejected", () -> {
            CartEventLog log = new CartEventLog();
            check(log.submit(a("S1", CartEventLog.Type.ADD, "A", 0, 100, "")) == CartEventLog.Reject.INVALID_QUANTITY, "qty 0");
            check(log.submit(a("S1", CartEventLog.Type.ADD, "A", 100, 100, "")) == CartEventLog.Reject.INVALID_QUANTITY, "qty 100");
            check(log.submit(a("S1", CartEventLog.Type.ADD, "A", 1, 0, "")) == CartEventLog.Reject.INVALID_PRICE, "price 0");
        });
        test("sessions are isolated and sequence numbers are strictly increasing", () -> {
            CartEventLog log = new CartEventLog();
            log.submit(a("S1", CartEventLog.Type.ADD, "A", 1, 100, ""));
            check(log.submit(a("S2", CartEventLog.Type.ORDER, "", 0, 0, "k2")) == CartEventLog.Reject.EMPTY_CART, "S2 empty");
            log.submit(a("S2", CartEventLog.Type.ADD, "A", 1, 100, ""));
            log.submit(a("S1", CartEventLog.Type.ORDER, "", 0, 0, "k1"));
            log.submit(a("S2", CartEventLog.Type.ORDER, "", 0, 0, "k2"));
            List<CartEventLog.Accepted> acc = log.accepted();
            for (int i = 1; i < acc.size(); i++) check(acc.get(i).seq() > acc.get(i - 1).seq(), "seq order");
            check(acc.size() == 4, "four accepted");
        });
        test("order without an idempotency key is a programming error", () -> {
            CartEventLog log = new CartEventLog();
            log.submit(a("S1", CartEventLog.Type.ADD, "A", 1, 100, ""));
            boolean threw = false;
            try { log.submit(a("S1", CartEventLog.Type.ORDER, "", 0, 0, "")); } catch (IllegalArgumentException e) { threw = true; }
            check(threw, "missing key must throw");
        });
        test("simulator is deterministic and accepted orders equal true orders", () -> {
            List<CartEventLog.Attempt> x = new ArrayList<>(), y = new ArrayList<>();
            List<Simulate.Truth> tx = new ArrayList<>();
            Random r1 = new Random(7), r2 = new Random(7);
            for (int i = 0; i < 500; i++) {
                tx.add(Simulate.session(r1, "S" + i, i * 1_000_000L, x));
                Simulate.session(r2, "S" + i, i * 1_000_000L, y);
            }
            check(x.equals(y), "same seed, same attempts");
            CartEventLog log = new CartEventLog();
            x.forEach(log::submit);
            long acceptedOrders = log.accepted().stream().filter(e -> e.attempt().type() == CartEventLog.Type.ORDER).count();
            long trueOrders = tx.stream().filter(Simulate.Truth::ordered).count();
            long rawOrders = x.stream().filter(e -> e.type() == CartEventLog.Type.ORDER).count();
            check(acceptedOrders == trueOrders, acceptedOrders + " vs " + trueOrders);
            check(rawOrders > trueOrders, "faults must inflate raw order attempts");
        });
        System.out.println(passed + " test groups passed, 0 failed");
    }
}
