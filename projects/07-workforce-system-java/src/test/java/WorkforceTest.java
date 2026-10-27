import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeMap;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.*;

final class WorkforceTest {
    private static Workforce organization() {
        Workforce app = new Workforce();
        app.addDepartment(1, 0);
        app.addDepartment(2, 0);
        app.addDepartment(3, 1);
        return app;
    }

    private static Workforce.Employee employee(int id, int department) {
        return new Workforce.Employee(id, "Synthetic " + id, department, id * 100L);
    }

    @Test
    void emptyOrganizationHasRootAndRejectsMissingEmployees() {
        Workforce app = new Workforce();
        assertNull(app.find(1));
        assertNull(app.find(0));
        assertNull(app.find(-1));
        assertEquals(0, app.count(0));
        assertEquals(List.of(), app.sortedEmployees());
        assertEquals(List.of(), app.salaryRange(0, Long.MAX_VALUE));
        assertThrows(IllegalArgumentException.class, () -> app.remove(1));
        assertThrows(IllegalArgumentException.class, () -> app.transfer(1, 0));
        app.verify();
    }

    static Stream<Arguments> invalidEmployees() {
        return Stream.of(
                Arguments.of(0, "Synthetic", 0L),
                Arguments.of(-1, "Synthetic", 0L),
                Arguments.of(1, null, 0L),
                Arguments.of(1, "", 0L),
                Arguments.of(1, " \t\n", 0L),
                Arguments.of(1, "Synthetic", -1L));
    }

    @ParameterizedTest
    @MethodSource("invalidEmployees")
    void invalidEmployeeRecordsAreRejected(int id, String name, long salary) {
        assertThrows(IllegalArgumentException.class,
                () -> new Workforce.Employee(id, name, 0, salary));
    }

    @Test
    void invalidOperationsLeaveBothIndexesUnchanged() {
        Workforce app = organization();
        Workforce.Employee original = employee(40, 3);
        app.add(original);
        List<Workforce.Employee> before = app.sortedEmployees();
        List<Runnable> invalid = List.of(
                () -> app.addDepartment(0, 0),
                () -> app.addDepartment(-1, 0),
                () -> app.addDepartment(1, 0),
                () -> app.addDepartment(4, 99),
                () -> app.add(employee(41, 99)),
                () -> app.add(employee(40, 2)),
                () -> app.transfer(40, 99),
                () -> app.transfer(99, 1),
                () -> app.remove(99),
                () -> app.count(99),
                () -> app.salaryRange(-1, 100),
                () -> app.salaryRange(100, 99));
        for (Runnable action : invalid) {
            assertThrows(IllegalArgumentException.class, action::run);
            assertEquals(before, app.sortedEmployees());
            assertSame(original, app.find(40));
            assertEquals(1, app.count(0));
            assertEquals(1, app.count(1));
            assertEquals(0, app.count(2));
            assertEquals(1, app.count(3));
            app.verify();
        }
        // A rejected department addition must not reserve its ID.
        app.addDepartment(4, 3);
        assertEquals(0, app.count(4));
        app.verify();
    }

    static Stream<Arguments> insertionRotations() {
        return Stream.of(
                Arguments.of("LL", new int[]{30, 20, 10}),
                Arguments.of("RR", new int[]{10, 20, 30}),
                Arguments.of("LR", new int[]{30, 10, 20}),
                Arguments.of("RL", new int[]{10, 30, 20}));
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("insertionRotations")
    void insertionRestoresBalance(String rotation, int[] ids) {
        Workforce app = organization();
        for (int id : ids) {
            app.add(employee(id, 1));
            app.verify();
        }
        assertEquals(20, rootEmployee(app).id());
        assertEquals(List.of(employee(10, 1), employee(20, 1), employee(30, 1)),
                app.sortedEmployees());
    }

    static Stream<Arguments> deletionRotations() {
        return Stream.of(
                Arguments.of("LL", new int[]{30, 20, 40, 10}, 40, 20),
                Arguments.of("RR", new int[]{20, 10, 30, 40}, 10, 30),
                Arguments.of("LR", new int[]{30, 10, 40, 20}, 40, 20),
                Arguments.of("RL", new int[]{20, 10, 40, 30}, 10, 30),
                Arguments.of("balanced left child", new int[]{40, 20, 50, 10, 30}, 50, 20),
                Arguments.of("balanced right child", new int[]{20, 10, 40, 30, 50}, 10, 40));
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("deletionRotations")
    void deletionRestoresBalanceIncludingZeroBalanceChildren(
            String rotation, int[] ids, int removed, int expectedRoot) {
        Workforce app = organization();
        TreeMap<Integer, Workforce.Employee> reference = new TreeMap<>();
        for (int id : ids) {
            Workforce.Employee employee = employee(id, id % 3 + 1);
            app.add(employee);
            reference.put(id, employee);
        }
        app.remove(removed);
        reference.remove(removed);
        assertNull(app.find(removed));
        assertEquals(expectedRoot, rootEmployee(app).id());
        assertMatches(app, reference);
    }

    @Test
    void deletingTwoChildRootPreservesSuccessorDepartmentAndRecord() {
        Workforce app = organization();
        TreeMap<Integer, Workforce.Employee> reference = new TreeMap<>();
        for (int id : new int[]{40, 20, 60, 10, 30, 50, 70, 55}) {
            Workforce.Employee employee = employee(id, id == 40 ? 2 : 3);
            app.add(employee);
            reference.put(id, employee);
        }
        assertEquals(40, rootEmployee(app).id());
        Workforce.Employee successor = app.find(50);
        app.remove(40);
        reference.remove(40);
        assertSame(successor, app.find(50));
        assertNotNull(app.find(55)); // Successor's right child must survive.
        assertEquals(0, app.count(2));
        assertMatches(app, reference);

        // Repeated root deletion exercises replacements down to the empty tree.
        while (!reference.isEmpty()) {
            int id = rootEmployee(app).id();
            app.remove(id);
            reference.remove(id);
            assertNull(app.find(id));
            assertMatches(app, reference);
        }
        app.add(employee(40, 1)); // Removed IDs can be reused.
        assertEquals(1, app.count(1));
        app.verify();
    }

    @Test
    void deletingRootWithOneChildThenLeafKeepsTreeUsable() {
        Workforce app = organization();
        app.add(employee(20, 1));
        app.add(employee(10, 2));
        app.remove(20);
        assertEquals(10, rootEmployee(app).id());
        assertEquals(0, app.count(1));
        app.verify();
        app.remove(10);
        assertNull(read(app, "root"));
        assertEquals(0, app.count(0));
        app.verify();
    }

    @Test
    void transferPreservesImmutableSnapshotsAndCountsWholeSubtrees() {
        Workforce app = organization();
        Workforce.Employee original = new Workforce.Employee(1, "Synthetic", 3, Long.MAX_VALUE);
        app.add(original);
        app.add(employee(2, 1));
        app.add(employee(3, 0));
        List<Workforce.Employee> snapshot = app.sortedEmployees();
        List<Workforce.Employee> salarySnapshot = app.salaryRange(0, Long.MAX_VALUE);
        Object rootBefore = read(app, "root");
        app.transfer(1, 2);
        assertEquals(3, original.department());
        assertEquals(original, snapshot.get(0));
        assertEquals(snapshot, salarySnapshot);
        assertEquals(new Workforce.Employee(1, "Synthetic", 2, Long.MAX_VALUE), app.find(1));
        assertNotSame(original, app.find(1));
        assertSame(rootBefore, read(app, "root"));
        assertEquals(3, app.count(0));
        assertEquals(1, app.count(1));
        assertEquals(0, app.count(3));
        assertEquals(1, app.count(2));
        app.verify();

        Workforce.Employee transferred = app.find(1);
        app.transfer(1, 2); // Same department is an idempotent no-op.
        assertSame(transferred, app.find(1));
        assertEquals(1, app.count(2));
        app.transfer(1, 0);
        assertEquals(3, app.count(0));
        assertEquals(0, app.count(2));
        app.transfer(1, 3);
        assertEquals(2, app.count(1));
        assertEquals(1, app.count(3));
        assertEquals(Long.MAX_VALUE, app.find(1).salaryCents());
        assertThrows(UnsupportedOperationException.class, snapshot::clear);
        assertThrows(UnsupportedOperationException.class, salarySnapshot::clear);
        app.verify();
    }

    @Test
    void salaryRangeUsesInclusiveCentsAndReturnsIdOrder() {
        Workforce app = new Workforce();
        app.add(new Workforce.Employee(1, "Zero", 0, 0));
        app.add(new Workforce.Employee(2, "Upper", 0, 200));
        app.add(new Workforce.Employee(3, "Lower", 0, 100));
        app.add(new Workforce.Employee(Integer.MAX_VALUE, "Maximum", 0, Long.MAX_VALUE));
        assertEquals(List.of(app.find(2), app.find(3)), app.salaryRange(100, 200));
        assertEquals(List.of(app.find(3)), app.salaryRange(100, 100));
        assertEquals(List.of(app.find(1)), app.salaryRange(0, 0));
        assertEquals(List.of(app.find(Integer.MAX_VALUE)),
                app.salaryRange(Long.MAX_VALUE, Long.MAX_VALUE));
        assertEquals(List.of(), app.salaryRange(201, 202));
        assertEquals(app.sortedEmployees(), app.salaryRange(0, Long.MAX_VALUE));
        app.verify();
        app.remove(Integer.MAX_VALUE);
        app.verify();
    }

    @Test
    void idRangePrunesBranchesAndSubtreeSalaryCentsPreventsOverflow() {
        Workforce app = organization();
        app.add(new Workforce.Employee(10, "A", 1, Long.MAX_VALUE));
        app.add(new Workforce.Employee(20, "B", 3, Long.MAX_VALUE));
        app.add(new Workforce.Employee(30, "C", 2, 500L));
        app.add(new Workforce.Employee(40, "D", 0, 250L));
        assertEquals(List.of(app.find(20), app.find(30)), app.idRange(15, 30));
        assertEquals(List.of(app.find(10)), app.idRange(10, 10));
        assertEquals(List.of(), app.idRange(11, 19));
        assertThrows(IllegalArgumentException.class, () -> app.idRange(0, 10));
        assertThrows(IllegalArgumentException.class, () -> app.idRange(20, 10));
        assertEquals(java.math.BigInteger.valueOf(Long.MAX_VALUE).multiply(java.math.BigInteger.TWO),
                app.subtreeSalaryCents(1));
        assertEquals(java.math.BigInteger.valueOf(Long.MAX_VALUE), app.subtreeSalaryCents(3));
        assertEquals(java.math.BigInteger.valueOf(500L), app.subtreeSalaryCents(2));
        assertEquals(4, app.departmentCount());
        assertTrue(app.treeHeight() >= 2 && app.treeHeight() <= 3);
        app.verify();
    }

    @ParameterizedTest(name = "descending={0}, 50000 employees")
    @ValueSource(booleans = {false, true})
    void largeOrderedInputsTransfersAndAlternatingDeletesStayBalanced(boolean descending) {
        int size = 50_000;
        Workforce app = organization();
        TreeMap<Integer, Workforce.Employee> reference = new TreeMap<>();
        for (int step = 1; step <= size; step++) {
            int id = descending ? size + 1 - step : step;
            Workforce.Employee employee = employee(id, 3);
            app.add(employee);
            reference.put(id, employee);
            if (step % 4096 == 0) {
                assertMatches(app, reference);
            }
        }
        assertMatches(app, reference);
        for (int id = 1; id <= size; id++) {
            assertEquals(reference.get(id), app.find(id));
            if (id % 3 == 0) {
                app.transfer(id, 2);
                reference.put(id, employee(id, 2));
            }
        }
        assertMatches(app, reference);
        for (int step = 0; step < size; step++) {
            int id = step % 2 == 0 ? reference.firstKey() : reference.lastKey();
            app.remove(id);
            reference.remove(id);
            assertNull(app.find(id));
            if (step % 4096 == 0) {
                assertMatches(app, reference);
            }
        }
        assertMatches(app, reference);
    }

    @Test
    void deepDepartmentHierarchyDoesNotUseTheCallStack() {
        Workforce app = new Workforce();
        int depth = 20_000;
        for (int id = 1; id <= depth; id++) {
            app.addDepartment(id, id - 1);
        }
        app.add(employee(1, depth));
        app.add(employee(2, 0));
        assertEquals(2, app.count(0));
        assertEquals(1, app.count(1));
        assertEquals(1, app.count(depth));
        app.verify();
        app.transfer(1, 0);
        assertEquals(0, app.count(1));
        assertEquals(2, app.count(0));
        app.verify();
    }

    @Test
    void seededMixedOperationsMatchTreeMapAfterEveryStep() {
        Workforce app = organization();
        TreeMap<Integer, Workforce.Employee> reference = new TreeMap<>();
        Random random = new Random(42);
        for (int step = 0; step < 5_000; step++) {
            int id = random.nextInt(512) + 1;
            int department = random.nextInt(4);
            Workforce.Employee old = reference.get(id);
            switch (random.nextInt(4)) {
                case 0 -> {
                    Workforce.Employee employee = employee(id, department);
                    if (old == null) {
                        app.add(employee);
                        reference.put(id, employee);
                    } else {
                        assertThrows(IllegalArgumentException.class, () -> app.add(employee));
                    }
                }
                case 1 -> {
                    if (old == null) {
                        assertThrows(IllegalArgumentException.class, () -> app.remove(id));
                    } else {
                        app.remove(id);
                        reference.remove(id);
                    }
                }
                case 2 -> {
                    if (old == null) {
                        assertThrows(IllegalArgumentException.class, () -> app.transfer(id, department));
                    } else {
                        app.transfer(id, department);
                        reference.put(id, new Workforce.Employee(
                                id, old.name(), department, old.salaryCents()));
                    }
                }
                default -> assertEquals(old, app.find(id));
            }
            assertMatches(app, reference);
            long minimum = random.nextInt(512) * 100L;
            long maximum = minimum + random.nextInt(128) * 100L;
            assertEquals(reference.values().stream()
                    .filter(e -> e.salaryCents() >= minimum && e.salaryCents() <= maximum).toList(),
                    app.salaryRange(minimum, maximum), "Salary oracle at step " + step);
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {"height", "balance", "order", "missing", "duplicate", "stale", "department"})
    void verifierDetectsCorruptedInvariants(String corruption) {
        Workforce app = organization();
        for (int id : new int[]{20, 10, 30, 5}) {
            app.add(employee(id, 1));
        }
        Object root = read(app, "root");
        switch (corruption) {
            case "height" -> write(root, "height", 99);
            case "balance" -> {
                // Leave valid ordering, membership and cached heights, but create balance 2.
                app.remove(30);
                root = read(app, "root"); // The legitimate deletion rotated the tree to 10.
                Object right = read(root, "right");
                write(right, "left", root);
                write(root, "right", null);
                write(root, "height", 2);
                write(right, "height", 3);
                write(app, "root", right);
            }
            case "order" -> {
                Object left = read(root, "left");
                Object right = read(root, "right");
                write(root, "left", right);
                write(root, "right", left);
            }
            case "missing" -> members(app, 1).remove(10);
            case "duplicate" -> members(app, 2).add(10);
            case "stale" -> members(app, 1).add(99);
            case "department" -> {
                members(app, 1).remove(10);
                members(app, 2).add(10);
            }
            default -> fail("Unknown corruption");
        }
        assertThrows(IllegalStateException.class, app::verify);
    }

    private static void assertMatches(Workforce app, TreeMap<Integer, Workforce.Employee> reference) {
        app.verify();
        assertEquals(new ArrayList<>(reference.values()), app.sortedEmployees());
        assertEquals(reference.size(), app.count(0));
        assertEquals(reference.values().stream()
                .filter(e -> e.department() == 1 || e.department() == 3).count(), app.count(1));
        assertEquals(reference.values().stream().filter(e -> e.department() == 2).count(), app.count(2));
        assertEquals(reference.values().stream().filter(e -> e.department() == 3).count(), app.count(3));
        Object root = read(app, "root");
        if (reference.isEmpty()) {
            assertNull(root);
        } else {
            int height = (int) read(root, "height");
            // A loose mathematical AVL bound, not a timing-dependent performance assertion.
            double bound = 1.45 * Math.log(reference.size() + 2.0) / Math.log(2);
            assertTrue(height <= bound, "AVL height " + height + " exceeds " + bound);
        }
    }

    private static Workforce.Employee rootEmployee(Workforce app) {
        return (Workforce.Employee) read(read(app, "root"), "employee");
    }

    @SuppressWarnings("unchecked")
    private static Set<Integer> members(Workforce app, int department) {
        Map<Integer, ?> departments = (Map<Integer, ?>) read(app, "departments");
        return (Set<Integer>) read(departments.get(department), "employees");
    }

    // Reflection is confined to structural checks and deliberate invariant corruption.
    // Production exposes no mutable nodes or testing-only public API.
    private static Object read(Object target, String name) {
        try {
            Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            return field.get(target);
        } catch (ReflectiveOperationException exception) {
            throw new AssertionError(exception);
        }
    }

    private static void write(Object target, String name, Object value) {
        try {
            Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            field.set(target, value);
        } catch (ReflectiveOperationException exception) {
            throw new AssertionError(exception);
        }
    }
}
