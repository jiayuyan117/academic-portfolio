import java.util.Random;
import java.util.TreeMap;

/** Behavioral tests; assertions are explicit and do not require -ea. */
public final class WorkforceTest {
    private static int checks;

    private static void check(boolean condition) {
        checks++;
        if (!condition) throw new AssertionError("Check " + checks);
    }

    private static void rejects(Runnable action) {
        try {
            action.run();
        } catch (IllegalArgumentException expected) {
            checks++;
            return;
        }
        throw new AssertionError("Expected rejection");
    }

    public static void main(String[] args) {
        Workforce app = new Workforce();
        app.addDepartment(1, 0);
        app.addDepartment(2, 0);
        app.addDepartment(3, 1);
        rejects(() -> app.addDepartment(1, 0));
        rejects(() -> app.addDepartment(4, 99));
        rejects(() -> app.add(new Workforce.Employee(1, "", 1, 1)));
        rejects(() -> app.add(new Workforce.Employee(1, "Demo", 99, 1)));
        rejects(() -> app.salaryRange(10, 1));

        for (int id : new int[]{40, 20, 60, 50, 70}) {
            app.add(new Workforce.Employee(id, "Synthetic " + id, 3, 100));
        }
        rejects(() -> app.add(new Workforce.Employee(40, "Duplicate", 1, 1)));
        rejects(() -> app.transfer(40, 99));
        check(app.find(40).department() == 3);
        app.transfer(40, 2);
        app.transfer(40, 2);
        check(app.count(1) == 4 && app.count(2) == 1);
        app.remove(40);
        app.verify();
        check(app.find(40) == null && app.find(50).department() == 3);
        app.remove(20);
        app.remove(60);
        app.remove(50);
        app.remove(70);
        check(app.count(0) == 0);
        rejects(() -> app.remove(70));
        rejects(() -> app.transfer(70, 1));

        TreeMap<Integer, Workforce.Employee> reference = new TreeMap<>();
        Random random = new Random(42);
        for (int step = 0; step < 1000; step++) {
            int id = random.nextInt(100) + 1;
            int department = random.nextInt(3) + 1;
            if (!reference.containsKey(id)) {
                Workforce.Employee employee = new Workforce.Employee(id, "Synthetic", department, id * 100L);
                app.add(employee);
                reference.put(id, employee);
            } else if (random.nextBoolean()) {
                app.remove(id);
                reference.remove(id);
            } else {
                app.transfer(id, department);
                Workforce.Employee old = reference.get(id);
                reference.put(id, new Workforce.Employee(id, old.name(), department, old.salaryCents()));
            }
            app.verify();
            check(app.sortedEmployees().equals(reference.values().stream().toList()));
            check(app.salaryRange(2000, 5000).equals(reference.values().stream()
                    .filter(e -> e.salaryCents() >= 2000 && e.salaryCents() <= 5000).toList()));
        }
        System.out.println("PASS: " + checks + " checks; 1000 seeded operations; invariant checks after every operation.");
    }
}
