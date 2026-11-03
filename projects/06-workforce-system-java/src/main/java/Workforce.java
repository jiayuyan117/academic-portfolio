import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * In-memory workforce index used to demonstrate data-structure invariants.
 * A department tree tracks membership in an AVL index of immutable employees.
 * This class is single-threaded; callers must serialize access.
 */
public final class Workforce {
    public record Employee(int id, String name, int department, long salaryCents) {
        public Employee {
            if (id <= 0 || name == null || name.isBlank() || salaryCents < 0) {
                throw new IllegalArgumentException("Invalid employee");
            }
        }
    }

    private static final class Department {
        final int id;
        final List<Department> children = new ArrayList<>();
        final Set<Integer> employees = new LinkedHashSet<>();
        Department(int id) {
            this.id = id;
        }
    }

    private static final class Node {
        Employee employee;
        Node left;
        Node right;
        int height = 1;
        Node(Employee employee) {
            this.employee = employee;
        }
    }

    private final Map<Integer, Department> departments = new HashMap<>();
    private Node root;

    public Workforce() {
        departments.put(0, new Department(0));
    }

    private Department department(int id) {
        Department result = departments.get(id);
        if (result == null) {
            throw new IllegalArgumentException("Unknown department");
        }
        return result;
    }

    public void addDepartment(int id, int parent) {
        if (id <= 0 || departments.containsKey(id)) {
            throw new IllegalArgumentException("Duplicate or invalid department ID");
        }
        Department parentNode = department(parent);
        Department child = new Department(id);
        parentNode.children.add(child);
        departments.put(id, child);
    }

    public Employee find(int id) {
        Node node = findNode(id);
        return node == null ? null : node.employee;
    }

    private Node findNode(int id) {
        Node node = root;
        while (node != null) {
            if (id == node.employee.id()) {
                return node;
            }
            node = id < node.employee.id() ? node.left : node.right;
        }
        return null;
    }

    public void add(Employee employee) {
        Department target = department(employee.department());
        root = insert(root, employee);
        target.employees.add(employee.id());
    }

    private Node insert(Node node, Employee employee) {
        if (node == null) {
            return new Node(employee);
        }
        if (employee.id() < node.employee.id()) {
            node.left = insert(node.left, employee);
        } else if (employee.id() > node.employee.id()) {
            node.right = insert(node.right, employee);
        } else {
            throw new IllegalArgumentException("Duplicate employee ID");
        }
        return rebalance(node);
    }

    private static int height(Node node) {
        return node == null ? 0 : node.height;
    }

    private static void updateHeight(Node node) {
        node.height = 1 + Math.max(height(node.left), height(node.right));
    }

    private static int balance(Node node) {
        return height(node.left) - height(node.right);
    }

    private static Node rotateRight(Node node) {
        Node pivot = node.left;
        node.left = pivot.right;
        pivot.right = node;
        updateHeight(node);
        updateHeight(pivot);
        return pivot;
    }

    private static Node rotateLeft(Node node) {
        Node pivot = node.right;
        node.right = pivot.left;
        pivot.left = node;
        updateHeight(node);
        updateHeight(pivot);
        return pivot;
    }

    private static Node rebalance(Node node) {
        updateHeight(node);
        if (balance(node) > 1) {
            if (balance(node.left) < 0) {
                node.left = rotateLeft(node.left);
            }
            return rotateRight(node);
        }
        if (balance(node) < -1) {
            if (balance(node.right) > 0) {
                node.right = rotateRight(node.right);
            }
            return rotateLeft(node);
        }
        return node;
    }

    public void transfer(int id, int destination) {
        Department target = department(destination);
        Node node = findNode(id);
        if (node == null) {
            throw new IllegalArgumentException("Unknown employee");
        }
        Employee employee = node.employee;
        if (employee.department() == destination) {
            return;
        }
        Department old = department(employee.department());
        Employee transferred = new Employee(id, employee.name(), destination, employee.salaryCents());
        old.employees.remove(id);
        target.employees.add(id);
        node.employee = transferred;
    }

    public void remove(int id) {
        Employee employee = find(id);
        if (employee == null) {
            throw new IllegalArgumentException("Unknown employee");
        }
        root = delete(root, id);
        department(employee.department()).employees.remove(id);
    }

    private Node delete(Node node, int id) {
        if (id < node.employee.id()) {
            node.left = delete(node.left, id);
        } else if (id > node.employee.id()) {
            node.right = delete(node.right, id);
        } else {
            if (node.left == null) {
                return node.right;
            }
            if (node.right == null) {
                return node.left;
            }
            Node successor = node.right;
            while (successor.left != null) {
                successor = successor.left;
            }
            // Moving the successor record inside the index does not change its department.
            node.employee = successor.employee;
            node.right = delete(node.right, successor.employee.id());
        }
        return rebalance(node);
    }

    public List<Employee> sortedEmployees() {
        List<Employee> result = new ArrayList<>();
        traverse(root, result);
        return List.copyOf(result);
    }

    private void traverse(Node node, List<Employee> result) {
        if (node == null) {
            return;
        }
        traverse(node.left, result);
        result.add(node.employee);
        traverse(node.right, result);
    }

    /** Counts direct employees and all descendants of the requested department. */
    public int count(int departmentId) {
        ArrayDeque<Department> pending = new ArrayDeque<>();
        pending.push(department(departmentId));
        int total = 0;
        while (!pending.isEmpty()) {
            Department current = pending.pop();
            total += current.employees.size();
            for (Department child : current.children) {
                pending.push(child);
            }
        }
        return total;
    }

    /** Returns an immutable ID-ordered snapshot, including both salary endpoints. */
    public List<Employee> salaryRange(long minimum, long maximum) {
        if (minimum < 0 || maximum < minimum) {
            throw new IllegalArgumentException("Invalid range");
        }
        return sortedEmployees().stream()
                .filter(e -> e.salaryCents() >= minimum && e.salaryCents() <= maximum)
                .toList();
    }

    /** Returns an immutable ID-ordered snapshot of employees in [minimumId, maximumId] in O(log n + k) time. */
    public List<Employee> idRange(int minimumId, int maximumId) {
        if (minimumId <= 0 || maximumId < minimumId) {
            throw new IllegalArgumentException("Invalid ID range");
        }
        List<Employee> result = new ArrayList<>();
        collectRange(root, minimumId, maximumId, result);
        return List.copyOf(result);
    }

    private void collectRange(Node node, int minId, int maxId, List<Employee> result) {
        if (node == null) {
            return;
        }
        int id = node.employee.id();
        if (id > minId) {
            collectRange(node.left, minId, maxId, result);
        }
        if (id >= minId && id <= maxId) {
            result.add(node.employee);
        }
        if (id < maxId) {
            collectRange(node.right, minId, maxId, result);
        }
    }

    /** Returns the sum of salaryCents across the department and all its descendants using exact big-integer arithmetic. */
    public java.math.BigInteger subtreeSalaryCents(int departmentId) {
        ArrayDeque<Department> pending = new ArrayDeque<>();
        pending.push(department(departmentId));
        java.math.BigInteger total = java.math.BigInteger.ZERO;
        while (!pending.isEmpty()) {
            Department current = pending.pop();
            for (int employeeId : current.employees) {
                Employee emp = find(employeeId);
                if (emp == null) {
                    throw new IllegalStateException("Department membership without employee");
                }
                total = total.add(java.math.BigInteger.valueOf(emp.salaryCents()));
            }
            for (Department child : current.children) {
                pending.push(child);
            }
        }
        return total;
    }

    /** Returns the height of the underlying AVL employee search tree (0 if empty). */
    public int treeHeight() {
        return height(root);
    }

    /** Returns the number of registered departments including root department 0. */
    public int departmentCount() {
        return departments.size();
    }

    /** Checks AVL structure and exact correspondence between both indexes. */
    public void verify() {
        Map<Integer, Integer> memberships = new HashMap<>();
        for (Department department : departments.values()) {
            for (int id : department.employees) {
                if (memberships.putIfAbsent(id, department.id) != null) {
                    throw new IllegalStateException("Duplicate department membership");
                }
            }
        }
        int employeeCount = memberships.size();
        verifyNode(root, 0L, (long) Integer.MAX_VALUE + 1, memberships);
        if (!memberships.isEmpty()) {
            throw new IllegalStateException("Department membership without employee");
        }
        if (count(0) != employeeCount) {
            throw new IllegalStateException("Count mismatch");
        }
    }

    private int verifyNode(Node node, long lower, long upper, Map<Integer, Integer> memberships) {
        if (node == null) {
            return 0;
        }
        Employee employee = node.employee;
        if (employee.id() <= lower || employee.id() >= upper) {
            throw new IllegalStateException("Unordered employee index");
        }
        Integer departmentId = memberships.remove(employee.id());
        if (departmentId == null || departmentId != employee.department()) {
            throw new IllegalStateException("Organization/AVL mismatch");
        }
        int leftHeight = verifyNode(node.left, lower, employee.id(), memberships);
        int rightHeight = verifyNode(node.right, employee.id(), upper, memberships);
        int actualHeight = 1 + Math.max(leftHeight, rightHeight);
        if (node.height != actualHeight || Math.abs(leftHeight - rightHeight) > 1) {
            throw new IllegalStateException("Invalid AVL height or balance");
        }
        return actualHeight;
    }

    public static void main(String[] args) {
        Workforce app = new Workforce();
        app.addDepartment(10, 0);
        app.addDepartment(20, 0);
        app.add(new Employee(100, "Demo Analyst", 10, 650000));
        app.transfer(100, 20);
        app.verify();
        System.out.println("Synthetic demo: " + app.sortedEmployees());
        System.out.println("Organization and employee index are consistent.");
    }
}
